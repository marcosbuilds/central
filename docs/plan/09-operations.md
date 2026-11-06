# 10 — Fluxos de trabalho, revisões, testes, publicações e produtividade

## Estados de uma tarefa

`rascunho` → `aprovada-para-executar` → `disponível` → `reservada` → `em-execução` → `aguardando-revisão` → `solicitadas-correções` (volta a execução) / `validada` → `entregue`. Estados auxiliares: `bloqueada`, `cancelada`. Mudanças de estado têm autor e justificativa.

## Estados de um change set

**Pequenos change sets:** `proposto` → `validado-automaticamente` → `aplicado-no-workspace-vivo` → `revisionado/snapshot` (sem aprovar master nem fazer deploy).

**Entrega para master:** `candidato-imutável` → `CI` → `em-revisão` → `correções-pendentes` / `reprovado` / `aprovado` → `integrado-na-master` → `elegível-para-release` (deploy exige autorização separada).

Rejeitado exige reversão/neutralização documentada no workspace vivo ou decisão de substituição; não pode ficar afetando silenciosamente a versão estável. Aprovações são vinculadas a hash exato: alterou diff, reavaliar.

## Regras de revisão

- O autor nunca é único aprovador de sua própria mudança.
- Mudança em área sensível (autorização, pagamento, dados, infraestrutura, deploy, exclusão de dados) tem dois olhares ou política especial.
- Review considera: requisito e aceite; diff; impactos; segurança; testes; legibilidade; tratamento de erros; desempenho quando necessário; documentação.
- Comentário tem estado aberto/resolvido e linha ou recurso lógico. Decisão precisa de justificativa nas rejeições.
- QA automatiza testes rotineiros; revisão humana foca risco e coerência.

## Testes mínimos por tipo

- Backend: regras, erro de entrada, autorização, concorrência, banco e integração.
- Frontend/mobile: fluxos, acessibilidade, estados vazios, erros de rede e dispositivos suportados.
- Contratos: API, eventos e compatibilidade com clientes.
- Infra: publicação reprodutível, rollback, backup e segredos.
- Motor da central: claims, revisões, patches, eventos, idempotência, agentes malcomportados e isolamento por projeto.

## Política de deploy

1. Escolher revisão candidata, congelar snapshot e listar change sets.
2. Exigir aprovações e testes válidos na **mesma revisão**; impedir aprovação antiga para diff alterado.
3. Gerar artefato identificável, de preferência com hash e evidências de build.
4. Fazer preview/staging; testar o funcionamento conforme risco.
5. Responsável autorizado aprova produção, com confirmação adicional nos sistemas sensíveis.
6. Publicar artefato imutável; monitorar falhas; ter comando de rollback pronto.
7. Registrar data, executor, versão, changelog, links e incidentes.

A expressão “subir deploy com streaming” na interface deve significar **acompanhar ao vivo** etapas, logs filtrados, testes e resultado. Nunca confundir acompanhar build com autorização para promover código não revisado.

## Métricas de trabalho e empenho

Medir equipe e projetos primeiro. Exemplos:

- **Entrega:** tarefas aceitas conforme critérios, previsibilidade da etapa, valor demonstrado ao cliente.
- **Qualidade:** falhas em produção, retrabalho por erro, testes cobertos por risco, revisões concluídas.
- **Fluxo:** tempo bloqueado, espera por revisão, tempo para restaurar um incidente.
- **Colaboração:** dependências resolvidas, documentação útil, revisões que previnem problemas.
- **Custo:** uso de ferramentas/infra por projeto, quando mensurável e com consentimento.

**Não usar:** linhas de código, número bruto de commits, tokens usados, horas conectado, frequência de teclas, número de mensagens, “pontuação de produtividade” punitiva e opaca. Um membro pode evitar um prejuízo importante com poucas linhas ou com uma boa entrevista.

## Comentários e planejamento

Uma decisão importante no comentário deve ser promovida a `decision` no projeto; discussões soltas não substituem requisitos. Menções avisam apenas membros autorizados do mesmo projeto. Cliente pode aprovar entrega funcional sem precisar entender internamente cada linha de código.

## Reuniões mínimas

- Definição de escopo com documento claro.
- Alinhamento de dependências quando muda contrato compartilhado.
- Revisão curta de entrega e demonstração para cliente/usuários.
- Retrospectiva de falhas sem caça às bruxas; corrigir processo.
