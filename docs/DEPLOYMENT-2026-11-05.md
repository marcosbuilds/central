# Entrega de infraestrutura — Central Colaborativa

Data: 2026-11-05  
Escopo: provisionamento dedicado e smoke test remoto

## Supabase

- Organização: `Seloryn Collective FREE`
- Projeto: `Central Colaborativa`
- Project ref: `ydouynbssldpjhlnawtm`
- URL pública do projeto: `https://ydouynbssldpjhlnawtm.supabase.co`
- Estado observado após o provisionamento: `Healthy`
- Compute: `Nano`
- Região observada no painel: `Canada (Central)` / `ca-central-1`
- Migrações aplicadas: `db/migrations/202611050001_coordination.sql` e `db/migrations/202611060002_sync_stream.sql`
- Resultado da segunda aplicação: `Success. No rows returned`

### Verificação executada no projeto real

A consulta de verificação retornou 19 linhas: as 14 tabelas da coordenação
estão com RLS habilitado (`true`) e as cinco funções de coordenação estão
negadas para `anon` e concedidas para `authenticated` (`false/true`).

Após a segunda aplicação, uma consulta no projeto real confirmou as RPCs
`register_device`, `get_project_devices`, `heartbeat_device`,
`upsert_sync_state`, `append_project_event` e `ensure_sync_folder`, a policy
privada de `realtime.messages` e `project_events`/`sync_states` na publicação
`supabase_realtime`.

Nenhuma organização, projeto, usuário, senha, service-role key ou dado de
produção foi criado dentro do schema. A criação de organização/projeto exige
uma sessão autenticada pelo próprio cliente.

## PythonAnywhere

- Conta: `MarcosBuilds`
- Web app: `https://marcosbuilds.pythonanywhere.com`
- Python: `3.12`
- WSGI: `/var/www/marcosbuilds_pythonanywhere_com_wsgi.py`
- Código enviado: `ops/gateway/central_gateway.py`
- Endpoint verificado após a publicação 0.2.0: `/healthz` → `status: ok`, `deployment: pythonanywhere`, `version: 0.2.0`
- Endpoint verificado: `/v1/capabilities` → somente `health` disponível

O gateway não recebeu senha, service-role key ou publishable key. As variáveis
opcionais são lidas do ambiente e aparecem apenas como booleanos de
configuração. O PythonAnywhere é um gateway de disponibilidade; não é disco
Syncthing nem fonte autoritativa de dados.

## Pacote para os computadores

O instalador Windows é self-contained x64 e continua local/offline-first. O
desktop desta versão contém login por senha em memória, cliente REST/Reatime
autenticado, checkpoint de replay e Syncthing empacotado. A criação de usuário,
organização e projeto ainda exige uma sessão autenticada; nenhum usuário ou
dado de produção foi criado automaticamente pela migração.

O segundo computador físico não está sob controle desta sessão. O pacote pode
ser instalado nele, mas isso não será declarado como teste concluído até que a
execução seja observada nesse equipamento.

## Verificações

- `dotnet test Central.sln -c Debug --no-restore`: 30 aprovados, 0 falhas.
- `dotnet build Central.sln -c Debug --no-restore`: aprovado, 0 erros e 0 avisos.
- O cliente desktop agora consulta somente `/healthz` ao abrir; os testes unitários do cliente de saúde cobrem sucesso, erro HTTP e URL inválida.
- Empacotamento Release concluído por `ops/scripts/Build-Central.ps1`; o instalador
  `artifacts/installer/Central-Colaborativa-Setup-0.2.0.exe` instalou e
  desinstalou em uma pasta temporária, com `Central.exe` e `syncthing.exe`
  presentes e códigos de saída 0.
- Teste Python local: não executado; o Python não está instalado neste Windows.
- Smoke test remoto PythonAnywhere: aprovado via navegador HTTPS.
