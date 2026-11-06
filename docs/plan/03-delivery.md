# 03 — Entrevista ao cliente, arquitetura inicial e entrega ao time

O responsável por produto/documentação **não é apenas alguém que escreve textos**. É o ponto de tradução entre o problema real do cliente e a execução da equipe. **Também faz o primeiro desenho de arquitetura**, sempre validado por líder técnico, QA e infraestrutura onde houver impacto.

## Jornada — da conversa à primeira linha de código

### 1. Preparar e entrevistar o cliente
- Identificar quem usa, quem paga, quem decide e quem conhece o trabalho diário.
- Entender primeiro o **problema existente**, não apenas a tela que o cliente pediu.
- Perguntar como a tarefa funciona hoje, o que provoca erro, o que demora, o que acontece sem internet, quem tem acesso, quais dados são guardados e o que precisa integrar.
- Demonstrar compreensão com exemplos reais: 'Se dois funcionários realizarem a mesma operação juntos, o que deve acontecer?'.
- Separar o que é essencial, desejável, fora do escopo e ainda não entendido.
- Obter autorização para registrar reunião e cuidado com dados pessoais/segredos; nunca colocar dados reais sensíveis em prompts sem base legal/contratual adequada.

### 2. Escrever requisitos testáveis
Cada requisito deve conter ID, problema, história simples, regra, permissão, prioridade, critérios de aceitação, dependência e dúvida. Exemplo:

> `REQ-012` — Uma recepcionista pode agendar uma consulta em horário livre; se outra pessoa escolher o mesmo horário, somente uma reserva deve vencer. **Teste:** simular duas reservas simultâneas; resultado esperado: um sucesso, um conflito compreensível.

### 3. Desenhar a solução antes do código
Preparar: telas/fluxos com designer; módulos com líder técnico; entidades e relações; contratos/API; integração externa e limites; riscos de acesso; ambientes; testes; registro das opções de arquitetura descartadas e motivo. Em caso de dúvida técnica, registrar `PENDENTE`, não inventar a decisão.

### 4. Planejar tarefas
Quebrar entregas pequenas e observáveis, com dependências. Criar responsáveis por **resultado**, não dividir exclusivamente por arquivo. Exemplo: `TASK-17 Criar reserva de consulta` depende de `TASK-08 cadastro de profissionais` e `TASK-11 horários disponíveis`.

### 5. Produzir o ZIP de início
O ZIP é um **pacote de partida versionado** com árvore organizada, documentação aprovada, arquivos de exemplo e contratos iniciais. Inclui README, decisões, requisitos, estrutura de apps/serviços, planejamento de testes e configuração de exemplo, mas **não** credenciais, dados reais de clientes, cache ou dependências instaladas. Não é promessa de projeto funcional completo.

### 6. Reunião de início e aceitação
O líder técnico revisa viabilidade, alternativas e interfaces entre módulos; designer revisa fluxo; QA revisa critérios; infraestrutura revisa implantação e segurança. Somente depois o pacote vira projeto ativo na Central. Cliente valida escopo e datas comerciais antes de prometer entrega.

## Conteúdo obrigatório do pacote
```
projeto-cliente/
├── README.md                      # contexto, instruções e situação do pacote
├── manifest.json                  # identificador, versão e módulos planejados
├── docs/
│   ├── briefing.md                # quem é o cliente, problema, pessoas e objetivos
│   ├── requisitos.md              # regras numeradas, critérios e prioridades
│   ├── escopo.md                  # entra/não entra, dependências e restrições
│   ├── fluxos.md                  # uso passo a passo e estados de interface
│   ├── arquitetura.md             # decisões e limites de cada parte
│   ├── dados-e-permissoes.md      # entidades e quem pode acessar
│   ├── integracoes.md             # serviços externos, riscos e contratos
│   ├── plano-de-testes.md         # cenários reais e requisitos não funcionais
│   ├── entrega.md                 # etapas, responsáveis, dúvidas e aprovações
│   └── decisoes/ADR-0001.md      # por que escolhemos esta arquitetura
├── apps/
│   ├── web/                       # incluir quando houver aplicação web
│   └── mobile/                    # incluir somente quando houver app mobile
├── services/api/                 # incluir quando o sistema tiver API
├── packages/contratos/           # formatos compartilhados e especificações
├── infra/                        # configurações de exemplo, sem segredos
└── tests/                        # casos e testes iniciais
```
**A árvore deve seguir o projeto.** Não criar pasta `mobile` ou microserviço só porque o modelo a possui; o gerador remove áreas não aplicáveis. É aceitável um único aplicativo bem organizado.

## `manifest.json`: identidade e responsabilidade
- ID e nome do projeto; cliente e ambiente (sem dados confidenciais em arquivos públicos); tipo de aplicação; módulos; sistemas externos; responsável de produto; aprovação de arquitetura; versão do pacote; origem do repositório; riscos e pendências.
- A Central lê o manifesto, compara com esquema válido, cria tarefas iniciais, solicita revisão e registra histórico. Não executar scripts desconhecidos automaticamente ao importar ZIP.

## Critério para liberar ao time
- [ ] Problema e resultado esperado estão escritos em linguagem simples.
- [ ] Escopo e exclusões claros; tarefas essenciais priorizadas.
- [ ] Requisitos principais possuem teste de aceitação.
- [ ] Fluxos e permissões revisados.
- [ ] Arquitetura técnica **aprovada**, não apenas gerada.
- [ ] Árvore do projeto corresponde aos módulos contratados.
- [ ] ZIP abre corretamente, sem senhas, tokens ou dados reais.
- [ ] Cliente aprovou o escopo; equipe aceitou a estimativa.
- [ ] Decisões pendentes têm dono e data para resolução.

## Regra para mudanças posteriores
Solicitação nova entra como mudança de escopo: registrar impacto em custo, dependências, arquitetura, trabalho já realizado e cronograma; exigir decisão do cliente antes de alterar prioridades da equipe.
