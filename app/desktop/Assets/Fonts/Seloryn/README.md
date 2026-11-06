# seloryn-font / v2.0

Experimental package candidate for the Seloryn brand family. The supplied
archive is preserved privately with its source hash; this directory is the
public package source and is not a stable GitHub release.

Custom font for the [Seloryn](https://github.com/marcosbuilds/Seloryn) brand,
visually derived from the official `assets/brand/seloryn-symbol.svg`.
**Languages: English + Brazilian Portuguese.** The local symbol in this package
matches the repository's canonical copy.

## Revised concept

The first version had too many conventional rings and stems. v2 uses a recurring
formal vocabulary: **two curve movements without artificial connections;
horizontal exits; rounded terminals; and intentional openings in bowl-shaped
letters**. For example, `a`, `b`, `d`, `e`, `g`, `o`, `p`, and `q` use
deliberately open bowls; `n`, `h`, `m`, and `r` use independent cues; `O`, `Q`,
and `0` repeat the two-flow construction. The font keeps a consistent weight
per variant, but curves and openings are not blindly copied from a single glyph.

- **Light 300**: 55/1000 em stroke; airy for phrases and titles.
- **Bold 700**: 113/1000 em stroke; signature, posters, and headings.
- **138 characters**: readable ASCII for EN + PT-BR, plus `Á À Â Ã É Ê Í Ó Ô Õ Ú Ç`
  and lowercase equivalents, `ª º`, `€ £`, typographic quotation marks, and
  text/code punctuation.
- **Proportional, not monospaced**: ideal for branding, titles, pages, and
  project materials. For long code or column alignment, we recommend a
  complementary monospaced font; the demonstration application uses a
  supporting monospaced font for code itself.

## Files

```
seloryn-font/
├─ fonts/
│  ├─ seloryn-font-light.ttf
│  ├─ seloryn-font-bold.ttf
│  ├─ seloryn-font-light.woff
│  ├─ seloryn-font-bold.woff
│  ├─ seloryn-font-light.woff2
│  └─ seloryn-font-bold.woff2
├─ previews/
│  ├─ seloryn-font-specimen.png
│  ├─ seloryn-font-real-use.png
│  └─ seloryn-font-wordmark-{light,bold}.svg
├─ examples/
│  └─ tensor-matmul.sely           # literal copy of the example published on GitHub
├─ source/
│  ├─ build_seloryn_font.py
│  └─ requirements.txt
├─ seloryn-font.css
├─ seloryn-symbol.svg              # official reference symbol (two colors)
├─ index.html                      # font lab + real Seloryn example
├─ LICENSE
└─ README.md
```

## Use on a website

Copy `fonts/` and `seloryn-font.css` while preserving the paths. Add this to HTML:

```html
<link rel="stylesheet" href="/assets/seloryn-font/seloryn-font.css">
<h1 style="font-family:'Seloryn Font';font-weight:700">Seloryn</h1>
<p style="font-family:'Seloryn Font';font-weight:300">Verifiable code.</p>
```

`index.html` opens offline and demonstrates real font usage in an interface
concept with [real `tensor-matmul.sely` code](https://github.com/marcosbuilds/Seloryn/blob/master/examples/tensors/tensor-matmul.sely) —
**it does not represent an executed run or a screenshot of the official site**.
The weight buttons and slider let you test text in both variants.

## Install on Windows

Open both `.ttf` files, click **Install**, and select the **Seloryn Font** family
in applications with either the Light or Bold style.

## Generator file

To regenerate in a Python environment:

```bash
python -m pip install -r source/requirements.txt
python source/build_seloryn_font.py
```

Strokes are described individually for each letter, including Bézier outlines;
the script generates vector curves and builds TrueType/WOFF/WOFF2 files. Basic
OT kerning is included.

## License

MIT, compatible with the public license consulted on 2026-10-28. See `LICENSE`.
