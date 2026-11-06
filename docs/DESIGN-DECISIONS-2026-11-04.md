# Decisões de design — revisão visual da Central

Status: decisão implementada na fonte WPF/.NET 8 e preparada para validação humana  
Data: 2026-11-04  
Escopo: shell desktop, Home, catálogo de projetos, tipografia, responsividade e estados sem gateway

Este documento é o adendo vigente ao `DESIGN-CONTRACT.md`. Ele registra o que foi decidido para a revisão pedida e separa o que já existe no aplicativo do que depende do servidor futuro.

## Direção visual

O gancho da Central é **“contexto certo, próximo passo claro”**. A interface não tenta parecer um feed de atividade nem uma sala de controle cheia de sinais. A Home responde, em ordem, a três perguntas:

1. qual é o uso técnico de IA que pode ser observado;
2. qual projeto merece atenção agora;
3. quais requisições o gateway poderá comprovar quando existir.

O resultado é um dashboard escuro, silencioso e editorial: superfície única para o gráfico, card de projeto à esquerda, gate coerente à direita e request logs abaixo. A densidade vem da hierarquia e da tabela, não de contadores decorativos.

## Decisões implementadas

### Navegação

- “Instalação atual” não faz parte do shell atual.
- “Visão geral” foi substituído por “Home”.
- O menu principal expõe Home, Projetos e o projeto selecionado. Pessoas/sessões e configurações não são destinos de primeiro nível.
- O perfil de Marcos Pereira mantém uma engrenagem; ela abre um diálogo centralizado de configurações visuais, com scrim, borda arredondada e foco contido. `Esc` fecha o diálogo e devolve o foco ao acionador.
- O controle à direita da marca é um vetor de porta com seta. O rail inicia recolhido, oculta integralmente a marca e mantém apenas os ícones; ao expandir, a marca e o perfil reaparecem. A transição é curta e pode ser desativada pelo modo de movimento reduzido.
- A marca da Central é um “C” aberto, sem nome ou logotipo de terceiro.

### Tipografia e assets

- Papéis de título usam `SF Pro Display`/`SF Pro Text` quando a máquina já os possui; o fallback oficial é `Segoe UI Variable`/`Segoe UI`. Não é instalado nem redistribuído um arquivo Apple sem licença.
- Títulos de página e títulos funcionais usam `SF Pro Display`/fallback Segoe; subtítulos, rótulos editoriais e microcopy curta usam Seloryn, empacotada como recurso WPF local a partir do repositório autorizado. IDs, paths, commits e código continuam em Cascadia Mono. Hash do asset validado: `3efcfff21b3fd204ee18378e1353d6b6c22d89dfea28a3734a7db5776981fb80`.
- Cada projeto possui uma marca vetorial própria no catálogo e no card em foco. A marca é parte do modelo local (`LogoPathData`), não um pacote externo nem um cadastro dinâmico.

### Home

- Os dois cards de “modo local” e o botão associado foram removidos.
- “Linha de Contexto”, “Sequência observável” e “Agentes e estados” foram removidos da Home para não competir com a decisão principal. O Pulso local continua disponível no detalhe do projeto, onde a simulação tem contexto e inspeção apropriados.
- O gráfico único é o ponto focal da tela. O seletor oferece 1 dia, 7 dias e 31 dias; o contrato visual reserva séries para duração técnica, tokens e requests. Sem gateway, o estado é explicitamente `N/D`, com fonte ausente e tooltip explicativo. Não há pontos inventados, ranking de pessoas ou inferência de produtividade.
- O card à esquerda mostra somente projeto em foco, marca, nome Seloryn, tier I–V e últimas atividades observáveis, com ação externa para abrir o catálogo/detalhe.
- À direita fica o próximo gate: tarefa, área lógica, dependência e ação permitida. A coluna existe porque ajuda a decidir, não para preencher espaço.
- Request logs seguem a densidade do anexo, mas começam vazios. O cabeçalho informa que conta/chave devem ser mascaradas e que fonte, frescor, modelo, transporte, status e TTFT só aparecem quando medidos pelo gateway.

