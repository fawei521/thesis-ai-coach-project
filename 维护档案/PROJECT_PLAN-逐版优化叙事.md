# PROJECT_PLAN 逐版优化叙事（v1.58 起）

> 原 `PROJECT_PLAN.md` 第 305 行之后的“九、v1.58 优化 …”各节整体搬来，正文一字未改。
> 按 `DEVELOPMENT.md` 的规矩，逐版变更的唯一来源是 `CHANGELOG.md`，这部分与它重复。
> 本目录在 git 里正常追踪（贡献者与 AI 都能查），但被 `.gitattributes` 的
> `export-ignore` 排除在发布包之外：学生只拿到必要文档，完整台账留在仓库。

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
- **测试与发布**：菜单 12→15 项，工具脚本 13→16 个（含 stats 共 26 实现模块）；`full_e2e.py` 343→**377 项全过**，consistency_check 退出 0（88 CLI 开关/24 csv 后缀无漂移），doubao-skill validate 通过；版本 v1.60（Skill 保持 v1.3）；全门禁绿＋项目外干净副本复验后打 tag。

## 十二、v1.62 优化：现代信效度指标补齐（McDonald's ω ＋ HTMT）

> 启动日期 2026-09-18（晚间自主推进，隔离 worktree 分支 `feat/advance-closed-loop`，基于 v1.61）。起因：JASP 默认同时报告 α 与 McDonald's ω、评审对现代信度指标的要求增多；Fornell-Larcker 被 Henseler 等（2015）证明对区分效度问题不敏感，HTMT 成为当代标准，而 v1.60 工具只能建议学生"去 CFA 软件补报 HTMT"，没装 AMOS/JASP 的学生被卡住。本版在纯标准库内补齐两个指标，正式口径仍引导 CFA 软件复核（不越界、不冒充）。

### 12.1 设计原则（本轮总纲）

1. **填真实缺口，不替代专业软件**：ω 用单因子主因子法（PAF）给快速预览，HTMT 用 Pearson 题项相关给教学/预览口径；两者都明确标注 JASP/lavaan/SmartPLS 的正式复核路径与方法差异（CFA-ω、polychoric HTMT/HTMT2）。
2. **公式先黄金验证**：PAF-ω 用已知载荷大样本模拟（还原误差<.001）、τ 等价数据 ω≈α 验证；HTMT 用正交/同因子/中等相关三套模拟验证判定方向；夹具锁定数值后 stdlib 实现与 numpy 逐位对齐。
3. **扩展既有工具而非新增脚本**：ω 进 auto_stats 信度节与 `_信度分析.csv`（学生跑主流程自动得到），HTMT 进 validity_cr_ave 的 `--htmt` 模式与菜单13二选一引导；工具脚本数保持 16、菜单保持 15，降低维护面。
4. **反作弊红线不放松**：HTMT 不达标要求如实报告并做模型处理，明确禁止删题凑数；ω/HTMT 都只接受真实数据，不提供任何"调整到达标"的入口。

### 12.2 改动清单

- **ω（P0）**：`tools/stats/reliability.py` 新增 `_complete_z_matrix()`、`_paf_one_factor()`（SMC 初值、迭代共同度、Heywood 截断）、`mcdonald_omega()`；auto_stats 信度节逐量表打印 ω 与等级、异常低提示，`_信度分析.csv` 新增 `McDonald_ω` 列；样本/题数不足中文"未算"。
- **HTMT（P0）**：`validity_cr_ave.py` 新增 `--htmt/--scales/--boot/--seed/--only-scales` 模式（自动反向计分、完整样本、|r| 均值口径、固定种子百分位 Bootstrap、.85/.90 双门槛＋CI 上限<1、块内相关非正守卫），导出 `_HTMT区分效度.csv`；菜单13改模式1/2引导，主屏提示同步。
- **夹具与测试（P0）**：新增 `tests/test-data/demo_htmt.csv`、`htmt_scales.txt`（正交 4+4 题 n=220）；`full_e2e.py` 390→**404 项全过**（ω 4 项、HTMT 10 项、菜单 1 项；含反向题等价、同因子阴性、三类坏参数守卫）。
- **文档（P1）**：stats-guide 新增 ω 小节与 HTMT 用法块；data-analysis-auto 流程图/第3步/第4步/质量闸；START、README（版本摘要轮换、断言计数）、QUICKSTART、e2e-test（测试61＋清单17/17b）同步；consistency_check 与 skill validate 退出 0。
- **范围控制**：本轮不做分层 ω（hierarchical ω/Schmid-Leiman）、HTMT2 与 polychoric 相关（列入后续候选）；doubao-skill 本轮无改动（手机不跑脚本，口径已在 stats-guide 单一信源）。

## 十三、v1.63 优化：高频量表库再扩充（29→39 组、10→11 大类）

> 启动日期 2026-09-18（晚间自主推进，同分支 `feat/advance-closed-loop`，承接 v1.62）。起因：v1.59/v1.60 后量表库覆盖 29 组，但积极品质（坚毅/自我同情/心理资本）、人际过程（交往焦虑/人际信任/社会比较）、新媒体行为（错失焦虑）、ACT 过程变量（经验性回避）与教育情境（学习投入/学业倦怠）仍有高频缺口。

### 13.1 设计原则（本轮总纲）

1. **只补高频成熟量表、不凑数**：每组给齐题数/维度/计分/反向题/中文版/信度六要素，优先本土验证、本科论文实际高频使用的版本（学业倦怠主推连榕 2005 而非直接上 MBI-SS）。
2. **版本分歧不抹平**：5点/7点锚点、维度题数分配、反向题号有不同记载的，显式写"以所引题本原文为准"，不替学生猜一个版本。
3. **结构变更脚本化**：插入与重编号由确定性脚本完成（类别锚点插入后全文统一重排 1–39），测试以硬事实字符串锁死，避免手工断号。

