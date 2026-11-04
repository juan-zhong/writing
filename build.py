#!/usr/bin/env python3
"""Builds the Writings site from content/*.txt.

Usage:  python3 build.py

Each file in content/ is one work: a short header between two '---' lines,
then the text exactly as written. Blank lines separate stanzas/paragraphs;
two or more blank lines in a row make a wider gap. The text is never altered,
only placed into the page.

Output: index.html, zh/*.html, en/*.html, works/*.html (overwritten each run).
If fontTools is installed and fonts/source/LXGWWenKai-Regular.ttf exists, the
Kaiti subset (fonts/lxgw-wenkai-writings.woff2) is regenerated for the
characters used in titles and navigation.
"""
import html
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")

ME = "https://juan-zhong.github.io/me/"
ART = "https://juan-zhong.github.io/art/"
YEARS_EN = "2018–2026"
YEARS_ZH = "戊戌至丙午"

CATEGORIES = [  # order on the contents pages
    ("poems", "POEMS", "诗集", "Poems"),
    ("essays", "ESSAYS", "文集", "Essays"),
    ("translations", "TRANSLATIONS", "翻译", "Translations"),
    ("notes", "NOTES", "笔记", "Notes"),
]
CAT = {c[0]: c for c in CATEGORIES}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

KAI_CHARS = set()


def esc(s):
    return html.escape(s, quote=False)


def attr(s):
    return html.escape(s, quote=True)


def kai(s):
    """Text set in Kaiti: remember its characters for the font subset."""
    KAI_CHARS.update(s)
    return esc(s)


# ---------- content ----------

def load():
    works = []
    for name in sorted(os.listdir(CONTENT)):
        if not name.endswith(".txt"):
            continue
        raw = open(os.path.join(CONTENT, name), encoding="utf-8").read()
        m = re.match(r"---\n(.*?)\n---\n?(.*)\Z", raw, re.S)
        if not m:
            raise SystemExit(f"{name}: missing header")
        head = {}
        for line in m.group(1).split("\n"):
            if line.strip():
                k, _, v = line.partition(":")
                head[k.strip()] = v.strip()
        head["body"] = m.group(2).rstrip("\n")
        head["order"] = int(head.get("order", 99))
        works.append(head)
    by_cat = {c[0]: [] for c in CATEGORIES}
    for w in works:
        by_cat[w["category"]].append(w)
    for c in by_cat:
        # works still to be edited (status: draft) go to the end of their category
        by_cat[c].sort(key=lambda w: (w.get("status") == "draft", w["order"]))
    return by_cat


def date_zh(w):
    s = w.get("written", "")
    m = re.fullmatch(r"(\d{4})-(\d{2})", s)
    if m:
        return f"{m.group(1)} · {m.group(2)}"
    return s.replace("-", "–")


def date_en(w):
    s = w.get("written", "")
    m = re.fullmatch(r"(\d{4})-(\d{2})", s)
    if m:
        return f"{MONTHS[int(m.group(2)) - 1]} {m.group(1)}"
    return s.replace("-", "–")


def main_title(w):
    """Original language is the big title; the other is the small one."""
    if w["original"] == "en":
        return w["title_en"], "en", w["title_zh"], "zh"
    return w["title_zh"], "zh", w["title_en"], "en"


def title_html(w, tag, cls=""):
    big, big_lang, small, small_lang = main_title(w)
    big_h = f'<{tag} class="t-big {big_lang}{cls}" lang="{"zh-CN" if big_lang == "zh" else "en"}">{kai(big) if big_lang == "zh" else esc(big)}</{tag}>'
    small_h = f'<p class="t-small {small_lang}" lang="{"zh-CN" if small_lang == "zh" else "en"}">{kai(small) if small_lang == "zh" else esc(small)}</p>'
    return big_h + "\n" + small_h


# ---------- body text ----------

