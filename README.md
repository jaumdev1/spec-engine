# ADLC — contratos formais e verificação SMT no desenvolvimento por agentes

> Rótulo provisório deste projeto: **ADLC** (*Agent Development Life Cycle*). Isto **não** é um padrão estabelecido — a sigla colide com usos já correntes ("Application Development Life Cycle" e "Agentic Development Lifecycle" de mercado). Ver a nota de desambiguação completa em [`paper/paper.md`](paper/paper.md#12-nota-de-desambiguação-sobre-a-sigla-adlc).

## Proposta

Investigamos se, e sob quais condições, agentes de IA que implementam código a partir de contratos formais revisados por humanos — com feedback de um verificador dedutivo baseado em SMT — produzem código mais conforme do que agentes sem essa camada, e a que custo. O texto completo, incluindo fundamentação teórica, revisão de trabalhos relacionados e metodologia experimental, está em [`paper/paper.md`](paper/paper.md).

**Pergunta de pesquisa**: em quais condições a integração de contratos formais revisados e feedback de verificação dedutiva melhora a conformidade do código produzido por agentes, isolando o efeito do contrato do efeito do feedback do verificador — e qual é o custo dessa integração?

## Status (2026-10-07)

| Item | Status |
|---|---|
| Revisão de trabalhos relacionados | Feita (busca web, outubro/2026) — ver Seção 8 do paper. Algumas referências precisam de confirmação manual antes de submissão (ver `paper/references.bib`). |
| Escolha de ferramenta de verificação | Decidida: **Dafny** (justificativa na Seção 7.1 do paper). |
| Exemplo pedagógico | Implementado e testado localmente: `examples/dafny/withdrawal.dfy` verifica com Dafny 4.11.0 (`6 verified, 0 errors`). As duas variantes com bug proposital (comentadas no arquivo) foram testadas à parte e falham exatamente como descrito no paper — a de bananas por pós-condição não provada, a de centavos com `might violate newtype constraint for 'Cents'` (overflow como obrigação de prova). |
| CI de verificação | `.github/workflows/verify.yml` validado rodando de fato em GitHub Actions após o primeiro push a este repositório — [run `37634671818`](https://github.com/jaumdev1/spec-engine/actions/runs/37634671818), sucesso em 9s. Aviso não bloqueante do runner sobre migração futura do `ubuntu-latest` (out/2026) e depreciação do Node 20 nas actions — não afeta o resultado da verificação. |
| Orquestrador (grupos A/B/C) | **Implementado** (`scripts/orchestrator.py` e módulos auxiliares) e testado de ponta a ponta com o Dafny real + um backend simulado (sem chamadas de API) na Tarefa 01. Ver **`docs/orchestration.md`** para como funciona e como rodar, incluindo o mecanismo de defesa contra enfraquecimento de contrato (Seção 6) validado com três cenários reais. Nenhuma chamada a um modelo de verdade foi feita ainda. |
| Prompts de agente | Templates genéricos para os três grupos implementados em `prompts/` (ver `prompts/README.md`). Cobrem a Tarefa 01; tarefas 2–5 ainda não têm arnês de teste. |
| Execução experimental | **Não realizada.** Seções de resultados do paper são espaços reservados. O que existe são testes de validação do próprio harness (modo mock), não um experimento — ver `results/README.md`. |

Nenhum número, gráfico ou taxa de sucesso neste repositório é real até que a seção "Resultados" do paper deixe de ter a marcação `[RESULTADO FUTURO]`.

## Estrutura do repositório

```
paper/              paper em Markdown (paper.md) + bibliografia (references.bib)
examples/dafny/      exemplos e contratos verificáveis (material didático, Seção 4 do paper)
tasks/               material de cada tarefa experimental (requisito, contrato fixo, testes) — só a Tarefa 01 por ora
prompts/             templates de prompt dos grupos A/B/C
scripts/             orquestrador dos grupos A/B/C e módulos auxiliares (ver docs/orchestration.md)
docs/                documentação de como o orquestrador funciona e como rodá-lo
results/             esquema documentado para resultados futuros, sem dados fictícios
.github/workflows/   CI de verificação
```

## Como reproduzir o que já existe

Pré-requisito: [Dafny](https://github.com/dafny-lang/dafny) instalado localmente (versão fixada no CI — ver `.github/workflows/verify.yml` — para reprodutibilidade; não usar "latest" silenciosamente).

```bash
dafny verify examples/dafny/withdrawal.dfy
```

Deve reportar `Dafny program verifier finished with 6 verified, 0 errors` (testado nesta sessão com Dafny 4.11.0 em macOS arm64). Os métodos com bug proposital (Seção 4 do paper) estão comentados no arquivo — descomentar um deles reproduz o erro de verificação relatado no paper.

Para rodar o orquestrador dos grupos A/B/C num modo que não chama API nenhuma (respostas simuladas, só para ver o encanamento funcionando):

```bash
python3 scripts/orchestrator.py --task task-01-debit --group C \
  --backend mock --mock-responses scripts/examples/mock_responses_c.json \
  --dafny-bin /caminho/para/dafny --max-attempts 3
```

Detalhes completos — incluindo como rodar com um modelo real — em [`docs/orchestration.md`](docs/orchestration.md).

## Licença

Ainda não definida. Não assumir nenhuma licença implícita até que este arquivo seja atualizado.

## Como contribuir / continuar o trabalho

Este é um projeto de pesquisa em andamento, não um produto. Antes de adicionar qualquer resultado experimental, releia a Seção 6 do paper (regras de integridade do contrato) e a Seção 9 (metodologia) — a validade do experimento depende de registrar execuções com falha e resultados inconclusivos com o mesmo rigor que sucessos.