### Responsividade, contraste e movimento

- A janela preserva largura mínima operável e permite maximizar. Na Home, o card de projeto e o próximo gate empilham antes de ficarem ilegíveis; a tabela de logs mantém rolagem horizontal contida no próprio painel.
- Scrollbars têm thumb escuro e estados hover/drag visíveis; foco, caret e seleção de texto usam tokens claros. Botões de ação verde usam texto escuro (`InkBrush`) para cumprir contraste.
- Não há loop, ticker, pulsação ou auto-scroll. A animação é curta e orienta a navegação. O usuário pode ativar “Reduzir movimento”.

## O que continua deliberadamente indisponível

O dashboard não afirma que Claude, Codex, MCP, Git, CI, WebSocket, PostgreSQL ou gateway já estão conectados. `N/D`, “fonte não conectada” e a ausência de request rows são estados de confiança, não falhas visuais. O plano para transformar esses contratos em streaming real está em `docs/SERVER-PLAN.md`.

## Validação desta revisão

- build Release sem warnings/erros;
- suíte xUnit existente aprovada;
- inspeção da Home em janela normal, compacta e maximizada;
- inspeção do rail expandido/recolhido, painel de configurações, catálogo, foco de busca, scrollbars e estados sem dados;
- verificação de que a publicação e o instalador carregam a fonte Seloryn como recurso embutido.

---

## Segunda decisão — bancada de coordenação de IA (supersede a IA anterior)

Status: decisão de arquitetura visual aprovada para implementação; aceite humano ainda pendente  
Data: 2026-11-04  
Motivo: a avaliação humana e a auditoria de referências públicas reprovaram a Central como um dashboard genérico com muitos destinos equivalentes.

### Evidência externa observada

- Na interface pública de Linear, a navegação lateral é curta e a tela de trabalho concentra um único objeto, sua atividade e a conversa contextual; não há uma grade de cards competindo pela primeira atenção.
- No repositório público do VS Code no GitHub, árvore de arquivos, branch, commit/histórico, README e metadados aparecem no mesmo contexto de repositório; a coluna lateral é contextual, não uma segunda navegação global.
- A pesquisa visual pública no Pinterest foi usada somente como moodboard. Ela confirmou a direção de canvas escuro e superfícies discretas, mas não autorizou copiar componentes nem definir fluxo.

Essas referências são evidência de composição visual, não de permissões, dados ou IA da Central. O domínio continua ancorado na documentação do projeto e nas fixtures locais.

### Contraexemplo que fundamenta a mudança

Se a Central expõe `Operar`, `Planejar`, `Workspace`, `Coordenação`, `Provar`, `Publicar` e `Contexto` como sete destinos equivalentes, a pessoa precisa memorizar a taxonomia antes de conseguir trabalhar. O caso de uso central — entender uma tarefa de IA, inspecionar o artefato, conversar e comprovar o resultado — fica quebrado em telas que repetem o mesmo projeto.

O contraexemplo decisivo é: abrir `TASK-33`, perceber que depende de `ADR-0004`, abrir o arquivo relacionado, perguntar a uma IA na thread e verificar uma evidência. Se cada passo muda de aba e perde o objeto selecionado, a Central falha no trabalho que pretende coordenar. A solução deve reduzir trocas sem colapsar estados distintos.

### Hipótese exclusiva da Central

A Central não é um gerenciador de projetos com muitos módulos. Ela é uma **bancada de coordenação de trabalho entre pessoas e IAs**. O projeto é o limite de contexto; a tarefa e o artefato são os objetos principais; a conversa e a prova fecham o ciclo.

```text
Home
├── triagem global compacta
├── foco selecionado + exceções de outros projetos
├── uso técnico de IA (N/D até gateway)
└── request logs (vazio honesto até gateway)

Projetos
└── resolver identidade e entrar no projeto explícito

Projeto
├── Operar       próximo passo, bloqueio e ação permitida
├── Workspace    tarefas, reservas, arquivos, pulso, commits, tags e releases
├── Coordenação  chat local, contratos e referências
└── Provar       evidências, checks, histórico e estado de publicação
```

