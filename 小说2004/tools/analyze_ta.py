# -*- coding: utf-8 -*-
"""
分析《带着GPT重回高中》正文中“他”的用法分布，为 A 方案（分级替换）做候选标注。
只分析、不修改。
"""
import os, re, json, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "正文")

# 其他男性角色（出现时可能成为“他”的真实指代对象）
MALE_OTHER = [
    "凯子", "周凯", "老宋", "刀哥", "周师傅", "陈师傅", "魏老板", "老三", "马涛",
    "老徐", "周哥", "王主任", "老闫", "冯三", "刘卫东", "张小峰", "陈冉爸",
    "医生", "警察", "司机", "业务员", "男人", "小伙子", "男孩", "少年", "老板",
    "那人", "那个人", "有人", "每个人", "别人", "谁", "表叔", "表弟", "弟弟",
    "我爸", "他爸", "凯子爸", "李建国",
]
KEEP = ("他们", "他妈", "他爸")

def has_other_male(line, exclude_self=True):
    for m in MALE_OTHER:
        if m in line:
            return True
    return False

def main():
    files = sorted(f for f in os.listdir(SRC) if f.endswith(".md"))
    stat = collections.Counter()
    samples = collections.defaultdict(list)

    for fn in files:
        path = os.path.join(SRC, fn)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        lines = text.split("\n")
        # 正文行 = 非空、非标题
        body_idx = [i for i, l in enumerate(lines) if l.strip() and not l.startswith("#")]
        if not body_idx:
            continue
        first_body = body_idx[0]
        last_body = body_idx[-1]

        for i, line in enumerate(lines):
            if not line.strip() or line.startswith("#"):
                continue
            for mo in re.finditer("他", line):
                j = mo.start()
                nxt = line[j + 1:j + 2]
                if line[j:j + 2] in KEEP:
                    stat["keep_他们他妈他爸"] += 1
                    continue
                prev = line[:j]
                seg = line[max(0, j - 12):j + 14]
                # 分类
                cat = None
                # ③章首/章尾金句段
                if i <= first_body + 1:
                    cat = "C1_章首金句"
                elif i >= last_body - 2:
                    cat = "C2_章尾金句"
                # ①歧义：本行同时有李志明和其他男性
                elif "李志明" in line and has_other_male(line):
                    cat = "A1_行内双男性(歧义高风险)"
                # 上一行情况
                else:
                    prevline = lines[i - 1] if i > 0 else ""
                    if "李志明" in prevline and has_other_male(prevline):
                        cat = "A2_上行双男性(歧义高风险)"
                    elif "李志明" in line and not has_other_male(line) and not has_other_male(prevline):
                        cat = "B1_行内单指(低风险可改)"
                    elif "李志明" in prevline and not has_other_male(prevline):
                        cat = "B2_上行单指(低风险可改)"
                    elif has_other_male(prevline) or has_other_male(line):
                        cat = "A3_疑似指别人(禁改)"
                    else:
                        cat = "D_无明确锚点(需人工)"
                stat[cat] += 1
                if len(samples[cat]) < 12:
                    samples[cat].append(f"{fn}:{i+1} | ...{seg}...")

    print("=== 全书「他」分类统计（已排除 他们/他妈/他爸）===")
    total = sum(v for k, v in stat.items() if k != "keep_他们他妈他爸")
    for k, v in sorted(stat.items(), key=lambda x: -x[1]):
        print(f"{k:28s} {v:6d}")
    print(f"{'合计(可判定)':28s} {total:6d}")

    print("\n=== 各类样本 ===")
    for k in sorted(samples):
        print(f"\n--- {k} ---")
        for s in samples[k][:8]:
            print("  " + s)

if __name__ == "__main__":
    main()
