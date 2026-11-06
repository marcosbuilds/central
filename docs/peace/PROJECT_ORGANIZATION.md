# Organização do projeto

## Objetivo

Manter a raiz previsível, separar código de estado local e permitir que o bot
evolua de um monólito funcional para módulos de domínio sem quebrar o servidor,
o banco ou os painéis já publicados.

## Árvore atual e regra de destino

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── assets/                 # recursos visuais versionados
├── bot/                    # pacote Python
├── docs/                   # documentação e decisões
├── tests/                  # será criado junto dos primeiros testes
└── data/                   # dados locais; não é fonte de código
    ├── README.md
    ├── runtime/            # estado operacional novo
    └── snapshots/          # exportações do Discord
```

O SQLite atual continua em `data/peace.sqlite3` por compatibilidade. Ele é um
local legado: não deve ser movido apenas por estética. Uma futura mudança para
`data/runtime/peace.sqlite3` precisa atualizar configuração, fazer cópia de
segurança e validar o banco antes e depois.

## Divisão planejada do pacote

Hoje `bot/main.py` contém inicialização, views, painéis, eventos, tickets, set,
operações, boosters, Iris e programação. A divisão deve ser incremental:

```text
bot/
├── main.py                 # compatibilidade e bootstrap
├── cfg.py                  # leitura e validação de configuração
├── db.py                   # fachada temporária do banco
├── context.py              # redaction e limites de contexto
├── ai.py                   # cliente e prompts da Iris
├── api.py                  # cliente REST usado pelos utilitários
├── features/               # regras por domínio
│   ├── set_flow.py
│   ├── tickets.py
│   ├── operations.py
│   ├── boosters.py
│   └── developer_flow.py
├── ui/                     # views, embeds e sincronização de painéis
├── integrations/           # Discord REST, Iris e serviços externos
└── persistence/            # schema, migrações e repositórios
```

As pastas novas só devem ser criadas quando houver código real para colocar
nelas. Não criar diretórios vazios apenas para completar uma árvore ideal.

## Ordem de refatoração

1. Criar testes para `context.py`, `nick.py`, configuração, IDs Peace e
   operações básicas do SQLite.
2. Extrair componentes visuais e embeds sem mudar regras de negócio.
3. Extrair o fluxo de set e tickets, mantendo chamadas delegadas em
   `PeaceBot`.
4. Extrair operações, boosters, Iris e o fluxo de desenvolvedores.
5. Separar schema e migrações do acesso ao banco.
6. Reduzir `main.py` a bootstrap, registro de eventos e composição dos módulos.

Em todas as etapas devem permanecer estáveis os comandos instaláveis, os
`custom_id` dos painéis e os dados existentes no SQLite.
