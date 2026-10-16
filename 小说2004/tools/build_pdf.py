# -*- coding: utf-8 -*-
"""
把「正文_读者版/*.md」排成书心尺寸的 HTML，再交给 Chrome headless 出 PDF。

── 2026-10-13 改版（原脚本写死旧版 正文/ 1—130 章）──
  · SRC 默认改到 `正文_读者版/`（export_reader.py --plain --merge 的产物）
  · 封面副标题／年份可参数化（本次：第 1 — 30 章 / 2006 — 2007）
  · 新增：`······` 场景分隔符 → <p class="ell">（此前旧稿用 `## 一`，现在不用了）
  · 新增：读者版章标题是**裸行**（无 `# ` 前缀），按 `第N章` 识别
  · 新增：`--pdf` 一步到位调 Chrome headless 出 PDF

── 用法 ──
    python3 tools/build_pdf.py                         # 默认 1—30 章，出 PDF
    python3 tools/build_pdf.py --no-pdf                # 只出 HTML，自己用浏览器打印
    python3 tools/build_pdf.py --src 正文 --sub '第 1 — 130 章' --years '2004 — 2012'

输出：`/tmp/novel_pdf/book.html` + `--out-pdf` 指定路径（默认项目根 带着GPT重回高中_1-30章.pdf）
"""
import argparse
import html
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')

DEFAULT_SRC = os.path.join(ROOT, '正文_读者版')
DEFAULT_OUT_HTML = '/tmp/novel_pdf/book.html'
DEFAULT_OUT_PDF = os.path.join(ROOT, '带着GPT重回高中_1-30章.pdf')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

SEP = '······'


def chap_key(fn):
    m = re.match(r'第0?(\d+)章', fn)
    return int(m.group(1)) if m else 9999


def inline(s):
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
    return s


def parse_chapter(raw, fallback_title):
    """读者版：首行是裸标题「第N章 xxx」，其后段落；`······` 为场景分隔。"""
    title, body = '', []
    title_done = False
    for ln in raw.split('\n'):
        st = ln.strip()
        if not st:
            continue
        if not title_done and re.match(r'^第0?\d+章', st):
            title = st
            title_done = True
            continue
        if st.startswith('# '):
            title = st[2:].strip()
            title_done = True
            continue
        if st.startswith('## '):
            body.append('<h2>%s</h2>' % inline(st[3:].strip()))
            continue
        if st.startswith('### '):
            body.append('<h3>%s</h3>' % inline(st[4:].strip()))
            continue
        if re.match(r'^-{3,}$', st) or st == '***':
            body.append('<hr/>')
            continue
        if st in (SEP, '······', '……'):
            body.append('<p class="ell">%s</p>' % st)
            continue
        body.append('<p>%s</p>' % inline(st))
    return title or fallback_title, '\n'.join(body)


CSS = """
@page { size: 152mm 228mm; margin: 18mm 16mm 16mm;
  @bottom-center { content: counter(page); font-family:"PingFang SC"; font-size:9pt; color:#888; } }
html,body{ margin:0; padding:0; }
body{ font-family:"PingFang SC","Hiragino Sans GB","Heiti SC","Songti SC",serif;
  font-size:11.5pt; line-height:1.85; color:#1a1a1a; text-align:justify; }
h1{ font-size:20pt; line-height:1.4; text-align:center; margin:0 0 22pt; font-weight:600;
  letter-spacing:1px; page-break-after:avoid; }
h2{ font-size:13pt; margin:20pt 0 10pt; font-weight:600; color:#333; page-break-after:avoid; }
h3{ font-size:12pt; margin:16pt 0 8pt; font-weight:600; page-break-after:avoid; }
p{ margin:0 0 10pt; text-indent:2em; }
p.ell{ text-align:center; text-indent:0; margin:10pt 0; color:#666; letter-spacing:3px; }
hr{ border:none; border-top:1px solid #ddd; margin:16pt 0; }
strong{ font-weight:700; }
em{ font-style:italic; color:#444; }
.chapter{ page-break-before:always; }
.chapter:first-of-type{ page-break-before:avoid; }
.cover{ page-break-after:always; text-align:center; padding-top:60mm; }
.cover h1{ font-size:30pt; margin-bottom:8pt; letter-spacing:4px; }
.cover .sub{ font-size:12pt; color:#666; letter-spacing:2px; }
.cover .yr{ margin-top:40mm; font-size:10pt; color:#999; }
.toc{ page-break-after:always; }
.toc h2{ text-align:center; font-size:16pt; margin-bottom:18pt; }
.toc ul{ list-style:none; padding:0; margin:0; columns:2; column-gap:14mm; }
.toc li{ font-size:9.5pt; line-height:1.9; break-inside:avoid; }
.toc a{ color:#1a1a1a; text-decoration:none; }
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=DEFAULT_SRC)
    ap.add_argument('--out-html', default=DEFAULT_OUT_HTML)
    ap.add_argument('--out-pdf', default=DEFAULT_OUT_PDF)
    ap.add_argument('--sub', default='第 1 — 30 章')
    ap.add_argument('--years', default='2006 — 2007')
    ap.add_argument('--title', default='带着GPT重回高中')
    ap.add_argument('--no-pdf', action='store_true', help='只生成 HTML，不调 Chrome')
    args = ap.parse_args()

    files = sorted([f for f in os.listdir(args.src) if f.endswith('.md')], key=chap_key)
    files = [f for f in files if chap_key(f) != 9999]

    chapters = []
    for fn in files:
        raw = open(os.path.join(args.src, fn), encoding='utf-8').read()
        title, body = parse_chapter(raw, fn[:-3].replace('-', ' '))
        chapters.append((chap_key(fn), title, body))

    toc = ['<li><a href="#c%d">%s</a></li>' % (n, html.escape(t)) for n, t, _ in chapters]

    parts = ['<!DOCTYPE html><html><head><meta charset="utf-8"><style>%s</style></head><body>' % CSS]
    parts.append('<div class="cover"><h1>%s</h1><div class="sub">%s</div>'
                 '<div class="yr">%s</div></div>'
                 % (html.escape(args.title), html.escape(args.sub), html.escape(args.years)))
    parts.append('<div class="toc"><h2>目 录</h2><ul>%s</ul></div>' % '\n'.join(toc))
    for n, t, b in chapters:
        parts.append('<div class="chapter" id="c%d"><h1>%s</h1>%s</div>' % (n, html.escape(t), b))
    parts.append('</body></html>')

    os.makedirs(os.path.dirname(args.out_html), exist_ok=True)
    open(args.out_html, 'w', encoding='utf-8').write('\n'.join(parts))
    print('章数 %d | HTML %s（%d 字节）' % (len(chapters), args.out_html, os.path.getsize(args.out_html)))

    if args.no_pdf:
        return 0

    if not os.path.exists(CHROME):
        print('未找到 Chrome：%s' % CHROME)
        return 2

    cmd = [CHROME, '--headless', '--disable-gpu', '--no-sandbox',
           '--no-pdf-header-footer', '--run-all-compositor-stages-before-draw',
           '--virtual-time-budget=10000',
           '--print-to-pdf=%s' % args.out_pdf,
           'file://%s' % args.out_html]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0 or not os.path.exists(args.out_pdf):
        print('Chrome 出图失败：', r.returncode, r.stderr[-800:])
        return 3
    print('PDF → %s（%.1f MB）' % (args.out_pdf, os.path.getsize(args.out_pdf) / 1048576))
    return 0


if __name__ == '__main__':
    sys.exit(main())