### O que sai da navegação principal e onde continua

- `Planejar` deixa de ser uma aba: tarefas, critérios, dependências e reservas vivem no Workspace, junto do arquivo e do trabalho que elas delimitam.
- `Publicar` deixa de ser uma tela: release, integração e deploy aparecem como estados distintos dentro de Provar; nenhum estado local recebe o rótulo de publicação real.
- `Contexto` deixa de ser uma aba: decisões e histórico observável aparecem no stream do Workspace e na linha de evidências do Provar.
- `Operar` não é o dono da árvore de arquivos; ele responde somente “o que pode avançar agora?”. O Workspace é o dono canônico de artefatos, tarefas e eventos.

Esta não é uma remoção estética. É uma alteração deliberada do contrato de navegação para privilegiar a unidade de trabalho específica da Central e manter o conteúdo acessível dentro do contexto correto.

### Regras de interface

- Uma tela de projeto sempre exibe nome, ID, status e revisão no cabeçalho.
- Cada referência resolve por destino semântico (`tarefa`, `arquivo`, `evento`, `tag`, `release`, `entrega`); não se navega por índice de aba.
- O Workspace usa painéis funcionais e linhas selecionáveis, não um card para cada item.
- A Coordenação é visualmente um chat, mas continua declarando `local`, `pendente` ou `indisponível`; não simula streaming.
- Provar distingue `release local`, `integração local`, `aprovada localmente` e `deploy não conectado`.
- A Home destaca somente um foco explicitamente resolvido; sem uma fonte que identifique projeto/objeto, não cria uma faixa de exceções agregadas nem transforma contagens em prioridade.

### Critérios de reprovação da direção

1. Selecionar um projeto e voltar à Home mostrando outro `project_id`.
2. Não encontrar uma tarefa, dependência e critério sem abrir uma sequência de telas sem contexto.
3. Clicar em arquivo, evento, tag ou release e perder a seleção no Workspace.
4. Interpretar release local como deploy por ausência de estado explícito.
5. Ver mais de um destino com a mesma ênfase visual sem explicar seu trabalho.
6. Não conseguir usar rail, diálogo e chat apenas por teclado em 820×560 e 200% de escala.
7. Mostrar `0`, verde ou “ativo” quando a fonte de gateway é ausente.

### Plano de motion e assets

- Rail: transição curta de largura/opacity somente para orientação; estado final permanece compreensível sem motion.
- Diálogo: entrada/saída curta de opacity/scale, scrim estático e `Tab` contido; movimento reduzido remove apenas a transição.
- Ícones de navegação: geometrias locais em grade lógica 24×24, área segura 16×16, stroke consistente e sem Unicode funcional.
- Logo Central: C aberto próprio, separado das logos de projeto; não é um indicador de estado.

### Validação adicional exigida

- checagem de contexto Home → Projetos → Projeto para todos os fixtures;
- UI Automation/foco: rail, diálogo, busca e chat;
- screenshots 820×560, 1024×768, 1440×900 e maximizado;
- inspeção a 125%, 150% e 200% de escala quando disponível;
- estados sem gateway, vazio, parcial e erro sem dados inventados;
- build Release, testes xUnit e testes de comportamento existentes.

---

## Terceira decisão — o Cursor de Contexto

Status: implementada na fonte após revisão adversarial; aceite humano ainda pendente  
Data: 2026-11-04  
Motivo: reduzir a leitura de “dashboard genérico” sem esconder a origem local dos dados.

### Evidência e contraponto

