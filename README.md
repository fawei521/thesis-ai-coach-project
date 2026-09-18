# Thesis AI Coach — 心理学毕业论文 AI 助手（超级向导）

> 一个AI可读取的毕业论文全程助手。学生下载后交给AI，AI作为陪你做毕业论文的 AI 助手/学习伙伴（不是老师、不是虚拟伴侣），从选题、开题、文献、问卷、数据分析、写作到答辩全程引导，并能自动检索文献、清洗数据、跑统计、生成重点文献卡片、图表和报告。

## 这是什么

这不是一个需要安装的软件，而是一个**AI可读取的项目包**。你把这个文件夹交给AI（豆包、ChatGPT等），AI读取 `START.md` 后自动成为你的毕业论文 AI 助手（一个好用的学习搭档，不自称老师）。

它有虚拟电脑（能操作网页）、自动化脚本（能跑统计、检索文献）、专业知识库（量表、统计、伦理），是一个覆盖论文全程的"超级向导"；它给你稳定的陪伴和支架，但鼓励你越来越独立、不制造情感依赖。

## 适合谁

- 心理学专业本科生
- 要做实证研究（问卷类）毕业论文
- 电脑小白也能用（手把手教装软件、跑工具）
- 想从选题到答辩全程有人带

## 怎么用（3步）

> 完全不懂电脑？先看 **`QUICKSTART.md`（快速上手）**，照着点就行。

1. **下载**整个项目文件夹，解压到电脑
2. **交给AI**：打开AI对话，上传整个文件夹（或 `START.md`）
3. **开始**：AI自动问你题目、进度、风格偏好，然后全程引导

你只需要跟AI说话。需要装软件、跑脚本、检索知网时，AI会一步步带你，或开虚拟电脑帮你做。不想记命令就双击「启动工具箱.bat」。换对话时把 `我的工作区/我的论文进度.md` 发给AI即可无缝续接。你自己的文献、数据、结果统一放进 `我的工作区/`（已建好分类子目录）。

> **两种使用形态**：① **完整版**（本文件夹，推荐）——含自动化脚本与知识库，按上面 3 步使用；
> ② **豆包 Skill 轻量版**（`doubao-skill/` 目录，Skill v1.3）——可安装到豆包技能目录，只保留分阶段引导协议、身份陪伴边界、鼓励系统与参考资料，**不含脚本**，并对手机做了原生适配，适合不想下载整个项目包、或主要在手机上推进的同学；需要自动化时轻量版会指引回到完整版。两版学术口径一致。

## 全程能力

| 阶段 | AI能帮你做什么 |
|---|---|
| 选题 | 给选题方向、验证创新性、检索英文文献 |
| 开题 | 开题报告模板、开题PPT、模拟开题问答 |
| 文献 | 自动操作知网检索、英文API检索、PDF结构化分析、研究空白梳理 |
| 量表 | 24组常用量表对比（含AI依赖、NSSI、孤独、反刍，以及DASS-21、压力知觉PSS-10、应对方式SCSQ、情绪调节ERQ、自我控制SCS、核心自我评价CSES、生活满意度SWLS、基本心理需要BPNS、社交媒体成瘾BSMAS等），信效度信息、问卷生成 |
| 数据 | 问卷星预处理、自动清洗（注意力检查题/长直线/低变异/高缺失/时长，附剔除报告）、反向计分、算总分 |
| 分析 | 一键跑人口学频数/信度α+McDonald ω+题项分析(CITC/删题α)+分半信度(Spearman-Brown/Guttman λ4)/结构效度KMO/自编量表完整EFA(多因子+Varimax+平行分析+自动碎石图)/Harman/描述统计(含偏度峰度正态性)/相关矩阵+α对角整合三线表并自动出下三角相关热图(系数+显著性星号、对角Cronbach α,支持--spearman秩相关、--partial控制性别年级等的偏相关)/人口学差异(Levene方差齐性+独立样本t/Welch t+单因素ANOVA/Welch ANOVA+Cohen d/η²+Bonferroni事后；偏态/有序时--nonparametric给Mann-Whitney U/Kruskal-Wallis H非参数检验)/人口学交叉卡方χ²+Cramér's V(分类×分类,Yates/Fisher提示)/回归(含容差/VIF共线性诊断)/Bootstrap中介(模型4/6)/调节效应(模型1中心化交互项+±1SD简单斜率+简单斜率图)、HTMT区分效度(原始问卷数据直算+Bootstrap 95%CI)、开题样本量功效估算(sample_size.py，G*Power等价)、生成三线表、画模型图，JASP/SPSS仅复核 |
| 写作 | 大纲、各章节要点、语言润色、格式检查、去AI味 |
| 答辩 | PPT大纲、发言稿、24个高频问题、模拟答辩 |

