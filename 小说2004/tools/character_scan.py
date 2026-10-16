#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人物戏份尺子（2026-10-15 老板 Q1 拍板立，第八把尺子）
=========================================================
老板原话：「做。而且别忘了你蒸馏出来的内容，每次写之前都要看一下，
能不能借用柳书和《大涅槃》写作手法来丰富内容。」

★为什么需要它：
  实测《大涅槃》唐妩 —— POV 段 206、旁人议论专段 37+、主场章 30%（约每 3 章一场）。
  我们前 30 章陈冉 —— POV 段 0、旁人议论 0 章、高光戏 0。
  **七把尺子一条都没报**，全靠老板审稿才发现。原因：人物戏份从来不在流水线里。

量四件事（照唐妩三板斧）：
  ① 出场次数        —— 这章有没有这个人
  ② POV 段         —— 段首是她＋心理词＝她的视角小节（女主每 3—5 章 ≥1）
  ③ 旁人议论段      —— 她出现在没有主角的段落里，且带"说/听说/议论/打听"
                       （光环靠别人的嘴，不靠自己写）
  ④ 高光场次        —— 她＋"全班/当着/底下/一片/都愣/看愣"（当众的戏）

用法：
  python3 tools/character_scan.py --range 1-10
  python3 tools/character_scan.py --range 1-10 --who 陈冉 --info
  python3 tools/character_scan.py --range 1-30 --brief

