# -*- coding: utf-8 -*-
"""
第二版：主语追踪 + 段落块级判定。
- 维护 current_subject（章首默认 = 李志明）
- 只有「句首」出现的男性名才切换主语（句尾出现视为宾语）
- 按空行分块（block），区分 block 首行 / block 内部
只分析、不修改。
"""
import os, re, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "正文")

MALE_OTHER = ["凯子", "周凯", "老宋", "刀哥", "周师傅", "陈师傅", "魏老板", "老三", "马涛",
              "老徐", "周哥", "王主任", "老闫", "冯三", "刘卫东", "张小峰",
              "医生", "警察", "司机", "男人", "小伙子", "男孩", "少年", "那人", "那个人",
              "有人", "每个人", "别人", "表叔", "表弟", "李建国"]
SELF = "李志明"
KEEP = ("他们", "他妈", "他爸")
# “他爸”也作为主语切换标记（切到「非主角」），防止“他爸在打字。他的手指…”被误改
NON_SELF_HEAD = "他爸"
ALL_HEAD = MALE_OTHER + [SELF, NON_SELF_HEAD]
SENT_START = re.compile(r"(^|[。！？…\"”]{1,3})\s*(" + "|".join(re.escape(m) for m in ALL_HEAD) + r")")

def first_male_at_sentence_start(line):
    """返回该行第一个「句首位置」的男性名（含李志明/他爸），没有则 None"""
    m = SENT_START.search(line)
    return m.group(2) if m else None

def main():
    files = sorted(f for f in os.listdir(SRC) if f.endswith(".md"))
    stat = collections.Counter()
    samples = collections.defaultdict(list)

    for fn in files:
        with open(os.path.join(SRC, fn), encoding="utf-8") as f:
            lines = f.read().split("\n")
        body = [(i, l) for i, l in enumerate(lines) if l.strip() and not l.startswith("#")]
        if not body:
            continue
        first_b, last_b = body[0][0], body[-1][0]

        subject = SELF
        # 先分 block
        blocks, cur = [], []
        for i, l in enumerate(lines):
            if l.strip() == "":
                if cur:
                    blocks.append(cur); cur = []
            else:
                cur.append((i, l))
        if cur:
            blocks.append(cur)

        block_of = {}
        for bi, blk in enumerate(blocks):
            for idx, (i, l) in enumerate(blk):
                block_of[i] = (bi, idx)

        for i, line in enumerate(lines):
            if not line.strip() or line.startswith("#"):
                continue
            bi, bpos = block_of.get(i, (0, 0))
            is_block_head = (bpos == 0)

            # 更新主语：本行句首出现的男性名
            nm = first_male_at_sentence_start(line)
            if nm:
                subject = nm

            for mo in re.finditer("他", line):
                j = mo.start()
                if line[j:j + 2] in KEEP:
                    stat["0_保留(他们/他妈/他爸)"] += 1
                    continue
                if subject != SELF:
                    stat["1_主语非主角(禁改)"] += 1
                    if len(samples["1_主语非主角(禁改)"]) < 8:
                        samples["1_主语非主角(禁改)"].append(f"{fn}:{i+1} | {line[max(0,j-14):j+14]}")
                    continue
                # 主语是李志明
                if i <= first_b + 1:
                    cat = "2_章首金句(改)"
                elif i >= last_b - 2:
                    cat = "3_章尾金句(改)"
                elif is_block_head:
                    cat = "4_段首锚定(改)"
                else:
                    cat = "5_段内连续动作(留)"
                stat[cat] += 1
                if len(samples[cat]) < 8:
                    samples[cat].append(f"{fn}:{i+1} | {line[max(0,j-14):j+14]}")

    print("=== 第二版分类统计 ===")
    for k, v in sorted(stat.items()):
        print(f"{k:26s} {v:6d}")
    chg = sum(v for k, v in stat.items() if k.endswith("(改)"))
    print(f"\n>>> A 方案实际改动量 ≈ {chg}")
    print(f">>> 保留不动 ≈ {stat['0_保留(他们/他妈/他爸)'] + stat['1_主语非主角(禁改)'] + stat['5_段内连续动作(留)']}")

    print("\n=== 样本 ===")
    for k in sorted(samples):
        print(f"\n--- {k} ---")
        for s in samples[k][:6]:
            print("  " + s)

if __name__ == "__main__":
    main()