def blocks(body):
    """Paragraphs/stanzas split on blank lines; a run of 2+ blank lines is a gap."""
    out, cur, blanks = [], [], 0
    # U+2028/U+2029 are soft line breaks (Shift+Return in Notes): real line breaks, not spaces
    body = body.replace(" ", "\n").replace(" ", "\n")
    for line in body.split("\n"):
        if line.strip() == "":
            if cur:
                out.append(("p", cur))
                cur = []
            blanks += 1
        else:
            if blanks >= 2 and out:
                out.append(("gap", None))
            blanks = 0
            cur.append(line.rstrip())
    if cur:
        out.append(("p", cur))
    return out


def depth(line):
    """Outline depth = how many numeric segments the line starts with (e.g. 4.1.2.1.)."""
    # "4.1.2.1.跨性别女" -> 4, "4.1 按…" -> 2, "1. 染色体" -> 1; "46,XX" is not a number label
    m = re.match(r"(\d+(?:\.\d+)*)\.?(?=[^\d,.])", line)
    if not m:
        return 0
    return len(m.group(1).split("."))


def render_body(w):
    form = w.get("form", "lines")
    lang = "zh-CN" if w["original"] == "zh" else "en"
    parts = []
    last = 0  # outline: depth of the last numbered line; unnumbered lines sit under it
    for kind, lines in blocks(w["body"]):
        if kind == "gap":
            parts.append('<div class="gap" aria-hidden="true"></div>')
            continue
        if form == "prose":
            parts.append("<p>" + "<br>".join(esc(l) for l in lines) + "</p>")
        elif form == "outline":
            spans = []
            for l in lines:
                d = min(depth(l), 7)
                if d:
                    last = d
                    spans.append(f'<span class="ln item d{d}">{esc(l)}</span>')
                else:
                    spans.append(f'<span class="ln cont d{min(last, 7)}">{esc(l)}</span>')
            parts.append('<p class="st">' + "".join(spans) + "</p>")
        else:  # verse, lines
            parts.append('<p class="st">' + "".join(f'<span class="ln">{esc(l)}</span>' for l in lines) + "</p>")
    return f'<div class="text {form} {"zh-body" if lang == "zh-CN" else "en-body"}" lang="{lang}">\n' + "\n".join(parts) + "\n</div>"


def render_lyrics(w):
    """Pasted English translation, set like a poem (stanzas separated by blank lines)."""
    parts = []
    for kind, lines in blocks(w["body"]):
        if kind == "gap":
            parts.append('<div class="gap" aria-hidden="true"></div>')
            continue
        parts.append('<p class="st">' + "".join(f'<span class="ln">{esc(l)}</span>' for l in lines) + "</p>")
    return '<div class="text verse en-body lyrics" lang="en">\n' + "\n".join(parts) + "\n</div>"


# ---------- page shell ----------

GFONT = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400&amp;display=swap">'


# back-to-top button, the same as on /me and /art (appears after scrolling down)
TOTOP = """<a href="#" class="to-top" id="toTop" aria-label="Back to top" title="Back to top">↑</a>
<script>
(function () {
  var b = document.getElementById('toTop');
  function f() { b.classList.toggle('show', window.scrollY > 600); }
  window.addEventListener('scroll', f, { passive: true }); f();
  b.addEventListener('click', function (e) { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); });
})();
</script>"""


def page(path, lang, title, body, body_class, zh_body=False, remember=None, extra_head=""):
    depth_ = path.count("/")
    r = "../" * depth_
    remember_js = ""
    if remember:
        remember_js = f"<script>try{{localStorage.setItem('writings-lang','{remember}')}}catch(e){{}}</script>"
    doc = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="Writings by Juan Zhong 钟娟: poems, essays, translations and notes.">
