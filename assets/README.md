# Assets

Assets are split by the code or document that consumes them. The split is part
of the public repository contract, not a staging area.

## Layout

| Folder | Contents | Consumer |
|---|---|---|
| `docs/` | neutral, text-free visuals for public documentation | `README.md` and `docs/` |
| `bot/` | panel, moderation, welcome, seasonal, and compact neutral artwork | `bot/main.py` and the bot package |

Documentation visuals are intentionally transparent PNGs with a restrained
neutral palette. They explain relationships such as coordination and review;
they do not prove that an integration or two-computer test is complete.

Bot artwork may contain product-specific text or seasonal styling. Keep it in
`assets/bot/` and load it through the bot entry point. Do not reuse it in public
architecture diagrams.

## Change rules

- Give every asset one documented purpose and a stable filename.
- Do not include credentials, identifiers, local paths, telemetry, or private
  conversation content in an image.
- Validate dimensions, PNG format, alpha behavior, and rendered appearance
  before opening a Pull Request.
- Update the consuming README or document in the same change.
