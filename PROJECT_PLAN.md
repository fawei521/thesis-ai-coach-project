# 项目计划书 — Thesis AI Coach

> 本文件是项目的权威计划。所有开发工作按本文件执行，变更需更新本文件。

---

## 一、项目定位

**产品名称**：心理学毕业论文AI导师超级向导（Thesis AI Coach）

**核心形态**：一个AI可读取的项目包。学生下载后交给AI，AI读取入口文件后自动扮演心理学毕业论文导师，利用虚拟电脑、自动化脚本、专业知识库，全程引导学生从选题到答辩。

**目标用户**：心理学专业本科生（电脑小白为主），做问卷类实证研究毕业论文。

**核心价值**：
- 零门槛：下载即用，不需要懂技术
- 全流程：选题、开题、文献、问卷、数据、写作、答辩全覆盖
- 自动化：能自动做的不让学生手动做（文献检索、数据清洗、统计、图表）
- 专业化：心理学专用量表库、统计指南、伦理规范
- 守底线：学术诚信红线不可破，AI只引导不代写

---

## 二、系统架构（分层设计）

```
┌─────────────────────────────────────────────────┐
│  启动层  START.md（AI读取后自动启动）              │
├─────────────────────────────────────────────────┤
│  核心规则层  core/                                │
│  ├── coach-rules.md   角色/人格/难度/阶段/红线     │
│  └── ai-literacy.md   AI素养/提问/幻觉/诚信        │
├─────────────────────────────────────────────────┤
│  工作流层  workflows/（AI按需读取的详细操作手册）   │
│  ├── environment-setup.md    环境搭建             │
│  ├── literature-auto-search.md  文献自动检索       │
│  ├── paper-reading-guide.md  PDF结构化分析        │
│  ├── toolchain-guide.md      Zotero+Obsidian      │
│  ├── data-analysis-auto.md   自动化数据分析        │
│  ├── proposal-guide.md       开题报告专项          │
│  ├── defense-guide.md        答辩专项             │
│  └── writing-guide.md        写作辅助             │
├─────────────────────────────────────────────────┤
│  工具层  tools/（可执行脚本，AI调用）              │
│  ├── data_cleaner.py         数据清洗             │
│  ├── chart_generator.py      模型图/统计图表       │
│  ├── literature_organizer.py 文献整理去重         │
│  ├── paper_search.py         英文文献API检索      │
│  └── auto_stats.py           自动统计+三线表      │
├─────────────────────────────────────────────────┤
│  专业知识层  psychology/                          │
│  ├── scale-library.md        量表库               │
│  ├── stats-guide.md          统计指南             │
│  └── ethics.md               伦理规范             │
├─────────────────────────────────────────────────┤
│  模板层  templates/                               │
│  ├── questionnaire-template.md   问卷模板         │
│  ├── paper-outline.md            论文大纲         │
│  ├── ai-usage-declaration.md     AI声明           │
│  ├── proposal-template.md        开题报告模板      │
│  └── defense-ppt-outline.md      答辩PPT大纲      │
├─────────────────────────────────────────────────┤
│  项目管理层                                       │
│  ├── README.md / CONSTITUTION.md / ROADMAP.md    │
│  └── PROJECT_PLAN.md（本文件）                    │
├─────────────────────────────────────────────────┤
│  测试层  tests/                                   │
│  ├── e2e-test.md             端到端测试用例       │
│  └── test-data/              测试数据             │
└─────────────────────────────────────────────────┘
```

**调用关系**：
- AI读START.md → 读core/规则 → 按学生当前阶段读对应workflow → 按需调用tools脚本、参考psychology知识库、生成templates模板
- 工作流层是"操作手册"，告诉AI在每个阶段具体怎么做
- 工具层是"手"，执行具体计算和自动化
- 知识层是"脑子"，提供专业参考

---

## 三、文件清单与状态

### v1.0 已完成 ✅
| 文件 | 职责 | 状态 |
|---|---|---|
| START.md | AI启动入口 | ✅ |
| core/coach-rules.md | 核心规则 | ✅（v1.1需更新） |
| psychology/scale-library.md | 20+量表 | ✅ |
| psychology/stats-guide.md | 10种统计方法 | ✅ |
| psychology/ethics.md | 伦理规范 | ✅ |
| tools/data_cleaner.py | 数据清洗 | ✅已测试 |
| tools/chart_generator.py | 模型图 | ✅已测试 |
| tools/sample_size.py | 开题样本量/功效估算(G*Power等价) | ✅scipy黄金 |
| tools/literature_organizer.py | 文献整理 | ✅已测试 |
| templates/questionnaire-template.md | 问卷模板 | ✅ |
| templates/paper-outline.md | 论文大纲 | ✅ |
| templates/ai-usage-declaration.md | AI声明 | ✅ |
| README/CONSTITUTION/ROADMAP | 项目文档 | ✅（需更新） |
| tests/e2e-test.md | 11个测试用例 | ✅ |

