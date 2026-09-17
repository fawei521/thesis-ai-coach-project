# Zotero + Obsidian 文献管理工具链

> 搭建"收集→管理→阅读→引用→写作"的完整文献工作流。
> 这是进阶配置，不装也能写论文（Word+手动管理即可），但装了效率提升明显，尤其适合读研。
>
> **带教约定**：本文件只提供本主题的专业步骤；每轮对话仍按 `core/coaching-protocol.md` 走引导循环、反馈三段式与 P0/P1/P2 分级，鼓励按 `core/encouragement-guide.md`（默认标准档，学生说"关闭鼓励"即关）；属于正式阶段的，收尾过 `core/coach-rules.md` 第十一节三道闸。

---

## 一、工作流全景

```
知网/英文数据库
   ↓（Zotero Connector一键抓取）
Zotero（文献库 + PDF管理 + 标注）
   ↓（Zotero Integration插件：把元数据与标注导成文献笔记）
Obsidian（每篇文献一个笔记 + 写作）
   ↓（正文插引用需另装 Citations / Zotero Citations 插件；更省事是直接用 Word 的 Zotero 插件，见3.5）
论文正文（自动插入引用 + 自动生成参考文献）
```

---

## 二、Zotero配置

### 2.1 安装中文GB/T 7714引用格式
1. 访问：https://www.zotero.org/styles
2. 搜索 "China" 或 "GB/T 7714"
3. 找到 "中国国家标准 GB/T 7714-2015 (numeric)"，点击安装
4. Zotero会自动弹出安装确认，点确定
5. 编辑 → 设置（Zotero 6 旧版叫"首选项"）→ 引用 → 样式，能看到该格式即成功

### 2.2 建立分类
左侧"我的文献库"右键 → 新建分类：
- 建议按变量/主题建：`自变量`、`因变量`、`中介变量`、`方法学`、`综述`
- 一篇文献可以同时属于多个分类（拖到分类时按住Ctrl）

### 2.3 导入文献的三种方式
1. **浏览器抓取（最常用）**：在知网/学术网页打开文献，点浏览器右上角Zotero图标
2. **批量导入**：知网搜索结果页，Zotero图标会变成文件夹，可勾选批量导入
3. **PDF拖拽**：直接把PDF拖进Zotero，右键"抓取元数据"自动识别

### 2.4 阅读和标注
- 双击PDF打开内置阅读器
- 高亮重点（黄色）、标注疑问（其他颜色）
- 右键标注可"添加到笔记"
- 这些标注之后能同步到Obsidian

### 2.5 导出参考文献
- 选中文献（Ctrl多选）
- 右键 → 由所选条目生成参考文献目录
- 样式选GB/T 7714-2015
- 复制到论文参考文献部分

---

## 三、Obsidian配置

### 3.1 安装Zotero Integration插件
> 先说清分工：**Zotero Integration 只负责把 Zotero 里的文献信息和 PDF 标注"导入成一篇结构化笔记"**（命令是 Import）；它**不提供**在正文里插入引用、自动生成参考文献的功能，那是 3.5 的另一款插件（或 Word 的 Zotero 插件）做的事。
1. Obsidian → 设置（左下角齿轮）→ 第三方插件
2. 关闭"安全模式"
3. 点"浏览"，搜索 "Zotero Integration"
4. 安装并启用

### 3.2 配置导入
1. 设置 → Zotero Integration
2. 设置PDF和笔记导入位置（如 `01-文献笔记/`）
3. 设置导入模板（可让AI根据你的需求生成模板）

### 3.3 基础文献笔记模板
AI可以帮你创建模板文件，典型结构：
```
---
title: "{{title}}"
authors: {{authors}}
year: {{date}}
citekey: {{citekey}}
tags: [文献]
status: 未读
---

## 核心观点

## 研究方法

## 关键发现

## 与我研究的关系

## 原文摘录
```

### 3.4 导入文献笔记
1. 在Obsidian按 Ctrl+P 打开命令面板
2. 输入 "Zotero Integration: Import"
3. 选择Zotero中的文献
4. 自动生成结构化笔记（含PDF标注）

### 3.5 在正文里插入引用、生成参考文献
注意：**Zotero Integration 插件没有 "Insert Citation" 命令**，它只做 3.4 的文献笔记导入。要在正文里像 Word 一样插入引用、文末自动生成参考文献，二选一：

