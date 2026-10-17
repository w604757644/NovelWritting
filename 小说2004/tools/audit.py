#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助扫描集合。旧步骤编号仅用于CLI兼容，写作流程以恢复卡新七步为准。
默认只运行确定性姓名和章号检查；旧启发式须显式--legacy-heuristics，不能作为写作硬门槛。
本地预检不代表平台审核。--tag仅在显式指定时保留旧快照功能。
用法：python3 tools/audit.py --dir 正文_重写版 --range A-B [--info]
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
    (2, '②名梗（人工按语境判断）', None, []),
    (3, '③爽点冲突', 'payoff_scan.py', ['--brief']),
    (4, '④笑点', 'humor_scan.py', ['--brief']),
    (5, '⑤去AI味', 'human_tone.py', ['--brief']),
    (6, '⑥一致性', 'consistency.py', []),
    (9, '⑨本地预检（非平台结论）', 'tomato_precheck.py', ['--quiet']),
    (10, '⑩人物戏份', 'character_scan.py', ['--brief']),
]


def run(cmd, rng):
    p = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


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
    """历史台账不能证明当前正文有梗；取消每章名梗数量门槛。"""
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='正文_重写版')
    ap.add_argument('--range', required=True)
    ap.add_argument('--info', action='store_true')
    ap.add_argument('--legacy-heuristics', action='store_true', help='显式运行旧数值启发式，仅作历史比较，不作为验收门槛')
    ap.add_argument('--brief', action='store_true')
    ap.add_argument('--skip', default='')
    ap.add_argument('--tag', default='')
    ap.add_argument('--note', default='')
    a = ap.parse_args()

    m = re.match(r'(\d+)-(\d+)$', a.range)
    if not m:
        print('--range 只支持 A-B（逗号多个区间不支持，请分两次跑）')
        return 2
    rng = (int(m.group(1)), int(m.group(2)))
    if rng[0] < 1 or rng[1] < rng[0]:
        print('范围须为正数且起点不大于终点')
        return 2
    skip = {int(x) for x in a.skip.split(',') if x.strip()}

    print(f'一键联审 · {a.dir} · 第{rng[0]}—{rng[1]}章')
    print('════════════════════════════════════════════════════════════')
    print('默认仅核确定性姓名与章号；其余依现行七步流程人工复读。')
    if a.legacy_heuristics:
        print('已显式启用旧启发式：配额、频率、落刀等输出均不构成现行改稿指令。')
    total_problems = 0
    tool_failures = 0
    hard_errors = 0
    for no, name, script, extra in STEPS:
        if not a.legacy_heuristics and no != 6:
            continue
        if no == 6 and not a.legacy_heuristics:
            extra = ['--only', 'c1,c4']
        if no in skip:
            print(f'{name}   （跳过）')
            continue
        if script is None:
            lines = meme_audit(rng)
        else:
            cmd = [PY, os.path.join('tools', script), '--dir', a.dir, '--range', a.range] + extra
            code, out = run(cmd, no)
            if code == 1 and no == 6 and re.search(r'^ERROR [1-9]\d*', out, re.M):
                hard_errors += int(re.search(r'^ERROR (\d+)', out, re.M).group(1))
                print(f'{name}   检出可定位的硬错误')
                print(out)
                continue
            if code:
                tool_failures += 1
                print(f'{name}   工具未正常完成（退出码 {code}），结果待复核')
                print(out[-1200:])
                continue
            if a.info:
                lines = ['    ' + s for s in out.splitlines() if s.strip()][:40]
            else:
                lines = brief_of(out, no)
        if lines:
            print(f'{name}   {len(lines)} 行候选提醒（非错误计数）')
            for l in lines[:12]:
                print(l)
            total_problems += len(lines)
        else:
            print(f'{name}   未提取到候选提醒（仍需人工复读）')
    print('════════════════════════════════════════════════════════════')
    print(f'共提取 {total_problems} 行候选提醒；{hard_errors} 个硬错误；{tool_failures} 个工具未正常完成。交稿须人工核验。')

    if a.tag:
        cmd = [PY, os.path.join('tools', 'snapshot.py'), '--tag', a.tag, '--range', a.range]
        if a.note:
            cmd += ['--note', a.note]
        code, out = run(cmd, 0)
        print('\n' + out)
        if code:
            tool_failures += 1
            print(f'快照未正常完成（退出码 {code}）')
    return 1 if tool_failures or hard_errors else 0


if __name__ == '__main__':
    sys.exit(main())
