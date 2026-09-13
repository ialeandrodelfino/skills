# Auditoria de custo e latência da deep-review

Análise de 12/09/2026. Escopo: logs reais do Codex, implementação deste repositório, cópia instalada no Compozy e artefatos de uma revisão concluída. Três subagentes exploraram logs, bootstrap e execução. A skill e suas alterações preexistentes foram preservadas.

O bootstrap desperdiça minutos e geração de código, mas responde por uma fração pequena do tempo total nos casos examinados. A maior oportunidade está em automatizar a contabilidade que os modelos escrevem, reduzir expansão de contexto e tornar execução/validação locais a cada job. A qualidade deve continuar sendo avaliada pelos achados e suas evidências.

**1. Existem duas versões relevantes, com melhorias diferentes**

| Comportamento em 12/09 | Fonte neste repositório | Instalação no Compozy |
| --- | --- | --- |
| Diretório | `skills/mine/deep-review` | `/Users/pedronauck/Dev/compozy/compozy/.agents/skills/deep-review` |
| Defect cohort | 100 arquivos / 6.000 linhas alteradas | 200 / 15.000 |
| Polish cohort | 20 arquivos / 1.200 linhas alteradas | 200 / 15.000 |
| Referências | Triagem por relevância e routing hints | Leitura integral de todas as fontes pending |
| Lint | Permite reutilizar evidência válida | Exige executar primeiro |

O aumento de escopo citado pelo usuário está na instalação do Compozy. As melhorias recentes de carregamento estão na fonte local, ainda não nessa instalação. A `.claude/skills/deep-review` do Compozy aponta para sua própria `.agents/skills/deep-review`, não para este repositório. Uma futura sincronização precisa conciliar os diretórios inteiros e preservar os limites ampliados.

Evidência: [constantes na fonte](../skills/mine/deep-review/scripts/build_jobs.py:42), [constantes instaladas](/Users/pedronauck/Dev/compozy/compozy/.agents/skills/deep-review/scripts/build_jobs.py:42) e [carregamento instalado](/Users/pedronauck/Dev/compozy/compozy/.agents/skills/deep-review/SKILL.md:74). As mudanças locais preexistentes em `SKILL.md`, `context-pack.md`, `build_knowledge.py` e testes foram consideradas na análise.

**2. Tempos observados nos logs**

Bootstrap = leitura efetiva da skill até primeiro dispatch de revisão. Total = mesma leitura até a saída de geração do relatório. Não é a duração de toda a conversa de implementação. Cada caso tem escopo diferente; esta tabela não constitui um benchmark comparativo entre versões.

| Caso | Data | Bootstrap | Até relatório | Chamadas de ferramenta do pai no bootstrap | Tokens de saída do pai no bootstrap |
| --- | --- | ---: | ---: | ---: | ---: |
| skill-sources | 25/08 | 5m48s | 1h15m32s | 25 | 12.884 |
| agent-comms | 25/08 | 6m47s | 3h05m12s | 27 | 16.729 |
| acp-runtime-catalog | 27/08 | 7m04s | 1h32m01s | 31 | 21.182 |
| integrated-terminal | 25/08 | 7m11s | 2h50m11s | 30 | 14.953 |
| integrated-terminal incremental | 01/09 | 10m18s | 6h02m15s | 51 | 26.016 |

O caso de 01/09 inclui alterações da skill e intervenções durante a execução; serve para investigar retomada e retrabalho, não como medida limpa da latência de revisão. Nos quatro outros casos, eliminar todo o bootstrap pouparia aproximadamente 4%–8% do tempo observado. Sua lentidão é real, mas corrigi-la isoladamente não resolve a duração total.

Pontos auditáveis nos JSONL, com timestamps UTC:

