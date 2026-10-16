# -*- coding: utf-8 -*-
"""
老板钦定规范第12条 · 口径 A'（真保守）
只改三类，其余保留「他」：
  R1 章首金句段（正文前 2 个非空行）
  R2 章尾金句段（正文最后 3 个非空行）
  R3 情感高点行（含情感词，且主语=李志明）
  R4 歧义块（同一段落块内同时出现「李志明」和另一个具体男性角色名，且主语=李志明）
硬排除：他们 / 他妈 / 他爸（原样保留）；主语非李志明（禁改）
用法：
  python3 replace_ta_A.py          # dry-run，只统计
  python3 replace_ta_A.py --apply  # 落盘
"""
import os, re, sys, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "正文")

# 具体男性角色（泛指词「有人/别人/那人」已移除，避免误判）
MALE_OTHER = ["凯子", "周凯", "老宋", "刀哥", "周师傅", "陈师傅", "魏老板", "老三", "马涛",
              "老徐", "周哥", "王主任", "老闫", "冯三", "刘卫东", "张小峰", "李建国",
              "医生", "警察", "司机", "男人", "小伙子", "男孩", "少年"]
SELF = "李志明"
KEEP = ("他们", "他妈", "他爸")
NON_SELF_HEAD = "他爸"          # 「他爸」开头 → 主语切为爸（禁改）
ALL_HEAD = MALE_OTHER + [SELF, NON_SELF_HEAD]
SENT_START = re.compile(r"(^|[。！？…\"”]{1,3})\s*(" + "|".join(re.escape(m) for m in ALL_HEAD) + r")")

# 情感高点词
EMO = ["眼泪", "泪", "哭了", "哭得", "哭出", "跪", "喉咙发紧", "浑身发抖", "手在抖",
       "说不出话", "心被狠狠", "心像被", "心脏猛地", "眼泪砸", "哭得喘", "一声都没喊",
       "喉咙", "发紧", "发抖", "攥紧", "拳头", "咬着", "忍住", "忍了", "画了一笔",
       "伸手，摸了摸", "抱在怀里", "低下头", "闭上眼睛", "红了"]

def build_blocks(lines):
    blocks, cur = [], []
    for i, l in enumerate(lines):
        if l.strip() == "":
            if cur: blocks.append(cur); cur = []
        else:
            cur.append(i)
    if cur: blocks.append(cur)
    return blocks

def process(path, apply=False):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    body_idx = [i for i, l in enumerate(lines) if l.strip() and not l.startswith("#")]
    if not body_idx:
        return 0, []
    head_end = body_idx[min(1, len(body_idx) - 1)]          # 章首前 2 个正文行
    tail_start = body_idx[max(0, len(body_idx) - 3)]        # 章尾后 3 个正文行

    # 歧义窗口：当前行 + 前 4 个正文行 + 后 1 个正文行内，是否出现另一具体男性角色
    amb_window = {}
    for pos, i in enumerate(body_idx):
        lo = max(0, pos - 4)
        hi = min(len(body_idx), pos + 2)
        txt = "".join(lines[k] for k in body_idx[lo:hi])
        amb_window[i] = (SELF in txt) and any(m in txt for m in MALE_OTHER)

    subject = SELF
    out = []
    changed = 0
    log = []
    for i, line in enumerate(lines):
        if not line.strip() or line.startswith("#"):
            out.append(line); continue
        # 行内句首男性名（按顺序），供「他」就近取主语
        heads = [(m.start(2), m.group(2)) for m in SENT_START.finditer(line)]
        if heads:
            subject = heads[-1][1]      # 行末主语传给下一行

        new_line = line
        # 只要本行存在「他」之前有李志明作句首，就逐字就近判定
        if "他" in line:
            is_head = i <= head_end
            is_tail = i >= tail_start
            is_emo = any(e in line for e in EMO)
            is_amb = amb_window.get(i, False)
            if is_head or is_tail or is_emo or is_amb:
                buf, k = [], 0
                while k < len(line):
                    if line[k] == "他" and line[k:k + 2] not in KEEP:
                        # 就近主语：取「他」之前最近的一个句首男性名，没有则继承上行主语
                        subj = subject
                        for pos, nm in heads:
                            if pos < k:
                                subj = nm
                            else:
                                break
                        # 反制：同一小句里「李志明」已在「他」之前 → 此「他」指别人（如「李志明看着他」）
                        # 限定「同一小句」：这 12 字内不得有句读，否则视为跨句（仍指主角，照改）
                        before = line[max(0, k - 12):k]
                        skip = (SELF in before and not re.search(r"[。，、；！？]", before))
                        if subj == SELF and not skip:
                            buf.append(SELF); changed += 1
                            log.append((i + 1, line.strip()))
                        else:
                            buf.append("他")
                    else:
                        buf.append(line[k])
                    k += 1
                new_line = "".join(buf)
        out.append(new_line)

    if apply and changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(out))
    return changed, log

def main():
    apply = "--apply" in sys.argv
    files = sorted(f for f in os.listdir(SRC) if f.endswith(".md"))
    total = 0
    per = []
    for fn in files:
        c, log = process(os.path.join(SRC, fn), apply)
        total += c
        if c:
            per.append((fn, c))
    print(f"{'已落盘' if apply else 'DRY-RUN'}：共改 {total} 处，涉及 {len(per)} 章")
    for fn, c in sorted(per, key=lambda x: -x[1])[:15]:
        print(f"  {c:5d}  {fn}")
    if not apply:
        # 抽查前 12 条改动
        print("\n=== 抽查前 12 处改动 ===")
        n = 0
        for fn in files:
            _, log = process(os.path.join(SRC, fn), False)
            for ln, s in log[:3]:
                print(f"  {fn}:{ln} | {s[:60]}")
                n += 1
                if n >= 12: break
            if n >= 12: break

if __name__ == "__main__":
    main()
