#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作区初始化 / 补齐工具
======================
把 `我的工作区/` 补齐成**覆盖论文全流程**的目录结构，并生成缺少的**学生自己填写的文件**
（进度卡、检索记录——包里只带模板，填写版随包分发会在下次装新包时盖掉学生的记录）。

为什么需要：一篇心理学毕业论文要归档的东西不止"读文献 + 跑数据"两段——
开题报告、论文正文各章、量表授权与知情同意、答辩材料、导师沟通记录……
缺了这些，学生的成果就散回桌面上了。

**三条硬规矩（这个工具的存在理由）**：
  1. 只新增，**绝不重命名、绝不移动、绝不删除**已有目录与文件——老学生本地已有数据；
  2. 幂等：重复跑没副作用，已存在的目录与文件一律跳过（连说明文件都不覆盖）；
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
if hasattr(sys.stdout, "reconfigure"):
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

# 学生**就地填写**的文件：发布包只带模板、不带这些填写版（`.gitignore` 已同步排除）。
# 缺了才从模板复制一份，已存在则一个字都不碰——所以装新包不可能盖掉学生的存档点与检索留痕。
# 这份清单同时给 tests/consistency_check.py 与 full_e2e 复用，别在别处再抄一遍名字。
GENERATED = [
    ("我的论文进度.md", "templates/progress-template.md",
     "论文存档点（换对话/换 AI 时靠它续接）"),
    ("01-文献PDF/检索记录.md", "templates/检索记录模板.md",
     "检索留痕（多词矩阵、命中数、0 命中反查证据）"),
    ("06-论文正文/我的写作留痕.md", "templates/写作留痕模板.md",
     "写作留痕（每交一版草稿记一行时间/字数/指纹，攒的是「这论文是我写的」过程证据）"),
    ("我的毕业材料清单.md", "templates/materials-checklist.md",
     "学校要交的那一整套表格（任务书/计划书/中期检查/答辩记录…逐校不同，问教务后逐项打勾）"),
]


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

    made_files, have_files, lack_files = [], [], []
    for rel, tpl, purpose in GENERATED:
        dst = ws / rel
        if dst.exists():
            have_files.append(rel)
            continue
        if args.check:
            lack_files.append((rel, purpose))
            continue
        src = ROOT / tpl
        if not src.exists():
            print(f"✗ 包里的模板 {tpl} 不见了，跳过生成 {rel}（请重新解压发布包）")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())      # 逐字节复制：保住模板的行尾与编码
        made_files.append(rel)

    print("=" * 62)
    print("工作区检查" if args.check else "工作区补齐")
    print("=" * 62)
    print(f"位置：{ws}")
    if args.check:
        if not missing and not lack_files:
            print(f"✅ {len(LAYOUT)} 个目录齐全，{len(GENERATED)} 份填写文件也都在，无需补齐。")
            return
        if missing:
            print(f"缺 {len(missing)} 个目录：")
            for name, purpose, _ in missing:
                print(f"  · {name}：{purpose[:44]}")
        if lack_files:
            print(f"缺 {len(lack_files)} 份要你填写的文件（补齐时从模板复制，已存在的一律不动）：")
            for rel, purpose in lack_files:
                print(f"  · {rel}：{purpose}")
        print("\n跑 `python tools/setup_workspace.py`（或菜单第 22 项）即可补齐上面这些。")
        return
    if created:
        print(f"新建 {len(created)} 个：{'、'.join(created)}")
    else:
        print("没有新建（都已存在）——重复运行不会有副作用。")
    print(f"已存在跳过 {len(skipped)} 个。")
    if made_files:
        print(f"生成 {len(made_files)} 份待填写文件：{'、'.join(made_files)}（内容取自包内空白模板）")
    if have_files:
        print(f"已存在、未改动 {len(have_files)} 份你的文件：{'、'.join(have_files)}")
    print("\n安全声明：本次没有重命名、移动或删除任何已有目录或文件；"
          "老数据留在原处即可，01–04 编号未改动。")
    print("下一步：把 `我的工作区/先读我.md` 看一眼，确认每类东西该放哪；"
          "换对话时把 `我的论文进度.md` 一起交给 AI 就能无缝接上。")


if __name__ == "__main__":
    main()