- [ACP, leitura da skill](/Users/pedronauck/.codex/sessions/2026/08/27/rollout-2026-08-27T14-18-25-01a0443a-e302-7572-b731-7f04a2274d2b.jsonl:8615): 20:59:50.032; primeiro dispatch linha 8850, 21:06:53.732; relatório linha 9406, 22:31:50.843.
- [Skill-sources, leitura](/Users/pedronauck/.codex/sessions/2026/08/25/rollout-2026-08-25T00-09-09-01a036e4-a533-7263-a0a5-6e6fd2b6b349.jsonl:17230): 13:17:39.378; dispatch 17396, 13:23:27.872; relatório 18262, 14:33:11.832.
- [Agent-comms, leitura](/Users/pedronauck/.codex/sessions/2026/08/25/rollout-2026-08-25T00-09-22-01a036e4-d805-7013-9787-862fdbdf6028.jsonl:24339): 20:50:07.732; dispatch 24514, 20:56:54.818; relatório 25753, 23:55:19.579.
- [Terminal, leitura](/Users/pedronauck/.codex/sessions/2026/08/25/rollout-2026-08-25T00-07-54-01a036e3-810c-7251-a96d-ad890d398b3e.jsonl:30183): 23:42:27.450; dispatch 30409; relatório 31365, em 26/08 às 02:32:38.926.
- [Terminal incremental, leitura](/Users/pedronauck/.codex/sessions/2026/09/01/rollout-2026-09-01T13-51-42-01a05de2-3cc0-7f70-8a1f-81fd0f1ef0ad.jsonl:24): 16:54:10.677; dispatch 346; relatório após ajustes 2493, 22:56:25.425. Há fan-out e render no log real.

**3. O consumo maior está nos reviewers Luna Max**

Os orquestradores dos casos selecionados registram Sol High/XHigh; os filhos de revisão registram `gpt-5.6-luna`, effort `max`. A atribuição abaixo separa filhos do pai e entrada em cache de entrada sem cache.

| Caso | Filhos registrados | Chamadas ao modelo nos filhos | Entrada sem cache | Entrada em cache | Saída, incluindo raciocínio |
| --- | ---: | ---: | ---: | ---: | ---: |
| ACP | 9 | 4.225 | 20.898.592 | 543.237.888 | 1.596.439 |
| Skill-sources | 36 | 3.710 | 16.502.885 | 460.490.240 | 1.567.805 |
| Agent-comms | 6 | 7.006 | 33.092.201 | 906.262.016 | 2.818.179 |

Contadores medem processamento acumulado das chamadas, não palavras únicas do código, nem uma fatura. Entrada inclui reapresentação de contexto entre chamadas. Raciocínio é subconjunto de saída e não foi somado novamente. No ACP, 853.244 dos tokens de saída eram raciocínio; no agent-comms, 1.485.227.

Os filhos examinados foram iniciados com `fork_turns=none`. Portanto herança integral da conversa não explica esses runs. O contexto base de instruções permanece: uma primeira chamada de reviewer tinha aproximadamente 25,6 mil tokens de entrada, dos quais 25,3 mil em cache. A reutilização do mesmo worker para novos jobs acumula depois o histórico desses jobs.

Método: deltas de `total_token_usage` entre fronteiras da fase para o pai; sessões filhas vinculadas por `parent_thread_id`, limitadas ao intervalo de revisão. Nos 63 filhos dos cinco casos, o primeiro total menos o primeiro `last_token_usage` foi zero; os incrementos subsequentes bateram com `last_token_usage` após excluir eventos repetidos. Portanto os totais dos filhos não carregam contabilidade herdada do pai. A décima tentativa de spawn no ACP falhou por limite de threads (linha 8896), explicando os nove filhos existentes.

Exemplos de trabalho estrutural efetivamente observado:

