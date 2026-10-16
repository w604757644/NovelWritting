#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正文快照器 —— 每次交稿后必跑，老板审稿前必跑。

★为什么必须有这个脚本（老板 2026-10-15 定案）：
  老板一定会亲自改稿，改完我要 diff 出他改了什么、逐条分析我哪里写得不好、总结记录。
  没有"他动手前"的基线，就 diff 不出来，学习闭环断掉。
  → **完成一批正文写作 = 必须打一次基线**，这是硬流程，不是可选项。

用法：
  python3 tools/snapshot.py --tag P12审前 --range 10-12     # 打基线
  python3 tools/snapshot.py --tag 定稿 --all                # 老板审完后打定稿基线
  python3 tools/snapshot.py --list                          # 列出现有基线

产出：
  正文_备份_<日期>_<tag>/         全量快照
  《备份台账.md》                  追加一行（时间／基线名／范围／用途／diff 命令）
"""
import os
import sys
import glob
import shutil
import hashlib
import argparse
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "正文_重写版")
LEDGER = os.path.join(BASE, "备份台账.md")
PATTERN = "正文_备份_*"


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def list_baselines():
    rows = []
    for d in sorted(glob.glob(os.path.join(BASE, PATTERN))):
        if not os.path.isdir(d):
            continue
        n = len([f for f in os.listdir(d) if f.endswith(".md")])
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(d))
        rows.append((os.path.basename(d), n, mt.strftime("%Y-%m-%d %H:%M")))
    return rows


def snapshot(tag, rng=None, note=""):
    if not os.path.isdir(SRC):
        sys.exit(f"源目录不存在：{SRC}")
    date = datetime.date.today().strftime("%m%d")
    name = f"正文_备份_{date}_{tag}" if tag else f"正文_备份_{date}"
    dst = os.path.join(BASE, name)

    if os.path.exists(dst):
        sys.exit(f"基线已存在，换个 --tag：{name}")

    shutil.copytree(SRC, dst)

    # 全量 md5 校验
    files = sorted(f for f in os.listdir(SRC) if f.endswith(".md"))
    bad = []
    for f in files:
        a, b = os.path.join(SRC, f), os.path.join(dst, f)
        if not os.path.exists(b):
            bad.append((f, "缺失"))
        elif md5(a) != md5(b):
            bad.append((f, "md5 不一致"))

    # 抽查指定范围是否真的被快照进去
    scope_note = ""
    if rng:
        try:
            lo, hi = (int(x) for x in rng.split("-"))
            hit = [f for f in files
                   if any(f.startswith(f"第{i}章") for i in range(lo, hi + 1))]
            scope_note = f"（本次交稿 {lo}-{hi} 章，命中 {len(hit)} 个文件）"
        except Exception:
            pass

    # 写台账
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if not os.path.exists(LEDGER):
        with open(LEDGER, "w", encoding="utf-8") as fh:
            fh.write("# 备份台账\n\n"
                     "> ★制度（老板 2026-10-15 定案）：**每完成一次正文写作，必须打一次基线。**\n"
                     "> 老板审稿必改稿，改完我要 diff 出他改了什么 → 逐条分析我哪里写得不好 → 总结记录。\n"
                     "> **没有基线 = 学习闭环断掉。** 打基线用 `tools/snapshot.py`，别手 cp。\n\n"
                     "| # | 时间 | 基线目录 | 范围 | 用途 | 章数 | 校验 |\n"
                     "|---|---|---|---|---|---|---|\n")
    with open(LEDGER, encoding="utf-8") as fh:
        body = fh.read()
    seq = body.count("\n| ") - 1
    if seq < 0:
        seq = 0
    diff_cmd = (f"`python3 tools/boss_review_diff.py --old {name}"
                f" --range {rng}`" if rng else
                f"`python3 tools/boss_review_diff.py --old {name}`")
    ok = "✓ 一致" if not bad else "✗ 有问题"
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(f"| {seq + 1} | {now} | `{name}` | {rng or '全书'} | "
                 f"{note or '—'} {scope_note} | {len(files)} | {ok} |\n")

    print(f"✓ 已建基线：{name}")
    print(f"  文件 {len(files)} 个，md5 {'全部一致' if not bad else '有问题'}")
    if bad:
        for f, r in bad:
            print(f"  ✗ {f}：{r}")
    print(f"  台账：{LEDGER}")
    if rng:
        print(f"  老板改完后对比：{diff_cmd}")
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="", help="基线后缀，如 P12审前 / 定稿")
    ap.add_argument("--range", default="", help="本次交稿章号范围，如 10-12（只用于台账记录）")
    ap.add_argument("--note", default="", help="用途说明")
    ap.add_argument("--list", action="store_true", help="列出现有基线")
    a = ap.parse_args()

    if a.list:
        rows = list_baselines()
        if not rows:
            print("（暂无基线）")
            return
        print(f"现有 {len(rows)} 个基线：")
        for name, n, mt in rows:
            print(f"  {mt}  {name}  （{n} 章）")
        return

    if not a.tag:
        sys.exit("请给 --tag（如 --tag P12审前），否则基线名字分不清")
    snapshot(a.tag, a.range or None, a.note)


if __name__ == "__main__":
    main()
