# -*- coding: utf-8 -*-
"""⑤一致性 · 跨章确定性校验（八步流水线第 5 步）

定位：**机器筛，模型判**。本脚本只做「能数、能比对、零脑补」的项；
凡需要读上下文才能定的，只出**候选 + 原文**，交人工判。

    python3 tools/consistency.py                      # 全审 正文_重写版
    python3 tools/consistency.py --range 21-30        # 只审一段（新章写完必跑）
    python3 tools/consistency.py --only c2,c3         # 只跑某几项
    python3 tools/consistency.py --info               # 抽表（INFO）打到屏幕，默认写文件

★2026-10-15 老板定案：INFO 抽表默认**写文件**不占上下文（`一致性抽表_最新.md`），
  终端只出 ERROR/WARN。要看抽表就 Read 那个文件，或临时加 --info。
  理由：C5/C8 抽表 30 章 5.2k 字符、130 章外推 ~23k，每批都打印会挤爆上下文。

检查项
    C1 名字变体    规范名 vs 误写变体（李志民／程双／老阎…）—— ERROR
    C2 称谓口径    引号外的单字「妈／爸」（定案：叙述语一律母亲／父亲）—— WARN，附原句
    C3 章末对表    正文末句 vs《章末钩子台账》登记的「章末停在哪」—— WARN（改造后易脱节）
    C4 章号首尾    文件名章号 == 正文首行章号 + 章号连续无缺 —— ERROR
    C5 时间轴      每章首个日期，出现倒流 —— WARN；全表 INFO
    C6 调用账      「第N次」调用序列抽表；同章序号重复 —— WARN
    C7 人物间隔    主角团每章出场表；>8 章未出场 —— WARN
    C8 物件/钱账   关键道具与金额的按章抽表（人工核钱账）—— INFO

只读稿件与台账、只出清单：不改稿、不联网、仅用标准库。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(BASE, "正文_重写版")
LEDGER = os.path.join(BASE, "outlines", "章末钩子台账.md")
INFO_FILE = os.path.join(BASE, "一致性抽表_最新.md")

# ───────────────────────── 规则表 ─────────────────────────

# C1：规范名 → 已知误写变体（命中即 ERROR）。支持正则，用「李建(?!国)」排除规范名自身
NAME_VARIANTS = {
    "李志明": ["李志民", "李志铭", "李志朋"],
    "凯子/周凯": ["周凯子", "周恺"],
    "程霜": ["程双", "程孀", "程爽"],
    "陈冉": ["陈再", "陈苒", "陈然", "陈冄"],
    "老闫": ["老阎", "阎老师"],
    "老周": ["老邹"],
    "孙磊": ["孙蕾", "孙垒"],
    "李建国": ["李建(?!国)"],
}

# C2：引号外允许出现的「妈／爸」口语（白名单，其余报候选）
KIN_OK = re.compile(
    r"(他妈的|妈的|他妈|她妈|他爸|她爸|你妈|你爸|我妈|我爸|"
    r"大妈|大爷|大伯|老妈|老爸|爸妈|爹妈|妈呀|姑妈|姨妈|舅妈|干妈|后妈)"
)

# C5：回忆豁免词（句内含这些词的日期不参与倒流判定）
MEMORY_OK = re.compile(r"(上一世|上辈子|前世|重回|重生|回来那天|那天早上|那一年|当年|那时候)")

CN_NUM = "一二三四五六七八九十"
DATE_RE = re.compile(r"([%s]*十?[%s]*)月([%s]*十?[%s]*)[号日]" % (CN_NUM, CN_NUM, CN_NUM, CN_NUM))
CALL_RE = re.compile(r"第([%s]+)次" % CN_NUM)

ROLES = {
    "李志明": ["李志明", "志明", "明哥"],
    "凯子": ["凯子", "周凯"],
    "陈冉": ["陈冉"],
    "程霜": ["程霜"],
    "母亲": ["母亲"],
    "父亲": ["父亲", "李建国"],
    "老闫": ["老闫", "闫老师"],
    "老周": ["老周"],
    "孙磊": ["孙磊"],
}
PROPS = ["软皮本", "糖纸", "随身听", "歌碟", "音箱", "皮筋", "圆珠笔", "黑皮本", "软盘"]
MONEY_RE = re.compile(r"([0-9]+|[%s百]+)(块钱|块|元|毛|分)" % CN_NUM)

# C7：不同角色的"晾太久"阈值（主角团紧，次要角色松）
GAP = {"李志明": 99, "凯子": 8, "陈冉": 8, "程霜": 8,
       "母亲": 10, "父亲": 12, "老闫": 12, "老周": 12, "孙磊": 12}
# C5：第 1 章是 2027 年的序言，不参与 2006 时间轴比较
PROLOGUE_CH = 1


def cn2int(s):
    d = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if not s:
        return 0
    if s.isdigit():
        return int(s)
    if "十" in s:
        a, _, b = s.partition("十")
        return (d.get(a, 1) if a else 1) * 10 + (d.get(b, 0) if b else 0)
    return d.get(s, 0)


# ───────────────────────── 读稿 ─────────────────────────

def ch_files(d):
    out = []
    for fn in sorted(os.listdir(d)):
        m = re.match(r"第(\d+)章-(.+)\.md$", fn)
        if m:
            out.append((int(m.group(1)), m.group(2), fn))
    out.sort()
    return out


def body_of(p):
    with open(p, encoding="utf-8") as f:
        raw = f.read()
    lines = [l.rstrip() for l in raw.splitlines()]
    # 去掉章首标题行
    while lines and (not lines[0].strip() or lines[0].lstrip().startswith("#")):
        lines.pop(0)
    return raw, lines


def last_sentence(lines):
    for l in reversed(lines):
        s = l.strip()
        if s and s != "······":
            return s
    return ""


def tail_block(lines, n=2):
    """正文末 n 个非空句，按原文顺序拼接（台账可能登记的是两三句）"""
    got = []
    for l in reversed(lines):
        s = l.strip()
        if s and s != "······":
            got.append(s)
            if len(got) >= n:
                break
    return "".join(reversed(got))


def strip_quotes(text):
    """把中文弯引号内的内容挖空（对白），只留叙述语"""
    return re.sub(r"“[^”]*”", "　", text, flags=re.S)


# ───────────────────────── C3 台账 ─────────────────────────

def load_hook_ledger():
    tbl = {}
    if not os.path.exists(LEDGER):
        return tbl
    with open(LEDGER, encoding="utf-8") as f:
        for ln in f:
            m = re.match(r"^\|\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(.+?)\s*\|\s*$", ln)
            if m:
                tbl[int(m.group(1))] = (m.group(2), m.group(3))
    return tbl


# ───────────────────────── 检查 ─────────────────────────

def run(d, rng, only, show_info):
    files = ch_files(d)
    if rng:
        a, b = rng
        files = [f for f in files if a <= f[0] <= b]
    errs, warns, infos = [], [], []

    def E(c, msg):
        errs.append("[%s] %s" % (c, msg))

    def W(c, msg):
        warns.append("[%s] %s" % (c, msg))

    def I(c, msg):
        infos.append("[%s] %s" % (c, msg))

    def want(c):
        return (not only) or (c.lower() in only)

    hook = load_hook_ledger()
    docs = []
    for no, title, fn in files:
        raw, lines = body_of(os.path.join(d, fn))
        # body＝去掉章首标题后的正文（标题里的「凯子的妈」之类不当叙述语）
        body = "\n".join(lines)
        docs.append((no, title, fn, raw, lines, body))

    # C4 章号
    if want("c4"):
        nums = [x[0] for x in docs]
        for i in range(1, len(nums)):
            if nums[i] != nums[i - 1] + 1:
                E("C4章号", "缺章：%d 之后直接到 %d" % (nums[i - 1], nums[i]))
        for no, title, fn, raw, lines, body in docs:
            m = re.match(r"^#\s*第(\d+)章\s*(.*)$", raw.splitlines()[0].strip())
            if not m:
                E("C4章号", "第%d章 首行不是「# 第N章 标题」：%s" % (no, raw.splitlines()[0][:30]))
            elif int(m.group(1)) != no:
                E("C4章号", "第%d章 文件名与首行章号不符（首行 %s）" % (no, m.group(1)))
            elif m.group(2).strip() and m.group(2).strip() != title:
                W("C4章号", "第%d章 标题不一致：文件名「%s」vs 首行「%s」" % (no, title, m.group(2).strip()))

    # C1 名字变体
    if want("c1"):
        for no, title, fn, raw, lines, body in docs:
            for canon, bads in NAME_VARIANTS.items():
                for b in bads:
                    if re.search(b, body):
                        E("C1名字", "第%d章 出现「%s」（规范名：%s）" % (no, b, canon))

    # C2 称谓
    if want("c2"):
        for no, title, fn, raw, lines, body in docs:
            narr = strip_quotes(body)
            for m in re.finditer(r"[妈爸]", narr):
                seg = narr[max(0, m.start() - 6): m.start() + 6]
                if KIN_OK.search(seg):
                    continue
                W("C2称谓", "第%d章 叙述语口语：「%s」（定案：叙述语一律母亲／父亲）" % (no, seg.strip()))

    # C3 章末对表
    if want("c3"):
        for no, title, fn, raw, lines, body in docs:
            if no not in hook:
                I("C3章末", "第%d章 台账无此行" % no)
                continue
            htype, htail = hook[no]
            tail = tail_block(lines, 3)
            last = last_sentence(lines)
            if htail == "待判" or not htail:
                continue
            a = htail.replace(" ", "")
            b = tail.replace(" ", "")
            if a in b or b in a or a[:12] == last.replace(" ", "")[:12]:
                continue
            W("C3章末", "第%d章 台账记「%s」／正文末两句「%s」——改稿后请同步台账"
              % (no, a[:30], b[:30]))

    # C5 时间轴
    if want("c5"):
        prev_no, prev_d = None, None
        table = []
        for no, title, fn, raw, lines, body in docs:
            ds = []
            # 只在叙述语里找日期（引号内的账页引述、书写内容不算叙事时点）
            for m in DATE_RE.finditer(strip_quotes(body)):
                narr = strip_quotes(body)
                line_start = narr.rfind("\n", 0, m.start()) + 1
                line_end = narr.find("\n", m.end())
                sent = narr[line_start: line_end if line_end > 0 else len(narr)]
                if MEMORY_OK.search(sent):
                    continue
                mo, dd = cn2int(m.group(1)), cn2int(m.group(2))
                ds.append((mo, dd, m.group(0)))
            if not ds:
                table.append((no, "—"))
                continue
            first = ds[0]
            table.append((no, "首 %s｜共 %d 处（%s）" % (first[2], len(ds), "、".join(d[2] for d in ds[:6]))))
            if no > PROLOGUE_CH and prev_no and prev_no > PROLOGUE_CH \
                    and prev_d and (first[0], first[1]) < prev_d:
                W("C5时间", "第%d章 首现日期 %s 早于第%d章的 %s——确认是不是回忆/倒叙"
                  % (no, first[2], prev_no, "%d月%d日" % prev_d))
            prev_no, prev_d = no, (first[0], first[1])
        I("C5时间", "按章日期：" + " ｜ ".join("%d:%s" % t for t in table))

    # C6 调用账
    if want("c6"):
        for no, title, fn, raw, lines, body in docs:
            hits = []
            for m in CALL_RE.finditer(body):
                line_start = body.rfind("\n", 0, m.start()) + 1
                line_end = body.find("\n", m.end())
                sent = body[line_start: line_end if line_end > 0 else len(body)]
                if not re.search(r"问|调用|换|知了|查询|它", sent):
                    continue
                hits.append((m.group(1), m.group(0), sent.strip()[:40]))
            if not hits:
                continue
            seq = [h[0] for h in hits]
            dup = [x for x in set(seq) if seq.count(x) > 1]
            if dup:
                W("C6调用", "第%d章 同章内序号重复：%s" % (no, "、".join(dup)))
            I("C6调用", "第%d章 调用序列：%s　｜例：%s"
              % (no, "→".join(h[1] for h in hits), hits[0][2]))

    # C7 人物间隔
    if want("c7"):
        last_seen = {r: None for r in ROLES}
        for no, title, fn, raw, lines, body in docs:
            for r, names in ROLES.items():
                if any(n in body for n in names):
                    gap = no - last_seen[r] if last_seen[r] is not None else 0
                    if last_seen[r] is not None and gap > GAP.get(r, 10):
                        W("C7人物", "%s 距上次出场（第%d章）已 %d 章（阈值 %d）"
                          % (r, last_seen[r], gap, GAP.get(r, 10)))
                    last_seen[r] = no
        for r in ROLES:
            if last_seen[r] is None:
                W("C7人物", "%s 全书未出场" % r)
        I("C7人物", "末次出场：" + "｜".join("%s@%s" % (r, last_seen[r] or "—") for r in ROLES))

    # C8 物件/钱账
    if want("c8"):
        for p in PROPS:
            chs = [str(no) for no, t, fn, raw, l, b in docs if p in b]
            if chs:
                I("C8物件", "%s：%s" % (p, "、".join(chs)))
        for no, title, fn, raw, lines, body in docs:
            ms = MONEY_RE.findall(raw)
            if ms:
                uniq = list(dict.fromkeys("".join(m) for m in ms))
                I("C8钱账", "第%d章 金额：%s" % (no, "、".join(uniq[:10])))

    # ── 输出 ──
    print("⑤一致性 · %s（%d 章）" % (os.path.basename(d.rstrip("/")), len(docs)))
    print("─" * 60)
    if errs:
        print("ERROR %d" % len(errs))
        for x in errs:
            print("   x " + x)
    if warns:
        print("WARN  %d" % len(warns))
        for x in warns:
            print("   ! " + x)
    if not errs and not warns:
        print("   ✓ 无 ERROR / WARN")
    # INFO 抽表默认落盘（不占上下文），只有 --info 才打到屏幕
    if infos:
        with open(INFO_FILE, "w", encoding="utf-8") as f:
            f.write("# 一致性抽表（tools/consistency.py 自动生成，勿手改）\n")
            f.write("# 用法：跑完 Read 本文件核对跨章账；要打到屏幕就加 --info\n\n")
            for x in infos:
                f.write("- " + x + "\n")
        if show_info:
            print("INFO  %d" % len(infos))
            for x in infos:
                print("   · " + x)
        else:
            print("INFO  %d 条 → %s（要看就 Read 它，或加 --info 打印）"
                  % (len(infos), os.path.basename(INFO_FILE)))
    print("─" * 60)
    print("判法：ERROR 必改；WARN 逐条人工判（误报就说出来，别改稿迁就尺子）；INFO 只作对表。")
    return len(errs)


def main():
    a = sys.argv[1:]
    d = DEFAULT_DIR
    rng = None
    only = ""
    show_info = "--info" in a          # 默认不打印 INFO（落盘），加此开关才打印
    if "--dir" in a:
        d = os.path.join(BASE, a[a.index("--dir") + 1])
    if "--range" in a:
        s = a[a.index("--range") + 1]
        if "-" in s:
            lo, hi = s.split("-")
            rng = (int(lo), int(hi))
        else:
            rng = (int(s), int(s))
    if "--only" in a:
        only = a[a.index("--only") + 1].lower()
    return run(d, rng, only, show_info)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
