# 10 — Etapas para construir a Central (ordem sugerida)

## Etapa 0 — Definições e protótipo de risco
- Documentador e líder técnico definem papéis, restrições dos clientes, tipos de projeto, políticas de revisão e backlog.
- Provar tecnicamente um gateway de patches com revisões/hashes e dois agentes simulados, com bloqueio da mesma lógica.
- Testar fechamento durante patch, queda de rede e recuperação. **Não investir primeiro em dashboard decorativo.**

## Etapa 1 — Base confiável
- Login/convite, aprovação/Discord OAuth, vínculo de membros, permissões de projetos e trilha de auditoria.
- Cadastro de projetos/alias, aberto/fechado e documentação vinculada; importação de ZIP e repositório Git.
- Tarefas com responsáveis, prioridades, bloqueios, critérios e dependências.

## Etapa 2 — Workspace vivo
- Gateway central de alterações, revisionamento, snapshots, reservas semânticas/arquivos, locks com TTL, workspaces locais sincronizados.
- Árvore de projeto, diff e atividade real; teste com agentes simulados e Git.
- Recuperação/reconciliação após desconexão, qualidade de sincronização, backups.

## Etapa 3 — Primeiras IAs e conversas
- Adaptador Codex documentado; depois Claude e outros conectores, com capacidades declaradas.
- Seleção de projeto por nome, leitura do planejamento, escolha/reserva de tarefa.
- Threads por projeto/tarefa, menções entre IAs, pedidos de API, contratos versionados e notificações.

## Etapa 4 — Entregas oficiais
- Criar candidato imutável, rodar CI, anexar evidências, revisão humana/IA autorizada conforme risco.
- Integrar com proteção real de `master`, reversão, releases e deploy separado com trilha de aprovação.
- Provar que mudanças pequenas não publicam automaticamente e que uma IA não consegue se autoaprovar.

## Etapa 5 — Operação e crescimento
- Dashboard: entrega, qualidade, filas, gargalos; definir retenção de dados e privacidade.
- Observabilidade, alertas, limites, backup/restauração, replicação, análise de custos.
- Suporte multi-equipes e clientes, políticas por repositório, administradores específicos e expansão de vagas.

## Gate de cada etapa
Para seguir adiante: demo real gravada, testes automatizados reproduzíveis, problemas conhecidos publicados, responsáveis definidos, dados de desempenho medidos e plano de recuperação verificado. Não declarar pronto com base apenas em protótipo visual.