- ACP: o pai gerou `prepare_review.py` em uma chamada de patch de aproximadamente 27,5 mil caracteres antes de disparar a revisão (linha 8824).
- Agent-comms: gerou `prepare_rules.py` e `prepare_plan.py` com chamadas de aproximadamente 12 KB e 8 KB (linhas 24439 e 24465). O gate acusou `duplicate source accounting` na linha 24479; o agente corrigiu a preparação na linha 24483.
- Agent-comms: 61 jobs, sendo 11 defect, 48 polish e 2 sweeps; seis workers foram reutilizados. Seus logs contêm 6.944 chamadas de ferramenta, 71 execuções de `run_jobs.py --validate-only`, 29 leituras/consultas de ajuda do validador e 94 consultas a `jobs.json`.
- Um [patch de resultado do reviewer](/Users/pedronauck/.codex/sessions/2026/08/25/rollout-2026-08-25T17-57-13-01a03ab6-7e45-7870-9b21-630d0776a2c9.jsonl:1746) chegou a cerca de 38 KB de JSON manual.
- Skill-sources terminou 36/36 jobs; reparos de ownership/certificado entre linhas 18193 e 18243 acrescentaram 3m03s. Terminal de 25/08 terminou 78/78; um certificado de sweep acrescentou 2m37s entre linhas 31337 e 31353.

Um [trecho do reviewer dr_c03](/Users/pedronauck/.codex/sessions/2026/08/25/rollout-2026-08-25T17-57-04-01a03ab6-5945-7831-b710-588400947125.jsonl:1246), entre 21:26:22 e 21:31:25, mostra tentativas de extrair coverage do prompt com regex, falha ao fazer parse de `defect` como JSON, reconstrução do coverage e patch de 151 checks faltantes. Depois o validador global falha por jobs de outros workers ainda pendentes, motivando nova execução. Há investigação de código intercalada; os cinco minutos não foram classificados integralmente como burocracia. Na linha 1451, o worker inicia outro job carregando novamente prompt, contexto, skill e taxonomy.

Esses exemplos comprovam custo estrutural, mas não autorizam classificar todas as milhares de chamadas como desperdício: parte é investigação substantiva. O resultado agent-comms registrou 72 defects e 298 advisories; sua validade individual não foi reavaliada nesta auditoria.

**4. O helper é rápido; a fila que ele entrega ao modelo é excessiva**

Executei o `build_knowledge.py` corrente duas vezes sobre uma cópia do manifest histórico ACP, com cwd no Compozy atual e saídas em diretório temporário. Tempos: 6,895 e 6,827 segundos; ambos exit 0. O código examinado e o inventário atual não são os mesmos do run histórico, portanto isso mede o helper atual sobre aquela seleção de paths.

| Resultado corrente | Quantidade |
| --- | ---: |
| Arquivos selecionados | 337 |
| Registros de fontes / caminhos únicos | 813 / 749 |
| Fontes pending | 433 |
| Skills candidatas | 90 de 95 |
| Referências candidatas | 333 de 335 |
| Aliases duplicados no registry | 64 |
| Entradas repetidas nas listas `applies_to` | 122.082 |
| Tamanho de `knowledge.json` | 7.319.471 bytes |

A seleção usa qualquer palavra compartilhada entre metadata e sinais globais do repositório, inclusive locks. Entraram `grill-me` por `get, until`, `git-rebase` por `resolve`, `demo-video` por `browser`, `favicon-gen` por `icons, site` e `x-pedro-voice` por `conventions, generic, table, which`. Os matches de metadata recebem todos os 337 paths. Referências são expandidas antes da decisão semântica sobre o parent.

Além disso, a discovery percorre instruções em toda a árvore: das 381 entradas de instrução, somente oito eram candidatas, correspondentes a quatro arquivos canônicos. `AGENTS.md` e seu destino `CLAUDE.md` aparecem duplicados porque a normalização resolve symlinks. O template os mantém, mas o gate rejeita source duplicado. Isso reproduz estruturalmente o reparo observado no log agent-comms.

Os objetos de fontes serializados de forma compacta ocupam 6.102.661 bytes. Removendo apenas as listas `applies_to`, caem para 357.837 bytes: 94,1% desse payload é repetição dessas listas. Um formato normalizado pode referenciar conjuntos de paths e preservar os vínculos. Essa proporção é de bytes, não uma economia medida de tokens.

