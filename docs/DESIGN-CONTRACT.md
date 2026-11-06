# Contrato de design — Central Colaborativa v1.1

Status: contrato de domínio e base de acessibilidade; a revisão visual vigente está em `docs/DESIGN-DECISIONS-2026-11-04.md`
Responsável pela decisão: implementação da Fase 1, sujeita à validação humana posterior
Data: 2026-11-04

> Nota de precedência: o adendo de decisões acima governa o shell/Home redesenhado nesta data. As seções de Pulso, workspace e governança abaixo continuam válidas para o detalhe do projeto e para o domínio futuro; não devem reintroduzir Linha de Contexto, Sequência observável ou Agentes e estados na Home.

## Evidência adicional e decisão de redesign

A avaliação humana registrada em `artifacts/qa-screens/HUMAN-REVIEW-2026-11-04.md` reconheceu a organização, mas pediu menos texto e mais representação visual: agentes trabalhando em sequência observável, tarefas específicas, discussões com menções e referências, workspace com arquivos, commits titulados, tags e releases. A revisão independente da arquitetura confirmou que o modelo anterior não possuía identidade/ordenação de eventos, árvore de arquivos nem destinos para referências.

Decisão: a assinatura “Linha de Contexto” permanece como orientação, mas a superfície principal do projeto passa a ser o **Pulso local**. Ele exibe agentes, tarefa, área lógica, operação e resultado em uma sequência manual e determinística. O usuário avança cada evento pelo botão `Avançar simulação`; isso não é streaming real, presença online, sincronização ou atividade externa.

Escopo permitido nesta revisão: fixtures locais em memória para arquivos, commits técnicos titulados, tags, releases, referências de discussão e eventos de stream. Cada item terá origem e estado explícitos. O projeto não terá Git, servidor, CI, WebSocket, Discord, Codex ou Claude conectados; releases/tags/commits são registros de demonstração local e não produzem deploy.

## Limite de evidência

Este contrato separa o que a documentação autoriza do que é interpretação visual. As superfícies de catálogo, Pulso manual, workspace e governança continuam sendo WPF/.NET 8 com `CentralStore` em memória e fixtures locais; elas não são convertidas em dados remotos por aparência. Em paralelo, a vertical slice de pasta compartilhada usa o `CentralSyncRuntime` com Syncthing, Supabase Auth/PostgreSQL/Realtime e estado de conexão explícito. Discord, Codex, Claude, Git, CI e deploy continuam fora do escopo.

Fontes principais usadas:

- `docs/plan/04-central.md`: navegação, coordenação, planejamento, reservas e telemetria observável.
- `docs/plan/07-collaboration.md`: claims, revisão-base, eventos, sessões e reconciliação.
- `docs/plan/08-security.md`: permissões por membro/projeto/tarefa/recurso e limites de aprovação.
- `docs/plan/09-operations.md`: métricas permitidas, auditoria, publicação e rollback.
- `docs/plan/10-roadmap.md`: priorizar o núcleo de coordenação antes de dashboard decorativo.
- `docs/plan/11-acceptance.md`: isolamento, estados, concorrência e validação.
- `docs/plan/13-catalog.md`: seleção por ID, contexto, ciclo de vida e bloqueio de escrita em projeto fechado.
- `docs/plan/14-approval.md`: edição local, workspace vivo, entrega aprovada, integração e publicação como conceitos distintos.
- `docs/plan/15-protocol.md`: eventos observáveis e sem raciocínio privado.

## Jobs primários

1. Identificar o projeto correto e recuperar contexto sem escolher por nome ambíguo.
2. Encontrar a próxima tarefa pronta, compatível e não bloqueada.
3. Ver reservas de tarefa, lógica, caminho físico e dependências antes de escrever.
4. Entender a revisão atual, a base, os bloqueios e o próximo gate.
5. Conversar sobre contrato/integração sem confundir pedido com resposta ou permissão.
6. Inspecionar evidências e revisão sem confundir aprovação com integração ou publicação.
7. Consultar pessoas, sessões e governança global sem transformar presença em produtividade.

Frequência real não é mensurável nesta fase: os dados são fixtures locais. As frequências acima são prioridades estruturais do protocolo, não telemetria de uso.

## Conteúdo autorizado e ações

Autorizado na Fase 1:

- navegar por Home, Projetos e o projeto explicitamente selecionado; configurações locais ficam no diálogo da engrenagem;
- selecionar projeto, visualizar ciclo de vida, tarefas, reservas simuladas, workspace simulado, discussões, entregas, qualidade, publicações e histórico;
- executar somente simulações locais já suportadas pelo `CentralStore`, sempre com rótulo de simulação;
- mostrar fonte, revisão, timestamp/frescor quando o dado existir; quando não existir, dizer que o indicador é local/simulado;
- bloquear visualmente ações incompatíveis com projeto fechado, estado da entrega ou falta de evidência.

