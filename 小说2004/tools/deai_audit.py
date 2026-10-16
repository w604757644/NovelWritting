#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《带着GPT重回高中》· 六步流水线第④步「去 AI 味」量化审计
=========================================================
对应 novel-workshop-pro/references/AI味硬禁止清单.md 第十一节 11 项自查。
本脚本只跑**可机器判定**的项；语义项（读出声、是否套路化）仍需人工。

本书体例是「一行一句」（一段≈一句），脚本对该体例做了适配：
  - F0 句法画像仍按「句」算（句＝以 。！？… 结尾的片段，含段内多句）
  - F8/F9 按「段」算，但本书一段＝一句，判据改为按段序列 judged

用法：
    python3 tools/deai_audit.py --dir 正文_新版 --range 1-5
    python3 tools/deai_audit.py --dir 正文_新版 --chapter 3 --verbose   # 列出命中原句
"""
import argparse
import os
import re
import statistics as st

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

# ---------------- 词表（来自 AI味硬禁止清单.md 第四/五/六节） ----------------
TONG_GAN = ["铁锈味", "铁锈", "血腥味", "腥甜", "甜腻", "黏腻", "冰凉", "滚烫",
            "湿冷", "阴冷", "霉味", "焦糊味", "土腥味"]
AI_ADV = ["骤然", "猛然", "旋即", "顿时", "愈发", "逐渐", "陡然", "径直", "始终",
          "极致", "缓缓", "慢慢", "轻轻", "淡淡", "幽幽", "静静", "默默", "微微",
          "狠狠", "死死"]
WEI_BIAO = ["呼吸一滞", "眸光一闪", "瞳孔骤缩", "心头一紧", "笑意凝固", "眼底闪过",
            "指尖微凉", "神色一凛", "心头一跳", "心头一震", "脸色一变", "心下一沉",
            "眸色一深", "嘴角一抽", "喉头一紧", "眼皮一跳"]
SENSE = list("凉冷热烫暖潮湿腥甜苦涩香臭麻硬软沉")
# F7 逗号节拍器用到的「一X」帧化尾
YI_X = re.compile(r'，一[^，。！？]{1,2}(?=[。！？])')

SENT_END = '。！？…'


def strip_meta(lines):
    """去掉标题行、粗体/斜体行、空行，返回正文段列表"""
    out = []
    for l in lines:
        s = l.strip()
        if not s:
            continue
        if s.startswith('#') or s.startswith('<!--'):
            continue
        # ★场景分隔符（2026-10-13 起正文用 `······` 替代 `## 一` 分节）
        #   它不是正文，必须排除，否则虚增段数、拉低段均长度。
        if re.match(r'^[·•]{4,}$', s):
            continue
        if (s.startswith('**') and s.endswith('**')) or (s.startswith('*') and s.endswith('*')):
            continue          # 章首/章尾金句、书名斜体
        out.append(s)
    return out


def is_dialog(s):
    return '"' in s or '"' in s or s.startswith('“')


def sentences(paras):
    """切句：按 。！？…（含叠用）切，保留末尾标点"""
    out = []
    for p in paras:
        parts = re.findall(r'[^。！？]*[。！？]+|[^。！？]+$', p)
        for x in parts:
            x = x.strip()
            if x:
                out.append(x)
    return out


def cnt(text, words):
    return sum(text.count(w) for w in words)


def f0_profile(sents):
    """句法画像：句均 / 句长CV / 长句(>=35字)占比"""
    lens = [len(re.findall(r'[\u4e00-\u9fff]', s)) for s in sents]
    lens = [x for x in lens if x > 0]
    if len(lens) < 2:
        return None
    avg = sum(lens) / len(lens)
    cv = st.pstdev(lens) / avg if avg else 0
    long_r = sum(1 for x in lens if x >= 35) / len(lens)
    return avg, cv, long_r, lens


def audit(ch_no, path, verbose=False):
    raw = open(path, encoding='utf-8').read()
    paras = strip_meta(raw.splitlines())
    sents = sentences(paras)
    issues, infos = [], []

    # 1 破折号
    # 注意：不能写成 raw.count('——') + raw.count('—')，
    # 因为 '——' 本身含两个 '—'，会重复计数（14 处被算成 42 处）。
    # 用正则匹配「一个或多个破折号」为一次出现。
    n_dash = len(re.findall(r'—+', raw))
    if n_dash:
        issues.append(f"[F1破折号] {n_dash} 处 ——")

    # 1b 直引号（老板硬口径）
    n_q = raw.count('"')
    if n_q:
        issues.append(f"[引号] 英文直引号 {n_q} 个（须为 0）")

    # 2 <=3字独立段 / 独立句（拟声与对白除外）
    short_paras = [p for p in paras if len(re.findall(r'[\u4e00-\u9fff]', p)) <= 3
                   and not is_dialog(p)]
    if short_paras:
        issues.append(f"[F2超短段] {len(short_paras)} 处：{short_paras[:4]}")

    # 3 感官字短句升华「是X的。」
    too_x = re.findall(r'是[^。！？]{1,3}的。', raw)
    sens_short = re.findall(
        r'(?:^|[。！？\n])([^。！？\n]{0,6}[凉冷冰热烫暖潮湿腥甜苦涩香臭麻硬软沉][^。！？\n]{0,6}。)',
        raw)
    # 过滤误报：正则的 [。！？\n] 边界会吃掉上一句残留的后引号/前引号
    # （如 “…辛苦你了。” 被切成 '”“辛苦你了。'），这类片段不含任何实质内容。
    import string as _s
    _punct = '“”‘’「」『』（）《》〈〉·—…、，。！？：；' + _s.punctuation
    sens_short = [x.strip() for x in sens_short
                  if len(re.findall(r'[\u4e00-\u9fff]', x)) > 0
                  and len(re.findall(r'[\u4e00-\u9fff]', x)) <= 4
                  and not x.strip().startswith(tuple(_punct))]
    if sens_short:
        issues.append(f"[F3感官短升] {len(sens_short)} 处：{sens_short[:4]}")

    # 4 通感词
    tg_hits = [(w, raw.count(w)) for w in TONG_GAN if raw.count(w)]
    if tg_hits:
        issues.append(f"[F4通感词] " + "、".join(f"{w}×{c}" for w, c in tg_hits))

    # 5 AI 高频副词（密度）
    cjk = len(re.findall(r'[\u4e00-\u9fff]', raw))
    adv_hits = [(w, raw.count(w)) for w in AI_ADV if raw.count(w)]
    adv_total = sum(c for _, c in adv_hits)
    adv_per_k = adv_total / (cjk / 1000)
    adv_txt = "（" + "、".join(f"{w}×{c}" for w, c in adv_hits) + "）" if adv_hits else ""
    infos.append(f"AI副词 {adv_per_k:.2f}/千字{adv_txt}")

    # 6 微表情四字独立成句
    wb = [(w, raw.count(w)) for w in WEI_BIAO if raw.count(w)]
    if wb:
        issues.append(f"[F6微表情] " + "、".join(f"{w}×{c}" for w, c in wb))

    # 7 逗号节拍器：一句内 >=3 个 <=4字分句
    beats = []
    for s in sents:
        # 对白句（含“”）里的「人名，某某说，短句」是正常对白格式，
        # 不是 F7 针对的「叙述动作被剁成等长小帧」，跳过以免误报。
        if is_dialog(s):
            continue
        frags = [f for f in re.split(r'[，、]', s) if f.strip()]
        if len(frags) >= 3:
            core = [len(re.findall(r'[\u4e00-\u9fff]', f.strip('。！？…'))) for f in frags]
            if sum(1 for x in core if 0 < x <= 4) >= 3:
                beats.append(s)
    yix = YI_X.findall(raw)
    if beats:
        issues.append(f"[F7逗号节拍] {len(beats)} 句" +
                      (f" → 例：{beats[0][:38]}" if not verbose else ""))
    if yix:
        issues.append(f"[F7一X帧化] {len(yix)} 处 {yix[:4]}")

    # 9 F0 句法画像（叙述故事类基线：句均42.3 / CV0.604 / 长句占比35.4%）
    prof = f0_profile(sents)
    if prof:
        avg, cv, long_r, lens = prof
        flag = ''
        if long_r > 0.80:
            flag = ' ★过度矫正'
        elif long_r < 0.15:
            flag = ' ★过碎'
        if avg < 20:
            flag += ' 句均偏低'
        infos.append(f"[F0] 句均{avg:.1f}｜CV{cv:.3f}｜长句占比{long_r:.1%}{flag}")

    # 10 F8 段落对称：连续3段字数差 <3（本书一段≈一句，判据按段长）
    lens_p = [len(re.findall(r'[\u4e00-\u9fff]', p)) for p in paras]
    sym_run, worst = 0, 0
    for i in range(len(lens_p) - 2):
        if abs(lens_p[i] - lens_p[i + 1]) < 3 and abs(lens_p[i + 1] - lens_p[i + 2]) < 3:
            sym_run += 1
            worst = max(worst, 3)
    if sym_run:
        infos.append(f"[F8] 连续3段等长(差<3字) {sym_run} 处 —— 一行一句体例需人工判断是否真同构")

    # 11 F9 升华矫正：连着3段都以「具体动作+句号」收尾
    ACT_TAIL = re.compile(r'[了着过完起下来去出上下进出回开来着去][。！？]$|'
                          r'(?:住|开|上|下|来|去|出|进|起)[。！？]$')
    act_run = 0
    for i in range(len(paras) - 2):
        if all(ACT_TAIL.search(p) for p in paras[i:i + 3]):
            act_run += 1
    if act_run:
        infos.append(f"[F9] 连续3段动作式收尾 {act_run} 处")

    return n_dash, n_q, len(paras), len(sents), issues, infos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='正文_新版')
    ap.add_argument('--chapter', type=int)
    ap.add_argument('--range')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()

    d = os.path.join(BASE_DIR, a.dir)
    files = []
    for f in os.listdir(d):
        m = re.match(r'第0?(\d+)章', f)
        if m and f.endswith('.md'):
            files.append((int(m.group(1)), f))
    files.sort()

    if a.chapter:
        files = [x for x in files if x[0] == a.chapter]
    elif a.range:
        lo, hi = [int(x) for x in a.range.split('-')]
        files = [x for x in files if lo <= x[0] <= hi]

    total = 0
    for no, fn in files:
        nd, nq, np_, ns, issues, infos = audit(no, os.path.join(d, fn), a.verbose)
        name = fn.rsplit('.', 1)[0]
        print(f"第{no}章 {name}  段{np_}｜句{ns}")
        for i in infos:
            print("   · " + i)
        for i in issues:
            print("   ✗ " + i)
        total += len(issues)
        print()

    print(f"── 共 {len(files)} 章，硬性问题 {total} 项 ──")


if __name__ == '__main__':
    main()