### 13.2 改动清单

- **量表库（P0）**：`psychology/scale-library.md` 新增 10 组（Grit-S、IAS、ITS、INCOM 全版＋上行 6 题、FoMOs、SCS/SCS-SF、PPQ、AAQ-II、UWES-S±9、连榕学业倦怠＋MBI-SS 备选），新开"十一、学习心理与教育情境类"，全文重编号 1–39。
- **测试（P0）**：`full_e2e.py` 404→**414 项全过**（+10 组硬事实断言；编号/大类断言更新为 39/11）。
- **文档（P1）**：CHANGELOG v1.63 索引与详情、本文件状态表与 §十三、START 版本号、README 版本轮换与断言计数、e2e-test 测试62 同步。
- **范围控制**：本轮无工具脚本改动（16 脚本/15 菜单项不变）；doubao-skill 本轮无改动（量表选择口径在 stage-4 引用本文件，内容扩充不破坏既有口径）；量表正文不附题目，版权与授权纪律不变。

## 十四、v1.64 优化：全流程三轮演练健壮性闭环

> 启动日期 2026-09-18（晚间自主推进，同分支 `feat/advance-closed-loop`，承接 v1.63）。起因：ROADMAP v1.x 挂账"自行完成整个系统测试，走一遍流程生成模拟论文，收集 bug 修改，循环至少三次"。

### 14.1 做法（先演练、再修复、后复验）

1. **学生视角端到端演练**：维护者侧脚本（不入库）从全新目录按真实菜单顺序走全部 15 项，第一轮标准路径 29 步、第二轮边界/坏参数 34 步（GBK、缺失值、小样本、无 scales、非参数族、15 组坏参）。
2. **缺陷分级修复**：5 个真缺陷按 P0/P1 修复，3 个演练脚本字符串误判纠正；同类问题（scales 题项校验）四处统一并下沉共享模块，不各写一份。
3. **修复后干净重跑＋产物链核对**：第三轮全新目录重跑全部步骤，并对照工作流与论文大纲逐节核对工具出口，断档挂账。

### 14.2 改动清单

- **模型图 direct（P0）**：`chart_generator.py` 新增 `--type direct`（2 变量直接效应）；三型变量数不符给交叉引导；`menu.py` 按变量数自动选型并补前置守卫；工作流文档同步。
- **scales 硬校验（P0）**：`stats/dataio.py` 新增 `find_missing_items/assert_items_exist`；`auto_stats.py`、`data_cleaner.py`、`item_analysis.py`、`validity_cr_ave.py`（HTMT）四工具对"文件不存在/题项与数据列不匹配"统一中文硬失败 rc=1，不再静默退化或按部分题计分。
- **坏参数退出码（P1）**：`data_cleaner.py` 四个数值参数手工中文校验（含取值范围）；`effect_size.py` 16 处校验点统一 raise→rc=1；`literature_organizer.py` 空文件/读取失败 rc=1。
- **测试（P0）**：`full_e2e.py` 414→**427 项全过**（+13 回归断言，2 条旧断言收紧到新契约）；三轮演练 29/29、34/34。
- **文档（P1）**：CHANGELOG v1.64 索引与详情、本节、START 版本号、README 版本轮换与断言计数、e2e-test 测试63、ROADMAP 三轮演练挂账勾选、paper-outline 信度处补 ω 同步。
- **范围控制**：工具脚本数/菜单项数不变；doubao-skill 本轮无改动；演练框架与补丁不入库。
- **挂账**：GB/T 7714 参考文献格式化工具——**已在 v1.65 兑现（见 §十五）**。

## 十五、v1.65 优化：GB/T 7714 参考文献格式化闭环

> 2026-09-18 晚间自主推进，同分支 `feat/advance-closed-loop`，承接 v1.64 产物链核对发现的挂账。

### 15.1 背景与做法

1. v1.64 三轮演练后对照论文大纲逐节核对工具出口，唯一定稿断档为参考文献著录。
2. 先联网核查 GB/T 7714-2015 顺序编码制规则（六类文献格式、作者 1-3 全列/≥4 截前三、欧美著者"姓全大写名缩写不带点"、电子资源 [更新日期][引用日期]、DOI 尾随），并确认 GB/T 7714-2025 已发布、外国作者姓氏改为首字母大写，故以 `--name-case 2015|2025` 同时支持两版口径、默认 2015。
3. 黄金用例先行（作者解析 10 例、出处尾部解析、污染题名还原、六类著录、全角），再补 CLI 端到端 16 组场景与 full_e2e 断言，最后接菜单与文档。

### 15.2 改动清单

- **新增 `tools/reference_formatter.py`（菜单第 16 项）**：题录 CSV（paper_search 导出/整理表/13 列模板）→ GB/T 7714-2015 [n] 编号文本；[J][M][D][C][N][EB/OL] 六类；作者多格式解析与三人截断；`--fullwidth`/`--no-number`/`--name-case`/`--access-date`/`--save-template`；缺字段【待补】标注＋警告，坏输入中文 rc=1；UTF-8/GBK 自适应；纯标准库、不联网、不生成文献。
- **整理表污染自愈**：标题列被出处尾部污染时以"原文出处"还原纯题名（中英文各有黄金用例）。
- **菜单与计数**：菜单 15→16 项（15 处步骤标签同步 /16，主屏补提示行）；工具脚本 16→17 个；stats 子包不变。
- **文档**：writing-guide §四重写、START 工具清单与用法、README 工具清单/目录树/版本轮换、AGENTS 文件地图、paper-outline 参考文献节、e2e-test 测试64、本文件。
- **测试（P0）**：`full_e2e.py` 427→**448 项全过**（+21）；黄金用例与 CLI 端到端 16 组场景全绿；consistency_check、doubao-skill validate、全量 py_compile 全绿。
- **范围控制**：doubao-skill 本轮无改动；测试与补丁不入库。

