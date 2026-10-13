"""Data models for AI opportunity intake."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class UseCaseInput:
    """Raw intake captured during a discovery conversation with business stakeholders."""

    title: str
    business_area: str                 # e.g. "Claims", "Provider Enrollment", "Prior Authorization"
    problem_statement: str             # pain point in the stakeholder's own words
    current_process: str = ""          # how the work is done today
    desired_outcome: str = ""          # what "good" looks like
    monthly_volume: int = 0            # transactions / cases / calls per month
    minutes_per_item: float = 0.0      # manual handling time per item today
    data_sources: List[str] = field(default_factory=list)
    data_is_structured: Optional[bool] = None
    involves_phi: bool = True          # default to the safer assumption in healthcare
    decision_impacts_member_or_provider: bool = False  # e.g. denies a claim, blocks enrollment
    stakeholders: List[str] = field(default_factory=list)
    sponsor: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DimensionScore:
    name: str
    score: int          # 1 (low) .. 5 (high)
    rationale: str


@dataclass
class ResponsibleAIFlag:
    category: str       # Human oversight, Privacy/PHI, Compliance, Operational risk, Bias/fairness
    severity: str       # Low / Medium / High
    finding: str
    mitigation: str
    escalate: bool = False


@dataclass
class Assessment:
    use_case: UseCaseInput
    ai_patterns: List[str]
    workflow_domain: str
    scores: List[DimensionScore]
    priority_score: float
    quadrant: str
    estimated_hours_saved_per_month: float
    estimated_fte_equivalent: float
    value_hypothesis: str
    use_case_summary: str
    solution_concept: str
    requirements: List[str]
    success_metrics: List[str]
    responsible_ai_flags: List[ResponsibleAIFlag]
    open_questions: List[str]
    generated_by: str = "rules"   # "rules" or "llm"

    def score(self, name: str) -> int:
        for s in self.scores:
            if s.name == name:
                return s.score
        raise KeyError(name)

    def to_dict(self) -> dict:
        return asdict(self)