### v1.1 待开发
| 文件 | 职责 | 优先级 |
|---|---|---|
| PROJECT_PLAN.md | 项目计划（本文件） | P0 |
| tools/auto_stats.py | 自动统计（信度/描述/相关/回归+三线表） | P0 |
| workflows/environment-setup.md | 环境搭建傻瓜指南 | P0 |
| workflows/literature-auto-search.md | 文献自动检索 | ✅已写 |
| workflows/paper-reading-guide.md | PDF结构化分析 | P0 |
| workflows/toolchain-guide.md | Zotero+Obsidian工具链 | P1 |
| workflows/data-analysis-auto.md | 自动化数据分析流程 | P0 |
| workflows/proposal-guide.md | 开题报告专项 | P1 |
| workflows/defense-guide.md | 答辩专项 | P1 |
| workflows/writing-guide.md | 写作辅助 | P1 |
| workflows/communication-guide.md | 跟老师沟通全程指南（v1.45新增） | P1 |
| core/ai-literacy.md | AI素养教育 | P1 |
| templates/proposal-template.md | 开题报告模板 | P1 |
| templates/defense-ppt-outline.md | 答辩PPT大纲 | P1 |
| 更新START.md | 整合新模块 | P0 |
| 更新coach-rules.md | 整合工作流调用 | P0 |
| 更新README.md | 新功能说明 | P1 |
| 更新ROADMAP.md | 版本规划 | P2 |

---

## 四、各模块详细规格

### 4.1 工具层规格

**auto_stats.py（自动统计分析）**
- 输入：CSV问卷数据 + 量表题目配置
- 功能：
  1. 数据画像（样本量、变量类型、缺失率）
  2. 描述统计（均值、标准差、最小最大值）
  3. 信度分析（Cronbach's α，删题建议）
  4. 相关分析（Pearson相关矩阵+显著性标记）
  5. 回归分析（线性回归，输出β、t、p、R²）
- 输出：控制台结果 + CSV三线表
- 依赖：优先纯标准库实现；高级统计用scipy（缺失时给降级方案）
- 必须实际测试通过

**paper_search.py（英文文献检索）**
- 数据源：OpenAlex（默认，免费无key）、Semantic Scholar
- 功能：检索、按被引排序、导出CSV、标记开放获取链接
- 依赖：纯标准库urllib
- 必须实际测试通过

### 4.2 工作流层规格

每个workflow文件统一结构：
1. 这个阶段做什么、产出什么
2. 前置条件
3. AI操作步骤（含虚拟电脑/脚本调用时机）
4. 学生需要自己做的部分
5. 检查清单（阶段完成标准）
6. 常见问题

**environment-setup.md**
- Python安装（Windows，勾选PATH，验证安装）
- JASP安装（免费统计软件，心理学推荐）
- Zotero安装（文献管理）
- Obsidian安装（笔记写作）
- 每个软件：下载地址、安装步骤截图位置说明、验证方法、常见报错
- 不要求一次全装，按阶段需要装

**paper-reading-guide.md**
- IMRaD结构化提取模板（研究问题/设计/样本/工具/统计/发现/贡献/局限/与本研究关系）
- 批量文献对比矩阵
- 研究空白分析方法
- AI读PDF的正确方式（不臆测、引用原文、标注页码）

**data-analysis-auto.md**
- 数据分析完整流程（清洗→反向计分→信效度→共同方法偏差→描述→相关→中介）
- 哪些AI自动跑（auto_stats.py）、哪些用JASP/SPSS图形界面（中介PROCESS）
- 结果解读和论文表述
- 三线表规范

**toolchain-guide.md**
- Zotero：导入文献、PDF管理、标注
- Obsidian：建库、文件夹结构、Zotero Integration插件配置
- 联动：一键导入文献笔记、插入引用、生成参考文献
- 用Obsidian写论文的工作流

**proposal-guide.md**
- 开题报告结构（选题依据、文献综述、研究方案、创新点、进度安排、参考文献）
- 开题PPT要点
- 开题答辩高频问题和回答策略
- 配套proposal-template.md

**defense-guide.md**
- 答辩PPT结构（10-15页，每页内容、字数、配图）
- 5-10分钟发言稿
- 20个高频问题库（意义/方法/结果/局限/创新）
- 模拟答辩流程
- 配套defense-ppt-outline.md

**writing-guide.md**
- 各章节写作要点和字数分配
- 学术语言规范（避免口语化、AI味）
- 引用格式（GB/T 7714）
- 格式检查清单
- 查重和AI检测应对

### 4.3 AI素养模块（ai-literacy.md）
- AI能做什么/不能做什么（去魅）
- 如何有效提问（角色、任务、材料、要求四要素）
- AI幻觉识别（文献、数据、量表必须核实）
- AI的风险（隐私、依赖、学术诚信）
- 正确的人机协作观（AI是助手不是替身）

---

## 五、今晚任务执行顺序

按依赖关系排序，逐项执行，每项完成后更新状态：

