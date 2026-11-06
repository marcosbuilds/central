# Contrato de integração — Peace e Central

Status: contrato documentado; implementação da troca de código ainda pendente

## Objetivo

O bot Discord da Peace será a porta de entrada da Central. Somente um membro
que possua o cargo técnico de acesso `Dev` poderá iniciar a liberação. O
usuário informa seu ID Peace, recebe um código de autenticação em DM e usa o
código para abrir uma sessão curta na Central.

Este fluxo não deve reutilizar o token do bot, a senha do Discord ou o banco
SQLite como credencial para o desktop.

## Fluxo normativo

1. O membro solicita acesso pelo comando/painel oficial do bot. O nome exato do
   comando continua uma decisão de UX e não deve ser inventado em código ainda.
2. O bot resolve o ID imutável do membro no Discord e verifica o ID do cargo
   `Dev` configurado em ambiente. Nome visual de cargo não é autorização.
3. O bot solicita o ID Peace e valida o vínculo no banco local conforme as
   regras de reserva/retorno já documentadas pela Peace.
4. Um serviço de autenticação cria um desafio aleatório, armazena somente o
   hash, associa-o ao Discord user ID, ao ID Peace, ao cliente e à finalidade
   `central-login`, define expiração curta e limita tentativas.
5. O bot envia o código em DM. O valor não aparece em logs, snapshots, tickets,
   respostas públicas ou prompts da Iris.
6. A Central envia o código por HTTPS ao serviço de autenticação. O serviço
   verifica uso único, expiração, tentativas, finalidade e associação. Em caso
   válido, emite uma sessão curta com escopo de projeto; em caso inválido,
   nega sem revelar se o ID ou o código foi o problema.
7. A Central usa a sessão curta para autenticar Supabase e registrar o Device ID
   do Syncthing. Revogação de cargo ou sessão invalida novas conexões.

## Limites e decisões abertas

- A implementação precisa escolher entre Supabase Edge Function e um serviço
  dedicado para o endpoint de troca; o gateway PythonAnywhere atual é
  health-only e não é autorizado a assumir essa função.
- A forma final do comando/painel, o tempo de expiração e o limite de tentativas
  devem ser aprovados antes do código.
- O Supabase deve receber uma identidade verificável e não confiar em um
  `peace_id` digitado pelo cliente sem prova emitida pelo bot.
- O fluxo deve suportar revogação, auditoria mínima e recuperação de DM
  bloqueada sem exibir o código em canal público.

## Invariantes de segurança

- O cargo `Dev` é verificado no servidor Discord pela identificação estável do
  cargo e do membro.
- O desktop nunca recebe o token do bot, a service-role key ou o banco SQLite.
- O código é uma credencial transitória, de uso único, com hash em repouso,
  expiração, rate limit e invalidação após sucesso.
- IP, nome da máquina e nome visual do Discord não são identidade suficiente.
- Falha parcial não concede acesso: DM enviada sem desafio persistido, desafio
  expirado, sessão revogada ou erro de Supabase resultam em acesso negado.

## Verificação prevista

- membro sem `Dev` é negado;
- ID Peace não pertencente ao membro é negado;
- código expirado, repetido ou tentado acima do limite é negado;
- código válido gera uma única sessão curta e não pode ser reutilizado;
- revogar o cargo impede novo login;
- nenhum segredo aparece em logs, banco local, snapshot ou artefato do desktop.

Até esses testes existirem, a integração deve ser tratada como planejamento e
não como capacidade disponível na Central.
