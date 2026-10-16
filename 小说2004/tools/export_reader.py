#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读者版导出器：把「写作稿」转成「能直接发出去的正文」。

── 2026-10-13 变更（老板拍板：不要 `## 四` 这种小节号）──
源文件 `正文_新版/` **已不再用 `## 一/二/三`**，直接改用 `······` 分场景。
本脚本现在只剩两个主要用途：
  ① `--plain`：去掉 markdown 粗体星号（番茄/起点不支持 markdown，**投稿必加**）
  ② `--merge`：合成单文件，方便连读／交付
兼容旧稿：`--keep-number`／`--sep` 仍支持 `## N` → 分隔符的转换
（旧版 `正文/` 1—130 章、`正文_备份_*/` 仍是 `## N` 格式）。

★为什么不用「空行」当分隔（老板原话：直接改空行不行吗）——实测证明不行：
  柳书 raw200：段均 31.2 字，空行占比 1.3%（每 79.6 行一个空行）
  本书新版　：段均 14.8 字，空行占比 **49.9%**（每 2.00 行一个空行）
  本书一行一句、满篇一半是空行，**空行已零区分度**，读者分不清换段还是换场景。
  柳书段落长、几乎不用空行，尚且要专门用 `······` 标场景。

★柳书 raw200 实测：200/200 章（100%）用 `······`，共 712 次，
  **0 章使用数字小节**；章均 3.6 个分隔，每场景 567 字。

── 用法 ──
    python3 tools/export_reader.py                    # 导出全部章节
    python3 tools/export_reader.py --chapter 6        # 只导第 6 章
    python3 tools/export_reader.py --merge            # 合成单文件
    python3 tools/export_reader.py --sep '＊＊＊'      # 自定义分隔符
    python3 tools/export_reader.py --keep-number      # 保留数字小节（不转换）

输出目录：`正文_读者版/`（不改动源文件）
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
SRC = os.path.join(ROOT, '正文_新版')
DST = os.path.join(ROOT, '正文_读者版')

DEFAULT_SEP = '······'          # 柳书 raw200 实测：200/200 章用这个
SEC_RE = re.compile(r'^##\s*[一二三四五六七八九十]+\s*$', re.M)


def chapter_num(fn):
    m = re.match(r'第(\d+)章', fn)
    return int(m.group(1)) if m else 9999


def convert(raw, sep=DEFAULT_SEP, keep_number=False):
    """把一章的写作稿转成读者版。"""
    lines = raw.splitlines()
    out = []
    first_sec = True
    for ln in lines:
        s = ln.rstrip()
        # 章标题：# 第6章 三块二 → 第6章 三块二（去掉 #，保留标题）
        if s.startswith('# '):
            out.append(s[2:].strip())
            continue
        # 节标题：## 一 → 场景分隔符（或保留）
        if re.match(r'^##\s*[一二三四五六七八九十]+\s*$', s):
            if keep_number:
                out.append(s[3:].strip())
            elif first_sec:
                # ★第一节不转：章标题本身已经是分隔，再插一个就是多余
                #  （2026-10-13：第6章导出后章首金句下冒出一个 ······，很难看）
                first_sec = False
            else:
                # 避免连续两个分隔符：往前跳过空行，看最近一个非空行是否已是分隔符。
                # ★坑（2026-10-13）：节标题前一行几乎总是空行，
                #   若直接判断 out[-1] != '' 则永远为假，分隔符一个都出不来。
                j = len(out) - 1
                while j >= 0 and out[j] == '':
                    j -= 1
                if j < 0 or out[j] != sep:
                    out.append(sep)
            continue
        out.append(s)

    # 收尾：压掉多余空行（连续 3 个以上空行压成 1 个）
    res = []
    blank = 0
    for s in out:
        if s == '':
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        res.append(s)
    return '\n'.join(res).strip() + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=SRC)
    ap.add_argument('--dst', default=DST)
    ap.add_argument('--chapter', type=int, default=0, help='只导指定章号，0=全部')
    ap.add_argument('--merge', action='store_true', help='合成单文件')
    ap.add_argument('--sep', default=DEFAULT_SEP)
    ap.add_argument('--keep-number', action='store_true')
    ap.add_argument('--plain', action='store_true',
                    help='去掉 markdown 粗体星号（番茄/起点等平台不支持 markdown，'
                         '** 会原样显示，投稿时用这个）')
    args = ap.parse_args()

    files = []
    for fn in sorted(os.listdir(args.src), key=chapter_num):
        if not fn.endswith('.md'):
            continue
        m = re.match(r'第(\d+)章', fn)
        if not m:
            continue
        if args.chapter and int(m.group(1)) != args.chapter:
            continue
        files.append((int(m.group(1)), fn))

    if not files:
        print('未找到章节文件')
        return 1

    os.makedirs(args.dst, exist_ok=True)
    merged = []

    for ch, fn in files:
        raw = open(os.path.join(args.src, fn), encoding='utf-8').read()
        body = convert(raw, args.sep, args.keep_number)
        if args.plain:
            # 只处理「整行加粗」与「行内加粗」两种：**xxx** → xxx
            body = re.sub(r'\*\*(.+?)\*\*', r'\1', body)
        merged.append(body)
        # 单章恒出（--merge 时也出，方便单独取用）
        out = os.path.join(args.dst, fn)
        open(out, 'w', encoding='utf-8').write(body)
        n = len(re.findall(r'[\u4e00-\u9fff]', body))
        nsep = body.count(args.sep)
        print(f'  ✓ {fn[:24]:<26}{n:>5}字  场景分隔 {nsep}')

    if args.merge:
        out = os.path.join(args.dst, '全文_读者版.md')
        open(out, 'w', encoding='utf-8').write('\n\n'.join(merged))
        n = len(re.findall(r'[\u4e00-\u9fff]', '\n'.join(merged)))
        print(f'  ✓ 全书合成 → {os.path.basename(out)}（{n} 字）')

    print(f'\n输出目录：{args.dst}（源文件未改动）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
