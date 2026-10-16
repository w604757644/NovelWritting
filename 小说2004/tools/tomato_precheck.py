#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄上传前预检 · 单章 / 批量
============================================================
在把稿子交给番茄之前跑一遍，目的是降低两件事的概率：
  1) 被朱雀（腾讯 DetectAI）判定为机器文本
  2) 命中番茄官方《关于加强低质内容治理公告》的四类低质

本脚本只做「机器可判」的部分；语义项（是否读得下去、是否符合人设）仍需人工。

检查项
  A 朱雀启发式五维 —— 子进程调用 deai-promax 的 zhuque_heuristic_check.py（近似，非官方）
  B 对白引导语模板化 —— AI 最容易暴露的地方（「X 说」「X 站在那儿」机械复现）
  C 高频词超载 —— 单个词在一章内被反复使用
  D 番茄低质红线自检 —— 流水账 / 句式重复 / 模板拼接 / 格式

用法
  python3 tools/tomato_precheck.py --dir 正文_新版 --chapter 24
  python3 tools/tomato_precheck.py --dir 正文_新版 --range 1-30
  python3 tools/tomato_precheck.py --file 正文_新版/第24章-帮对手.md
  python3 tools/tomato_precheck.py --dir 正文_新版 --range 1-30 --quiet   # 只列风险汇总

