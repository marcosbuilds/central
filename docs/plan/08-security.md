# 06 — Cadastro, Discord, permissões e segurança

## Requisito de entrada

A central tem cadastro controlado por convite/aprovação, vinculação ao Discord e liberação do servidor. Não é cadastro público que concede acesso só por preencher formulário.

## Fluxo proposto (com consentimento)

1. Um administrador gera um convite individual limitado por validade, uso e, quando apropriado, e-mail convidado.
2. Pessoa acessa a central e autentica com **OAuth2 do Discord** (Authorization Code; usar `state` contra falsificação, PKCE se aplicável ao cliente, armazenamento seguro de sessão).
3. Central lê identidade Discord com escopo `identify` e verifica o convite. Se necessário, consulta associação ao servidor, com consentimento `guilds.members.read` ou bot autorizado.
4. Registro fica `pending_approval`, sem acesso a projetos.
5. Um administrador revisa, escolhe cargo e projetos permitidos, e aprova.
6. Bot aplica cargo no servidor. Se a pessoa não estiver no servidor, oferece convite; opcionalmente, adesão via `guilds.join` **somente com autorização expressa** e pré-requisitos da API.
7. Confirmação e auditoria. Se Discord falhar, estado fica `pending_discord_sync` para nova tentativa, nunca assume sucesso.
8. Ao suspender ou desligar, central revoga tokens/sessões; bot tenta retirar cargos/acesso Discord, registrando eventuais falhas para correção.

**Discord não é o banco principal de permissões.** Pode sincronizar cargos, mas acessos reais são validados na central a cada requisição. Não mostrar documentos de outros clientes só porque usuário entrou num canal.

## Papéis e controle por projeto

| Papel | Ler projeto | Alterar código em área reservada | Aprovar código | Produção | Gerir usuários |
|---|---|---|---|---|---|
| Membro desenvolvedor | conforme projeto | sim, por reserva validada | revisão de pares quando autorizado | não | não |
| Documentador/produto | conforme projeto | documentos/arquitetura por reserva | escopo/requisitos | não | não |
| QA | conforme projeto | testes por reserva | valida testes e critérios | não | não |
| Líder técnico | conforme projeto | sim | sim, com independência | com segundo controle | não necessariamente |
| Infra/operador | conforme projeto | infra por reserva | aprovação de infra | execução autorizada | não necessariamente |
| Administrador | projetos autorizados | não automaticamente | não automaticamente | não automaticamente | sim |
| Agente de IA | restrito por token | só operações escopadas | **não como aprovação final única** | **nunca via token padrão** | não |
| Cliente externo futuro | somente entregáveis liberados | não | aceite de negócio | não | não |

Aplicar **RBAC + permissões por projeto + condições por tarefa/recurso**. Ser administrador da plataforma não deve autorizar sem registro e sem revisão a modificar código de cliente.

## Tokens e sessões

- API tokens curtos por escopo/projeto, com hash armazenado, expiração, rotação e limite de uso.
- Sessão de navegador em cookie `HttpOnly`, `Secure`, `SameSite` adequado; proteção CSRF quando aplicável; TLS obrigatório.
- Diferenciar `member`, `device`, `agent_session`, `service_account` e `deploy_identity`.
- Chaves de serviço, Discord Bot token e dados de clientes ficam em secret manager, não no repositório nem no ZIP.
- 2FA/passkeys para ações críticas na central é altamente recomendado; sessão Discord sozinha não é garantia suficiente para produção.
- Registros de auditoria sensíveis com autor, horário, IP de segurança quando necessário, antes/depois resumido e motivo; prazo de retenção documentado.

## Proteção contra abusos

- Convite roubado, troca de conta Discord e remoção do servidor exigem verificação/revogação.
- Bots e usuários só veem projetos liberados; limitar acesso entre clientes.
- Rate limits e proteção contra força bruta, validação de webhook/assinaturas, sanitização de Markdown e comentários, isolamento de uploads ZIP contra caminhos `../`, zip bombs e executáveis inesperados.
- Segredos acidentalmente adicionados ao código: varredura e bloqueio antes de publicar.
- O cliente de IA só pode executar comandos em sandbox limitado; operações destrutivas e acesso a rede/segredos exigem consentimento apropriado.
- Informar equipe e clientes sobre que dados entram em ferramentas de terceiros; atender exigências contratuais e legais aplicáveis, inclusive LGPD.

## Condições de aceitação

Pessoa sem aprovação não abre workspace; membro de projeto A não acessa B; token revogado falha imediatamente; bot sem acesso não cria aprovação fictícia; alteração fora de reserva é negada; deploy para produção exige permissão humana e snapshot aprovado.


## Complemento — projetos múltiplos, congelamento e revisão delegada

- Uma sessão de IA recebe apenas a lista de projetos que o integrante **já pode acessar**, mesmo quando o token habilita descoberta de vários projetos. Dados de outros clientes continuam invisíveis.
- Operações de escrita exigem `project.state=OPEN`, autorização no momento da execução, reserva válida e revisão-base atual. Um comando de fechamento invalida concessões de escrita e bloqueia mesmo tokens já emitidos.
- Fechamento/reabertura requer cargo autorizado, motivo registrado e transição atômica. Fechar não apaga histórico ou discussões.
- A capacidade `review.propose` não concede `review.approve`. Aprovação de IA só ocorre com autorização delegada específica para o projeto e risco. A central conserva evidências, identidade da IA, seu responsável, hash exato revisado e política aplicada.
- Aprovador independente: pessoa/IA não pode aprovar seu próprio lote nem usar segunda identidade do mesmo autor para simular independência. Alteração posterior invalida aprovação daquele hash.
- Aprovação para integrar código não dá permissão de deploy; publicar produção pede papel próprio, regras de ambiente e testes.
- Não expor segredos, dados pessoais ou conteúdo privado em mensagens entre agentes ou na telemetria.
