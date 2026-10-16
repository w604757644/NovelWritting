# -*- coding: utf-8 -*-
"""②名梗植入 · 抽节取梗器（八步流水线第 2 步）

把《名梗_取用路径.md》的 L0 三步做成一条命令，杜绝整读 130KB 梗库（≈83k token）。

    python3 tools/meme_pick.py --list              # 列出 H6 的 14 个情绪节
    python3 tools/meme_pick.py 1                   # 抽第 1 节（想说但不能说）
    python3 tools/meme_pick.py 8 10 --top 8        # 抽 8+10 两节，各给前 8 条
    python3 tools/meme_pick.py 3 --used            # 连已用的一起列（看重复风险）
    python3 tools/meme_pick.py --find 朴实无华      # L1 取证：全库 grep，只看匹配行
    python3 tools/meme_pick.py --adopt "痛点,留存" --chapter 31   # 采用后落台账

输出按 ★★★ → ★★ → ★ → 无星 排序，默认隐藏全书已用梗（派新梗用；--used 看回响机会）。
★2026-10-17 老板明文：**同一梗不限次数**——「梗只要有适合插入的地方就用，不要规定次数。
梗用的多了才是梗。」反复出现＝本书的记忆点／角色口头禅，是好事，只需每次语境有变化。
★2026-10-17 老板同日改量：**每章 5 个**——「不是强制 5 个，尽量按照内容有插口就插入，
但是也不要加的太刻意。」（配套：笑点每章 5—7 个，同样不强制不刻意。）

只读梗库、只出候选：不改稿、不联网、仅用标准库。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.expanduser("~/.workbuddy/skills/net-meme-injection/references")
H6 = os.path.join(REF, "H6_按情绪检索表.md")
USED_FILE = os.path.join(BASE, "名梗_已用一行流.txt")

# H6 的节名（与文件保持一致；--list 时会重新从文件读，这里只作兜底）
SECTION_TITLES = {
    1: "想说但不能说（★★★ 重生者专属）",
    2: "代价／宿命／换命守恒（★★★ 全书核心）",
    3: "贫穷／算计／省钱（★★★ 家属院主线）",
    4: "时间流逝／回忆／物是人非（★★★ 遗憾线）",
    5: "忍着／硬撑／疲惫（★★★ 父亲线）",
    6: "心疼／温柔／爱具体的人（★★ 感情线）",
    7: "孤独／独处／一个人扛",
    8: "得意／小赢／爽点（配“余光里的凉意”）",
    9: "失手／翻车／事与愿违（★★ 最多用的一层）",
    10: "不服／愤怒／硬气（本书要短促）",
    11: "看穿／祛魅／大人世界不过如此（★★★ 重生者视角红利）",
    12: "家属院口语（非网络梗，本书声口底座）",
    13: "禁忌清单（以下场景不用梗）",
    14: "本书已用梗台账",
}


def read_sections():
    """返回 {节号: (标题, [条目行])}"""
    with open(H6, encoding="utf-8") as f:
        lines = f.read().splitlines()
    out, cur, title, buf = {}, None, "", []

    def flush():
        if cur is not None:
            out[cur] = (title, buf[:])

    for ln in lines:
        m = re.match(r"^##\s+(\d+)\.\s*(.*)", ln)
        if m:
            flush()
            cur, title, buf = int(m.group(1)), m.group(2).strip(), []
            continue
        if cur is not None and ln.startswith("- "):
            buf.append(ln[2:].strip())
    flush()
    return out


def list_sections(secs):
    print("H6 情绪节（用法：python3 tools/meme_pick.py <节号>）\n")
    for n in sorted(secs):
        title, items = secs[n]
        print("  %2d  %-42s （%d 条）" % (n, title[:42], len(items)))
    print("\n★高频组合：1+2（想说不能说＋代价）／3+8（穷算计＋小赢）／9+10（翻车＋不服）")


def parse_item(line):
    """'出来混，迟早要还的｜★★★（《无间道》）' -> (梗, 星级, 注释)"""
    parts = line.split("｜")
    name = parts[0].strip()
    rest = "｜".join(parts[1:])
    stars = rest.count("★")
    note = re.sub(r"[★]+", "", rest).strip()
    return name, stars, note


def load_used():
    """去重源＝《名梗_已用一行流.txt》＋全部《名梗植入统计_XX-XX章.md》。

    ★2026-10-14：一行流只覆盖旧版 1—130 章与重构版 1—5 章，**漏掉重写版 21—30 章**，
    所以必须把各批统计文件一起纳进来，否则会重复派梗。
    """
    import glob
    buf = []
    srcs = [USED_FILE] + sorted(glob.glob(os.path.join(BASE, "名梗植入统计_*.md")))
    for p in srcs:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                buf.append(f.read())
    return "\n".join(buf)


def pick(secs, nums, top, show_used, chapter=None):
    used = load_used()
    for n in nums:
        if n not in secs:
            print("x 没有第 %d 节（--list 看全部）" % n)
            continue
        title, items = secs[n]
        print("\n=== %d. %s ===" % (n, title))
        rows = []
        for it in items:
            name, stars, note = parse_item(it)
            if not name:
                continue
            is_used = name and name in used
            if is_used and not show_used:
                continue
            rows.append((stars, name, note, is_used))
        # 稳定排序：只按星级降序，节内保持梗库原顺序（原顺序是人工排的，重要的在前）
        rows.sort(key=lambda r: -r[0])
        shown = rows[:top] if top else rows
        for stars, name, note, is_used in shown:
            tag = "★" * stars if stars else " "
            mark = " [已用]" if is_used else ""
            note_s = ("  " + note) if note else ""
            print("  %s %s%s%s" % (tag.ljust(3), name, note_s, mark))
        hidden = len(rows) - len(shown)
        if hidden > 0:
            print("  …另有 %d 条（--top 0 看全部）" % hidden)
        if not shown:
            print("  （本节候选已全部用过，换一节或 --used 看回响机会）")


def find_kw(kw):
    hits = 0
    for fn in sorted(os.listdir(REF)):
        if not fn.endswith(".md") or fn.endswith(".bak20261013"):
            continue
        p = os.path.join(REF, fn)
        with open(p, encoding="utf-8") as f:
            for i, ln in enumerate(f, 1):
                if kw in ln:
                    print("%s:%d: %s" % (fn, i, ln.strip()[:120]))
                    hits += 1
    print("\n共 %d 行命中（只看匹配行，未加载全文）" % hits)


def adopt(text, chapter):
    """把采用的梗追加进《名梗_已用一行流.txt》"""
    names = [x.strip() for x in re.split(r"[,，、]\s*", text) if x.strip()]
    if not names:
        print("x 没给梗名")
        return
    tag = ("第%02d章" % chapter) if chapter else "未标章"
    with open(USED_FILE, "a", encoding="utf-8") as f:
        f.write("\n# %s 采用（meme_pick --adopt，%s）" % (tag, "自动"))
        for n in names:
            f.write("\n%s  %s" % (tag, n))
    print("已写入 %s：%s → %s" % (os.path.basename(USED_FILE), tag, "、".join(names)))
    print("★ 同一梗不限次数（2026-10-17 老板：梗用多了才是梗，反复出现＝记忆点）；每次语境要有变化。写完记得回填 G_植入台账.md")


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    secs = read_sections()
    if a[0] == "--list":
        list_sections(secs)
        return
    if a[0] == "--find":
        if len(a) < 2:
            print("x 用法：--find <关键词>")
            return
        find_kw(a[1])
        return
    if a[0] == "--adopt":
        chapter = None
        if "--chapter" in a:
            chapter = int(a[a.index("--chapter") + 1])
        adopt(a[1], chapter)
        return

    top = 10
    if "--top" in a:
        i = a.index("--top")
        top = int(a[i + 1])
        del a[i:i + 2]
    show_used = "--used" in a
    if show_used:
        a.remove("--used")
    nums = [int(x) for x in a if x.isdigit()]
    if not nums:
        print("x 给个节号，或 --list")
        return
    if top == 0:
        top = None
    pick(secs, nums, top, show_used)


if __name__ == "__main__":
    main()
