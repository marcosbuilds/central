# Iris

## Contexto e privacidade

Iris usa três camadas separadas:

- o ticket atual, para responder ao solicitante;
- canais de gerência, apenas como referência interna de processo e padrão;
- chats públicos e tickets encerrados, anonimizados para entender cultura e dúvidas recorrentes.

Mensagens brutas de chats não são gravadas como memória da Iris. Antes de entrar
no contexto, menções, URLs, e-mails, telefones, tokens e outros identificadores
são removidos. O SQLite registra somente eventos operacionais sem o conteúdo da
conversa, como abertura, claim, resposta e escalonamento.

Informação de gerência nunca deve ser citada para um usuário. Informação antiga
é uma referência, não uma regra atual: estado verificado do Discord sempre vence
histórico.

## Atendimento

Iris responde quando um ticket é aberto e acompanha mensagens do solicitante.
Depois que um staff assume, Iris fica silenciosa por padrão e só responde se for
mencionada. Se o ticket ficar sem atendimento, ela envia um PV ao responsável ou
a membros online da staff e registra o escalonamento.

As respostas da Iris são publicadas como texto normal, com indicador de digitação
durante o processamento; não usam card, título técnico ou menção repetida ao
solicitante. A regra Humanizer da Iris prioriza palavras comuns, frases curtas,
resposta direta ao último ponto e uma pergunta por vez. Ela não repete a resposta
do usuário, não explica o próprio processo e não revela score, histórico interno
ou critérios de avaliação. Mensagens fixas de painel, abertura, controles e encerramento usam
embeds com a identidade visual da Peace. Os controles ficam no próprio ticket em
uma única mensagem exclusiva da staff; o solicitante não recebe botões. O callback
valida a permissão da staff e o canal `staff-only` não recebe painéis de ticket.

Tickets encerrados ficam invisíveis para o solicitante e para a staff. A Iris pode
consultar o histórico encerrado em contexto anonimizado para comparar atendimentos,
calcular afinidade de suporte e encaminhar ao staff mais adequado; se não houver
evidência suficiente, menciona o cargo da staff e não inventa um responsável.

Pedidos de set entram como pendentes no `scan-only`. O cargo só é aplicado depois
da aprovação manual de um recrutador ou do recrutador selecionado pelo solicitante.

Reports são organizados sem declarar culpa. Projetos, ideias e propostas são
desenvolvidos como conversa, sem transformar a interação em formulário.

## Programação

Na área de desenvolvimento, a staff menciona Iris e descreve a ideia em linguagem
normal. Iris prepara plano, impacto, permissões, riscos e validação. Se faltar
informação, menciona o autor e pergunta o que precisa saber.

Antes de sugerir criação, Iris consulta categorias, canais e cargos existentes.
Consultas de estado, como "como está a categoria", retornam o estado verificado
sem criar ou editar nada. Quando já existe um objeto, ela propõe editar o atual
ou pergunta se deve criar outro.

Alterações estruturais ficam pendentes até uma confirmação natural do autor.
Remover Peace, apagar cargo, apagar canal ou apagar categoria exige autoridade
compatível e confirmação explícita. A Iris só edita, move ou apaga cargos, canais
e categorias registrados como criados por ela; para objetos externos, pede que a
alteração seja solicitada a quem criou ou fez a última edição. A Iris nunca trata
uma sugestão como execução.

Consultas de membros, cargos, canais e permissões usam o estado atual do Discord e
não passam por adivinhação do modelo. Punições pela área de desenvolvimento exigem alvo
por ID ou menção exata, motivo e confirmação. Timeout e advertência exigem staff;
expulsão e banimento exigem fundador, administrador ou `Gerenciar servidor`, além
de hierarquia compatível. A Iris registra a ação e nunca pune o fundador, o bot,
quem fez o pedido ou um membro acima da hierarquia do bot.

Solicitações de dev, streamer, recrutador ou outra função passam por entrevista
rígida no ticket e nunca recebem cargo por esse fluxo. Na área de desenvolvimento, somente
um dev autorizado pode aplicar um cargo com alvo e confirmação exatos; o score de
histórico e sinais de risco bloqueia operações quando não houver confiança suficiente.
Tags Peace seguem o padrão `N/D/S/R/G/F ⎰ nome id`, conforme a função principal.

Boosters recebem automaticamente cargo e call privada própria no meio da categoria
de calls privadas, nomeada `├🎧・username`. O booster pode adicionar/remover pessoas
do cargo privado e puxá-las ou removê-las da call; a Iris pode explicar o benefício,
mas não concede o cargo por conversa.

## Configuração atual

- Gerência: `1460526534527025208` e `1491899123547242656`
- Controles privados da staff: `1491899123547242656`
- Chat geral e demais chats: configurados em `IRIS_GENERAL_CHANNEL_IDS` e
  descobertos automaticamente quando pertencem à área de resenha/social.
- Tickets anteriores: categoria `1495064004194861137`
- Planejamento: `1555060813046226964`