## 自动化工具（tools/）

- `menu.py` + 根目录「启动工具箱.bat」 — **零门槛入口**，双击看中文菜单，文件可拖进窗口
- `wjx_preprocess.py` — 问卷星原始答卷预处理（中文表头/文本选项/"2分3秒"用时→标准数字表，附列映射报告）
- `paper_search.py` — 检索英文学术文献（OpenAlex/Semantic Scholar 免费API，无需key，返回真实文献和下载链接）；支持多组近义词（`--queries "词1;词2"`）、`--source all` 双源、`--min 90` 逐词翻页去重凑齐约90篇候选池
- `auto_stats.py` — 自动统计分析（人口学频数表、反向计分、信度α+McDonald's ω(单因子PAF,写入_信度分析.csv)+逐题CITC/删题α题项分析表+分半信度(前后半/奇偶分半,Spearman-Brown与Guttman λ4,导出_信度分析.csv)、结构效度KMO/Bartlett/因子载荷、`--efa`完整探索性因子分析(主成分+Varimax旋转+共同度+交叉载荷+Horn平行分析定因子数+自动碎石图PNG)、Harman共同方法偏差、量表总分、描述统计(偏度/峰度正态性)、M/SD/相关矩阵/α对角整合三线表(并自动出下三角相关热图_相关热图.png：下三角相关系数+显著性星号、对角Cronbach α、上三角留白，--spearman时为秩相关热图)、人口学差异(Levene方差齐性+独立样本t/Welch t/单因素ANOVA/Welch ANOVA+Cohen d/η²+Bonferroni事后，不齐提示Games-Howell)、多元异常值Mahalanobis D²筛查(--mahalanobis按χ²只标记不删除+敏感性分析建议)、多元回归(含容差/VIF共线性诊断)、Bootstrap中介模型4/6、调节效应模型1(中心化交互项+W均值±1SD简单斜率+Bootstrap CI，导出_调节效应.csv并出_调节效应_简单斜率图.png)、`--nonparametric`非参数差异(偏态/有序时2组Mann-Whitney U报U/z/p/r、多组Kruskal-Wallis H报H/df/p/ε²，事后引导Dunn)、`--spearman`秩相关、`--partial "性别,年级"`偏相关(控制混淆后的净相关矩阵+_偏相关.csv)；自动对人口学分类列两两做卡方独立性检验(分类×分类,χ²/df/p/Cramér's V,2×2 Yates校正,期望<5提示Fisher,导出_卡方检验.csv)；绘图（相关热图、碎石图、简单斜率图）为可选依赖，未装matplotlib不影响数值结果）
- `generate_demo_data.py` — 生成内置链式中介的模拟问卷数据（练手/测试，严禁写进论文）
- `data_cleaner.py` — 问卷数据清洗（识别无效问卷：时长过短/长直线/低变异SD/高缺失/注意力检查题答错，导出清洗后数据＋剔除明细报告）
- `literature_organizer.py` — 文献去重分类（UTF-8/GBK 都能读，可直接吃检索导出的 CSV）
- `literature_cards.py` — 重点文献卡片网页：检索/整理 CSV 自动去重、选出重点，生成手机友好的单文件 HTML（搜索/分类/⭐重点/点开看摘要），是"先读哪篇"的导航
- `chart_generator.py` — 研究模型图
- `sample_size.py` — 开题样本量/功效估算（G*Power 等价：相关/回归R²/R²增量/ANOVA/独立两样本t/配对(单样本)t，非中心F精确+三档效应量速查+无效卷冗余建议）
- `webpage_preview.py` — 学生自己做网页时的**本地预览器**（纯标准库静态服务器；只读、不上传、不越出指定目录，默认只绑本机；`--lan` 后手机可看）
- `anonymize_data.py` — **数据去标识化/隐私闸**（发给AI/上传/给外校前：自动假名化或删除姓名、学号、手机、邮箱、身份证、微信/QQ、IP、住址等直接标识符，表头没写明的按内容模式识别；对性别/年级/专业/生源组合做 k-匿名体检；只读原文件、另存新文件，可生成单独保管的假名对照表用于前后测配对）
- `effect_size.py` — **效应量换算与复核**（写结果时由两组均值标准差或 t 值算 Cohen's d/Hedges' g/配对 d_z，由 r、n 算 Fisher z 置信区间并换算 d，由 F 算偏 η²/η²/ε²，由 χ² 算 Cramér's V/φ，支持 r↔d 互转；纯标准库，阈值口径 .1/.3/.5、.2/.5/.8、.01/.06/.14 与 stats-guide 一致）
- `validity_cr_ave.py` — **聚合/区分效度计算**（模式1：CFA 后由标准化因子载荷算组合信度 CR、平均方差抽取 AVE、√AVE，并结合因子间相关做 Fornell-Larcker 判定，支持手动参数或载荷/相关 CSV，可另存 `_聚合区分效度.csv`；模式2：`--htmt 数据.csv --scales scales.txt` 直接由原始问卷数据算 HTMT 异质-单质比率与 Bootstrap 95%CI，导出 `_HTMT区分效度.csv`；纯标准库，载荷须来自真实 CFA 输出、不得为达标改数）
- `item_analysis.py` — **预试问卷项目分析**（按量表总分取高/低各 27% 逐题做独立样本 t 得决断值 CR，并给均值标准差、CITC 校正项总相关、删题后 α 与保留/讨论删改判定，导出 `_项目分析.csv`；复用 stats 包，纯标准库，CR 经 scipy 黄金核对；只提示不替学生删题）
- `content_cvi.py` — **自编量表内容效度 CVI**（专家 1-4 相关性评分 → 逐条 I-CVI、机遇校正 κ*、量表 S-CVI/Ave 与 S-CVI/UA，按 Lynn 1986/Polit&Beck 2006 阈值给保留/修改/重审建议，导出 `_内容效度CVI.csv`；纯标准库，仅自编/修订量表需要）
- `reference_formatter.py` — **参考文献格式化**（题录 CSV → GB/T 7714-2015 顺序编码制 [n] 文本：期刊/专著/学位论文/会议/报纸/电子资源六类，作者超 3 人自动截"等/et al"、欧美著者姓全大写名缩写，支持全角标点与 GB/T 7714-2025 姓氏口径开关，吃 paper_search 导出与文献整理表；缺字段标【待补】不伪造、坏输入中文报错；纯标准库，只格式化不生成文献）
- `missing_report.py` — **缺失值分析与 Little's MCAR 检验**（预处理后清洗前：总/逐题缺失率、缺失模式、成列删除完整样本量；EM 多元正态估计后按缺失模式算 Little (1988) T_MLμ 统计量，与 R naniar::mcar_test / Enders (2010) 同口径；p≥.05 可成列删除、p<.05 建议多重插补/FIML；给可直接粘论文的段落，导出 `_缺失值分析.csv`/`_缺失值报告.txt`；纯标准库）
- `mult_compare.py` — **多重比较校正**（Bonferroni/Holm 控制族系错误率 FWER、BH/BY 控制错误发现率 FDR；`--ps` 直给 p 值或读 CSV 的 p 值列（可带名称列），四法同列，与 R `p.adjust`/scipy `false_discovery_control` 同口径；导出 `_多重比较校正.csv`/`_多重比较报告.txt`；纯标准库）
- `paired_compare.py` — **配对设计差异检验**（前后测/两条件：配对样本 t、Cohen's d_z 及近似95%CI、差值 Shapiro-Wilk、Wilcoxon 符号秩（n≤25 无结精确 p，否则结校正/连续性校正 z，SPSS 口径）与 rank-biserial r 效应量；单文件宽表 `--pairs 前:后` 或两文件 `--id 编号`（可配 scales 算均分），支持 `--group/--level` 组内配对；**另支持单样本对标称常数** `--onesample 列 --constant C`（如 Likert 中值 3、常模分，菜单 19 选单样本）；导出 `_配对检验.csv`/`_配对检验报告.txt`；纯标准库）
- `assumption_check.py` — **参数检验前提假设**（t/ANOVA/回归前：Shapiro-Wilk 正态性 W/p（Royston AS R94，3≤n≤5000，与 R/scipy 同口径）、调整偏度/超额峰度及 z、Kline 判据；`--group` 逐组正态＋Brown-Forsythe 方差齐性（Levene 基于中位数）；p<.05 但偏度峰度在 Kline 内给 Bootstrap/Welch 稳健通道，明显偏态指引非参数；给可粘论文段落，导出 `_前提假设检验.csv`/`_前提假设报告.txt`；纯标准库）

