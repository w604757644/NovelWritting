#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《我真没想重生啊》· 蒸馏统计（给《带着GPT重回高中》当参照基线）
================================================================
不整读语料，只逐行扫描计数。统计两件事：
  ① 内容配比：学习／感情／家庭／友谊／工作／日常 各占多少
  ② 描写方式：对话占比、肢体情态密度、五感词、心理、数字

用法：
    python3 tools/distill_stats.py                 # 全书 200 章
    python3 tools/distill_stats.py --limit 60      # 只看前 60 章
"""
import argparse
import os
import re

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                    '蒸馏_语料', '我真没想重生啊', 'raw200')

# ---------------- ① 内容配比词表（按「段落」判，取命中最多的一类） ----------------
TOPIC = {
    '学习校园': ['学校', '大学', '高中', '上课', '下课', '考试', '成绩', '分数', '老师', '同学',
                '教室', '宿舍', '专业', '学分', '考研', '毕业', '开学', '作业', '试卷', '题目',
                '复习', '自习', '班长', '系里', '学号', '录取', '分数线', '招生'],
    '感情暧昧': ['喜欢', '心跳', '脸红', '牵手', '吻', '恋爱', '女朋友', '男朋友', '暧昧',
                '心动', '表白', '约会', '暗恋', '初恋', '吃醋', '嫁', '娶'],
    '家庭亲情': ['爸', '妈', '娘', '家里', '父母', '亲戚', '回家', '家人', '爷', '奶', '叔', '姑'],
    '友谊兄弟': ['兄弟', '哥们', '朋友', '死党', '室友', '老乡', '搭档', '合伙人'],
    '工作事业': ['公司', '创业', '生意', '项目', '客户', '赚', '投资', '员工', '老板',
                '合同', '市场', '订单', '融资', '营业', '产品', '团队', '业务'],
    '日常烟火': ['吃饭', '睡觉', '走路', '天气', '街', '食堂', '超市', '车站', '雨', '雪'],
}

GESTURE = ["摇头", "点了点头", "点头", "低下头", "低头", "抬起头", "抬头", "皱眉", "眯眼",
           "瞪", "瞥", "抿嘴", "撇嘴", "咧嘴", "攥", "搓", "捏", "握", "拍", "摸",
           "挠", "掰", "抠", "戳", "摆手", "招手", "耸肩", "肩膀", "喉结", "咽"]
SAY = ["说", "道", "问", "答", "喊", "叫", "骂", "嘀咕", "嘟囔", "开口"]
SENSE = list("凉冷热烫暖潮湿腥甜苦涩香臭麻硬软沉")
MIND = ["心想", "心里想", "心里", "脑海中", "忽然想到", "想起", "觉得", "感觉"]
ENV = ["窗", "天", "风", "雨", "树", "灯", "墙", "路", "云", "太阳", "月", "山", "水"]
NUM = re.compile(r'[0-9０-９一二三四五六七八九十百千万零两]{1,}')


def classify(p):
    best, bn = '其他', 0
    for k, ws in TOPIC.items():
        n = sum(p.count(w) for w in ws)
        if n > bn:
            best, bn = k, n
    return best if bn else '其他'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()

    files = sorted(f for f in os.listdir(BASE) if f.endswith('.md'))
    if a.limit:
        files = files[:a.limit]

    tc = {k: [0, 0] for k in TOPIC}          # [段数, 字数]
    tc['其他'] = [0, 0]
    tp = ts = tg = ty = te = tm = tsen = tnum = tsay = 0
    paras = []

    for fn in files:
        for l in open(os.path.join(BASE, fn), encoding='utf-8'):
            s = l.strip()
            if not s or s.startswith('#') or set(s) <= {'·', '…', '—', '.', '-'}:
                continue
            paras.append(s)
            tp += 1
            cjk = len(re.findall(r'[\u4e00-\u9fff]', s))
            ts += cjk
            if '"' in s or '"' in s or s.startswith('“'):
                ty += 1
            tg += sum(s.count(w) for w in GESTURE)
            te += sum(s.count(w) for w in ENV)
            tm += sum(s.count(w) for w in MIND)
            tsay += sum(s.count(w) for w in SAY)
            tsen += sum(s.count(c) for c in SENSE)
            tnum += len(NUM.findall(s))
            k = classify(s)
            tc[k][0] += 1
            tc[k][1] += cjk

    print(f"语料：{len(files)} 章 ｜ 段落 {tp} ｜ 字数 {ts:,}")
    print()
    print("【① 内容配比】按段落数与字数双口径")
    print(f"  {'类别':<10}{'段数':>7}{'段%':>8}{'字数':>10}{'字%':>8}")
    print('  ' + '-' * 45)
    for k, (pn, wc) in sorted(tc.items(), key=lambda x: -x[1][1]):
        print(f'  {k:<10}{pn:>7}{pn/tp*100:>7.1f}%{wc:>10,}{wc/ts*100:>7.1f}%')
    print()

    # ---------------- ② 描写方式 ----------------
    print("【② 描写方式】密度均为 /千字")
    print(f"  肢体情态        {tg/(ts/1000):>7.2f}")
    print(f"  说类词         {tsay/(ts/1000):>7.2f}")
    print(f"  说:做 比       {tsay/max(tg,1):>7.1f}:1")
    print(f"  对话行占比     {ty/tp*100:>7.1f}%")
    print(f"  心理/内心      {tm/(ts/1000):>7.2f}")
    print(f"  环境景物       {te/(ts/1000):>7.2f}")
    print(f"  五感字         {tsen/(ts/1000):>7.2f}")
    print(f"  数字           {tnum/(ts/1000):>7.2f}")
    print(f"  段落均长(字)   {ts/tp:>7.1f}")


if __name__ == '__main__':
    main()
