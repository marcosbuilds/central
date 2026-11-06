# 11 — Critérios e testes de aceitação

| ID | Cenário | Resultado exigido |
|---|---|---|
| CA-01 | Membro sem convite tenta entrar | Negado e registrado |
| CA-02 | Discord desconectado após criação | Política local segura; nenhuma concessão implícita |
| CA-03 | IA pede `trabalhe na Seloryn` | Resolve somente projeto autorizado, mostra estado e tarefa válida |
| CA-04 | IA pede nome ambíguo | Pergunta antes de alterar qualquer projeto |
| CA-05 | Uma IA ocupa `auth.register` | Outra IA não consegue reservar lógica incompatível |
| CA-06 | Backend implementa rota usada pelo frontend | Conversa, contrato versionado e testes de integração disponíveis |
| CA-07 | Sessão backend está offline | Pedido fica pendente; nenhuma falsa resposta automática |
| CA-08 | Dois patches chegaram com mesma base | Um aplicado; outro revalidado ou rejeitado com conflito |
| CA-09 | Projeto fecha durante patch | Sem escrita aceita após fechamento; sessão recebe sinal e pode recuperar estado |
| CA-10 | Projeto está fechado | Sem patches, claims, merge ou deploy; leitura com permissão mantida |
| CA-11 | Pequena edição sem necessidade de versão oficial | Revisionada e recuperável sem PR nem deploy |
| CA-12 | Candidato à master foi modificado depois da aprovação | Aprovação invalidada; nova revisão exigida |
| CA-13 | IA revisa mudança criada por ela própria | Negado por falta de independência |
| CA-14 | IA autorizada revisa mudança de baixo risco | Somente aprova com evidências verificadas e política permitindo |
| CA-15 | Mudança de autenticação tem somente parecer de IA | Bloqueada até aprovação humana definida |
| CA-16 | Testes falharam mas IA escreveu 'aprovado' | Não integrar master |
| CA-17 | Regra GitHub bloqueia merge | Mostrar bloqueio real, não 'aprovado e publicado' |
| CA-18 | Versão master foi aprovada | Não fazer deploy sem etapa própria de autorização |
| CA-19 | Contrato de API mudou de forma incompatível | Consumidores alertados, integração bloqueada até reconciliação |
| CA-20 | Cliente sem autorização pede ver outro projeto | Nenhum dado cruzado por API, busca, logs, eventos ou cache |

Executar testes de simultaneidade com 9 sessões, latências variadas, retries, conexões caindo e concorrência em recursos lógicos distintos e sobrepostos. Verificar também que o conector local sem controle de escrita **não** consegue enganar a Central publicando alterações fora do gateway.