## 十六、v1.66 优化：缺失值分析与 Little's MCAR 检验闭环

> 2026-09-18 晚间自主推进，同分支 `feat/advance-closed-loop`，承接 v1.65 之后的数据准备段断档排查。

### 16.1 背景与做法

1. 清洗器只剔除高缺失个案，方法章还需要"缺失率—缺失模式—机制检验—处理结论"的规范产物，SPSS Missing Values/R naniar 的 Little's MCAR 是常见报告项，工具箱此前无出口。
2. 先联网核查公式口径，发现存在两个版本：均值项 T_MLμ（naniar/misty/Enders，df=Σk_j−k）与含协方差似然项的完整版（SPSS，df=Σ k_j(k_j+1)/2−k(k+1)/2）。下载 naniar 1.0.0 CRAN 源码逐行核对确认其为均值项版；再用 400 次蒙特卡洛模拟比较三种实现口径：均值项一类错误 6.5%（名义 5%）、MAR 检出 98%，(n−1) 无偏协方差完整版严重保守（0.8%），朴素 LR 完整版反保守（45.8%），据此选定均值项口径并在文档注明 SPSS 差异。
3. 黄金验证先行（EM 对 numpy 参照、χ²/df 对照、校准模拟、df 手算），再补 16 组 CLI 场景与 full_e2e 断言，最后接菜单与文档。

### 16.2 改动清单

- **新增 `tools/missing_report.py`（菜单第 17 项）**：描述统计＋EM（D-L-R，ML 除 N）＋Little T_MLμ；导出 `_缺失值分析.csv`（三段式）与 `_缺失值报告.txt`（可粘论文段落）；`--scales/--only/--csv-out/--report/--alpha`；无缺失不出检验、整列缺失/Σ 奇异/不收敛/坏输入统一中文 rc=1；UTF-8/GBK 自适应；纯标准库（复用 stats.dataio/linalg/mathx）。
- **修复的真 bug**：E 步条件回归系数矩阵 Σ_mo 取列误用模式内局部下标（修复后 Σ 误差从 2.30 降到 1.7e-8，MAR 场景恢复收敛）。
- **边界**：只检验不插补，拒绝 MCAR 时指引 SPSS 多重插补/R mice/FIML；显式声明正态假设、不显著≠证明 MCAR、不得改动真实作答。
- **菜单与计数**：菜单 16→17 项（16 处标签同步 /17）；工具脚本 17→18 个；stats 子包不变。
- **文档**：stats-guide 缺失值方法学小节、data-analysis-auto 第 1.5 步（修订 2.3 均值替代旧说法）、START、README、AGENTS、QUICKSTART、e2e-test 测试65、本文件。
- **测试（P0）**：`full_e2e.py` 448→**475 项全过**（+27）；numpy 黄金模拟与 CLI 16 场景全绿；consistency_check、validate、全量 py_compile 全绿。
- **范围控制**：doubao-skill 本轮无改动；测试与补丁不入库。

## 十七、v1.67 优化：参数检验前提假设闭环（正态性 / 方差齐性）

> 2026-09-18 晚间自主推进，同分支 `feat/advance-closed-loop`，承接 v1.66，补齐 t/ANOVA/回归方法章的前提检验断档。

### 17.1 背景与做法

1. 参数检验方法章普遍要求报告正态性（Shapiro-Wilk）与组间方差齐性（Levene/Brown-Forsythe）；此前只有描述统计的偏度峰度 Kline 启发式，正式检验要去 SPSS/JASP，auto_stats 的 Levene 也只在差异分析内部自动跑，没有独立的"前提检验＋可粘论文结论"出口。
2. 算法口径先联网核查：从 EnvStats `swGofTestStatistic.R`（rdrr 镜像）核对 Royston 权重多项式，从 AS R94 公开源码镜像（matrixscience 的 swilk C++ 移植，与 R swilk.c、scipy swilk.f 同源）取得 p 值正态化变换全部系数（c3–c6、g，n=3 精确分布），不凭记忆写系数。
3. 黄金验证先行：295 组（n=3…4000 × 五种分布）对 scipy.stats.shapiro，W 误差 4.3e-10、p<8e-9 个数量级；偏度峰度对 scipy 无偏估计 1.4e-14；200 组 Brown-Forsythe 对 scipy.stats.levene 误差 2.5e-13。再补 18 组 CLI 场景与 full_e2e 断言，最后接菜单与文档。

### 17.2 改动清单

