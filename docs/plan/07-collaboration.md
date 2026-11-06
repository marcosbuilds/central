# 04 — Workspace vivo: mesmo código, IAs diferentes, sem choque

> **Requisito central definido pela equipe:** agentes trabalham sobre o mesmo projeto compartilhado e enxergam rapidamente as mudanças uns dos outros. Reservas proíbem concorrência na mesma parte/ lógica. Branch isolada por IA **não é** a experiência principal. Uma versão estável aprovada fica separada da área de edição viva por motivo de segurança operacional.

## Por que somente “travar arquivo” não resolve

A lógica “criar pedido” pode estar distribuída entre `api/orders.py`, uma tabela SQL, um contrato de tipos e uma interface web. Duas IAs mexendo em arquivos diferentes podem quebrar a mesma regra. E um arquivo enorme pode conter funções que não se afetam. Portanto é preciso coordenar em **camadas de intenção**, além de arquivo.

## Três camadas de coordenação

1. **Reserva de tarefa**: uma pessoa/agente é responsável pela entrega definida no planejamento.
2. **Reserva lógica/semântica**: módulo, serviço, recurso, endpoint, modelo de dados, contrato externo, esquema, função ou conjunto de responsabilidades.
3. **Reserva física**: arquivos e diretórios que podem ser alterados, com exclusividade quando a análise de código não for confiável.

Exemplo: `auth.login` é uma reserva lógica que cobre validação da senha, sessão e seus contratos de autorização. Ninguém altera os mesmos pontos sem solicitar transferência ou negociar divisão.

## Origem da verdade

- Um **workspace canônico vivo** é a fonte dos arquivos que todos consultam.
- O servidor mantém revisão `workspace_revision` monotônica e manifesto de caminhos/hashes por revisão.
- A camada de sincronização transmite mudanças **confirmadas** à visão dos demais em segundos, não promete simultaneidade absoluta em redes instáveis.
- Toda alteração possui `change_set_id`, autor humano, agente/sessão, tarefa, reservas, revisão-base e hashes.
- O gateway aplica o conjunto de mudanças de forma **atômica**, ou rejeita o lote inteiro; grava evento e snapshot recuperável.
- Alterações em análise são **visíveis e etiquetadas**, mas ainda não aparecem na versão estável publicada.

## Protocolo obrigatório da IA

1. `discover`: consultar projeto, tarefas abertas, reservas, dependências e contratos.
2. `claim`: pedir tarefa e reservas de lógica/arquivos, informando intenção e previsão.
3. `refresh`: obter revisão atual + documentação e arquivos necessários.
4. `plan`: declarar arquivos e lógica previstos; a central pode expandir áreas protegidas conforme dependências.
5. `heartbeat`: manter reserva ativa enquanto trabalha.
6. `propose_patch`: enviar diferenças e hashes-base; o servidor inspeciona caminhos, operações, dependências e mudanças inesperadas.
7. `apply_patch`: gateway valida novamente **no momento exato** da aplicação; em transação/controle de exclusão, atualiza workspace e emite evento ordenado.
8. `verify`: executar testes apropriados e análise de código; registrar resultados.
9. `request_review`: enviar mudança para revisão independente.
10. `release_claim`: liberar reserva e atualizar mapa para os demais; fechar sessão ao terminar.

**Importante:** `claim` por si só não pode garantir que a IA nunca acesse outro caminho se ela possuir acesso livre ao disco. O sistema deve controlar a capacidade de escrita do adaptador e do ambiente executado.

## Política de reservas

- Exclusividade para gravação na mesma área lógica ou física, compartilhamento de leitura.
- Reservas cobrem **dependências impactadas**, não só arquivo selecionado.
- Dependências são declaradas no projeto e inferidas gradualmente com imports, call graph, contrato de API e mapa de ownership; inferência é **heurística**, nunca garantia formal.
- Se a linguagem não puder ser analisada com confiança, reservar o arquivo todo (ou módulo todo em mudanças estruturais).
- Documentos e contratos centrais têm reserva reforçada e aviso aos responsáveis por módulos dependentes.
- Reserva por tarefa tem dono humano, agente(s) associados, escopo, prazo de expiração e heartbeats.
- Deadlock: solicitar múltiplos recursos numa ordem estável, com pedido atômico; se indisponível, não segurar parcialmente recursos por tempo indefinido.
- Expiração: sessão sem sinais entra em `suspect`; após período configurado, cancelamento seguro da escrita e recuperação supervisionada de bloqueios; não liberar no meio de patch.
- Deslocamento manual: líder com justificativa, aviso, auditoria e confirmação de que não há operação ativa.
- Um recurso sensível pode exigir reserva de um único agente por vez, mesmo que dois editem símbolos diferentes.

