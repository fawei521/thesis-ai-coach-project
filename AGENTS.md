# AGENTS.md — AI 助手入口

> 本文件是给**自动化 AI 助手**（支持 AGENTS.md 约定的工具）读的入口。
> 人类学生请直接看 `QUICKSTART.md`；被学生交付项目包的对话式 AI 请从 `START.md` 开始。

## 这个仓库是什么

`thesis-ai-coach-project` 是一个**可交付给 AI 的毕业论文导师工具包**：学生把整个文件夹交给 AI，
AI 读取 `START.md` 后扮演心理学毕业论文导师，引导学生完成从选题到答辩的全过程，
并能运行随包的 Python 工具完成数据清洗、统计分析、文献检索、图表生成。

**它不是软件，不需要安装**；核心是文档规则 + 纯标准库 Python 脚本。

## 读什么（按优先级）

| 顺序 | 文件 | 说明 |
|---|---|---|
| 1 | `CONSTITUTION.md` | **项目宪法，最高原则**。与任何其它文件冲突时以它为准 |
| 2 | `START.md` | **辅导学生的启动流程**（角色、规则层级、必读/按需读清单、12 阶段导航） |
| 3 | `core/coach-rules.md` | 行为准则（人格、难度、12 阶段、学术红线、工具调用规范、检查闸） |
| 4 | `core/coaching-protocol.md` | 每轮对话强制基准（引导循环、反馈三段式、P0/P1/P2、边界、危机、门禁） |
| 5 | `core/encouragement-guide.md` | 鼓励与奖赏式反馈（默认开，可关；P0 不包装） |
| 6 | `core/ai-literacy.md` | AI 素养（能力边界、幻觉防范、学术诚信） |
| 按需 | `workflows/*.md` | 分阶段操作手册，**到哪个阶段读哪个，不要一开始全读** |
| 按需 | `psychology/*.md` | 量表库 / 统计指南 / 伦理，**查证时才读** |
| 按需 | `templates/*` | 需要产出问卷、大纲、开题、PPT、网页时再读 |

## 如果你要改这个项目（维护者模式）

必须先读 `DEVELOPMENT.md`（九阶段门：分析→调研→查找→学习→方案→实现→测试→文档→发布）。

**改动后的强制验证（退出码 0 才算通过）：**

```bash
python -m py_compile tools/*.py tools/stats/*.py tests/*.py
python tests/full_e2e.py            # 全量回归，约 3-5 分钟
python tests/consistency_check.py   # 文档 ↔ 代码一致性
```

- 新增能力**必须**同步往 `tests/full_e2e.py` 加断言，不允许只加功能不加回归。
- 版本历史只有 `CHANGELOG.md` 一个来源；`README.md` / `PROJECT_PLAN.md` / `ROADMAP.md` 只留指针。
- 发布需在**项目之外**的干净解压副本里再跑一遍 `full_e2e.py`。

## 硬约束（不要违反）

- **不代写论文正文**、不编造文献 / 数据 / 引用、不替学生做决定。
- 所有统计脚本结果是**预览与教学口径**，正式结果以 JASP / SPSS / PROCESS 复核为准。
- `generate_demo_data.py` 的模拟数据**严禁**进入真实论文。
- 涉及自伤 / 自杀等敏感话题时遵守 `psychology/ethics.md`，提供求助渠道（全国心理援助热线 **12356**），不做临床诊断。
- 不在学生数据上做删除 / 篡改；数据清洗只识别无效问卷，**不得为追求显著而删数据**。
- 学生的工作文件统一放在 `我的工作区/`（`01-文献PDF` / `02-问卷数据` / `03-分析结果` / `04-网页`），不要与项目文件混放。

## 目录速查

```
START.md            AI 辅导入口（对话式 AI 从这里开始）
CONSTITUTION.md     项目宪法（最高原则）
core/               规则手册 + 引导反馈协议 + 鼓励系统 + AI 素养
workflows/          各阶段操作手册（按需读）
psychology/         量表库 / 统计指南 / 伦理
templates/          各类模板 + 网页范例/
tools/              13 个脚本（含 webpage_preview.py 网页预览器、anonymize_data.py 去标识化、effect_size.py 效应量换算复核、literature_cards.py 文献卡片）+ stats/ 统计实现包（9 个模块）
tests/              full_e2e.py 全量回归、consistency_check.py 一致性自检
我的工作区/          学生自己的文件（原始数据、PDF、结果、网页）
CHANGELOG.md        版本历史（唯一来源）
DEVELOPMENT.md      维护者开发流程（学生辅导时不需要）
```