退出码：0 = 全部通过；1 = 有高风险项
"""
import argparse
import os
import re
import sys
import subprocess
import collections

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ZHUQUE = os.path.expanduser(
    '~/.workbuddy/skills/deai-promax/scripts/zhuque_heuristic_check.py')

DASH_RE = re.compile(r'—+')
SEP_RE = re.compile(r'^[·•]{4,}$')

# 常见「无进度」动作句，一章里反复出现 = 模板化
ACT_PHRASES = [
    '站在那儿', '站在那', '站在他旁边', '挠了挠后脑勺', '挠后脑勺',
    '抬起头', '低下头', '抬了下头', '愣了一下', '愣住', '停住',
    '顿了一下', '没说话', '没答', '没接话', '把笔放下', '放下笔',
    '点了点头', '摇了摇头', '张了张嘴', '转过头', '转过身',
    '咧开嘴', '笑了', '沉默了', '看着窗外',
]
SPEAK_RE = re.compile(r'([\u4e00-\u9fff]{2,3})(说道|说|问道|问|答道|答|喊道|喊|回道|开口)(?=[，。：:""])')

# 易在长篇里超载的词（不是你写错了，是用多了就成「可预测」）
HOT_WORDS = [
    '最后', '然后', '但是', '其实', '已经', '还是', '终于', '忽然', '突然',
    '默默', '轻轻', '缓缓', '慢慢', '微微', '静静', '当然', '毕竟', '反正',
    '于是', '接着', '而且', '不过', '好像', '似乎', '终于', '只剩下',
]
# 单独成段的「流水账」碎片：纯时间 / 纯次数 / 纯数字
LEDGER_RE = re.compile(
    r'^[（(]?[一二三四五六七八九十百千零两\d]+[)）]?\s*(次|遍|天|分钟|秒|点|分|号|人|句|个|行|页)?[。！？…]?$')
TIME_HEAD_RE = re.compile(
    r'^(周[一二三四五六日天]|第[一二三四五六七八九十\d]+[天次个月]|今天|昨天|明天|上午|下午|晚上|中午|傍晚|夜里|第二天)')


def cjk(s):
    return len(re.findall(r'[\u4e00-\u9fff]', s))


def load(path):
    raw = open(path, encoding='utf-8').read()
    paras = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith('#') or SEP_RE.match(s):
            continue
        if (s.startswith('**') and s.endswith('**')) or (s.startswith('*') and s.endswith('*')):
            continue
        paras.append(s)
    return raw, paras


def check_zhuque(path):
    """A · 调用 deai-promax 的朱雀启发式脚本，返回 (综合分, 五维 dict, 明细) 或 None"""
    if not os.path.exists(ZHUQUE):
        return None
    try:
        out = subprocess.run([sys.executable, ZHUQUE, path],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return None
    m = re.search(r'综合 AI 疑似度：(\d+)', out)
    if not m:
        return None
    dims = {}
    for name, key in [('突发性', '突发性'), ('困惑度', '困惑度'),
                      ('词汇分布', '词汇分布'), ('标点', '标点'), ('逻辑', '逻辑')]:
        mm = re.search(rf'{key}[^:：]*[:：]\s*(\d+)/100', out)
        if mm:
            dims[name] = int(mm.group(1))
    detail = re.search(r'AI 偏好词命中：(.+)', out)
    return int(m.group(1)), dims, (detail.group(1).strip() if detail else '')


def check_dialogue(paras):
    """B · 对白引导语模板化"""
    hits = []
    c = collections.Counter()
    for p in paras:
        for m in SPEAK_RE.finditer(p):
            c[m.group(0)] += 1
        for ph in ACT_PHRASES:
            if ph in p:
                c[ph] += p.count(ph)
    for s, n in c.most_common():
        if n >= 3:
            hits.append((s, n))
    return hits


def check_hotwords(text):
    """C · 高频词超载 + 重复 8 字串"""
    n = cjk(text)
    per_k = n / 1000 if n else 1
    words = []
    for w in HOT_WORDS:
        cnt = text.count(w)
        if cnt >= 5 and cnt / per_k >= 2:
            words.append((w, cnt, cnt / per_k))
    words.sort(key=lambda x: -x[2])
    # 重复 8 字串（去掉标点与空白后）
    body = re.sub(r'[^\u4e00-\u9fff]', '', text)
    c8 = collections.Counter(body[i:i + 8] for i in range(len(body) - 7))
    grams = [(s, k) for s, k in c8.items() if k >= 3]
    grams.sort(key=lambda x: -x[1])
    return words, grams


def check_lowquality(raw, paras):
    """D · 番茄《低质治理公告》四项机器可判部分"""
    issues = []
    # 流水账：独立成段的纯时间/次数碎片
    frag = [p for p in paras if len(p) <= 8 and LEDGER_RE.match(p.rstrip('。！？…'))]
    if len(frag) >= 8:
        issues.append(f'流水账碎片 {len(frag)} 段（如 {frag[:6]}）')
    # 连续 3 段以上以时间词开头
    run = best = 0
    for p in paras:
        if TIME_HEAD_RE.match(p):
            run += 1
            best = max(best, run)
        else:
            run = 0
    if best >= 3:
        issues.append(f'连续 {best} 段以时间词开头 —— 易被判「机械罗列时间」')
    # 连续 3 段前 2 字相同
    dup = 0
    for i in range(len(paras) - 2):
        a, b, c = (paras[i][:2], paras[i + 1][:2], paras[i + 2][:2])
        if len(a) == 2 and a == b == c:
            dup += 1
    if dup:
        issues.append(f'连续 3 段前 2 字相同 {dup} 处 —— 易被判「句式重复堆砌」')
    # 格式
    if '"' in raw:
        issues.append(f'英文直引号 {raw.count(chr(34))} 个（须为 0）')
    nd = len(DASH_RE.findall(raw))
    if nd / (cjk(raw) / 1000 or 1) > 2.38:
        issues.append(f'破折号密度偏高（{nd} 处）')
    return issues


def audit(path, verbose=True, quiet=False):
    raw, paras = load(path)
    name = os.path.basename(path)
    n = cjk(raw)
    zq = check_zhuque(path)
    dia = check_dialogue(paras)
    words, grams = check_hotwords(raw)
    low = check_lowquality(raw, paras)

    rank = {'OK': 0, 'WATCH': 1, 'HIGH': 2}
    level = 'OK'

    def bump(lv):
        nonlocal level
        if rank[lv] > rank[level]:
            level = lv

    ai = zq[0] if zq else 0
    dia_max = dia[0][1] if dia else 0
    hot = words[0][2] if words else 0.0

    if ai >= 45:
        bump('HIGH')
    elif ai >= 30:
        bump('WATCH')
    if dia_max >= 8:
        bump('HIGH')
    elif dia_max >= 6:
        bump('WATCH')
    if hot >= 4:
        bump('HIGH')
    elif hot >= 3:
        bump('WATCH')
    if len(low) >= 2:
        bump('WATCH')

    if not quiet:
        print(f'── {name}  {n} 字  [{level}]')
        if zq:
            a, dims, det = zq
            d = ' '.join(f'{k}{v}' for k, v in dims.items())
            print(f'   A 朱雀近似 {a}/100  ({d})' + (f'  偏好词：{det}' if det else ''))
        else:
            print('   A 朱雀脚本未找到，已跳过')
        if dia:
            print('   B 对白模板：' + '、'.join(f'{s}×{k}' for s, k in dia[:5]))
        if words:
            print('   C 高频词：' + '、'.join(f'{w}×{k}({d:.1f}/千字)' for w, k, d in words[:5]))
        if grams:
            print('   C 重复串：' + '、'.join(f'{s}×{k}' for s, k in grams[:4]))
        if low:
            for i in low:
                print('   D ✗ ' + i)
        if not (dia or words or grams or low):
            print('   B/C/D 无明显问题')
        print()
    return level, zq, dia, words, grams, low


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir')
    ap.add_argument('--file')
    ap.add_argument('--chapter', type=int)
    ap.add_argument('--range')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()

    files = []
    if a.file:
        files = [a.file if os.path.isabs(a.file) else os.path.join(BASE_DIR, a.file)]
    else:
        d = os.path.join(BASE_DIR, a.dir)
        for f in sorted(os.listdir(d)):
            m = re.match(r'第0?(\d+)章', f)
            if m and f.endswith('.md'):
                files.append((int(m.group(1)), os.path.join(d, f)))
        files.sort()
        if a.chapter:
            files = [p for no, p in files if no == a.chapter]
        elif a.range:
            lo, hi = [int(x) for x in a.range.split('-')]
            files = [p for no, p in files if lo <= no <= hi]
        else:
            files = [p for _, p in files]

    if not files:
        print('没找到章节文件', file=sys.stderr)
        return 1

    print('=' * 72)
    print('番茄上传前预检  |  A 朱雀近似 · B 对白模板 · C 高频词 · D 低质红线')
    print('=' * 72)
    print()

    rows, bad = [], 0
    for p in files:
        lv, zq, dia, words, grams, low = audit(p, quiet=a.quiet)
        if lv != 'OK':
            bad += 1
        rows.append((lv, os.path.basename(p), zq[0] if zq else None,
                     dia[0][1] if dia else 0, low,
                     words[0][2] if words else 0.0,
                     words[0][0] if words else ''))

    print('=' * 72)
    print('风险汇总（按严重度）')
    print('=' * 72)
    order = {'HIGH': 0, 'WATCH': 1, 'OK': 2}
    for lv, nm, z, dt, low, hot, hw in sorted(
            rows, key=lambda r: (order[r[0]], -(r[2] or 0), -r[5])):
        zs = f'朱雀{z:>3}' if z is not None else '朱雀 --'
        hs = f'高频「{hw}」{hot:.1f}/千字' if hot >= 2 else '高频 —'
        print(f'  [{lv:>5}] {nm:<26} {zs}  对白模板{dt:>2}  {hs}  低质项{len(low)}')
    print()
    print(f'共 {len(files)} 章，需处理 {bad} 章。')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