Não autorizado:

- alegar integração real, sincronização, segurança operacional, CI, Git, deploy, aprovação humana ou presença online real;
- mostrar raciocínio privado, tokens, tempo conectado ou atividade como produtividade;
- inventar ACL, aliases, fonte de eventos, stale threshold, reconexão ou garantia de entrega;
- oferecer “aprovar”, “integrar master” ou “publicar” como se produzissem efeito externo.

## Hipótese de informação e navegação

Hipótese: a Central é uma fila de decisões ancorada em contexto, não um painel de contagens. A primeira resposta da interface deve ser: “em qual projeto estou, qual decisão pode avançar, o que bloqueia e qual é a próxima ação permitida?”.

Navegação global vigente:

- **Home**: contexto sem projeto ou triagem do projeto já escolhido; uso técnico e request logs permanecem honestos quando não há gateway.
- **Projetos**: catálogo, busca inequívoca, ciclo de vida e escolha explícita.
- **Projeto selecionado**: acesso contextual aos quatro modos canônicos; pessoas/sessões e configurações não competem como destinos globais.

Dentro do projeto:

- **Operar**: próximo passo, bloqueios e ação permitida.
- **Workspace**: tarefas, dependências, reservas, arquivos, pulso local, commits, tags e releases.
- **Coordenação**: discussões locais, contratos e referências.
- **Provar**: qualidade, evidências, entregas e estados de publicação.

`Planejar`, `Publicar`, `Pessoas e sessões` e `Contexto` não são destinos equivalentes no shell atual. Seus objetos continuam acessíveis no modo canônico em que podem ser entendidos.

## Assinatura visual do detalhe: Pulso local

Gancho: **Contexto certo. Próximo passo claro.**

O antigo conceito de Linha de Contexto não é uma faixa da Home nem um destino de navegação. No detalhe, o Pulso local mostra eventos observáveis sem afirmar execução externa. Ele não é um progresso genérico nem um ticker.

### Pulso local

O Pulso local é a representação visual prioritária da atividade autorizada. Cada evento mostra:

`evento + sequência → agente/provedor → tarefa → arquivo/recurso → operação → resultado`

Eventos futuros ficam em uma fila manual; avançar a simulação revela um evento por vez, seleciona seu detalhe e atualiza a atividade local sem auto-rolagem. A lista mantém identidade e sequência para que repetição, inspeção e origem não sejam confundidas com um stream externo.

O workspace usa uma composição mestre-detalhe: árvore de arquivos à esquerda, stream no centro e detalhe selecionado à direita. Abaixo do stream ficam commits técnicos locais com título, tags e releases locais. Referências resolvíveis aparecem como chips acionáveis; referências sem objeto modelado continuam visíveis, mas desabilitadas e rotuladas como indisponíveis nesta simulação.

Exceções têm precedência visual sobre a lista: projeto fechado, dependência bloqueada, sessão offline, fonte indisponível, revisão obsoleta, evidência ausente e erro devem aparecer acima/com destaque textual. O usuário deve entender o bloqueio antes de perceber a sequência.

## Modelo de estado e confiança

Cada região deve distinguir, sempre que aplicável:

- estado de negócio: aberto, fechado, em revisão, aprovado, pendente;
- disponibilidade: local, conectado, offline, stale, fonte desconhecida;
- resultado: pass, fail, erro de execução, não executado;
- fonte/frescor: simulação local, observação e momento; sem “ao vivo” sem stream real;
- permissão: permitido, leitura, negado ou bloqueado por ciclo de vida.

Matriz mínima:

| Região | Estado local honesto |
|---|---|
| Projeto | aberto / fechando / fechado / reabrindo; fechado continua legível e bloqueia escrita |
| Tarefa | pronta / reservada / em andamento / em revisão / bloqueada / concluída / cancelada |
| Workspace | revisão simulada; patch local pendente/aplicado; sem arquivo real alterado |
| Discussão | persistida localmente, pendente, negada ou erro; nunca resposta inventada |
| Entrega | rascunho/preparada/em revisão/aprovada localmente; integração externa não confirmada |
| Qualidade | PASS/FAIL/PENDENTE/STALE/ERRO; execução separada do resultado |
| Sessão | observável local, desconectada, pendente; sem inferência de produtividade |

## Tokens visuais

Valores semânticos iniciais, sujeitos a teste de contraste:

- canvas `#0E1216`;
- surface `#151B20`;
- surface elevada `#1C252C`;
- border/divider `#2A353D`;
- texto principal `#F3F6F7`;
- texto secundário `#A9B3BD`;
- ação/foco `#D8FF63`;
- informação `#7EA9FF`;
- sucesso/verificado `#42D6AE`;
- atenção/pendente `#F2B660`;
- erro/negado `#F17E86`;
- indisponível `#8D9AAD`.

