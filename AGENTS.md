# AGENTS.md — AI 助手入口

> 本文件是给**自动化 AI 助手**（支持 AGENTS.md 约定的工具）读的入口。
> 人类学生请直接看 `QUICKSTART.md`；被学生交付项目包的对话式 AI 请从 `START.md` 开始。

## 这个仓库是什么

`thesis-ai-coach-project` 是一个**可交付给 AI 的毕业论文引导工具包**：学生把整个文件夹交给 AI，
AI 读取 `START.md` 后作为陪学生做心理学毕业论文的 AI 助手/学习伙伴（不是老师、不是虚拟伴侣），引导学生完成从选题到答辩的全过程，
并能运行随包的 Python 工具完成数据清洗、统计分析、文献检索、重点文献卡片、图表生成。

**它不是软件，不需要安装**；核心是文档规则 + 纯标准库 Python 脚本。

## 读什么（按优先级）

| 顺序 | 文件 | 说明 |
|---|---|---|
| 1 | `CONSTITUTION.md` | **项目宪法，最高原则**。与任何其它文件冲突时以它为准 |
| 2 | `START.md` | **辅导学生的启动流程**（角色、规则层级、必读/按需读清单、12 阶段导航） |
| 3 | `core/coach-rules.md` | 行为准则（角色、核心原则、语气、难度、进度卡、学术红线、紧急模式、检查闸）；其 12 阶段/常见错误/工具调用三节 v1.84 起下沉为按需读，指针在本文件 |
| 4 | `core/companionship.md` | 身份定位与陪伴边界（AI 工具/学习伙伴，不自称老师、不做虚拟伴侣，识别并拉回情感依赖，未成年人条款） |
| 5 | `core/coaching-protocol.md` | 每轮对话强制基准（引导循环、反馈三段式、P0/P1/P2、边界、危机、门禁） |
| 6 | `core/encouragement-guide.md` | 鼓励与反馈口径（默认开、可关；原则化自然化；P0 不包装） |
| 7 | `core/ai-literacy.md` | AI 素养（能力边界、幻觉防范、学术诚信） |
| 按需 | `core/outcome-delivery.md` | **学生要你直接出成品时必读**：先问截止日期与学校格式要求，把「一个成果」拆成一整套交付物（开题＝报告+PPT+模型图+讲稿+问答+自查），交学生确认，每件先找现成技能，最后给三态回执；**执行者身份不等于代交** |
| 按需 | `core/skill-sourcing.md` | 本包模板/脚本兜不住质量时（PPT 美化、去 AI 腔、学校排版）：去哪检索外部技能、装前过**许可证／行为／学生同意**三道闸、只装项目级 `.qoder/skills/_external/`、登记与卸载 |
| 按需 | `core/evidence-rigor.md` | **证据与核验纪律**：报出任何来自论文/网页/数据库的数字、下任何"没人做过/原文没报"的否定结论之前必读——摘要与检索页不算原文 |
| 按需 | `core/literature-kb.md` | **文献知识库纪律**：学生问"这个数哪来的"、要回答领域事实、或要收尾登记时读——先查本地库再联网；**卡片是定位器不是第二源**，摘要级的卡照样不能吃 |
| 按需 | `workflows/*.md` | 分阶段操作手册，**到哪个阶段读哪个，不要一开始全读** |
| 按需 | `core/coach-rules/*.md` | 主手册下沉的五份细则：`stage-playbook.md`（12 阶段各自的手册/动作/完成标志）、`common-errors.md`（8 类错误的处置）、`tool-rules.md`（调用工具前三步）、`tones.md`（三种可选语气各要做到什么）、`emergency.md`（紧急模式 7天/3天/1天逐日方案）——**进到对应场景才读，不要开局通读** |
| 按需 | `psychology/*.md` | 量表库 / 统计指南 / 伦理，**查证时才读** |
| 按需 | `templates/*` | 需要产出问卷、大纲、开题、PPT、网页时再读 |

## 如果你要改这个项目（维护者模式）

> **先认清你在哪份上工作**：发布包（学生拿到的那份）**不含 `tests/` 与 `DEVELOPMENT.md`**——
> 回归断言与开发流程只存在于仓库里（`tests/e2e_cases/case_21.py` 钉着这件事）。
> 在学生包副本里既跑不了回归，也不该按下面的门禁动手；那种副本只用于"验证学生看到的东西"。

必须先读 `DEVELOPMENT.md`（九阶段门：分析→调研→查找→学习→方案→实现→测试→文档→发布）。

**改动后的验证：按"改了什么东西"选闸，不要每完成一小步就跑全量。**

```bash
python tests/smoke_check.py         # 改中途：约 5 秒，九项结构闸
python tests/smoke_check.py --full  # 该跑全量时：跑完打印一行 [门禁凭证]，原样贴进 commit 说明
```

**哪一批改动必须跑到全量，只看 `DEVELOPMENT.md` 阶段 T 的"跑哪一道闸"表**——那张表只有一份，这里不重抄。
动了表里那些路径却没贴凭证，`case_21.py` 的审计判红：凭证里的 `head=` 是**跑那一刻的 commit 短号**，
没真跑过就凑不出来——这就是让"偷懒留痕"的机制，你不用盯着。**项数一律看各命令末行，不要在文档里抄数字。**

