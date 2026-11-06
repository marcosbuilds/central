# Central Colaborativa — aplicativo desktop Windows

Implementação da Central Colaborativa para Windows, construída em C# e .NET 8 com WPF. O shell visual continua usando fixtures locais para as áreas ainda não conectadas, enquanto a pasta dedicada já pode sincronizar arquivos entre computadores via Syncthing e receber estado/eventos pelo Supabase.

Este repositório agora é um monorepo: o bot Discord da Peace está em
[`bot`](bot), com testes em [`tests/peace`](tests/peace). O contrato de liberação
Peace→Central está documentado em
[`docs/INTEGRATION-PEACE-CENTRAL.md`](docs/INTEGRATION-PEACE-CENTRAL.md), mas a
troca de código ainda não é uma capacidade implementada.

## O que está entregue

- Shell desktop nativo com navegação por Home, Projetos e projeto selecionado; configurações visuais ficam na engrenagem do perfil.
- Catálogo com busca por nome, identificador ou módulo.
- Detalhe de projeto com visão geral, planejamento, Pulso local manual, workspace explorável, discussões, entregas, qualidade, publicações e histórico.
- Simulações coerentes de reserva semântica, patch com revisão-base, eventos ordenados, referências locais, commits/tags/releases locais, candidatos de entrega, evidências, aprovação local e fechamento/reabertura.
- Estado fechado bloqueando escrita, reserva, Pulso, versionamento local, aprovação, integração e deploy na camada de domínio local.
- Catálogo de projetos com marca vetorial própria, título funcional em Apple/Segoe, subtítulos editoriais em Seloryn, tier de prioridade e leitura responsiva.
- Dashboard de uso técnico preparado para duração, tokens e requests em 1/7/31 dias, mantendo `N/D` quando o gateway não fornece medições.
- Home sem projeto escolhido por padrão: a Central não adivinha o foco; o catálogo resolve a identidade antes de abrir uma bancada.
- Suíte xUnit com doze testes de domínio e comportamento cobrindo os invariantes principais, seleção semântica e os fluxos do Pulso/workspace.
- Núcleo `Central.Core` com normalização de recursos Windows, reservas pai/filho, leases, heartbeat, expiração, fencing token e teste de corrida entre 32 sessões.
- Primeira migração Supabase versionada em `db/migrations/202611050001_coordination.sql`, com RLS, tabelas de coordenação e RPCs transacionais para adquirir, renovar e liberar reservas; ela foi aplicada ao projeto dedicado `ydouynbssldpjhlnawtm`.
- Gateway WSGI mínimo publicado em `https://marcosbuilds.pythonanywhere.com`, com `/healthz` e `/v1/capabilities` para smoke test; a publicação não armazena chaves nem substitui o Supabase.
- O desktop faz um smoke test automático de `/healthz` ao abrir e aceita `CENTRAL_GATEWAY_URL` para apontar a instalação a outro gateway sem recompilar.
- Publicação self-contained x64 e instalador Windows Inno Setup.
- Sincronização real opt-in: cada instalação autentica no Supabase, registra seu Device ID, configura uma pasta Syncthing local e acompanha peers, estado, heartbeat e conflitos.
- Streaming de controle por Supabase Realtime privado, com confirmação de `phx_join`, renovação de sessão, backoff e replay persistente após reconexão. O cursor local é apenas checkpoint; PostgreSQL continua sendo a fonte de verdade.
- Migração `db/migrations/202611060002_sync_stream.sql` aplicada e verificada no projeto dedicado `ydouynbssldpjhlnawtm`; peers são filtrados por projeto e writes sensíveis passam por RPC autenticada.
- Estado vazio validado também pela árvore UI Automation: a Home não anuncia escalas fictícias nem cabeçalhos de logs sem linhas; Provar reflowa ações antes de perder conteúdo em largura compacta.

## Árvore do repositório

```text
app/       Central desktop e núcleo compartilhado
bot/       bot Discord Peace
db/        migrações Supabase
ops/       gateway, instalador e scripts
tests/     testes da Central e da Peace
assets/    imagens versionadas do bot
docs/      arquitetura, decisões, integração e plano
data/      marcadores locais; dados reais ficam fora do Git
```

## Limite honesto da fase

Ainda não há conexão com Discord, Codex, Claude, Git, CI/CD ou deploy. O Pulso, tags, releases, commits e catálogo visual continuam sendo fixtures locais; eles não devem ser confundidos com o plano de dados da pasta compartilhada. O PythonAnywhere permanece health-only nesta fase: o streaming real usa Supabase Realtime/WebSocket e os bytes usam Syncthing. Uma prova física entre dois PCs ainda precisa ser observada antes de ser declarada concluída.

## Executar a partir do código

O SDK usado está em `tools/dotnet` para manter o ambiente organizado no disco D:. No PowerShell:

```powershell
$dotnet = 'D:\projetos\Central\tools\dotnet\dotnet.exe'
& $dotnet restore 'D:\projetos\Central\Central.sln'
& $dotnet build 'D:\projetos\Central\Central.sln' -c Debug --no-restore
& $dotnet run --project 'D:\projetos\Central\app\desktop\Central.Desktop\Central.Desktop.csproj' -c Debug --no-restore
```

## Testes

```powershell
& 'D:\projetos\Central\tools\dotnet\dotnet.exe' test 'D:\projetos\Central\Central.sln' -c Debug --no-restore
```

## Empacotamento

O instalador final fica em `artifacts\installer\Central-Colaborativa-Setup-0.2.0.exe`. O fluxo reproduzível está em `ops\scripts\Build-Central.ps1` e a publicação self-contained fica em `artifacts\publish`. O registro da infraestrutura está em [docs/DEPLOYMENT-2026-11-05.md](docs/DEPLOYMENT-2026-11-05.md).

## Decisões e próximo passo

- O contrato visual vigente está em [docs/DESIGN-DECISIONS-2026-11-04.md](docs/DESIGN-DECISIONS-2026-11-04.md).
- O planejamento futuro do gateway Python, adapters Claude/Codex e chaves por usuário está em [docs/SERVER-PLAN.md](docs/SERVER-PLAN.md). O componente atualmente publicado está em `ops/gateway/` e deliberadamente expõe apenas saúde/capacidades; não é broker de arquivos nem substitui o Supabase.

## Fonte de planejamento

O planejamento original foi preservado como evidência em
`docs/plan`. O contrato visual e o adendo de
decisões podem substituir a interpretação de navegação quando o contraexemplo
documentado demonstrar que a hipótese original faria a pessoa perder contexto;
os limites de domínio, segurança e integração futura continuam normativos.
Toda mudança desse tipo está registrada em
`docs/DESIGN-DECISIONS-2026-11-04.md`.