Evidência de implementação: [varredura](../skills/mine/deep-review/scripts/build_knowledge.py:53), [sinais globais e menções](../skills/mine/deep-review/scripts/build_knowledge.py:139), [seleção e expansão](../skills/mine/deep-review/scripts/build_knowledge.py:227), [rejeição de duplicatas](../skills/mine/deep-review/scripts/build_jobs.py:147). [Snapshot da medição](/var/folders/7x/xg204hnd04b81fczcxvjlhzr0000gn/T/deep-review-bootstrap-audit-6jz1ahaa/audit-metrics.json).

**5. Os modelos reescrevem metadados que o pipeline já conhece**

Antes do primeiro reviewer, o [Step 2](../skills/mine/deep-review/SKILL.md:71) exige rules, context-pack, plan e walkthrough. O plano repete paths e calcula slices a partir de informações já presentes no manifest. Há particionamento determinístico para polish que pode ser reutilizado. Walkthrough não é entrada do `build_jobs.py`: pode sair do caminho crítico e ser concluído durante o fan-out ou na montagem do relatório.

Na revisão ACP preservada em disco:

- 337 arquivos, 1.363 hunks e 13.230 linhas de hunk selecionadas;
- 6 jobs defect, 21 polish, 2 sweeps;
- 37 regras, com 421 atribuições de regra aos jobs;
- 589.762 bytes de prompts e 1.020.124 bytes de outputs JSON;
- 2.726 linhas de accounting de hunks, uma por hunk em cada lane;
- merge registrou 23 defects e 114 advisories canônicos, com cobertura completa das duas lanes. Esses números são resultados do pipeline, não validação independente dos achados.

O prompt repete hunks em FILES e HUNK COVERAGE, além do scope nas slices. O reviewer repete `file`, `hunk` e `checks` no output. A cobertura linha a linha já é calculada pelo Python a partir dos ranges; o LLM não precisa serializar novamente esses metadados.

Experimento de representação, sem alterar a skill: manter cada outcome explícito, substituir identidade do hunk por ID numérico por job e preservar status/notas de todas as regras reduziu o JSON compacto de coverage de **387.513 para 102.799 caracteres, 73,5%**. O experimento exclui o mapa ID→path, que precisa estar no pacote de entrada. Não é uma medição de tokens nem de latência, mas identifica uma redução concreta no transporte de saída sem remover avaliações.

Evidência: [artefatos ACP](/Users/pedronauck/Dev/compozy/compozy/.deep-review/acp-runtime-catalog/review-stats.json), [duplicação do contrato](../skills/mine/deep-review/scripts/build_jobs.py:320) e [expansão da cobertura](../skills/mine/deep-review/scripts/merge_findings.py:218).

**6. Ordem recomendada de implementação**

1. **Conciliar a fonte e a instalação.** Incorporar os limites amplos já escolhidos pelo usuário e o carregamento seletivo no mesmo pacote. Registrar versão/hash e limites efetivos nos artefatos. Não sobrescrever a instalação com os limites antigos da fonte.
2. **Compilar o bootstrap.** Corrigir aliases; descobrir instruções por ancestrais dos paths selecionados; apresentar uma fila compacta de routers; expandir referências após a decisão de aplicabilidade. O modelo fornece decisões, spans de regras lidos, intenção e exceções semânticas. Helpers produzem registry, contexto e plano padrão, reutilizando o particionamento existente. Parent excluído pode contabilizar suas referências dependentes; referências compartilhadas exigem considerar todos os parents. Walkthrough sai do caminho crítico.
3. **Compilar o output do reviewer.** IDs estáveis para hunks e regras, avaliações explícitas compactas e expansão por script para o schema canônico existente. Findings continuam com evidência causal, localização e citações. Ausência de avaliação continua sendo erro; nunca completar `clear` ou `compliant` automaticamente.
4. **Validar e reparar por job.** Oferecer um comando local que valida somente o output atribuído e devolve todos os erros acionáveis. Workers não consultam repetidamente o status global. O orquestrador mantém o gate completo, o freeze e a prova de cobertura na barreira final. Erro de formato retorna ao mesmo resultado para reparo, preservando investigação válida.
5. **Reduzir duplicação entre jobs.** Pacote de contexto por job; regras vinculadas por lane/lente; sweeps apenas quando há uma hipótese transversal não coberta por um dono local. O sweep `tests` hoje tem trigger para qualquer mudança de comportamento, apesar de defects já revisar testes. Manter `spec-parity` quando solicitado. Avaliar vida útil dos workers reutilizados e tamanho de contexto, sem presumir que um worker novo por job será sempre mais econômico.
6. **Calibrar slices e effort com comparação real.** Preservar o escopo amplo aprovado; usar tamanho total dos arquivos/contexto e risco, além de changed lines, para evitar slices que repetem a leitura integral de um arquivo enorme. Testar mudanças de effort somente depois de remover trabalho mecânico, com os mesmos casos e critérios de qualidade.

