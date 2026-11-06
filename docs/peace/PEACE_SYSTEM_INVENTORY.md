# Inventário atualizado da Peace

Este inventário registra o estado do código e a adaptação aplicada no Discord
Development em 2 de novembro de 2026. Snapshots completos ficam em
`data/snapshots/` e não são fonte de código.

## Código e entradas

| Arquivo | Responsabilidade | Estado |
| --- | --- | --- |
| `bot/main.py` | Gateway, views, painéis, tickets, entrevistas, boosters e Iris | ativo |
| `bot/maintenance.py` | migração estrutural idempotente e limpeza explícita | novo utilitário operacional |
| `bot/db.py` | SQLite, tickets, eventos, set e pedidos de desenvolvedor | ativo |
| `bot/cfg.py` | configuração por `.env` | ativo |
| `bot/ai.py` | cliente e prompts da Iris | disponível no código; atendimento com IA desativado por `IRIS_ENABLED=false` |
| `bot/context.py` | redaction, limites e sanitização | ativo |
| `bot/api.py` | REST usado pelos utilitários | ativo |
| `bot/snap.py` | snapshot somente leitura | ativo |
| `bot/nick.py` | utilitário de apelidos | usar apenas com revisão |

## Estado final aplicado

- servidor preservado como `REAL PEACE IS BACK`;
- `programming-only` deixou de ser um espaço de execução estrutural e foi
  convertido no canal público `spam-control`;
- `rules` permaneceu no topo;
- AFK foi movido para o topo como call pública visível, sem conexão;
- categoria `[🤝] FLORENZA & PEACE` virou `[💻] DEVELOPERS`;
- `chat-tie` virou `chat-dev`;
- `Call` virou `╭💻・programming`;
- `[🎙️] CALL・PEACE` virou `[🎙️] CALLS`, acessível a Peace, desenvolvimento e
  staff;
- `[🛡️] STAFF` recebeu `scan-only`, `staff-only` e `logs`, nessa ordem;
- `scan-only` ficou exclusivo do `Recrutador`; `staff-only` e `logs` ficaram
  exclusivos de `Staff Peace`;
- ticket panel permaneceu em `[☎️] ATENDIMENTO`;
- `[🎟️] TICKETS-FECHADOS` permanece vazio, reservado para arquivo e invisível;
- tickets abertos ficam acessíveis à `Staff Peace`, sem triagem automática da
  Íris;
- `[🔫] AÇÃO` e suas calls foram removidas;
- tickets `sup-*` antigos foram limpos do Discord e do SQLite;
- o cargo `Florenza Founds` foi removido pela interface de proprietário do
  Discord após a migração de acesso.
- os cargos `Advertência I`, `Advertência II`, `Advertência III` e `Sublider`
  foram removidos por manutenção autorizada.

## Cargos

| Cargo | Tipo | Regra |
| --- | --- | --- |
| `Dev` | acesso técnico | acesso à categoria Developers; permissões globais zeradas |
| `Developer` | visual | identificação, sem acesso |
| `Frontend` | visual | identificação, sem acesso |
| `Backend` | visual | identificação, sem acesso |
| `Documentation` | visual | identificação, sem acesso |
| `AI & Bots` | visual | somente bots com IA; sem acesso por si só |
| `Peace` | pertencimento/acesso existente | preservado |
| `Novato Peace` | progressão | preservado |
| `Staff Peace` | acesso operacional | preservado |
| `Gerência` | organização/hierarquia | preservado, com permissões globais zeradas; acesso somente por canais explícitos |
| `Recrutador` | aprovação | preservado |
| `Elite Peace` | acesso específico | preservado |
| `Visitante` | acesso de entrada | preservado |
| `Streamer` | identidade/benefício | preservado |
| booster e cargos gerenciados | integração | preservados |

O cargo antigo `Developer` não foi mantido com permissões perigosas: ele foi
reaproveitado pelo ID como `Dev` e teve as
permissões globais removidas. A identidade visual fica nos cargos separados.

## Banco local

O SQLite continua em `data/peace.sqlite3` por compatibilidade. A tabela
`developer_requests` registra o novo fluxo em etapas; RG e telefone pertencem ao
fluxo in-game de player e não devem ser reutilizados no processo de dev.

As tabelas antigas de `builder_objects` permanecem apenas para compatibilidade
de schema. O builder não está exposto em canal nem em `on_message`; uma limpeza
de schema só deve ocorrer em migração própria, com backup e rollback.

`peace_id_pool` agora distingue IDs disponíveis de IDs reservados. Quando uma
conta sai com `Peace`, o ID fica reservado; ao retornar, o pedido aparece no
`scan-only` com o botão `Liberar ID`. A aprovação libera o ID antigo e cria um
novo para a conta, evitando reutilização silenciosa.

## Auditoria e segurança

- `developer_requests` só é publicado em `scan-only`;
- aprovação de dev é limitada ao `Recrutador` com acesso ao `scan-only`;
- aprovação não concede cargo automaticamente;
- `spam-control` remove a mensagem, aplica timeout de sete dias e grava
  apenas o necessário no log;
- cargos visuais não entram em guardas de autorização;
- `scan-only` é acessível somente a recrutadores; `staff-only` e `logs` somente
  a `Staff Peace`;
- canais Developers aceitam `Dev` e `Staff Peace`; Gerência não tem override;
- `assets/automod.png` e o conteúdo do `spam-control` não participam da rotação
  visual Halloween;
- tickets fechados ficam ocultos para membros comuns;
- qualquer alteração estrutural futura deve ter alvo, hierarquia, snapshot e
  registro.

## Produção no ACLClouds

A raiz do serviço mantém somente os itens necessários para iniciar a aplicação:

- `bot.py`: inicializador compatível da hospedagem;
- `requirements.txt`: dependências instaladas pelo provedor;
- `peace-deploy-20261102-0606/`: versão publicada, com `bot/`, `assets/` e
  `docs/`;
- `releases/`: pacotes de distribuição e rollback, fora do caminho de execução.

`__pycache__/` e `.deps/` são diretórios gerados pelo próprio ACLClouds e não
fazem parte da fonte de verdade. O token fica somente no campo protegido do
provedor; nunca deve ser colocado dentro da árvore publicada.

Na auditoria de 2 de novembro de 2026, todos os membros humanos já possuíam
algum cargo customizado. O bot também mantém a reconciliação de `Visitante` no
`on_member_join` e no `on_ready`: membro humano sem `Peace` recebe `Visitante`,
e membro aprovado como `Peace` deixa de ser visitante.

## Próximas verificações

1. conferir no servidor real uma entrevista de player e uma simulação de dev;
2. testar o honeypot com uma conta de teste que possa receber timeout;
3. validar que o bot mantém somente um painel em `boas-vindas` e um em
   `spam-control`;
4. revisar as permissões efetivas de `Gerência`, `Staff Peace` e `Recrutador`;
5. adicionar testes automatizados para permissões, migrações e persistência.
