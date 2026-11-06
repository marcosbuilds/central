# 14 — Entregas aprovadas, commits, versionamento e diálogo entre IAs

**Status:** especificação proposta; não está implementada. **Objetivo:** permitir um código vivo compartilhado sem confundir edição, versão oficial e publicação; permitir que IA e pessoas discutam integrações de modo rastreável.

## 1. Linguagem da Central: quatro coisas diferentes

| Nome simples na tela | Registro técnico | Exige revisão humana? | Entra na master? | Faz deploy? |
|---|---|---|---|---|
| Edição em andamento | Mudança local não sincronizada | Não | Não | Não |
| Alteração ao vivo | `change_set`, revisão sequencial, snapshot recuperável | Em geral não; exige checagem automática | Não | Não |
| Entrega para aprovação | Conjunto de revisões + diff + checks + parecer | Conforme risco e política | Só após aprovação | Não automaticamente |
| Publicação | Release, ambiente, artefato e rollback | Conforme ambiente | Usa versão já aprovada | Sim, após autorização |

**Nota de precisão:** o Git define *commit* como registro de alterações, e não como uma mudança necessariamente grande. A experiência da Central chama o pacote que pede aprovação de **entrega**; sua implementação pode usar commits técnicos periódicos, hash de snapshots e um commit consolidado de integração, sem exigir que cada microedição produza PR e deploy. Alterações pequenas de alto risco continuam exigindo aprovação.

## 2. Modelo de versionamento

- `workspace_revision`: incrementa a cada conjunto de patches confirmado no workspace vivo; todos veem a mesma sequência lógica.
- `change_set`: autor, agente, tarefa, arquivos e símbolos, revisão-base, patch, hash, data, verificações, motivo, reversões; mudanças podem ser agrupadas.
- `snapshot`: estado recuperável em ponto conhecido; gravação automática por lote/intervalo e antes de entregas importantes.
- `delivery_candidate`: conjunto imutável de `change_set`s selecionados para integrar; um ID, hash, versão-base da master, dependências e resumo de risco.
- `master`: histórico estável Git protegido; apenas o serviço de integração aprovado publica uma entrega validada na branch protegida (via mecanismo de PR/merge ou equivalentemente sujeito às regras do provedor).
- `release`: versão nomeada/tag após entrega aprovada; não implica deploy.
- `deployment`: ligação entre release/commit, ambiente, solicitante, aprovação, testes, logs e rollback.

Recomendação: usar versão semântica para os produtos que precisarem (por exemplo `1.2.0`), e números de revisão do workspace para coordenação cotidiana (`r145`). Não aumentar a versão do produto por cada patch.

## 3. Política de risco (não apenas tamanho)

| Risco | Exemplo | Aprovação sugerida |
|---|---|---|
| Baixo | Texto da interface, formatação sem efeito em comportamento | IA revisora **independente** com evidências pode ser suficiente, se o projeto autorizar |
| Médio | Nova rota, ajuste de banco compatível, comportamento de validação | IA especializada independente + verificações obrigatórias; revisão humana opcional/conforme política |
| Alto | Autenticação, autorização, pagamentos, exclusão de dados, migrations destrutivas, configuração de produção | Pelo menos uma pessoa autorizada, com parecer técnico e testes; IA auxilia, não decide sozinha |

**Condição universal:** sem permissão explícita, uma IA só dá **parecer**, não aprovação executável. Nunca se autoaprova. Se a política Git exigir revisão de humano, um parecer da IA não satisfaz essa revisão automaticamente. A aprovação pertence ao hash exato revisado; se muda o diff, reavaliar.

## 4. Prova exigida antes de aprovar

Cada entrega gera um **dossiê de evidências**:

1. **Mudança exata:** referência da revisão, hash, diff, autoria humana e agente, tarefa/requisito.
2. **Por que mudar:** problema, resultado esperado, impacto nas dependências e no usuário.
3. **Checagens executadas:** comandos, ambiente, versões, status, logs sem segredos, cobertura relevante, comparação com cenário anterior.
4. **Contratos:** APIs/rotas/eventos/esquemas tocados, consumidores notificados, testes de contrato.
5. **Segurança e recuperação:** risco, análise de permissões e de dados, plano de reversão, backup/migration se aplicável.
6. **Revisão independente:** autor/revisor distintos, comentários respondidos, motivo da decisão, timestamp e ID do job de testes.

