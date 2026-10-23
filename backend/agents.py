"""The Gavel agent team: Policy Compiler, Request Reader, Skeptic, Drafter (questions + memo).
Every agent uses the same model -- gpt-6-luna through Portkey, the only model this project
allows -- via PydanticAI's OpenAIResponsesModel (the /v1/responses endpoint; chat completions
rejects tool calls when reasoning effort is set). Agents touch data only through the MCP server
(mcp_server/server.py); CHAIR (backend/chair.py) is plain Python orchestration, not an LLM agent
-- see harness.md for why.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from backend.models import (
    DrafterMemoOutput,
    DrafterQuestionsOutput,
    PolicyCompilerSummary,
    RequestReaderOutput,
    SkepticOutput,
)
from env_loader import require_env

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
SERVER_SCRIPT = ROOT / "mcp_server" / "server.py"

# Only model/provider allowed for this project: gpt-6-luna, through Portkey.
MODEL_NAME = "gpt-6-luna"

require_env(["PORTKEY_API_KEY"])

_provider = OpenAIProvider(base_url="https://api.portkey.ai/v1", api_key=os.environ["PORTKEY_API_KEY"])
# Reasoning effort "low": this is a reasoning model on a shared, sometimes-slow endpoint: low
# effort is enough for classification/compilation work at a fraction of the token cost of the
# default ("medium"). `timeout` bounds a single call to the model API (the stdio MCP round-trip
# itself is bounded separately, in backend/chair.py's asyncio.wait_for wrapper).
MODEL = OpenAIResponsesModel(
    MODEL_NAME,
    provider=_provider,
    settings=OpenAIResponsesModelSettings(openai_reasoning_effort="low", openai_text_verbosity="low", timeout=60),
)


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text()


def _toolset_for(names: set[str]):
    base = MCPToolset(SERVER_SCRIPT)
    return base.filtered(lambda ctx, tool_def, _names=names: tool_def.name in _names)


POLICY_COMPILER_TOOLS = {"load_policy", "propose_rule"}
READER_TOOLS = {"get_request"}
SKEPTIC_TOOLS = {"get_request"}
# Drafter agents get no tools: CHAIR already resolves everything they need (line facts, verdicts,
# citations via explain_line, aggregate totals) into the prompt before calling them, since none of
# that requires the agent to make its own fresh tool call.

policy_compiler_agent = Agent(
    MODEL,
    output_type=PolicyCompilerSummary,
    system_prompt=_load_prompt("policy_compiler"),
    toolsets=[_toolset_for(POLICY_COMPILER_TOOLS)],
)

request_reader_agent = Agent(
    MODEL,
    output_type=RequestReaderOutput,
    system_prompt=_load_prompt("request_reader"),
    toolsets=[_toolset_for(READER_TOOLS)],
)

skeptic_agent = Agent(
    MODEL,
    output_type=SkepticOutput,
    system_prompt=_load_prompt("skeptic"),
    toolsets=[_toolset_for(SKEPTIC_TOOLS)],
)

drafter_questions_agent = Agent(
    MODEL,
    output_type=DrafterQuestionsOutput,
    system_prompt=_load_prompt("drafter_questions"),
)

drafter_memo_agent = Agent(
    MODEL,
    output_type=DrafterMemoOutput,
    system_prompt=_load_prompt("drafter_memo"),
)
