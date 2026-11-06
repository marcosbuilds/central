# 12 — Referências técnicas consultadas (03/11/2026)

Fontes oficiais usadas como base para recursos existentes, **não como comprovação de que a Central está implementada**:

- Git — registrar alterações e histórico: https://git-scm.com/docs/git-commit
- GitHub — proteger branch, revisão, checks e fila de merge: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- Codex SDK — controlar trabalhos e integração: https://learn.chatgpt.com/docs/codex-sdk
- Codex App Server — eventos em streaming, threads, aprovações: https://learn.chatgpt.com/docs/app-server
- Anthropic — comparativo de Agent SDK, ferramentas e sessões: https://platform.claude.com/docs/en/managed-agents/migration

**Limites explícitos:** integrações de IA dependem de versão, autorização, capacidade de hooks/SDK e plano contratado; streaming de operações só é real quando a integração informa eventos. A prevenção de conflitos semânticos perfeita é impraticável; políticas, reservas, análise de contratos e testes reduzem o risco. Nem toda revisão de IA equivale a um review do provedor Git. O bot Discord não é a origem única de permissões. Deploy é sempre distinto de sincronização de código.

- Discord — OAuth2 para login e autorização: https://discord.com/developers/docs/topics/oauth2
- OpenAPI Initiative — especificar contratos de API: https://spec.openapis.org/oas/latest.html