**典型数据流水线**：问卷星导出 →（外发前）去标识化 → 预处理 → 清洗 → 一键自动统计（频数/信度/效度/Harman/相关/回归/Bootstrap中介）→ JASP/SPSS复核 → 画模型图

## 学生自己做网页（可选能力）

AI 助手可以引导学生做一个**给自己用**的网页，把手里多而杂的东西变得能检索、能一眼看懂：

| 类型 | 用在哪一步 |
|---|---|
| 文献笔记网页 | 文献检索与精读（几十上百篇要搜要筛） |
| 数据分析结果看板 | 分析完成后，把三线表/热图/中介结果整理成一页 |
| 研究流程 / 模型可视化 | 选题与开题，讲清变量关系与步骤 |
| 量表与问卷速查页 | 选量表、设计问卷时对照 |
| 论文进度看板 | 全程 |

- 引导手册：`workflows/webpage-guide.md`　预览工具：`tools/webpage_preview.py`（菜单第 9 项）
- 学生作品放 `我的工作区/04-网页/`；随包还带了 **4 个现成网页范例**在 `templates/网页范例/`（含一个问答式统计方法选择器）
- 规矩：单文件自包含、不引用外网 CDN、不放个人隐私、内容必须真实可追溯
- ⚠️ **网页不是论文成果**：论文正文、结果、讨论仍必须学生自己写

