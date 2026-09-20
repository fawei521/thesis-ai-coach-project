# -*- coding: utf-8 -*-
"""v1.94 成果交付纪律 / 外部技能规范 / PPT 底线与风格化 / 毕业材料总清单（详见 CHANGELOG v1.94）。
full_e2e.py 顺序片段 22/22（由壳按序 exec，不单独运行）。
骨架名字（check/tx/tdoc/SK/ROOT…）都在壳的 globals() 里，本文件不重新定义、
也不给 _ns/_fn/_p 赋值（v1.91 的 case_20 就是这么把后续片段的运行环境换成空字典的）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，与拆分前的扁平脚本语义一致

    # ---- 1. 两份新权威文件两侧都在，且被入口指到（写了没人读＝没写）----
    od_full = tx("core/outcome-delivery.md")
    od_lite = tx("doubao-skill/references/outcome-delivery.md")
    ss_full = tx("core/skill-sourcing.md")
    ss_lite = tx("doubao-skill/references/skill-sourcing.md")

    def _c22_missing(text, anchors):
        """返回没命中的锚点。写成函数是为了能做阴性：抽掉一句就该抓到一句。"""
        return [a for a in anchors if a not in text]

    OD_ANCHORS = ["先问截止时间", "一套交付物", "三态回执", "不擅自进入", "静默消失", "一件不少",
              "PPT 属于开题与答辩的必交付物"]
    SS_ANCHORS = ["三道闸", "许可证", "_external", "绝不", "登记", "规避 AI 检测",
                  "不装用户全局目录", "保底"]

    check("v194成果交付五步两侧齐",
          not _c22_missing(od_full, OD_ANCHORS) and not _c22_missing(od_lite, OD_ANCHORS),
          "完整版缺 %s ｜ 轻量版缺 %s" % (_c22_missing(od_full, OD_ANCHORS),
                                          _c22_missing(od_lite, OD_ANCHORS)))
    check("v194外部技能规范两侧齐",
          not _c22_missing(ss_full, SS_ANCHORS) and not _c22_missing(ss_lite, SS_ANCHORS),
          "完整版缺 %s ｜ 轻量版缺 %s" % (_c22_missing(ss_full, SS_ANCHORS),
                                          _c22_missing(ss_lite, SS_ANCHORS)))
    # 阴性：把"PPT 是必交付物"整句抽掉，锚点尺必须抓到（用户 09-20 实测就是栽在这一句上）
    _m22 = od_full.replace("PPT 属于开题与答辩的必交付物，不是加分项。", "（此处植入：把必交付那句删掉了）")
    check("v194抽掉PPT必交付那句必须判红",
          _m22 != od_full and "PPT 属于开题与答辩的必交付物" in _c22_missing(_m22, OD_ANCHORS))
    _m22b = ss_full.replace("不得出现\"规避 AI 检测\"", "不得出现\"某种说法\"")
    check("v194抽掉检测红线必须判红",
          _m22b != ss_full and "规避 AI 检测" in _c22_missing(_m22b, SS_ANCHORS))

    for _f22, _name in (("START.md", "完整版入口"), ("AGENTS.md", "维护者入口"),
                        ("core/coach-rules.md", "主手册")):
        _t22 = tdoc(_f22)
        check("v194%s指向两份新文件" % _name,
              "core/outcome-delivery.md" in _t22 and "core/skill-sourcing.md" in _t22)
    check("v194轻量版入口指向两份新文件",
          "references/outcome-delivery.md" in tx("doubao-skill/SKILL.md")
          and "references/skill-sourcing.md" in tx("doubao-skill/SKILL.md"))
    check("v194交付门禁已进每轮回复前清单",
          "本轮若在学生要求下直接产出了成品" in tdoc("core/coaching-protocol.md"))

    # ---- 2. 紧急模式必做全套：主手册与两份阶段卡口径一致 ----
    check("v194紧急模式指向成果交付",
          "core/outcome-delivery.md" in tdoc("core/coach-rules.md")
          and "学生此时要**你**直接出成品" in tdoc("core/coach-rules.md"))
    check("v194轻量版紧急模式同样必做全套",
          "默认做全套" in od_lite and "一件不少" in od_lite)

    # ---- 3. PPT 从骨架升级为底线＋风格化 ----
    pg = tx("workflows/proposal-guide.md")
    PPT_ANCHORS = ["内容底线", "视觉底线", "风格化", "不接受\"套一个模板交上去\"",
                   "外部 PPT 技能", "保底路径", "必交付物，不是加分项"]
    check("v194PPT 第四节含底线与风格化两段",
          not _c22_missing(pg, PPT_ANCHORS), str(_c22_missing(pg, PPT_ANCHORS)))
    tmpl = tx("templates/opening-ppt-outline.md")
    check("v194开题模板带风格化作业单且可被就绪度自检抓到",
          "风格化作业单" in tmpl and "主色" in tmpl and "版式语言" in tmpl
          and "【 】" in tmpl.split("风格化作业单")[1][:400])
    check("v194模板页数骨架仍是 12 页（就绪度按第N页计数）",
          len(re.findall(r"第\s*\d+\s*页", tmpl)) == 12)
    check("v194轻量版阶段6同步底线与检索要求",
          all(s in tx("doubao-skill/stages/stage-6-method.md")
              for s in ("必交付物，不是加分项", "视觉底线", "风格化由做的人自己设计",
                        "references/skill-sourcing.md")))

    # ---- 4. 修掉的真实口径冲突：开题 PPT 页数三处一致 ----
    s6 = tx("doubao-skill/stages/stage-6-method.md")
    check("v194开题PPT页数两侧统一为8-12",
          "8–12 页" in s6 and "8-12页" in pg.replace("8–12 页", "8-12页")
          and "10–15 页（背景" not in s6)
    check("v194轻量版开题PPT不再写10-15页",
          "PPT 控制 10–15 页" not in s6 and "控制 **8–12 页**" in s6)

    # ---- 5. 毕业材料总清单：模板入库、进生成清单、阶段0 指向它 ----
    mc = tx("templates/materials-checklist.md")
    MAT_ANCHORS = ["任务书", "计划书", "中期检查", "指导记录", "外文", "承诺书",
                   "答辩记录", "成绩评定", "查重", "AI 使用声明", "需核实"]
    check("v194材料清单覆盖原流程漏掉的表格",
          not _c22_missing(mc, MAT_ANCHORS), str(_c22_missing(mc, MAT_ANCHORS)))
    check("v194材料清单标明逐校不同不套别校",
          "本校" in mc and "别拿别的学校的清单当标准" in tx("core/coach-rules/stage-playbook.md"))
    sw22 = tx("tools/setup_workspace.py")
    check("v194材料清单进第22项生成清单",
          '("我的毕业材料清单.md", "templates/materials-checklist.md"' in sw22)
    check("v194阶段0先要学校那套表格",
          "先要齐本校那套表格" in tx("core/coach-rules/stage-playbook.md")
          and "我的工作区/我的毕业材料清单.md" in tx("core/coach-rules/stage-playbook.md"))
    check("v194材料清单来源可追溯且标注非本校标准",
          "南京航空航天大学" in mc and "上海大学" in mc and "江苏海洋大学" in mc)

    # ---- 6. 外部技能的许可证红线（本包要转发给学生）----
    check("v194许可证红线点名 source-available 并禁止复制入包",
          "All rights reserved" in ss_full and "绝不能被我们复制进包里" in ss_full
          and "source-available" in ss_full)
    check("v194装前必查行为且读不懂就不装",
          "读不懂它做什么，就是不装的理由" in ss_full and "读不懂它做什么，就是不装的理由" in ss_lite)
    check("v194轻量版如实处理装不了的环境不假装",
          "装不了就是装不了" in ss_lite and "假装" in ss_lite)
    gi = tx(".gitignore")
    check("v194外部技能目录不入库不随包分发",
          ".qoder/skills/_external/" in gi)

    # ---- 7. 松绑：示例是判据不是台词 ----
    check("v194全局松绑条款已落地",
          "把示例当台词念" in tdoc("core/coach-rules.md")
          and "不是要你照念的台词" in tx("doubao-skill/personalities/default.md"))
    check("v194四个语气文件的示例段都改判据口径",
          all("不是要你照念的台词" in tx("doubao-skill/personalities/%s.md" % n)
              for n in ("default", "concise-direct", "gentle-patient", "lively-warm")))
