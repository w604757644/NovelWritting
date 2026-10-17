#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""老板审稿对比器：正文_重写版/（老板改后） vs 审稿基线（我交稿时）。

用法：
    python3 tools/boss_review_diff.py            # 全部 30 章对比（默认基线 1015）
    python3 tools/boss_review_diff.py --range 11-11           # 只看第 11 章
    python3 tools/boss_review_diff.py --old 正文_备份_老板审稿基线_1014 --range 11-11
                                                 # 换一份基线比（如：看我自己今天改了什么）

★基线纪律：每批交稿都要打新基线，否则 diff 里会混入我自己的改动，看不清老板改了什么。
  打基线：mkdir -p 正文_备份_老板审稿基线_YYYYMMDD && cp 正文_重写版/*.md 该目录/
  然后改本文件 OLD_DIR（或用 --old 临时指定）。

输出：改了哪些文件、每处改动的行号与前后对照（- 我的原句 / + 老板的改句）。
口径：老板删掉的内容也是信息（说明那类写法不要）；改动按句罗列，供逐条学习。
"""
import argparse
import difflib
import os
import re
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
NEW_DIR = os.path.join(BASE, '正文_重写版')
OLD_DIR = os.path.join(BASE, '正文_备份_老板审稿基线_1015')


def num_of(fname):
    m = re.match(r'第(\d+)章', fname)
    return int(m.group(1)) if m else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--range', help='如 2-5')
    ap.add_argument('--old', required=True, help='需要比较的现存基线目录；旧基线已清理')
    a = ap.parse_args()

    old_dir = OLD_DIR
    if a.old:
        old_dir = a.old if os.path.isabs(a.old) else os.path.join(BASE, a.old)

    if not os.path.isdir(old_dir):
        ap.error(f"基线目录不存在：{old_dir}")
    files = sorted(os.listdir(old_dir), key=num_of)
    old_files = {f for f in files if f.endswith('.md')}
    new_files = {f for f in os.listdir(NEW_DIR) if f.endswith('.md')}

    lo = hi = None
    if a.range:
        lo, hi = map(int, a.range.split('-'))

    n_changed = n_lines = 0
    for f in sorted(old_files, key=num_of):
        n = num_of(f)
        if lo is not None and not (lo <= n <= hi):
            continue
        old = open(os.path.join(old_dir, f), encoding='utf-8').read().splitlines()
        new_path = os.path.join(NEW_DIR, f)
        if not os.path.exists(new_path):
            print(f'== {f}：老板删除了整章 ==')
            n_changed += 1
            continue
        new = open(new_path, encoding='utf-8').read().splitlines()
        diff = [d for d in difflib.unified_diff(old, new, lineterm='', n=1)
                if d.startswith(('---', '+++', '@@', '-', '+')) and not d.startswith(('--- ', '+++ '))]
        if not diff:
            continue
        n_changed += 1
        print(f'\n== {f} ==')
        for d in diff:
            print(d)
            if d[:1] in '-+':
                n_lines += 1

    # 新增的整章（老板新写/改名）
    added = {f for f in new_files if f not in old_files
             and (lo is None or (lo <= num_of(f) <= hi))}
    for f in sorted(added, key=num_of):
        print(f'\n== {f}：新增文件 ==')
        n_changed += 1

    print('\n' + '=' * 60)
    if n_changed == 0:
        print('没有改动：正文_重写版/ 与审稿基线完全一致。')
    else:
        print(f'共 {n_changed} 个文件有改动，{n_lines} 处增删行。逐条学习后写入恢复卡与留痕。')


if __name__ == '__main__':
    sys.exit(main())