## 工作流手册（workflows/）

- `environment-setup.md` — Python/JASP/Zotero/Obsidian零门槛安装
- `literature-auto-search.md` — 知网浏览器自动化 + 英文API检索
- `paper-reading-guide.md` — 论文PDF的IMRaD结构化分析
- `toolchain-guide.md` — Zotero+Obsidian文献管理工具链
- `data-analysis-auto.md` — 数据分析全流程
- `proposal-guide.md` — 开题报告专项
- `defense-guide.md` — 毕业答辩专项
- `writing-guide.md` — 论文写作辅助
- `communication-guide.md` — 跟老师沟通全程指南（节奏、12个场景话术、反馈解读、礼仪、留痕）
- `webpage-guide.md` — 引导学生自己做网页（五类网页、硬规矩、七步流程、三闸检查）

## 专业知识库（psychology/）

- `scale-library.md` — 16种心理学常用量表（题数、维度、信度、出处，含AI依赖、NSSI等新主题）
- `stats-guide.md` — 常用统计方法的SPSS/JASP/PROCESS操作步骤（信效度、共同方法偏差、相关与差异、中介/调节、网络分析、功效分析等）
- `missing-imputation-guide.md` — MCAR 被拒绝/缺失较多时的多重插补（SPSS MI、R mice）与 FIML（AMOS）照做步骤、Rubin 池化公式、敏感性分析与论文模板
- `ethics.md` — 研究伦理（知情同意、未成年人、敏感话题）

