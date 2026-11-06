# Plano do servidor Python — gateway de streaming da Central

Status: planejamento; nenhuma conexão real é ativada pela Fase 1 desktop  
Data: 2026-11-04  
Objetivo: substituir o `CentralStore` em memória por um gateway auditável, com streaming ordenado e integração futura com Claude/Codex

Este plano transforma as necessidades da documentação 1.1 e do redesign em contratos implementáveis. Ele não autoriza colocar chaves, chamadas externas ou telemetria inventada na interface atual.

## Princípios e limites

1. O servidor é a fonte de eventos observáveis; a UI nunca infere produtividade, presença ou raciocínio privado.
2. Cada evento tem identidade, sequência, origem, timestamp, estado de disponibilidade e referência de projeto/tarefa.
3. O cliente pode desconectar e retomar a partir de `last_seq`; reconexão não duplica eventos.
4. Uso de tokens só é exibido quando o provedor retorna contagens medidas. Se não houver usage, o valor é `N/D`.
5. Chaves de API são por usuário e provedor, mas nunca são devolvidas ao desktop, gravadas em logs, eventos ou mensagens de erro.
6. MCP é uma fronteira de ferramentas/recursos. A integração com Claude/Codex deve passar por adapters oficiais e manter um caminho de fallback para a API oficial do provedor quando MCP não for o transporte apropriado.

## Arquitetura proposta

```text
Windows Central
   │ HTTPS + SSE (eventos) / WebSocket (controle opcional)
   ▼
FastAPI gateway
   ├── AuthN/AuthZ + tenant/project policy
   ├── Run service + idempotency + cancellation
   ├── Provider adapters
   │     ├── Claude adapter (API oficial ou MCP server)
   │     └── Codex/OpenAI adapter (API oficial ou MCP server)
   ├── Event normalizer + redaction + outbox
   ├── Stream broker (Redis Streams ou NATS, quando houver escala)
   └── Audit/usage service
        ├── PostgreSQL: estado, claims, eventos e auditoria
        └── Secret store/KMS: chaves cifradas por usuário
```

### Stack inicial

- Python 3.12+, FastAPI, Uvicorn, AnyIO e Pydantic v2;
- PostgreSQL para estado transacional, `workspace_revision`, claims, outbox e auditoria;
- Redis Streams na primeira implantação distribuída; NATS JetStream é uma alternativa quando o volume e o isolamento de consumidores justificarem;
- Alembic para migrações, `httpx` para adapters HTTP, SDK oficial quando existir e cliente MCP isolado por processo/sessão;
- OpenTelemetry para métricas técnicas, com redaction antes do exporter;
- pytest, pytest-asyncio, Hypothesis e testes de contrato para eventos.

Redis/NATS não são pré-requisitos da primeira vertical slice. O gateway pode iniciar com outbox em PostgreSQL e um worker único, mantendo a mesma interface de stream.

## Identidade, API keys e autorização

### Usuário e sessão

- O desktop autentica o usuário por OIDC/device flow ou sessão local de desenvolvimento explicitamente marcada.
- O gateway emite um access token curto, com `user_id`, `tenant_id` e escopos; refresh token fica fora dos eventos.
- Todas as operações recebem `project_id` explícito. Nunca selecionar projeto apenas pelo nome.
- Policy checa membro, papel, estado do projeto, tarefa, recurso e ação antes de criar claim, run, entrega ou publicação.

### Chaves dos provedores

- `provider_credentials` guarda `user_id`, `provider`, `key_version`, escopos, estado de revogação e metadados; o segredo cifrado fica em KMS/secret manager ou envelope encryption com chave mestra fora do banco.
- Em desenvolvimento, usar um secret store local documentado; nunca usar `.env` versionado, `appsettings`, JSON de fixture ou clipboard como armazenamento permanente.
- A API aceita `POST /v1/me/provider-keys` somente pelo usuário autenticado; grava a chave cifrada e retorna apenas fingerprint mascarada, provedor, data e estado.
- Worker descriptografa a chave somente no momento da chamada, em memória, e passa a um adapter. Nunca inclui a chave em exceção, trace, prompt, payload MCP ou `request_log`.
- Rotação/revogação é idempotente. A versão anterior deixa de ser aceita; jobs em andamento terminam como `cancelled` ou `provider_error` sem tentar repetir com segredo revogado.
- O usuário pode usar uma credencial de serviço por projeto no futuro, mas isso é uma decisão separada e não deve ser inferida a partir da chave pessoal.

## Contrato de streaming

Cada evento normalizado tem uma forma equivalente a:

```json
{
  "event_id": "evt_01J...",
  "request_id": "req_01J...",
  "seq": 42,
  "tenant_id": "ten_...",
  "project_id": "prj_seloryn",
  "run_id": "run_...",
  "session_id": "ses_...",
  "type": "run.delta",
  "provider": "claude",
  "model": "provider-model-id",
  "created_at": "2026-11-04T20:15:00Z",
  "availability": "connected",
  "payload": {"text_delta": "..."},
  "redaction": {"secrets_removed": true}
}
```

