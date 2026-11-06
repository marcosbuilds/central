# Mensagens recuperadas do bot original

Snapshot consultado em 30/09/2026 (horário do projeto):

- servidor: `1427129030427279503`
- bot observado: `Peace tools` (`1495083108083433643`)
- mensagens únicas recuperadas: `238`
- fonte completa: os JSONs em `data/snapshots/discord_snapshot_*.json`
- armazenamento local: tabela `bot_messages` em `data/peace.sqlite3`

## Painéis e interações identificadas

| Canal | Mensagem/título | Custom IDs observados |
| --- | --- | --- |
| `1459443839998759042` · pedir-set | `🔹 Pedir set 🔹` | `peace_pedir_set_open` |
| `1459446670411567105` · ticket | `Suporte Peace` | `peace_support_open_ticket` |
| `1495087589604982785` · painel | `Painel de operações` | `clock_in_btn` |
| tickets fechados/abertos | `Ticket aberto`, `Ticket encerrado`, `Atendimento assumido` | `peace_support_poke_ticket`, `peace_support_poke_staff`, `peace_support_close_ticket`, `peace_support_rename_ticket`, `peace_support_claim_ticket`, `peace_support_create_call` |

## Famílias de mensagens observadas

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
- avisos de metas e registros sem embed/título

O primeiro recorte implementado neste projeto preserva o custom ID do pedido de
set e recria a entrevista inicial, incluindo apelido, RG, telefone, origem
(`recrutado`, `streamer` ou `clipes`) e seleção do recrutador quando aplicável.

Também foram reintegrados os painéis de suporte e operações. A migração de
apelidos atualiza somente o ID Peace salvo no SQLite; membros acima da
hierarquia do bot e o dono do servidor ficam preservados para evitar erro de
permissão. Tickets encerrados têm seus componentes removidos na sincronização e
também são rejeitados no callback, mesmo que uma mensagem antiga ainda exista.

