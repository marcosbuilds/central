# 04 — Especificação funcional da Central

## O problema que a Central resolve
Nove pessoas em computadores diferentes usam ferramentas, repos, IAs e mensagens diferentes. Sem visão compartilhada, duas pessoas podem pegar o mesmo trabalho, IAs alterar arquivos sobrepostos, revisões serem esquecidas, mudanças alcançarem produção sem controle e ninguém saber por que uma decisão foi tomada.

**Solução proposta:** uma aplicação interna que centraliza identidade, projetos, tarefas, informações, atividade autorizada de agentes, revisão, qualidade e publicação — com um workspace central vivo, revisão de mudanças e Git para conservar o histórico das versões oficiais.

## Visão de navegação
```
Central
├── Início / Dashboard
├── Projetos (catálogo, busca por nome, status aberto/fechado)
│   ├── Visão geral
│   ├── Planejamento (escopo, etapas, tarefas, dependências)
│   ├── Workspace (versão compartilhada ao vivo, árvore, áreas reservadas, diff e atividade)
│   ├── Discussões / Integrações (pessoas, IAs, contratos, perguntas)
│   ├── Entregas / Revisões (evidências, aprovações, master)
│   ├── Qualidade (testes, falhas, cobertura quando disponível)
│   ├── Publicações (prévia, homologação, produção, logs)
│   ├── Documentação / Decisões
│   ├── Fechar/Reabrir (controle de alterações e versão congelada)
│   └── Histórico / Auditoria
├── Atividade das IAs e conexões locais
├── Pessoas / Equipes / Convites
└── Configurações / Segurança / Integrações
```

## Módulo A — cadastro, convite, Discord e liberação
**Fluxo:** administrador gera convite de uso único e validade curta → pessoa cria conta ou acessa com Discord OAuth2 → Central compara identidade e convite → status `PENDENTE` → administrador/bot autorizado libera → conceder papel na Central e cargo apropriado no servidor Discord → sessão ativa com acesso aos projetos permitidos.

**Detalhes:** o bot do Discord integra comunidade, liberação e avisos, mas **não é a fonte única de segurança da Central**. Remoção no Discord pode acionar revisão/suspensão, conforme política explícita. Usar OAuth2 `identify`; `guilds.join` apenas com consentimento se for entrar automaticamente no servidor. Cargos e bot exigem permissões específicas. Nunca solicitar a senha do Discord.

**Estados de conta:** convidado → cadastrado → pendente → ativo → suspenso/revogado. Revalidação do acesso em todas as APIs e streams, não apenas na tela.

## Módulo B — dashboard com informações úteis
- **Projetos:** ativos, aguardando cliente, em revisão, concluídos e bloqueados.
- **Entregas:** tarefas concluídas com aceitação, tarefas abertas, tempo de espera e prazos.
- **Qualidade:** entregas aprovadas/reprovadas, testes com falha, defeitos reabertos, falhas após publicação.
- **Fluxo:** tarefas bloqueadas, tempo até revisão, tempo até entrega, tempo de recuperação após incidentes.
- **Colaboração de IA:** sessões ativas, tarefas em execução, reservas expirando e possíveis conflitos.
- **Trabalho pessoal:** tarefas sob responsabilidade e próximas revisões; evitar ranking de horas online, número de commits, prompts ou tokens como se fossem produtividade.

Todos os indicadores devem mostrar fonte, período e definição. Não fazer classificação individual automática ou monitoramento invasivo. A equipe deve conhecer e aprovar a política de telemetria.

## Módulo C — planejamento completo
Um projeto possui: problema → escopo → marcos → tarefas → dependências → responsáveis → critérios → riscos → decisões → entregas. Permitir backlog, quadro Kanban, cronograma simples, prioridades, anexos, estimativas, comentários e bloqueios.

Tarefa: título claro; descrição; aceitação; responsável; participantes; status; dependências; módulos/caminhos pretendidos; revisão; risco; prioridade e histórico. Um projeto pode ser selecionado por nome/ID e a IA consulta tarefas e documentação associadas.

Estados: `rascunho`, `pronta`, `reservada`, `em_andamento`, `em_revisao`, `bloqueada`, `concluida`, `cancelada`. 'Concluída' exige evidência e aceite; não basta um agente dizer que terminou.

