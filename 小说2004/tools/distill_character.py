#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
柳书人物手法 / 对话幽默性 采样器
只挖「质感实例」，不算数值。输出落盘后人工读。
用法:
  python3 tools/distill_character.py --out /tmp/liu_char.txt
  python3 tools/distill_character.py --cat F --top 30
"""
import os, re, sys, glob, argparse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "蒸馏_语料", "我真没想重生啊", "raw200")

# 八类：A-D 人物丰满度，E-H 对话幽默性
CATS = {
    "A_嘴硬言行不一": [
        r"嘴上[^。！？\n]{0,20}", r"嘴硬", r"说[^。！？\n]{0,8}其实",
        r"嘴上说着[^。！？\n]{0,20}", r"一边说[^。！？\n]{0,20}一边",
        r"说是[^。！？\n]{0,15}，[却还]",
    ],
    "B_撒谎遮掩": [
        r"撒谎", r"骗[^。！？\n]{0,8}", r"隐瞒", r"敷衍", r"搪塞",
        r"装作[^。！？\n]{0,12}", r"假装[^。！？\n]{0,12}", r"糊弄",
    ],
    "C_退让认怂": [
        r"认怂", r"服软", r"退让", r"让步", r"低[^。！？\n]{0,6}头[^。！？\n]{0,8}",
        r"不敢[^。！？\n]{0,10}", r"妥协", r"忍[^。！？\n]{0,10}",
    ],
    "D_重复犯错": [
        r"又[^。！？\n]{0,10}(忘|犯|错)", r"每次都", r"还是老样子",
        r"第[^。！？\n]{0,3}次[^。！？\n]{0,10}", r"又来了",
        r"老毛病", r"重蹈",
    ],
    "E_擅长解决": [
        r"办法[^。！？\n]{0,15}", r"主意[^。！？\n]{0,15}", r"一下就[^。！？\n]{0,12}",
        r"三下五除二", r"轻而易举", r"搞定", r"摆平", r"解决了",
    ],
    "F_损友冒犯": [
        r"损[^。！？\n]{0,8}", r"滚蛋", r"去你的", r"你大爷", r"傻[逼B]",
        r"有病", r"不要脸", r"贱[^。！？\n]{0,6}", r"狗东西", r"狗腿子",
    ],
    "G_主角毒舌": [
        r"陈汉升[^。！？\n]{0,6}(笑|说|道)[^。！？\n]{0,40}",
        r"陈汉升[^。！？\n]{0,10}(撇|冷笑|摇头|淡淡)",
    ],
    "H_群像笑场": [
        r"哄堂大笑", r"哄笑", r"笑成一团", r"都笑了", r"全场[^。！？\n]{0,6}笑",
        r"忍俊不禁", r"噗[^。！？\n]{0,4}笑", r"笑喷", r"笑得[^。！？\n]{0,10}",
    ],
    # === 以下四类 2026-10-15 补：暧昧 / 喜欢 / 身体接触 / 女主心理 ===
    "I_暧昧好感": [
        r"脸[^。！？\n]{0,4}(红|热|烫)", r"耳根[^。！？\n]{0,8}", r"心跳[^。！？\n]{0,8}",
        r"偷偷[^。！？\n]{0,6}看", r"瞄了[^。！？\n]{0,6}", r"多看了[^。！？\n]{0,6}",
        r"不太好意思", r"不好意思[^。！？\n]{0,10}", r"害羞", r"心跳加速",
        r"有点[^\n。！？]{0,4}喜欢", r"喜欢上[^。！？\n]{0,8}", r"心动",
    ],
    "J_身体接触": [
        r"(拉|牵|拽|攥|握)住[^。！？\n]{0,4}(她|他)[^。！？\n]{0,6}手",
        r"[她他][^。！？\n]{0,6}(的手|手背|手腕)",
        r"(搂|揽|抱)住[^。！？\n]{0,8}", r"靠在[^。！？\n]{0,6}(肩|身上|怀里)",
        r"(摸|揉|拍|碰)了[^。！？\n]{0,2}(一下|下)[^。！？\n]{0,6}(头|脸|手|肩)",
        r"头发[^。！？\n]{0,10}", r"(凑|凑近|靠近)了[^。！？\n]{0,6}",
        r"闻到[^。！？\n]{0,8}", r"气息[^。！？\n]{0,8}",
    ],
    "K_女主心理": [
        r"(萧容鱼|小鱼|陈岚|黄婷|王思楠)[^。！？\n]{0,4}(心里|心中|心想|暗想)",
        r"(萧容鱼|小鱼|陈岚|黄婷|王思楠)[^。！？\n]{0,6}(觉得|想着|寻思|琢磨)",
        r"(萧容鱼|小鱼|陈岚)[^。！？\n]{0,4}(想|觉得)[^。！？\n]{0,20}",
        r"她[^。！？\n]{0,2}心里[^。！？\n]{0,24}",
        r"她[^。！？\n]{0,2}心想[^。！？\n]{0,24}",
    ],
    "L_吃醋较劲": [
        r"吃醋", r"酸[^\n。！？]{0,6}", r"醋意", r"心里不是滋味",
        r"凭什么[^。！？\n]{0,12}", r"凭啥[^。！？\n]{0,12}",
        r"不高兴[^。！？\n]{0,10}", r"生气[^。！？\n]{0,10}",
    ],
}


def load_chapters(limit=120):
    files = sorted(glob.glob(os.path.join(RAW, "*.md")))[:limit]
    out = []
    for f in files:
        try:
            txt = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        out.append((os.path.basename(f).split()[0], txt))
    return out


def sample(cat, limit=120, per_pat=6):
    pats = CATS[cat]
    chapters = load_chapters(limit)
    hits = []
    for pat in pats:
        rx = re.compile(pat)
        n = 0
        for cid, txt in chapters:
            for m in rx.finditer(txt):
                s = max(0, m.start() - 90)
                e = min(len(txt), m.end() + 90)
                frag = txt[s:e].replace("\n", " / ").strip()
                hits.append((cid, frag))
                n += 1
                break
            if n >= per_pat:
                break
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", default="")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    lines = []
    cats = [c.strip() for c in a.cat.split(",") if c.strip()] if a.cat else list(CATS)
    for c in cats:
        lines.append("=" * 8 + f" {c} " + "=" * 8)
        for cid, frag in sample(c, a.limit, a.top):
            lines.append(f"[{cid}] {frag}")
        lines.append("")
    body = "\n".join(lines)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(body)
        print(f"written {a.out}  chars={len(body)}")
    else:
        print(body)


if __name__ == "__main__":
    main()
