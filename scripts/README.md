# Scripts de execução e avaliação

Vazio por enquanto. Este diretório deve conter, quando implementado:

- O orquestrador que executa uma tarefa em um dos grupos A/B/C (Seção 9 do paper), controlando orçamento de tentativas/tempo/tokens e registrando toda execução — incluindo falhas — em `results/`.
- O parser de diagnóstico do verificador Dafny (saída `--diagnosticsFormat json`) usado para alimentar o agente no grupo C.
- O script de avaliação independente (testes adicionais não vistos pelo agente + checagem de alinhamento ao requisito), que roda separadamente do critério "passou no verificador" (Seção 9.2 do paper).
- O detector/registrador de violações de integridade do contrato (Seção 6 do paper): enfraquecimento de pós-condição, fortalecimento indevido de pré-condição, uso de `assume`/`{:trusted}`, etc.

Nenhum script aqui deve reportar sucesso com base apenas em "o verificador não retornou erro" sem também checar explicitamente se a obrigação não ficou em UNKNOWN/timeout — essa distinção é central para a metodologia (Seção 3.8 e 9.4 do paper).
