#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爽点结构探测器（本书专用，替代 acceptance.py 里的「爆点密度」）

── 为什么不用「爆点密度」 ──
原指标统计的是「他记得 / 前世 / 多年以后 / 2027」这类**重生设定说明词**的出现次数。
第 1 章密度 23.4，是因为开篇在交代设定；第 2—5 章掉到 4—5，是**设定交代完了**，不是爽度掉了。
追这个数 ⇒ 每章塞一堆"他记得/前世" ⇒ 正好是我们刚清掉的复读机式 AI 腔。
★该指标只能用于「设定交代是否过量」。

── 本书爽点公式 ──
不是「我比你们强」（碾压型），是「**我算准了你们会错在哪儿**」（精准型）。
理由：换命守恒要求"多拿的都要还"。碾压型爽点会和守恒打架——读者会问"代价呢"。
精准型里他**没有多拿一分**，只是把分送到了该去的地方，账落在别人头上。

── 闭环四步 ──
① 埋判断（未来的断言）→ ② 兑现（后文证实）→ ③ 见证（第二人物看见）→ ④ 代价（章内落凉意）

★两处刻意放宽（2026-10-13 修订，别再收紧）：
  · 埋点**不强制含数字** —— 本书大量预判是行为路径（"她要举手了"），不是数值。
  · 代价**只看章内** —— 本书结构是「爽在中段、凉在章末」，天然相距几十段。

── 用法 ──
    python3 tools/payoff_scan.py --dir 正文_新版 --range 1-5
    python3 tools/payoff_scan.py --dir 正文_新版 --range 4-4 --verbose
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NAMES_PATH = os.path.join(HERE, 'names.txt')

CJK = re.compile(r'[\u4e00-\u9fff]')
NUM = re.compile(r'[0-9零一二三四五六七八九十百千两]+')

# ① 埋判断：对未来的断言（数值型 + 行为型都算，不强制数字）
FORECAST = [
    r'你会[^。！？]{0,12}',
    r'他要[^。！？]{0,12}',
    r'这回[会能要][^。！？]{0,10}',
    r'不出(?:所料|三天|意外|一个月|一周)',
    r'我猜[^。！？]{0,12}',
    r'我算[^。！？]{0,12}',
    r'能考[到得]?[^。！？]{0,8}',
    r'排在第?[0-9零一二三四五六七八九十百千两]{1,4}',
    r'追[0-9零一二三四五六七八九十百千两]{1,4}分',
    r'才会[^。！？]{0,10}',
]

# ①b 诊断型断言：不预言未来，而是断言「病根在哪儿」。
# ★本书主力爽点形态：李志明常说「不是笨，是断链」「根都在初二」——
#   这类断言同样会在后文被「当场演示」兑现（凯子真的在初二那一步接上了），
#   但 FORECAST 的「你会/他要/我猜」全部抓不到，导致系统性漏判。
#   （2026-10-13 写第 6 章时首次暴露：埋点 3 处，配对 0。）
DIAGNOSE = [
    r'根[^。！？]{0,4}在[^。！？]{0,10}',
    r'卡在[^。！？]{0,10}',
    r'断在[^。！？]{0,10}',
    r'断链',
    r'不是[^。！？]{0,4}是[^。！？]{0,12}',
    r'从来不是[^。！？]{0,12}',
    r'难的从来不是[^。！？]{0,12}',
]

# ② 兑现：断言被证实的信号
REDEEM = [
    r'果然', r'果不其然', r'真是', r'真就', r'应了',
    r'跟[^。！？]{0,4}说的一样', r'让他猜着', r'说中了',
    r'一字不差', r'一语成谶',
]

# ④ 代价：爽完接凉意
COST = [
    r'代价', r'这笔账', r'换命', r'忘了', r'记不住', r'说不上来',
    r'空了', r'静默写入', r'回弹', r'迟早要还', r'挪', r'还不起',
    r'想不起来', r'凉',
]


def load_names():
    if not os.path.exists(NAMES_PATH):
        return []
    return [l.strip() for l in open(NAMES_PATH, encoding='utf-8') if l.strip()]


