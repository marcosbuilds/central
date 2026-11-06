# Adaptação da Peace: comunidade + trabalho

## Decisão de produto

A Peace continua sendo a mesma comunidade: resenha, jogos juntos, calls,
atendimento e tickets. O trabalho de desenvolvimento entra como uma segunda
função, usando a estrutura existente e poucos canais. Não há troca de nome,
marca ou identidade do servidor.

O princípio de governança é separar duas coisas:

- cargo de acesso: controla uma permissão ou uma área;
- cargo visual: organiza a lista de membros e a aparência, sem conceder acesso.

Cargo visual nunca deve aparecer em uma regra de autorização.

## Estado aplicado no servidor

### Raiz pública

- `rules`: permanece no topo e continua público para boas-vindas/regras;
- `spam-control`: canal público de honeypot, também no topo;
- `AFK`: call pública visível, sem permissão de conexão, preservando a função de
  AFK.

### Categorias preservadas e adaptadas

| Área | Canais principais | Regra de uso |
| --- | --- | --- |
| `[🎫] RECEPÇÃO` | `boas-vindas`, `regras`, `pedir-set` | entrada e entrevista inicial |
| `[💻] DEVELOPERS` | `╰💬・chat-dev`, `╭💻・programming` | colaboração do time técnico |
| `[🔔] RESENHA & SOCIAL` | chats sociais e `música` | comunidade e convivência |
| `[☎️] ATENDIMENTO` | painel, espera e suporte | atendimento de jogo, Discord ou trabalho |
| `[🎙️] CALLS` | quatro calls existentes | calls compartilhadas para Peace e desenvolvimento |
| `[🎙️] CALL・PRIVADA` | calls privadas atuais | benefício de booster, sem mistura com dev |
| `[🎟️] TICKETS-FECHADOS` | vazio | arquivo futuro, invisível para membros |
| `[🛡️] STAFF` | `scan-only`, `staff-only`, `logs` | recrutamento e operação interna |

Os IDs existentes foram reaproveitados sempre que isso reduziu risco. A antiga
área Florenza foi reaproveitada internamente para `DEVELOPERS`; a identidade
pública da Peace não foi trocada. O canal de chat virou `╰💬・chat-dev` e a call
virou `╭💻・programming`.

## O que foi retirado

- a categoria `[🔫] AÇÃO` e suas calls específicas do modelo antigo;
- os canais de ticket abertos/fechados que estavam acumulados;
- os registros desses tickets no SQLite, mantendo o banco e o histórico técnico
  do sistema intactos;
- o cargo legado `Florenza Founds`;
- os cargos legados `Advertência I`, `Advertência II`, `Advertência III` e
  `Sublider`;
- a exposição pública do fluxo antigo `programming-only` como builder;
- o uso de `programming-only` como canal de execução estrutural.

Nenhum cargo de `Streamer`, booster, Peace, staff, visitante, elite ou
integração de bot foi removido como parte desta limpeza. `Gerência` foi mantido
como cargo de organização, mas suas permissões globais foram zeradas.

## Matriz de cargos

### Acesso técnico

`Dev` é o cargo técnico que controla o acesso à categoria de Developers. Ele foi
reaproveitado do antigo `Developer`, mas suas
permissões globais amplas foram zeradas. A autorização de área fica nos
overwrites dos canais e categorias, não em `Administrator`, `Manage Guild`,
`Manage Roles` ou `Manage Channels`.

### Identidade visual

Os cargos abaixo têm finalidade visual/organizacional e permissões globais
zeradas:

- `Developer`;
- `Frontend`;
- `Backend`;
- `Documentation`;
- `AI & Bots` — reservado para bots com IA; atualmente usado pelo bot da Peace.

Eles podem dar cor, ordem e identificação. Não podem abrir canais, conceder
cargos, moderar ou alterar a estrutura.

### Cargos preservados

`Peace`, `Novato Peace`, `Staff Peace`, `Gerência`, `Recrutador`, `Elite Peace`,
`Visitante`, `Streamer`, booster e cargos gerenciados por integrações foram
mantidos. Mudanças futuras nesses cargos exigem inventário de membros,
permissões e dependências antes da aplicação.

## Entrada e entrevistas

O painel de `pedir-set` agora oferece três entradas:

1. `Sou player`;
2. `Join Developers`;
3. `Staff — indisponível por hora`.