A inspeção da publicação mostrou que a base escura, o rail e os quatro modos já eram coerentes, mas a mesma hierarquia era repetida por faixas, cartões e avisos. O contraexemplo foi uma “sala de controle neon”: muitos cartões, sete destinos equivalentes, estados verdes, stream automático e métricas sem fonte. Ela chamaria atenção, mas contradiz a Central porque faria a pessoa memorizar a taxonomia e poderia confundir fixture com atividade real.

O time de revisão convergiu para um gancho exclusivo da Central: **um C aberto voltado para o próximo passo**. O C não indica sucesso nem presença; indica contexto delimitado com passagem clara para a ação seguinte. A frase de produto permanece **“contexto certo. próximo passo claro.”**

### Aplicação na fonte

- O banner “Contexto local” do detalhe foi removido como superfície independente; a honestidade não foi removida: `fixture local · gateway ausente` aparece inline no cabeçalho do projeto.
- O Workspace concentra a bancada: arquivos, inspetor, tags/releases e colaboradores observáveis; em largura compacta, a ordem vira arquivos → inspetor → metadados → tarefas → commits.
- O catálogo deixou de ser uma pilha de cartões independentes: usa uma moldura de lista com divisórias, logo própria, identidade textual e um único comando de abrir com ícone vetorial.
- A busca usa path vetorial 24×24; não há Unicode funcional em controles.
- Títulos funcionais usam Apple/Segoe; subtítulos e rótulos curtos usam Seloryn; texto técnico usa mono. Isso é uma escolha de função tipográfica, não decoração.
- O gráfico sem gateway não exibe `0`: cada série fica `N/D`, porque ausência não é zero medido.
- A integração de uma entrega só fica habilitada quando a entrega está aprovada localmente e o projeto está aberto. Referências de tarefa, arquivo, revisão, evento, commit, tag, release e entrega selecionam o objeto e levam ao modo canônico.
- A rail inicia realmente em 78 DIP; na forma recolhida o perfil reduz-se à engrenagem, evitando clipping do avatar e do nome.

### Motion decision cards

| Movimento | Propósito | Duração | Sem movimento reduzido |
|---|---|---:|---|
| Rail | orientação espacial entre ícones e rótulos | 170 ms | largura direta, mesmo estado final |
| Seleção/foco | mostrar o objeto atual | curto, sem loop | marcador/contraste persistem |
| Gráfico vazio | feedback de troca de período | 160–180 ms | estado aparece sem fade |

Nenhum desses movimentos afirma streaming, presença ou produtividade. Não há ticker, pulsação, auto-rolagem ou animação decorativa.

### Critérios falsificáveis desta decisão

1. Em `820×560`, o Workspace não pode gerar rolagem horizontal da janela; os painéis devem empilhar na ordem declarada.
2. Clicar em cada tipo de referência deve preservar a identidade do objeto; não é suficiente exibir um toast de “localizado”.
3. Com `RequestLogs` vazio e gateway ausente, não pode existir linha de request nem número `0` apresentado como medição.
4. Com uma entrega em revisão, `Registrar integração` deve estar desabilitado; após aprovação local, habilitar somente com projeto aberto.
5. Recolher o rail deve deixar a engrenagem inteira dentro de sua área; expandir deve restaurar nome e perfil.
6. A leitura da interface deve permitir identificar projeto, bloqueio, próxima ação e gate seguinte em até cinco segundos, sem usar cor como única pista.

### Validação registrada

- Revisão estática independente por arquitetura de informação, visual/interação e acessibilidade/responsividade.
- Build Debug após a alteração: 0 avisos, 0 erros.
- xUnit após a alteração: 12 aprovados.
- A rodada final ainda precisa substituir as capturas antigas e registrar os tamanhos/escala realmente observados; esta pendência não será tratada como aceite visual.

---

## Quarta decisão — identidade explícita antes do foco

Status: implementada na fonte após revisão do contraexemplo; aceite humano ainda pendente  
Data: 2026-11-04  
Motivo: retirar uma escolha silenciosa que contradizia o próprio contrato de resolução de projetos

### Contraexemplo e evidência

