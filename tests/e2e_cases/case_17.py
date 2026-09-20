# -*- coding: utf-8 -*-
"""v1.85 开题就绪度自检工具（tools/proposal_readiness.py + 菜单第 23 项）。
full_e2e.py 顺序片段 17/17（由壳按序 exec，不单独运行）。
夹具全部现造在 tests/.tmp_e2e/v185 里，不依赖学生工作区（发布包里的 我的工作区 只有占位文件）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与其他片段一致
    _d17 = new_tmp("v185")
    BAD17 = """# 我的开题大纲
## 第1页：选题背景
- 【填：使用普及率的数字与来源】青少年 AI 依赖越来越普遍
## 第2页：文献综述
- 三条脉络与缺口
## 第3页：研究假设
- H1 AI 依赖会**导致**自伤增加
## 第4页：研究方法
- 横断问卷，计划发放 400 份
- 用 auto_stats.py 跑中介模型
- 模型图见 ![模型](不存在的模型图.png)
## 第5页：创新点
- 新人群与新变量组合
## 第6页：进度安排
- 3 月完成开题
## 第7页：预期困难
- 样本回收慢
"""
    GOOD17 = """# 我的开题大纲
副标题：开题报告
汇报人：张三
指导教师：李老师
## 第1页：选题背景与意义
- 青少年 AI 陪伴使用普及，需要弄清它与心理风险的关系
## 第2页：文献综述与研究空白
- 三条脉络（AI 依赖、孤独感与自伤、同伴媒介），缺口在机制（张伟, 2022）
## 第3页：研究问题与假设
- H1 孤独感在 AI 依赖与自伤间起中介作用；H2 反刍起链式中介作用
## 第4页：研究模型
- ![研究模型图](我的模型图.png)
## 第5页：研究方法与设计
- 横断问卷，对象为初中生与高中生，计划发放 350 份（样本量估算依据见方法节）
- 工具：UCLA 孤独感量表 8 题、信度 α=.84；反刍量表 10 题、α=.87（均引原文献）
- 分析：相关与链式中介（PROCESS 模型6，Bootstrap 5000），用 JASP 复核
- 程序：匿名施测，参与前取得学生本人知情同意与监护人同意
## 第6页：研究创新点
- 新情境下的变量组合，1 个创新点
## 第7页：研究进度安排
- 3 月开题、4-5 月收数据、6 月分析、9 月答辩
## 第8页：预期困难与对策
- 回收慢则扩大渠道并如实报告样本局限
## 第9页：参考文献
- 李强, 2023；王芳, 2021（均已在库中核对原文）
## 第10页：请老师指正
- 谢谢各位老师，恳请批评指正
"""
    (_d17 / "我的模型图.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (_d17 / "坏大纲.md").write_text(BAD17, encoding="utf-8")
    (_d17 / "好大纲.md").write_text(GOOD17, encoding="utf-8")
    (_d17 / "进度卡.md").write_text(
        "# 进度卡\n- 论文题目：AI依赖与青少年自伤\n- 研究类型：横断问卷\n"
        "- 自变量 X：AI情感依赖\n- 因变量 Y：非自杀性自伤\n- 计划答辩时间：2027年5月\n", encoding="utf-8")
    b17 = run(["tools/proposal_readiness.py", str(_d17 / "坏大纲.md"), str(_d17 / "进度卡.md"), "--strict"])
    bo17 = (b17.stdout or "") + (b17.stderr or "")
    check("v185 坏大纲能跑通并报缺项", b17.returncode == 1 and "没找到——按 proposal-guide" in bo17
          and "处【】没换成你自己的内容" in bo17 and "找不到，排成 PPT 会是空框" in bo17, bo17[-500:])
    check("v185 坏大纲抓到三类风险",
          "未成年人却没写知情同意" in bo17 and "强因果措辞" in bo17 and "混进了工具脚本名" in bo17, bo17[-500:])
    check("v185 进度卡与大纲不一致能抓到", "AI情感依赖 在大纲中找不到" in bo17
          and "大纲的进度安排里没有对应月份" not in bo17, bo17[-400:])
    g17 = run(["tools/proposal_readiness.py", str(_d17 / "好大纲.md"), "--no-progress", "--strict"])
    go17 = (g17.stdout or "") + (g17.stderr or "")
    check("v185 写好的大纲不误报（尺子不空咬）", g17.returncode == 0 and "可以拿去讲了" in go17
          and "[缺项]" not in go17 and "[矛盾]" not in go17 and "[风险]" not in go17, go17[-600:])
    n17 = run(["tools/proposal_readiness.py", str(_d17 / "根本不存在.md")])
    check("v185 找不到大纲时中文报错退出1", n17.returncode == 1 and "找不到开题大纲" in (n17.stdout or ""))
    _before17 = sorted(p.name for p in _d17.iterdir())
    run(["tools/proposal_readiness.py", str(_d17 / "坏大纲.md"), "--no-progress"])
    check("v185 只报问题不改写任何文件",
          sorted(p.name for p in _d17.iterdir()) == _before17
          and not any(k in (ROOT / "tools" / "proposal_readiness.py").read_text(encoding="utf-8")
                      for k in ("write_text", "write_bytes", "mkdir(", "unlink", "remove(")))
    menu17 = "\n".join(tx("tools/" + p.name) for p in sorted((ROOT / "tools").glob("menu*.py")))
    check("v185 菜单第23项已接线", "【23/23】" in menu17 and "t_readiness" in menu17
          and "proposal_readiness.py" in menu17, "菜单里没找到第 23 项")
    check("v185 入口文档已同步", "proposal_readiness.py" in tx("START.md")
          and "就绪度" in tx("QUICKSTART.md"))
    check("v185 不写论文正文的红线写在工具里",
          "不代写" in tx("tools/proposal_readiness.py") and "只报问题" in tx("tools/proposal_readiness.py"))
    # ---- v1.87 真人走查缺陷修：S1 隐私闸（v1.92 起改量"包里那一份"）----
    # 原状：包里那份就是学生要填的那一份（同一路径），所以这把尺只能盯 git 基线、在干净副本里自动跳过。
    # P9 之后包内只有 `templates/progress-template.md` 一份空白基线（填写版不进包），
    # 于是它可以离开 .git 条件——**阶段 G 的干净解压副本也会量一遍**，学生拿到手的空白卡保证是空的。
    _fields87 = ("- 学生姓名/昵称", "- 指导教师", "- 计划答辩时间",
                 "- 论文题目（暂定）", "- 自变量 X", "- 因变量 Y")
    def filled87(text):
        rows = [l for l in text.splitlines() if l.split("：")[0] in _fields87]
        return len(rows), [l for l in rows if l.split("：", 1)[1].strip()]
    _n87, _hot87 = filled87(tx("templates/progress-template.md"))
    check("v187包内进度卡基线仍是空白模板", _n87 == 6 and not _hot87,
          "六个身份字段命中 %d 行、其中已填 %d 行" % (_n87, len(_hot87)))
    if (ROOT / ".git").exists() and (ROOT / "我的工作区" / "我的论文进度.md").exists():
        # 尺子不空转的现场证明：同一把尺量本机这份真填过的，必须抓到痕迹
        _nw87, _hw87 = filled87(tx("我的工作区/我的论文进度.md"))
        check("v187同一把尺量工作副本要能抓到填写痕迹", _hw87 and len(_hw87) >= 1,
              "工作副本命中 %d 条" % len(_hw87))
    # S5：菜单第21项排 PPT 前要先警告占位符没换（不阻塞、不吃输入，避免改变既有交互断言）
    _ppt87 = tx("tools/menu_lit.py")
    check("v187排PPT前警告未替换占位", "处【】没换成你自己的内容" in _ppt87 and "菜单第 23 项" in _ppt87)
    # S4：PPT 与报告体两套口径；S2/S3：进度卡取值净化与假设"空即报"
    _pr87 = tx("tools/proposal_readiness.py")
    check("v187就绪度双口径与取值净化已生效",
          "SECTIONS_PPT" in _pr87 and "SECTIONS_REPORT" in _pr87 and "def clean_value" in _pr87
          and '("研究假设", "HYP")' in _pr87)
    # ---- v1.92（P9）：包内不带填写版之后，"缺才生成、有则绝不动"必须真做到，且不靠某个人记得 ----
    _s92 = new_tmp("p9files")
    _w92 = _s92 / "我的工作区"
    (_w92 / "01-文献PDF").mkdir(parents=True)
    (_w92 / "01-文献PDF" / "学生的旧文件.txt").write_text("别动我", encoding="utf-8")
    _rr92 = run(["tools/setup_workspace.py", "--root", str(_s92)])
    check("v192第22项按模板生成进度卡", _rr92.returncode == 0
          and (_w92 / "我的论文进度.md").read_bytes() == (ROOT / "templates" / "progress-template.md").read_bytes())
    check("v192第22项按模板生成检索记录",
          (_w92 / "01-文献PDF" / "检索记录.md").read_bytes() == (ROOT / "templates" / "检索记录模板.md").read_bytes())
    check("v192生成结果如实报告了", "生成 2 份待填写文件" in (_rr92.stdout or ""))
    (_w92 / "我的论文进度.md").write_text("我已填到阶段5：开题 9-23\r\n", encoding="utf-8")
    _rr92b = run(["tools/setup_workspace.py", "--root", str(_s92)])
    check("v192重跑绝不覆盖已填内容",
          _rr92b.stdout and "我已填到阶段5" in (_w92 / "我的论文进度.md").read_text(encoding="utf-8")
          and "未改动 2 份" in _rr92b.stdout)
    _s92c = new_tmp("p9check")
    (_s92c / "我的工作区").mkdir(parents=True)
    _rr92c = run(["tools/setup_workspace.py", "--root", str(_s92c), "--check"])
    check("v192只检查模式报缺且不写盘", "缺 2 份" in (_rr92c.stdout or "")
          and not (_s92c / "我的工作区" / "我的论文进度.md").exists())
    check("v192缺卡时就绪度会指路", "菜单第22项" in tx("tools/proposal_readiness.py"))
    check("v192入口文档已改成先生成",
          "已就位" not in tx("START.md") and "打开已就位的" not in tx("core/coach-rules/stage-playbook.md")
          and "故意不带" in tx("我的工作区/先读我.md") and "别直接覆盖" in tx("QUICKSTART.md"))
    # README 正文里**第一个** Skill 版本号（＝能力介绍那行）必须等于 SKILL.md 自己的声明，
    # 且任何一处都不许超过它（历史版本段落写旧号是允许的）。2026-09-20 实测 README 停在 v1.3 而轻量版已 v1.7。
    _sk92 = re.search(r"Skill\s*版本：v(\d+\.\d+)", tx("doubao-skill/SKILL.md"))
    _rm92 = re.findall(r"Skill v(\d+\.\d+)", tx("README.md"))
    _v92 = lambda v: tuple(int(x) for x in v.split("."))
    check("v192README里的Skill版本串不再漂", bool(_sk92) and bool(_rm92)
          and _rm92[0] == _sk92.group(1) and all(_v92(v) <= _v92(_sk92.group(1)) for v in _rm92),
          "SKILL.md=v%s README=%s" % (_sk92.group(1) if _sk92 else "?", _rm92))
