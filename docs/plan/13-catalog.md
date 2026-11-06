# 13 — Seleção de projetos por IA e fechamento seguro

## Objetivo em linguagem simples
O integrante abre o Codex/Claude e pede: **'Trabalhe no projeto Seloryn e continue de onde paramos.'** A IA encontra o projeto cadastrado na Central, conhece a versão atual e o que os colegas estão fazendo, escolhe uma tarefa livre compatível com o pedido e trabalha no **mesmo projeto compartilhado**.

O time pode fechar um projeto: ele continua disponível para consulta, mas não aceita alterações nem novas publicações até que alguém com permissão o reabra.

## Exemplo de conversa e fluxo
```
Pessoa: 'Continue o projeto da Seloryn. Veja o que está faltando.'
IA   -> list_projects('Seloryn')
     <- [{id:'proj-101', name:'Seloryn', status:'ABERTO'}]
IA   -> select_project('proj-101')
IA   -> get_project_context('proj-101')
     <- versão rev-127, árvore, documentação, módulos, contrato e tarefas
IA   -> get_active_work('proj-101')
     <- Ana + Codex ocupam parser; Bruno + Claude ocupam runtime
IA   -> list_tasks('proj-101', available=true)
     <- testes de CLI livres, documentação bloqueada por decisão
IA   -> claim_task('TASK-29', resources=['module:cli/tests'])
     <- lease confirmado
IA   -> envia progresso + mudanças propostas, recebe verificação
     <- revisão compartilhada rev-128 após validação/aceite
```

## 1. Identificar o projeto corretamente
- Chave oficial é UUID/ID interno, nunca nome de pasta adivinhado.
- Nome, aliases e busca ajudam a identificar. Alias 'seloryn', projeto 'Seloryn' e repositório correspondente apontam para o mesmo ID.
- Se dois projetos combinarem com a expressão (ex.: 'site interno'), IA pergunta qual deseja; não escolhe arbitrariamente.
- Se usuário já está trabalhando em Seloryn e diz 'continue aquilo', pode usar `selected_project_id` anterior **se não houver dúvida relevante**.
- Se usuário manda 'trabalhe na Seloryn', prevalece o comando explícito sobre o projeto anterior.
- IA deve validar a mudança de alvo com o registro, não confiar em texto de README, comentário ou issue que mande trocar de projeto.

## 2. Antes de começar a alterar
A Central devolve `id`, `status`, `generation`, `shared_revision`, plano aprovado, manifesto, árvore, módulos, tarefas, regras, áreas ocupadas e dependências. O modelo só consegue editar um projeto ao qual o integrante tem acesso, mediante token da Central autenticado e autorização de escrita.

O integrante pode ter direito de **ver todos os projetos** e selecionar qualquer um, mas acessos a clientes precisam seguir contratos. Ler não equivale a escrever. A IA nunca herda poder de fechar/reabrir ou publicar em produção por ter permissão de editar.

## 3. Seleção da tarefa
- Com pedido específico ('corrija o comando inspect'), procurar tarefa e área coerentes; se não existir, propor criar tarefa e pedir validação conforme política.
- Com pedido amplo ('dê continuidade'), oferecer a próxima tarefa **aprovada, pronta e desbloqueada** segundo prioridade e dependências.
- Reservar também recursos lógicos: se um backend muda um contrato, frontend que depende dele recebe sinal de bloqueio ou coordenação.
- A IA não deve iniciar nova tarefa se estiver sem sincronização ou com reserva de outro projeto sem liberar/checkpoint.

## 4. Trocar de projeto durante trabalho
1. Capturar estado do trabalho atual, diff não integrado e comentário de pendências.
2. Finalizar ou pausar com segurança e liberar reserva (ou manter apenas se permitido para continuidade planejada, com prazo).
3. Resolver o novo projeto, validar status e autorização.
4. Atualizar contexto, revisão e dependências; criar sessão/associação nova.
5. Confirmar ao usuário que mudou e informar o que foi preservado do projeto anterior.

## 5. Fechamento e reabertura
| Status | Leitura | Nova tarefa/edit/merge/deploy | Descrição |
|---|---|---|---|
| `ABERTO` | Permitida por ACL | Permitida pelas regras | Trabalho normal |
| `FECHANDO` | Permitida | **Bloqueada** | Interrompe trabalhos, cancela jobs, prepara snapshot |
| `FECHADO` | Permitida | **Bloqueada** | Versão congelada e auditável |
| `REABRINDO` | Permitida | **Bloqueada** | Verifica sincronização e restabelece regras |

**Quem fecha:** gestor/autorizado; registrar motivo, responsável, timestamp e revisão. O pedido deve exigir confirmação. **Quem reabre:** pessoa autorizada pela política, com justificativa.

### Fechamento atômico sugerido
- Validar permissão e registrar intenção.
- No banco transacional, `ABERTO` → `FECHANDO` + `generation += 1` e fechar o portão de gravações **no mesmo passo**. Todas as APIs e jobs rejeitam a geração anterior a partir daí.
- Invalidar reservas e sessões de edição, notificar conectores e tentar interromper execução local supervisionada.
- Bloquear integração e publicação com credenciais de serviço e regras externas de repositório/CI quando disponível.
- Registrar `closed_revision`, documento de pendências, trabalhos não incorporados e links de auditoria.
- Confirmar controles externos antes de marcar `FECHADO`; se não funcionarem, o sistema continua bloqueando escritas via Central e avisa que o bloqueio externo é parcial.

### Reabertura
- Solicitar autorização; entrar `REABRINDO`, verificar permissões, repo, CI e status de tarefas.
- Restaurar políticas de escrita, incrementar geração e manter bloqueados tokens/sessões antigas até reautenticação ou renovação; não reaproveitar reservas.
- Atualizar contexto de agentes e sincronizar revisão antes de aceitar nova gravação; só então `ABERTO`.

### E se uma IA ainda estiver rodando?
A central pode emitir 'parar' para o conector e bloquear imediatamente gravações **via gateway**. Porém não pode garantir que um programa local offline pare de editar seu próprio disco. As mudanças locais não entram no projeto oficial enquanto fechado; acessos diretos ao Git/servidores devem ser bloqueados separadamente.

## 6. Histórias de usuário
- Como integrante, quero dizer o nome do projeto e a IA carregar automaticamente contexto e tarefas.
- Como integrante, quero trocar de projeto sem perder trabalho pendente.
- Como revisor, quero ver alterações em andamento antes de virarem mudança integrada.
- Como gestor, quero fechar projeto e impedir qualquer nova gravação no repositório controlado até abrir novamente.
- Como auditor, quero saber quem fechou/reabriu, qual revisão ficou congelada e quais trabalhos foram rejeitados.

## 7. Erros esperados da IA e reação correta
- 'Seloryn não existe': não criar repositório novo automaticamente; consultar catálogo/aliases e pedir confirmação.
- 'Projeto fechado': não alterar; pode ler e propor plano de retomada sem escrever no projeto.
- 'Sem permissão': não solicitar bypass; orientar integrante a pedir acesso.
- 'Outra IA ocupa a tarefa': procurar atividade independente documentada, ou aguardar/liberar trabalho de forma coordenada.
- 'Sessão perdeu conexão': não inventar progresso; sincronizar antes de atuar.
- 'Revisão-base mudou': reavaliar diff e testes, sem overwrite silencioso.

## 8. Frase que define a experiência
**'Diga o projeto; a IA encontra o contexto certo, continua com o time e respeita quando o trabalho está fechado.'**