- **新增 `tools/assumption_check.py`（菜单第 18 项）**：Shapiro-Wilk（Royston AS R94，3≤n≤5000）＋偏度/峰度 z（SE≈√(6/N)、√(24/N)）＋Kline 判据；`--group` 逐组正态＋Brown-Forsythe（复用 stats.compare._levene）；量表均分自动反向计分（题项全答才纳入，如实报 n）；导出 `_前提假设检验.csv`（三段式）与 `_前提假设报告.txt`；坏输入统一中文 rc=1；UTF-8/GBK 自适应；纯标准库。
- **stats/mathx.py 增补**：`normal_quantile`（Acklam，误差 5e-9）与 `normal_sf`（erfc，2e-16）；工具内另含 AS66 Mills 比连分式远尾函数（极小 p 不被截到 1e-19）。
- **分档判读（辅助而不限制 AI/学生判断）**：p≥.05＋Kline 通过→不拒绝；p<.05 但 Kline 内按 n≥300/50≤n<300/|z|>3.29 分三档给"近似正态＋稳健性校验/Bootstrap 主分析"建议；超 Kline 才指引 Welch/非参数；方差不齐指引 Welch/Games-Howell。
- **红线**：不显著≠证明正态、大样本 Shapiro 过敏感、Likert 单题不要求正态、不得为通过检验删数据或挑变换、n>5000 提示口径不稳。
- **菜单与计数**：菜单 17→18 项（17 处标签同步 /18）；工具脚本 18→19 个；stats 子包模块数不变（mathx 为增补函数）。
- **文档**：stats-guide 新增"参数检验前提"方法学小节并改写旧表述、t/ANOVA 节交叉引用；data-analysis-auto 新增第 6.5 步与总览行；START、README（版本轮换）、AGENTS、QUICKSTART、paper-outline、e2e-test 测试66、本文件。
- **测试（P0）**：`full_e2e.py` 475→**504 项全过**（+29）；黄金脚本与 18 组 CLI 场景全绿；consistency_check、validate、全量 py_compile 全绿。
- **范围控制**：doubao-skill 本轮无改动；测试与补丁不入库。

## 十八、v1.68 优化：配对设计差异检验闭环（前后测 / 两条件）

> 2026-09-18 晚自主推进，同分支 `feat/advance-closed-loop`，承接 v1.67，补齐干预研究的组内变化检验断档。

### 18.1 背景与做法

1. 干预类本科论文（实验组/对照组×前测/后测）普遍要报前后测变化；此前只有 ttest-paired 样本量设计与由 t 反算 d_z 的效应量工具，没有能直接吃前后测数据、给齐配对检验＋前提＋非参数＋论文段落的出口，学生易误用独立样本 t 或只报组内显著。
2. 算法不凭记忆：配对 t 即差值单样本 t（mathx 已有 t 分布）；Wilcoxon 符号秩零差值剔除、结平均秩，n≤25 无结用 W+ 精确分布（2^n 符号组合动态规划计数），否则用含结校正 σ²=n(n+1)(2n+1)/24−Σ(t³−t)/48 与连续性校正正态近似（SPSS 口径）；差值正态性直接复用 v1.67 的 Shapiro-Wilk。
3. 黄金验证先行：462 组模拟（n=3…100 × 正态/含结/指数偏态）对 scipy.stats.ttest_rel/wilcoxon，再补 20 组 CLI 场景与 full_e2e 断言，最后接菜单与文档。开发中修掉：read_data 返回二元组误用三元解包、分组列中文走数值矩阵变 None、双文件 --pairs 冒号语义、结果列表与原始行变量同名、精确统计量整数化、scipy 新版双侧统计量取 min(W+,W−) 等问题。

### 18.2 改动清单

- **新增 `tools/paired_compare.py`（菜单第 19 项）**：配对 t＋d_z 近似 CI＋差值 Shapiro-Wilk＋Wilcoxon 符号秩（精确/近似自动切换）；单文件宽表 `--pairs 前:后`（可 `--id`）与两文件 `前测 后测 --id 编号`（强制编号、内连接、独有人员计数）两种口径；`--scales` 两文件量表均分（自动反向计分）；`--group/--level` 组内配对；导出 `_配对检验.csv` 与 `_配对检验报告.txt`；坏输入统一中文 rc=1；UTF-8/GBK 自适应；纯标准库（复用 stats.mathx 与 assumption_check）。
- **菜单与计数**：菜单 18→19 项（18 处标签同步 /19）；工具脚本 19→20 个；stats 子包模块数不变。
- **红线**：前提看差值正态；同一个体才能配对（两文件强制 --id）；3+ 时点用重复测量 ANOVA/混合模型、两两比较 Bonferroni；组间变化幅度用差值 t 或组别×时点交互。
- **文档**：stats-guide 配对设计方法学小节、data-analysis-auto 第 6.6 步与总览行、START、README（版本轮换）、AGENTS、QUICKSTART、paper-outline、e2e-test 测试67、本文件。
- **测试（P0）**：`full_e2e.py` 504→**541 项全过**（+37）；scipy 黄金（t 1.8e-15、Wilcoxon 精确 p 零误差、近似 z 1.3e-15）与 20 组 CLI 场景全绿；consistency_check、validate、全量 py_compile 全绿。
- **范围控制**：doubao-skill 本轮无改动；测试与补丁不入库。

## 十九、v1.69 优化：多重比较校正闭环（Bonferroni / Holm / BH / BY）

> 2026-09-18 晚自主推进，同分支 `feat/advance-closed-loop`，承接 v1.68，补齐多检验场景的 p 值校正断档。

### 19.1 背景与做法

1. 多组两两比较、多量表同时比较、相关矩阵、多个时点配对检验等"一个家族多个检验"的场景，假阳性随检验数膨胀（m=10、全零假设为真时族系假阳性最高约 40%）；此前只有 auto_stats 内部 Bonferroni 事后，没有能对任意一组 p 值统一校正、区分 FWER/FDR 的独立出口。
2. 算法不凭记忆、与权威软件同口径：Bonferroni=min(1,m·p)；Holm 逐步法（排序后 (m−i+1)·p 前缀累积取大，R p.adjust("holm")）；BH 逐步法（从大到小 p·m/i 后缀累积取小，R p.adjust("BH")/scipy false_discovery_control）；BY 在 BH 基础上除以调和数 c(m)=Σ1/i。黄金对照中发现临界值运算顺序会影响浮点判定（m·p/i 在 p=.03、m=5、i=3 时得 0.049999999999999996，而 scipy 的 p·(m/i) 得 .05），已按 scipy 顺序对齐，.05 边界不再误翻。
3. 黄金验证先行：R p.adjust 经典向量逐位一致，3000 组随机向量（m=2…65，含 ties/0/1）对 R 口径独立实现与 scipy：Bonferroni/Holm/BH 零误差、BY ≤4.4e-16；再补 20 组 CLI 场景与 full_e2e 断言，最后接菜单（第 20 项）与全套文档。

