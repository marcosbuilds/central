# Plano de testes e verificação

## Automatizado

Executado em 04/11/2026 com .NET SDK 8.0.427:

- Build da solução: aprovado, 0 avisos, 0 erros.
- Testes xUnit: 12 aprovados na rodada final, incluindo as verificações de referência, foco explícito e reflow abaixo.
- Casos: seleção autorizada; conflito semântico e trabalho independente; base obsoleta; fechamento/reabertura; aprovação com evidência separada de integração; equipe com nove pessoas e agente offline; Pulso local ordenado; patch com commit técnico/tags/releases locais; bloqueio de ações de versionamento em projeto fechado.

## Verificação manual da interface

Executada na publicação self-contained x64 após a revisão visual da Home; a inspeção foi feita com captura de janela e UI Automation nativa. A captura exibida pelo ambiente não foi convertida em screenshot arquivada automaticamente, portanto os arquivos históricos não são apresentados como evidência desta rodada:

1. Abrir a Home e confirmar que não existem `Instalação atual`, `Visão geral`, `MODO LOCAL · SIMULAÇÃO`, cards de modo local, Linha de Contexto, Sequência observável ou Agentes e estados.
2. Confirmar o gráfico único com filtros `1 dia`, `7 dias` e `31 dias`, estado `N/D`, fonte não conectada e tooltip explicativo sem inventar pontos.
3. Confirmar card esquerdo com marca do projeto, nome Seloryn, tier I–V, últimas atividades e ação externa; confirmar o próximo gate coerente à direita.
4. Confirmar request logs abaixo com cabeçalho mascarado e estado vazio honesto.
5. Navegar para Projetos, filtrar `vendas`/`seloryn`, confirmar marcas vetoriais próprias e estado vazio quando não houver resultado.
6. Abrir Seloryn e verificar abas, revisão `r127`, módulos e contexto do gateway futuro.
7. Reservar `TASK-29`; confirmar atualização de área e toast. Fechar projeto e confirmar bloqueios visuais de escrita.
8. No Workspace, selecionar arquivo, evento, commit, tag e release; confirmar que cada seleção atualiza o inspetor sem afirmar Git, branch ou deploy.
9. Recolher/expandir o rail pelo controle-porta; confirmar largura animada, rotação da seta, apenas ícones no estado recolhido e tooltips acessíveis.
10. Abrir a engrenagem do perfil, testar `Esc`, foco de retorno e opção de reduzir movimento.
11. Repetir em janela maximizada e em largura mínima operável; confirmar que os cards empilham e que apenas a tabela usa rolagem horizontal local.
12. Confirmar caret, seleção, foco e scrollbar com contraste visível.
13. No Workspace compacto, confirmar a ordem arquivos → inspetor → metadados → tarefas → commits e a presença de colaboradores observáveis sem afirmar presença externa.
14. Clicar em referências de tarefa, arquivo, revisão, entrega, commit, tag e release; confirmar seleção e destino sem depender da ordem visual das abas.
15. Em Provar, confirmar que `Registrar integração` fica desabilitado em entrega em revisão e projeto fechado, e habilita somente para entrega aprovada localmente em projeto aberto.
16. Confirmar no gráfico vazio que todas as séries aparecem como `N/D`, sem zero inferido, com resumo acessível.
17. Abrir uma sessão nova e confirmar que a Home mostra `nenhum projeto em foco`; abrir Projetos, selecionar explicitamente um item e confirmar que o foco/rail passam a usar o mesmo `project_id`.
18. Em um projeto com tarefas em estados mistos, confirmar que “próxima decisão” usa a primeira tarefa `PRONTA`; nunca usar a posição `Tasks[0]` como atalho semântico.
19. Na Home sem gateway, confirmar por UI Automation que eixos/legendas do gráfico e cabeçalho/linhas vazios de Request Logs não entram no `Document text`.
20. Em Provar compacto, confirmar que as ações da entrega permanecem visíveis abaixo do resumo e que ações incompatíveis seguem desabilitadas.
21. Abrir configurações pela engrenagem, confirmar `ControlType=Window`, nome `Configurações`, `Escape` e retorno do foco.

## Cobertura futura obrigatória

Antes de conectar serviços reais, automatizar os cenários CA-01 a CA-20 da documentação, incluindo nove sessões, latências, retries, queda de conexão, bypass de conector local, isolamento entre projetos e regras externas de branch protegida.