Os testes são executados pela infraestrutura isolada de CI, não apenas declarados no texto da IA. Uma IA pode apontar dúvidas, reproduzir defeitos, abrir pedido de correção e marcar `inconclusivo`. Um revisor não pode simplesmente escrever 'aprovado' sem associar a evidência. Logs e artefatos precisam ser verificáveis.

### Máquina de estados de entrega

`RASCUNHO → PREPARADA → TESTANDO → EM_REVISAO → [ALTERACOES_SOLICITADAS | REPROVADA | APROVADA] → INTEGRANDO → INTEGRADA`.

- Alterações solicitadas: autor corrige, atualiza hash, reinicia verificações e revisão quando necessário.
- Reprovada: não integra master, mas mantém histórico auditável e rollback na área viva. Se outros change sets dependem do reprovado, abrir incidente de reconciliação.
- Integrando: serviço verifica estado do projeto, permissão, hash e base master de novo; detecta regressão e incompatibilidades; só então publica na branch protegida.
- `APROVADA` não significa que GitHub ou produção já aceitaram a alteração. Se a regra externa negar merge, marcar `BLOQUEADA` e registrar o motivo.

## 5. Conversa entre agentes dentro do projeto

**Locais:** canal do projeto, thread por tarefa, discussão por arquivo/linha, pedido de integração por API, comentário de revisão, anúncio de mudança de contrato. Cada mensagem pertence a um projeto e pode citar recurso lógico, revisão, contrato e tarefa.

**Mensagem mínima:** `message_id, project_id, thread_id, sender_type, member_id, agent_session_id, type, resource_refs, body, created_at, mentions, visibility, reply_to`. A identidade mostrada é `Codex de [integrante]`, `Claude de [integrante]` etc., nunca 'uma IA desconhecida'.

Tipos: `question`, `integration_request`, `contract_proposal`, `contract_ack`, `contract_ready`, `blocker`, `decision`, `review_comment`, `evidence`, `notification`. Threads podem ser resolvidas, reabertas, pesquisadas e auditadas.

**Coordenação:** uma sessão ativa recebe menção e responde por adaptador autorizado; uma sessão inativa recebe notificação/pedido pendente, sem inventar resposta nem iniciar gasto de modelo sem a política e autorização do dono. Recomendado orçamento e limite de mensagens por integração para impedir ciclos infinitos entre IAs.

## 6. Exemplo completo — frontend pede API ao backend

1. Codex do frontend reserva `ui.registration` e vê no planejamento dependência de `api.registration`.
2. Publica a pergunta: 'Qual rota, autenticação, payload, resposta, erros e prazo esperado?'. Central cria `integration_request IR-24` ligado às tarefas T-17 e T-18.
3. Claude do backend, responsável por `api.registration`, responde com **proposta de contrato** (não promete código pronto):

```yaml
id: api.registration.v1
status: proposed
method: POST
path: /api/register
request:
  content_type: application/json
  body: { name: string, email: string, password: string }
responses:
  201: { user_id: string, status: pending_verification }
  400: { code: validation_error }
  409: { code: email_already_registered }
owner: task:T-18
consumer: task:T-17
```

4. O Codex responde `contract_ack` (aceita ou pergunta); a Central muda contrato para `acordado`, registra versão e avisa ambos.
5. Frontend pode preparar a interface usando mock **marcado como simulação**; não confunde API proposta com API disponível.
6. Backend implementa e publica evidências de teste de contrato. Estado: `implementado` e depois `testado`.
7. Central avisa o frontend: a rota está testada na revisão `r123`; o Codex sincroniza e executa integração real em ambiente de teste.
8. Se o backend alterar um campo, cria `contract_change` antes de aplicar mudança incompatível; dependentes ficam alertados e integração é testada novamente.
9. Todos os envolvidos podem comentar e consultar a decisão meses depois, sem perder contexto em chat privado.