### 19.2 改动清单

- **新增 `tools/mult_compare.py`（菜单第 20 项）**：四法校正 p＋显著判定同列、显著项汇总、可粘论文段落；`--ps` 直给（可 `--names`）或 CSV 位置参数＋`--pcol`（可 `--namecol`）；`--method bonferroni/holm/bh/by/all`（默认 holm）、`--alpha`；导出 `_多重比较校正.csv` 与 `_多重比较报告.txt`；坏输入统一中文提示；UTF-8/GBK；纯标准库（复用 stats.dataio/mathx）。
- **菜单与计数**：菜单 19→20 项（19 处标签同步 /20）；工具脚本 20→21 个；stats 子包模块数不变。
- **红线**：家族范围与方法分析前确定、不得挑最宽松的报；原始 p 与校正后 p 同报；校正后不显著也是结果；等方差全两两比较优先 Tukey HSD（指引 SPSS），本工具用于计划比较与跨方法汇总。
- **文档**：stats-guide 多重比较校正方法学小节、data-analysis-auto 第 6.7 步与总览行、START、README（版本轮换）、AGENTS、QUICKSTART、paper-outline、e2e-test 测试68、本文件。
- **测试（P0）**：`full_e2e.py` 541→**570 项全过**（+29）；scipy/R 黄金（Bonferroni/Holm/BH 零误差、BY ≤4.4e-16）与 20 组 CLI 场景全绿；consistency_check、validate、全量 py_compile 全绿。
- **范围控制**：doubao-skill 本轮无改动；测试与补丁不入库。

## 二十、v1.70 优化：配对检验效应量与口径增强（rank-biserial r）

> 2026-09-18 晚自主推进，同分支 `feat/advance-closed-loop`，承接 v1.69，补 Wilcoxon 效应量与两处口径隐患。

### 20.1 背景与做法

1. v1.68 的符号秩检验只有显著性没有效应量；非参数结果在论文里需要配套的效应量（评审常问"差异多大"），rank-biserial r 是配对/单样本 Wilcoxon 的标准配套指标（Kerby 2014；R effectsize、JASP 默认输出）。
2. 公式与权威软件对齐：r_rb=（W+−W−）/T，T=n(n+1)/2（零差值剔除后），幅度等价 1−2·min(W+,W−)/T；600 组模拟（连续/Likert 结/偏态/含零）对 scipy.stats.wilcoxon 的双侧统计量反推，最大误差 8.9e-16，符号约定 d=后−前。
3. 顺带收口两处口径隐患（工作树内已完成的增强，经审查与门禁回归一并纳入）：n<30 有结只能正态近似时明示 p 偏乐观、需精确法/蒙特卡洛复核；反向计分越界硬提示（0 起编/无效码/0-1 题误配）。

### 20.2 改动清单

- **`tools/paired_compare.py`**：wilcoxon_signed_rank 返回 r_rb；控制台精确/近似两分支、论文段落（随非参数结论句）、CSV 新增 `Wilcoxon_r_rb` 列；新增 _r_tag 分档（.1/.3/.5）。
- **`tools/stats/dataio.py`**：recoded_item_series 反向结果越界硬提示（正向题不误报）。
- **菜单与计数**：菜单项 20、工具脚本 21 个均不变；full_e2e 570→**577 项全过**（+7）；consistency（21 工具/31 模块/103 开关/29 csv 后缀）、validate、全量 py_compile 全绿。
- **文档**：stats-guide、data-analysis-auto、START、README（版本轮换）、AGENTS、QUICKSTART、paper-outline、CHANGELOG、e2e-test 测试69、本文件同步。
- **范围控制**：doubao-skill 本轮无改动；测试与补丁不入库。

## 二十一、v1.71 优化：多重插补/FIML 教学指引闭环（缺失处理最后一公里）

> 2026-09-18 晚自主推进，同分支 `feat/advance-closed-loop`，承接 v1.66 缺失分析与 v1.70，补齐"建议插补之后怎么做"。

### 21.1 背景与做法

1. v1.66 工具在拒绝 MCAR 时只输出"建议多重插补/FIML"，学生缺操作路径；网络教程错误做法（均值插补、LOCF、单点回归当完整数据）泛滥，需要一份可照做、可核对、红线明确的指引。
2. 坚持"工具只检验不插补"：MI/FIML 涉及模型选择、池化规则与敏感性分析，内置一键插补会让学生在不理解 Rubin 规则时制造虚假精度；改为高质量教学文档＋权威软件操作（SPSS/R/AMOS），AI 带教时按需引用，既辅助又不替代判断。
3. 事实核查先行：SPSS PMM/默认 m=5/菜单路径、AMOS FIML 勾选位置均查 IBM/SPSS 官方文档确认；池化公式与 m 建议引 Rubin(1987)、Graham et al.(2007)、von Hippel(2018)。

### 21.2 改动清单

