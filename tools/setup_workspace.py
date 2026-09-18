#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作区初始化 / 补齐工具
======================
把 `我的工作区/` 补齐成**覆盖论文全流程**的目录结构。

为什么需要：包里原来只有 4 个目录（文献PDF / 问卷数据 / 分析结果 / 网页），
只覆盖"读文献 + 跑数据"两段。而一篇心理学毕业论文实际要归档的东西远不止这些：
开题报告、论文正文各章、量表授权与知情同意、答辩材料、导师沟通记录……
缺了这些，学生的成果就散回桌面上了。

**三条硬规矩（这个工具的存在理由）**：
  1. 只新增，**绝不重命名、绝不移动、绝不删除**已有目录——老学生本地已有数据；
  2. 幂等：重复跑没副作用，已存在的目录一律跳过（连说明文件都不覆盖）；
  3. 不碰项目文件：只在 `我的工作区/` 里面动手。

用法：
  python tools/setup_workspace.py            # 补齐
  python tools/setup_workspace.py --check    # 只报告缺什么，不创建
"""
import argparse
import os
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与其他工具同款，避免 GBK 崩溃）---
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "我的工作区"

# (目录名, 放什么, 是否随包就该有)。01–04 是历史编号，保持不动。
LAYOUT = [
    ("01-文献PDF", "下载的论文 PDF、知网题录、文献总表 CSV、检索记录.md", True),
    ("02-问卷数据", "问卷星导出的原始答卷、预处理与清洗后的数据（原始那份不要改动）", True),
    ("03-分析结果", "脚本或 JASP/SPSS 跑出的统计表、三线表、模型图、中介结果", True),
    ("04-网页", "你自己做的网页（文献笔记页、数据看板、研究流程图、进度看板）", True),
    ("05-开题报告", "开题大纲、开题报告草稿与定稿、模型图/技术路线图、开题 PPT(.pptx)、"
                    "论证问答准备、导师与论证小组意见", False),
    ("06-论文正文", "各章草稿与定稿、图表源文件、格式检查记录；每存一版留日期后缀", False),
    ("07-答辩材料", "答辩 PPT、讲稿、预设问答、答辩记录", False),
    ("08-量表与伦理", "scales.txt、量表授权与版权使用记录、知情同意书（未成年人需监护人同意）、"
                      "伦理审查材料、数据保管与去标识化说明", False),
    ("09-导师沟通记录", "每次见导师/微信沟通的要点、老师要求改什么、你答应了什么"
                        "（回头看要求时这份最有用）", False),
]


# 占位说明文件名（沿用包内 `把…放这里.txt` 命名约定，full_e2e 的白名单按此模式放行）
PLACEHOLDER = {
    "05-开题报告": "开题报告与PPT",
    "06-论文正文": "论文正文",
    "07-答辩材料": "答辩材料",
    "08-量表与伦理": "量表授权与伦理材料",
    "09-导师沟通记录": "导师沟通记录",
}


def main():
    ap = argparse.ArgumentParser(description="补齐 我的工作区/ 的论文全流程目录（只新增不删除）")
    ap.add_argument("--check", action="store_true", help="只检查缺什么，不创建")
    ap.add_argument("--root", default="", help="项目根目录（默认自动定位到本工具上一层）")
    args = ap.parse_args()
    ws = Path(args.root).resolve() / "我的工作区" if args.root else WORKSPACE

    if not ws.exists() and args.check:
        print(f"✗ 找不到工作区：{ws}")
        sys.exit(1)

    created, skipped, missing = [], [], []
    for name, purpose, legacy in LAYOUT:
        d = ws / name
        if d.exists():
            skipped.append(name)
            continue
        if args.check:
            missing.append((name, purpose, legacy))
            continue
        d.mkdir(parents=True, exist_ok=True)
        # 占位说明沿用包内既有命名约定 `把…放这里.txt`：
        # full_e2e 的"学生数据不入库"白名单按这个模式放行，用别的名字会被判成泄漏。
        note = d / ("把" + PLACEHOLDER.get(name, name.split("-", 1)[-1]) + "放这里.txt")
        if not note.exists():
            note.write_text(f"{name}\n\n该放：{purpose}\n\n"
                            f"（本目录由 tools/setup_workspace.py 创建；"
                            f"目录只新增，工具不会重命名或删除任何已有内容。）\n",
                            encoding="utf-8")
        created.append(name)

    print("=" * 62)
    print("工作区目录检查" if args.check else "工作区目录补齐")
    print("=" * 62)
    print(f"位置：{ws}")
    if args.check:
        if not missing:
            print("✅ 九个目录齐全，无需补齐。")
            return
        print(f"缺 {len(missing)} 个目录（跑 `python tools/setup_workspace.py` 即可补齐）：")
        for name, purpose, _ in missing:
            print(f"  · {name}：{purpose[:44]}")
        return
    if created:
        print(f"新建 {len(created)} 个：{'、'.join(created)}")
    else:
        print("没有新建（都已存在）——重复运行不会有副作用。")
    print(f"已存在跳过 {len(skipped)} 个。")
    print("\n安全声明：本次没有重命名、移动或删除任何已有目录或文件；"
          "老数据留在原处即可，01–04 编号未改动。")
    print("下一步：把 `我的工作区/先读我.md` 看一眼，确认每类东西该放哪；"
          "换对话时把 `我的论文进度.md` 一起交给 AI 就能无缝接上。")


if __name__ == "__main__":
    main()