A cor de ação não significa sucesso. Cada estado terá rótulo e/ou ícone/forma além da cor. O texto usará Segoe UI existente, com papéis display 32/40, título 20/28, corpo 14/21, rótulo 11/14 e números/revisão 24/30. Espaçamento base: 8 px; poucos níveis de superfície; sem sombra ornamental.

## Comportamento compacto

- Na largura mínima suportada, cabeçalho do projeto usa colunas explícitas e pode quebrar em duas linhas; nunca sobrepõe título, badge e ação.
- A navegação de projeto reduz visualmente os grupos e permite rolagem horizontal localizada das guias, sem clipping de texto.
- Conteúdo principal conserva ordem de leitura; listas não forçam rolagem horizontal da janela.
- Textos longos e escala de 125–200% devem manter identificação do estado e ação.
- Listas futuras de eventos devem agrupar atualizações (“N novas atualizações”), preservar foco e permitir pausa/inspeção.
- No workspace, a árvore, o stream e o detalhe podem empilhar em largura compacta; a rolagem horizontal fica contida somente no painel de código/manifesto quando o conteúdo exigir duas dimensões.
- O botão de avanço é uma ação manual e permanece próximo ao estado do Pulso; ele não inicia timer, loop ou auto-scroll.

## Acessibilidade

- Moldura e controles de janela terão nomes acessíveis explícitos ou moldura nativa preservada.
- Todo campo tem rótulo visível ou `AutomationProperties.Name`; tooltip não é o único nome.
- Navegação atual expõe estado semântico, não apenas cor.
- Foco visível em botões, abas, campos e controles desabilitados com explicação.
- Ações de alto risco pedem confirmação e motivo quando suportadas pelo domínio.
- Mensagens importantes não desaparecem apenas por timeout e podem ser lidas por tecnologia assistiva.
- Teclado completo: Tab/Shift+Tab, Enter/Space, setas de guias, Escape em overlays; foco retorna ao acionador.
- Contraste visível, estados não dependentes de cor e modo de movimento reduzido.

## Motion

Sem loops, pulsos ou ticker. Permitidas somente transições curtas (aprox. 150–180 ms) de opacidade/transform para seleção, orientação e abertura de contexto. Movimento reduzido remove a transição sem remover o estado. Atualização de atividade não reordena nem faz auto-rolagem da lista.

## Decisões abertas

- fonte real de dados, autenticação, ACL, cadência/frescor e reconexão;
- contratos de evento, releases, deployments, auditoria persistente e integrações;
- alias oficial e resolução de ambiguidades;
- desenho final da visão global Trabalho/Governança;
- auditoria automatizada com Accessibility Insights/Inspect e teste de carga com nove sessões.

Enquanto abertas, essas áreas permanecem rotuladas como futuras/desconectadas e não autorizam novos comportamentos.

## Plano de validação e checks falsificáveis

1. `dotnet build` Release sem warnings/erros.
2. Testes xUnit existentes e novos checks de identidade/ordenação do Pulso, seleção de arquivos, criação local de tags/releases e bloqueio por ciclo de vida.
3. Inspeção visual da instalação em dashboard, catálogo, detalhe, planejamento, workspace, discussões, entregas, qualidade, publicações, histórico, equipe e configurações.
4. Cenário sem resultado de busca: contagem e estado vazio corretos.
5. Cenário fechado: leitura continua; reservar, patch, aprovação, integração e publicação ficam bloqueados/explicados.
6. Cenário pendente/offline/stale: sem pontos verdes falsos, sem resposta inventada e sem garantia externa.
7. Teste de tecla, foco, nomes acessíveis e largura compacta/escala ampliada.
8. Teste de reação: avançar o Pulso, selecionar agente/evento/tarefa/arquivo, abrir uma referência, ver o título do commit e distinguir tag/release local de publicação. Em até cinco segundos, identificar projeto, bloqueio, ação permitida e gate seguinte. Se a pessoa repetir a sequência visual mas errar a exceção, o Pulso local falhou.
9. Não alegar auditoria de leitor de tela/performance de produção sem ferramenta e fonte correspondentes.

## Critérios de conclusão

O redesign só é considerado melhor quando reduz os sinais enganosos encontrados na inspeção: `LOCAL · SEGURO`, estados todos verdes, binding literal de risco, ações incompatíveis habilitadas, busca sem estado vazio, títulos sem contraste, cabeçalho/abas quebrando e campos sem nome. O instalador final deve conter a mesma honestidade da fonte e continuar compilado/navegável.

---

## Contrato vigente de navegação — bancada de coordenação de IA

