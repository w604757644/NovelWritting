#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构版 1—5 章 · P1/P2/P5 + C4/C8 + P3 一次性落盘
=================================================
老板 2026-10-13 拍板：P1 起点名次统一 214｜P2 学习委员统一孙磊｜P3 省略号立新体例每章≤3
P4 F0 本书豁免｜P5 日期账按实测日历改
C4 老闫年龄统一 52｜C8 班级人数统一 56（这两条同类，按「先定者优先」同批处理）

用法：
    python3 tools/apply_p1_p5.py            # dry-run，只打印将要改什么
    python3 tools/apply_p1_p5.py --apply    # 落盘
"""
import argparse
import os
import re
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '正文_新版')

# ---------------- ① 逐条文本替换（每章独立，防误伤） ----------------
# (文件匹配, 原文, 新文, 说明)
REPLACEMENTS = [
    # ---- C8 班级人数：全书定案高二（2）班五十六人／五十七张桌子
    ('第2章', '那道题全班四十七个人，做出来的一只手数得过来。',
     '那道题全班五十六个人，做出来的一只手数得过来。', 'C8 班级人数 47→56'),

    # ---- P2 学习委员统一孙磊（含座位统一到第一排正中间）
    ('第3章', '学习委员姓孙，坐在斜前方，回头看了一眼。',
     '学习委员姓孙，坐在第一排正中间，回头看了一眼。', 'P2 座位统一'),
    ('第3章', '“看出来？”孙浩说，“陈冉，你别听他的。看出来是玄学，你得算。”',
     '“看出来？”孙磊说，“陈冉，你别听他的。看出来是玄学，你得算。”', 'P2 孙浩→孙磊'),
    ('第3章', '孙浩从斜前方伸着脖子看了半天，最后把椅子转回去，一句话没说。',
     '孙磊伸着脖子看了半天，最后把椅子转回去，一句话没说。', 'P2 孙浩→孙磊'),

    # ---- P1 起点名次统一 214（第4章两处 + 旁白复合 + 派生的「年级能进二百八」）
    ('第4章', '这是他上次月考的年级位次。',
     '这是他上次月考的年级位次。', 'P1 保留'),
    ('第4章', '三百八十四名。\n', '二百一十四名。\n', 'P1 起点名次 384→214'),
    ('第4章', '“一百零九？他上次不是三百多名吗。”',
     '“一百零九？他上次不是二百多名吗。”', 'P1 旁白复合'),
    ('第4章', '“三百八十四。”另一个声音补了一句。',
     '“二百一十四。”另一个声音补了一句。', 'P1 旁白复合'),
    ('第4章', '一百一十三，班次能进前二十，年级能进二百八。',
     '一百一十三，班次能进前二十，年级能进一百八十。', 'P1 派生：214 出发只能是提升，不能倒退到 280'),

    # ---- C4 老闫年龄统一 52（第1章先定）
    ('第4章', '老闫是他们班主任，教数学，四十七八，头发花白，茶缸子上的茶垢有半指厚。',
     '老闫是他们班主任，教数学，五十二岁，头发花白，茶缸子上的茶垢有半指厚。', 'C4 老闫年龄'),

    # ---- P5 日期账（实测：4-17=74 / 4-18=73 / 4-20=71 / 4-21=70 / 4-22=69）
    ('第4章', '四月二十号，周三，年级周测。',
     '四月二十号，周四，年级周测。', 'P5 星期：2006-04-20 是周四'),
    ('第4章', '一百八十四个位次，还剩七十三天',
     '一百八十四个位次，还剩七十一天', 'P5 4-20 应剩 71'),
    ('第4章', '七十三天，追三十一分。',
     '七十天，追三十一分。', 'P5 第七节在 4-21，应剩 70'),
    ('第5章', '**七十四天，追一百八十四个位次，真正要补的只有这四样。**',
     '**七十天，追一百八十四个位次，真正要补的只有这四样。**', 'P5 4-21 夜应剩 70'),
    ('第5章', '*2006.4.20。立体几何、从句、受力顺序、配平。四样。*',
     '*2006.4.22。立体几何、从句、受力顺序、配平。四样。*', 'P5 软皮本日期'),
    ('第5章', '**还剩七十一天。**', '**还剩六十九天。**', 'P5 4-22 夜应剩 69'),
]

# ---------------- ② P3 省略号新体例：清除行首前缀 + 独立段 ----------------
STANDALONE = re.compile(r'^……\s*$')
PREFIX = re.compile(r'^……\s*')

# 每章保留的显著位置（1 起的行号，清完后重新插回）
KEEP_ELLIPSIS = {
    '第1章': [],   # 后面用 Edit 手放回最具节拍感的 2—3 处
    '第2章': [],
    '第3章': [],
    '第4章': [],
    '第5章': [],
}


def strip_ellipsis(text, fname):
    """删掉所有行首……前缀与……独立段，并把多余空行压成一个"""
    lines = text.split('\n')
    out, removed = [], 0
    for ln in lines:
        if STANDALONE.match(ln):
            removed += 1
            continue
        new = PREFIX.sub('', ln)
        if new != ln:
            removed += 1
        out.append(new)
    text = '\n'.join(out)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text, removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--skip-ellipsis', action='store_true')
    a = ap.parse_args()

    # 先备份
    bak = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                       '正文_备份_P1P5前')
    if a.apply and not os.path.exists(bak):
        os.makedirs(bak)
        for f in sorted(os.listdir(BASE)):
            if f.endswith('.md'):
                open(os.path.join(bak, f), 'w', encoding='utf-8').write(
                    open(os.path.join(BASE, f), encoding='utf-8').read())
        print(f"[备份] 已备份 5 章 → {os.path.basename(bak)}\n")

    files = sorted(f for f in os.listdir(BASE) if f.endswith('.md'))
    grand = 0
    for fn in files:
        path = os.path.join(BASE, fn)
        text = open(path, encoding='utf-8').read()
        orig = text
        log = []

        # ① 文本替换
        for key, old, new, why in REPLACEMENTS:
            if key in fn and old in text and old != new:
                c = text.count(old)
                text = text.replace(old, new)
                log.append(f"  · {why}（{c} 处）")
                grand += c

        # ② 省略号体例
        if not a.skip_ellipsis:
            text, removed = strip_ellipsis(text, fn)
            if removed:
                log.append(f"  · P3 清除行首……／独立……段 {removed} 处，空行已归一化")

        if text != orig:
            print(f"════ {fn} ════")
            for l in log:
                print(l)
            if a.apply:
                open(path, 'w', encoding='utf-8').write(text)
            else:
                print("  （dry-run，未落盘）")
            print()

    mode = '已落盘' if a.apply else 'DRY-RUN 未改任何文件'
    print(f"── 共替换 {grand} 处｜{mode} ──")


if __name__ == '__main__':
    main()
