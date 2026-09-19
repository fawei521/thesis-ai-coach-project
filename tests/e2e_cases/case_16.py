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
          all(h in cr_main for h in ("## 六、12阶段工作流", "## 八、8个常见错误处理",
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
    check("v184 必读六份合计低于 70KB",
          sum(len(tx("core/" + f).encode("utf-8")) for f in
              ("coach-rules.md", "companionship.md", "coaching-protocol.md",
               "encouragement-guide.md", "ai-literacy.md")) + len(tx("CONSTITUTION.md").encode("utf-8")) < 70000,
          "合计%d" % sum(len(tx(f).encode("utf-8")) for f in
                        ("core/coach-rules.md", "core/companionship.md", "core/coaching-protocol.md",
                         "core/encouragement-guide.md", "core/ai-literacy.md", "CONSTITUTION.md")))
    check("tdoc 无同名子目录时等价于 tx（阴性：尺子不空转）",
          tdoc("core/ai-literacy.md") == tx("core/ai-literacy.md"))
    check("tdoc 把分片拼进来了（阴性：漏读会被抓到）",
          "阶段11：答辩准备" in cr and "阶段11：答辩准备" not in cr_main)
    st16 = tx("START.md") + tx("AGENTS.md")
    check("v184 入口文档同步了按需读口径",
          st16.count("core/coach-rules/") >= 2 and "进入" in st16)
