#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
口径对照器：把「本书」和「柳书」用**完全相同**的代码路径量一遍。

背景（重要）：
  早期统计（distill_stats.py）里的 "CV 1.048 / 长句≥35字 21.2% / 均长 26.6"
  是**段落级**指标，且字数只数汉字（去标点），不是句子级。
  本脚本把两级、两种计字口径全部拆开，避免拿苹果比橘子。

两级指标：
  段级：一句一行排版下，"段落"≈视觉行；柳书是成段排版，段落内含多句。
  句级：按 。！？… 切分。

两种计字：
  含标点：所有全角字符 + 连续 ASCII 段计 1（视觉长度）
  净汉字：只数 [\u4e00-\u9fff]（语义长度）

用法：
  python3 tools/caliber_compare.py --dir 正文_新版 --range 1-5
  python3 tools/caliber_compare.py --dir 正文_新版 --range 1-5 --limit-liu 200
"""
import argparse
import glob
import os
import re
import statistics as st
import sys

SENT_END = '。！？…'
TRIM_TAIL = '”）」』】》"\'）)'
SKIP_LINE = re.compile(r'^\s*(#|>|---|\*\*\*|【|（注|注：|附：)')
CJK = re.compile(r'[\u4e00-\u9fff]')

LIU_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                        '蒸馏_语料', '我真没想重生啊', 'raw200')


def is_body(line):
    s = line.strip()
    if not s or SKIP_LINE.match(s):
        return False
    if re.fullmatch(r'[-—=*·　\s]+', s):
        return False
    return True


def width_len(s):
    """含标点的视觉字宽：全角计1，连续 ASCII 段整体计1。"""
    n = i = 0
    while i < len(s):
        if ord(s[i]) < 0x2E80:
            j = i
            while j < len(s) and ord(s[j]) < 0x2E80:
                j += 1
            n += 1
            i = j
        else:
            n += 1
            i += 1
    return n


def han_len(s):
    return len(CJK.findall(s))


def split_sentences(paras):
    out = []
    for p in paras:
        buf = ''
        for ch in p:
            buf += ch
            if ch in SENT_END:
                s = buf.rstrip()
                while s and s[-1] in TRIM_TAIL and s[-1] not in SENT_END:
                    s = s[:-1]
                out.append(s.strip())
                buf = ''
        tail = buf.strip().rstrip(TRIM_TAIL).strip()
        if tail:
            out.append(tail)
    return [x for x in out if x]


def stats(lens):
    lens = [x for x in lens if x > 0]
    if not lens:
        return None
    m = st.mean(lens)
    sd = st.pstdev(lens)
    return {
        'n': len(lens), 'mean': m, 'sd': sd, 'cv': sd / m if m else 0,
        'p35': sum(1 for x in lens if x >= 35) / len(lens) * 100,
        'p5': sum(1 for x in lens if x <= 5) / len(lens) * 100,
        'max': max(lens),
    }


def collect(files):
    paras = []
    for p in files:
        with open(p, encoding='utf-8') as f:
            paras += [l.strip() for l in f if is_body(l)]
    return paras


def report(name, paras):
    pl_w = [width_len(x) for x in paras]
    pl_h = [han_len(x) for x in paras]
    sl_w = [width_len(s) for s in split_sentences(paras)]
    sl_h = [han_len(s) for s in split_sentences(paras)]
    return {
        'name': name,
        '段_含标点': stats(pl_w), '段_净汉字': stats(pl_h),
        '句_含标点': stats(sl_w), '句_净汉字': stats(sl_h),
        '总字': sum(pl_h), '总段': len(paras),
    }


def row(label, a, b, key, unit=''):
    va = a[key]['mean']; vb = b[key]['mean']
    gap = va - vb
    print(f"  {label:<10}均长 {va:>6.1f} / {vb:>6.1f}{unit}  差 {gap:>+6.1f}"
          f"   CV {a[key]['cv']:>5.3f} / {b[key]['cv']:>5.3f}"
          f"   ≥35字 {a[key]['p35']:>5.1f}% / {b[key]['p35']:>5.1f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='正文_新版')
    ap.add_argument('--range', default='1-5')
    ap.add_argument('--limit-liu', type=int, default=200)
    args = ap.parse_args()

    a, _, b = args.range.partition('-')
    lo, hi = int(a), int(b or a)
    mine = []
    for i in range(lo, hi + 1):
        hit = glob.glob(os.path.join(args.dir, f'第{i}章*.md'))
        if hit:
            mine.append(hit[0])
    if not mine:
        print('没找到本书章节', file=sys.stderr)
        return 1

    liu = sorted(glob.glob(os.path.join(LIU_BASE, '*.md')))
    liu = liu[:args.limit_liu] if args.limit_liu else liu

    r_me = report(f'本书{args.range}章', collect(mine))
    r_liu = report(f'柳书前{len(liu)}章', collect(liu))

    print('=' * 84)
    print(f"  左＝{r_me['name']}（一句一行排版）   右＝{r_liu['name']}（成段排版）")
    print(f"  本书 {r_me['总段']} 段 / {r_me['总字']:,} 汉字      柳书 {r_liu['总段']} 段 / {r_liu['总字']:,} 汉字")
    print('=' * 84)
    row('段落', r_me, r_liu, '段_含标点')
    row('段落', r_me, r_liu, '段_净汉字')
    row('句子', r_me, r_liu, '句_含标点')
    row('句子', r_me, r_liu, '句_净汉字')
    print()
    print('  注：本书一句一行 ⇒ 段级≈句级；柳书成段 ⇒ 段级远大于句级。')
    print('      真正可比的是【句_净汉字】这一行。')
    print('=' * 84)
    return 0


if __name__ == '__main__':
    sys.exit(main())