- **新增 `psychology/missing-imputation-guide.md`**：决策树、七条红线、SPSS MI（PMM、m、池化与 PROCESS 出路）、AMOS FIML（均值截距/辅助变量）、R mice 模板与 Rubin 公式、MNAR 敏感性、三章论文模板；含与其他专业文档一致的使用约定块与 P0 指针。
- **接线**：`tools/missing_report.py`（控制台解读＋论文段落指路径）、stats-guide、data-analysis-auto 第1.5步、START 查证表、README 知识库列表。
- **测试（P0）**：full_e2e 577→**589 项全过**（+12）；v1566 专业文档断言三份→四份；consistency（Markdown 41 个；开发中捕获一处误写的清洗脚本名并改为 data_cleaner.py）、validate、全量 py_compile 全绿。
- **范围控制**：无新增可执行插补代码，运行时纯标准库约束不变；菜单项 20、工具脚本 21 个不变；doubao-skill 无改动；测试与补丁不入库。

## 二十二、v1.72 优化：配对检验扩展单样本模式（对标称常数）

> 2026-09-18 晚自主推进，同分支 `feat/advance-closed-loop`，承接 v1.68/v1.70。

### 22.1 背景与做法

1. "Likert 均分是否高于中值 3""与常模分/理论值是否一致"是本科论文高频问题，此前无工具支持，学生易误用独立样本 t 或手点 SPSS 且漏掉前提检验。
2. 单样本 t 数学上等价于 d=x−C 的配对检验，直接复用 paired_test（pre=[C]*n、post=x），前提（差值正态）、d_z、Wilcoxon、rank-biserial r、有结警示全套同构，新增面只在 CLI 互斥与呈现条件分支，回归风险可控。
3. 黄金先行：300 组模拟对 scipy ttest_1samp/wilcoxon 零误差后才动代码。

### 22.2 改动清单

- `tools/paired_compare.py`：argparse 新增 `--onesample`/`--constant` 与四类互斥校验；单文件分支独立单样本循环（支持 --group/--level）；row 增加 mode/constant；print_rows/make_paragraph/write_csv 按模式切换文案，CSV 表头不变、备注标注"单样本(vs C)"。
- `tools/menu.py`：第19项开头选模式（回车配对/1 单样本），问答收集列与常数；受单文件 ≤700 行硬约束，同步压缩至 700 行。
- 文档：stats-guide 新增"单样本：一组分数对标称常数"小节（含"偏离中点≠干预有效"边界）、workflow 6.6、START、README、AGENTS、QUICKSTART、CHANGELOG、e2e-test 测试71。
- **测试（P0）**：full_e2e 589→**600 项全过**（+11）；consistency、validate、全量 py_compile 全绿；黄金脚本不入库。
- **范围控制**：工具脚本 21 个、菜单项 20 不变；doubao-skill 无改动；运行时纯标准库约束不变。

## 二十三、v1.73 优化：回归残差诊断闭环（Durbin-Watson＋残差正态，SW 下沉）

> 2026-09-18 晚自主推进，同分支 `feat/advance-closed-loop`，承接 v1.62 ω/HTMT 与 v1.67 前提假设。

### 23.1 背景与做法

1. 心理学论文多元回归表常要求 D-W 与残差正态，此前只报 VIF；手点 SPSS 易漏，且阈值口径（dL/dU vs 经验 1.5~2.5）需要带教提示。
2. Shapiro-Wilk 原在工具层 assumption_check.py，stats 包复用会造成反向依赖；借本次新增残差正态的契机把 SW 整体下沉 mathx，函数体逐行不动，两个调用方改导入，结构归位。
3. DW 为定义级统计量，黄金以 numpy diff 口径＋构造序列（常量/交替/AR(1)/白噪声）验证，不引入新依赖；残差 SW 复用已黄金过的 Royston 实现，端到端数值再与 numpy OLS＋scipy 逐位对照。

### 23.2 改动清单

- `tools/stats/mathx.py`：接收 shapiro_wilk（含 AS R94 系数、_poly/_norm_upper）；新增 durbin_watson。
- `tools/assumption_check.py`：删除下沉块，改从 stats.mathx 导入；`tools/paired_compare.py` 同步改导入。
- `tools/stats/regress.py`：linear_regression 末尾输出残差诊断块并在返回字典加"残差诊断"；压缩至 700 行硬约束内。
- 文档：stats-guide 新增"残差独立性（Durbin-Watson）与残差正态"前置小节、workflow 第7步回归说明、START/README/CHANGELOG/e2e-test 测试72。
- **测试（P0）**：full_e2e 600→**608 项全过**（+8）；consistency、validate、全量 py_compile 全绿；黄金脚本不入库。
- **范围控制**：工具脚本 21、菜单 20 不变；doubao-skill 无改动；运行时纯标准库约束不变。

## 二十四、v1.74 维护：论文模板接线（单样本与回归残差诊断进入产出链）

> 2026-09-18 晚自主推进，同分支 `feat/advance-closed-loop`，纯文档接线闭环。

### 24.1 背景与做法

1. v1.72/v1.73 的新能力只接到工具与 stats-guide 层，paper-outline/START/QUICKSTART 未同步，学生照模板写方法章会漏掉单样本口径与回归残差前提。
2. 本闭环无代码、无数值变化，只做产出链接线与接线断言，是"检查维护旧内容"的例行收口。

### 24.2 改动清单

- `templates/paper-outline.md`：4.4 补单样本 t/Wilcoxon 场景、报告项与边界；4.5 表3 规范补 VIF/D-W/残差正态与 Bootstrap 退路。
- START（auto_stats 能力＋版本号）、QUICKSTART 第3步、README（612 项/版本块）、CHANGELOG、e2e-test 测试73。
- **测试（P0）**：full_e2e 608→**612 项全过**（+4 接线断言）；consistency、validate、全量 py_compile 全绿。
- **范围控制**：工具脚本 21、菜单 20 不变；doubao-skill 无改动。

## 二十五、v1.75 维护：路线图挂账与版本区收敛