## 7. Regras de dependência e conflitos

- Recurso lógico tem dono temporário e consumidores (`api.registration` provê, `ui.registration` consome). Dois agentes podem desenvolver em paralelo suas partes; modificação incompatível do contrato exige coordenação.
- Mensagem *não concede* reserva nem autorização. A central confere reivindicações e permissões por API.
- Regras por arquivo **e por lógica**; nomes de arquivos diferentes não garantem independência. Em dúvida, reservar módulo maior e bloquear alteração perigosa.
- O gateway revalida `project.state`, revisão e hashes ao confirmar o patch. Nenhuma conversa pode autorizar bypass.
- Projetos `FECHADO` permitem discussão/leitura se a política autorizar; escrita, merge, release e deploy ficam bloqueados até reabertura.

## 8. Onde aparece na interface

Tela do projeto: `Visão geral | Planejamento | Workspace vivo | Discussões | Integrações/API | Entregas | Histórico | Publicações | Segurança`.

No Workspace, clicar em um arquivo mostra mudanças de cada agente, contratos relacionados, revisões e thread. Em 'Integrações' existem pedidos pendentes, contratos acordados, consumidores e verificações. Em 'Entregas', dossiês, diff comparado com master, checks, quem aprovou e por quê. No histórico, recuperar a revisão sem contaminar a master.

## 9. Riscos e salvaguardas

- **Bate-boca/ciclo de IA:** limitar turnos, desestimular ping-pong, permitir cancelar/escalar ao humano.
- **Alucinação de rota/resultado:** contratos somente mudam para `testado` com check de CI; distinguir proposta de implementação.
- **Autoaprovação disfarçada:** correlacionar agente→integrante→autor e obrigar outro responsável para revisão executável.
- **Mudança silenciosa da API:** changelog e assinatura dos consumidores, testes de compatibilidade.
- **Patch seguido de fechamento:** fencing token e conferência atômica no gateway para não aceitar escrita após fechamento.
- **Aprovação obsoleta:** aprovação amarrada ao hash exato e commit-base; revalidar na integração.
- **Merge de entrega em trabalho vivo que mudou:** calcular candidato imutável; conciliar dependências e revisões até ficar consistente antes de aprovar/publicar.
- **Dados confidenciais em conversas e streaming:** autorização por projeto, retenção configurável e redação de segredos; jamais armazenar raciocínio privado de modelos como requisito.

## 10. Testes de aceite específicos

- Duas IAs solicitam e confirmam contrato; outra pessoa acompanha a thread em tempo real.
- Sessão backend offline: pedido persiste e é respondido ao reconectar; não fabricar resposta.
- Mudança de contrato invalida integração afetada e dispara check obrigatório.
- 100 edições pequenas geram revisões reversíveis **sem** 100 deploys/PRs.
- Entrega de risco baixo com IA revisora independente, provas válidas e política delegada pode seguir para master; sem delegação, não.
- IA autora tenta aprovar com outro token da mesma pessoa: bloquear quando política exige independência.
- Alteração de autenticação com parecer favorável da IA continua bloqueada até revisão humana.
- Aprovação referente a hash anterior não serve após patch novo.
- Projeto fechado entre a revisão e o merge impede integração e deploy.
- Checks externos GitHub rejeitam merge: Central não exibe sucesso falso.

## Referências técnicas

- Git: https://git-scm.com/docs/git-commit (commit registra estado; não requer alteração grande).
- GitHub protected branches: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches (revisores, verificações, travamento e merge queue).
- Codex App Server: https://learn.chatgpt.com/docs/app-server (eventos, aprovações e integração de aplicação).
- Claude Agent SDK: https://platform.claude.com/docs/en/managed-agents/migration (agentes, sessões, ferramentas e permissões).

*Todos os números de revisão, tarefas, projetos e APIs deste capítulo são exemplos propostos, não implementações existentes.*