## Módulo D — workspace compartilhado e vivo
- Uma **versão de trabalho viva** por projeto, identificada por número de revisão; todos veem mudanças confirmadas nessa mesma linha de evolução.
- Cada IA atua em uma tarefa e área lógica reservada (ex.: `auth.register`, `ui.registration`, `api.contract.registration`); a Central impede duas escritas simultâneas sobre a mesma responsabilidade. Reservas de diretórios/arquivos reforçam o bloqueio quando necessário.
- Alterações pequenas entram na área viva após verificação de permissão, revisão-base, integridade do patch e testes mínimos. **Não exigem aprovação da master nem deploy**.
- Antes de aplicar um lote, o gateway confere revisão-base, hashes, reservas, status aberto do projeto, dependências e permissões. Aceita atomicamente ou rejeita; nunca confia somente no prompt da IA.
- A árvore mostra quem está trabalhando, IA, tarefa, contrato afetado, últimas revisões e conflitos. Mensagens e discussões podem ser vinculadas a qualquer parte da árvore.
- Uma cópia estável aprovada fica separada: conteúdo ainda em trabalho não muda produção.
- Streaming mostra eventos observáveis; qualquer agente sem adaptador confiável pode ser limitado a leitura/proposta.

## Módulo E — discussões por projeto e cooperação entre IAs
- Canal geral de projeto, discussões por tarefa/módulo/arquivo/rota, respostas em threads, menções a pessoas e IAs, recibo de leitura, busca e histórico.
- Mensagens estruturadas: pergunta, pedido de contrato, proposta de mudança, decisão, dúvida bloqueante, confirmação, evidência, comentário de revisão.
- IA frontend pode solicitar contrato à IA backend. A central cria `integration_request`, relaciona consumidor/provedor, avisa a sessão de IA responsável, preserva mensagens e contrato versionado; quando ela estiver offline, cria pendência.
- Contratos de API incluem método/rota, autenticação, campos, exemplos, respostas de sucesso/erro, versão e status (`proposto`, `acordado`, `implementado`, `testado`, `obsoleto`). Mudança de contrato acordado notifica dependentes e exige confirmação/validação.
- Nenhuma IA pode se comprometer em nome do cliente, mudar requisito comercial ou autorizar acesso a segredos apenas por mensagem.

## Módulo F — entregas, histórico e revisões
- Edições vivas são `change_sets` auditáveis e recuperáveis. Histórico técnico pode persistir snapshots/commits internos sem incomodar usuários com revisão a cada linha.
- `Entrega para aprovação` reúne uma mudança coerente (grande ou pequena mas arriscada), com diff, módulos, motivo, autoria, testes, impacto, contratos e plano de recuperação.
- Fluxo: preparar → validar automaticamente → revisão independente → aprovar/reprovar/pedir correção → integrar à `master` → publicar quando autorizado.
- Revisor pode ser **humano** ou **IA especializada delegada** com escopo explícito, identidade própria e provas anexadas; nunca o próprio autor ou a IA autora, nem aprovação sem evidências.
- Mudanças de alto risco (autenticação, financeiro, acesso, dados críticos, infraestrutura, mudanças incompatíveis) exigem ao menos uma aprovação humana, inclusive se uma IA revisou. O responsável do projeto escolhe políticas mais rigorosas.
- Provas: testes reproduzíveis (com comandos, logs redigidos, resultado, versão e hash), validação de contrato, verificação de segurança e explicação do diff; se faltam, resultado `inconclusivo` e a entrega não avança.
- Os mecanismos reais de proteção de branch do provedor de Git devem ser mantidos; a decisão da Central não substitui automaticamente revisão exigida pelo GitHub.

## Módulo F.1 — agentes, tokens, acesso a projetos
- Cada integrante registra um token da Central para uso em Codex/Claude Code, com permissão separada para ler projetos, atuar em tarefas, propor patches e revisar.
- O agente pode descobrir projetos autorizados pelo nome/alias: `Trabalhe na Seloryn` resolve o cadastro real, recupera documentação, revisão, trabalho em andamento e prioridades. Se ambíguo, pergunta; nunca escolhe projeto fora da lista autorizada.
- Projetos fechados continuam consultáveis por quem pode ler, mas não recebem escrita, tarefa, merge ou deploy. Fechamento cancela novas autorizações e invalida reservas de escrita; operações em voo devem revalidar estado.
- Cada conector local informa eventos observáveis e envia patches por gateway. O token da Central não é uma chave de API da OpenAI/Anthropic e não dá acesso gratuito a esses serviços.