> 2026-09-18 晚自主推进，同分支 `feat/advance-closed-loop`，纯文档闭环。

### 25.1 背景与做法

1. v1.62–v1.74 连续闭环后 ROADMAP 失真：今晚识别的真实能力缺口未挂账，"MI 不内置一键插补"的架构决策未落档；后续会话可能重复造轮子或误判边界。
2. README 版本区多次轮换残留孤立要点，逼近 <200 行硬约束且偏离"当前＋上一版"自定规约，借本次发版收敛回 CHANGELOG 单一事实源。

### 25.2 改动清单

- `ROADMAP.md`：新增 Friedman/Nemenyi、polychoric/polyserial、分层 ω/Schmid-Leiman、HTMT2、回归诊断扩展、PPT 导出在制 6 项挂账；MI 不内置与 v1.62–v1.74 收成 2 项已完成决策；仍 <60 行。
- `README.md`：版本区收敛（当前 v1.75 块＋v1.74 一行），计数 616；START/CHANGELOG/e2e-test 测试74 同步。
- **测试（P0）**：full_e2e 612→**616 项全过**（+4）；consistency、validate、全量 py_compile 全绿。
- **范围控制**：无代码改动；工具脚本 21、菜单 20 不变；doubao-skill 无改动。

## 二十六、v1.76 文档勘误与行数守卫

> 2026-09-18 晚自主推进，同分支 `feat/advance-closed-loop`，纯文档闭环。

1. v1.75 CHANGELOG 详情行数表述"约 150 行"与实计 170 行不符，违反"数字可追溯"自律，发现即勘误并保留勘误痕迹。
2. 全局断言只守 README <200 行硬上限，无提前量；新增版本区行数守卫 ≤180，逼近即提示收敛。
3. full_e2e 616→**617 项全过**（隔离 worktree 验证，避开并行会话在制品）；consistency、validate、全量 py_compile 全绿；无代码改动，工具脚本 21、菜单 20 不变。

---

## 二十七、v1.77 开题产出物闭环（并行复核会话交付）

> 2026-09-18 晚，同分支 `feat/advance-closed-loop`。本版不新增统计工具，改为补齐
> 使用者当前阶段（开题）真正拿得出去的产出物。

1. 全项目原本零 PPT 生成能力（只有带【】的 markdown 大纲）。新增 `pptx_writer.py`
   （python-pptx 封装，含优雅降级）与 `outline_to_ppt.py`（大纲 → 真 .pptx）
   ＋12 页开题模板，结构照抄 `workflows/proposal-guide.md` 第四节。
   定位为**只排版不代写**，内容留【】由学生自填，避开 CONSTITUTION 红线。
2. `我的工作区/` 原 4 个目录只覆盖"文献＋数据＋结果＋网页"，不含开题/正文/答辩/伦理/
   导师沟通。新增 `setup_workspace.py` 扩到 9 个：只新增、不重命名移动删除、幂等，
   01–04 编号不动以兼容老学生本地数据。
3. `full_e2e.py` +21 条行为锁定（`v176guard`），钉住本轮之前四次修复；并把已过时的
   "ROADMAP 不得提到 outline_to_ppt/pptx_writer"点名禁令改回其本意不变量
   （被引用的 `*.py` 必须真实存在）。611→**632 项全过**，干净解压副本 632/632。
4. 已知欠账：`menu.py` 恰好 700 行撞单文件上限，两个新工具未进菜单，须先拆 menu.py
   （`菜单标签全部20项制` 断言硬编码的菜单数要同步改）。

---

## 二十八、v1.78 手机合并单文件构建链路闭环（仓库收拢到唯一目录后第一版）

> 2026-09-19。三个 git 工作区合并为唯一目录 `thesis-ai-coach-project`（master 快进跟齐 v1.77，
> 未重写历史；合并前全量 ref 备份在项目外 `_归档/bundles/`），此后开发直接在 master 上进行。

1. 开发树两条红（`Skill自检退出0`、`v161旧语气名清零`）在干净副本里不复现，追下去是**一处路径不一致**：
   `build_mobile_single.py` 的 `--out` 默认按当前目录解析，从仓库根跑就把产物写进仓库根
   （不在 .gitignore 内），而 `validate.py` 检查 `doubao-skill/` 那份 → 重新生成也永远报不同步；
   Skill README 的发布流程又只往分发包生成，受检那份必然长期过期。
2. 修：默认输出 `ROOT/DEFAULT_NAME`（与受检、被忽略的那份同一个），显式 `--out` 语义不变；
   validate 提示给可执行命令；README 用法与发布流程两步改正；旧语气名断言排除构建产物
   （产物过期归 validate 管，不让源码断言替它报警）。**分发包里那份一直是正确的**，学生侧零变化。
3. `full_e2e.py` +2 条行为锁定，真跑子进程钉住"生成方与校验方同一路径"，跑完还原产物原状；
   632→**636 项全过**；consistency、validate、py_compile 全绿。Skill v1.4.1（只动维护者工具）。
   过程中 `consistency_check.py` 自身两处误报一并修掉（与 v1.77 那颗幽灵脚本雷同类）：
   全局开关集合只扫 `tools/`，把版本历史引用的技能生成器真实开关判成未定义；
   文档引用被 .gitignore 排除的构建产物路径，在干净副本里必然"悬空"。
   两处都做了阴性验证——植入假开关、引用真不存在的文档仍被抓。
4. 顺带清账：顶层 20 多个一次性验证副本目录（约 190 MB）删除（`git archive <tag>` 可重建），
   黄金对照脚本与审查报告移入 `_归档/` 并改指主仓路径；`_构建验证/`、`_scratch/` 留空壳并写明
   "用完即删"的规则，防止再长回垃圾堆。