Tipos mínimos: `run.started`, `run.delta`, `run.tool_call`, `run.tool_result`, `run.usage`, `run.completed`, `run.cancelled`, `run.failed`, `connection.heartbeat` e `audit.decision`. `run.usage` carrega `input_tokens`, `output_tokens`, `total_tokens` e a origem da medição; não calcula tokens por aproximação.

### Entrega e retomada

- `GET /v1/runs/{run_id}/events` usa SSE e aceita `Last-Event-ID`/`last_seq`.
- Cada stream mantém sequência monotônica por `run_id`; banco/outbox garante persistência antes da publicação.
- O cliente confirma apenas leitura local; o servidor não apaga o evento até a política de retenção/auditoria permitir.
- Repetições são deduplicadas por `event_id`; o cliente aplica somente uma vez e atualiza `last_seq` monotonicamente.
- Heartbeat não é atividade de agente. Queda, atraso, `stale` e reconexão aparecem como estado de disponibilidade.
- Backpressure: limite de buffer por sessão, coalescência apenas de `run.delta` consecutivo e nunca de mudança de estado, uso, erro ou decisão.
- Cancelamento propaga para o adapter e registra quem cancelou e por quê.

## Endpoints da primeira vertical slice

| Método | Rota | Contrato |
|---|---|---|
| `GET` | `/v1/projects` | catálogo com ID, logo, status, revisão e permissão |
| `GET` | `/v1/projects/{project_id}` | contexto, tarefa, claims e próximo gate |
| `POST` | `/v1/runs` | cria run idempotente; recebe projeto, tarefa, provider/model e prompt permitido |
| `GET` | `/v1/runs/{run_id}` | snapshot de estado, origem e `last_seq` |
| `GET` | `/v1/runs/{run_id}/events` | SSE retomável, redigido e ordenado |
| `POST` | `/v1/runs/{run_id}/cancel` | cancelamento autorizado e auditado |
| `GET` | `/v1/usage?range=1d\|7d\|31d` | agregações por equipe/projeto, somente de usage medido |
| `GET` | `/v1/request-logs` | logs mascarados com fonte, frescor, modelo, transporte e status |
| `POST/DELETE` | `/v1/me/provider-keys/{provider}` | salvar/revogar credencial do usuário sem expor o segredo |

## Modelo de dados mínimo

- `users`, `tenants`, `project_members`, `projects`, `tasks`, `claims` com TTL e fencing;
- `runs`, `run_events` com unique `(run_id, seq)` e unique `event_id`;
- `provider_credentials` com envelope cifrado, `key_version`, fingerprint e revocation timestamp;
- `outbox_events` com tentativas, published_at e erro redigido;
- `request_logs` com `request_id`, principal mascarado, provider/model, transport, status, TTFT medido, usage e freshness;
- `audit_log` append-only para autorização, acesso a segredo, cancelamento, aprovação, integração e publicação.

Índices e retenção devem ser definidos com o volume real. Não declarar SLA, stale threshold ou duração de retenção antes de medir e decidir com o responsável operacional.

## Observabilidade e segurança operacional

- correlation ID de ponta a ponta (`request_id`) sem incluir prompt completo por padrão;
- logs estruturados com allowlist, redaction de chaves, tokens e conteúdo sensível;
- métricas: latência até primeiro token, duração, eventos descartados, reconexões, duplicatas, erro por provider e usage retornado;
- alertas de fila, outbox atrasado, falha de KMS, provider rate-limit e divergência de sequência;
- testes de autorização por projeto, isolamento entre usuários, replay de eventos, rotação de chave, cancelamento, reconexão e carga com nove sessões;
- limites de tamanho e tempo, rate limit por usuário/provedor e circuit breaker por provider;
- CSP/HTTPS, secrets fora do desktop, dependências fixadas e SBOM no empacotamento.

## Fases de entrega

1. **Contrato e fake gateway**: schemas, redaction, sequência, SSE e cliente de teste; sem chamadas externas.
2. **Persistência**: PostgreSQL, outbox, claims, auditoria, autorização por projeto e migrações.
3. **Credenciais**: secret store, chaves por usuário, rotação/revogação e testes de não-vazamento.
4. **Adapter Claude**: caminho oficial escolhido após validar disponibilidade da API/MCP, usage, tool calls e cancelamento.
5. **Adapter Codex/OpenAI**: mesmo contrato normalizado, sem vazar diferenças de provider para a UI.
6. **Desktop streaming**: substituir fixtures por cliente SSE/WebSocket, manter `N/D` em offline e suportar retomada.
7. **Operação**: broker, workers, tracing, load test, rollout gradual e plano de rollback.

## Critérios de aceite do servidor

- um run produz eventos ordenados e retomáveis sem duplicação;
- dois usuários não conseguem ler, cancelar ou usar credencial do outro;
- uma chave revogada não é usada em novas chamadas e não aparece em logs/eventos;
- tokens exibidos são os retornados pelo provider, com origem e frescor;
- queda do provider resulta em estado explícito `provider_error`/`stale`, nunca sucesso verde;
- nove sessões concorrentes preservam claims, `workspace_revision`, sequência e auditoria;
- testes de contrato provam que a Central desktop consegue renderizar o mesmo modelo com fake gateway e com provider real sem mudar a UI.

