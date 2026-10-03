# -*- coding: utf-8 -*-
"""v1.84 拆分批3：core/coach-rules.md 的流程性三节下沉为按需读（分片放 core/coach-rules/）。
full_e2e.py 顺序片段 16/16（由壳按序 exec，不单独运行）。
本节盯三件事：① 正文真的搬到了分片里（不是被删）；② 主手册不再复述它（单源，不重复记账）；
③ 主手册的三节标题与指针仍在（别处"见 coach-rules.md 第六节"不断链）。
分片随包分发，所以本段断言在开发树与发布包干净副本里应当完全一致地成立。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与其他片段一致
    CRD = ROOT / "core" / "coach-rules"
    cr_main = tx("core/coach-rules.md")
    _shards = {"stage-playbook.md": "### 阶段0：项目初始化与环境准备",
               "common-errors.md": "### 错误1：统计结果不显著",
               "tool-rules.md": "### 调用前三步"}
    check("v184 三个分片都在包里", all((CRD / f).is_file() for f in _shards),
          str(sorted(p.name for p in CRD.glob("*.md"))))
    _sh_text = {f: (CRD / f).read_text(encoding="utf-8") for f in _shards}
    check("v184 下沉正文真的搬到了分片里",
          all(first in _sh_text[f] for f, first in _shards.items()))
    check("v184 主手册不再复述下沉正文（单源不重复）",
          all(first in _sh_text[f] and first not in cr_main for f, first in _shards.items()))
    check("v184 三节标题仍留在主手册（引用不断链）",
          all(h in cr_main for h in ("## 六、12阶段工作流", "## 八、常见错误处理",
                                     "## 十、工具调用规范"))
          and all(("`core/coach-rules/" + f + "`") in cr_main for f in _shards))
    check("v184 每个分片都带出处指针",
          all(_sh_text[f].splitlines()[2].count("core/coach-rules.md") >= 1 for f in _shards))
    check("v184 十二阶段一条没丢", all(("### 阶段%d：" % i) in _sh_text["stage-playbook.md"]
                                        for i in range(12)))
    check("v184 八类错误一条没丢", all(("### 错误%d：" % i) in _sh_text["common-errors.md"]
                                        for i in range(1, 9)))
    _main_b = len(cr_main.encode("utf-8"))
    _sh_b = sum(len(t.encode("utf-8")) for t in _sh_text.values())
    check("v184 必读主手册瘦身过半", _main_b <= 16000 and _sh_b >= 15000,
          "主手册%d 分片%d" % (_main_b, _sh_b))
    # ---- 开局必读总量：清单从 START 的声明里现抽，不写死在本片段 ----
    # 为什么必须这样抽：P43 把"六份必读"改成三层加载之后，任何把文件列表写死的总量闸都会立刻失去意义——
    # 改口径的人可以顺手把清单缩到三份来"达标"。所以这把尺**只认 START.md 第二步声明的层一清单**：
    # 抽不出四份＝声明改了、这把尺没跟着改（红）；清单变多＝有人把每轮必需的东西加进开局集（读数立刻涨，照样撞闸）。
    # 保护的是"开局一次读进上下文的量"：它涨，挤掉的是学生材料与对话空间，而且条数越多、越靠后的规则越容易被漏掉
    # （IFScale，arXiv 2507.11538）。
    # 为什么是 54,000：闸放在 P43 第二批摘完人设与副本之后。余量约 1.8 KB ＝"一条确实必须开局在场的规矩"的成本；
    # 更宽等于允许把内容搬进开局集而不必真瘦身，更严会让下一次合理下沉刚做完就撞红、闸变成惩罚瘦身本身。
    # ⚠ `tx()` 把 CRLF 归一成 LF 再量，所以这里管的是归一后的字节，不是文件原始大小。
    # 撞了怎么办：**先把按需读的内容摘出开局集，减不下来才动这个数**，动数要在
    # `维护档案/CHANGELOG/02-维护决定.md` 当日写清摘了哪几段、挪到哪个分片——抬数本身不算处理。
    _l1_16, _seen16 = [], False
    for _ln16 in tx("START.md").split("\n"):
        _s16 = _ln16.strip()
        if "层一" in _s16:
            _seen16 = True
        elif "层二" in _s16:
            break
        if _seen16 and _s16[:1].isdigit() and _s16[1:3] == ". " and _s16[3:4] == "`":
            _l1_16.append(_s16.split("`")[1])
    check("层一清单能从 START 声明抽出四份（抽不出＝改了口径没同步这把尺）",
          len(_l1_16) == 4 and "CONSTITUTION.md" in _l1_16, "抽到：%s" % _l1_16)
    _open16 = len(tx("START.md").encode("utf-8")) + sum(len(tx(f).encode("utf-8")) for f in _l1_16)
    check("开局必读层一总量低于 54KB", _open16 < 54000, "合计%d 清单%s" % (_open16, _l1_16))
    check("总量这把尺不空转（阴性：层一再加 2KB 就该撞闸，说明余量确实薄）", _open16 + 2000 >= 54000,
          "现量%d＋2KB=%d，闸在 54000" % (_open16, _open16 + 2000))
    # 阴性：清单被抽少一份时，上面那条"抽得出四份"要当场红（证明这把尺真在盯口径，不是只盯数字）
    # 阴性（真变异）：把 START 声明里"层一"那两个字改掉，这把尺就该抽不到清单——
    # 证明它盯的是**声明本身**，而不是把四份文件名硬编码在这里。改掉声明却改不出红＝这把尺空转。
    _mut_l1 = tx("START.md").replace("层一·开局必读", "第X部分·开局必读", 1)
    _probe, _sp = [], False
    for _pl in _mut_l1.split("\n"):
        _ps = _pl.strip()
        if "层一" in _ps:
            _sp = True
        elif "层二" in _ps:
            break
        if _sp and _ps[:1].isdigit() and _ps[1:3] == ". " and _ps[3:4] == "`":
            _probe.append(_ps.split("`")[1])
    check("抽清单这步不空转（阴性：改掉层一声明标题后应抽不到四份）",
          _probe != _l1_16 and len(_l1_16) == 4,
          "变异后抽到%d份：%s" % (len(_probe), _probe))
    check("tdoc 无同名子目录时等价于 tx（阴性：尺子不空转）",
          tdoc("core/ai-literacy.md") == tx("core/ai-literacy.md"))
    check("tdoc 把分片拼进来了（阴性：漏读会被抓到）",
          "阶段11：答辩准备" in cr and "阶段11：答辩准备" not in cr_main)
    st16 = tx("START.md") + tx("AGENTS.md")
    check("v184 入口文档同步了按需读口径",
          st16.count("core/coach-rules/") >= 1 and "进入" in st16)

    # ---- v1.95：主手册下沉两处（三种可选语气 / 紧急模式三档逐日方案）----
    # P43 第二批：语气那一处已被**撤销**（用户 2026-10-03 拍板"人设什么的都可以完全删了"，
    # 三条理由与逐字出处在 `维护档案/评估结论-开局必读集减负-2026-10-03.md`），`tones.md` 只剩存根。
    # 原来那三条"正文真搬到了语气分片／主手册不复述它／分片里的语气标签仍在"都不再是正确判据，
    # 所以从这里抽掉 tones.md：紧急模式那处照旧全文核对，语气翻成下面两条正面判据。
    _new195 = {"emergency.md": "### 7天版（保完整、砍锦上添花）"}
    _nt195 = {f: (CRD / f).read_text(encoding="utf-8") for f in _new195}
    check("v195 下沉分片都在包里且正文真搬到了分片",
          all((CRD / f).is_file() for f in _new195)
          and all(h in _nt195[f] for f, h in _new195.items()))
    check("v195 主手册不再复述这两处下沉正文（单源不重复）",
          all(h in _nt195[f] and h not in cr_main for f, h in _new195.items()))
    check("v195 下沉分片都带出处指针",
          all(_nt195[f].splitlines()[2].count("core/coach-rules.md") >= 1 for f in _new195))
    check("v195 下沉小节的标题与指针仍留在主手册（引用不断链）",
          all(h in cr_main for h in ("### 7天／3天／1天三档逐日方案",))
          and all(("`core/coach-rules/" + f + "`") in cr_main for f in _new195),
          "缺指针：%s" % [f for f in _new195 if ("`core/coach-rules/" + f + "`") not in cr_main])
    # 阴性：把分片正文抄回主手册，单源那条必须判红（否则这把尺子空转）
    _mut195 = cr_main + "\n" + _new195["emergency.md"]
    check("v195 单源尺子抓得住复述（阴性）",
          not all(h in _nt195[f] and h not in _mut195 for f, h in _new195.items()))
    # ---- P43 新增两条：语气撤销之后要撤干净、也不许留成孤儿文件 ----
    # 存根若没人指，下个会话读到它会把"三种语气"当成还在提供；若标签与人设名还活在任意一份学生读得到的文件里，
    # 撤销就是假的。两条都是正面判据，比原来只查"标签在不在分片里"更严。
    _stub16 = (CRD / "tones.md").read_text(encoding="utf-8") if (CRD / "tones.md").is_file() else ""
    check("P43 语气分片收成存根且被主手册指着（不留孤儿）",
          "不要再往这里加语气内容" in _stub16 and "### 可选语气" not in _stub16
          and "`core/coach-rules/tones.md`" in cr_main)
    check("P43 语气标签不再出现在任何学生读得到的规则里",
          not any(h in cr_main for h in ("### 可选语气三种", "简洁直接 / 温和耐心 / 活泼热情"))
          and "可选语气 1：简洁直接" not in _stub16)
    # 下面这条是给"下一个版本"留的余量，不是给今天看的：主手册与回归壳都不许再贴闸。
    _shell195 = tx("tests/full_e2e.py").splitlines()
    check("v195 主手册与回归壳都为下次改动留了余量",
          220 - len(cr_main.splitlines()) >= 20 and 220 - len(_shell195) >= 100,
          "主手册%d 壳%d" % (len(cr_main.splitlines()), len(_shell195)))