def strip_meta(lines):
    """只去掉标题与分隔线，保留正文段。

    ★关键：不过滤「独立成行的加粗金句」。
      本书的预判（「一个要答题的人，才会先摘笔帽」）与代价
      （「这笔账…已经在欠了」）大量写在金句行里；
      若按 deai_audit 的口径一并过滤，探测器会系统性地漏掉所有闭环。
      （第 4 章第一次跑就踩过这个坑，当时只绕过去了，现在从根上修。）
    """
    out = []
    for l in lines:
        s = l.strip()
        if not s or s.startswith('#') or s.startswith('---'):
            continue
        # ★场景分隔符（2026-10-13 起正文用 `······` 替代 `## 一` 分节）
        #   它不是正文，必须排除，否则会虚增段数、拉低段均长度。
        if re.match(r'^[·•]{4,}$', s):
            continue
        out.append(s)
    return out


def is_dialog(s):
    return '\u201c' in s or '\u201d' in s


def scan(path, names, verbose=False):
    raw = open(path, encoding='utf-8').read()
    paras = strip_meta(raw.splitlines())
    others = [n for n in names if n != '李志明']

    # 兑现信号所在段
    rede = [i for i, p in enumerate(paras)
            if any(re.search(r, p) for r in REDEEM)]
    F_ALL = FORECAST + DIAGNOSE
    all_fore = [i for i, p in enumerate(paras)
                if any(re.search(f, p) for f in F_ALL)]

    # 埋点配对：兑现信号之前、80 段窗口内、最靠近的一次断言即为它的埋点。
    # ★窗口取 80 而不是 3：本书是「一段一句」的白描体，一章 250—350 段，
    #   「埋在中段、兑在后段」天然相距 60—70 段（第 6 章实测 66 段）。
    #   按 80 计算：一章内几乎任何「先埋后兑」都能配上，而跨章仍配不上。
    paired = []
    for r in rede:
        hit = [f for f in all_fore if f < r and r - f <= 80]
        if hit:
            paired.append((hit[-1], r))

    used = {f for f, _ in paired}
    dangling = [i for i in all_fore if i not in used]

    # ③ 见证：兑现段前后 2 段内出现第二人物
    witnessed = 0
    for f, r in paired:
        nb = paras[max(0, r - 2): r + 3]
        if any(o in x for x in nb for o in others):
            witnessed += 1

    # ④ 代价：章内出现（不限制距离）
    has_cost = any(any(re.search(c, x) for c in COST) for x in paras)
    costed = len(paired) if has_cost else 0

    cjk = len(CJK.findall(raw))
    per3k = len(paired) / (cjk / 3000) if cjk else 0

    return {
        'paras': len(paras),
        'fore': len(all_fore),
        'redeem': len(rede),
        'paired': len(paired),
        'witness': witnessed,
        'cost': costed,
        'dangling': dangling,
        'per3k': per3k,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='正文_新版')
    ap.add_argument('--range', default='1-5')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    a, b = (int(x) for x in args.range.split('-'))
    names = load_names()

    files = []
    for f in sorted(os.listdir(args.dir)):
        m = re.match(r'第(\d+)章', f)
        if m and a <= int(m.group(1)) <= b and f.endswith('.md'):
            files.append((int(m.group(1)), os.path.join(args.dir, f)))
    if not files:
        print('未找到章节文件')
        return 1

    print('=' * 78)
    print('爽点结构探测 · 闭环四步：①埋判断 → ②兑现 → ③见证 → ④代价')
    print('=' * 78)
    print(f"{'章节':<22}{'埋点':>5}{'兑现':>6}{'闭环':>6}{'见证':>6}{'代价':>6}{'/3000字':>8}")
    print('-' * 78)

    tot = dict(fore=0, redeem=0, paired=0, witness=0, cost=0, dang=0)
    for ch, p in files:
        r = scan(p, names, args.verbose)
        for k in ('fore', 'redeem', 'paired', 'witness', 'cost'):
            tot[k] += r[k]
        tot['dang'] += len(r['dangling'])
        flag = '' if r['paired'] else '  <-- 无闭环'
        print(f"{os.path.basename(p)[:20]:<22}{r['fore']:>5}{r['redeem']:>6}"
              f"{r['paired']:>6}{r['witness']:>6}{r['cost']:>6}{r['per3k']:>8.1f}{flag}")

    print('-' * 78)
    print(f"合计：埋点 {tot['fore']}｜兑现 {tot['redeem']}｜完整闭环 {tot['paired']}"
          f"｜见证 {tot['witness']}｜代价提示 {tot['cost']}")
    print(f"悬空埋点（埋了没兑现）：{tot['dang']} 处")
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
