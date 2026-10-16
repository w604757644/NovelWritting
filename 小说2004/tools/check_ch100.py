# -*- coding: utf-8 -*-
"""抽查：打印某章里被判为「主语非主角(禁改)」的所有句子，人工核对误判率"""
import os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "正文")
MALE_OTHER = ["凯子", "周凯", "老宋", "刀哥", "周师傅", "陈师傅", "魏老板", "老三", "马涛",
              "老徐", "周哥", "王主任", "老闫", "冯三", "刘卫东", "张小峰",
              "医生", "警察", "司机", "男人", "小伙子", "男孩", "少年", "那人", "那个人",
              "有人", "每个人", "别人", "表叔", "表弟", "李建国"]
SELF = "李志明"
KEEP = ("他们", "他妈", "他爸")
SENT_START = re.compile(r"(^|[。！？…\"”]{1,3})\s*(" + "|".join(re.escape(m) for m in MALE_OTHER + [SELF]) + r")")

fn = sys.argv[1] if len(sys.argv) > 1 else "第100章-你上次也是这么问的.md"
with open(os.path.join(SRC, fn), encoding="utf-8") as f:
    lines = f.read().split("\n")

subject = SELF
print(f"### {fn} —— 被判「非主角(禁改)」的句子：\n")
n = 0
for i, line in enumerate(lines):
    if not line.strip() or line.startswith("#"):
        continue
    nm = SENT_START.search(line)
    if nm:
        subject = nm.group(2)
    if subject == SELF:
        continue
    for mo in re.finditer("他", line):
        j = mo.start()
        if line[j:j + 2] in KEEP:
            continue
        n += 1
        print(f"  L{i+1} [主语={subject}] {line.strip()}")
print(f"\n共 {n} 处")