## 4种语气风格（默认不套人设）

自然（默认，就是一个专业、不端着的 AI 助手，不套任何人设）/ 简洁直接（少寒暄、给结论）/ 温和耐心（慢一点、多安抚）/ 活泼热情（轻快有感染力，但不撒娇、不制造依附）。说"语气换成XX"随时切换；AI 始终不自称老师、不扮演虚拟伴侣。

## 3种难度

入门（手把手）/ 进阶（给方向）/ 专家（只挑毛病）。

## 鼓励式反馈（默认打开，可随时关闭）

AI 会结合你当下的状态和任务难度，**自然地给具体肯定**（夸你做对的动作和判断，不夸天赋、不空夸、不堆砌），反馈按"具体肯定 → P0/P1/P2 分级问题 → 一个最小下一步"三段走，学术问题（P0）绝不和稀泥。
三档可随时口语切换：**标准（默认）/ 精简（只在过关、开题、初稿等大节点夸）/ 关闭（完全不要夸奖，只要客观反馈）**——说一句"关闭鼓励""鼓励精简一点""开启鼓励"即可，设置记在进度卡里，换对话也不丢。焦虑、被批评、结果不显著时有挫折应对流程；陪伴稳定但不越界，发现你越来越依赖 AI 时会温和地把你拉回真实人际与学校资源。

## AI不会做什么

- 不替你写论文正文、不编造文献和数据
- 不替你做决定（给选项让你选）
- 不碰你的账号密码：**知网/图书馆登录一律你自己在浏览器里输入**，AI 不索取、不代填、不保存，也不会去读任何写着密码的文件（即使你主动说"你拿去用"也会被拒绝）
- 不运行来源不明的脚本、不违反学术规范

## 项目结构

```
thesis-ai-coach-project/
├── START.md                  # AI入口（先读这个）
├── AGENTS.md                 # 自动化 AI 助手入口（支持 AGENTS.md 约定的工具会自动读）
├── QUICKSTART.md             # 学生快速上手（电脑小白看这个）
├── 启动工具箱.bat             # 双击打开中文工具菜单（无需记命令）
├── PROJECT_PLAN.md           # 项目计划
├── CHANGELOG.md              # 版本历史（单文件 · 日期标签 · 版本倒序）
├── LICENSE                   # 授权条款（免费非商用，条款以 CONSTITUTION.md 为准）
├── requirements.txt          # 可选依赖（不装也能跑，只是不出图）
├── doubao-skill/             # 豆包 Skill 轻量版（可安装技能：SKILL.md+12阶段+引导协议+身份陪伴边界+鼓励系统+手机原生适配+validate.py 自检）
├── README.md / CONSTITUTION.md / ROADMAP.md
├── DEVELOPMENT.md            # 维护者强制开发流程（九阶段门+测试金字塔，改功能前必读）
├── 我的工作区/                # 学生自己的文件：01-文献PDF/02-问卷数据/03-分析结果/04-网页 + 我的论文进度.md
├── core/                     # AI规则（coach-rules）+ 身份陪伴边界（companionship）+ 引导反馈协议 + 鼓励系统 + AI素养
├── workflows/                # 10个阶段工作流手册
├── tools/                    # 21个脚本（含统一菜单menu.py、重点文献卡片literature_cards.py、网页预览器、去标识化anonymize_data.py、效应量换算effect_size.py、聚合区分效度validity_cr_ave.py、预试项目分析item_analysis.py、内容效度content_cvi.py、参考文献格式化reference_formatter.py、缺失值分析missing_report.py、前提假设assumption_check.py、配对检验paired_compare.py、多重校正mult_compare.py）+ stats/ 统计实现包（9个模块）
├── psychology/               # 量表/统计/伦理知识库
├── templates/                # 问卷/大纲/开题/答辩/进度卡/AI声明模板 + 网页范例/
└── tests/                    # full_e2e.py 一键全量回归、consistency_check.py 文档↔代码一致性自检、专项测试与测试数据
```

