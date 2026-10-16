#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
句法画像：对标柳书（《我真没想重生啊》）的 F0 真人句法画像三项数值。

柳书基线（raw200 实测）：
  句长 CV = 1.048 ／ 长句(>=35字)占比 = 21.2% ／ 段落均长 = 26.6 字

本报告不改任何文件，只输出：
  每章 句数 / 均值 / 标准差 / CV / 长句占比 / 极短句(<=5字)占比 / 最长句 / 段均长
以及"为把 CV 抬到 0.9 还需补几句长句"的估算。

用法：
  python3 tools/sentence_profile.py --dir 正文_新版 --range 1-5
  python3 tools/sentence_profile.py --dir 正文_新版 --range 1-5 --detail 3   # 列出最长3句
"""
import argparse
import glob
import os
import re
import statistics as st
import sys

# 句末切分：。！？… 以及后引号/后括号结尾
SENT_END = '。！？…'
TRIM_TAIL = '”）」』】》"\'）)'

# 只统计"正文字"，排除标题行、分隔线、章末引导句、注释
SKIP_LINE = re.compile(r'^\s*(#|>|---|\*\*\*|---|【|（注|注：|附：)')


def is_body(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if SKIP_LINE.match(s):
        return False
    # 纯分隔符号
    if re.fullmatch(r'[-—=*·　\s]+', s):
        return False
    return True


def split_sentences(paras):
    """把段落切成句子；若段落本身带句末标点则按标点切，否则整段算一句。"""
    sents = []
    for p in paras:
        buf = ''
        for ch in p:
            buf += ch
            if ch in SENT_END:
                # 吃掉紧跟的后引号/后括号
                s = buf.rstrip()
                while s and s[-1] in TRIM_TAIL and s[-1] not in SENT_END:
                    s = s[:-1]
                sents.append(s.strip())
                buf = ''
        tail = buf.strip()
        if tail:
            sents.append(tail.rstrip(TRIM_TAIL).strip())
    return [s for s in sents if s]


def cjk_len(s: str) -> int:
    """字宽：中日韩/全角计 1，其余连续 ASCII 段整体计 1。"""
    n = 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ord(ch) < 0x2E80:
            j = i
            while j < len(s) and ord(s[j]) < 0x2E80:
                j += 1
            n += 1
            i = j
        else:
            n += 1
            i += 1
    return n


def profile(path: str, detail: int = 0):
    with open(path, encoding='utf-8') as f:
        raw = f.read().splitlines()

    paras, para_lens = [], []
    for line in raw:
        if not is_body(line):
            continue
        s = line.strip()
        paras.append(s)
        para_lens.append(cjk_len(s))

    sents = split_sentences(paras)
    lens = [cjk_len(s) for s in sents if cjk_len(s) > 0]

    if not lens:
        return None

    mean = st.mean(lens)
    std = st.pstdev(lens)
    cv = std / mean if mean else 0
    long_n = sum(1 for x in lens if x >= 35)
    short_n = sum(1 for x in lens if x <= 5)

    return {
        'file': os.path.basename(path),
        'chars': sum(para_lens),
        'nsent': len(lens),
        'mean': mean,
        'std': std,
        'cv': cv,
        'long_pct': long_n / len(lens) * 100,
        'short_pct': short_n / len(lens) * 100,
        'max': max(lens),
        'para_mean': st.mean(para_lens) if para_lens else 0,
        'top': sorted(zip(lens, sents), key=lambda x: -x[1 - 1])[:detail],
    }


def need_long_for_cv(lens, target_cv=0.9, add_len=(45, 70)):
    """粗估：还需补几句 L 字长句，才能把 CV 抬到 target。"""
    cur = list(lens)
    for k in range(1, 31):
        trial = cur + [add_len[0]] * k
        m = st.mean(trial)
        s = st.pstdev(trial)
        if m and s / m >= target_cv:
            return k
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='正文_新版')
    ap.add_argument('--range', default='1-5')
    ap.add_argument('--detail', type=int, default=0)
    ap.add_argument('--target-cv', type=float, default=0.9)
    args = ap.parse_args()

    a, _, b = args.range.partition('-')
    lo, hi = int(a), int(b or a)

    files = []
    for i in range(lo, hi + 1):
        hit = glob.glob(os.path.join(args.dir, f'第{i}章*.md'))
        if hit:
            files.append(hit[0])
    if not files:
        print('没找到章节文件', file=sys.stderr)
        return 1

    print('=' * 78)
    print(f'句法画像 · 柳书基线：CV 1.048 ｜ 长句≥35字 21.2% ｜ 段均长 26.6 字')
    print('=' * 78)
    print(f"{'章节':<22}{'字数':>6}{'句数':>6}{'句均':>7}{'CV':>7}"
          f"{'长句%':>7}{'短句%':>7}{'最长':>6}{'段均':>7}{'补长句':>8}")
    print('-' * 78)

    cvs, longs = [], []
    for p in files:
        r = profile(p, args.detail)
        if not r:
            continue
        need = need_long_for_cv([r['mean']] * r['nsent'], args.target_cv)
        cvs.append(r['cv'])
        longs.append(r['long_pct'])
        print(f"{r['file'][:20]:<22}{r['chars']:>6}{r['nsent']:>6}{r['mean']:>7.1f}"
              f"{r['cv']:>7.3f}{r['long_pct']:>7.1f}{r['short_pct']:>7.1f}"
              f"{r['max']:>6}{r['para_mean']:>7.1f}{(need if need else '—'):>8}")
        if args.detail:
            for L, s in r['top']:
                print(f"      [{L}字] {s[:60]}")
            print()

    print('-' * 78)
    print(f"均值：CV {st.mean(cvs):.3f}（目标 ≥{args.target_cv}）｜"
          f"长句占比 {st.mean(longs):.1f}%（目标 15—21%）")
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
