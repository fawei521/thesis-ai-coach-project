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
│  ├── coach-rules.md          角色/人格/难度/阶段/红线  │
│  ├── coaching-protocol.md    每轮引导/三段式/P分级/门禁 │
│  ├── encouragement-guide.md  鼓励三档(默认可关)/奖赏    │
│  └── ai-literacy.md          AI素养/提问/幻觉/诚信      │
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
| psychology/scale-library.md | 29 组量表（10 大类，v1.60） | ✅ |
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

> 注：上表为早期快照，实际工具以 `AGENTS.md` 文件地图与 `tools/` 目录为准（v1.57 为 10 个脚本，v1.58 新增 `literature_cards.py` 后为 11 个，v1.59 新增 `anonymize_data.py`、`effect_size.py` 后为 13 个、菜单 12 项；v1.60 新增 `validity_cr_ave.py`、`item_analysis.py`、`content_cvi.py` 后为 16 个、菜单 15 项）。

---

## 九、v1.58 优化：定位/陪伴、多词检索、90 篇候选池与卡片、手机原生适配

> 启动日期 2026-09-17。起因：实际使用反馈四条——①鼓励"热情的太夸张、标准的太冷淡"，且 AI 不应以"老师/导师"自称、不应被工作流脚本绑死；②整体定位要从"严肃老师"调整为"有稳定陪伴感的 AI 工具/学习伙伴"，并参考 AI 情感依赖/数字伙伴相关研究把握陪伴边界；③检索（文献与量表）不能只搜一个词就下判断，要用多组近义/同义词综合判断；④文献自动搜集量太少，候选池至少 90 篇，并把重点做成手机友好的网页卡片推荐阅读；⑤手机版本质是把电脑版套壳，要做真正的手机原生适配。

### 9.1 设计原则（本轮总纲）

1. **AI 是工具，不是老师**：对学生说话不自称"导师/老师"，自我定位为"陪你把论文做完的 AI 助手/学习伙伴"。产品包保留 Thesis AI Coach 名称，但**第一人称身份与开场口径统一为 AI 助手**。
2. **工作流辅助而非操控**：规则给原则、边界与门禁，不逐句喂台词；鼓励只规定"要鼓励、鼓励什么、不能怎么鼓励"，具体措辞由 AI 结合**学生当下状态与任务难易**自然发挥，保留豆包式自然语气与灵活性。
3. **稳定但不越界的陪伴**（循证，来源见 `core/companionship.md`）：零评判承接情绪→把人带回具体任务；支持自主感/胜任感/归属感（自我决定理论）；支架可撤除（脚手架而非拐杖，PISA 2025）；**不制造情感依附**——不说"我永远在/只有我懂你"、不发展虚拟亲密关系、不替代现实连接；出现依赖信号温和拉回现实支持；危机一律转真人/热线。国内《人工智能拟人化互动服务管理暂行办法》（2026-04）禁止向未成年人提供虚拟伴侣等虚拟亲密关系服务，本工具服务学业、不做陪伴拟人化越界。
4. **检索用概念矩阵，不单词下判断**：每个核心概念至少 3 个同义/近义/上下位/缩写/中英对译词，概念内 OR、概念间 AND，多库交叉、去重后综合判断；量表检索同理。方法学依据：系统综述的 concept grid / logic grid 法。
5. **候选池要大、精读要少而精**：自动检索目标为**候选题录池 ≥90 篇**（多词多源去重后的题录/摘要，不等于 90 篇都引用）；再分级筛重点 10–20 篇精读，实际引用按质量。重点由 `literature_cards.py` 生成单文件卡片网页推荐。
6. **手机原生**：按"手机能做什么"重写路径，而非搬运电脑步骤；跑脚本/虚拟电脑/本地软件（JASP/SPSS/PROCESS）明确回电脑，并提供"设备交接单"让手机↔电脑无缝切换。

### 9.2 改动清单（按工作流，小步提交）

