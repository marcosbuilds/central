# Decisão de implementação — sincronização real e streaming 2026-11-06

Status: aceita para a primeira vertical slice operacional  
Responsável: usuário da Central / Central Colaborativa  
Escopo: pasta de teste dedicada, coordenação Supabase, eventos Realtime, integração local Syncthing e reconexão

## Resultado observável desejado

Dois computadores podem participar do mesmo projeto autenticado. Cada instalação registra um dispositivo, mantém uma pasta local dedicada e observa o estado resumido da sincronização. O conteúdo dos arquivos viaja por Syncthing; o Supabase guarda identidade, autorização, estado, locks e eventos. A Central recebe avisos em tempo real, mas relê eventos persistentes depois de uma queda.

## Invariantes

- `project_id`, usuário, dispositivo e sessão são identidades explícitas; não há pareamento por IP ou por nome de máquina.
- A pasta compartilhada é uma raiz dedicada fora do código-fonte e recebe regras de ignore para segredos e artefatos.
- O PostgreSQL é a fonte autoritativa de eventos e estado; Realtime é entrega de baixa latência e pode perder mensagens.
- O cursor de eventos é monotônico. Duplicatas e sequências antigas não alteram a UI; lacunas provocam recuperação por consulta persistente.
- A Central não guarda service-role key, senha do banco ou credenciais de provedor.
- Conflito de arquivo não é sucesso: arquivos `sync-conflict` e estados de erro continuam visíveis.
- Pausar a integração não apaga arquivos, não despareia dispositivos e não propaga uma exclusão de rollback.

## Evidência e revisões

- E-001: `CentralStore` e a UI atual são locais; `app/desktop/Central.Desktop/Services/CentralStore.cs` e `docs/ARCHITECTURE.md`.
- E-002: o gateway publicado oferece somente `/healthz` e capacidades; `ops/gateway/central_gateway.py`.
- E-003: a migração inicial já contém `devices`, `sync_states` e `project_events`; `db/migrations/202611050001_coordination.sql`.
- E-004: Lorentz (`01a1ae5c-a9a1-7742-815e-406db1c711e3`) e Newton (`01a1ae5c-aae1-7a42-8a8d-6b61431069bd`) fizeram passagens adversariais somente leitura sobre o worktree atual; os relatórios são revisão separada/role simulation e não substituem teste de integração entre dois PCs.
- E-005: a documentação oficial do Syncthing confirma a REST API de configuração, status, eventos e consulta de reinício; `https://docs.syncthing.net/rest/config` e `https://docs.syncthing.net/dev/rest.html`.
- E-006: a documentação do Supabase Realtime exige que o banco continue sendo relido após reconexão; o canal não é fonte autoritativa.
- E-007: a migração 202611060002 foi executada no SQL Editor do projeto `ydouynbssldpjhlnawtm` e a consulta posterior confirmou RPCs, policy privada e publicação de `sync_states`.

## Decisão

1. Syncthing é o plano de dados. A Central inicializa/observa uma instância local somente quando o executável empacotado estiver disponível e nunca compartilha o repositório inteiro.
2. Supabase é o plano de controle. A migração aditiva já aplicada adiciona registro idempotente de dispositivo, heartbeat, atualização autenticada de `sync_states`, eventos idempotentes, uma pasta de projeto, filtro de dispositivos por projeto e autorização do canal privado.
3. O desktop usa REST para snapshot/replay e WebSocket Realtime para notificação. A reconexão sempre busca `project_events` depois de `last_seq`.
4. O gateway PythonAnywhere permanece health-only nesta fase. Não há SSE contínuo no plano gratuito.
5. O modo de sincronização fica explícito na configuração. A primeira pasta de teste pode ser `send-only`/`receive-only`; `send-receive` só deve ser usado depois de a cópia e o hash do arquivo de teste estarem comprovados.

## Alternativas rejeitadas ou adiadas

- Supabase Storage como pasta local: não fornece semântica P2P, edição offline e resolução de conflitos adequada.
- SSE contínuo no PythonAnywhere gratuito: um worker e timeout de web request não são compatíveis com uma conexão durável.
- Copiar arquivos pelo gateway: aumentaria o risco de perda, transformaria o gateway em armazenamento e não resolveria edição offline.
- Declarar a presença do segundo PC por `/healthz`: saúde do servidor não prova identidade, pareamento ou igualdade de hashes.

## Verificação mínima

- Testes determinísticos de cursor, deduplicação, contrato JSON, RPC e parser de status.
- Build e suíte .NET completos.
- Migração aplicada no projeto dedicado e validada com RLS, RPCs e Realtime.
- Syncthing local em pasta descartável: arquivo A→B, hash igual, alteração B→A, pausa/reconexão e conflito controlado.
- Prova física: dois Device IDs, dois heartbeats, arquivo/nonce e SHA-256 idêntico nos dois PCs, estado `insync` nos dois lados.

## Risco residual

O plano Supabase gratuito não é backup; Syncthing não substitui backup. Exclusões propagadas e conflitos permanecem operações que exigem teste em pasta descartável. A prova de dois PCs só será declarada quando as evidências acima forem observadas nos dois equipamentos.