<link rel="stylesheet" href="{r}styles.css">
{GFONT if zh_body else ""}{extra_head}
{remember_js}
</head>
<body class="{body_class}">
{body.replace("{R}", r)}
{TOTOP}
</body>
</html>
"""
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full) or ROOT, exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(doc)


def tabs(lang, other_href=None):
    # other_href is no longer shown: the 中 / EN switch lives only on the two contents pages
    if lang == "zh":
        return f"""<nav class="tabs" aria-label="导航">
<a class="zh" href="{{R}}index.html">{kai("随笔")}</a>
<a class="zh" href="{{R}}zh/index.html">{kai("目录")}</a>
</nav>"""
    return f"""<nav class="tabs" aria-label="Navigation">
<a class="en tab-en" href="{{R}}index.html">A COLLECTION OF WRITINGS</a>
<a class="en tab-en" href="{{R}}en/index.html">CONTENTS</a>
</nav>"""


def footer(lang):
    zh_me = f' <span class="zh">{kai("钟娟")}</span>'
    zh_art = f' <span class="zh">{kai("摄影")}</span>' if lang == "zh" else ""
    return f"""<footer class="site-foot">
<a href="{ME}">JUAN ZHONG{zh_me}</a>
<a href="{ART}">ART{zh_art}</a>
</footer>"""


def cat_header(cat):
    _, big, zh, _ = CAT[cat]
    return f"""<header class="cat-head">
<h1 class="en">{big}</h1>
<p class="zh" lang="zh-CN">{kai(zh)}</p>
</header>"""


# ---------- pages ----------

def build_intro():
    zh = [
        "求学期间，我接受过不同的人文社科领域的学术训练。这些学习经历和我的日常生活经验，是我思考和写作的来源。这里选录了我在学术论文之外的习作，包括诗歌、散文、杂记、笔记和翻译。",
        "我用中文和英文写作，偶尔也做翻译。目录可选择中文或英文，正文则按各篇作品的语言呈现。",
    ]
    en = [
        "Over the years, I received academic training in various fields across the humanities and social sciences. My studies and everyday experiences inform my thinking and writing. This site collects some of my writings beyond academic papers, including poems, essays, notes, and translations.",
        "I write in Chinese and English and occasionally translate. The table of contents can be viewed in Chinese or English, while each piece is presented in the language in which it was written or translated.",
    ]
    zh_p = "\n".join(f"<p>{esc(x)}</p>" for x in zh)
    en_p = "\n".join(f"<p>{esc(x)}</p>" for x in en)
    body = f"""<main class="card intro spread-card">
<div class="spread">
<section class="side side-zh" lang="zh-CN">
<h1 class="zh">{kai("随笔")}</h1>
<div class="intro-body zh-body">
{zh_p}
</div>
<a class="go zh" href="zh/index.html">{kai("目录")} →</a>
</section>
<div class="spine" aria-hidden="true"></div>
<section class="side side-en" lang="en">
<h1><span class="kick">A Collection of</span>WRITINGS</h1>
<div class="intro-body">
{en_p}
</div>
<a class="go" href="en/index.html">CONTENTS →</a>
</section>
</div>
<div class="intro-foot">
<a class="zh" href="{ME}" lang="zh-CN">{kai("钟娟")}</a>
<span class="fig">{YEARS_EN}</span>
<a class="en-name" href="{ME}">JUAN ZHONG</a>
</div>
</main>"""
    page("index.html", "en", "A Collection of Writings 随笔 · Juan Zhong", body, "p-intro", zh_body=True)


def build_index_zh(by):
    groups = []
    for cat, _, zh, _ in CATEGORIES:
        items = [f'<a class="m" href="{cat}.html">{kai(zh)}</a>']
        for w in by[cat]:
            t = kai(w["title_zh"])
            mk = ""
            if w["original"] == "en":
                mk = "英"
            if cat == "translations":
                mk = "中译英" if w.get("direction") == "zh-en" else "英译中"
            if w.get("zh_index_mark"):
                mk = w["zh_index_mark"]
            draft = w.get("status") == "draft"
            if draft:
                mk = "待整理"
            mk_h = f'<span class="mk">{kai(mk)}</span>' if mk else ""
            if cat in ("poems", "translations"):
                href = f"{cat}.html#{w['slug']}"
            else:
                href = work_href(w)
            if draft:
                items.append(f'<span class="s x">{t}{mk_h}</span>')
            else:
                items.append(f'<a class="s" href="{href}">{t}{mk_h}</a>')
        # the number of entry columns sets the group's width in CSS (Safari can't measure vertical text in a grid reliably)
        groups.append(f'<div class="g" style="--n:{len(items) - 1}">\n' + "\n".join(items) + "\n</div>")
    body = f"""<main class="card vcard">
