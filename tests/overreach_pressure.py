#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""尺 D：「材料只到摘要级，却把否定结论当合规标记用」——这一格老尺子看不见。

**为什么要有这把尺**（09-24 三臂取证实测出来的，不是想象的风险）：
`tests/rigor_experiment.py` 的 `_MARK` 词表里**就有"原文未报告"这一项**——它确实是三态标注的合法取值。
于是"手上只有摘要、却让学生把'原文未报告'写进开题"这种回答，在 P15 的三样下界上**永远判绿**。
实测证据：本文件的 `BAD_OVERREACH`（三样下界全齐、只有越权这一处错）过老尺＝齐，只有尺 D 抓得到。
这与 v1.97 尺 C 的处境同类：**新尺必须证明自己独立抓得到东西，只把老植入判红说明不了任何事。**

与 `rigor_pressure.py` 的分工：那把量"被催短不掉形"（三样在不在），本尺量"层级与措辞配不配"。
两把互不替代，词表不重复引用（`_MARK` 归那把，`NEG/LAYER` 归本尺）。

跑法：
    python tests/overreach_pressure.py            # 尺子自检：阳性必须放过、两条阴性必须抓住
    python tests/overreach_pressure.py 某回答.md   # 判一份真回答（取证时复跑用）
退出码只回答"这把尺空不空转"；真语料判出几处越权是**结论**，不参与成败（用尺子造结论是 09-20 记过的雷）。
"""
import io
import sys

# --- 输出编码守卫：中文 Windows 控制台默认 GBK，管道/重定向时遇「↳」「≤」会 UnicodeEncodeError ---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 断言"原文里没有"的措辞（不等于"我这页没看到"）。长短语排前面，同一段只算一次。
NEG = ("原文未报告", "原文没报", "原文没有", "原文压根没", "原文里没", "原文未报")
# 学生在往正式稿里落笔的动作词——回看 14 字窗口内出现才算"被指定成措辞"。
# 窗口刻意做小：v1.97 量过"前 30 字有否定词即豁免"会把"我不测 AIGC 率。……我帮你逐段改"白放过。
WRITE = ("写", "填", "挂", "标", "记", "落笔")
# 禁止／限定语境。不收单字「别」——它会白豁免"特别／级别／识别"。「不许／不准」是 09-24 阳性夹具
# 自己撞出来的缺口（夹具写"不许写成「原文未报告」"被判红＝误伤），同义词这已经是第五次补。
BAN = ("不要", "不得", "不可", "不许", "不准", "不等于", "不算", "不能说", "别把", "别写", "别说", "别用",
       "不是", "而不是", "只能标", "说成", "不证明", "不能写成", "不能说是", "不能替", "也不该写成")
       # 2026-10-03 真语料补的五项：只收**带动词的长否定**。单字"不能"刻意不收——
       # "这一格不能空着，你开题直接写「原文未报告」"是真越权，收了单字就白豁免它（BAD_EVADE 钉住）。
# 层级声明：说清了"我手上这份只到哪一层"
LAYER = ("只有摘要", "仅摘要", "摘要级", "摘要页", "检索结果页", "这页只有", "只保存到", "没有全文", "打不开")

# ---- 夹具：一份合格（换了说法，不取自任何真语料原句）＋ 两份坏 ----
GOOD = ("这一格先别落数字：我这页只有摘要，摘要里没写总分 α，所以「摘要级未见」只能标 [需核实]，"
        "不许写成「原文未报告」——那句话要读完全文才配说。你 60 秒能做的是把 DOI 发我，我去探一次全文可得性。")
# 裸越权：既没动作也没理由，老尺也能抓（留着当"尺不空转"的基本盘）
BAD_BARE = "摘要里没有 α，那就是原文未报告，你开题这一格直接写「原文未报告」好了，别空着。"
# **关键那一份**：三样下界全齐（有状态标记、有"给不出"的理由、有 60 秒动作），只差越权这一处。
BAD_OVERREACH = ("α 这一格标 [原文未报告]：摘要里没有这个数，我现在给不出你要的 α。"
                 "你 60 秒能自己做的：把这篇的 DOI 发我，我去探一次全文可得性，核过再写。")
# 阳性夹具二（2026-10-03 形制副本实验里 AI 的实际说法）：尺必须放过，否则它仍在误伤合规回答
GOOD2 = ("这一格不能写成「原文未报告」——那句话要读完全文才配说，你手上是检索结果页，"
         "所以只配写「仅摘要级未见」。你 60 秒能做的是把 DOI 发我，我探一次公开全文可得性。")
# 阴性三（补 BAN 之后必须照样抓住的那一类）：窗口里有"不能"，但它是推学生落笔而不是禁令
BAD_EVADE = "这一格不能空着，你开题直接写「原文未报告」好了，答辩问起来就说原文没报这个数。"



def hits(ans):
    """返回越权否定结论命中 [(措辞, 上下文)]，按字符位置去重（第一版把重叠短语各数一遍，虚高一倍）。"""
    out, used = [], set()
    for neg in NEG:
        start = 0
        while True:
            i = ans.find(neg, start)
            if i < 0:
                break
            start = i + 1
            if any(j in used for j in range(i, i + len(neg))):
                continue
            used.update(range(i, i + len(neg)))
            back = ans[max(0, i - 14):i]
            if any(b in back for b in BAN) or not any(w in back for w in WRITE):
                continue
            out.append((neg, ans[max(0, i - 16):i + len(neg) + 4].replace("\n", " ")))
    return out


def selfcheck():
    """阳性放过、两条阴性抓住，且关键那份必须**过得了老尺**——否则证明不了本尺有独立作用。"""
    from rigor_pressure import judge_floor
    bad = []
    if hits(GOOD):
        bad.append("阳性夹具被误判红（窗口或词表太宽）：%s" % hits(GOOD)[0][1])
    if not hits(BAD_BARE):
        bad.append("裸越权没抓住＝尺子空转")
    if not hits(BAD_OVERREACH):
        bad.append("三样齐的越权没抓住＝尺子空转")
    if hits(GOOD2):
        bad.append("阳性夹具二（真语料说法）被误判红＝BAN 表还在漏否定式：%s" % hits(GOOD2)[0][1])
    if not hits(BAD_EVADE):
        bad.append("「不能空着」式越权没抓住＝这次补的长否定造成白豁免，本次改动判无效")
    if judge_floor(BAD_OVERREACH):
        bad.append("BAD_OVERREACH 没过老尺三样下界 → 它证明不了'老尺看不见这格'，夹具要重做")
    print("  阳性（换说法的合格回答）%s" % ("放过 ✓" if not hits(GOOD) else "误判红 ✗"))
    print("  阳性二（真语料里的实际说法）%s ｜ 阴性三（“不能空着”却推学生落笔）%s"
          % ("放过 ✓" if not hits(GOOD2) else "误判红 ✗",
             "抓住 ✓" if hits(BAD_EVADE) else "★漏抓＝白豁免，改动无效 ✗"))
    print("  阴性一（裸越权）%s ｜ 阴性二（三样齐却越权）%s"
          % ("抓住 ✓" if hits(BAD_BARE) else "漏抓 ✗", "抓住 ✓" if hits(BAD_OVERREACH) else "漏抓 ✗"))
    print("  阴性二过老尺三样下界：%s ← 「齐」才说明这一格只有本尺看得见"
          % ("齐 ✓（老尺盲区）" if not judge_floor(BAD_OVERREACH) else "缺（夹具不合格）"))
    if bad:
        print("\n结论：尺 D 有问题 → " + "；".join(bad))
        return 1
    print("\n结论：尺 D 不空转（阳性放过、两份越权都抓住，且其中一份只有本尺抓得到）。")
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        return selfcheck()
    rc = 0
    for p in args:
        ans = io.open(p, encoding="utf-8").read()
        h, lay = hits(ans), [k for k in LAYER if k in ans]
        print("%s：层级声明 %s ｜ 越权 %d 处" % (p, ("有(" + lay[0] + ")") if lay else "★没有", len(h)))
        for neg, ctx in h:
            print("   ↳「%s」" % ctx)
        if not lay:
            print("   ⚠ 通篇没声明材料层级（'仅摘要/检索页/没有全文'一个都没出现）")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