- **A 定位/陪伴/鼓励**：新增 `core/companionship.md` 与 `doubao-skill/references/companionship.md`（工具定位、稳定陪伴原则、反依附边界、依赖信号与拉回、危机转真人、带来源；用户点名的《数字伙伴：AI 陪伴下的青少年情感补偿机制研究》未在公开库核到原文，按反虚构规则标"需核实"，不杜撰）；重写两份 encouragement-guide（原则化/自然化，保留三档与切换、P0 不包装、里程碑、挫折协议、禁夸天赋/攀比、理论出处，删逐句台词与机械计数）；coach-rules §一/§三/§十二与阶段0、两份 coaching-protocol、START、SKILL、personalities、stage-0、进度卡同步去老师化与"默认自然+三种可选语气（简洁直接/温和耐心/活泼热情，后者降温）"。
- **B+C 工具**：`paper_search.py` 支持 `--query` 重复、`--queries`、`--source all`、`--min N`，多词多源去重合并，输出加来源/命中词/日期列，纯函数化以便无网络单测，不足目标非静默提示；新增 `literature_cards.py` 生成同范例视觉语言的单文件手机优先卡片页（搜索/分类/⭐重点/详情，无 CDN、转义、无隐私、带来源声明）；菜单加第 10 项；START/AGENTS/README/webpage-guide（归入既有"文献笔记网页"类，不新增第六类）/literature-auto-search/检索记录模板接线。
- **B 文档**：literature-auto-search、coach-rules 阶段2/4、scale-library、skill stage-2/stage-4 写清概念矩阵、≥90 候选池与精读/引用之分、量表多词交叉核验后才能判"无现成量表"。
- **D 手机**：mobile-guide 重写为手机优先手册（保留既有边界令牌）+ 设备交接单 + 手机端知网/英文/PDF/进度卡/卡片做法 + 无 Python/无虚拟电脑/无本地软件不承诺清单；SKILL 手机节手机优先；stage-0/2 补手机分支；build_mobile_single 让边界与陪伴文档先于阶段加载并纳入 companionship。
- **测试与发布**：full_e2e 演进旧断言（语气标签、必读六份、菜单 /10）并新增多词聚合/--min/卡片/陪伴令牌/交接单确定性断言；两份行为自测补连续编号用例；validate 补新文件/令牌；版本 v1.58 / Skill v1.3，更新两处 CHANGELOG、README、AGENTS；全门禁绿 + 干净副本验证 + 同步 `.user_skills` + 重生成手机合并单文件 + 更新发布包。**只动本项目与该 skill 目录；显式 `git add` 指定文件，不卷入并行文献会话的工作区产物。**

## 十、v1.59 优化：数据隐私闸、多元异常值严谨处理、效应量必报、量表库与网页范例加厚

> 启动日期 2026-09-18（凌晨自主推进）。起因：问卷实证全流程三类高频风险——①数据外发（发给 AI/上传/给外校）前的隐私泄露；②多元异常值"一删了之"、人为改变结论；③结果章只报 p 值、缺效应量与置信区间，且量表候选面偏窄、学生面对多种检验不知如何选择。本版在 v1.58 之上做加固，不改动 v1.58 的定位/陪伴/检索/卡片/手机能力。

### 10.1 设计原则（本轮总纲）

1. **隐私默认保护（privacy by default）**：数据离开本机前先去标识化；工具只读原文件、另存新文件，假名对照表单独保管、可选择不可复原；去标识化降低再识别风险但不替代伦理审查，如实说明局限。
2. **异常值只标记、不静默删除**：任何可能改变样本与结论的操作都不自动执行，改为报告标记＋敏感性分析建议，决定权交还学生并要求留痕。
3. **效应量与置信区间必报**：显著性不等于重要性；工具只做"由真实检验输出换算"，绝不反推、不编数，不显著也如实报告，阈值口径与 `stats-guide.md` 单源一致。
4. **知识/范例加厚但口径不漂移**：新增量表的题数/计分/分级逐条联网核查、有出入标注以原文为准；网页范例延续单文件、零外链、数据与界面分离、"范例请勿直接使用"双标注的既有规范。
5. **小步可回退、纯标准库交付**：每个增量独立提交、配确定性 e2e 断言；新增脚本只用 Python 标准库（绘图仍为可选依赖），不引入运行时第三方依赖。

### 10.2 改动清单（按工作流，小步提交）

- **隐私闸**：新增 `tools/anonymize_data.py`（菜单第 11 项），直接标识符假名化/删除＋内容模式识别、准标识符 k-匿名体检、`--dry-run/--no-key/--columns/--k`、UTF-8/GBK、拒绝覆盖原文件、无标识符友好退出；接线 ai-literacy、data-analysis-auto（外发前隐私闸步骤）、START/QUICKSTART/README/AGENTS。
- **多元异常值**：`tools/stats/regress.py` 增 `mahalanobis_outliers()`/`_chi2_critical()`，`auto_stats.py` 增 `--mahalanobis`/`--mah-alpha`（默认 p<.001，只标记不删除＋敏感性分析建议）。
- **量表库**：`psychology/scale-library.md` 16→24 小节、9 大类，新增 DASS-21、压力知觉、应对方式、情绪调节（过程模型）、自我控制、核心自我评价、生活满意度、基本心理需要，手机/网络成瘾补 BSMAS。
- **网页范例**：新增 `templates/网页范例/04-统计方法选择器/`（问答式决策树，10 问/26 结果，推荐方法＋前提＋应报告统计量/效应量阈值＋脚本与 JASP/SPSS 路径＋留空论文句式＋真实性提醒）。
- **效应量工具**：新增 `tools/effect_size.py`（菜单第 12 项），8 子命令 d/d-t/paired-d/r/r-t/eta/v/convert，给 d/g/配对 d_z 与 95%CI、r Fisher 区间、偏 η²/η²/ε²、Cramér's V/φ、r↔d。
- **合并与测试**：合并 master v1.58（多词检索/90 池/卡片/手机原生/陪伴文档），菜单最终 12 项（卡片 10、去标识化 11、效应量 12）；full_e2e 新增脱敏/Mahalanobis/量表/选择器/效应量断言后 **343 项全过**，consistency_check 退出 0，doubao-skill validate 通过；版本 v1.59（Skill 保持 v1.3，新工具属完整版本体能力）；全门禁绿＋干净副本复验后发布。

