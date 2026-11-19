# Assets

Assets are split by the code or document that consumes them. The split is part
of the public repository contract, not a staging area.

There are intentionally no top-level folders named after file formats such as
`png/` or `svg/`: the consumer boundary is canonical and the file extension is
only an implementation detail. Frontend-only artwork remains in
`bot/site/assets/` and is not mixed into this runtime/documentation tree.

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

The transparent 128x128 `peace_civil.png`, `peace_verify.png`,
`peace_pending.png`, `peace_set.png`, `peace_alert.png`, `peace_dove.png`,
`peace_badge.png`, and `peace_helper.png` files are Peace application-emoji
artwork generated through the ChatGPT browser on 2026-11-13 from a Peace icon
sheet. They use RGBA PNG with transparent margins and remain below Discord's
256 KB application-emoji limit. The matching application emojis are uploaded
under the same names for use by Peace Tools. `peace_bot.png` is a local
semantic alias of `peace_helper.png` for generic bot identity messages and is
not a separate uploaded emoji.

The current `assets/bot/set.png`, `assets/bot/verification.png`,
`assets/bot/ops.png`, `assets/bot/support.png`, and `assets/bot/welcome.png` are
reviewed, text-free 2:1 banner assets generated from consolidated visual briefs
for the bot panels. `assets/bot/automod.png` remains unchanged because
spam-control artwork is a strict panel contract. The legacy
`welcome-halloween.png` file remains available as migration history but is no
longer selected for new welcome messages.

The public Peace home consumes `bot/site/assets/peace-bird.png`, a transparent
RGBA cutout of the Peace bird supplied for the public-site redesign. It is site
runtime artwork rather than a documentation visual; the original attachment is
not a runtime dependency.

The public Peace site also consumes `bot/site/assets/discord.svg`, a local
theSVG Discord default icon used only to identify links that redirect to the
Peace Discord invite. The source, declared license metadata, retrieval date,
hash, and brand-use constraint are recorded in [`docs/bot/site.md`](../docs/bot/site.md).

The public Peace flow also consumes the following site-only visuals under
`bot/site/assets/`. The four 1672x941 RGB background PNGs are atmospheric,
text-free illustrations generated through the ChatGPT browser on 2026-11-15
for the candidature, process, exam, and authenticated member surfaces. They
keep the main copy area quiet and place the visual focal point away from the
reading column. The three Discord verification crops are sanitized UI crops
from the authorized Discord reference used for the candidature guide: they
contain no account identifiers, credentials, or private conversation content.

| Asset | Dimensions | Purpose |
|---|---:|---|
| `bot/site/assets/peace-candidature-bg.png` | 1672x941 | candidature background |
| `bot/site/assets/peace-process-bg.png` | 1672x941 | process and set-up background |
| `bot/site/assets/peace-exam-bg.png` | 1672x941 | candidate exam and management background |
| `bot/site/assets/peace-members-bg.png` | 1672x941 | authenticated member-area background |
| `bot/site/assets/discord-verify-channel.png` | 1060x68 | cropped `#verify` channel cue |
| `bot/site/assets/discord-verification-card-clean.png` | 1905x826 | cropped verification panel |
| `bot/site/assets/discord-verification-action-clean.png` | 1050x210 | cropped “Iniciar verificação” action |

The crops are rendered responsively as individual guide steps rather than as
one panoramic screenshot. Older unsanitized guide composites are intentionally
not retained in the site asset set.

`bot/site/assets/fonts/PeaceFonte-Regular.woff2` is the supplied PeaceFonte
display font used for the Peace wordmark and shared contextual titles. It is
distributed under the SIL Open Font License 1.1; the public copy of the terms
is kept beside the font in `bot/site/assets/fonts/PeaceFonte-LICENSE.txt`.

## Change rules

- Give every asset one documented purpose and a stable filename.
- Do not include credentials, identifiers, local paths, telemetry, or private
  conversation content in an image.
- Validate dimensions, PNG format, alpha behavior, and rendered appearance
  before opening a Pull Request.
- Update the consuming README or document in the same change.
- `bot/site/assets/civil-police-verification.png` — badge visual used to identify members whose Civil exam is approved in the Peace member directory. Source: user-provided attachment in the task; public-purpose asset.