## Conflitos e atualização simultânea

**Cenário 1 — Mesma lógica:** IA A reservou `payments.capture`. IA B tenta tocar essa lógica: **negação** com quem é dono, tarefa atual e opções de pedir ajuda, aguardar ou escolher parte independente.

**Cenário 2 — Arquivos diferentes, mesma API:** IA A altera resposta de `/bookings`. IA B altera o app que consome `/bookings`. Central detecta dependência, bloqueia alteração de contrato sem acordo, avisa IA B e exige teste de contrato.

**Cenário 3 — Mesmo arquivo, funções independentes:** somente liberar concorrência por símbolo quando parser/AST + mapa de ownership da linguagem permitirem diferenciar trechos e validar hashes por trecho. Caso contrário, o arquivo inteiro é exclusivo.

**Cenário 4 — Ambas leram a revisão 15:** IA A aplica patch e gera revisão 16. IA B envia patch baseado na revisão 15. Gateway compara hashes dos trechos tocados e dependências: se ainda aplicável, reconcilia e gera revisão 17; caso contrário retorna `409 STALE_BASE` e exige recarregar/reescrever. Nunca aplicar cegamente com base antiga.

**Cenário 5 — Rede caiu:** o cliente enfileira somente alterações locais seguras, marcadas `aguardando sincronização`, sem prometer que estão no workspace vivo. Ao reconectar, revalida reservas, hashes e revisão. Caso inválidas, não sincroniza por força bruta.

**Cenário 6 — Mudança reprovada:** o conjunto foi visto na área viva, mas não pode entrar na versão estável. Reverter seletivamente por change set e testar, avaliando mudanças dependentes; se outros agentes construíram sobre ele, abrir tarefa de recuperação e bloquear publicação até resolver.

**Cenário 7 — Agente altera nomes/estrutura sem anunciar:** gateway exige reserva do diretório/módulo antigo e novo, analisa referências, invalidando tarefas dependentes e exigindo revisão reforçada.

## Risco fundamental: alteração compartilhada pode quebrar o projeto vivo

Um workspace global em edição é inerentemente mais vulnerável a falhas transitórias que ambientes de desenvolvimento isolados. Redução de risco:

- Lotes pequenos e reversíveis; *checkpoint* antes de cada lote.
- Testes rápidos pré-aplicação para operações críticas; testes completos pós-aplicação.
- Preview e build/execução em contêiner isolado, nunca diretamente no servidor com dados reais.
- **Snapshot estável sempre recuperável**; nunca executar produção diretamente da árvore viva.
- Se falhar um teste essencial, sinalizar e bloquear promoção; em regras estritas, reverter o lote antes de liberar dependências.
- **Não prometer prevenção de 100% dos conflitos semânticos.** Reservas, validação de base e testes reduzem riscos conhecidos; contratos e revisão humana cobrem lacunas.

## Caso especial: as IAs de cada um estão no próprio computador

O app desktop/daemon local observa operações permitidas, conecta-se ao gateway e mantém uma cópia sincronizada. A fonte de verdade é central. Uma cópia local pode ficar atrasada; o patch só é aceito depois que o servidor revalida. A integração por SDK/hook é **instrumentada**: ferramentas de escrita/terminal precisam passar pelo controlador ou ser executadas em um workspace com acesso restrito. Agentes soltos em diretórios de usuários sem agente controlador não podem receber garantia de exclusividade.

## Teste de aceite obrigatório

Executar 9 sessões simuladas, misturando provedores, com 4 tarefas sem conflito e 5 tentativas de sobreposição. A central deve permitir independentes, negar todas as sobreposições configuradas, rejeitar patches com base obsoleta, exibir eventos ordenados, recuperar-se de queda de conexão e preservar versão estável. Testar também que uma tentativa de bypass não consegue publicar no workspace canônico.


---

# 05 — IA própria de cada integrante: conexão e streaming

## Ideia

Cada dev pode continuar usando Codex, Claude Code ou outra ferramenta compatível. A central **não substitui** o modelo; adiciona contexto compartilhado, reservas, autorização, observabilidade e publicação controlada.

## Componentes

- **App do integrante**: interface, sessões, tarefas, alertas.
- **Agente local de sincronização**: autentica máquina, obtém planos/contratos, observa mudanças, transmite eventos e submete patches.
- **Adaptador por provedor**: traduz chamadas e eventos da ferramenta para contratos da central.
- **Gateway da central**: autentica, verifica escopo, reserva, controla gravação, versões e auditoria.
- **Canal de eventos**: servidor envia presença, progresso, diff, bloqueio e revisão pelo WebSocket (ou SSE para clientes só de leitura).

