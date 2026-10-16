#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
笑点尺子（2026-10-15 老板第 3/5 条立）
老板原话：「笑点不够爆，不够让读者笑起来」「有说同学们笑成一片、笑的拍桌子，这不合理？」

★为什么需要它：实测发现本书笑点密度 0.33/千字 **比柳书 0.23 还高**，
  但 30 章里 10 章是 0 笑点、41% 的"笑"是「乐了」这种没画面的叙述词。
  **总密度是个骗人的指标**——真正要看的是「0 笑点的章」和「笑的写法有没有画面」。

判三件事：
  ① 笑点分布（哪些章一个笑点都没有）
  ② 笑的写法有没有画面（"乐了" → 读者看不见）
  ③ 强度配不配得上包袱（"笑翻了/拍桌子" → 老板认为不合理）

用法：
  python3 tools/humor_scan.py --dir 正文_重写版 --range 1-30
  python3 tools/humor_scan.py --dir 正文_重写版 --range 1-30 --brief
"""
import os
import re
import sys
import glob
import argparse

# ① 有画面的笑（正面计数）：具体的人/声音/身体反应
GOOD = ["笑出声", "笑出", "笑了一声", "笑了一阵", "笑起来", "笑开了", "憋笑", "偷笑",
        "忍笑", "噗", "哈哈", "嘿嘿", "笑岔", "笑骂", "嗤笑", "笑得", "喷出", "呛住",
        "咳得", "拍桌", "笑倒", "有人笑", "底下笑", "哄一声", "哄地", "笑意", "咧嘴",
        "乐出声", "逗笑", "绷不住", "笑纹", "真笑了"]
# ② 没画面的叙述词（警告）：读者看不见
FLAT = ["乐了", "可乐", "好笑", "觉得有趣", "忍俊不禁", "忍俊", "可乐的"]
# ③ 批发式群笑（警告）：老板明确否掉的
WHOLESALE = ["哄堂大笑", "哄堂", "笑成一团", "笑成一片", "都笑了", "全场笑",
             "笑翻了", "笑翻", "笑成一", "全都笑", "一片笑"]

WARN_FLAT = 2        # 「乐了」类超过 2 处/章 → 警告
WARN_WHOLESALE = 0   # 批发式群笑出现即警告
MIN_LAUGH = 1        # 每章至少 1 处笑（老板：笑点不够）


def chapter_no(p):
    m = re.search(r'第(\d+)章', os.path.basename(p))
    return int(m.group(1)) if m else -1


def scan_file(path):
    t = open(path, encoding="utf-8").read()
    good, flat, whole = [], [], []
    for w in GOOD:
        for m in re.finditer(re.escape(w), t):
            line = t[:m.start()].count("\n") + 1
            ctx = t.split("\n")[line - 1].strip()
            good.append((w, line, ctx))
    for w in FLAT:
        for m in re.finditer(re.escape(w), t):
            line = t[:m.start()].count("\n") + 1
            flat.append((w, line, t.split("\n")[line - 1].strip()))
    for w in WHOLESALE:
        for m in re.finditer(re.escape(w), t):
            line = t[:m.start()].count("\n") + 1
            whole.append((w, line, t.split("\n")[line - 1].strip()))
    return good, flat, whole


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="正文_重写版")
    ap.add_argument("--range", default="")
    ap.add_argument("--brief", action="store_true")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.dir, "*.md")), key=chapter_no)
    if a.range:
        lo, hi = (int(x) for x in a.range.split("-"))
        files = [f for f in files if lo <= chapter_no(f) <= hi]

    rows, issues = [], 0
    for f in files:
        good, flat, whole = scan_file(f)
        rows.append((chapter_no(f), len(good), flat, whole))
        if len(good) < MIN_LAUGH or len(flat) > WARN_FLAT or len(whole) > WARN_WHOLESALE:
            issues += 1

    for cn, n, flat, whole in rows:
        marks = []
        if n < MIN_LAUGH:
            marks.append(f"x [一笑点] 全章 {n} 处笑点——老板：笑点不够，读者笑不起来")
        if len(flat) > WARN_FLAT:
            marks.append(f"x [二画面] 「{'/'.join(sorted(set(w for w, _, _ in flat)))}」{len(flat)} 处"
                         f"——叙述词，读者看不见画面，改成具体的人/声音/动作")
        if len(whole) > WARN_WHOLESALE:
            marks.append(f"x [三强度] 「{'/'.join(sorted(set(w for w, _, _ in whole)))}」"
                         f"{len(whole)} 处——批发式群笑，笑点强度配不上包袱")
        if marks and not a.brief:
            print(f"第{cn:02d}章  {n} 处笑点")
            for m in marks:
                print(f"   {m}")
            for w, ln, ctx in flat[:3]:
                print(f"      · 无画面 L{ln}：{ctx[:50]}")
            for w, ln, ctx in whole[:3]:
                print(f"      · 群笑   L{ln}：{ctx[:50]}")

    if a.brief:
        zeros = [cn for cn, n, _, _ in rows if n < MIN_LAUGH]
        if zeros:
            print(f"0 笑点章 {len(zeros)} 章：第 {'、'.join(str(z) for z in sorted(zeros))} 章")
        flatc = sum(len(fl) for _, _, fl, _ in rows)
        wc = sum(len(wh) for _, _, _, wh in rows)
        print(f"无画面叙述词 {flatc} 处｜批发群笑 {wc} 处")

    print(f"\n── 共 {len(rows)} 章，笑点问题 {issues} 项 ──")


if __name__ == "__main__":
    main()