5. 仍欠：`menu.py` 700 行上限（同上第 4 条）、GitHub Release 未建（本机无 `gh`，且属对外动作待用户点头）、
   使用者 `我的论文进度.md` 仍空白（包没被真人走通过）。

---

## 二十九、v1.79 菜单拆分（将 v1.78 挂账的接线门禁拆掉）

> 2026-09-19。行为零变化的结构重组，目的是让"新工具能进菜单"重新变得可能。

1. `menu.py` 恰好 700 行撞 `原大文件已分解` 门禁，加一项实测红 4 条 → v1.77 的 `outline_to_ppt.py`
   与 `setup_workspace.py` 只能走命令行。本版本先拆后接：拆为入口 `menu.py`（102 行）
   ＋ `menu_io.py`（`ask_path`/`run`/`pause`/`_ask_num`）＋ `menu_data.py`（12 项）＋ `menu_lit.py`（8 项）。
2. 拆法用脚本按顶层 `def` 切片搬移，处理器正文一字未改；拆分前后同输入抓主菜单输出**逐字节一致**，
   并真跑第 6 项取消路径确认子进程链完好。
3. 断言层同步：18 条菜单文本断言从各自 `tx("tools/menu.py")` 改为统一读 `tools/menu*.py` 合并文本；
   新增 4 条结构不变量——其中最关键一条是**真 import** 核对（菜单表 20 项、每项可调用、首末编号 1/20、
   `t_*` 定义集合与挂接集合相等），因为文本匹配抓不到"函数搬家了却没挂进表"这种拆分典型错；
   实测摘掉最后一项即报 `False ['t_multcomp']`。636→**640 项全过**。
4. 文档：`DEVELOPMENT.md` 阶段 D 写明"加一项"的四步姿势（分组模块写 `t_xxx` → `MENU` 表挂一行 →
   标签分母同改 → `菜单标签全部20项制` 断言同改）；`AGENTS.md` 目录速查工具数 21→23（v1.77 起就漏更）。
5. 下一步（v1.80）即把 PPT 与工作区两项接进菜单第 21/22 项。

---

## 三十、v1.80 开题产出物接进菜单（把 v1.77 欠的接线补完）

> 2026-09-19。菜单 20→22 项；顺手修掉两处会让学生卡住/被误导的真实缺陷。

1. 接线：第 21 项 `t_ppt()`（默认吃 `我的工作区/05-开题报告/我的开题大纲.md`，可先只自检）、
   第 22 项 `t_workspace()`（`c` 走 `--check` 只报告）。1–20 编号一律不动，
   所以 `proposal-guide`/`data-analysis-auto`/`START` 里"菜单第 8/14/15/19 项"等引用不需要改。
2. 断言去硬编码：`菜单标签全部20项制` 换成 `菜单标签编号连续且分母等于项数`（自数 N），
   v179 的两条结构断言改为按 N 核对。这既是本次加项的最小代价路径，也顺手拆掉
   PROJECT_PLAN 二十九里"硬编码菜单数"那颗维护地雷。
3. 修缺陷：`--dry-run` 与正式生成同一把尺子（过去不查图片存在性，自检通过、真跑硬失败）；
   报错文案错指"模型图看菜单第10项"改为第 6 项；PPT 模板与工具文档里工作区的 `02-开题报告` 改回 `05-开题报告`。
   为这类"嵌在命令里的目录号"补 `consistency_check` 规则 5b（旧规则只看整段反引号路径，抓不到）。
4. 文档接线补平：`START.md` 工具清单此前**根本没有** outline_to_ppt/setup_workspace 两条（v1.77 漏更），
   现补齐并加"开题/答辩PPT用法""工作区用法"；START 第六步的目录列表也从 4 个补到 9 个；
   QUICKSTART 菜单清单、proposal-guide 第四节、先读我、README 目录树同步；
   `tests/e2e-test.md` 补 测试76/77/78（v1.77 未同步的用例清单一并补平）。
5. 验证：两项真跑走完整交互；full_e2e 640→**643 项全过**；consistency/validate/py_compile 全绿；
   菜单四件套最大 402 行。doubao-skill 无改动。

---

## 三十一、v1.81 开题 PPT 的中文字体写进主题

> 2026-09-19。把 v1.80 交付时推给学生的"现场改字体"变成生成物自带的确定性。

1. 缺陷：默认模板主题里 `a:ea` 为空 → 中文用哪套字体由各台机器的 Office 主题决定，
   换到学院机房就可能从雅黑变宋体、行高字宽一变 12 页版式就抖。v1.80 的文档甚至把这件事写成学生的责任。
2. 做法：`pptx_writer` 加 `cn_font`（默认微软雅黑），`save()` 后重写包内 `ppt/theme/themeN.xml`，
   major/minor 两组各自的 latin/ea/cs 一并写死。直接改 zip 的原因：python-pptx 把主题当不透明部件存，
   没有公开 API 能写 `a:ea`。回填保持原顺序/压缩方式/时间戳（`[Content_Types].xml` 仍在首位），
   临时文件同盘替换；字体名做 `&<>` 实体转义。
3. 出口：`outline_to_ppt.py --cn-font 宋体` 按学校口径换；`--cn-font none` 完全不动主题；
   菜单第 21 项加一问，学生不需要记开关。
4. 测试 +4：默认=雅黑、指定=宋体、none 确实为空（防止"不改"被静默改成"照改"）、
   改后包仍可被 python-pptx 回读且无形状越出页面边界（重写 zip 最坏情况兜底）。643→**647 项全过**。
5. 文档：START/README/ROADMAP 同步；START 里"字体由各机器决定"的旧措辞改为"已写进主题，换机器仍现场确认版式"。
