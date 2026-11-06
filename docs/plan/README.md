# Startup de software + Central Colaborativa de Desenvolvimento

**Versão do planejamento:** 1.1 · **Data:** 03/11/2026 · **Time inicial:** 9 pessoas  
**Estado da fonte:** planejamento original preservado; a implementação da Fase 1 desktop está em `D:\projetos\Central` e não reescreve os contratos de domínio deste pacote.

## O que vamos construir
A empresa entrega **sistemas, aplicações web, mobile, desktop, automações, plataformas e serviços**, não apenas sites. A Central é seu aplicativo interno para planejar, documentar e acompanhar projetos; integrar as IAs próprias dos integrantes; coordenar a **mesma versão viva** do código; promover cooperação entre IAs; revisar entregas e controlar versões oficiais e publicação.

## Regras acordadas
1. **Nove especialidades**, mas equipe multidisciplinar; o documentador entrevista o cliente, detalha escopo/arquitetura junto ao líder técnico e entrega um ZIP organizado.
2. **Múltiplos projetos** na Central. A IA escolhe pelo nome/alias natural (`trabalhe na Seloryn`), consultando apenas os projetos autorizados.
3. **Mesmo workspace vivo para todos**, com revisões sequenciais, patches atômicos, reserva por tarefa, módulo, lógica e arquivo. Não usar branches isoladas por IA como experiência principal.
4. **Projetos podem ser fechados** para tornar seu código/estado imutável até a reabertura, inclusive frente a agentes e tokens antigos; leitura conforme permissão.
5. **Alterações cotidianas ≠ entrega oficial ≠ deploy.** Código ao vivo tem histórico recuperável; a `master` é protegida e só recebe entregas aprovadas; publicar é uma decisão independente.
6. **Revisão humana ou por IA especializada com delegação explícita e provas reproduzíveis.** Uma IA não aprova a própria alteração. Mudanças críticas pedem aprovação humana.
7. **IAs conversam no projeto**, discutem tarefas, pedem rotas de API, registram contratos e resolvem bloqueios; o time acompanha tudo em threads pesquisáveis.
8. Segurança por projeto, cliente, membro e token; Discord apoia convites/comunidade e não substitui autenticação/autorização.
9. Telemetria mostra fatos observáveis, não captura raciocínio privado da IA nem inventa streaming. Dashboard mede resultado e qualidade, não vigia horas online.

## Documentos (leitura recomendada)

| Caminho | Conteúdo |
|---|---|
| `01-team.md` | Equipe atual e futuras vagas |
| `02-cases.md` | Frontend, backend e sistemas com exemplos |
| `03-delivery.md` | Cliente, documentador, arquitetura e ZIP inicial |
| `04-central.md` | Telas, módulos e regras da plataforma |
| `05-architecture.md` | Componentes, servidores, integração e limites |
| `06-data.md` | Entidades, contratos e eventos |
| `07-collaboration.md` | Workspace vivo, reserva por lógica, conectores e streaming |
| `08-security.md` | Discord, identidade, tokens, projetos, delegações |
| `09-operations.md` | Métricas, revisões, deploys e operação |
| `10-roadmap.md` | Ordem recomendada de construção |
| `11-acceptance.md` | Cenários verificáveis para testar a Central |
| `12-references.md` | Documentação oficial consultada e limites |
| `13-catalog.md` | IA escolhe projeto, pausa e fechamento |
| `14-approval.md` | **Política de commits/entregas, aprovação e conversas entre IAs** |
| `15-protocol.md` | API sugerida, entidades, eventos e regras de integração |
| `template/` | Modelo curto de um projeto entregue ao time |

## Glossário simples

- **Frontend:** telas e interações que a pessoa vê.
- **Backend:** regras, processamento e dados por trás das telas.
- **Sistema:** conjunto completo funcionando (interface, lógica, banco de dados, integrações e operação).
- **API:** forma combinada para programas trocarem informações.
- **Workspace vivo:** versão compartilhada em que o time acompanha alterações autorizadas quase em tempo real.
- **Revisão `r123`:** registro recuperável de uma etapa do trabalho vivo.
- **Commit Git:** registro de alterações; pode ser pequeno ou grande.
- **Entrega para aprovação:** grupo coerente de mudanças que busca entrada na `master`.
- **`master`:** histórico protegido e estável, separado do trabalho em andamento.
- **Deploy:** colocar uma versão aprovada no ambiente de teste ou produção.
- **Contrato de API:** acordo documentado sobre rotas, dados e erros entre frontend e backend.

## Próxima ação real
Antes de criar dashboards, testar o **núcleo de coordenação** com duas IAs simuladas e depois nove sessões: selecionar projeto; travar lógica; enviar patch; mostrar atividade; abrir discussão de API; congelar projeto; preparar entrega; revisar com evidência; integrar à master sem deploy automático. Exigir provas de teste e recuperação de falhas antes de ampliar.

**Atenção:** os fluxos e endpoints são **propostas**, não recursos já disponíveis. Integrações Codex/Claude precisam de testes com SDKs e versões reais; não presumir que um token sozinho impede edições locais fora do gateway.

## Adendo de contraexemplo — interface da Fase 1

Este adendo altera a hipótese de navegação visual do documento original somente onde a implementação e a revisão adversarial demonstraram um contraexemplo melhor fundamentado. O domínio continua normativo: workspace vivo, reservas, revisão, evidências, segurança e publicação permanecem separados.

O contraexemplo rejeitado é expor no shell uma sala de controle com `Visão geral`, `Pessoas`, `Configurações`, `Planejar`, `Publicar` e outros módulos como destinos equivalentes, além de cards para cada métrica. Essa forma parece completa, mas obriga a pessoa a memorizar a taxonomia antes de resolver o trabalho central: identificar o projeto, entender a próxima decisão, inspecionar o artefato, conversar com a equipe e provar o resultado.

A hipótese exclusiva que substitui essa forma na Fase 1 é:

```text
Home → Projetos → Projeto selecionado
                         ├── Operar
                         ├── Workspace
                         ├── Coordenação
                         └── Provar
```

O projeto é o limite de contexto. Tarefas, arquivos, commits, tags, releases e Pulso pertencem ao Workspace; referências de pessoas/IAs pertencem à Coordenação; evidências, checks e estados de publicação pertencem a Provar. A Home começa sem projeto em foco e não escolhe a primeira fixture silenciosamente.

Também fica registrado que a interface não pode inventar streaming, produtividade, tokens, presença, Git, CI ou gateway. Sem fonte, usage e Request Logs são `N/D`/vazios; os estados locais são declarados como locais. A implementação desktop e suas decisões auditáveis estão em `docs\DESIGN-CONTRACT.md` e `docs\DESIGN-DECISIONS-2026-11-04.md`.
