# Messages recovered from the original bot

Snapshot consulted on 2026-09-30 (project time):

- server: `1427129030427279503`
- observed bot: `Peace tools` (`1495083108083433643`)
- unique messages recovered: `238`
- complete source: the JSON files in `data/snapshots/discord_snapshot_*.json`
- local storage: `bot_messages` table in `data/peace.sqlite3`

## Identified panels and interactions

| Channel | Message/title | Observed custom IDs |
| --- | --- | --- |
| `1459443839998759042` · request-set | `🔹 Pedir set 🔹` | `peace_pedir_set_open` |
| `1459446670411567105` · ticket | `Suporte Peace` | `peace_support_open_ticket` |
| `1495087589604982785` · panel | `Painel de operações` | `clock_in_btn` |
| closed/open tickets | `Ticket aberto`, `Ticket encerrado`, `Atendimento assumido` | `peace_support_poke_ticket`, `peace_support_poke_staff`, `peace_support_close_ticket`, `peace_support_rename_ticket`, `peace_support_claim_ticket`, `peace_support_create_call` |

## Observed message families

- `Pedir set`
- `Set aprovado`
- `Set atualizado`
- `Suporte Peace`
- `Ticket aberto`, `Ticket encerrado`, `Atendimento assumido`
- `Ponto iniciado`, `Ponto finalizado`
- `Farme confirmado`
- `Top 3 da temporada`
- `Solicitação de ausência`
- `Painel de operações`
- goal and record notices without an embed/title

The first slice implemented in this project preserves the set-request custom ID
and recreates the initial interview, including nickname, national ID, phone,
source (`recruited`, `streamer`, or `clips`), and recruiter selection when
applicable.

The support and operations panels were also reintegrated. The nickname
migration updates only the Peace ID stored in SQLite; members above the bot's
hierarchy and the server owner remain untouched to avoid permission errors.
Closed tickets have their components removed during synchronization and are also
rejected in the callback, even if an old message still exists.
