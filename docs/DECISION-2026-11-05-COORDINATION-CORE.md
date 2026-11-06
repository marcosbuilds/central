# Decisão de implementação — núcleo de coordenação 2026-11-05

Status: implementada localmente; integração Supabase pendente de projeto dedicado
Responsável: Central Colaborativa
Escopo: reservas de recursos, leases, fencing e primeira migração de coordenação

## Contrato da primeira vertical slice

O primeiro incremento verificável da missão é proteger o recurso antes da escrita:

- caminhos lógicos são relativos ao projeto, normalizados para o comportamento case-insensitive do Windows;
- uma reserva de projeto conflita com qualquer descendente; uma reserva de diretório conflita com arquivos descendentes e vice-versa;
- a reserva identifica usuário, dispositivo, agente, sessão, tarefa e projeto;
- leases têm heartbeat, expiração e fencing token monotônico;
- uma sessão pode repetir a aquisição do mesmo recurso sem criar duas reservas;
- somente o proprietário pode renovar ou liberar;
- conflito, expiração e liberação preservam o registro para auditoria;
- o coordenador em memória só é um adaptador determinístico para testes/offline e não é autoridade entre computadores.

## Evidências

| ID | Claim | Fonte | Classe | Resultado |
| --- | --- | --- | --- | --- |
| E-001 | A base atual é WPF/.NET 8 e `CentralStore` está em memória | `README.md`, `docs/ARCHITECTURE.md`, `app/desktop/Central.Desktop/Services/CentralStore.cs` | documentação + código | verificado |
| E-002 | A arquitetura existente já exige claims com TTL, revisão-base, auditoria e substituição por gateway | `docs/ARCHITECTURE.md`, `docs/SERVER-PLAN.md`, `docs/plan/07-collaboration.md` | contrato do projeto | verificado |
| E-003 | Reservas devem impedir sobreposição semântica e não podem depender de variável local | briefing da missão, seção 6 | requisito do usuário | adotado |
| E-004 | A primeira implementação precisa funcionar sem alegar integração externa inexistente | `README.md`, `docs/DESIGN-CONTRACT.md` | contrato do projeto | verificado |
| E-005 | Build Release atual passa sem avisos/erros | comando `dotnet build Central.sln -c Release --no-restore` em 2026-11-05 | observação executável | pass |
| E-006 | Suíte existente tinha 12 testes aprovados antes do incremento | comando `dotnet test Central.sln -c Release --no-restore` em 2026-11-05 | observação executável | pass |
| E-007 | PostgreSQL aceita a migração completa, incluindo DDL, funções, RLS, grants e Realtime | PostgreSQL 16 descartável no Docker; `Get-Content db/migrations/202611050001_coordination.sql | docker exec -i ... psql -v ON_ERROR_STOP=1` em 2026-11-05 | observação de integração local | pass |
| E-008 | Dois membros veem o projeto, uma reserva pai bloqueia a filha, renewal/release funcionam e usuário externo recebe `42501` | fixtures efêmeras + RPCs `create_organization`, `create_project`, `acquire_resource_lock`, `renew_resource_lock`, `release_resource_lock` em PostgreSQL 16 | observação de segurança/concor­rência local | pass |

## Decisão

Manter .NET 8 como stack da primeira integração porque a base WPF, o SDK empacotado e o instalador já existem neste ambiente. Adicionar um `Central.Core` sem dependências externas para expressar as invariantes do domínio e uma migração Supabase que será a fonte autoritativa multiusuário.

O caminho compartilhado usa RPCs PostgreSQL com `pg_advisory_xact_lock` por projeto. A checagem de sobreposição e a inserção acontecem na mesma transação. RLS restringe leitura ao projeto, e as RPCs validam `auth.uid()`, participação, proprietário da reserva, sessão e prazo.

## Autoridade externa adotada

- [Supabase Database Functions](https://supabase.com/docs/guides/database/functions): RPCs são a fronteira para operações transacionais; funções `security definer` têm `search_path` vazio, referências qualificadas e execução restrita.
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security): grants e policies são necessários em conjunto; a migração habilita RLS em todas as tabelas expostas e revoga o papel `anon`.
- [Supabase Realtime](https://supabase.com/docs/guides/realtime/subscribing-to-database-changes): o estado persistente não depende de uma notificação; a próxima etapa usará Broadcast/Presence para sinais rápidos e manterá PostgreSQL como fonte autoritativa.
- [Syncthing Config REST API](https://docs.syncthing.net/rest/config): a futura automação deve ler e atualizar dispositivos/pastas pelas APIs oficiais e acompanhar `restart-required`, sem editar configuração de outro computador às cegas.

## Riscos selecionados

- concorrência/idempotência: teste paralelo e aquisição repetida;
- dados/esquema: migração nova, sem alteração no banco existente;
- autorização: RLS e validações negativas ainda precisam de execução em projeto dedicado;
- integração externa: Supabase/Realtimes ainda não foram executados;
- compatibilidade: desktop atual continua com `CentralStore` local até existir cliente autenticado.

## Superfícies autorizadas nesta rodada

- `app/core/**`;
- `tests/app/**` apenas para referência e testes do novo núcleo;
- `Central.sln`;
- `db/migrations/202611050001_coordination.sql`;
- este registro e a documentação de arquitetura/README.

Não foram alterados projetos Supabase, dados existentes, credenciais, PythonAnywhere ou o instalador publicado.

## Verificação prevista

1. Build Release da solução.
2. Testes unitários e concorrentes do núcleo.
3. Validação SQL em um projeto Supabase dedicado, incluindo RLS entre dois usuários e RPCs em corrida; a sintaxe e o fluxo equivalente já foram validados em PostgreSQL 16 descartável.
4. Só depois: cliente autenticado do desktop, sincronização Syncthing e integração MCP.

## Limitações ainda abertas

- A migração ainda não foi aplicada; o Supabase aberto no navegador contém uma organização existente com um projeto que não será reutilizado.
- Não há ainda autenticação desktop, cliente REST/RPC, Syncthing configurado, Git worktree ou adapters Codex/Claude.
- O teste local prova a invariável do algoritmo, não prova concorrência entre dois computadores nem a execução de PostgreSQL.
