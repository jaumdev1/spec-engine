"""Utilitários de manipulação textual de arquivos .dfy usados pelo
orquestrador (ver docs/orchestration.md).

Limitação deliberada e documentada: isto NÃO é um parser Dafny real (não
há AST). É um scanner de chaves ingênuo, com remoção de comentários de
linha (`//`) antes de contar chaves, suficiente para o estilo de código
gerado neste projeto (sem literais de string contendo `{`/`}` dentro do
corpo de métodos). Qualquer uso fora desse escopo deve ser revisado
manualmente — ver Seção "Limitações conhecidas" em docs/orchestration.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


class BodyNotFoundError(Exception):
    pass


def _strip_line_comments(source: str) -> str:
    """Substitui o conteúdo após `//` em cada linha por espaços, preservando
    deslocamentos de caractere (offsets) para que o brace-matching feito
    sobre o resultado ainda aponte para posições válidas no texto original.
    """
    out_lines = []
    for line in source.split("\n"):
        idx = line.find("//")
        if idx == -1:
            out_lines.append(line)
        else:
            out_lines.append(line[:idx] + " " * (len(line) - idx))
    return "\n".join(out_lines)


@dataclass
class MethodSpan:
    header_end: int  # índice (exclusive) do fim do header, isto é, logo após o "{" de abertura
    body_start: int  # == header_end
    body_end: int  # índice do "}" de fechamento (inclusive, ou seja, source[body_end] == '}')


def find_method_span(source: str, method_name: str) -> MethodSpan:
    """Localiza `method <method_name>(...)` e faz brace-matching a partir
    do primeiro `{` encontrado após a assinatura (que deve vir depois de
    quaisquer cláusulas `requires`/`ensures`/`modifies`/`decreases`).
    """
    scan_source = _strip_line_comments(source)

    sig_match = re.search(r"\bmethod\s+" + re.escape(method_name) + r"\s*\(", scan_source)
    if not sig_match:
        raise BodyNotFoundError(f"assinatura 'method {method_name}(' não encontrada")

    brace_open = scan_source.find("{", sig_match.end())
    if brace_open == -1:
        raise BodyNotFoundError(f"'{{' de abertura do corpo de {method_name} não encontrado")

    depth = 0
    i = brace_open
    n = len(scan_source)
    while i < n:
        c = scan_source[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return MethodSpan(header_end=brace_open + 1, body_start=brace_open + 1, body_end=i)
        i += 1

    raise BodyNotFoundError(f"'}}' de fechamento do corpo de {method_name} não encontrado (chaves desbalanceadas)")


def split_header_and_body(source: str, method_name: str) -> tuple[str, str]:
    """Retorna (header, body) onde header é tudo até e incluindo o '{' de
    abertura, e body é o conteúdo estritamente entre as chaves (sem incluir
    o '}' final). `header + body + "}" + source[span.body_end+1:]`
    reconstrói o arquivo original.
    """
    span = find_method_span(source, method_name)
    header = source[: span.header_end]
    body = source[span.body_start : span.body_end]
    return header, body


def splice(canonical_header: str, body: str) -> str:
    """Recombina um header canônico (de tasks/<task>/contract.dfy) com um
    corpo extraído de uma submissão, reconstruindo um arquivo .dfy completo.
    Usado para a avaliação independente (Seção 9.2 do paper): sempre
    reavalia o CORPO da submissão contra o contrato fixo verdadeiro, nunca
    contra um header que o próprio agente possa ter alterado.
    """
    if not canonical_header.rstrip().endswith("{"):
        raise ValueError("canonical_header deve terminar em uma linha '{' isolada")
    return canonical_header + body + "\n}\n"