<div class="title"><h1 class="v"><a href="../index.html">{kai("随笔")}</a></h1></div>
<nav class="toc" aria-label="目录">
{chr(10).join(groups)}
</nav>
<div class="foot"><p class="year">{kai(YEARS_ZH)}</p><p class="note">{kai("标英者原以英文写成")}</p><p class="name"><a href="{ME}">{kai("钟娟")}</a></p></div>
<a class="lang en" href="../en/index.html" lang="en">EN</a>
</main>"""
    page("zh/index.html", "zh-CN", "随笔 · 钟娟", body, "p-index-zh", remember="zh")


def build_index_en(by):
    groups = []
    for cat, _, _, en in CATEGORIES:
        subs = []
        for w in by[cat]:
            t = esc(w["title_en"])
            small = ""
            if w["original"] == "en" and cat == "poems":
                small = "(EN)"
            if cat == "translations":
                small = "(ZH → EN)" if w.get("direction") == "zh-en" else "(EN → ZH)"
            draft = w.get("status") == "draft"
            if draft:
                small = "(to be edited)"
            small_h = f"<small>{small}</small>" if small else ""
            if cat in ("poems", "translations"):
                href = f"{cat}.html#{w['slug']}"
            else:
                href = work_href(w)
            if draft:
                subs.append(f'<span class="x">{t}{small_h}</span>')
            else:
                subs.append(f'<a href="{href}">{t}{small_h}</a>')
        groups.append(f'<div><a class="main" href="{cat}.html">{en}</a>\n<div class="subs">{"".join(subs)}</div></div>')
    name = "".join(f"<span>{c}</span>" for c in "JUAN") + '<span class="gap"></span>' + "".join(f"<span>{c}</span>" for c in "ZHONG")
    body = f"""<main class="card pcard">