O store local iniciava a Home apontando automaticamente para o primeiro item do catálogo e o card de “próxima decisão” lia `Tasks[0]`. Esse atalho parece conveniente em uma captura, mas falha no caso real em que há múltiplos projetos: a pessoa pode interpretar uma fixture arbitrária como seu contexto e uma tarefa em revisão/bloqueada como o próximo passo permitido.

O contraexemplo melhor fundamentado é abrir a Central, ver `Seloryn` por acaso e executar uma ação pensando estar em `Sistema de Vendas`. Isso viola o job primário de resolver identidade e o critério de não misturar `project_id` entre Home, catálogo e detalhe.

### Decisão exclusiva da Central

A Home não escolhe foco por ordem de seed. Ela mostra um estado vazio operacional e um único próximo passo: **resolver o projeto em Projetos**. Depois da seleção explícita, a Home mostra o projeto selecionado e deriva a próxima decisão da primeira tarefa com estado `PRONTA`; se não existir, declara que não há tarefa pronta, sem promover uma tarefa bloqueada ou em revisão a ação recomendada.

Essa regra preserva o gancho do C aberto: o C delimita o contexto depois que ele foi escolhido; ele não inventa contexto.

### Aplicação e checks falsificáveis

- `CentralStore` não preenche `SelectedProject` automaticamente.
- `CentralViewModel.FeaturedProject` é anulável e a Home tem estado `NENHUM PROJETO EM FOCO` com ação para o catálogo.
- `ProjectModel.NextActionableTask` procura somente `PRONTA`; `Tasks[0]` não é mais usado para a decisão da Home.
- A superfície `Operar` usa a mesma propriedade canônica; a tarefa exibida no detalhe não pode divergir da triagem da Home.
- O estado vazio é navegável por teclado e não desabilita o caminho para o catálogo.
- Teste automatizado confirma sessão nova sem projeto, seleção explícita e resolução de `TASK-29` como tarefa pronta.

---

## Quinta decisão — Home honesta antes da triagem

Status: implementada na fonte após revisão adversarial; aceite humano ainda pendente  
Data: 2026-11-04  
Motivo: retirar uma promessa de triagem que não era sustentada quando nenhum projeto estava em foco

### Contraexemplo e evidência

Na captura `14-home-no-focus-0.1.2.png`, a tela sem projeto selecionado se apresenta como `Triagem`, afirma `Um projeto em foco` e mostra `2 bloqueios`/`1 em revisão`. Esses números são agregados locais, mas não identificam projeto, tarefa ou gate. A pessoa consegue abrir Projetos, porém não consegue inspecionar a exceção a partir daquela Home.

O contraexemplo decisivo é perguntar “qual projeto devo abrir agora?” e receber somente contagens agregadas. Chamar isso de triagem sugere uma investigação que a superfície não oferece; aumentar a quantidade de cards ou inventar nomes de projetos resolveria a aparência, mas violaria a fronteira de dados da Fase 1.

### Decisão exclusiva da Central

Sem projeto explícito, a Home é **Contexto**: mostra um único próximo passo, `Abrir projetos`, sem contagens agregadas que não apontem para um objeto. Depois que a pessoa escolhe um projeto, a mesma rota muda para **Triagem**, com foco, próxima tarefa `PRONTA` e resumo do projeto selecionado.

O vazio deixa de ser apenas um componente escondido: estados mutuamente exclusivos não podem aparecer na árvore de UI Automation. A Central mantém o C aberto como marca de passagem, mas não transforma ausência de identidade em prioridade.

### Aplicação e checks falsificáveis

- `HomeTitle` e `HomeSubtitle` mudam conforme `FeaturedProject`; a frase `Um projeto em foco` não aparece sem foco.
- Sem foco, o estado é curto e acionável; não são adicionados nomes, contagens, prioridades ou “próximas ações” inferidas.
- `AutomationStateGrid` e `AutomationStateBorder` usam peers que removem os descendentes da ramificação inativa; a Home não anuncia `FOCO ATUAL`/`PRÓXIMA DECISÃO` quando o estado vazio está ativo, e Projetos não anuncia `Nenhum projeto encontrado` quando há resultados.
- Busca vazia e estado de filtro sem resultados continuam acessíveis e recuperáveis por `Limpar busca`.
- O executável expõe a versão canônica `0.1.2` no assembly, manifesto e instalador.

