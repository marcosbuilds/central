# 08 — Dados, APIs e eventos: contratos para começar a implementação

## Entidades principais (modelo conceitual)

- `organizations`: empresa/cliente e isolamento.
- `members`: identidade interna; `discord_id` é associação externa, não chave primária do sistema.
- `invitations`, `memberships`, `project_memberships`, `roles`, `permissions`, `devices`, `api_tokens`.
- `projects`: objetivo, estado e configuração.
- `requirements`, `decisions`, `documents`, `document_versions`, `project_architecture_versions`, `project_modules`.
- `tasks`: responsável, estado, prioridade, aceite, módulo e dependências.
- `resource_map`: recursos lógicos, físicos e seus relacionamentos de dependência.
- `claims`: proprietário, sessão, projeto, recursos, expiração, estado e versão de reserva.
- `agent_sessions`: provedor, dispositivo, token, tarefa e heartbeat.
- `workspace_revisions`: número sequencial por projeto, manifesto de hashes, origem, horário.
- `change_sets`: intenção, base, patch, estado, testes, reviewer, impacto e reversão.
- `change_set_files`: caminho, hash anterior/novo, tipo e símbolo afetado.
- `reviews`, `review_comments`, `test_runs`, `deployments`, `releases`, `artifacts`, `audit_events`.
- `project_events`: evento persistente com `event_id`, `project_seq`, ator e payload filtrado.

## Regras que devem ser impostas pelo banco/gateway

- E-mail/nome Discord não são IDs de autorização; nunca confiar só em dados enviados pelo cliente.
- Um recurso exclusivo não pode estar ativamente reservado por dois escritores. Garantir por transação de banco com lock/índice adequado ou serviço serializador; não só checar e depois inserir sem proteção.
- `workspace_revision` cresce em ordem por projeto; `project_seq` de eventos é durável, gerado no mesmo fluxo transacional ou por outbox.
- Um change set só pode ser aplicado com sessão autorizada, reserva válida, paths permitidos e base compatível.
- Aplicação idempotente: a mesma chave de operação produz o mesmo resultado já registrado.
- Uma release aponta para revisão específica e lista de change sets aprovados e testes válidos.
- Revisão feita por pessoa diferente do autor quando requerido; aprovação invalidada se diff muda.

## Endpoints principais (desenho, sujeito a refinamento)

| Método | Rota | Ação |
|---|---|---|
| POST | `/v1/auth/discord/start` | Iniciar login Discord (fluxo seguro) |
| GET | `/v1/auth/discord/callback` | Concluir autenticação |
| POST | `/v1/invitations` | Criar convite, admin |
| POST | `/v1/members/{id}/approve` | Aprovar membro |
| GET | `/v1/projects` | Listar projetos acessíveis |
| POST | `/v1/projects` | Criar projeto |
| POST | `/v1/projects/{id}/imports` | Importar ZIP validado |
| GET | `/v1/projects/{id}/plan` | Planejamento e arquitetura |
| GET | `/v1/projects/{id}/tasks` | Tarefas e dependências |
| GET | `/v1/projects/{id}/workspace/manifest` | Árvore e hashes |
| GET | `/v1/projects/{id}/workspace/files` | Arquivo por caminho validado |
| POST | `/v1/projects/{id}/claims` | Pedir reserva atômica |
| POST | `/v1/claims/{id}/heartbeat` | Renovar presença/reserva |
| DELETE | `/v1/claims/{id}` | Liberar reserva |
| POST | `/v1/projects/{id}/patches/validate` | Pré-checar conjunto de alteração |
| POST | `/v1/projects/{id}/patches/apply` | Aplicar lote canônico |
| POST | `/v1/projects/{id}/reviews` | Solicitar revisão |
| POST | `/v1/reviews/{id}/decision` | Aprovar, rejeitar, pedir correção |
| POST | `/v1/projects/{id}/test-runs` | Executar testes permitidos |
| POST | `/v1/projects/{id}/releases` | Criar snapshot estável aprovado |
| POST | `/v1/projects/{id}/deployments` | Deploy com autorização específica |
| GET | `/v1/projects/{id}/events?after_seq=N` | Recuperar eventos perdidos |
| WS | `/v1/projects/{id}/stream` | Websocket autenticado e ordenado |
| POST | `/v1/me/tokens` | Criar token com menor permissão |
| DELETE | `/v1/me/tokens/{id}` | Revogar token |

Endpoints de mutação exigem autorização por projeto, validação de entrada, idempotência quando houver risco de duplicidade e logs auditáveis. **Patches grandes** podem ser enviados por objeto temporário assinado com expiração em vez de payload ilimitado na API.

## Payload mínimo para pedido de reserva

```json
{
  "project_id": "P-001",
  "task_id": "T-104",
  "session_id": "S-IA-1",
  "semantic_resources": ["booking.create", "booking.availability"],
  "write_paths": ["services/api/src/booking/**"],
  "read_dependencies": ["packages/contracts/booking.schema.json"],
  "intent": "Criar agendamento sem duplicar horário",
  "lease_seconds": 120,
  "idempotency_key": "claim-uuid"
}
```

## Exemplo de envelope de patch

```json
{
  "project_id": "P-001",
  "task_id": "T-104",
  "agent_session_id": "S-IA-1",
  "claim_id": "C-040",
  "base_revision": 127,
  "idempotency_key": "patch-uuid",
  "changes": [
    {
      "path": "services/api/src/booking/service.py",
      "base_sha256": "sha256-do-conteudo-original",
      "operation": "modify",
      "patch_ref": "objeto-restrito-patch-42"
    }
  ]
}
```

O conteúdo do `patch_ref` deve ter limites de tamanho, verificações de segurança e retenção. O gateway calcula hashes novos, checks de escopo e dependências e só então aplica.

## Modelo de eventos

Todo evento importante carrega: `event_id`, `project_id`, `project_seq`, `occurred_at`, `actor_type`, `actor_id`, `session_id` opcional, `task_id`, `workspace_revision`, `type`, `payload` limitado. Não inserir conteúdo sensível desnecessário nem credenciais.

**Semântica de exibição:** status `agent.activity` é observação da execução; `patch.applied` é confirmação de que houve alteração no código central. Nunca mostrar ‘arquivo já atualizado’ só com base em um token de texto da IA.

## Compatibilidade de versões

Versão da API `/v1`, tipo de evento estável e `schema_version` dentro dos envelopes; consumidores ignoram campos desconhecidos e rejeitam alterações incompatíveis explicitamente. Alterações de contratos importantes exigem migração e testes.
