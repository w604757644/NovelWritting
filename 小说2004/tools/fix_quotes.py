#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文正文引号修正器（写新章后必跑）

── 为什么需要这个脚本 ──
用 Write 工具写中文正文时，很容易敲成 ASCII 直引号 " "（U+0022）。
本书口径是中文弯引号 “ ”（U+201C / U+201D），硬校验要求「直引号 = 0」。
（2026-10-13 写第 6 章时整章 208 个直引号，全部漏网。）

── 规则 ──
把 ASCII 直引号按出现顺序交替替换为 左弯“ / 右弯”。
因为引号总是成对出现（哪怕跨段），全文顺序交替即正确。

★保护：``` 代码块内的引号不动（保留示例代码原样）。
★检查：若总数为奇数，报「引号不配对」并指出第一个落单的位置。

── 用法 ──
    python3 tools/fix_quotes.py 正文_新版/第6章-三块二.md
    python3 tools/fix_quotes.py 正文_新版/第7章*.md --check   # 只检查不改
"""
import argparse
import re
import sys

L = '\u201c'  # “
R = '\u201d'  # ”
Q = '"'       # ASCII 直引号


def split_code_blocks(text):
    """切出代码块，返回 [(is_code, chunk), ...]"""
    parts = re.split(r'(```.*?```)', text, flags=re.S)
    return [(p.startswith('```'), p) for p in parts]


def convert(text):
    """返回 (new_text, n_converted, odd_index_or_None)"""
    chunks = split_code_blocks(text)
    out = []
    cnt = 0           # 全文（非代码块）内已见直引号数
    odd_at = None
    for is_code, chunk in chunks:
        if is_code:
            out.append(chunk)
            continue
        buf = []
        for ch in chunk:
            if ch == Q:
                if cnt % 2 == 0:
                    buf.append(L)
                else:
                    buf.append(R)
                cnt += 1
            else:
                buf.append(ch)
        if cnt % 2 == 1 and odd_at is None:
            odd_at = cnt
        out.append(''.join(buf))
    new = ''.join(out)
    return new, cnt, (odd_at if cnt % 2 == 1 else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--check', action='store_true', help='只检查不修改')
    args = ap.parse_args()

    bad = 0
    for path in args.files:
        raw = open(path, encoding='utf-8').read()
        n = raw.count(Q)
        if n == 0:
            print(f'  OK   {path}（无需修正）')
            continue
        new, total, odd = convert(raw)
        if odd:
            bad += 1
            print(f'  ✗    {path}：直引号 {n} 个，总数为奇数，可能不配对（第 {odd} 个落单）')
            continue
        if args.check:
            bad += 1
            print(f'  ✗    {path}：发现直引号 {n} 个（--check 模式，未修改）')
            continue
        open(path, 'w', encoding='utf-8').write(new)
        print(f'  ✓    {path}：直引号 {n} 个 → 弯引号（左 {total//2} / 右 {total//2}）')

    if bad:
        print(f'\n{bad} 个文件需要处理')
        return 1
    print('\n全部通过：直引号 = 0')
    return 0


if __name__ == '__main__':
    sys.exit(main())
