# -*- coding: utf-8 -*-
"""cross_review_experiment · 交付后那段"换上下文复审"的委托话，缺一条要素能不能分得开。

规则在 `core/outcome-delivery.md` 第七节：三态回执给完，AI 要提醒学生把稿子交给**新会话或另一个 AI**
复审 AI 表达度，并**当场替他写出要发给那边的话**——五条要素齐才算做到，包里不留模板。
"要求 AI 怎么想"的规矩也算功能：没有可复跑的对照，它就只是一句写在文档里的期望。

这把尺只判形状：要素有没有交代，判不了交代得好不好。后者是行为账，走 `tests/behavior-self-test.md`
的 T77–T79，用新会话真跑一轮，不在本脚本里。

用法：python tests/cross_review_experiment.py --demo      # 逐臂打印判定，末行自数分得开几条
      python tests/cross_review_experiment.py --selftest  # 植入缺项，证明这把尺不空转
退出码：全对 0；有一条对不上 1。

变量前缀 _crx*：本文件会被 case_33.py exec 进回归壳的 globals，撞名会静默改掉后面片段的运行环境。
"""
import re
import sys

# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 上 stdout 被管道捕获会退回 GBK，读子进程输出时中文乱码（本仓在 case_21 读 git 输出时踩过）。
# 本脚本会被 case_33.py 用 subprocess 跑，读数全靠这些 print，故 stdout/stderr 一并钉成 UTF-8。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 短码与 outcome-delivery 第七节那 1.–5. 一一对应；改名要同时改 CRX_EXPECT。
CRX_VERBATIM_PAT = r"逐字比对|照这张表|照着.{0,6}词表|按词表"
CRX_NEG_PAT = r"不要|别|不必|无需|不许|不接受|禁止|不能"


def crx_asks_verbatim(text):
    """逐句看：有人要求"照着词表逐字比"才算没做到 E2；同一句里带着"不要"的否定式不算。
    这一条本身就是教训：第一版不分否定，把合规夹具自己判成了缺项（和因果词表冤枉否定句同一类错）。"""
    for sent in re.split(r"[。；！\n]", text):
        if re.search(CRX_VERBATIM_PAT, sent) and not re.search(CRX_NEG_PAT, sent):
            return True
    return False


CRX_ELEMENTS = [
    ("E1", lambda t: bool(re.search(r"文件|哪几节|章节|这份稿|该稿|稿子|草稿|\.md|版本", t))
     and bool(re.search(r"只读|不要改|不改|别改|不许直接改|不动稿|改字", t))),
    ("E2", lambda t: bool(re.search(r"类别|哪一类", t))
     and bool(re.search(r"原句|位置", t))
     and not crx_asks_verbatim(t)),
    ("E3", lambda t: bool(re.search(r"只有.{0,6}做过", t)) and bool(re.search(r"写得?得出", t))),
    ("E4", lambda t: bool(re.search(r"(?:不|别|无需|拒)[^。；]{0,28}(?:AIGC|检测|降率)", t))
     or bool(re.search(r"(?:AIGC|降率|过检测)[^。；]{0,28}(?:不做|不测|不接受|不采纳|不提供)", t))),
    ("E5", lambda t: bool(re.search(r"第 24 项|体检", t)) and bool(re.search(r"条数|剩余|命中", t))),
]

# 每臂声明自己该缺哪几条——期望写在夹具旁边，改夹具就得同时改这里。
CRX_EXPECT = {
    "合格臂": {},
    "缺 E1 臂": {"E1"}, "缺 E2 臂": {"E2"}, "缺 E3 臂": {"E3"},
    "缺 E4 臂": {"E4"}, "缺 E5 臂": {"E5"},
    "套模板臂": {"E2", "E3", "E4", "E5"},
    # 五要素看着都齐，唯独把"按类别判"换成了"照词表逐字比"——专门验 E2 那条否定判据不是摆设
    "只许逐字比表臂": {"E2"},
}

# ---- 合格臂：按五条要素现写的一段委托话（夹具；包里不留模板，这一份也不许抄去交差）----
CRX_GOOD = """请把 `我的工作区/06-论文正文/第三章草稿.md` 当成一份你没参与写过的稿子来读，只读不改——
要改哪句，写下来交回给学生自己动笔。请按学术语体的类别找问题：宣传话术、空转评价、句首靠序号撑着的骨架、
翻译腔、通篇找不出数字的段落，每条给出原句、所在小节、属于哪一类、一句改法方向，不要照着一张词表逐字比对。
读的时候最想在意的是一件事：这一节里有多少句子是只有真正做过这项施测的人才写得出来的；反过来请举出反例——
一句语法没错却等于什么都没说的那种段落，哪怕全篇零语病也要点名。这是复审表达，不测 AIGC 率，
也不要给出任何降率、过检测的建议，这类意见我一律不采纳。本稿上一轮体检还剩 2 条命中（一处设问句、
一处信度小数写法），那两条我已按位置改过，重复议了不必再报，剩余条数以这次实测为准。"""

