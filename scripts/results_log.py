"""Registro de execuções em results/, seguindo o esquema documentado em
results/README.md. Append-only JSONL — uma linha por tentativa, incluindo
falhas e resultados inconclusivos (nunca omitidos — ver Seção 9.4 do
paper, cujos denominadores exigem as tentativas, não só os sucessos).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


SCHEMA_FIELDS = [
    "task_id", "group", "model_version", "model_config", "prompt_version",
    "tools_available", "attempt_number", "budget_limits", "verifier_version",
    "solver_version", "environment", "commit_sha", "timestamp",
    "obligations_total", "obligations_proved", "obligations_unknown",
    "contract_modified_by_agent", "integrity_violations",
    "independent_eval_passed", "human_intervention", "time_seconds",
    "cost_tokens", "outcome", "notes",
]


@dataclass
class ResultRecord:
    task_id: str
    group: str
    model_version: str
    model_config: dict
    prompt_version: str
    tools_available: list
    attempt_number: int
    budget_limits: dict
    verifier_version: str
    solver_version: str
    environment: str
    commit_sha: str
    obligations_total: int
    obligations_proved: int
    obligations_unknown: int
    contract_modified_by_agent: bool
    integrity_violations: list
    independent_eval_passed: bool
    human_intervention: bool
    time_seconds: float
    cost_tokens: int
    outcome: str  # "success" | "failure" | "inconclusive" — ver docs/orchestration.md para a regra exata
    notes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        missing = [f for f in SCHEMA_FIELDS if f not in d]
        if missing:
            raise ValueError(f"ResultRecord não cobre os campos do esquema: {missing}")
        return d


def append_result(results_dir: str, record: ResultRecord) -> str:
    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, "runs.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    return path
