# Writings · 书写选集

**Visit the site:** https://juan-zhong.github.io/writing/

Poems, essays, translations and notes by Juan Zhong 钟娟, in Chinese and English.

## What is in this repository

| Path | What it is |
|---|---|
| `index.html` | Home: bilingual introduction, choose 中文 or English |
| `zh/` , `en/` | Contents pages (题跋 vertical layout / poster layout) and the category pages |
| `works/` | One page per essay or note |
| `content/` | **The texts themselves**, one `.txt` file per work. Edit these, not the HTML |
| `build.py` | Turns `content/` into the HTML pages |
| `styles.css` | Shared look (same fonts and colours as /me and /art) |
| `fonts/` | Self-hosted fonts (OFL licences included) |

## Editing or adding a work

1. Open or create a file in `content/`. Each file starts with a short header:

   ```
   ---
   slug: xianyou              # file name of the page / anchor
   category: poems            # poems, essays, translations or notes
   title_zh: 闲游
   title_en: Idle Wandering
   original: zh               # zh or en: decides which title is large
   written: 2025-11           # or 2018-2019
   order: 2                   # position inside the category
   form: verse                # verse (poems), lines, prose, outline (numbered notes)
   ---
   ```

   Optional keys: `status: draft` (shown greyed as 待整理 / to be edited, no page),
   `zh_index_mark: 辛丑` (small note in the Chinese contents), `content_note: …`,
   `updated: yes`, `with_en` / `with_zh` (co-authors).
   Translations also use `direction: zh-en`, `kind: lyrics` or `pdf`, `listen:` (link to an official recording), `pdf:`.

2. Below the header, paste the text exactly as written. Blank lines separate
   stanzas or paragraphs; two or more blank lines make a wider gap.
   For lyrics translations, alternate lines: one Chinese line, then its English line.

3. Run `python3 build.py`, then commit everything (content and the regenerated HTML).

New Chinese characters in titles fall back to the system Kaiti font until the
font subset is rebuilt (`pip install fonttools brotli`, put `LXGWWenKai-Regular.ttf`
from https://github.com/lxgw/LxgwWenKai/releases into `fonts/source/`, run `build.py`).

## License

Texts © 2018–2026 Juan Zhong. All rights reserved.
Translated source texts remain with their authors and rights holders.
Site code is released under CC0 (see `LICENSE-CODE`). Fonts: SIL Open Font License (see `fonts/`).
