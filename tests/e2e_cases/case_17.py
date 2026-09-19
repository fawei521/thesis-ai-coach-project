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
"""
    (_d17 / "我的模型图.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (_d17 / "坏大纲.md").write_text(BAD17, encoding="utf-8")
    (_d17 / "好大纲.md").write_text(GOOD17, encoding="utf-8")
    (_d17 / "进度卡.md").write_text(
        "# 进度卡\n- 论文题目：AI依赖与青少年自伤\n- 研究类型：横断问卷\n"
        "- 自变量 X：AI情感依赖\n- 因变量 Y：非自杀性自伤\n- 计划答辩时间：2027年5月\n", encoding="utf-8")
    b17 = run(["tools/proposal_readiness.py", str(_d17 / "坏大纲.md"), str(_d17 / "进度卡.md"), "--strict"])
    bo17 = (b17.stdout or "") + (b17.stderr or "")
    check("v185 坏大纲能跑通并报缺项", b17.returncode == 1 and "八节里的「参考文献」没找到" in bo17
          and "留着【】" in bo17 and "找不到，排成 PPT 会是空框" in bo17, bo17[-500:])
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
