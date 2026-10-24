"""CHAIR: orchestrates one full Gavel run. Plain Python, not an LLM agent (see harness.md for why)
-- the pipeline order is fixed and doesn't need a model to decide it: compile rules (once), read
every request in parallel, run the Skeptic on lines the engine would currently allow in full, run
the engine, the consistency report, the optimizer, then draft committee questions and a memo.

Limits on every model call: a wall-clock timeout, a request limit, and a per-call token cap
(enforced via PydanticAI's UsageLimits on that one call). A separate whole-run token cap of
400,000 is tracked here in Python across every call this run makes. Hitting any limit raises
RunLimitHit, which ends the run cleanly with status='limit_hit' and a recorded reason -- it does
not crash the process.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.usage import UsageLimits

import mcp_server.server as srv
from backend import agents, audit, safety
from backend.db import get_connection

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

WHOLE_RUN_TOKEN_CAP = 400_000
AGENT_TIMEOUT_SECONDS = 60
READER_SEMAPHORE_SIZE = 8

# Thresholds for what the Drafter writes a question about, beyond needs_docs/flagged lines.
LARGE_REDUCTION_FRACTION = 0.5  # allowed <= 50% of requested counts as a "large reduction"


class RunLimitHit(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class ChairRun:
    def __init__(self, run_id: str, benchmark_mode: bool = True):
        self.run_id = run_id
        self.benchmark_mode = benchmark_mode
        self.conn = get_connection()
        self.total_tokens_used = 0
        self.trace: list[dict] = []

    def _trace(self, step: str, detail: dict) -> None:
        self.trace.append({"ts": datetime.now(timezone.utc).isoformat(), "step": step, **detail})

    async def _call_agent(self, agent, prompt: str, agent_name: str, *, request_limit: int, token_limit: int):
        if self.total_tokens_used >= WHOLE_RUN_TOKEN_CAP:
            audit.log_event(self.conn, self.run_id, "run_limit_hit", {"reason": "whole_run_token_cap_reached", "agent": agent_name})
            raise RunLimitHit("whole_run_token_cap_reached")

        limits = UsageLimits(request_limit=request_limit, total_tokens_limit=token_limit)
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(agent.run(prompt, usage_limits=limits), timeout=AGENT_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as exc:
            audit.log_event(self.conn, self.run_id, "run_limit_hit", {"reason": "timeout", "agent": agent_name, "seconds": AGENT_TIMEOUT_SECONDS})
            raise RunLimitHit(f"{agent_name}_timeout_after_{AGENT_TIMEOUT_SECONDS}s") from exc
        except UsageLimitExceeded as exc:
            audit.log_event(self.conn, self.run_id, "run_limit_hit", {"reason": "usage_limit_exceeded", "agent": agent_name, "error": str(exc)})
            raise RunLimitHit(f"{agent_name}_usage_limit_exceeded") from exc
        elapsed = time.monotonic() - start

        usage = result.usage
        reasoning_tokens = usage.details.get("reasoning_tokens", 0) if usage.details else 0
        self.total_tokens_used += usage.input_tokens + usage.output_tokens
        usage_logged = srv.log_usage(
            run_id=self.run_id,
            agent=agent_name,
            input_tokens=usage.input_tokens,
            cached_tokens=usage.cache_read_tokens,
            cache_write_tokens=usage.cache_write_tokens,
            output_tokens=usage.output_tokens,
            reasoning_tokens=reasoning_tokens,
            seconds=elapsed,
        )
        audit.log_event(self.conn, self.run_id, "agent_run", {"agent": agent_name, "usage": usage_logged})
        messages = ModelMessagesTypeAdapter.dump_python(result.all_messages(), mode="json")
        self._trace(
            "agent_run",
            {
                "agent": agent_name, "prompt": prompt,
                "output": result.output.model_dump() if hasattr(result.output, "model_dump") else result.output,
                "usage": usage_logged, "messages": messages,
            },
        )
        return result

    # -----------------------------------------------------------------
    # 1. Policy Compiler (once)
    # -----------------------------------------------------------------

    async def compile_rules(self) -> dict:
        result = await self._call_agent(
            agents.policy_compiler_agent, "Compile the policy into rules now.", "policy_compiler",
            request_limit=40, token_limit=60_000,
        )
        proposed = srv.list_rules(status="proposed")
        rejected = srv.list_rules(status="rejected")

        auto_approved_ids: list[str] = []
        if self.benchmark_mode:
            by_para: dict[str, list[dict]] = defaultdict(list)
            for rule in proposed:
                by_para[rule["para_id"]].append(rule)
            for para_id, rules in by_para.items():
                # "verified AND match nothing else": only auto-approve when exactly one rule was
                # proposed for this paragraph -- if the compiler proposed more than one candidate
                # for the same paragraph (it shouldn't, but could, e.g. on a retry), that's a real
                # ambiguity a human should resolve, not something the benchmark flag should paper over.
                if len(rules) == 1 and rules[0]["quote_verified"]:
                    rule = rules[0]
                    approval = srv.approve_rule(rule["id"], "benchmark-auto-approve")
                    if approval["approved"]:
                        audit.log_event(
                            self.conn, self.run_id, "auto_approved_for_benchmark",
                            {"rule_id": rule["id"], "para_id": para_id, "type": rule["type"]},
                        )
                        auto_approved_ids.append(rule["id"])
                else:
                    audit.log_event(
                        self.conn, self.run_id, "rule_needs_human_review",
                        {"para_id": para_id, "rule_ids": [r["id"] for r in rules], "reason": "multiple proposals for one paragraph"},
                    )

        approved = srv.list_rules(status="approved")
        info = {
            "summary": result.output.model_dump(),
            "proposed_count": len(proposed), "rejected_count": len(rejected),
            "auto_approved_count": len(auto_approved_ids), "approved_count": len(approved),
            "approved_rule_ids": [r["id"] for r in approved],
        }
        self._trace("policy_compiler_done", info)
        return info

    # -----------------------------------------------------------------
    # 2. Request Reader (parallel, semaphore 8)
    # -----------------------------------------------------------------

    async def _read_one_request(self, request_id: str, semaphore: asyncio.Semaphore):
        async with semaphore:
            blocked = safety.sanitize_request_in_db(self.conn, request_id, self.run_id)
            if blocked:
                self._trace("blocked_injection", {"request_id": request_id, "events": blocked})
            result = await self._call_agent(
                agents.request_reader_agent, f"Read and classify every line of request {request_id}.",
                f"request_reader:{request_id}", request_limit=10, token_limit=12_000,
            )
            output = result.output
            for line in output.lines:
                self.conn.execute(
                    "UPDATE lines SET category=?, headcount=?, qty=?, nights=?, unit_cost=? WHERE id=?",
                    (line.category, line.headcount, line.qty, line.nights, line.unit_cost, line.line_id),
                )
            self.conn.commit()
            return request_id, output

    async def read_all_requests(self, request_ids: list[str]) -> dict[str, list[str]]:
        """Returns {request_id: [error strings]} for any request whose Reader call failed (a
        RunLimitHit stops the whole run; other errors are recorded per-request and skipped)."""
        semaphore = asyncio.Semaphore(READER_SEMAPHORE_SIZE)
        tasks = [self._read_one_request(rid, semaphore) for rid in request_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors: dict[str, list[str]] = {}
        for request_id, outcome in zip(request_ids, results):
            if isinstance(outcome, RunLimitHit):
                raise outcome
            if isinstance(outcome, Exception):
                errors[request_id] = [repr(outcome)]
                audit.log_event(self.conn, self.run_id, "request_reader_failed", {"request_id": request_id, "error": repr(outcome)})
        return errors

    # -----------------------------------------------------------------
    # 3. Skeptic (only lines the engine would currently allow in full)
    # -----------------------------------------------------------------

    def _preliminary_allowed_lines(self, request_ids: list[str]) -> dict[str, list[str]]:
        candidates: dict[str, list[str]] = {}
        for request_id in request_ids:
            engine_result = srv.run_engine(request_id)["lines"]
            allowed = [line_id for line_id, r in engine_result.items() if r["verdict"] == "allowed"]
            if allowed:
                candidates[request_id] = allowed
        return candidates

    async def _run_skeptic_one_request(self, request_id: str, line_ids: list[str], semaphore: asyncio.Semaphore):
        async with semaphore:
            lines_block = "\n".join(f"- {lid}" for lid in line_ids)
            prompt = (
                f"Request {request_id}. These lines were classified by the Request Reader and the "
                f"engine's preliminary verdict for each is currently 'allowed':\n{lines_block}\n"
                f"Call get_request to see their descriptions and amounts, then review each one."
            )
            result = await self._call_agent(
                agents.skeptic_agent, prompt, f"skeptic:{request_id}", request_limit=10, token_limit=10_000,
            )
            return result.output

    async def run_skeptic(self, candidates: dict[str, list[str]]) -> dict[str, dict]:
        """Returns {line_id: {"flagged": bool, "reason": str}} for every reviewed line."""
        semaphore = asyncio.Semaphore(READER_SEMAPHORE_SIZE)
        tasks = [self._run_skeptic_one_request(rid, lids, semaphore) for rid, lids in candidates.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        flags: dict[str, dict] = {}
        for (request_id, _line_ids), outcome in zip(candidates.items(), results):
            if isinstance(outcome, RunLimitHit):
                raise outcome
            if isinstance(outcome, Exception):
                audit.log_event(self.conn, self.run_id, "skeptic_failed", {"request_id": request_id, "error": repr(outcome)})
                continue
            for flag in outcome.flags:
                flags[flag.line_id] = {"flagged": flag.flagged, "reason": flag.reason}
        return flags

    # -----------------------------------------------------------------
    # 4/5. Engine + consistency + optimizer (code only, no model calls)
    # -----------------------------------------------------------------

    def persist_verdicts(self, request_ids: list[str], skeptic_flags: dict[str, dict]) -> dict[str, dict]:
        all_results: dict[str, dict] = {}
        for request_id in request_ids:
            engine_result = srv.run_engine(request_id)["lines"]
            for line_id, res in engine_result.items():
                flag = skeptic_flags.get(line_id, {"flagged": False, "reason": ""})
                self.conn.execute(
                    """INSERT INTO verdicts (run_id, line_id, verdict, allowed_amount, rules_json, explanation, flagged_for_review)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        self.run_id, line_id, res["verdict"], res["allowed_amount"], json.dumps(res["rules"]),
                        flag["reason"] if flag["flagged"] else None, 1 if flag["flagged"] else 0,
                    ),
                )
                all_results[line_id] = {**res, "request_id": request_id, "flagged_for_review": flag["flagged"], "flag_reason": flag["reason"]}
                self._trace("verdict", {"request_id": request_id, "line_id": line_id, **res, "flagged_for_review": flag["flagged"], "flag_reason": flag["reason"]})
        self.conn.commit()
        self._trace("engine_run_complete", {"line_count": len(all_results)})
        return all_results

    # -----------------------------------------------------------------
    # 6. Drafter
    # -----------------------------------------------------------------

    def _lines_needing_questions(self, request_id: str, verdicts: dict[str, dict]) -> list[dict]:
        request = srv.get_request(request_id)
        descriptions = {line["id"]: line for line in request["lines"]}
        needing = []
        for line_id, result in verdicts.items():
            if result["request_id"] != request_id:
                continue
            amount = descriptions[line_id]["amount"]
            large_reduction = (
                result["verdict"] == "reduced" and amount > 0 and result["allowed_amount"] <= LARGE_REDUCTION_FRACTION * amount
            )
            if result["verdict"] == "needs_docs" or result["flagged_for_review"] or large_reduction:
                explanation = srv.explain_line(request_id, line_id)
                needing.append(
                    {
                        "line_id": line_id, "description": descriptions[line_id]["description"], "amount": amount,
                        "verdict": result["verdict"], "allowed_amount": result["allowed_amount"],
                        "why": "needs_docs" if result["verdict"] == "needs_docs" else ("skeptic_flag" if result["flagged_for_review"] else "large_reduction"),
                        "flag_reason": result["flag_reason"],
                        "citations": explanation["citations"],
                    }
                )
        return needing

    async def _draft_questions_one_request(self, request_id: str, line_infos: list[dict], semaphore: asyncio.Semaphore):
        async with semaphore:
            lines_block = "\n".join(
                f"- {li['line_id']}: {li['description']} (${li['amount']}), verdict={li['verdict']}, "
                f"allowed=${li['allowed_amount']}, reason={li['why']}"
                + (f" ({li['flag_reason']})" if li["flag_reason"] else "")
                + (f", citation: {li['citations'][0]['quote']}" if li["citations"] else "")
                for li in line_infos
            )
            prompt = f"Request {request_id}. Draft questions for these lines:\n{lines_block}"
            result = await self._call_agent(
                agents.drafter_questions_agent, prompt, f"drafter_questions:{request_id}",
                request_limit=6, token_limit=8_000,
            )
            return result.output

    def _save_draft(self, kind: str, request_id: str | None, content: dict) -> str:
        draft_id = f"DRAFT-{uuid.uuid4().hex[:8]}"
        self.conn.execute(
            "INSERT INTO drafts (id, run_id, request_id, kind, content_json, status, created_at) VALUES (?, ?, ?, ?, ?, 'awaiting_approval', ?)",
            (draft_id, self.run_id, request_id, kind, json.dumps(content), datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        return draft_id

    async def run_drafter(
        self, request_ids: list[str], verdicts: dict[str, dict], consistency: dict, allocation: dict, club_history: dict
    ) -> dict:
        semaphore = asyncio.Semaphore(READER_SEMAPHORE_SIZE)
        per_request_tasks = []
        per_request_ids = []
        for request_id in request_ids:
            needing = self._lines_needing_questions(request_id, verdicts)
            if needing:
                per_request_tasks.append(self._draft_questions_one_request(request_id, needing, semaphore))
                per_request_ids.append(request_id)

        results = await asyncio.gather(*per_request_tasks, return_exceptions=True) if per_request_tasks else []
        question_drafts = []
        for request_id, outcome in zip(per_request_ids, results):
            if isinstance(outcome, RunLimitHit):
                raise outcome
            if isinstance(outcome, Exception):
                audit.log_event(self.conn, self.run_id, "drafter_questions_failed", {"request_id": request_id, "error": repr(outcome)})
                continue
            draft_id = self._save_draft("questions", request_id, outcome.model_dump())
            question_drafts.append({"draft_id": draft_id, "request_id": request_id, "questions": outcome.model_dump()["questions"]})

        verdict_counts: dict[str, int] = defaultdict(int)
        for result in verdicts.values():
            verdict_counts[result["verdict"]] += 1
        total_requested = sum(
            line["amount"] for request_id in request_ids for line in srv.get_request(request_id)["lines"]
        )
        total_allowed = sum(result["allowed_amount"] for result in verdicts.values())
        memo_prompt = (
            f"Pot: ${club_history['pot']}. Total requested across all clubs: ${total_requested}. "
            f"Total allowed by policy: ${total_allowed}. Verdict breakdown: {dict(verdict_counts)}. "
            f"Consistency check: {consistency['inconsistent_count']} of {consistency['matched']} "
            f"prior decisions were inconsistent with what this year's rules would allow. "
            f"Allocation scenario used (alpha=0.5): total allocated ${sum(allocation['allocation'].values())}."
        )
        memo_result = await self._call_agent(
            agents.drafter_memo_agent, memo_prompt, "drafter_memo", request_limit=6, token_limit=10_000,
        )
        memo_draft_id = self._save_draft("memo", None, memo_result.output.model_dump())

        return {
            "question_drafts": question_drafts,
            "memo_draft_id": memo_draft_id,
            "memo": memo_result.output.memo,
        }

    # -----------------------------------------------------------------
    # Run status
    # -----------------------------------------------------------------

    def finalize_run(self, status: str, reason: str | None = None) -> None:
        self.conn.execute(
            "UPDATE runs SET finished_at = ?, status = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), status, self.run_id),
        )
        self.conn.commit()
        audit.log_event(self.conn, self.run_id, "run_end", {"status": status, "reason": reason})
        self._trace("run_end", {"status": status, "reason": reason, "total_tokens_used": self.total_tokens_used})


async def run_full_pipeline(request_ids: list[str], *, benchmark_mode: bool = True, run_id: str | None = None) -> dict:
    run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
    chair = ChairRun(run_id, benchmark_mode=benchmark_mode)
    audit.log_event(chair.conn, run_id, "run_start", {"request_ids": request_ids, "benchmark_mode": benchmark_mode})

    chair.conn.execute(
        "INSERT INTO runs (id, started_at, status, mode) VALUES (?, ?, 'running', ?)",
        (run_id, datetime.now(timezone.utc).isoformat(), "benchmark" if benchmark_mode else "live"),
    )
    chair.conn.commit()

    rules_info: dict = {}
    reader_errors: dict = {}
    all_results: dict = {}
    consistency: dict = {}
    allocation: dict = {}
    drafts: dict = {}

    try:
        rules_info = await chair.compile_rules()
        reader_errors = await chair.read_all_requests(request_ids)
        candidates = chair._preliminary_allowed_lines(request_ids)
        skeptic_flags = await chair.run_skeptic(candidates)
        all_results = chair.persist_verdicts(request_ids, skeptic_flags)

        consistency = srv.consistency_report()
        club_history = json.loads((DATA_DIR / "club_history.json").read_text())
        allocation = srv.allocate(club_history["pot"], 0.5)
        drafts = await chair.run_drafter(request_ids, all_results, consistency, allocation, club_history)

        chair.finalize_run("completed")
        status, reason = "completed", None
    except RunLimitHit as exc:
        chair.finalize_run("limit_hit", reason=exc.reason)
        status, reason = "limit_hit", exc.reason
    finally:
        trace = chair.trace
        total_tokens = chair.total_tokens_used
        chair.conn.close()

    return {
        "run_id": run_id,
        "status": status,
        "reason": reason,
        "total_tokens_used": total_tokens,
        "rules_info": rules_info,
        "reader_errors": reader_errors,
        "verdicts": all_results,
        "consistency": consistency,
        "allocation": allocation,
        "drafts": drafts,
        "trace": trace,
    }