> 维护者/接手者：改动后运行 `python tests/full_e2e.py`（约3-5分钟，600 项断言，自动备份恢复测试数据），退出码 0 才算通过；学生日常使用不需要跑。

## 版本

**当前版本：v1.72**（2026-09-18）配对检验扩展单样本模式（完整版；doubao-skill 本轮无改动）
- **单样本检验闭环**：`paired_compare.py` 新增 `--onesample 列 --constant C`（菜单第19项选"单样本"），一组分数对标称常数（Likert 中值 3、常模分、理论值）的单样本 t/Wilcoxon 一次给齐；数学上等价于 d=x−C 的配对检验，前提（差值正态）、d_z、rank-biserial r、有结小样本警示与配对模式完全同构；支持 `--group/--level`，控制台/论文段落/CSV 备注按单样本口径呈现
- **黄金验证**：300 组模拟（n=5…100，连续/含结）对 scipy `ttest_1samp`/`wilcoxon` 零误差（t 4.3e-14、p 1.3e-13、d_z 4.9e-15、校正 z 1.8e-15）；手工例 x=[3,4,5] vs 3 → t(2)=√3；full_e2e 589→600 项；菜单因 700 行硬约束同步瘦身
- **边界**：与中值比较只能说明"偏离中点"，不能声称干预效果（文档明示）；坏参数四类互斥校验（缺常数/缺列/混 scales/常数无 onesample）rc=1；配对模式零回归

**上一个版本：v1.71** 多重插补/FIML 教学指引闭环（完整版；doubao-skill 无改动）：
- **缺失处理"最后一公里"补齐**：新增 `psychology/missing-imputation-guide.md`——缺失机制×缺失率决策树（何时成列删除可接受、何时必须 MI/FIML）、SPSS 多重插补照做步骤（PMM 预测均值匹配、m=20+、自动池化与 PROCESS 不池化的两条出路）、AMOS FIML（勾选估计均值与截距即自动启用＋辅助变量）、R mice 代码模板与 Rubin 池化公式（T=Ū+(1+1/m)B、校正自由度）、MNAR 敏感性分析（delta/tipping point）、方法/结果/局限三章论文模板
- **接线**：`missing_report.py` 在拒绝 MCAR 的控制台解读与可粘论文段落中直接指向该指南；stats-guide、data-analysis-auto 第1.5步、START 查证表、README 知识库列表同步登记
- **红线先行**：禁止均值/LOCF/单点回归插补当完整数据、禁止看结果换插补方法、插补模型须含全部分析变量与辅助变量、量表题均替代只作描述性处理、成对删除不推荐；关键菜单/方法经 IBM 官方手册核对（PMM、默认 m=5、AMOS FIML 勾选位置）
- **验证**：full_e2e 577→589 项（指南内容静态断言＋四处接线＋MAR 场景控制台/报告指引）；consistency（Markdown 41 个）、validate、全量 py_compile 全绿；工具脚本与菜单项数不变（21 个/20 项）


**更早版本（v1.64 及以前）的逐版说明全部见
[CHANGELOG.md](CHANGELOG.md)** —— 本 README 自 v1.57 起只保留当前版本与上一版本的摘要，
不再往下堆积版本正文（同一版本的说明只维护 CHANGELOG 一处，避免两处漂移、README 无限变长）。

> 维护者：改动后必须跑 `python tests/full_e2e.py`（约 3-5 分钟，退出码 0 才算通过）
> 与 `python tests/consistency_check.py`（文档↔代码一致性）；发布流程见 `DEVELOPMENT.md`。

## 致谢

设计思路参考了 paper-conductor（三道闸）、Academic Research Skills（skill分工）、cnki-skills（知网自动化）、OpenAlex/Semantic Scholar（免费学术API）等开源项目；鼓励反馈系统的设计依据正强化、成长型思维（Dweck）、反馈干预理论（Kluger & DeNisi）与自我决定理论（Deci & Ryan）。