判法：批汇总里的"报警"是提示不是圣旨——0 出场章按铁律不硬塞，别为了过尺子加戏。
"""
import argparse
import glob
import os
import re

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

PSY = ('想', '觉得', '知道', '明白', '心里', '记得', '发现', '清楚', '算了', '怕', '看出')
TALK = ('说', '听说', '议论', '传', '打听', '八卦', '嘀咕', '喊', '念叨', '闲话', '风声',
        '传开', '消息', '议论', '背后', '嘴', '聊', '问')
HL = ('全班', '当着', '底下', '一片', '都看', '都愣', '看愣', '哄', '掌声', '有人喊',
      '齐刷刷', '盯着', '围', '回头看', '放慢脚步')
# 代词接力（议论块里第二句起通常不再点名）
REF = ('她', '这姑娘', '这丫头', '这女生', '那姑娘', '这女的', '人家')
QUOTE = re.compile(r'[“"](.+?)[”"]', re.S)


def load_chapters(dirname, rng):
    pat = os.path.join(BASE, dirname, '第*.md')
    files = []
    for f in glob.glob(pat):
        m = re.search(r'第(\d+)章', os.path.basename(f))
        if not m:
            continue
        n = int(m.group(1))
        if rng and not (rng[0] <= n <= rng[1]):
            continue
        files.append((n, f))
    return sorted(files)


def scan(text, who, main='李志明'):
    """段级扫描。★2026-10-15 修判定（第 10 章实测：加了一整块旁人议论，尺子报 0）：
    原判定要求「段内必须出现人名 ＋ 段内必须有说/问/议论」，太窄——
    真实的议论块是「一句点名 ＋ 后面几句是'她''这姑娘'的代词接力」，一段都带名字反而不像人话。
    修正两条：① 引号对白＝有人在说话，不必再找"说/问"字；
             ② 名字出现后 2 段内、用「她/这姑娘」接力的对白段，算同一场议论。"""
    cnt = text.count(who)
    pov = talk = hl = 0
    paras = [p.strip() for p in re.split(r'\n+', text)]
    last_who, last_pov = -9, -9
    for i, p in enumerate(paras):
        if len(p) < 8:
            continue
        has_who = who in p
        if has_who:
            last_who = i
            # ★2026-10-15 修：POV 是"块"不是"段"。真实 POV＝「段首点名领起 ＋ 后面几段接力」，
            #   不可能每段都以名字开头（那样反而不像中文）。原判定要求同段内必须有心理词，
            #   第 3 章加了一整节 POV 仍判 0。改为：段首点名 ＋ 其后 2 段内出现心理词＝1 个 POV。
            if p.startswith(who):
                window = ' '.join(paras[i:i + 3])
                if any(w in window for w in PSY) and (i - last_pov) > 3:
                    pov += 1
                    last_pov = i
            if any(w in p for w in HL):
                hl += 1
        # 议论：主角不在场 ＋（点到名字 或 紧接名字后 2 段内的代词接力）＋（对白 或 议论动词）
        near = (i - last_who) <= 2
        pronoun = any(w in p for w in REF) or has_who
        spoken = bool(QUOTE.search(p)) or any(w in p for w in TALK)
        if main not in p and has_who and spoken:
            talk += 1
        elif main not in p and near and pronoun and spoken and not has_who:
            talk += 1
        elif main not in p and has_who and any(w in p for w in HL):
            hl += 1
    return cnt, pov, talk, hl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='正文_重写版')
    ap.add_argument('--range', default='1-30')
    ap.add_argument('--who', default='陈冉')
    ap.add_argument('--main', default='李志明', help='主角名，用来判断"她不在主角视角里"的独立段')
    ap.add_argument('--brief', action='store_true')
    ap.add_argument('--info', action='store_true')
    a = ap.parse_args()

    rng = None
    m = re.match(r'(\d+)-(\d+)$', a.range)
    if m:
        rng = (int(m.group(1)), int(m.group(2)))
    files = load_chapters(a.dir, rng)
    if not files:
        print('没有匹配的章节')
        return

    rows = []
    for n, f in files:
        text = open(f, encoding='utf-8').read()
        rows.append((n, os.path.basename(f)) + scan(text, a.who, a.main))

    n_ch = len(rows)
    zero = [r[0] for r in rows if r[2] == 0]
    pov_ch = [r[0] for r in rows if r[3] > 0]
    talk_ch = [r[0] for r in rows if r[4] > 0]
    hl_ch = [r[0] for r in rows if r[5] > 0]
    need_pov = max(1, n_ch // 5)

    print(f'人物戏份尺子 · {a.dir}（{n_ch} 章，主角={a.main}）· 目标人物：{a.who}')
    print('────────────────────────────────────────────────────────────')
    if a.info or not a.brief:
        print('  章 | 出场 | POV | 议论 | 高光')
        for n, fn, c, p, t, h in rows:
            print(f'  {n:>3} | {c:>4} | {p:>3} | {t:>4} | {h:>4}   {fn}')
        print('────────────────────────────────────────────────────────────')

    warn, info = [], []
    # ★POV／高光是"批级"指标（每 3—5 章一个），只跑 1 章时必然报 —— 降级为 INFO，别污染单章结论
    batch = n_ch >= 5
    if len(pov_ch) < need_pov:
        msg = (f'POV 小节不足：批内 {len(pov_ch)} 个，建议 ≥{need_pov}（每 3—5 章一个）'
               f'｜现有：{pov_ch or "无"}')
        (warn if batch else info).append(msg)
    if not talk_ch:
        warn.append('旁人议论为 0：她的光环全靠自己写，没有别人的嘴（唐妩 37 段/主场章 30%）')
    elif len(talk_ch) < max(1, n_ch // 4):
        warn.append(f'旁人议论偏少：{len(talk_ch)}/{n_ch} 章｜有议论的章：{talk_ch}')
    if not hl_ch:
        msg = '无高光场次：她没有一场"当众"的戏（全班/底下/都愣）'
        (warn if batch else info).append(msg)

    for w in info:
        print(f'   · INFO（批级指标，本章不判）{w}')
    if warn:
        for w in warn:
            print(f'   ! {w}')
    else:
        print(f'   ✓ 人物戏份达标（POV {len(pov_ch)}／议论 {len(talk_ch)} 章／高光 {len(hl_ch)} 章）')

    print(f'   INFO {len(zero)} 章 0 出场：{zero}（0 出场章按铁律不硬塞，别为过尺子加戏）')


if __name__ == '__main__':
    main()
