#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
老板批注处理器 —— 识别 `#…` 标记（老板 2026-10-15 立的规则）。

★规则（老板原话）：「我修改的时候感觉那些内容不合理，会在每句或者每段加上 #我写的内容
  的方式来写到正文中，你去修改的时候要理解这套规则。」

**判据**：从 `#` 起到**行尾**＝老板的批注/改写内容。
  - 行内：`……是眼睛多。#他面开过几千家媒体，"是眼睛多"？这不合理`
          → 正文「……是眼睛多。」保留，`#…` 后面是批注
  - 整行：`#我写的内容` 独占一行 → 该行是标记，删整行
  - 章标题：`# 第12章 上讲台` → **不是批注，必须保留**（正则排除）
  - ★脏话屏蔽：`“我@#￥%……我说呢！”`（第 8 章）→ **不是批注，必须保留**
    判据：`#` 的前一个字符或后一个字符属于 `@￥%&*!~` → 视为符号串，跳过。

用法：
  python3 tools/boss_notes.py --list                 # 列出所有批注（给我看）
  python3 tools/boss_notes.py --list --range 12-12
  python3 tools/boss_notes.py --check                # 导出/PDF 前检查：还有没有未清理的批注
  python3 tools/boss_notes.py --strip --out 正文_待清  # 剥离批注，输出到新目录（不原地改）
  python3 tools/boss_notes.py --apply                # 原地清除批注（★会先自动打基线）

★纪律：老板改稿期间**不要跑 --apply**，批注是我要读的学习材料。
      只有等他改完、我学完、改完之后才清。清之前必须备份（--apply 会自动做）。
"""
import os
import re
import sys
import glob
import shutil
import argparse
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRC = os.path.join(BASE, "正文_重写版")

# 章标题：行首 # + 空格 + 第N章
TITLE_RE = re.compile(r'^#\s*第\d+章')
# 批注：# 不在符号串里（前后都不是 @￥%&*!~），也不是章标题
SYMS = '@￥%&*!~＠＃＄％＆'
NOTE_RE = re.compile(r'(?<![%s])#(?![%s\s])' % (re.escape(SYMS), re.escape(SYMS)))


def chapter_no(fname):
    m = re.search(r'第(\d+)章', os.path.basename(fname))
    return int(m.group(1)) if m else -1


def split_line(line):
    """返回 (正文部分, 批注部分 or None)"""
    if TITLE_RE.match(line):
        return line, None
    m = NOTE_RE.search(line)
    if not m:
        return line, None
    return line[:m.start()].rstrip(), line[m.start():]


def scan(src, rng=None):
    rows = []
    for f in sorted(glob.glob(os.path.join(src, "*.md"))):
        cn = chapter_no(f)
        if rng and not (rng[0] <= cn <= rng[1]):
            continue
        for i, line in enumerate(open(f, encoding="utf-8").read().split("\n"), 1):
            _, note = split_line(line)
            if note is not None:
                rows.append((os.path.basename(f), i, note))
    return rows


def strip_text(text):
    out = []
    for line in text.split("\n"):
        body, note = split_line(line)
        if note is None:
            out.append(line)
            continue
        # 整行都是批注（# 在行首）→ 删整行；否则只留正文部分
        if body == "":
            continue
        out.append(body)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--range", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--strip", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    rng = None
    if a.range:
        try:
            rng = tuple(int(x) for x in a.range.split("-"))
        except Exception:
            sys.exit("--range 格式如 12-12")

    if a.list:
        rows = scan(a.src, rng)
        if not rows:
            print("（无批注）")
            return
        print(f"共 {len(rows)} 条批注：\n" + "─" * 70)
        for f, i, note in rows:
            print(f"[{f} : {i}行]\n  {note}\n")
        return

    if a.check:
        rows = scan(a.src, rng)
        if rows:
            print(f"⚠ 仍有 {len(rows)} 条批注未清理——**导出/PDF 前必须清掉**，否则会印进读者版：")
            for f, i, note in rows[:20]:
                print(f"   {f}:{i}  {note[:40]}")
            sys.exit(1)
        print("✓ 无残留批注，可以导出")
        return

    if a.strip or a.apply:
        if a.strip and not a.out:
            sys.exit("--strip 需要 --out <新目录>（不原地改，安全）")
        if a.apply:
            # ★原地清除前自动打基线
            date = datetime.date.today().strftime("%m%d")
            bak = os.path.join(BASE, f"正文_备份_{date}_清批注前")
            if os.path.exists(bak):
                sys.exit(f"基线已存在，请先处理：{bak}")
            shutil.copytree(a.src, bak)
            print(f"✓ 已自动备份 → {bak}")
            dst = a.src
        else:
            if os.path.exists(a.out):
                sys.exit(f"输出目录已存在：{a.out}")
            os.makedirs(a.out)
            dst = a.out

        n = 0
        for f in sorted(glob.glob(os.path.join(a.src, "*.md"))):
            raw = open(f, encoding="utf-8").read()
            new = strip_text(raw)
            if new != raw:
                n += 1
            open(os.path.join(dst, os.path.basename(f)), "w", encoding="utf-8").write(new)
        print(f"✓ 已剥离批注，写入 {dst}（{n} 个文件有改动）")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
