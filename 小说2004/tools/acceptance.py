#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《带着GPT重回高中》· 写完后的六步验收（可量化部分一键跑）
=========================================================
★老板 2026-10-12「以后写作的第一原则」定案，顺序不得改：
    ① 风格对齐（writing-dna-skill 蒸馏《我真没想重生啊》）
          —— 检查写作风格、人物对话风格、人物描述风格是否对齐
    ② 名梗植入（net-meme-injection）
          —— 按本章内容挑合理的梗，每章 3—6 个；出口≤1，苦难场景不用
    ③ 爽点 / 吸引力 / 冲突（tomato-viral-novel 方法论 + 本书专属词库）
    ④ 去 AI 味（deai-promax）
    ⑤ 一致性（webnovel-review）
    ⑥ 字数 2200–4000（2026-10-12 放宽：超 3500 上限 500 字以内允许）
    ⑦ 易读性＋防剧透（2026-10-13 老板定案）：
        a. 上一世的人物结局**可以说**（既定事实、救人动机）；
        b. 这一世未发生的结果**不许提前说死**（"这回六十八"式报数）；
        c. 前瞻闪回句式"多年以后"一律不用，上一世回忆改用"上一世/上辈子"句式；
        d. 隔 21 年的题号级细节（"选择题第四题"）不许凭"上帝记忆"写，必须有来源
           （对方念叨过 / 强情绪事件）；
        e. 模板金句与复读比喻设配额（"带回来二十一年的记忆"每章≤1全书≤3、"心里那本账"每章≤1）。

本脚本只能量化 ①⑤⑥⑦（＋③的机械项）；②④内容判定、③的语义词仍需人工跑对应 skill。

用法：
    python3 tools/acceptance.py --chapter 101          # 单章
    python3 tools/acceptance.py --range 1-10           # 区间
    python3 tools/acceptance.py --all                  # 全书
    python3 tools/acceptance.py --range 1-10 --brief   # 只出不达标项