## Módulo G — deploys e stream de logs
- Prévia opcional de change_set/entrega → testes → ambiente de homologação → solicitação de produção → aprovação por responsável autorizado → publicação → checagem de saúde/rollback.
- Acompanhar logs do pipeline em tempo real, com limpeza de segredos; falhas, versão, autor, commit e ambiente.
- Separar 'stream de execução do agente' de 'stream de deploy': são eventos diferentes com controles diferentes.
- Produção nunca deve ser um botão liberado a qualquer token de IA; projeto fechado bloqueia **novos deploys** (com exceção de recuperação emergencial formalmente autorizada, se a política permitir).

## Módulo H — documentação viva
- Requisitos e decisões associados ao código e às tarefas.
- Comparar mudanças de escopo e histórico de aprovações.
- Exportar pacotes aprovados em ZIP e importá-los com validação.
- Pesquisa por requisito, tarefa, arquivo e decisão.

## Regras de experiência
- Responsivo desde o início; aplicativo instalável/PWA primeiro, app nativo somente quando houver necessidade comprovada.
- Indicadores de 'ao vivo', 'atualizado há 2 min' e 'desconectado'; não simular atividade.
- Não sobrecarregar a tela com painel de vigilância; preferir foco em projeto/tarefa.
- Mensagens de conflito explicam quem está trabalhando, onde, por quê e alternativas disponíveis.
- Ações destrutivas ou de alto risco exigem confirmação e ficam registradas.

## Adendo de contraexemplo visual — Fase 1 desktop

Esta seção é uma alteração autorizada da hipótese de navegação, não uma revogação das regras de domínio acima. A implementação mostrou que um shell com muitos destinos equivalentes e cartões por módulo faria a pessoa decorar a arquitetura antes de executar o trabalho que a Central deve coordenar.

O contraexemplo decisivo é abrir uma tarefa, descobrir uma dependência em um arquivo, conversar com uma IA sobre o contrato e verificar uma evidência. Se cada etapa muda de módulo e perde o projeto/objeto selecionado, a Central falha no ciclo de coordenação. O desenho visual aprovado para a Fase 1 reduz a troca de contexto:

```text
Home → Projetos → Projeto selecionado
                         ├── Operar       (próxima decisão e bloqueios)
                         ├── Workspace    (tarefas, arquivos e Pulso local)
                         ├── Coordenação  (thread e referências)
                         └── Provar       (evidência, checks e gates)
```

`Planejar`, `Publicar`, `Pessoas e sessões` e `Configurações` não são destinos globais no shell desta fase. Seus objetos não foram apagados: planejamento vive no Workspace, publicação é um estado explícito em Provar, configuração local abre pela engrenagem e fatos de colaboradores aparecem no contexto do Workspace/Coordenação.

O estado vazio também é parte do contrato: a Home não escolhe o primeiro projeto por ordem de fixture; o catálogo resolve o ID. Sem gateway, métricas e logs não recebem valores inventados. Esse recorte torna a Central exclusiva como bancada de coordenação entre pessoas e IAs, em vez de um dashboard genérico de telemetria.

## Módulo I — catálogo, seleção contextual e ciclo de vida
- Projeto com identificador imutável, nome de exibição, apelidos, dono, repositório, versão, equipes, situação e permissões.
- A pessoa pode dizer 'trabalhe na Seloryn'; o agente chama `list_projects`/`resolve_project`, confirma a correspondência, lê o estado e associa a sessão ao identificador exato.
- Nomes ambíguos exigem escolha, não suposição. Ao trocar de projeto, a IA encerra/pausa a reserva anterior, registra o ponto de retomada e abre nova sessão no destino.
- Status do projeto: `ABERTO` → `FECHANDO` → `FECHADO` → `REABRINDO` → `ABERTO`. `ARQUIVADO` é um estado administrativo opcional à parte.
- Fechamento é uma **transação do servidor**: suspende novas tarefas, invalida permissões temporárias e sincronizações atrasadas, registra versão e motivo, bloqueia publicações e notifica conectores. Reabertura exige autorização e nova sincronização.
- Bloqueios devem valer para API, interfaces, WebSocket, jobs, workers, integrações Git e deploy — não apenas para a interface.
- Detalhes e critérios verificáveis em `13-catalog.md`.
