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

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

# 通用/文档示意开关，不属于某个脚本但允许出现在文档里
SWITCH_WHITELIST = {"--help", "-h", "--outdir", "-o", "--version"}


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

    py_files = sorted(p.name for p in TOOLS.glob("*.py"))
    py_set = set(py_files)
    switches_by_tool = {n: tool_switches(TOOLS / n) for n in py_files}
    all_switches = set().union(*switches_by_tool.values()) | SWITCH_WHITELIST
    all_exports = set()
    for n in py_files:
        all_exports |= py_export_suffixes(TOOLS / n)

    md_files = list(ROOT.rglob("*.md"))
    for md in md_files:
        # 跳过 .user_skills 等目录外内容（rglob 已限定 ROOT）
        rel = md.relative_to(ROOT)
        # 学生自由工作区：文件由学生自己命名，不由工具保证，不做导出一致性核对
        is_workspace = rel.parts[0] == "我的工作区"
        text = md.read_text(encoding="utf-8", errors="replace")

        # 1. 显式 tools/xxx.py 引用存在性
        for ref in re.findall(r"tools/([A-Za-z0-9_]+\.py)", text):
            if ref not in py_set:
                problems.append(f"[{rel}] 引用了不存在的 tools/{ref}")

        # 2. 命令片段（围栏块/逐行）内开关归属核对（-- 后首字符必须是字母/数字，排除 ---）
        sw_re = re.compile(r"(--[a-zA-Z0-9][a-zA-Z0-9-]*)")
        for block in command_segments(text):
            tools_in_block = re.findall(r"([A-Za-z0-9_]+\.py)", block)
            block_switches = set(sw_re.findall(block))
            owner = next((t for t in tools_in_block if t in py_set), None) if tools_in_block else None
            if owner:
                for sw in block_switches:
                    if sw in SWITCH_WHITELIST:
                        continue
                    if sw not in switches_by_tool.get(owner, set()):
                        # 同一块可能串联多个工具；任一工具定义过即视为合理
                        if not any(sw in s for s in switches_by_tool.values()):
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

    # 汇总打印
    print("=" * 56)
    print("文档 ↔ 代码 一致性自检")
    print("=" * 56)
    print(f"工具脚本 {len(py_files)} 个；Markdown {len(md_files)} 个；")
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
