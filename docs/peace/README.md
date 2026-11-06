# Peace Discord Bot

Primeiro recorte do bot da Real Peace em Python:

- captura membros com o cargo `Peace`, cargos completos e mensagens do bot;
- atribuição persistente de IDs Peace no SQLite, reservando `0` para o fundador;
- fluxo de `Pedir set` com modal de apelido, RG, telefone, origem e recrutador;
- tickets privados com `Poke`, encerramento, renomear e assumir;
- seleção de categoria para tickets, call privada, avisos por DM e bloqueio de ações após encerramento;
- ponto, logs de farme e solicitação de ausência;
- atendimento contínuo da Iris usando o histórico recente do ticket;
- preservação dos `custom_id` originais `peace_pedir_set_open`, `peace_support_open_ticket` e `clock_in_btn`.

## Executar

```powershell
python -m pip install -e .
python -m bot.snap
python -m bot.main
python -m bot.nick --apply
```

`snapshot` é somente leitura no Discord e grava o snapshot JSON em
`data/snapshots/` e o banco em `data/`. Ele não renomeia membros nem modifica cargos. O bot só aplica cargos e
apelido quando um candidato conclui o fluxo de set e o painel está aberto.

Para abrir vagas, altere `SET_VAGAS_ABERTAS=true` no `.env` e reinicie o bot.
O painel existente no servidor permanece fechado enquanto estiver `false`.

O atendimento da Iris usa um modelo local. Mantenha o serviço disponível em
`IRIS_URL` antes de iniciar o bot. A Iris monta o contexto com os dados do
ticket e as mensagens recentes; isso é recuperação de contexto local, não uma
alteração dos pesos do modelo.

No ambiente atual, o serviço usa armazenamento em `D:\\Ollama\\Models`, a porta
`11435` e o perfil `iris-peace`, que foi validado no hardware disponível. Em uma
máquina menor, `iris-peace-micro` continua disponível como alternativa de menor
consumo:

```powershell
$env:OLLAMA_MODELS = "D:\\Ollama\\Models"
$env:OLLAMA_HOST = "127.0.0.1:11435"
$env:OLLAMA_LLM_LIBRARY = "cpu_avx2"
ollama serve
```

O catálogo das mensagens observadas está em
[`RECOVERED_MESSAGES.md`](RECOVERED_MESSAGES.md).

A organização da árvore e as regras para não versionar entulho ou dados locais
estão em [`AGENTS.md`](AGENTS.md) e
[`PROJECT_ORGANIZATION.md`](PROJECT_ORGANIZATION.md). Snapshots novos
são gravados em `data/snapshots/`; o SQLite atual permanece em
`data/peace.sqlite3` até uma migração explícita.

O inventário do código e do servidor está em
[`PEACE_SYSTEM_INVENTORY.md`](PEACE_SYSTEM_INVENTORY.md), e a proposta
de adaptação sem trocar a identidade da Peace está em
[`PEACE_ADAPTATION_PLAN.md`](PEACE_ADAPTATION_PLAN.md).

A política operacional e o limite de privacidade da Iris estão em
[`IRIS.md`](IRIS.md). Ela consulta gerência, chats e tickets anteriores
como contexto controlado, mas não grava conversas brutas como memória nem
revela conteúdo interno ao solicitante.

`bot.nick` troca somente o ID final dos apelidos existentes e preserva o nome
in-game. Ele ignora automaticamente o dono do servidor e membros acima da
hierarquia do bot; cargos não são removidos nem adicionados por essa migração.


