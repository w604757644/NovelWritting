#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键联审（2026-10-15 老板 Q3 拍板：合并七把尺子，"不然你老是忘记"）
=====================================================================
一次跑完九步流水线里所有可量化的检查，按新顺序输出：

  ① 风格对齐　 acceptance（锚点／起伏／段落／破折号）
  ② 名梗植入　 台账审计：**每章 ≥1 个梗**（老板 Q2 硬门槛）
  ③ 爽点冲突　 payoff_scan（辅助，体感为准）
  ④ 笑点　　　 humor_scan（0 笑点章／无画面词／批发群笑）★原⑨，老板拍板前移到④
  ⑤ 去 AI 味　 human_tone（翻案句／名词化／黑话）
  ⑥ 一致性　　 consistency（C1—C8）
  ⑦ 字数　　　 acceptance（2200—4000，含⑥⑦）
  ⑧ 易读防剧透 acceptance（同上，随①⑦一起出）
  ⑨ 番茄审核　 tomato_precheck
  ⑩ 人物戏份　 character_scan（POV／旁人议论／高光）★老板 Q1 新立

用法：
  python3 tools/audit.py --range 1-6                # 默认 brief
  python3 tools/audit.py --range 7-12 --info        # 看明细
  python3 tools/audit.py --range 7-12 --tag 交付标记 --note "说明"   # 跑完顺手打基线
  python3 tools/audit.py --range 1-6 --skip 3,10     # 跳过某几步

★提交前必跑（老板2026-10-15「交稿必打基线」硬制度）：
  python3 tools/audit.py --range A-B --tag <标记> --note "<说明>"
"""
import argparse
import os
import re
import subprocess
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PY = sys.executable
LEDGER = os.path.join(BASE, '名梗_已用一行流.txt')

STEPS = [
    (1, '①风格对齐', 'acceptance.py', ['--brief']),
    (2, '②名梗植入', None, []),
    (3, '③爽点冲突', 'payoff_scan.py', ['--brief']),
    (4, '④笑点', 'humor_scan.py', ['--brief']),
    (5, '⑤去AI味', 'human_tone.py', ['--brief']),
    (6, '⑥一致性', 'consistency.py', []),
    (9, '⑨番茄审核', 'tomato_precheck.py', ['--quiet']),
    (10, '⑩人物戏份', 'character_scan.py', ['--brief']),
]


def run(cmd, rng):
    p = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    return (p.stdout or '') + (p.stderr or '')


PASS = re.compile(r'问题\s*0\s*项|笑点问题\s*0|需处理\s*0\s*章|无 ERROR|✓|\[\s*OK\]|无残留批注')


def brief_of(out, step_no):
    """抽取问题行，避免刷屏（"问题 0 项"这类通过行一律丢掉）。"""
    keep = []
    for line in out.splitlines():
        s = line.strip()
        if not s or PASS.search(s):
            continue
        if re.match(r'^\s*(x|!|WARN|ERROR|HIGH|WATCH)', s):
            keep.append('    ' + s)
        elif re.search(r'问题\s*[1-9]\d*\s*项', s) or re.search(r'需处理\s*[1-9]\d*\s*章', s):
            keep.append('    ' + s)
        elif step_no == 3 and ('爽' in s or '泪' in s or '冲突' in s):
            keep.append('    ' + s)
    return keep


def meme_audit(rng):
    """②名梗：台账里每章至少 1 个梗。"""
    if not os.path.exists(LEDGER):
        return ['    台账缺失：' + LEDGER]
    txt = open(LEDGER, encoding='utf-8').read()
    miss = []
    for n in range(rng[0], rng[1] + 1):
        if not re.search(rf'第{n:02d}章|第{n}章', txt):
            miss.append(n)
    if miss:
        return [f'    x 无梗章（老板 Q2 硬门槛：每章 ≥1）：{miss}']
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='正文_重写版')
    ap.add_argument('--range', required=True)
    ap.add_argument('--info', action='store_true')
    ap.add_argument('--brief', action='store_true')
    ap.add_argument('--skip', default='')
    ap.add_argument('--tag', default='')
    ap.add_argument('--note', default='')
    a = ap.parse_args()

    m = re.match(r'(\d+)-(\d+)$', a.range)
    if not m:
        print('--range 只支持 A-B（逗号多个区间不支持，请分两次跑）')
        return
    rng = (int(m.group(1)), int(m.group(2)))
    skip = {int(x) for x in a.skip.split(',') if x.strip()}

    print(f'一键联审 · {a.dir} · 第{rng[0]}—{rng[1]}章')
    print('════════════════════════════════════════════════════════════')
    total_problems = 0
    for no, name, script, extra in STEPS:
        if no in skip:
            print(f'{name}   （跳过）')
            continue
        if script is None:
            lines = meme_audit(rng)
        else:
            cmd = [PY, os.path.join('tools', script), '--dir', a.dir, '--range', a.range] + extra
            out = run(cmd, no)
            if a.info:
                lines = ['    ' + s for s in out.splitlines() if s.strip()][:40]
            else:
                lines = brief_of(out, no)
        if lines:
            print(f'{name}   x {len(lines)} 项')
            for l in lines[:12]:
                print(l)
            total_problems += len(lines)
        else:
            print(f'{name}   ✓')
    print('════════════════════════════════════════════════════════════')
    print(f'共 {total_problems} 项待处理' + ('（0 项＝可交稿）' if total_problems == 0 else ''))

    if a.tag:
        cmd = [PY, os.path.join('tools', 'snapshot.py'), '--tag', a.tag, '--range', a.range]
        if a.note:
            cmd += ['--note', a.note]
        print('\n' + run(cmd, 0))


if __name__ == '__main__':
    main()