<a class="lang zh" href="../zh/index.html" lang="zh-CN">{kai("中")}</a>
<a class="name" href="{ME}" aria-label="Juan Zhong">{name}</a>
<div class="body">
<p class="kicker"><a href="../index.html">A Collection of</a></p>
<h1 class="big"><a href="../index.html">WRITINGS</a></h1>
<nav class="toc" aria-label="Contents">
{chr(10).join(groups)}
</nav>
<div class="endrow"><p class="year fig">{YEARS_EN}</p><p class="note">(EN) originally written in English;<br>all other works were written in Chinese.</p></div>
</div>
</main>"""
    page("en/index.html", "en", "A Collection of Writings · Juan Zhong", body, "p-index-en", remember="en")


def poem_section(w, lang):
    big, big_lang, small, small_lang = main_title(w)
    meta = []
    if lang == "zh":
        if w.get("with_zh"):
            meta.append(f'<span class="zh">{kai(w["with_zh"])}</span>')
        meta.append(date_zh(w))
        if w["original"] == "en":
            meta.append(f'<span class="zh">{kai("英文原作")}</span>')
    else:
        if w.get("with_en"):
            meta.append(esc(w["with_en"]).upper())
        meta.append(date_en(w).upper())
        if w["original"] == "en":
            meta.append("(EN)")
    return f"""<section class="work" id="{w['slug']}">
{title_html(w, "h2")}
<p class="meta">{" · ".join(meta)}</p>
{render_body(w)}
</section>"""


def build_poems(by, lang):
    ws = by["poems"]
    jump = []
    for w in ws:
        big, big_lang, _, _ = main_title(w)
        cls = "zh" if big_lang == "zh" else "en it"
        jump.append(f'<a class="{cls}" href="#{w["slug"]}">{kai(big) if big_lang == "zh" else esc(big)}</a>')
    note = ""
    if lang == "en":
        note = '<p class="cat-note">(EN) originally written in English; the other poems were written in Chinese.</p>'
    other = "../en/poems.html" if lang == "zh" else "../zh/poems.html"
    body = f"""{tabs(lang, other)}
{cat_header("poems")}
<nav class="jump" aria-label="{"本页诗目" if lang == "zh" else "Poems on this page"}">{"".join(jump)}</nav>
<main class="col col-poems">
{chr(10).join(poem_section(w, lang) for w in ws)}
{note}
</main>
{footer(lang)}"""
    title = "诗集 · 随笔 · 钟娟" if lang == "zh" else "Poems · Writings · Juan Zhong"
    page(f"{lang}/poems.html", "zh-CN" if lang == "zh" else "en", title, body, f"p-cat p-{lang}", zh_body=True, remember=lang)


def work_href(w):
    """Link to a work from zh/ or en/: its own page, or its PDF if the work is kept as a PDF."""
    if w.get("pdf"):
        return w["pdf"] if w["pdf"].startswith("http") else "../" + w["pdf"]
    return f"../works/{w['slug']}.html"


def row(w, lang, href):
    big, big_lang, small, small_lang = main_title(w)
    draft = w.get("status") == "draft"
    big_h = kai(big) if big_lang == "zh" else esc(big)
    small_h = kai(small) if small_lang == "zh" else esc(small)
    flag = ""
    if draft:
        flag = f'<span class="flag zh">{kai("待整理")}</span>' if lang == "zh" else '<span class="flag en">(to be edited)</span>'
    if w.get("pdf") and w.get("category") == "essays":
        flag += '<span class="flag en">PDF</span>'
    d = date_zh(w) if lang == "zh" else date_en(w)
    if w.get("updated") == "yes":
        d = f'{d} <span class="zh">{kai("更新")}</span>' if lang == "zh" else f"Updated {d}"
    inner = f"""<span class="rt"><span class="t {big_lang}" lang="{"zh-CN" if big_lang == "zh" else "en"}">{big_h}{flag}</span><span class="st2 {small_lang}" lang="{"zh-CN" if small_lang == "zh" else "en"}">{small_h}</span></span><span class="d">{d}</span>"""
    if draft or not href:
        return f'<div class="row x">{inner}</div>'
    return f'<a class="row" href="{href}">{inner}</a>'


def build_essays(by, lang):
    rows = [row(w, lang, work_href(w)) for w in by["essays"]]
    note = '<p class="cat-note">All essays were written in Chinese.</p>' if lang == "en" else ""
    other = "../en/essays.html" if lang == "zh" else "../zh/essays.html"
    body = f"""{tabs(lang, other)}
{cat_header("essays")}
<main class="col list">
{chr(10).join(rows)}
{note}
</main>
{footer(lang)}"""
    title = "文集 · 随笔 · 钟娟" if lang == "zh" else "Essays · Writings · Juan Zhong"
    page(f"{lang}/essays.html", "zh-CN" if lang == "zh" else "en", title, body, f"p-cat p-{lang}", remember=lang)


def build_notes(by, lang):
    rows = [row(w, lang, work_href(w)) for w in by["notes"]]
    note = '<p class="cat-note">Written in Chinese.</p>' if lang == "en" else ""
    other = "../en/notes.html" if lang == "zh" else "../zh/notes.html"
    body = f"""{tabs(lang, other)}
{cat_header("notes")}
<main class="col list">
{chr(10).join(rows)}
{note}
</main>
{footer(lang)}"""
    title = "笔记 · 随笔 · 钟娟" if lang == "zh" else "Notes · Writings · Juan Zhong"
    page(f"{lang}/notes.html", "zh-CN" if lang == "zh" else "en", title, body, f"p-cat p-{lang}", remember=lang)


def translation_section(w, lang):
    if w.get("kind") == "lyrics":
        if lang == "zh":
            credit = f'{kai(w["artist_zh"])} {kai("原唱")} · {kai("钟娟")} {kai("英译")} · {kai("中译英")}'
            credit = f'<p class="meta zh">{credit}</p>'
        else:
            credit = f'<p class="meta">{esc(w["artist_en"]).upper()} · TRANSLATED BY JUAN ZHONG · ZH → EN</p>'
        btns = []
        if w.get("pdf"):  # the translation sheet, uploaded by hand to pdf/
            href = w["pdf"] if w["pdf"].startswith("http") else "../" + w["pdf"]
            label = f'<span class="zh">{kai("译文")}</span> PDF' if lang == "zh" else "TRANSLATION (PDF)"
            btns.append(f'<a class="btn" href="{attr(href)}">{label}</a>')
        # the listen link now lives inside the translation PDF, so no button here
        btn = f'<div class="btns">{"".join(btns)}</div>' if btns else ""
        text = render_lyrics(w) if w["body"].strip() else ""
        return f"""<section class="work tr" id="{w['slug']}">
{title_html(w, "h2")}
{credit}
{btn}
{text}
</section>"""
    # annotated translation published as PDF
    if lang == "zh":
        credit = f'<p class="meta zh">{kai(w["author_zh"])} {kai("原著")} {w["source_year"]} · {kai("钟娟")} {kai("注释英译")} {w["written"]} · {kai("中译英")}</p>'
        btn_label = f'<span class="zh">{kai("译文")}</span> PDF'
    else:
        credit = f'<p class="meta">{esc(w["author_en"]).upper()}, {w["source_year"]} · ANNOTATED TRANSLATION BY JUAN ZHONG, {w["written"]} · ZH → EN</p>'
        btn_label = "TRANSLATION (PDF)"
    return f"""<section class="work tr" id="{w['slug']}">
{title_html(w, "h2")}
{credit}
<p class="course">{esc(w["course"])}</p>
<a class="btn" href="{attr(w["pdf"])}">{btn_label}</a>
</section>"""


def build_translations(by, lang):
    other = "../en/translations.html" if lang == "zh" else "../zh/translations.html"
    body = f"""{tabs(lang, other)}
{cat_header("translations")}
<main class="col">
{chr(10).join(translation_section(w, lang) for w in by["translations"])}
</main>
{footer(lang)}"""
    title = "翻译 · 随笔 · 钟娟" if lang == "zh" else "Translations · Writings · Juan Zhong"
    page(f"{lang}/translations.html", "zh-CN" if lang == "zh" else "en", title, body, f"p-cat p-{lang}", zh_body=True, remember=lang)


def build_work(w, siblings):
    cat = w["category"]
    _, big_cat, zh_cat, en_cat = CAT[cat]
    orig = w["original"]
    nav_zh = tabs("zh", f"../en/{cat}.html").replace("<nav ", f'<nav data-nav="zh"{"" if orig == "zh" else " hidden"} ')
    nav_en = tabs("en", f"../zh/{cat}.html").replace("<nav ", f'<nav data-nav="en"{"" if orig == "en" else " hidden"} ')
    meta = [date_zh(w)]
    if w.get("updated") == "yes":
        meta.append(f'<span class="zh">{kai("更新")}</span> updated')
    note = ""
    if w.get("content_note"):
        note = f'<p class="cnote"><span class="zh" lang="zh-CN">{kai(w["content_note"])}</span><span class="en" lang="en">Contains sensitive content, including suicide. Please read with care.</span></p>'
    i = siblings.index(w)
    live = [s for s in siblings if s.get("status") != "draft" and not s.get("pdf")]
    j = live.index(w)
    prev_w = live[j - 1] if j > 0 else None
    next_w = live[j + 1] if j + 1 < len(live) else None

    def link(x, arrow_left):
        if not x:
            return "<span></span>"
        big, bl, _, _ = main_title(x)
        t = f'<span class="{bl}">{kai(big) if bl == "zh" else esc(big)}</span>'
        if x.get("zh_index_mark"):  # tell the two 杂记 apart
            t += f' <span class="pn-mark">{date_zh(x).split(" ")[0]}</span>'
        return f'<a href="{x["slug"]}.html">{"← " + t if arrow_left else t + " →"}</a>'

    body = f"""{nav_zh}
{nav_en}
<header class="work-head">
{title_html(w, "h1")}
<p class="meta">{" · ".join(meta)}</p>
{note}
</header>
<main class="col article">
{render_body(w)}
</main>
<nav class="pn" aria-label="Previous and next">{link(prev_w, True)}<a class="up" href="../zh/{cat}.html" data-up-zh="../zh/{cat}.html" data-up-en="../en/{cat}.html"><span class="zh">{kai(zh_cat)}</span> {big_cat}</a>{link(next_w, False)}</nav>
{footer("zh" if orig == "zh" else "en")}
<script>
(function(){{
  var l; try {{ l = localStorage.getItem('writings-lang'); }} catch (e) {{}}
  if (l !== 'zh' && l !== 'en') return;
  var navs = document.querySelectorAll('[data-nav]');
  for (var k = 0; k < navs.length; k++) navs[k].hidden = navs[k].getAttribute('data-nav') !== l;
  var up = document.querySelector('.pn .up'); if (up) up.href = up.getAttribute('data-up-' + l);
}})();
</script>"""
    big, _, _, _ = main_title(w)
    page(f"works/{w['slug']}.html", "zh-CN" if orig == "zh" else "en", f"{big} · {zh_cat} · 随笔 · 钟娟", body, f"p-work form-{w.get('form', 'lines')}", zh_body=True)


def subset_font():
    src = os.path.join(ROOT, "fonts", "source", "LXGWWenKai-Regular.ttf")
    out = os.path.join(ROOT, "fonts", "lxgw-wenkai-writings.woff2")
    chars = "".join(sorted(c for c in KAI_CHARS if ord(c) > 127))
    with open(os.path.join(ROOT, "fonts", "kai-chars.txt"), "w", encoding="utf-8") as f:
        f.write(chars + "\n")
    try:
        from fontTools import subset
    except ImportError:
        print("fontTools not installed: kept the existing Kaiti subset")
        return
    if not os.path.exists(src):
        print("fonts/source/LXGWWenKai-Regular.ttf not found: kept the existing Kaiti subset")
        return
    try:
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["*"]
        f = subset.load_font(src, opts)
        s = subset.Subsetter(opts)
        s.populate(text=chars + "·—–")
        s.subset(f)
        subset.save_font(f, out, opts)
        print(f"Kaiti subset: {len(chars)} characters, {os.path.getsize(out)//1024} KB")
    except Exception as e:  # e.g. brotli missing: keep the old subset
        print(f"Could not rebuild the Kaiti subset ({e}); kept the existing one")


def main():
    by = load()
    build_intro()
    build_index_zh(by)
    build_index_en(by)
    for lang in ("zh", "en"):
        build_poems(by, lang)
        build_essays(by, lang)
        build_translations(by, lang)
        build_notes(by, lang)
    for cat in ("essays", "notes"):
        for w in by[cat]:
            if w.get("status") != "draft" and not w.get("pdf"):
                build_work(w, by[cat])
    subset_font()
    print("built")


if __name__ == "__main__":
    main()
