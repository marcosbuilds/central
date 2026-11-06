# 02 — Frontend, backend e sistemas: exemplos reais

## O que significa cada área
**Frontend** é o que a pessoa vê e usa: menu, botões, formulários, tela de cadastro, gráficos, notificações. Pode estar em um **site**, **aplicativo de celular**, **programa de computador** ou painel de máquinas.

**Backend** é quem recebe pedidos das telas e aplica as regras: confere senha, verifica estoque, calcula valores, grava dados, conversa com serviços externos e autoriza operações.

**Sistema** não é apenas backend. É o conjunto de frontend, backend, dados, integrações, processos, segurança, testes e operação que resolve uma necessidade. Alguns sistemas funcionam sem telas; outros incluem web, celular e desktop ao mesmo tempo.

## Exemplo A — Clínica que quer marcar consultas
**Problema do cliente:** pacientes ligam demais e há conflitos de horários.

1. **Produto/documentador** entrevista recepção e profissionais: horários, encaixes, cancelamentos, confirmações, regras de acesso e dados sensíveis. Produz requisitos, fluxos, desenhos de entidades e pacote inicial.
2. **Design** mostra como seria escolher data, médico e receber confirmação.
3. **Frontend** constrói a tela do paciente e o painel da recepção.
4. **Backend** verifica disponibilidade, evita dupla reserva, registra consultas e dispara lembretes.
5. **Infra** disponibiliza ambiente de testes, autenticação, cópias de segurança e monitoramento.
6. **QA** testa duas pessoas marcando o mesmo horário, falha de internet, cancelamento e acessibilidade.
7. **Todos** revisam o resultado com a clínica antes do lançamento.

**Entrega:** não apenas um site: um sistema de agendamento com regras, banco de dados, painel e integrações. Dados de saúde exigem cuidado adicional com LGPD e escopo; não começar sem revisão adequada.

## Exemplo B — Loja com estoque e vendas
- **Frontend web:** painel de produtos e pedidos.
- **Frontend mobile/desktop:** aplicativo para consultar o estoque, inclusive eventual modo offline se contratado.
- **Backend:** controla entradas/saídas, evita venda acima do estoque e integra pagamentos/notas quando previstas.
- **Produto/documentador:** descobre como a loja trabalha na prática e decide o que vem primeiro.
- **QA + infra + design:** garantem que o resultado seja utilizável, verificável e estável.
- **Sistema final:** painel + aplicativo + API + dados + integrações e rotinas.

## Exemplo C — Empresa que recebe arquivos por e-mail e preenche planilhas manualmente
- O produto pode ser **uma automação sem uma interface complexa**: busca arquivos autorizados, valida, transforma dados, registra resultado e avisa falhas.
- Backend/integrações assume mais trabalho; frontend entrega apenas um pequeno painel se necessário; QA valida arquivos ruins e erros; documentação define regras; infra monitora.

## Exemplo D — Plataforma interna da própria startup
- **Frontend:** dashboard, lista de projetos, árvore de arquivos, comentários, trabalho ao vivo.
- **Backend:** login, permissões, tarefas, reservas, histórico e APIs dos agentes.
- **Conector local:** lê eventos autorizados de Codex/Claude e envia a atividade do desenvolvedor.
- **QA:** simula duas IAs tentando alterar o mesmo módulo.
- **Infra:** operação, deploy e segurança.
- **Produto/documentador:** especifica fluxos e regras da Central antes do código.

## O que não confundir
- Ter 3 backends não significa que um faz 'site' e outro faz 'sistema'. Eles podem trabalhar no mesmo produto com responsabilidades por módulos.
- Uma interface pode ser feita em diferentes tecnologias; não assumir que quem faz frontend web dominará mobile nativo automaticamente.
- O cliente deve enxergar **resultado**, não nomenclatura técnica: menos trabalho manual, menos erros, atendimento melhor, mais controle ou nova fonte de receita.