Quem já tem `Peace` não pode solicitar novamente a entrada de player. A
entrevista inicial do player mantém a coleta in-game solicitada e passa por
aprovação manual.

O fluxo de desenvolvedor é separado em etapas:

1. nome e sobrenome reais, apelido e motivação;
2. área: Frontend, Backend, Documentação ou IA & Bots · Íris;
3. tempo de especialização, experiência anterior e portfólio opcional;
4. envio das respostas para `scan-only`;
5. aprovação ou recusa manual por um recrutador autorizado;
6. após aprovação, seleção de horário no próximo dia útil, entre `06:00–13:00`
   ou `14:00–00:00` no horário de Brasília;
7. DM com o horário marcado; se não puder comparecer, o integrante é orientado
   a abrir um ticket.

O fluxo não concede cargo automaticamente. A integração acontece depois da
reunião e da decisão humana.

### Retorno de membros Peace

Quando um membro sai com `Peace`, o ID não volta imediatamente para o pool: ele
fica reservado para a conta. Se a conta retornar, o bot publica um card no
`scan-only` e não restaura o vínculo sozinho. Um recrutador autorizado pode usar
`Liberar ID`; essa ação libera o ID antigo e registra um novo ID para o retorno
aprovado.

Na STAFF, `scan-only` é acessível somente a `Recrutador`. `staff-only` e `logs`
aceitam somente `Staff Peace`, além do bot; `Gerência` não tem acesso.

## Honeypot de moderação

O canal `spam-control` publica um único embed com asset visual e cards de escopo,
ação, limite e status. Qualquer mensagem enviada por um membro é:

1. apagada imediatamente;
2. registrada no log sem republicar o conteúdo;
3. punida com timeout de sete dias, sem banimento e sem expulsão.

O bot precisa manter `Manage Messages` e `Moderate Members`, e a hierarquia do
bot deve permitir aplicar o timeout. O canal é uma camada específica para
contas que disparam spam em massa; AutoMod nativo continua sendo uma boa camada
complementar para links, menções e padrões de spam.

O embed e `assets/automod.png` são rígidos e não entram na rotação de Halloween.
Halloween fica restrito aos painéis leves de boas-vindas, set, atendimento e
operações.

## Tickets e atendimento

O painel continua em um único canal. As categorias devem tratar tanto a
comunidade quanto o trabalho:

- Comunidade e Discord;
- Trabalho e desenvolvimento;
- Apresentar projeto;
- Ideia ou proposta;
- Privacidade ou moderação;
- Parceria ou contato privado.

`Apresentar projeto` aceita jogo, produto, ferramenta ou ideia. O ticket é
privado; apresentações públicas continuam no espaço social ou em threads quando
isso for adequado. A Íris está desativada por enquanto; tickets abertos ficam
acessíveis à `Staff Peace` e seguem atendimento manual.

## Bots e integrações

Não foi adicionado outro bot de tickets, música, boas-vindas ou moderação. A
Peace já possui bot próprio, Jockie Music, DutiesBot, Medal e TimeCord; cada um
deve manter uma responsabilidade clara. O próximo ganho de integração deve vir
de recursos nativos do Discord e de GitHub para PRs, CI e releases, somente
quando a equipe estiver pronta para operá-los.

## Operação e rollback

- `bot/maintenance.py` aplica a adaptação estrutural em modo seco, normal ou
  com limpeza explícita;
- `bot/snap.py` cria snapshots em `data/snapshots/`;
- `bot/main.py` mantém a sincronização dos painéis, tickets, boosters, Iris
  (desativada por configuração), honeypot e entrevistas;
- qualquer nova limpeza deve ser precedida de snapshot e validação de IDs,
  membros e overwrites.

No ACLClouds, a raiz de produção não deve receber cópias soltas do código. O
entrypoint e as dependências ficam na raiz por exigência do provedor; a versão
executável permanece dentro de uma pasta versionada e os pacotes ficam em
`releases/`. Diretórios como `__pycache__` e `.deps` são gerados pelo ambiente e
podem ser ignorados na revisão da árvore.

Na entrada do servidor, o bot reconcilia `Visitante` para membros humanos sem
`Peace`. A rotina é idempotente: não remove cargos existentes, não atribui
`Visitante` a bots de integração e não reusa IDs de Peace.

O bot deve ser observado após mudanças de permissão. Se uma sincronização falhar
parcialmente, corrigir o alvo exato e repetir a etapa; não recriar a árvore toda.
