# -*- coding: utf-8 -*-
"""
V2 拆超长行（本书排版规范：一行一句，单段 ≤60 字符）
====================================================
与旧版 split_long_para.py 的区别：
1. **只在句末标点 。！？ 处断行**，不按逗号断 —— 逗号断句会把一个动作切成两半，也容易拆进引号里。
2. **引号保护**：断行点之前 “ 与 ” 必须成对。本书严禁跨行引号（前期专门修过一轮），这条是硬约束。
3. **省略号保护**：…… 中间的句号不拆。
4. **覆盖任意章号**（旧版写死 1—10）。
5. 拆不动的长句原样保留并报出来，不硬拆。

只插入换行 + 空行，不改任何一个字符、不动标题与 <!-- --> 注释。

用法：
    python3 tools/split_long_para_v2.py --range 11-15          # dry-run
    python3 tools/split_long_para_v2.py --range 11-15 --apply   # 落盘
"""
import argparse
import glob
import os
import re

LIMIT = 60
BREAK = "。！？"


def safe_at(line: str, i: int) -> bool:
    """line[i] 是不是一个可以断行的句末标点"""
    ch = line[i]
    if ch not in BREAK:
        return False
    # 省略号保护
    if ch == "。" and (line[i - 1:i + 1] == "。。" or line[i:i + 2] == "。。"):
        return False
    # 引号保护：断行点（含其后紧跟的 ” ）之前，引号必须成对
    j = i + 1
    if j < len(line) and line[j] == "”":
        j += 1
    seg = line[:j]
    if seg.count("“") != seg.count("”"):
        return False
    return True


def split_line(line: str):
    # ★只处理真正的超长行；≤LIMIT 的一律不动（否则会把全书每行都算一遍）
    if len(line) <= LIMIT:
        return None
    parts, start = [], 0
    for i in range(len(line)):
        if not safe_at(line, i):
            continue
        j = i + 1
        if j < len(line) and line[j] == "”":
            j += 1
        piece = line[start:j].strip()
        if piece:
            parts.append(piece)
        start = j
    tail = line[start:].strip()
    if tail:
        parts.append(tail)
    if len(parts) <= 1:
        return None
    # 必须真的变短才算成功
    if max(len(p) for p in parts) >= len(line):
        return None
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--range", dest="rng")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "正文")
    if a.chapter:
        keys = [f"第{a.chapter:02d}章"]
    elif a.rng:
        lo, hi = a.rng.split("-")
        keys = [f"第{i:02d}章" for i in range(int(lo), int(hi) + 1)]
    else:
        print("需要 --chapter N 或 --range A-B")
        return

    total, stuck_all = 0, []
    for key in keys:
        fs = glob.glob(os.path.join(base, key + "*.md"))
        if not fs:
            print(f"未找到 {key}")
            continue
        f = fs[0]
        lines = open(f, encoding="utf-8").read().split("\n")
        out, cnt, stuck = [], 0, []
        for ln in lines:
            s = ln.strip()
            if not s or s.startswith("#") or s.startswith("<!--"):
                out.append(ln)
                continue
            parts = split_line(ln)
            if parts is None:
                out.append(ln)
                if len(ln) > LIMIT:
                    stuck.append((len(ln), ln[:40]))
                continue
            # 必须全部 ≤LIMIT 才算达标；否则只接受"确实变短"的拆分
            if max(len(p) for p in parts) > LIMIT and max(len(p) for p in parts) >= len(ln):
                out.append(ln)
                stuck.append((len(ln), ln[:40]))
                continue
            cnt += 1
            if not a.apply:
                print(f"  [{len(ln):>3}] {ln}")
                for p in parts:
                    print(f"        →[{len(p):>3}] {p}")
            for i, p in enumerate(parts):
                out.append(p)
                if i < len(parts) - 1:
                    out.append("")   # 本书格式：段间空一行
        if cnt or stuck:
            print(f"{key}  拆 {cnt} 行" + (f"  ⚠拆不动 {len(stuck)}" if stuck else ""))
            for n, s in stuck:
                print(f"      拆不动[{n}] {s}")
        stuck_all.extend(stuck)
        total += cnt
        if a.apply and cnt:
            open(f, "w", encoding="utf-8").write("\n".join(out))
    print(f"\n合计 {total} 行" + ("（已落盘）" if a.apply else "（dry-run 未改）"))


if __name__ == "__main__":
    main()