**判定只看各命令最后一行结论（"失败 0"）。** 放后台跑时，"后台任务退出码 0"说的是任务包装器，
不是被测程序——这条误判过一次，别再犯。

- 新增能力**必须**同步加断言（不允许只加功能不加回归）：断言写在 `tests/e2e_cases/` 下对应主题的 `case_NN` 片段里（编号连续，顺序以壳里的 `FRAGMENTS` 为准），
  `tests/full_e2e.py` 是骨架 + 片段顺序清单的壳，只在新增主题片段时才动。
- 文件尺寸：不在 `tests/size_baseline.txt` 里的文件一律 ≤220 行；超标的存量文件冻结在清单里，
  **只减不增**；降到 220 以下后跑 `python tests/size_ratchet.py --write` 把它移出清单（棘轮自动收紧）。
- 版本历史只有 `CHANGELOG.md` 一个来源；`README.md` / `PROJECT_PLAN.md` / `ROADMAP.md` 只留指针。
- 发布需在**项目之外**的干净解压副本里再跑一遍 `full_e2e.py`。

## 硬约束（不要违反）

- **不代写代交论文正文**（可给可编辑草稿，但必须标注草稿、逐段报告风险、经学生逐句核实改写；不改不核实直接提交仍是红线）、不编造文献 / 数据 / 引用、不替学生做决定。
- 所有统计脚本结果是**预览与教学口径**，正式结果以 JASP / SPSS / PROCESS 复核为准。
- `generate_demo_data.py` 的模拟数据**严禁**进入真实论文。
- 涉及自伤 / 自杀等敏感话题时遵守 `psychology/ethics.md`，提供求助渠道（全国心理援助热线 **12356**），不做临床诊断。
- 不在学生数据上做删除 / 篡改；数据清洗只识别无效问卷，**不得为追求显著而删数据**。
- 学生的工作文件统一放在 `我的工作区/`（`01-文献PDF` / `02-问卷数据` / `03-分析结果` / `04-网页`），不要与项目文件混放。

## 目录速查

```
START.md            AI 辅导入口（对话式 AI 从这里开始）
CONSTITUTION.md     项目宪法（最高原则）
core/               规则手册（coach-rules.md + 下沉细则 coach-rules/*.md）+ 引导反馈协议 + 身份陪伴边界 + 鼓励系统 + AI 素养
workflows/          各阶段操作手册（按需读）
psychology/         量表库 / 统计指南 / 伦理
templates/          各类模板 + 网页范例/
tools/              31 个可调脚本（菜单入口 menu.py 的实现拆为 menu_io.py 交互件 + menu_data.py 数据统计组 + menu_lit.py 文献产出组 + menu_thesis.py 开题与材料检查组 + menu_ref.py 原文与题录核验组 + menu_kb.py 文献知识库组）＋含 webpage_preview.py 网页预览器、anonymize_data.py 去标识化、effect_size.py 效应量换算复核、validity_cr_ave.py 聚合/区分效度、item_analysis.py 预试项目分析、content_cvi.py 自编量表内容效度CVI、reference_formatter.py 参考文献GB/T 7714格式化、missing_report.py 缺失值分析与Little MCAR检验、assumption_check.py 参数检验前提假设（Shapiro正态性/Brown-Forsythe方差齐性）、paired_compare.py 配对设计差异检验（前后测配对t/d_z/Wilcoxon符号秩/rank-biserial r；--onesample/--constant 单样本对标称常数）、mult_compare.py 多重比较校正（Bonferroni/Holm/BH/BY）、literature_cards.py 文献卡片、outline_to_ppt.py 大纲→PPT（只排版不代写）、setup_workspace.py 工作区补齐、proposal_readiness.py 开题就绪度自检、style_check.py AI 腔体检（不测检测率）、authorship_log.py 写作留痕、lit_fetch.py 原文可得性探测与下载、lit_verify.py 题录双源核验、kb_index.py 知识库清点与对账、kb_search.py 知识库检索（BM25＋中文二元切分，纯标准库离线））+ stats/ 统计实现包（13 个模块：mathx / linalg / dataio / desc / reliability / plots / efa / compare / correlation / regression / mediation / moderation / outliers；`regress.py` 自 v1.82 起只是仅再导出的历史入口）
tests/              只在仓库里、不随发布包分发：full_e2e.py 全量回归（壳，v1.95 起临时目录与收尾清理的实现在 e2e_tmp.py）+ e2e_cases/ 断言主题片段（case_NN 编号连续，顺序见壳里的 FRAGMENTS）、consistency_check.py 一致性自检、size_ratchet.py 文件尺寸棘轮
我的工作区/          学生自己的文件（原始数据、PDF、结果、网页）；进度卡与检索记录**不在包里**，由菜单第 22 项缺才生成
CHANGELOG.md        版本历史（唯一来源）
DEVELOPMENT.md      维护者开发流程（学生辅导时不需要；同样只在仓库里，不随发布包分发）
```
