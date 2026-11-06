# Regras da fonte do bot Peace

Este documento descreve as regras específicas do bot Peace dentro do monorepo.
As regras gerais estão em `AGENTS.md` na raiz.

## Estrutura do bot

Os arquivos do bot ficam nestes pontos curtos da árvore:

- `bot/`: código do pacote;
- `assets/`: imagens e outros recursos versionados usados pelo bot;
- `docs/peace/`: arquitetura, operação e decisões do bot;
- `tests/peace/`: testes automatizados;
- `data/`: estado local e exportações, sempre ignorados quando forem dados reais;
- `pyproject.toml`: empacotamento e comandos do bot.

Não criar na raiz pastas ou arquivos chamados `tmp`, `output`, `backup`, `new`,
`final`, `logs`, `exports`, `reports` ou equivalentes. Saídas temporárias devem
ficar em `data/runtime/`, `data/snapshots/` ou em uma pasta temporária fora do
projeto.

## Regras para dados e segredos

- Nunca versionar `.env`, tokens, credenciais, banco SQLite, snapshots do Discord,
  dumps, logs com conteúdo de mensagens ou dados pessoais.
- `data/` é estado local, não código-fonte. O banco legado
  `data/peace.sqlite3` só deve ser movido através de uma migração explícita e com
  backup verificado.
- Novos snapshots devem ser gravados em `data/snapshots/`.
- Estado operacional novo deve ser gravado em `data/runtime/` quando a migração
  do banco for planejada.
- Não imprimir tokens, RG, telefone, conteúdo de tickets ou dados privados em
  logs, testes ou mensagens de revisão.

## Regras para o código

- A identidade da Peace é preservada. Não renomear servidor, marca ou categorias
  de identidade como parte de uma refatoração; mudanças de nomenclatura precisam
  de decisão explícita e plano de compatibilidade.
- Manter os pontos de entrada públicos `peace-bot`, `peace-snapshot` e
  `peace-nick` definidos em `pyproject.toml`.
- Não alterar os `custom_id` dos painéis existentes sem uma migração planejada.
- O painel e o asset do canal `spam-control` são contrato rígido: não trocar
  texto, embed ou `assets/automod.png` sem autorização explícita. Artes de
  boas-vindas, set, atendimento e operações são os pontos seguros para evolução
  visual.
- Não alterar o schema ou mover o SQLite sem preservar os dados e registrar a
  migração.
- `bot/main.py` deve permanecer como ponto de compatibilidade durante a
  refatoração. Novas funcionalidades devem ser extraídas gradualmente para
  módulos em `bot/features/`, `bot/ui/`, `bot/integrations/` ou
  `bot/persistence/`, em vez de aumentar o arquivo monolítico.
- Configurações do servidor vêm de `.env` e `bot/cfg.py`; não hardcodar tokens,
  IDs ou permissões em novas features.
- Todo cargo deve ser classificado como `acesso` ou `visual`. Cargo visual deve
  ter permissões globais zeradas, não aparecer em guards de autorização e nunca
  controlar a visibilidade de canais. Cargo de acesso deve ter uma finalidade
  técnica documentada; não usar cargo visual para conceder permissão.
- Novos nomes operacionais devem seguir o padrão em inglês já usado no servidor.
  Em categorias organizadas, use `╭` no primeiro canal, `├` nos canais do meio
  e `╰` no último; áreas secas como `staff-only`, `scan-only` e `logs` não usam
  ornamentos.
- Antes de renomear, remover ou reaproveitar cargo/canal, levantar ID, membros,
  overwrites e uso no código. Preservar o ID quando isso reduzir risco.
- IDs Peace nunca devem ser reutilizados silenciosamente: saída com Peace reserva
  o ID; retorno exige card no `scan-only`, aprovação e registro do novo ID.
- Toda alteração de permissão, cargo, ticket, moderação ou dado pessoal deve
  validar autorização, hierarquia e falhas parciais.
- O atendimento com IA permanece desligado enquanto `IRIS_ENABLED=false`; ao
  reativar, registrar antes quais canais, dados e guardas serão usados.

## Regras para dependências e bots externos

- Antes de adicionar uma dependência ou bot externo, documentar o problema que
  ele resolve, os dados que acessa e o plano de remoção.
- Preferir uma integração bem configurada a vários bots com responsabilidades
  sobrepostas.
- A Iris pode orientar e preparar ações, mas nunca deve ser tratada como
  autoridade para conceder cargo, punir membro ou apagar estrutura sem as
  confirmações e guardas do sistema.

## Processo obrigatório para mudanças

1. Ler este arquivo e a documentação relevante antes de editar.
2. Fazer mudanças pequenas e reversíveis, separando organização de alteração de
   comportamento.
3. Adicionar ou atualizar testes para lógica pura, banco, permissões e fluxos
   alterados.
4. Executar os testes e uma verificação de inicialização antes de concluir.
5. Atualizar o README ou `docs/` quando a execução, configuração ou árvore mudar.
6. Descrever riscos, migrações necessárias e arquivos gerados na entrega.

## Convenções

- Python: módulos e funções em `snake_case`, classes em `PascalCase`.
- Documentação: nomes descritivos em `UPPER_SNAKE_CASE.md` ou `kebab-case.md`,
  sem cópias concorrentes do mesmo assunto.
- Um arquivo deve ter uma responsabilidade clara; evitar módulos genéricos como
  `utils.py` quando um nome de domínio for possível.
- Artefatos gerados devem ser recriáveis e nunca ser usados como fonte de
  verdade.