Esta seção supersede a hipótese de sete abas equivalentes descrita acima. A alteração foi autorizada pelo responsável do produto após a avaliação humana de 04/11/2026 e está registrada integralmente em `docs/DESIGN-DECISIONS-2026-11-04.md`.

### Job central

Uma pessoa deve conseguir escolher o projeto correto, entender a próxima decisão permitida, inspecionar o artefato e o trabalho de humanos/IAs, conversar sobre a decisão e comprovar o resultado sem perder o contexto. A Central é uma bancada de coordenação, não um painel de contagens nem um gerenciador genérico de módulos.

### Rotas canônicas

- **Home:** contexto global compacto. Mostra um foco explicitamente selecionado ou uma indicação clara de que nenhum foco foi escolhido, uso técnico de IA e request logs sem inventar fonte ou contagens agregadas sem objeto.
- **Projetos:** catálogo e resolução inequívoca de identidade. Entrar em um projeto exige seleção explícita.
- **Projeto / Operar:** próximo passo, bloqueios, revisão atual e ação permitida. Não é o dono da árvore de arquivos.
- **Projeto / Workspace:** dono canônico de tarefas, critérios, dependências, reservas, árvore de arquivos, README quando existir no manifesto, Pulso local, commits, tags e releases.
- **Projeto / Coordenação:** chat local com threads, menções e referências a objetos conhecidos. Tipos de pedido, contrato e integração continuam visíveis dentro da conversa.
- **Projeto / Provar:** entregas, checks, histórico e estados de publicação. `release local`, `integração local`, `aprovação local` e `deploy não conectado` nunca são colapsados em “publicado”.

`Planejar`, `Publicar` e `Contexto` não são destinos de primeiro nível nesta revisão. Seus objetos não foram apagados: tarefas/reservas vivem no Workspace; histórico vive no stream/Provar; publicação vive como estado explícito dentro de Provar.

### Contrato de destino de referências

O destino deve ser semântico e independente da ordem visual dos controles:

| Referência | Destino canônico | Resultado mínimo |
|---|---|---|
| tarefa, dependência, critério | Workspace | item selecionado e contexto da reserva visível |
| arquivo, linha, commit, evento, tag, release | Workspace | inspetor selecionado e origem local visível |
| entrega, check, revisão, estado de publicação | Provar | item selecionado e gate distinguido |
| pessoa, agente, sessão | Coordenação/Workspace | identidade e disponibilidade explicitamente modeladas ou “sem detalhe nesta fase” |

### Superfície visual

O projeto usa uma única bancada por modo, com divisórias e linhas selecionáveis; não usa um card separado para cada dado. A árvore, o conteúdo e o inspetor permanecem em painéis funcionais. Em largura compacta, a ordem de leitura é preservada, o inspetor empilha e ações de entrega descem para uma faixa própria em vez de sair da viewport.

### Estados e honestidade

O contrato continua proibindo inventar presença, produtividade, tokens, streaming, Git, CI ou publicação. Quando o gateway não existir, usage e request logs mostram `N/D`/vazio com a fonte ausente. `0` só pode aparecer quando zero foi medido por uma fonte real. Um estado local deve dizer `local`, `pendente`, `não conectado` ou equivalente.

### Navegação compacta

O shell inicia com rail recolhida por padrão, mas o botão de reabrir e o contexto da página permanecem acessíveis por nome e foco. Ao expandir, marca e perfil reaparecem. A largura mínima suportada segue 820×560; a bancada empilha painéis quando a largura não sustenta colunas legíveis. A Home inicia sem projeto em foco: nenhuma fixture é escolhida silenciosamente; o usuário resolve a identidade no catálogo.

## Adendo de precisão — Cursor de Contexto

O antigo banner de contexto do detalhe foi deliberadamente substituído por um estado inline no cabeçalho (`fixture local · gateway ausente`). A informação não foi removida; sua superfície foi reduzida para que o projeto e a próxima decisão tenham precedência visual.

O contraexemplo rejeitado é uma sala de controle com cartões repetidos, estados verdes e movimento contínuo. Isso seria chamativo, mas não seria a Central: confundiria ausência de fonte com produtividade e obrigaria a pessoa a memorizar módulos. A gramática vigente é um **C aberto voltado para o próximo passo** — contexto delimitado, passagem clara e nenhum significado de sucesso/presença embutido no logo.

No Workspace, a ordem compacta é arquivos → inspetor → metadados/colaboradores → tarefas → commits → Pulso. O catálogo usa linhas com logos locais normalizadas e destinos explícitos. Referências devem selecionar o objeto canônico; um toast sem seleção é falha de comportamento.

A métrica `N/D` permanece distinta de zero medido. Em estado sem gateway, o gráfico não mostra escala numérica que possa ser lida como medição, eixos ou legenda; request logs removem cabeçalho/viewport de tabela e mantêm apenas o vazio compacto.