# ---- 缺项臂：把合格臂里对应的交代整块拿掉，其余原样留着 ----
CRX_MISS = {
    "E1": lambda t: re.sub(r"请把.*稿子来读，只读不改——\n要改哪句，写下来交回给学生自己动笔。",
                           "请读这份稿子。", t, flags=re.S),
    "E2": lambda t: re.sub(r"请按学术语体的类别找问题：.*逐字比对。",
                           "请把不通顺的句子挑出来。", t, flags=re.S),
    "E3": lambda t: re.sub(r"读的时候最想在意的是一件事：.*也要点名。",
                           "整体读一遍看看顺不顺。", t, flags=re.S),
    "E4": lambda t: re.sub(r"这是复审表达，不测 AIGC 率，\n也不要给出任何降率、过检测的建议，这类意见我一律不采纳。",
                           "这是复审表达，请认真读。", t),
    "E5": lambda t: re.sub(r"本稿上一轮体检还剩 2 条命中（一处设问句、\n一处信度小数写法）[^。]*。",
                           "上一轮已经查过一遍了。", t),
}

# ---- 套模板臂：把包里的禁则表原样粘过去当"提示词"，这正是要判不合格的那种 ----
CRX_TEMPLATE = """请把 `我的工作区/06-论文正文/第三章草稿.md` 交给你审，只读不改，改字归学生。
下面这张表是我们包里的判据，请照这张表逐字比对，命中哪个词就报哪个词：
| 风险 | AI 高频动词 | 深入探讨,全面剖析,系统梳理 | 包含 | 模型最爱用的书面动词 |
| 缺项 | 空转评价 | 具有重要意义,前景广阔 | 包含 | 自我评价句，删掉不损失内容 |
"""


def crx_grade(text):
    """返回 {短码: 有没有做到}。"""
    return {code: bool(fn(text)) for code, fn in CRX_ELEMENTS}


# 只改一处：把"不要照着一张词表逐字比对"翻成要求逐字比，其余五要素原样不动。
CRX_VERBATIM = CRX_GOOD.replace("不要照着一张词表逐字比对", "请照着这张表逐字比对")

_crx_arms = [("合格臂", CRX_GOOD)]
for _crx_k in sorted(CRX_MISS):
    _crx_arms.append(("缺 " + _crx_k + " 臂", CRX_MISS[_crx_k](CRX_GOOD)))
_crx_arms.append(("套模板臂", CRX_TEMPLATE))
_crx_arms.append(("只许逐字比表臂", CRX_VERBATIM))


def crx_run(mode="demo"):
    codes = [c for c, _ in CRX_ELEMENTS]
    bad, lines = [], []
    for name, text in _crx_arms:
        got = crx_grade(text)
        miss = CRX_EXPECT.get(name)
        if miss is None:
            bad.append((name, "夹具没有对应的期望声明，先修夹具"))
            continue
        diff = [c for c in codes if got[c] != (c not in miss)]
        lines.append("%-12s 要素 %d/%d  实缺：%s"
                     % (name, sum(got.values()), len(codes),
                        "、".join(c for c in codes if not got[c]) or "无"))
        for c in diff:
            bad.append((name, c + " 判定与夹具声明不符"))
    total = len(_crx_arms) * len(codes)
    if mode == "selftest":
        base = crx_grade(CRX_GOOD)
        planted = crx_grade(CRX_MISS["E1"](CRX_GOOD))
        print("合格臂 %d/%d 为真；整块删掉 E1 那句之后 %d/%d 为真"
              % (sum(base.values()), len(base), sum(planted.values()), len(planted)))
        if sum(base.values()) != len(base):
            print("尺子漏判：合格夹具自己都没放行")
            return 1
        if sum(planted.values()) >= sum(base.values()):
            print("尺子空转：删掉一整块交代它照样放行")
            return 1
        flip = crx_grade(CRX_VERBATIM)["E2"]
        print("否定语境单独测：合格臂写着“不要逐字比”判 E2 为真；只把那句翻成要求逐字比，E2 应为假，实为%s"
              % ("真" if flip else "假"))
        if flip:
            print("尺子空转：E2 不看否定，把要求照表逐字比的臂也放行了")
            return 1
        print("植入式阴性通过：删一条就少一条，翻一句否定就翻一次判定，不是恒真的尺")
        return 0
    print("\n".join(lines))
    if bad:
        print("对不上：" + "；".join("%s %s" % b for b in bad))
        print("分得开 0/%d 条" % total)
        return 1
    print("%d 臂各判 %d 条，判定与夹具声明逐条一致：分得开 %d/%d 条（条数由本脚本自己数，不写死）"
          % (len(_crx_arms), len(codes), total, total))
    return 0


if __name__ == "__main__":
    _crx_a = sys.argv[1:]
    if "--grade" in _crx_a:
        # 用法：--grade 某段回复.txt —— 拿同一把尺量真实产出（行为读数用这个，不再靠人眼看）
        _crx_p = _crx_a[_crx_a.index("--grade") + 1]
        with open(_crx_p, "rb") as _crx_fh:
            _crx_t = _crx_fh.read().decode("utf-8", "replace")
        _crx_g = crx_grade(_crx_t)
        for _crx_c in _crx_g:
            print("%s %s" % (_crx_c, "有" if _crx_g[_crx_c] else "缺"))
        print("实测要素 %d/%d：%s" % (sum(1 for v in _crx_g.values() if v), len(_crx_g), _crx_p))
        sys.exit(0 if all(_crx_g.values()) else 1)
    sys.exit(crx_run("selftest" if "--selftest" in _crx_a else "demo"))