1. **P0-PLAN**：写PROJECT_PLAN.md ← 当前
2. **P0-TOOL1**：写auto_stats.py
3. **P0-TEST1**：测试paper_search.py（实际联网调用）
4. **P0-TEST2**：测试auto_stats.py（用测试数据）
5. **P0-WF1**：写environment-setup.md
6. **P0-WF2**：写paper-reading-guide.md
7. **P0-WF3**：写data-analysis-auto.md
8. **P1-WF4**：写toolchain-guide.md
9. **P1-WF5**：写proposal-guide.md + proposal-template.md
10. **P1-WF6**：写defense-guide.md + defense-ppt-outline.md
11. **P1-WF7**：写writing-guide.md
12. **P1-CORE**：写core/ai-literacy.md
13. **P0-UPDATE**：更新START.md、coach-rules.md
14. **P1-UPDATE**：更新README.md、ROADMAP.md
15. **P0-VERIFY**：全量检查文件完整性、脚本可运行性
16. **P0-GIT**：Git提交v1.1
17. **P2-REVIEW**：系统化查漏补缺，补充遗漏
18. **P2-GIT2**：如有补充，再次提交

---

## 六、验收标准

### 功能验收
- [ ] 所有Python脚本在干净环境能运行（只依赖标准库或明确提示装包）
- [ ] paper_search.py能真实联网返回文献
- [ ] auto_stats.py能对测试数据输出正确统计结果和三线表
- [ ] 每个workflow文件结构完整、步骤可执行
- [ ] START.md能引导AI找到所有模块
- [ ] coach-rules.md覆盖所有阶段的工作流调用

### 质量验收
- [ ] 无编造的文献、量表、数据
- [ ] 所有软件下载地址、操作步骤准确
- [ ] 统计方法描述与stats-guide.md一致
- [ ] 学术诚信红线贯穿所有文件
- [ ] 小白能看懂（无未解释的术语）

### 安全验收
- [ ] 脚本只在项目目录操作
- [ ] 无删除、无系统级安装、无不明网络请求
- [ ] 账号密码由学生自己输入
- [ ] 工具调用有告知-确认-保护三步

---

## 七、约束与原则

1. 只在 `E:\毕业论文\thesis-ai-coach-project\` 目录内操作，不动其他文件
2. 不运行不知名脚本，所有脚本自己写、自己测试
3. 所有事实性信息（量表、软件、统计方法）必须准确，不确定的标注"需核实"
4. 客观精准实用，不写空话
5. 学生主体，AI引导不代写
6. 每完成一个模块更新todo状态
7. 遇到错误先解决，不跳过；同一方法失败两次换方案

---

## 八、版本规划与实际进展

> **开发方法论（强制）**：所有功能推进必须遵守根目录 `DEVELOPMENT.md` 的九阶段门
> （分析→调研→查找→学习→方案→实现→测试→文档→发布）。计算类功能须有解析解或
> Wolfram/JASP/SPSS 黄金对照证据；每版在全新解压副本端到端验证后才打包。调研可用
> github-remote 搜成熟实现，算法验证用 wolfram，推送远程默认私有且不得含学生数据。

> **v1.0 – v1.53 的逐版进展已合并到 [CHANGELOG.md](CHANGELOG.md)**（单文件 · 日期标签 · 版本倒序），此处不再重复。

- **v2.0**（远期）：本地知识库向量检索、实验/质性研究支持、多学科扩展
- **v3.0**（远期）：网页应用、社区化

### 当前工具层清单（tools/，共8个脚本）

| 脚本 | 作用 | 依赖 |
|---|---|---|
| wjx_preprocess.py | 问卷星原始答卷→标准数字表（编码/用时/文本选项/列映射报告） | 标准库 |
| data_cleaner.py | 无效问卷检测（用时过短/规律作答/全同） | 标准库 |
| auto_stats.py | 人口学频数、反向计分、α+逐题CITC/删题α题项分析表、结构效度(KMO/Bartlett/载荷)、`--efa`完整探索性因子分析(多因子+Varimax+Horn平行分析+自动碎石图)、Harman、量表总分、描述统计(偏度/峰度正态性)、M/SD/相关/α对角整合三线表、人口学差异(Levene方差齐性+独立样本t/Welch t/单因素ANOVA/Welch ANOVA+d/η²+Bonferroni，不齐提示Games-Howell)、多元回归(含容差/VIF共线性诊断)、Bootstrap中介模型4/6、调节效应模型1(中心化交互项+±1SD简单斜率+Bootstrap CI+简单斜率图) | 标准库（碎石图/简单斜率图可选matplotlib，缺失自动降级） |
| generate_demo_data.py | 生成内置链式中介的可复现模拟数据供练手（严禁写进论文） | 标准库 |
| paper_search.py | 英文学术文献检索（OpenAlex/Semantic Scholar，免费无key） | 标准库+联网 |
| literature_organizer.py | 文献去重、分类、导出 | 标准库 |
| chart_generator.py | 研究模型图/路径系数图 | matplotlib |
| menu.py | 中文统一菜单（配合「启动工具箱.bat」，支持拖拽） | 标准库 |
