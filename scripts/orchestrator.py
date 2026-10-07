"""Orquestrador dos grupos A/B/C (Seção 9 do paper).

Ver docs/orchestration.md para a explicação completa do fluxo. Resumo:

  Grupo A: requisito em linguagem natural, sem contrato, 1 tentativa.
  Grupo B: requisito + contrato formal fixo, sem feedback do verificador, 1 tentativa.
  Grupo C: requisito + contrato formal fixo + diagnóstico do verificador entre
           tentativas, até --max-attempts tentativas.

Toda tentativa — sucesso, falha ou inconclusiva — é registrada em
results/runs.jsonl (scripts/results_log.py), nunca só as bem-sucedidas.

Exemplo (modo mock, sem chamar nenhuma API, sem gastar orçamento real):

  python3 scripts/orchestrator.py --task task-01-debit --group C \
      --backend mock --mock-responses scripts/examples/mock_responses_c.json \
      --dafny-bin /caminho/para/dafny --max-attempts 3
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

from agent_backend import AnthropicBackend, MockBackend
from dafny_runner import run_dafny_verify
from dfy_contract_utils import BodyNotFoundError, split_header_and_body, splice
from integrity_check import check_integrity
from results_log import ResultRecord, append_result

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_DIR = os.path.join(REPO_ROOT, "tasks")
PROMPTS_DIR = os.path.join(REPO_ROOT, "prompts")

_CODE_BLOCK_RE = re.compile(r"```dafny\s*\n(.*?)```", re.DOTALL)
_PROMPT_VERSION_RE = re.compile(r"<!--\s*prompt_version:\s*([\w.-]+)\s*-->")
_METHOD_SIG_RE = re.compile(r"\bmethod\s+(\w+)\s*\(([^)]*)\)\s*returns\s*\(([^)]*)\)")
_NEWTYPE_RE = re.compile(r"^newtype .*$", re.MULTILINE)


def _newtype_line(contract_source: str) -> str:
    m = _NEWTYPE_RE.search(contract_source)
    if not m:
        raise ValueError("não foi possível localizar uma declaração 'newtype' em contract.dfy")
    return m.group(0)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _load_task(task_id: str) -> dict:
    task_dir = os.path.join(TASKS_DIR, task_id)
    if not os.path.isdir(task_dir):
        raise FileNotFoundError(f"tarefa não encontrada: {task_dir}")
    return {
        "dir": task_dir,
        "requirement": _read(os.path.join(task_dir, "requirement.md")),
        "contract": _read(os.path.join(task_dir, "contract.dfy")),
        "visible_tests": _read(os.path.join(task_dir, "visible_tests.dfy")),
        "hidden_tests_path": os.path.join(task_dir, "hidden_tests.dfy"),
    }


def _method_identity(contract_source: str) -> tuple[str, str, str]:
    m = _METHOD_SIG_RE.search(contract_source)
    if not m:
        raise ValueError("não foi possível localizar a assinatura do método em contract.dfy")
    return m.group(1), m.group(2).strip(), m.group(3).strip()


def _prompt_version(template: str) -> str:
    m = _PROMPT_VERSION_RE.search(template)
    return m.group(1) if m else "sem-versao"


def _render(template: str, **kwargs) -> str:
    out = template
    for key, value in kwargs.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def _extract_code(response_text: str) -> str | None:
    m = _CODE_BLOCK_RE.search(response_text)
    if not m:
        return None
    return m.group(1)


def _git_commit_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() if out.returncode == 0 else "desconhecido"
    except Exception:
        return "desconhecido"


def _dafny_version(dafny_bin: str) -> str:
    try:
        out = subprocess.run([dafny_bin, "--version"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or out.stderr.strip() or "desconhecido"
    except Exception:
        return "desconhecido"


def _format_feedback(diagnostics) -> str:
    if not diagnostics:
        return "(nenhum diagnóstico — verifique se o bloco de código foi extraído corretamente)"
    lines = []
    for d in diagnostics:
        lines.append(f"- linha {d.line}, coluna {d.character}: {d.message}")
    return "\n".join(lines)


def run_attempt(
    *,
    task: dict,
    group: str,
    method_name: str,
    attempt_number: int,
    max_attempts: int,
    backend,
    dafny_bin: str,
    verifier_version: str,
    commit_sha: str,
    environment: str,
    model_version: str,
    feedback_text: str | None,
) -> ResultRecord:
    start = time.monotonic()
    notes: list[str] = []

    system_prompt = _read(os.path.join(PROMPTS_DIR, "common", "system_prompt.md"))

    if group == "A":
        method_name_sig, params, returns = _method_identity(task["contract"])
        template = _read(os.path.join(PROMPTS_DIR, "group_a.md"))
        prompt_version = _prompt_version(template)
        user_prompt = _render(
            template,
            REQUIREMENT=task["requirement"],
            NEWTYPE_LINE=_newtype_line(task["contract"]),
            METHOD_NAME=method_name_sig,
            METHOD_PARAMS=params,
            METHOD_RETURNS=returns,
        )
    elif group == "B":
        template = _read(os.path.join(PROMPTS_DIR, "group_b.md"))
        prompt_version = _prompt_version(template)
        user_prompt = _render(
            template,
            REQUIREMENT=task["requirement"],
            CONTRACT=task["contract"],
            VISIBLE_TESTS=task["visible_tests"],
        )
    elif group == "C":
        template = _read(os.path.join(PROMPTS_DIR, "group_c.md"))
        prompt_version = _prompt_version(template)
        user_prompt = _render(
            template,
            REQUIREMENT=task["requirement"],
            CONTRACT=task["contract"],
            VISIBLE_TESTS=task["visible_tests"],
            MAX_ATTEMPTS=str(max_attempts),
        )
        if feedback_text:
            user_prompt += (
                "\n\n## Diagnóstico da tentativa anterior\n\n"
                f"```\n{feedback_text}\n```\n"
            )
    else:
        raise ValueError(f"grupo inválido: {group!r}")

    response_text = backend.complete(system_prompt, user_prompt)
    usage = getattr(backend, "last_usage", {}) or {}
    cost_tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))

    code = _extract_code(response_text)

    obligations_total = obligations_proved = obligations_unknown = 0
    contract_modified_by_agent = False
    integrity_violations: list[str] = []
    independent_eval_passed = False
    any_inconclusive = False
    raw_diagnostics_for_feedback: list = []

    if code is None:
        notes.append("não foi possível extrair bloco ```dafny``` da resposta do agente")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            submission_path = os.path.join(tmp, "submission.dfy")
            with open(submission_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Passo 1: verificação da submissão exatamente como foi dada.
            raw_result = run_dafny_verify(dafny_bin, submission_path)
            raw_diagnostics_for_feedback = raw_result.diagnostics
            obligations_total = (raw_result.verified_count or 0) + (raw_result.error_count or 0)
            obligations_proved = raw_result.verified_count or 0
            obligations_unknown = 0  # Dafny --json-output não distingue UNKNOWN de erro definitivo (ver dafny_runner.py)
            any_inconclusive = raw_result.any_inconclusive

            # Passo 2: auditoria de integridade contra o contrato canônico (Seção 6).
            if group in ("B", "C"):
                findings = check_integrity(code, task["contract"], method_name)
                integrity_violations = [f"{f.kind}: {f.detail}" for f in findings]
                contract_modified_by_agent = bool(integrity_violations)

            # Passo 3: avaliação independente — corpo extraído, reencaixado no
            # contrato canônico verdadeiro, verificado contra hidden_tests.dfy.
            try:
                canon_header, _ = split_header_and_body(task["contract"], method_name)
                _, sub_body = split_header_and_body(code, method_name)
                canonical_source = splice(canon_header, sub_body)

                canonical_path = os.path.join(tmp, "canonical_submission.dfy")
                with open(canonical_path, "w", encoding="utf-8") as f:
                    f.write(canonical_source)
                canonical_result = run_dafny_verify(dafny_bin, canonical_path)

                eval_dir = os.path.join(tmp, "eval")
                os.makedirs(eval_dir, exist_ok=True)
                with open(os.path.join(eval_dir, "submission.dfy"), "w", encoding="utf-8") as f:
                    f.write(canonical_source)
                shutil.copy(task["hidden_tests_path"], os.path.join(eval_dir, os.path.basename(task["hidden_tests_path"])))
                hidden_result = run_dafny_verify(
                    dafny_bin, os.path.join(eval_dir, os.path.basename(task["hidden_tests_path"]))
                )

                independent_eval_passed = canonical_result.all_proved and hidden_result.all_proved
                any_inconclusive = any_inconclusive or canonical_result.any_inconclusive or hidden_result.any_inconclusive
            except BodyNotFoundError as exc:
                notes.append(f"extração do corpo da submissão falhou: {exc} — avaliação independente não pôde ser feita")
                independent_eval_passed = False

    if any_inconclusive:
        outcome = "inconclusive"
    elif independent_eval_passed:
        outcome = "success"
    else:
        outcome = "failure"

    record = ResultRecord(
        task_id=os.path.basename(task["dir"]),
        group=group,
        model_version=model_version,
        model_config={},
        prompt_version=prompt_version,
        tools_available=[],
        attempt_number=attempt_number,
        budget_limits={"max_attempts": max_attempts},
        verifier_version=verifier_version,
        solver_version="não capturado automaticamente nesta versão do orquestrador (ver docs/orchestration.md)",
        environment=environment,
        commit_sha=commit_sha,
        obligations_total=obligations_total,
        obligations_proved=obligations_proved,
        obligations_unknown=obligations_unknown,
        contract_modified_by_agent=contract_modified_by_agent,
        integrity_violations=integrity_violations,
        independent_eval_passed=independent_eval_passed,
        human_intervention=False,
        time_seconds=round(time.monotonic() - start, 3),
        cost_tokens=cost_tokens,
        outcome=outcome,
        notes="; ".join(notes),
    )
    return record, raw_diagnostics_for_feedback


def run_task(
    *,
    task_id: str,
    group: str,
    backend,
    dafny_bin: str,
    max_attempts: int,
    model_version: str,
    environment: str,
    results_dir: str,
) -> list[ResultRecord]:
    task = _load_task(task_id)
    method_name, _, _ = _method_identity(task["contract"])
    verifier_version = _dafny_version(dafny_bin)
    commit_sha = _git_commit_sha()

    effective_max = 1 if group in ("A", "B") else max_attempts
    records: list[ResultRecord] = []
    feedback_text = None

    for attempt in range(1, effective_max + 1):
        record, raw_diagnostics = run_attempt(
            task=task,
            group=group,
            method_name=method_name,
            attempt_number=attempt,
            max_attempts=effective_max,
            backend=backend,
            dafny_bin=dafny_bin,
            verifier_version=verifier_version,
            commit_sha=commit_sha,
            environment=environment,
            model_version=model_version,
            feedback_text=feedback_text,
        )
        append_result(results_dir, record)
        records.append(record)

        if record.outcome == "success" or group != "C":
            break
        feedback_text = _format_feedback(raw_diagnostics)

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="id da tarefa, ex.: task-01-debit")
    parser.add_argument("--group", required=True, choices=["A", "B", "C"])
    parser.add_argument("--backend", required=True, choices=["mock", "anthropic"])
    parser.add_argument("--model", default="", help="obrigatório para --backend anthropic")
    parser.add_argument("--mock-responses", default="", help="JSON com lista de respostas, para --backend mock")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--dafny-bin", required=True)
    parser.add_argument("--results-dir", default=os.path.join(REPO_ROOT, "results"))
    parser.add_argument("--environment", default="local-dev")
    args = parser.parse_args()

    if args.backend == "mock":
        if not args.mock_responses:
            parser.error("--mock-responses é obrigatório para --backend mock")
        with open(args.mock_responses, encoding="utf-8") as f:
            responses = json.load(f)
        backend = MockBackend(responses)
        model_version = "mock"
    else:
        if not args.model:
            parser.error("--model é obrigatório para --backend anthropic")
        backend = AnthropicBackend(model=args.model)
        model_version = args.model

    records = run_task(
        task_id=args.task,
        group=args.group,
        backend=backend,
        dafny_bin=args.dafny_bin,
        max_attempts=args.max_attempts,
        model_version=model_version,
        environment=args.environment,
        results_dir=args.results_dir,
    )

    for r in records:
        print(f"tentativa {r.attempt_number}: outcome={r.outcome} independent_eval_passed={r.independent_eval_passed} integrity_violations={r.integrity_violations}")


if __name__ == "__main__":
    main()
