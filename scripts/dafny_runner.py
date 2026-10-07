"""Wrapper fino em torno de `dafny verify --json-output`.

Esquema de saída verificado empiricamente nesta sessão (Dafny 4.11.0,
macOS arm64 e comportamento equivalente esperado no Linux da CI — mesma
versão fixada, ver .github/workflows/verify.yml): a ferramenta imprime,
por linha, um objeto JSON com `"type"` igual a `"diagnostic"` (um erro ou
aviso pontual, com localização) ou `"status"` (a linha-resumo final, ex.:
"Dafny program verifier finished with 3 verified, 0 errors"). Isto **não**
é a flag citada na versão original do paper (`--diagnosticsFormat json` —
essa flag não existe em 4.11.0; foi corrigida para `--json-output` depois
de testar o binário real). Ver docs/orchestration.md, seção "Diagnóstico
do Dafny", para a correção completa e para o aviso de honestidade sobre o
que NÃO foi testado (timeouts reais — ver `Obligation.looks_inconclusive`).
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field


@dataclass
class Diagnostic:
    severity: int
    message: str
    file: str
    line: int
    character: int
    raw: dict

    @property
    def looks_inconclusive(self) -> bool:
        """Heurística NÃO confirmada contra um timeout real do Dafny nesta
        sessão (ver aviso no topo do arquivo) — procura substrings
        observadas na documentação/discussões do Boogie/Dafny para
        UNKNOWN/timeout. Qualquer execução real que produza um diagnóstico
        deste tipo deve ter a linha JSON bruta copiada para o campo
        `notes` do registro em results/ (Seção 9.3 do paper), para
        corrigir esta heurística com dado real em vez de suposição.
        """
        text = self.message.lower()
        return any(
            s in text
            for s in ("timed out", "time out", "timeout", "out of resource", "inconclusive")
        )


@dataclass
class VerificationResult:
    exit_code: int
    verified_count: int | None
    error_count: int | None
    diagnostics: list  # list[Diagnostic], apenas severity de erro (>=1)
    raw_ndjson: list  # linhas brutas, para auditoria (Seção 9.3)
    command: list

    @property
    def all_proved(self) -> bool:
        return self.exit_code == 0 and (self.error_count or 0) == 0

    @property
    def any_inconclusive(self) -> bool:
        return any(d.looks_inconclusive for d in self.diagnostics)


_STATUS_RE = re.compile(r"(\d+)\s+verified,\s+(\d+)\s+error")


def run_dafny_verify(dafny_bin: str, dfy_path: str, timeout_seconds: int = 120) -> VerificationResult:
    cmd = [dafny_bin, "verify", "--json-output", dfy_path]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )

    raw_lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    diagnostics: list[Diagnostic] = []
    verified_count = None
    error_count = None

    for line in raw_lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue  # linha não-JSON (ex.: warning do runtime .NET) — ignorada, mantida em raw_ndjson

        if obj.get("type") == "diagnostic":
            value = obj.get("value", {})
            loc = value.get("location", {})
            range_ = loc.get("range", {})
            start = range_.get("start", {})
            diagnostics.append(
                Diagnostic(
                    severity=value.get("severity", -1),
                    message=value.get("defaultFormatMessage", ""),
                    file=loc.get("filename", ""),
                    line=start.get("line", -1),
                    character=start.get("character", -1),
                    raw=obj,
                )
            )
        elif obj.get("type") == "status":
            m = _STATUS_RE.search(obj.get("value", ""))
            if m:
                verified_count = int(m.group(1))
                error_count = int(m.group(2))

    return VerificationResult(
        exit_code=proc.returncode,
        verified_count=verified_count,
        error_count=error_count,
        diagnostics=diagnostics,
        raw_ndjson=raw_lines,
        command=cmd,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("uso: python3 dafny_runner.py <caminho-do-dafny> <arquivo.dfy>", file=sys.stderr)
        raise SystemExit(2)

    result = run_dafny_verify(sys.argv[1], sys.argv[2])
    print(f"exit_code={result.exit_code} verified={result.verified_count} errors={result.error_count}")
    print(f"all_proved={result.all_proved} any_inconclusive={result.any_inconclusive}")
    for d in result.diagnostics:
        print(f"  [{d.file}:{d.line}] {d.message}")
