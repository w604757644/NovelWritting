#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节五要素自检（2026-10-15 老板第 4 条立，替代被否掉的 humor_scan 词频逻辑）

★老板第 1 条原话（打脸记录）：
  「搞笑不是'哈哈，嘿嘿，乐了'这些词出现多少次，是什么对话、动作、剧情让人物产生了
   '哈哈，嘿嘿，乐了'，这才是关键。你统计'哈哈，嘿嘿，乐了'出现的次数没意义。」

**所以本工具不做判定，只做提示**——把五要素的候选痕迹（带行号＋原文）列出来，
**由人来判断本章靠什么成立**。词频一律不算分。

老板第 4 条硬门槛：
  「一个章节，要嘛有搞笑，要嘛有感动，要嘛有暧昧情愫，要嘛有反转打脸，
   要嘛有一定的色情（跟女主、女配）。不然这一章大概率是失败的。」

用法：
  python3 tools/chapter_check.py --range 13-13      # 单章细看（列候选位置＋原文）
  python3 tools/chapter_check.py --range 1-30 --brief   # 全书只看"哪章缺"
"""
import os
import re
import glob
import argparse

# 每类只做"线索提示"，不判定、不算分
HINTS = {
    "①搞笑": ["贫嘴", "咧嘴", "嘿嘿", "哈哈", "噗", "笑出", "笑了一声", "笑起来",
              "绷不住", "笑得", "逗", "损", "耍贫", "接了一句", "白了.*一眼"],
    "②感动": ["他记得", "前世", "这一回", "母亲", "父亲", "妈", "爸", "忍着",
              "没舍得", "舍不得", "眼眶", "鼻子一酸", "攥", "还来得及", "眼泪"],
    "③暧昧": ["脸红", "耳根", "心跳", "多看了", "眼睛亮", "抿嘴", "不好意思",
              "离得近", "靠近", "碰了", "手指", "发梢", "味道", "呼吸", "挪开"],
    "④打脸": ["打脸", "愣住", "说不出话", "哑口", "脸上一阵", "不吭声", "低下头",
              "啪", "全场", "鸦雀", "没人想到", "谁都没想到", "这下"],
    "⑤色情": ["腰", "锁骨", "锁骨", "领口", "胸", "腿", "皮肤", "气息", "香味",
              "喉结", "贴着", "怀里", "耳垂", "颈"],
}


def chapter_no(p):
    m = re.search(r'第(\d+)章', os.path.basename(p))
    return int(m.group(1)) if m else -1


def collect(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    out = {}
    for k, ws in HINTS.items():
        hits = []
        for i, ln in enumerate(lines, 1):
            if not ln.strip() or ln.startswith("#"):
                continue
            for w in ws:
                if re.search(w, ln):
                    hits.append((i, ln.strip()))
                    break
        out[k] = hits
    return out


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

    for f in files:
        cn = chapter_no(f)
        res = collect(f)
        empty = [k for k, v in res.items() if not v]
        if a.brief:
            if len(empty) >= 4:
                print(f"⚠ 第{cn:02d}章  {len(empty)}/5 项无线索（{'、'.join(empty)}）"
                      f"——按老板第4条，本章大概率失败")
            continue
        print(f"\n第{cn:02d}章")
        for k, v in res.items():
            if v:
                print(f"  {k}  候选 {len(v)} 处")
                for i, ln in v[:3]:
                    print(f"      L{i}: {ln[:46]}")
            else:
                print(f"  {k}  — 无线索")
        if len(empty) >= 4:
            print(f"  ⚠ 5 项里 {len(empty)} 项无线索 → 本章大概率失败（老板第 4 条）")


if __name__ == "__main__":
    main()