口径（与番茄闸门 viral_novel_audit.py 一致）：
    正文字数 = 中文字符 + 英文单词，不含标题行(#)、注释行(<!--)、空行。
    注意：柳岸花又明 200 章按此口径章均 2013 字 —— 不是 2463。
"""
import argparse
import os
import re
import statistics
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '正文')
CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                      '蒸馏_语料', '我真没想重生啊', 'raw200')
HOOK_LEDGER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                                'outlines', '章末钩子台账.md')


def load_hook_ledger():
    """读 outlines/章末钩子台账.md → {章号: 型号或'待判'}。文件不存在返回空表。"""
    out = {}
    if not os.path.exists(HOOK_LEDGER_PATH):
        return out
    for line in open(HOOK_LEDGER_PATH, encoding='utf-8'):
        m = re.match(r'^\|\s*(\d{1,3})\s*\|\s*([^|]+?)\s*\|', line)
        if not m:
            continue
        out[int(m.group(1))] = m.group(2).strip()
    return out


HOOK_LEDGER = load_hook_ledger()

CJK = re.compile(r'[\u4e00-\u9fff]')

# ---------------------------------------------------------------- 阈值
MIN_WORDS, MAX_WORDS = 2200, 4000          # ⑥ 字数（老板 2026-10-12 定案；上限由 3500 放宽至 4000）
# 单段字符数（含标点）。
# ★2026-10-13 由 60 上调至 70，依据柳书 raw200 实测行长分布：
#   P50=29 / P75=44 / P90=57 / P95=65 / P99=80 / MAX=129；>80 仅 0.93%。
#   原 60 上限会直接卡死「照抄柳书长句」这一口径（柳书 41—60 字区间占 21.3%），
#   故放宽至 70（≈柳书 P97），超过即判硬伤。
MAX_PARA_CHARS = 70

# ① 风格参考值（柳岸花又明 200 章，同一严格词表实测）
# ★★2026-10-15 重大修订：老板指出「别对齐数值，真正的作者不会一直对齐数据」。
#   这些数字**只作参考展示，不再当判定线**。风格数值一律降级为「极端预警」——
#   只在离谱时才报（如整章没有一个肢体动作），不要求每章卡到柳书均值。
#   理由：AI 味的本质＝**方差消失**（柳书句长标准差 3.8，我们只有 1.3）。
#   把每章摁到同一个数值，就是把书写成「统计平均物」，那正是机器味。
BASELINE = {
    'gesture_per_k': 3.29,   # 肢体情态/千字（参考，非判定线）
    'say_do': 6.4,           # 说 : 做（越低越好，柳 6.4:1）
    'para_avg': 33,          # 段落均长（字）
    'sent_avg': 33.1,        # 句均长（字）——★注：此前误记为「16—18」，实测口径 28.0／本表 33.1
}
# ── 极端预警线（只有跌破这些才算问题，不是要你对齐到柳书均值）──
WARN_GESTURE_PER_K = 1.2    # 原 2.5 太严（逼着为过检加动作）；低于 1.2＝整章几乎没动作
# ── 句长起伏（章内标准差）──
#   实测（raw200 前 120 章 vs 本书 30 章，同一口径）：
#     柳书 中位 17.7，波动 13.8–26.8
#     我们 中位  9.0，波动  6.5–11.0   ← 只有柳书一半；最好的一章(11.0)还不如柳书最差一章(13.8)
#   ★注意：这是「章内」起伏（一章之内句子长短交替），与「章间」均值波动是两回事。
LIU_STDEV_MED = 17.7        # 柳书章内句长标准差中位（方向，不是红线）
LIU_STDEV_MIN = 13.8        # 柳书最平的一章
WARN_SENT_STDEV = 8.0       # 低于此＝严重平（机器味明显），必改
# 角色锚点（出场章必须带）
# ★2026-10-13 修订：原词表只收了唯一一种写法（如「低头」），
#   导致正文里写了更自然的「低着头 / 低下头」却判 0 分，
#   逼着作者为了过检去改字 —— 这是尺子的问题，不是稿子的问题。
#   现按「同一动作的不同写法」补全，判定的是动作，不是字面。
ANCHORS = {
    '凯子/周凯': ['挠后脑勺', '挠着后脑勺', '挠了挠后脑勺', '挠了挠头',
                  '白牙', '指节粗', '指甲缝'],
    '陈冉': ['低头', '低着头', '低下头', '低了头',
             '把本子往他这边推', '圆珠笔', '虎牙', '倒刺'],
    # 程霜已于第 2 章入场（原「21 章」注释为旧时间线残留，已删），补第二锚点
    '程霜': ['沉默', '手指很长', '指尖干净', '没抬头'],
}

# ② 本书五型爆点（替代番茄的打脸流词库 —— 直接跑番茄会永远 0 分）
PAYOFF_BOOK = {
    '①信息差兑现': ['果然', '应验', '不出所料', '跟他说的一样', '他早知道',
                    '真让他猜着了', '一语成谶', '应了'],
    '②先知碾压': ['他记得', '前世', '二十三年后', '他早就知道', '那时候他还不知道',
                  '后来的事', '多年以后', '2027', '往后'],
    '③救人兑现': ['拦住', '拉住', '拽住', '别去', '还来得及', '挡在', '替他', '救'],
    '④第一笔钱': ['挣', '赚', '数钱', '票子', '钢镚', '毛票', '进账',
                  '到手', '攒够', '第一笔'],
    '⑤爽完接凉意': ['代价', '这笔账', '换命', '忘了', '记不住', '空了',
                    '静默写入', '回弹', '迟早要还'],
}
# 冲突信号（本书版：悬念/时间压力/家变，不是暴力）
CONFLICT_BOOK = ['倒计时', '还剩', '来不及', '要出事', '出事', '塌了', '下岗',
                 '买断', '改制', '病', '走散', '抓', '追', '输', '欠', '缺口',
                 '窟窿', '瞒不住', '不对劲', '变了', '死', '散了']
# 微钩子：沿用番茄完整 HOOK_SIGNALS（悬念/转折/揭示/标点），本书实测适配
HOOK_SIG = ['突然', '忽然', '却是', '竟', '竟然', '居然', '没想到', '难道',
            '为什么', '是谁', '不可能', '只见', '就在这时', '下一秒', '与此同时',
            '殊不知', '不知何时', '隐隐', '似乎', '仿佛', '原本', '第一次',
            '从未', '陌生', '未知', '阴影', '倒计时', '检测', '提示', '响起']

# ④ 一致性预检
BANNED_WORDS = []                           # 留空：按 story-dna 补
NAME_VARIANTS = {'李志明': ['李志明'], '陈冉': ['陈冉'], '周凯': ['周凯', '凯子'],
                 '程霜': ['程霜'], '郑佳怡': ['郑佳怡']}

# 最长匹配计数器：词表里存在「点头 ⊂ 点了点头」这类包含关系，
# 用 raw.count(短词) 会把一次出现算成两次。按长度降序做正则最长匹配即可去重。
def count_words(raw, words):
    pat = '|'.join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return len(re.findall(pat, raw)) if pat else 0


# ① 肢体情态词表（严格版，与柳岸花又明同源）
GESTURE = [
    "摇头", "点了点头", "点头", "低下头", "低头", "抬起头", "抬头", "扭头", "扭过头",
    "侧过头", "歪着头", "仰头", "挠了挠头", "挠头", "摸了摸头", "摸着头",
    "皱眉", "皱了皱眉", "挑眉", "眯着眼", "眯眼", "瞪了", "瞪着", "瞥了", "瞥了一眼",
    "瞄了", "扫了一眼", "盯着", "抿嘴", "抿着嘴", "撇嘴", "咧嘴", "张了张嘴",
    "咬着嘴唇", "咬嘴唇", "嘴角", "脸一红", "脸红", "涨红", "耳根",
    "攥紧", "攥着", "攥了", "搓了搓", "搓手", "捏了捏", "掐了", "握住", "握紧",
    "拍了拍", "拍拍", "摸了摸", "挠了挠", "掰着", "抠着", "戳了", "指了指", "摆手",
    "摆了摆手", "招手", "挥了挥", "伸出手", "伸手", "耸肩", "肩膀", "前倾", "后仰",
    "侧身", "侧过身", "转身", "倚着", "靠着", "蹲下", "蹲着", "弓着", "挺直",
    "缩了缩", "缩着", "抖了一下", "抖了抖", "颤了一下", "一怔", "怔了", "怔住",
    "愣了一下", "愣住", "咳了一声", "清了清嗓子", "喉结", "咽了口", "踮脚", "踮着",
    "踢了", "退了半步", "往后退", "迈步", "跨",
]
SAY = ["说", "道", "问", "答", "喊", "叫", "骂", "嘀咕", "嘟囔",
       "补了一句", "接话", "开口", "应了一声", "念叨", "接了句"]


# ---------------------------------------------------------------- 工具
def cw(t):
    """正文字数 = 中文字符 + 英文单词（与番茄闸门同口径）"""
    return len(CJK.findall(t)) + len(re.findall(r'[A-Za-z]+', t))


def body_of(path):
    raw = open(path, encoding='utf-8').read()
    lines = [l for l in raw.splitlines()
             if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('<!--')]
    return raw, "\n".join(lines), lines


def ch_files():
    out = []
    for f in os.listdir(BASE):
        m = re.match(r'第0?(\d+)章', f)
        if m and f.endswith('.md'):
            out.append((int(m.group(1)), f))
    return sorted(out)


# ---------------------------------------------------------------- 五步
def check(ch_no, fname, brief=False):
    raw, body, lines = body_of(os.path.join(BASE, fname))
    words = cw(body)
    issues, infos = [], []

    # ⑥ 字数
    if not (MIN_WORDS <= words <= MAX_WORDS):
        issues.append(f"[⑥字数] {words} 不在 {MIN_WORDS}-{MAX_WORDS}"
                      + (f"，需补 {MIN_WORDS - words}" if words < MIN_WORDS
                         else f"，需压 {words - MAX_WORDS}"))

    longest = max((len(l.strip()) for l in lines), default=0)
    if longest > MAX_PARA_CHARS:
        issues.append(f"[⑤段落] 最长 {longest} 字符 > {MAX_PARA_CHARS}")

    # ① 风格对齐
    g = count_words(raw, GESTURE)
    s = count_words(raw, SAY)
    gpk = g / (words / 1000)
    ratio = s / max(g, 1)
    infos.append(f"肢体 {gpk:.2f}/千字（柳参考 {BASELINE['gesture_per_k']}）｜说:做 {ratio:.1f}:1（柳 {BASELINE['say_do']}:1）")
    # ★2026-10-15：风格数值降为「极端预警」，不要求对齐柳书均值
    if gpk < WARN_GESTURE_PER_K:
        issues.append(f"[①风格] 肢体情态 {gpk:.2f} < {WARN_GESTURE_PER_K}/千字（整章几乎没动作）")
    if ratio > BASELINE['say_do']:
        issues.append(f"[①风格] 说:做 {ratio:.1f}:1 高于柳书 {BASELINE['say_do']}:1（人物在干说）")

    # ★句长起伏（2026-10-15 新增）：AI 味的本质＝方差消失。
    #   柳书句长标准差 3.8（21—42 字混着来），我们只有 1.3（每句都 13 字左右）。
    seglen = [len(CJK.findall(s)) for s in re.split(r'[。！？…]+', body)]
    seglen = [n for n in seglen if n > 0]
    if len(seglen) >= 20:
        sd = statistics.pstdev(seglen)
        shortest = min(seglen)
        n_short = sum(1 for n in seglen if n <= 5)
        infos.append(f"句长起伏 sd {sd:.1f}（柳中位 {LIU_STDEV_MED}／柳最平 {LIU_STDEV_MIN}）"
                     f"｜最短句 {shortest} 字｜≤5 字短句 {n_short} 处")
        if sd < WARN_SENT_STDEV:
            issues.append(
                f"[①起伏] 句长起伏 sd {sd:.1f} < {WARN_SENT_STDEV}——每句几乎一样长＝机器味"
                f"｜补法：长句后跟一个 3—5 字短句（柳中位 {LIU_STDEV_MED}）")
        elif sd < LIU_STDEV_MIN:
            infos.append(f"起伏偏低（柳书最平的一章也有 {LIU_STDEV_MIN}），朝 {LIU_STDEV_MED} 靠")
        if n_short == 0:
            issues.append(f"[①起伏] 全章无 ≤5 字短句（柳书长短交替）")

    # 角色锚点（只对「正式出场」生效：提及 1-2 次不算，避免误报）
    MIN_APPEAR = 3
    for role, keys in ANCHORS.items():
        appear = raw.count('周凯') + raw.count('凯子') if role == '凯子/周凯' \
            else sum(raw.count(n) for n in NAME_VARIANTS.get(role, [role]))
        if appear < MIN_APPEAR:
            continue
        hit = sum(raw.count(k) for k in keys)
        rate = hit / appear
        if hit == 0:
            issues.append(f"[①锚点] {role} 出场 {appear} 次，锚点「{keys[0]}」0 次复现")
        elif rate < 0.2:
            issues.append(f"[①锚点] {role} 锚点复现率 {rate:.0%} < 20%（出场 {appear}／锚点 {hit}）")

    # ② 爽点 / 冲突
    pay_hits = {k: sum(raw.count(w) for w in ws) for k, ws in PAYOFF_BOOK.items()}
    pay_total = sum(pay_hits.values())
    pay_density = pay_total / (words / 3000)
    infos.append("爆点 " + "｜".join(f"{k}{v}" for k, v in pay_hits.items())
                 + f"｜密度 {pay_density:.1f}/3000字")
    if pay_density < 1:
        issues.append(f"[②爽点] 五型爆点密度 {pay_density:.1f} < 1（每 3000 字至少 1 处）")
    types_hit = sum(1 for v in pay_hits.values() if v > 0)
    if types_hit < 2:
        issues.append(f"[②爽点] 五型只命中 {types_hit} 型，建议 ≥2 型搭配")

    conf = sum(raw.count(w) for w in CONFLICT_BOOK)
    if conf == 0:
        issues.append("[②冲突] 全章 0 处冲突信号")
    # 微钩子：词信号 + 标点信号（本书「一行一句」格式，？…—— ！ 是主要贡献）
    hooks = sum(raw.count(w) for w in HOOK_SIG)
    hooks += raw.count('？') + raw.count('！') + raw.count('……') + raw.count('——')
    hook_density = hooks / (words / 500)
    if hook_density < 1:
        issues.append(f"[②微钩] 每500字 {hook_density:.1f} < 1")

    # ★2026-10-12 改：章末钩子不再读正文注释（已从全部正文删除），改读独立台账
    #   outlines/章末钩子台账.md。正文只留内容，管理信息住台账。
    hk = HOOK_LEDGER.get(ch_no)
    if hk is None:
        infos.append("章末钩子 台账缺第%02d章" % ch_no)
    elif hk == '待判':
        infos.append("章末钩子 待判（章末句已入台账）")
    else:
        infos.append("章末钩子 " + hk)

    # ③ 去 AI 味（预检，模型判为主）
    # 注意：不收「最后」「与此同时」——本书里多为实义用法（"最后一声""最后那把火"），误杀严重
    ai_hits = []
    for w in ['首先', '其次', '再次', '总而言之', '综上所述', '值得注意的是',
              '不难看出', '总的来说', '在这个过程中', '无一例外', '值得一提的是',
              '由此可见', '换句话说', '换言之']:
        c = raw.count(w)
        if c:
            ai_hits.append(f"{w}×{c}")
    if ai_hits:
        issues.append(f"[③AI味] 模板连接词 {'、'.join(ai_hits)}，交 deai-promax 处理")

    # ④ 一致性预检
    title_no = int(re.match(r'第0?(\d+)章', fname).group(1))
    if title_no != ch_no:
        issues.append(f"[④一致] 章号错位：文件名 {title_no} vs 序号 {ch_no}")
    for bw in BANNED_WORDS:
        if bw in raw:
            issues.append(f"[④一致] 禁用词命中：{bw}")
    # 引号：只查「孤儿闭引号」——即 depth==0 时遇到 ”
    # （多段连续引语合法写法：每段开前引号、只末段收后引号，配对法会误报，不能用）
    depth = 0
    orphans = []
    for ln, line in enumerate(raw.splitlines(), 1):
        for ch in line:
            if ch == '“':
                depth += 1
            elif ch == '”':
                if depth == 0:
                    orphans.append(ln)
                else:
                    depth -= 1
    if orphans:
        issues.append(f"[④一致] 孤儿闭引号 {len(orphans)} 处，行号 {orphans[:6]}")
    # 破折号：★D1 定案「全书清零」，比番茄口径（密度≤2.38/千字）严得多。
    # 2026-10-15 实测：tomato_precheck 只卡密度，第 29 章 1 处破折号被它放过，
    # 靠新引入的活人感尺子才抓到——所以这条必须补在这里（内部纪律，不是番茄口径）。
    n_dash = raw.count('——') + raw.count('–')
    if n_dash:
        ln = [i for i, l in enumerate(raw.splitlines(), 1) if '——' in l or '–' in l]
        issues.append(f"[④一致] 破折号 {n_dash} 处（D1 全书清零），行号 {ln[:6]}"
                      f"　→ 对白迟疑/被打断改省略号（D8：省略号保留）")

    # ⑦ 易读性＋防剧透（2026-10-13 老板定案，流程第七条）
    #   口径：①上一世的人物结局**可以说**（既定事实、救人动机）；
    #         ②这一世未发生的结果**不许提前说死**（"这回六十八"式报数）；
    #         ③前瞻闪回句式"多年以后"一律不用——上一世回忆改用"上一世/上辈子"句式；
    #         ④模板金句与复读比喻设配额（故作高深＝AI味）。
    rd = []
    if re.search(r'多[许很]?年以[后来]', raw):
        rd.append('前瞻闪回“多年以后”（上一世回忆请改“上一世/上辈子”句式）')
    if re.search(r'他记得[这那次][^，。\n]{0,8}结果', raw):
        rd.append('结果剧透“他记得…结果”')
    if re.search(r'这回[会考]?[一二三四五六七八九十百零\d]+', raw):
        rd.append('这一世预言报数（“这回X”，数字留给兑现时刻）')
    n_dna = raw.count('带回来二十一年的记忆')
    if n_dna > 1:
        rd.append(f'对仗金句模板×{n_dna}（每章≤1，全书≤3）')
    n_zhang = raw.count('心里那本账')
    if n_zhang > 1:
        rd.append(f'“心里那本账”×{n_zhang}（每章≤1）')
    if rd:
        issues.append("[⑦易读] " + "；".join(dict.fromkeys(rd)))
    else:
        infos.append("⑦易读 无前瞻闪回/报数剧透/模板超标")

    # 输出
    head = f"第{ch_no}章 {fname[:-3]}  {words}字"
    if brief:
        if issues:
            print(head)
            for i in issues:
                print("   x " + i)
    else:
        print(head)
        for i in infos:
            print("   · " + i)
        if issues:
            for i in issues:
                print("   x " + i)
        else:
            print("   ✓ 五步全过")
    return len(issues)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapter', type=int)
    ap.add_argument('--range', help='如 1-10')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--brief', action='store_true', help='只出不达标项')
    ap.add_argument('--dir', help='章节目录名（默认“正文”；重构期用“正文_新版”）')
    a = ap.parse_args()

    global BASE, HOOK_LEDGER, HOOK_LEDGER_PATH
    if a.dir:
        BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', a.dir)
        if not os.path.isdir(BASE):
            print(f"目录不存在：{BASE}")
            return 1
        # 台账跟随目录，避免新版与旧版 1—130 撞行
        HOOK_LEDGER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                                        'outlines', f'{a.dir}_章末钩子台账.md')
        # ★2026-10-15 修：现行稿就是 正文_重写版/，但台账文件名没带目录前缀，
        #   专用台账不存在时若不回落，会把「已有型号」误报成「台账缺章」。
        if not os.path.exists(HOOK_LEDGER_PATH):
            HOOK_LEDGER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                                            'outlines', '章末钩子台账.md')
        HOOK_LEDGER = load_hook_ledger()

    files = ch_files()
    if a.chapter:
        files = [x for x in files if x[0] == a.chapter]
    elif a.range:
        lo, hi = map(int, a.range.split('-'))
        files = [x for x in files if lo <= x[0] <= hi]

    total = 0
    for n, f in files:
        total += check(n, f, a.brief)
    print(f"\n── 共 {len(files)} 章，问题 {total} 项 ──")
    return 0


if __name__ == '__main__':
    sys.exit(main())