### Verificação desta decisão

- Build Debug após o patch: 0 avisos, 0 erros.
- UI Automation nativa observada na Home sem foco e no catálogo com três projetos: os rótulos das superfícies inativas não aparecem no `Document text`.
- Estado de busca sem resultados observado com `0 resultado(s)`, painel vazio e `Limpar busca`; o catálogo foi restaurado depois do teste.
- A validação Release, capturas finais por viewport/escala e aceite humano continuam pendentes; esta decisão não os substitui.

---

## Sexta decisão — vazio compacto e estado acessível

Status: implementada na fonte e republicada em `0.1.2`; aceite humano ainda pendente  
Data: 2026-11-04  
Motivo: a inspeção da publicação mostrou que a Home ainda reservava espaço para módulos sem fonte e que ramos colapsados continuavam aparecendo na árvore UI Automation.

### Contraexemplo e evidência

O contraexemplo é uma Home visualmente “completa” porque mantém eixos, legendas, cabeçalho de tabela e um viewport largo mesmo quando não existe gateway. A pessoa vê a forma de um dashboard, mas não recebe uma medição. Isso é pior que um vazio curto: sugere telemetria ausente e aumenta a carga visual sem aumentar a decisão possível.

Na publicação, a mesma regra apareceu em Provar: uma linha fixa de três colunas empurrava ações para fora da viewport compacta. A entrega continuava semanticamente correta, mas a ação desaparecia visualmente — um contraexemplo de responsividade que não pode ser tratado como detalhe de acabamento.

### Decisão exclusiva da Central

Quando a fonte não existe, a Central mostra somente o fato que pode provar: `Sem medição`, período selecionado e `N/D`; eixos numéricos, legenda e tooltip de ponto ficam reservados ao estado medido. Request Logs recolhem o cabeçalho e o viewport da tabela e exibem um vazio curto, sem converter ausência em zero.

Em Provar, cada entrega usa uma leitura em duas camadas: identidade/resumo/status na primeira e ações em uma faixa que pode quebrar na segunda. A ação não depende de uma coluna rígida nem é perdida em largura compacta.

### Aplicação e checks falsificáveis

- `UsageChart` e `RequestTableViewport` removem os ramos inativos da árvore UI Automation; o estado vazio não anuncia `HORA`, `CONTA`, `N/D` de eixo ou `agora`.
- O vazio de logs não força `MinWidth=900` quando não há linhas; a rolagem horizontal permanece confinada à tabela somente quando houver registros reais.
- Provar empilha as ações em `WrapPanel`, mantendo `Registrar integração` desabilitado em entrega em revisão.
- O painel de configurações é uma janela UIA nomeada, centralizada, arredondada, com scrim e retorno de foco ao acionador.
- Botões de ação lima renderizam texto ligado ao `Foreground` do estado do botão; no estado habilitado o texto usa `InkBrush`, e no estado desabilitado usa o texto de indisponibilidade.

### Verificação registrada nesta rodada

- Build Release: 0 avisos, 0 erros.
- xUnit Release: 12 aprovados.
- Publicação self-contained win-x64 e instalador Inno Setup regenerados em `D:\projetos\Central\artifacts`.
- UI Automation observada na Home publicada: somente o estado vazio ativo aparece; eixos do gráfico e cabeçalho/linhas de logs colapsados não aparecem no `Document text`.
- Home, Projetos, Operar, Workspace, Coordenação, Provar e configurações foram percorridos na publicação; Provar foi observado em largura compacta com ações visíveis depois do reflow.
- Escalas de 125–200%, leitor de tela formal e aceite humano continuam não executados; não são inferidos desta rodada.