Há também um problema específico do runtime externo: [run_jobs.py](../skills/mine/deep-review/scripts/run_jobs.py:67) apaga output inválido antes de repetir o mesmo prompt, não injeta o erro no retry e pode repetir após timeout sem validar o arquivo que já foi produzido. Defaults permitem duas tentativas de até 35 minutos. Preservar tentativas e separar reparo de contrato de nova investigação corrige esse caminho. Esse comportamento de retry externo não foi usado para explicar automaticamente os logs Luna/native.

O artigo recomenda routers enxutos, carregamento contextual e reavaliar receitas excessivas, e ressalva diferenças entre modelos. As mudanças recentes já seguem essa direção. Aqui, o próximo ganho exige que o software assuma a montagem e validação mecânica hoje delegadas ao modelo. [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).

Os casos completos de agosto antecedem as últimas mudanças de setembro. Não foi identificado, no recorte recente examinado, um run concluído que combinasse os limites ampliados e o carregamento seletivo atual. Não é possível atribuir a essas mudanças uma melhora ou ausência de melhora com a amostra disponível.

**7. Como comprovar melhora sem perder resultado**

A suíte canônica é [tests/deep_review/test_pipeline.py](../tests/deep_review/test_pipeline.py). Ao implementar, ampliar esse arquivo para invariantes das camadas existentes: identidade/escopo das fontes, referências compartilhadas, propriedade exata de hunks, expansão dos IDs, rejeição de avaliações ausentes, preservação de resultados válidos em reparo e pipeline real até HTML. A suite já exercita CLIs com repositório temporário; outputs artificiais não comprovam qualidade de revisão.

Comparação comportamental: escolher casos históricos pequeno, médio e grande; congelar os mesmos commits, instruções e achados adjudicados; executar baseline e versão proposta com Luna Max e o mesmo limite de concorrência. Medir tempo até primeiro reviewer, tempo até relatório, chamadas por job, leituras repetidas, saídas rejeitadas, retries e tokens separados em entrada sem cache, entrada em cache, saída e raciocínio. Avaliar recuperação dos defeitos conhecidos, validade dos novos achados e utilidade dos advisories, além da cobertura formal. Resultados anteriores do pipeline precisam de adjudicação antes de servirem como verdade de referência.

Critérios estruturais verificáveis: nenhum script Python de preparação inventado durante um run normal; nenhuma duplicata produzida pelo discovery; nenhuma serialização manual de paths/ranges conhecida pelo manifest; validação global sob responsabilidade do orquestrador; nenhuma perda de cobertura, precedência, congelamento da fonte, evidência causal ou controle de publicação. Ganhos percentuais de custo/latência só podem ser afirmados após essa comparação.

Esta auditoria fez leitura dos logs e do código, comparação das instalações, duas execuções reais do helper de knowledge e um experimento local de serialização. Não executou um novo review pago nem alterou a implementação. Os cálculos dos logs e suas fronteiras foram preservados em [/tmp/deep-review-audit-logs/metrics.json](/tmp/deep-review-audit-logs/metrics.json) e [measure.py](/tmp/deep-review-audit-logs/measure.py); arquivos temporários não são armazenamento permanente.