## Compatibilidade baseada em APIs documentadas

- **Codex**: o SDK ajuda a automatizar sessões; **Codex App Server** é opção de integração mais rica, com eventos, aprovações e controle. Evitar presumir que todo modo do Codex permitirá bloquear todas as escritas externas sem um adaptador controlador.
- **Claude Code**: Agent SDK em Python/TypeScript tem streaming, permissões e hooks capazes de interceptar chamadas de ferramentas; usá-los para aplicar regras e registrar eventos, sujeito a comportamento e versões reais da instalação.
- **Outros agentes**: adaptadores versionados; requerem capacidade de reportar atividade e submeter mudanças por um gateway. Se a ferramenta não suporta integração confiável, oferecer modo somente leitura ou trabalho manual, não selo falso de 'sem conflitos'.

## Token pessoal da central

Criar token por integrante, projeto, dispositivo e tempo de validade. Identificador público do token + segredo mostrado só uma vez. Guardar hash do token, não texto puro. Permissões mínimas: `project.read`, `tasks.read`, `claims.create`, `workspace.read`, `patch.propose`, `patch.apply.claimed`, `tests.run`, `review.read`. `deploy.production` e administração nunca embutidos no token padrão da IA.

Rotação, revogação instantânea, expiração, limite de taxa e auditoria. Token é vinculado a projeto e usuário. Um membro removido deixa de acessar mesmo que tenha cópia antiga do token.

## Sessões e eventos

Sessão: `session_id`, `member_id`, `provider`, `project_id`, `task_id`, `agent_version`, `client_version`, `status`, `started_at`, `last_heartbeat_at`, `resource_claims`, `last_workspace_revision`.

Eventos mínimos:

- `agent.connected`, `agent.disconnected`, `agent.heartbeat`;
- `task.claimed`, `claim.blocked`, `claim.released`;
- `agent.started_work`, `agent.activity`, `agent.waiting`, `agent.completed`, `agent.failed`;
- `patch.proposed`, `patch.denied`, `patch.applied`, `workspace.revision_updated`;
- `test.started`, `test.finished`, `review.requested`, `review.decided`.

**Streaming útil**, em vez de capturar raciocínio privado ou teclado: mostrar o passo atual autorizado, tarefa, arquivo/contrato afetado, operação e seu resultado. Não coletar *chain of thought*, senhas, prompts confidenciais ou saída completa de terminal por padrão.

## Processo de conexão da IA

1. Integrante faz login na central e obtém aprovação para o projeto.
2. Cria um token restrito para sua máquina e seu agente, com data de expiração.
3. Instala e configura o adaptador/agente local; segredo fica no armazenamento seguro do dispositivo.
4. Adaptador registra a sessão e obtém o manifesto de tarefas/contratos.
5. Antes de agir, a IA consulta reservas e propõe plano de trabalho.
6. Central libera escopo; o adaptador limita operações de escrita ao escopo.
7. Atividades e patches aparecem em streaming; mudanças confirmadas entram no workspace compartilhado.
8. Revisor aprova ou pede correção; após testes, cria snapshot estável.

## Limites reais e segurança

- Não basta informar à IA em prompt “não toque em arquivos alheios”: é uma regra **operacional** imposta ao gateway e, sempre que possível, à camada de execução.
- Um plugin apenas observador não impede o processo local de editar arquivos; precisa controlar a publicação e preferencialmente mediar a escrita.
- Subprocessos e terminal podem modificar arquivos fora da ferramenta de edição. Executá-los com permissões delimitadas e validar toda diferença antes de sincronizar.
- Nunca copiar credencial de provedor para a central sem necessidade; preferir credenciais geridas localmente pelo usuário ou acesso empresarial autorizado.
- Limitar o conteúdo transmitido; arquivos e logs de clientes podem ser confidenciais. Definir autorização e transparência contratual de uso de IA.

## Exemplo de mensagem da central para um agente

```json
{
  "status": "denied",
  "reason": "SEMANTIC_RESOURCE_BUSY",
  "resource": "booking.create",
  "current_owner": "session_A",
  "blocked_task": "T-104",
  "available_tasks": ["T-109", "T-112"],
  "suggestion": "Escolha uma tarefa independente ou peça acordo de interface ao responsável."
}
```

## Metas de desempenho — propostas para testar, não evidências

Objetivo de sensação em rede normal: status da reserva/atividade chega a outros clientes em poucos segundos; propagação do patch após confirmação igualmente rápida; reestabelecimento após desconexão sem alterações perdidas/duplicadas. Latência exata e escala serão definidas e medidas com protótipo e testes, não prometidas agora.
