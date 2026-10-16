# -*- coding: utf-8 -*-
"""活人感尺子（包在 human-writing 的 check_prose.py 外面的一层「本书口径」）

为什么要包一层：原尺子是给**论坛长帖/非虚构长文**设计的，直接拿来判《带着GPT重回高中》
会误杀三条本书的命根子。本脚本做三件事：

    ① 关掉「禁冒号」——本书软皮本账页（「忘了什么：母亲的声音」）与引出原话都要用冒号
    ② 「不是X，是Y」翻案句**不禁，只配额**（每章 ≤2）——那是柳书调性的核心句式
    ③ 输出 brief 化（老板 2026-10-15 定案：全量跑一律 brief，明细落盘）

用法：
    python3 tools/human_tone.py                       # 全审 正文_重写版
    python3 tools/human_tone.py --range 21-30         # 只审一段
    python3 tools/human_tone.py --range 12-12 --info  # 看第 12 章明细（它翻案句超标）

只读稿件、只出清单：不改稿、不联网。依赖 human-writing 的 scripts/check_prose.py。
"""
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(BASE, "正文_重写版")
PROSE = os.path.expanduser(
    "~/.workbuddy/skills/human-writing/scripts/check_prose.py")
INFO_FILE = os.path.join(BASE, "活人感抽表_最新.md")

PIVOT_QUOTA = 2          # 「不是X，是Y」类翻案句：每章上限（超过才报）
# 黑话命中但属于**本书名梗植入**的，不报（第 1 章「赋能／工具人／爷青回」就是这么来的）。
# 2026-10-15：原尺子把「赋能」判成黑话，其实它是登记在册的名梗。
import glob
MEME_SRC = "\n".join(
    open(p, encoding="utf-8").read()
    for p in [os.path.join(BASE, "名梗_已用一行流.txt")]
    + sorted(glob.glob(os.path.join(BASE, "名梗植入统计_*.md")))
    if os.path.exists(p)
)
FIELDS = ["翻案句", "翻案腔变形", "同构排比", "名词化", "黑话", "硬停词",
          "模型路标", "需辨语境词", "抒情词", "洞察路标", "长前置成分", "重定语句"]
# 本书**不适用**的项（见《活人感_引入与不适用清单.md》）
SKIP_AS_ERROR = ("中文冒号", "英文冒号")
# 本书**保留句式**，只做配额统计，不做删改建议
KEEP_PATTERN = re.compile(r"(疑似翻案腔变形|疑似翻案句)")


def ch_files(d):
    out = []
    for fn in sorted(os.listdir(d)):
        m = re.match(r"第(\d+)章-(.+)\.md$", fn)
        if m:
            out.append((int(m.group(1)), fn))
    out.sort()
    return out


def run_one(path):
    r = subprocess.run([sys.executable, PROSE, path],
                       capture_output=True, text=True)
    return r.stdout


def parse(out):
    counts, fails, warns = {}, [], []
    m = re.search(
        r"翻案句 (\d+)，翻案腔变形 (\d+)，同构排比 (\d+)，名词化 (\d+)，黑话 (\d+)，"
        r"硬停词 (\d+)，模型路标 (\d+)，需辨语境词 (\d+)，抒情词 (\d+)，"
        r"洞察路标 (\d+)，长前置成分 (\d+)，重定语句 (\d+)", out)
    if m:
        counts = dict(zip(FIELDS, map(int, m.groups())))
    sect = None
    for ln in out.splitlines():
        if ln.startswith("需要修改"):
            sect = "f"
        elif ln.startswith("需要人工判断"):
            sect = "w"
        elif ln.startswith("- ") and sect:
            (fails if sect == "f" else warns).append(ln[2:])
    return counts, fails, warns


def main():
    a = sys.argv[1:]
    d = DEFAULT_DIR
    rng = None
    show_info = "--info" in a
    if "--dir" in a:
        d = os.path.join(BASE, a[a.index("--dir") + 1])
    if "--range" in a:
        s = a[a.index("--range") + 1]
        rng = (int(s), int(s)) if "-" not in s else tuple(map(int, s.split("-")))

    files = [f for f in ch_files(d) if not rng or rng[0] <= f[0] <= rng[1]]
    tot = {k: 0 for k in FIELDS}
    quota_over, real_fail, keep_notes, details = [], [], [], []

    for no, fn in files:
        out = run_one(os.path.join(d, fn))
        c, fails, warns = parse(out)
        for k, v in c.items():
            tot[k] += v
        # ① 冒号不适用，直接丢掉
        fails = [f for f in fails if not any(s in f for s in SKIP_AS_ERROR)]
        warns = [w for w in warns if not any(s in w for s in SKIP_AS_ERROR)]
        # ③ 黑话命中但属名梗植入 → 降级为「保留」
        keep, fails = [], []
        for f in fails:
            m = re.search(r"黑话，第 \d+ 行，(.+)$", f)
            if m and m.group(1).strip() in MEME_SRC:
                keep.append("第%02d章 「%s」＝名梗植入，保留" % (no, m.group(1).strip()))
            else:
                fails.append(f)
        # ② 翻案句：保留句式，只统计配额
        pivot_lines = [w for w in warns if KEEP_PATTERN.search(w)]
        warns = [w for w in warns if not KEEP_PATTERN.search(w)]
        n_pivot = c.get("翻案腔变形", 0) + c.get("翻案句", 0)
        if n_pivot > PIVOT_QUOTA:
            quota_over.append((no, n_pivot))
        details.append("第%02d章 翻案句式 %d 处%s"
                       % (no, n_pivot, " ←超配额" if n_pivot > PIVOT_QUOTA else ""))
        real_fail += ["第%02d章 %s" % (no, f) for f in fails]
        keep_notes += ["第%02d章 %s" % (no, w) for w in warns] + keep

    print("活人感尺子 · %s（%d 章，口径见《活人感_引入与不适用清单.md》）"
          % (os.path.basename(d.rstrip("/")), len(files)))
    print("─" * 60)
    print("   " + "｜".join("%s %d" % (k, tot[k]) for k in FIELDS))
    if real_fail:
        print("需修改 %d" % len(real_fail))
        for x in real_fail:
            print("   x " + x)
    if quota_over:
        print("翻案句式超配额（每章≤%d）%d 章" % (PIVOT_QUOTA, len(quota_over)))
        for no, n in sorted(quota_over, key=lambda x: -x[1]):
            print("   ! 第%02d章 %d 处——同章反复用「不是X，是Y」会读成套路" % (no, n))
    if not real_fail and not quota_over:
        print("   ✓ 无必改项、翻案句式未超配额")
    with open(INFO_FILE, "w", encoding="utf-8") as f:
        f.write("# 活人感抽表（tools/human_tone.py 生成，勿手改）\n\n")
        f.write("## 翻案句式按章（本书保留句式，只配额不改）\n")
        f.write("\n".join("- " + x for x in details) + "\n\n")
        if keep_notes:
            f.write("## 待人工判\n" + "\n".join("- " + x for x in keep_notes) + "\n")
    if show_info:
        for x in details:
            print("   · " + x)
        for x in keep_notes:
            print("   ? " + x)
    else:
        print("INFO 明细 → %s（--info 打印）" % os.path.basename(INFO_FILE))
    print("─" * 60)
    return 1 if real_fail else 0


if __name__ == "__main__":
    sys.exit(main())
