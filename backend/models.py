"""Typed outputs for every model-backed agent. No business logic here -- just the shapes."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

RULE_TYPES = Literal[
    "prohibited_category",
    "unit_cap",
    "per_person_cap",
    "per_night_cap",
    "event_cap",
    "requires_docs",
    "unit_threshold_prohibit",
    "deadline",
    "retroactive_prohibit",
    "semester_cap",
]

Category = Literal[
    "food", "alcohol", "gift_card", "prize", "speaker_fee", "lodging",
    "apparel", "equipment", "printing", "supplies", "venue", "registration",
]


class PolicyCompilerSummary(BaseModel):
    """Final report from the Policy Compiler run. The actual rules were already persisted via
    propose_rule tool calls during the run -- this is just a human-readable summary."""

    paragraphs_reviewed: int
    rules_proposed: int
    decoy_paragraphs_skipped: list[str] = Field(description="para_ids judged guidance/info, not rules")
    notes: str = ""


class LineFacts(BaseModel):
    line_id: str
    category: Category
    headcount: int = Field(ge=0)
    qty: int = Field(ge=0)
    nights: int = Field(ge=0)
    unit_cost: float = Field(ge=0)


class RequestReaderOutput(BaseModel):
    request_id: str
    lines: list[LineFacts]


class SkepticFlag(BaseModel):
    line_id: str
    flagged: bool
    reason: str = ""


class SkepticOutput(BaseModel):
    request_id: str
    flags: list[SkepticFlag]


class CommitteeQuestion(BaseModel):
    line_id: Optional[str] = None
    question: str
    rule_id: Optional[str] = None
    quote: Optional[str] = None


class DrafterQuestionsOutput(BaseModel):
    request_id: str
    questions: list[CommitteeQuestion]


class DrafterMemoOutput(BaseModel):
    memo: str


# --- Mode A benchmark baseline (step06): a generic AI assistant, one prompt, no tools, no engine.
VerdictType = Literal["allowed", "reduced", "denied", "needs_docs"]


class ModeALineVerdict(BaseModel):
    line_id: str
    verdict: VerdictType
    allowed_amount: float = Field(ge=0)
    citation_quote: Optional[str] = Field(default=None, description="exact policy text justifying this verdict, or null if none applies")


class ModeAOutput(BaseModel):
    request_id: str
    lines: list[ModeALineVerdict]
