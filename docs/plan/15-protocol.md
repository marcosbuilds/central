# 15 — Protocolo técnico: mudanças, conversas, contratos e revisão

**Estado:** contratos conceituais para futura implementação. O objetivo não é prometer uma API funcionando; os caminhos e exemplos são uma proposta de engenharia a validar.

## A. Modelo de recursos

- `projects`: id, slug, aliases, owner, state `OPEN|CLOSING|CLOSED`, `fencing_epoch`, repositories, workspace_revision.
- `memberships`: membro, projeto, papéis/escopos, validade.
- `agent_sessions`: agente, dono humano, provider, connection_id, active_project_id, permissions, last_seen, adapter_version.
- `tasks`: owner, descrição, critérios, prioridade, dependências, recursos lógicos, estado.
- `resource_claims`: projeto, lógica/arquivo, tarefa, sessão, exclusividade, epoch, expiração, heartbeat.
- `change_sets`: revisão, base_revision, hash, patch, claimed_resources, resultado, CI, writer, time.
- `snapshots`: workspace_revision, manifest, checksums, armazenamento recuperável.
- `threads`: projeto, contexto, recurso associado, visibilidade, estado, participantes.
- `messages`: thread, autor, membro patrocinador, agente, tipo, payload, timestamp, anexos restritos.
- `integration_requests`: consumer, provider, task_ids, status, contract_id, prazo desejado, bloqueio.
- `api_contracts`: id, versão, fonte OpenAPI/JSON Schema, owner, consumers, agreed_hash, status, checks.
- `delivery_candidates`: base_master, selected_change_sets, hash exato, diff, risco, status, responsável.
- `evidence_runs`: CI job, runner, commands, env, artifact hashes, logs filtrados, status.
- `reviews`: reviewer member/agent, delegated scope, candidate hash, decision, reason, evidence_ids, signed event.
- `releases`, `deployments`, `audit_events`: versões aprovadas, implantação e trilha não regravável.

Banco relacional com integridade referencial (ex.: PostgreSQL), objetos imutáveis para snapshots/diffs e fila de eventos para distribuir alterações. Não armazenar tokens em texto puro.

## B. Comandos e autenticação (pseudorrotas)

```text
GET    /v1/projects                         # somente autorizados
POST   /v1/agents/sessions                   # vincular provedor e membro
POST   /v1/agents/sessions/{id}/select       # escolher projeto por id, após busca
GET    /v1/projects/{id}/manifest             # requisitos, contratos, revisão
POST   /v1/projects/{id}/claims               # reservar recurso lógico
POST   /v1/projects/{id}/patches/propose      # submeter diff, base + hashes
POST   /v1/projects/{id}/patches/{id}/apply   # gateway valida e confirma
GET    /v1/projects/{id}/threads
POST   /v1/projects/{id}/threads
POST   /v1/projects/{id}/threads/{id}/messages
POST   /v1/projects/{id}/integrations/requests
POST   /v1/projects/{id}/contracts/{id}/versions
POST   /v1/projects/{id}/deliveries
POST   /v1/projects/{id}/deliveries/{id}/evidence
POST   /v1/projects/{id}/deliveries/{id}/reviews
POST   /v1/projects/{id}/deliveries/{id}/integrate
POST   /v1/projects/{id}/close                 # cargo próprio
POST   /v1/projects/{id}/reopen                # cargo próprio
GET    /v1/projects/{id}/events                # WebSocket/SSE autorizado
```

**Regras transacionais:** cada comando de escrita confere projeto aberto, membership, escopo, epoch, recurso, hash e base_revision; respostas incluem event_id/idempotency_key. A confirmação do patch e aumento da revisão precisam ser atômicos. Eventos são *at-least-once* com sequências; clientes deduplicam. Operações repetidas com mesma chave não criam alterações duplicadas.

## C. Envelope de evento

```json
{
  "event_id": "evt_000123",
  "project_id": "seloryn",
  "project_seq": 203,
  "type": "integration.requested",
  "actor": {"member_id": "member_A", "agent_session_id": "session_codex_A"},
  "refs": {"task_id": "T-17", "contract_id": "api.registration.v1", "thread_id": "thread_45"},
  "payload": {"summary": "Frontend solicita contrato de cadastro"},
  "visibility": "project_members",
  "occurred_at": "2026-11-03T12:00:00Z"
}
```

Transições importantes: `workspace.patch_applied`, `task.blocked`, `agent.mentioned`, `integration.requested`, `contract.proposed`, `contract.agreed`, `contract.verified`, `delivery.created`, `delivery.evidence_added`, `delivery.reviewed`, `delivery.integrated`, `project.closed`, `project.reopened`.

## D. Política de avaliação de aprovação

```text
can_approve(candidate, reviewer, evidence):
    require candidate.frozen_hash == evidence.reviewed_hash
    require project.state == OPEN
    require no_open_blocking_comments(candidate)
    require all_required_CI_checks_pass(candidate.frozen_hash)
    require independent(reviewer, candidate.author)
    require reviewer.is_authorized_for(project, risk)
    require evidence.reproducible_and_authenticated
    if candidate.risk == HIGH: require human_approval_from_distinct_member
    return APPROVABLE
```

A execução real deve usar transações e políticas de segurança implementadas pelo backend, não somente essa pseudológica. Para permissões de GitHub, respeitar as regras externas da branch, que podem exigir pessoas e CI específicos.

## E. Garantias mínimas

1. Nunca aplicar alteração em projeto fechado, mesmo com token previamente válido.
2. Não aceitar mudanças se o epoch do projeto foi alterado (revogação/fechamento).
3. Não fundir dois patches com conflito semântico conhecido; registrar bloqueio e resolução.
4. Nunca marcar uma rota como pronta/testada apenas porque a IA a descreveu.
5. Vincular aprovação ao exato conteúdo revisado, evidências e identidade real/delegada.
6. Nunca executar produção automaticamente por uma simples edição do workspace.
7. Não exigir que sessão offline responda a menções; notificação aguarda ou é escalada.
8. A IA só lê projetos autorizados, não todos os projetos de todos os clientes indistintamente.
