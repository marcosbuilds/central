# Technical references consulted

Official sources used as a basis for existing capabilities, **not as proof that
Central is implemented**:

- Git — record changes and history: https://git-scm.com/docs/git-commit
- GitHub — protect branches, reviews, checks, and merge queue:
  https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- Codex SDK — control work and integration: https://learn.chatgpt.com/docs/codex-sdk
- Codex App Server — streaming events, threads, approvals: https://learn.chatgpt.com/docs/app-server
- Anthropic — Agent SDK, tools, and sessions comparison: https://platform.claude.com/docs/en/managed-agents/migration

**Explicit limits:** AI integrations depend on version, authorization,
hook/SDK capability, and the contracted plan; operation streaming is real only
when the integration reports events. Perfect semantic-conflict prevention is
impractical; policies, reservations, contract analysis, and tests reduce risk.
Not every AI review is equivalent to a Git-provider review. The Discord bot is
not the sole source of permissions. Deployment is always distinct from code synchronization.

- Discord — OAuth2 for login and authorization: https://discord.com/developers/docs/topics/oauth2
- OpenAPI Initiative — specify API contracts: https://spec.openapis.org/oas/latest.html
