# Central — regras do monorepo

Este diretório é a fonte de código da Central Colaborativa e do bot Discord da
Peace. A organização separa os produtos por responsabilidade, mas mantém um
único controle de versão e um único fluxo de revisão.

## Árvore canônica

```text
.
├── app/                      # Central desktop: core/ e desktop/
├── bot/                      # código Python do bot Peace
├── db/                       # migrações Supabase
├── ops/                      # gateway, instalador e scripts
├── tests/                    # testes app/ e peace/
├── assets/                   # assets versionados do bot
├── data/                     # estado local ignorado
├── docs/                     # arquitetura, decisões, integração e plano/
└── .github/                  # CI e templates de revisão
```

`artifacts/`, `tools/`, `shared-test/`, caches, bancos locais, snapshots,
`.env` e credenciais são locais e não entram no repositório. O `.env.example`
é permitido somente quando não contém valores secretos.

## Integração Peace → Central

O contrato planejado está em `docs/INTEGRATION-PEACE-CENTRAL.md`. O bot Discord
é a autoridade para confirmar o membro e o cargo técnico `Dev`; a Central não
recebe nem armazena o token do bot. O código de DM deverá ser de uso único, com
expiração, limite de tentativas e registro sem o valor em claro.

O contrato está documentado, mas a troca de código ainda não é considerada
implementada. O gateway PythonAnywhere atual continua sendo apenas health e
capabilities; ele não deve receber o token do Discord nem virar um broker de
autenticação sem uma decisão de arquitetura e testes de segurança.

## Processo Git

- `main` representa somente código revisado e aprovado.
- Todo trabalho entra por branch (`feature/`, `fix/`, `docs/` ou `chore/`).
- Nenhum commit direto em `main` é permitido.
- Toda alteração deve passar por Pull Request, CI verde e aprovação de
  colaborador autorizado.
- Migrações, permissões Discord, autenticação e mudanças de dados exigem uma
  decisão registrada e um teste negativo correspondente.

## Verificação mínima

- Central: `tools/dotnet/dotnet.exe build Central.sln -c Release` e `dotnet test`.
- Peace: `python -m pytest tests/peace -q` após instalar o
  pacote em ambiente virtual.
- Antes de publicar, revisar `git diff --check`, `git status` e a lista de
  arquivos para confirmar que nenhum segredo ou estado local foi incluído.
