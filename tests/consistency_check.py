#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档 ↔ 代码 一致性自检（测试金字塔跨工件层）。

防止"文档说谎"：学生照着 README/START/workflows 里的命令操作却失败。
核对三件事：
  1. 文档里显式引用的 tools/xxx.py 都真实存在；
  2. 文档命令里出现的 --开关 都在对应脚本 argparse 中真实定义；
  3. 文档声称会导出的 _xxx.csv 文件，代码里确实会写出。

纯标准库，直接运行：python tests/consistency_check.py
退出码 0=全部一致，1=发现漂移（打印清单，需修文档或代码）。
"""
import ast
import re
import sys
from pathlib import Path
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

# 通用/文档示意开关，不属于某个脚本但允许出现在文档里
SWITCH_WHITELIST = {"--help", "-h", "--outdir", "-o", "--version"}

# 构建产物：由脚本生成、被 .gitignore 排除，因此**干净解压副本里必然不存在**。
# 文档引用它们是正确的（要告诉维护者产物在哪），不能当悬空链接报漂移。
BUILD_ARTIFACT_REFS = {"doubao-skill/thesis-ai-coach-手机版.md"}


def tool_switches(py_path: Path):
    """用 AST 解析某脚本 argparse add_argument 的长开关。"""
    switches = set()
    try:
        tree = ast.parse(py_path.read_text(encoding="utf-8"))
    except Exception:
        return switches
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "add_argument":
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                            and arg.value.startswith("--"):
                        switches.add(arg.value)
    return switches


def py_export_suffixes(py_path: Path):
    """抓取脚本里写出的 _中文/英文.csv 导出文件名后缀（如 _信度分析.csv）。"""
    text = py_path.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"_[0-9A-Za-z\u4e00-\u9fa5]+\.csv", text))


def code_blocks(md_text: str):
    """返回 markdown 中每个 ``` 围栏代码块的文本列表。"""
    return re.findall(r"```[^\n]*\n(.*?)```", md_text, flags=re.S)


def command_segments(md_text: str):
    """提取所有可能含命令的片段：围栏代码块（整块，支持多行续行）＋围栏外的每一行。"""
    segments = []
    rest = md_text
    for m in re.finditer(r"```[^\n]*\n(.*?)```", md_text, flags=re.S):
        segments.append(m.group(1))
        rest = rest.replace(m.group(0), "\n", 1)
    segments.extend(rest.splitlines())
    return segments


def main():
    problems = []

    # 扫描 tools/ 下全部 .py（含 stats/ 子包）：导出文件名与 CLI 开关可能定义在任一实现模块里，
    # 只扫顶层会在拆分后漏掉 "_因子分析.csv" 这类由子模块写出的文件，导致误报漂移。
    tool_paths = sorted(p for p in TOOLS.rglob("*.py") if "__pycache__" not in p.parts)
    tool_keys = {p.relative_to(TOOLS).as_posix(): p for p in tool_paths}
    py_set = set(tool_keys) | {p.name for p in tool_paths}
    top_py_files = sorted(p.name for p in TOOLS.glob("*.py"))
    switches_by_tool = {k: tool_switches(p) for k, p in tool_keys.items()}
    # 命令片段里通常只写裸脚本名，按文件名汇总其开关，供 owner 归属核对
    switches_by_name = {}
    for k, sw in switches_by_tool.items():
        switches_by_name.setdefault(k.rsplit("/", 1)[-1], set()).update(sw)
    all_switches = (set().union(*switches_by_tool.values()) if switches_by_tool
                    else set()) | SWITCH_WHITELIST
    # doubao-skill 与 tests/ 的维护者脚本不属 tools/ 命名空间（build_mobile_single.py、size_ratchet.py 等），
    # 但文档里引用它们的 --out/--write 是真实开关：并入全局集合即可，不参与按脚本归属核对。
    for _sp in sorted((ROOT / "doubao-skill").glob("*.py")) + sorted((ROOT / "tests").glob("*.py")):
        all_switches |= tool_switches(_sp)
    all_exports = set()
    for p in tool_keys.values():
        all_exports |= py_export_suffixes(p)

    # 全项目 Python 脚本名（tools + tests），用于核对命令里出现的脚本（含 tests/ 下脚本）
    all_py_names = {p.name for p in ROOT.rglob("*.py")
                    if "__pycache__" not in p.parts and ".git" not in p.parts}
    # 全项目文档同名映射（用于裸文件名导航引用兜底，如文档里只写 stats-guide.md）
    name_map = {}
    for p in ROOT.rglob("*"):
        if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts:
            name_map.setdefault(p.name, []).append(p)

    def doc_exists(md: Path, ref: str):
        """文档引用是否存在：依次试 相对当前md、相对ROOT、tools、test-data、工作区，最后全项目同名兜底。"""
        ref = ref.strip().replace("\\", "/")
        cands = [md.parent / ref, ROOT / ref, ROOT / "tools" / Path(ref).name,
                 ROOT / "tests" / "test-data" / Path(ref).name,
                 ROOT / "我的工作区" / Path(ref).name]
        if any(c.exists() for c in cands):
            return True
        return bool(name_map.get(Path(ref).name))

    md_files = list(ROOT.rglob("*.md"))
    skill_files = [p for p in md_files if p.relative_to(ROOT).parts[0] == "doubao-skill"]
    for md in md_files:
        # 跳过 .user_skills 等目录外内容（rglob 已限定 ROOT）
        rel = md.relative_to(ROOT)
        # 学生自由工作区：文件由学生自己命名，不由工具保证，不做导出一致性核对
        # doubao-skill 独立分发子包，由其 validate.py 自检，不纳入完整版核对
        if rel.parts[0] in ("doubao-skill", "维护档案"):   # 档案＝历史快照，不参与文档↔代码核对
            continue
        is_workspace = rel.parts[0] == "我的工作区"
        text = md.read_text(encoding="utf-8", errors="replace")

        # 1. 显式 tools/xxx.py 引用存在性（允许子包路径，如 tools/stats/efa.py）
        for ref in re.findall(r"tools/([A-Za-z0-9_/]+\.py)\b", text):
            if ref not in py_set:
                problems.append(f"[{rel}] 引用了不存在的 tools/{ref}")

        # 2. 命令片段（围栏块/逐行）内开关归属核对（-- 后首字符必须是字母/数字，排除 ---）
        sw_re = re.compile(r"(--[a-zA-Z0-9][a-zA-Z0-9-]*)")
        for block in command_segments(text):
            tools_in_block = re.findall(r"([A-Za-z0-9_]+\.py)\b", block)
            block_switches = set(sw_re.findall(block))
            for t in tools_in_block:
                # 带 tools/ 前缀的已由规则1核对，这里只补裸名/其它目录（如 tests/）脚本
                if f"tools/{t}" in block or f"tools\\{t}" in block:
                    continue
                if t not in all_py_names:
                    problems.append(f"[{rel}] 命令引用了项目中不存在的脚本 {t}")
            owner = next((t for t in tools_in_block if t in py_set), None) if tools_in_block else None
            if owner:
                for sw in block_switches:
                    if sw in SWITCH_WHITELIST:
                        continue
                    if sw not in switches_by_name.get(owner, set()):
                        # 同一块可能串联多个工具；任一工具定义过即视为合理
                        if not any(sw in s for s in switches_by_name.values()):
                            problems.append(
                                f"[{rel}] 命令片段里的开关 {sw} 在 {owner}（及其它工具）中均未定义")
            else:
                # 没有可归属的真实工具脚本：仍核对开关是否在全项目定义过
                for sw in block_switches:
                    if sw not in all_switches:
                        problems.append(f"[{rel}] 出现未定义开关 {sw}")

        # 3. 导出 csv：只核对"含中文"的工具报告后缀（英文 csv 多为输入/临时文件）；
        #    学生自由工作区是自命名示例，跳过。
        if not is_workspace:
            for exp in set(re.findall(r"_[0-9A-Za-z\u4e00-\u9fa5]*[\u4e00-\u9fa5][0-9A-Za-z\u4e00-\u9fa5]*\.csv", text)):
                if exp not in all_exports:
                    problems.append(f"[{rel}] 文档声称导出 {exp}，但没有任何工具写出该文件")

        # 4. 文档导航完整性：markdown 链接与反引号里引用的 .md 必须真实存在
        #    （AI 会按引导去读这些文件，悬空会直接断链）；裸文件名用全项目同名兜底
        md_refs = set(re.findall(r"\]\(([^)\s#]+\.md)(?:#[^)]*)?\)", text))
        md_refs |= set(re.findall(r"`([^`\n\s]+\.md)`", text))
        for ref in md_refs:
            if ref.startswith(("http", "<")) or "*" in ref:
                continue
            if ref.startswith("我的工作区/"):
                # 工作区里的是**学生自己产出**的文件（如"把大纲存成 我的工作区/05-开题报告/我的开题大纲.md"），
                # 包里不可能带着它，按文档链接判悬空会在干净副本里必然误报（目录号交给规则 5/5b 管）
                continue
            if ref in BUILD_ARTIFACT_REFS:
                continue
            if not doc_exists(md, ref):
                problems.append(f"[{rel}] 引用了不存在的文档 {ref}")

        # 5. 学生工作区路径引用完整：`我的工作区/子目录或文件` 的第一段必须真实存在
        #    （只核到第一段：目录号写错——把开题写成 02——要抓得到；
        #      而目录里学生会存什么文件包说了不算，核到整条路径会在干净副本里误报）
        for ws_ref in re.findall(r"`(我的工作区/[^`\n\s]+)`", text):
            if "*" in ws_ref or "<" in ws_ref:
                continue
            # 跳过示意性/枚举性引用：一个反引号里并列多个编号目录（01-…/02-…），或含占位措辞
            if len(re.findall(r"\d+-", ws_ref)) >= 2:
                continue
            if "子目录" in ws_ref or "xxx" in ws_ref.lower():
                continue
            first = ws_ref[len("我的工作区/"):].split("/")[0].rstrip(":：")
            if not first:
                continue
            if not (ROOT / "我的工作区" / first).exists():
                problems.append(f"[{rel}] 引用了不存在的工作区路径 {ws_ref}")

        # 5b. 命令示例与图片语法里嵌的"我的工作区/NN-目录"也必须真实存在。
        #     上面那条只认整段被反引号包住的路径，`python tools/x.py 我的工作区/02-开题报告/a.md`
        #     这类会从缝里漏过去——学生照着敲就撞"目录不存在"（v1.77 的 PPT 模板就这么错过一次）。
        for seg in set(re.findall(r"我的工作区/(\d{2}-[0-9A-Za-z一-鿿-]+)", text)):
            if not (ROOT / "我的工作区" / seg).is_dir():
                problems.append(f"[{rel}] 引用了不存在的工作区目录 我的工作区/{seg}")

    # 汇总打印（去重排序）
    problems = sorted(set(problems))
    print("=" * 56)
    print("文档 ↔ 代码 一致性自检")
    print("=" * 56)
    print(f"工具脚本 {len(top_py_files)} 个（含 stats/ 子包共 {len(tool_keys)} 个实现模块）；"
          f"Markdown {len(md_files) - len(skill_files)} 个（另 doubao-skill 子包 {len(skill_files)} 个由其 validate.py 自检）；")
    print(f"已定义 CLI 开关 {len(all_switches)} 个；导出 csv 后缀 {len(all_exports)} 个。")
    if problems:
        print(f"\n发现 {len(problems)} 处漂移：")
        for p in problems:
            print("  [漂移] " + p)
        print("\n结论：不一致，需修正文档或代码。")
        return 1
    print("\n结论：全部一致，未发现漂移。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
