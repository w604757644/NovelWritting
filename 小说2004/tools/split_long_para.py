# -*- coding: utf-8 -*-
"""
拆超长段落（番茄硬规格：单段 ≤60 字，手机屏 3-4 行）
保守策略：先按 ；。 断句（本书本就"一行一句"），仍 >60 再按 ， 断。
只插入换行，不改任何字符、不动标题与空行。
用法： python3 split_long_para.py          # dry-run
       python3 split_long_para.py --apply  # 落盘
"""
import os, sys, glob, re

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '正文')
APPLY = '--apply' in sys.argv
LIMIT = 60


def split_once(s, seps):
    """找一个标点把 s 切成两段，优先让两段都 <=LIMIT；取最靠中间的那个标点"""
    fallback = None
    for sep in seps:
        idxs = [m.start() for m in re.finditer(re.escape(sep), s)]
        if not idxs:
            continue
        mid = len(s) / 2
        idx = min(idxs, key=lambda i: abs(i - mid))
        a = s[:idx + len(sep)].strip()
        b = s[idx + len(sep):].strip()
        if not a or not b:
            continue
        if len(a) <= LIMIT and len(b) <= LIMIT:
            return a, b
        if fallback is None:
            fallback = (a, b)
    return fallback


def split_line(s):
    parts = [s]
    for seps in (['；', '。'], ['，']):
        changed = True
        while changed:
            changed = False
            new = []
            for p in parts:
                if len(p) > LIMIT:
                    r = split_once(p, seps)
                    if r:
                        new.extend(r)
                        changed = True
                    else:
                        new.append(p)
                else:
                    new.append(p)
            parts = new
    return parts


def main():
    total = 0
    files = []
    for f in glob.glob(os.path.join(BASE, '*.md')):
        m = re.match(r'第(\d+)章', os.path.basename(f))
        if not m:
            continue
        n = int(m.group(1))
        if 1 <= n <= 10:
            files.append((n, f))
    files.sort()
    for n, f in files:
        lines = open(f, encoding='utf-8').read().split('\n')
        out, cnt, stuck = [], 0, []
        for l in lines:
            s = l.strip()
            if not s or s.startswith('#') or len(s) <= LIMIT:
                out.append(l)
                continue
            ps = split_line(s)
            if max(len(p) for p in ps) <= LIMIT:
                cnt += 1
                # 本书格式：段间空一行
                for i, p in enumerate(ps):
                    out.append(p)
                    if i < len(ps) - 1:
                        out.append('')
            else:
                out.append(l)
                stuck.append(s[:40])
        if cnt or stuck:
            print(f"第{n:02d}章  拆 {cnt} 段" + (f"  ⚠拆不动 {len(stuck)}: {stuck}" if stuck else ""))
        if cnt:
            total += cnt
            if APPLY:
                open(f, 'w', encoding='utf-8').write('\n'.join(out))
    print(f"\n合计 {total} 段" + ("（已落盘）" if APPLY else "（dry-run，未写盘）"))


if __name__ == '__main__':
    main()