## 十一、v1.60 优化：测量学闭环补齐（聚合/区分效度、项目分析、内容效度 CVI、t 样本量）与共同方法偏差加固

> 启动日期 2026-09-18（凌晨自主推进，隔离 worktree 分支 `feat/overnight-privacy-scales`）。起因：v1.59 补齐隐私/异常值/效应量后，问卷测量学链条仍有四个教材必做环节缺工具或只覆盖一半——CFA 后的 CR/AVE/Fornell 要手算、预试决断值 CR 缺失、开题样本量缺最常用的 t 设计、自编量表内容效度 CVI 完全空白。本版在 v1.59 之上补齐，不改动既有统计口径。

### 11.1 设计原则（本轮总纲）

1. **补测量学闭环，不重复造轮子**：新工具复用 `stats/` 子包既有统计量（dataio/reliability/mathx），量表总分计分等已由 auto_stats 覆盖的不再另建；每个新工具只填一个真实缺口。
2. **公式先黄金验证、再固化断言**：CR/AVE、决断值 CR、t 样本量、CVI κ* 全部先用本机 scipy/numpy 或 R 包算例逐位核对，再写进 `full_e2e.py` 硬事实断言，不凭记忆实现统计量。
3. **数字必须来自真实输入**：CFA 载荷、专家评分、效应量都要求来自真实测量模型/专家评定，工具只量化整理，坏参数中文守卫、不抛 Traceback、不得为达标改数。
4. **小步可回退、纯标准库交付**：六个增量各自独立提交、配断言；新脚本只用标准库（`math.comb` 算组合数），不引入运行时第三方依赖。

### 11.2 改动清单（按工作流，小步提交）

- **聚合/区分效度**：新增 `tools/validity_cr_ave.py`（菜单第 13 项），CFA 标准化载荷→CR/AVE/√AVE＋Fornell-Larcker，手动/CSV 双输入，导出 `_聚合区分效度.csv`；注明单因子下 CR 与 McDonald's ω 等价、建议补 HTMT。
- **预试项目分析**：新增 `tools/item_analysis.py`（菜单第 14 项），高低 27% 等方差独立样本 t 决断值 CR（稳定排序）＋CITC＋删题后 α＋判定，复用 stats 包，导出 `_项目分析.csv`。
- **样本量补 t**：`tools/sample_size.py` 借 df1=1 时 t²=F 精确等价新增独立两样本 t（等组取偶）与配对/单样本 t，最小 N 经 `scipy.stats.nct` 逐位核对（独立 d=.5 总 128/每组 64；配对 dz=.5 N=34）。
- **内容效度 CVI**：新增 `tools/content_cvi.py`（菜单第 15 项），专家 1–4 评分→I-CVI/Pc/校正 κ*/S-CVI(Ave、UA)，按 Lynn 1986 与 Polit-Beck 阈值给保留/修改/重审，导出 `_内容效度CVI.csv`；黄金对照 R `contentValidity` 算例（夹具 `tests/test-data/demo_cvi.csv`）。
- **量表库**：`psychology/scale-library.md` 24→29 小节、9→10 大类，新增 PANAS、IRI-C、GQ-6、GHQ-12、PSQI（新开睡眠与心身健康类），全部小节确定性重编号，硬事实逐条联网核查。
- **共同方法偏差**：stats-guide 第四节与 data-analysis-auto 第 5 步补程序控制（Podsakoff 等 2003）与 ULMC、标记变量法（Lindell & Whitney 2001），标明 Harman 仅最宽松事后检验与工具边界。
- **测试与发布**：菜单 12→15 项，工具脚本 13→16 个（含 stats 共 26 实现模块）；`full_e2e.py` 343→**375 项全过**，consistency_check 退出 0（88 CLI 开关/24 csv 后缀无漂移），doubao-skill validate 通过；版本 v1.60（Skill 保持 v1.3）；全门禁绿＋项目外干净副本复验后打 tag。