**方案A（推荐，最省事）：正文放 Word 写，用 Zotero 自带的 Word 插件**
1. 安装 Zotero 桌面版时 Word 插件会自动装好（Word 顶部出现 Zotero 选项卡；没有就去 Zotero：编辑→设置→引用→文字处理软件→重新安装）
2. Word 里点 Zotero 选项卡 → Add/Edit Citation 选文献插入
3. 文末点 Add/Edit Bibliography 自动生成参考文献，样式选 GB/T 7714-2015
4. Obsidian 只用来管理文献笔记和草稿，互不冲突

**方案B（坚持全程在 Obsidian 写）：再装一款引用插件**
- 装 **Citations** 插件：先在 Zotero 装 Better BibTeX 插件，导出（或自动输出）一个 `.bib` / CSL-JSON 文件，在 Citations 设置里把 Citation Database path 指向它；之后 Ctrl+P 用 "Citations: Insert citation" 插引用、"Citations: Insert bibliography" 生成参考文献，最后用 Pandoc 导出 Word。
- 或装 **Zotero Citations** 插件：直接联动开着的 Zotero 桌面版，Ctrl+P 搜 "Insert citation" / "Insert bibliography"，Pandoc 导出 docx 时参考文献会保留。
- 方案B配置较繁，卡住就退回方案A，不影响论文进度和规范性。

---

## 四、推荐的Obsidian论文库结构

```
毕业论文库/
├── 00-总览/
│   ├── 研究进度看板.md
│   └── 选题与假设.md
├── 01-文献笔记/        # Zotero导入的文献笔记
├── 02-研究设计/
│   ├── 研究模型.md
│   ├── 量表选择.md
│   └── 问卷终稿.md
├── 03-数据分析/
│   ├── 分析计划.md
│   └── 结果记录.md
├── 04-论文草稿/
│   ├── 引言.md
│   ├── 文献综述.md
│   ├── 研究方法.md
│   ├── 研究结果.md
│   ├── 讨论.md
│   └── 结论.md
├── 05-开题答辩/
└── 附件/
```

---

## 五、日常使用流程

### 检索阶段
1. 知网/数据库看到相关文献 → Zotero一键抓取 → 归入对应分类
2. 高相关的下载PDF、做标注
3. Obsidian导入重点文献笔记，填结构化卡片

### 阅读阶段
1. Zotero读PDF、高亮
2. Obsidian笔记里写"与我研究的关系"
3. 用双链 `[[]]` 把相关文献连起来

### 写作阶段
1. Obsidian分章节写草稿、整理文献笔记
2. 正文引用与参考文献按 3.5 走：要么在 Word 里用 Zotero 插件（方案A，推荐），要么在 Obsidian 装 Citations / Zotero Citations 插件（方案B）
3. 最终按学校模板用 Word 排版、生成 GB/T 7714 参考文献

---

## 六、不想折腾配置怎么办

**最简替代方案**：
- 只用Zotero管理文献和生成参考文献（跳过Obsidian）
- 论文用Word写
- Zotero有Word插件（安装时自动装），可在Word里直接插入引用

**最最简方案**：
- 不用任何工具
- 用一个Excel表管理文献（本项目literature_organizer.py可生成）
- 参考文献手动按GB/T 7714排版
- 适合文献<30篇的情况

---

## 七、常见问题

| 问题 | 处理 |
|---|---|
| Zotero抓不到知网文献 | 安装/更新Zotero Connector；用RIS导出再导入 |
| 中文文献元数据乱 | 知网导入后手动检查标题作者；用"知网"版本translator |
| Obsidian插件搜不到 | 关闭安全模式；网络问题可手动下载插件放入plugins文件夹 |
| 引用格式不对 | 确认选了GB/T 7714-2015 numeric；让AI检查格式 |
| 联动失败 | 确保 Zotero 桌面版开着；Zotero Integration 一般可直接用，若你的模板用到 citekey，再装 Better BibTeX 插件 |
| 命令面板搜不到 Insert Citation | 正常：Zotero Integration 没有这个命令。正文插引用要装 Citations / Zotero Citations 插件，或直接用 Word 的 Zotero 插件（见 3.5） |
| 同步空间不够 | Zotero免费300MB附件空间；PDF可只不同步（用坚果云WebDAV扩容，AI可指导） |
