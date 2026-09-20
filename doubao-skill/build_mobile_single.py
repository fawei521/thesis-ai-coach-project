#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把整个 Skill 合并成**一个 Markdown 文件**，供「只收一个文件的手机 AI」使用。

用途：有些手机 AI 不支持上传技能目录、或一次只让发一个附件。把本 Skill 的全部规则
（引导协议、陪伴边界、12 阶段、自然语气与三种可选语气、鼓励档、知识边界、危机与伦理口径）合并成一个文件，
学生发这一个文件即可开始，不需要再传别的。

用法：
    python doubao-skill/build_mobile_single.py        # 输出到本目录（doubao-skill/），与 CWD 无关
    python doubao-skill/build_mobile_single.py --out 输出路径.md
    python doubao-skill/build_mobile_single.py --check   # 只校验生成结果是否与源文件同步

默认输出路径就是 validate.py 检查"产物是否与源同步"的那个路径，两处必须一致：
在 doubao-skill/ 里生成、在发布时把该文件拷进分发包（或显式 --out 指到分发包目录）。

原则：
  - 逐文件**原样拼接**，不改写任何规则文字（避免"生成版与源版本不一致"）；
  - 每段前保留来源路径，便于学生/AI 溯源；
  - 文件头写明身份、能力边界与使用说明，让只读一个文件的 AI 也知道如何以"AI 助手/学习伙伴"身份工作；
  - 生成结果带内容指纹（各源文件字节数合计的 hash），便于 `--check` 比对是否过期。

纯标准库；中文 Windows 下管道输出不会崩（带输出编码守卫）。
"""
import argparse
import hashlib
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 默认 GBK）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
DEFAULT_NAME = "thesis-ai-coach-手机版.md"

# 拼接顺序：先入口与强制基准（身份陪伴→引导协议→鼓励），再阶段，再参考，最后语气与模板
ORDER = [
    "SKILL.md",
    "references/coaching-protocol.md",
    "references/companionship.md",
    "references/encouragement-guide.md",
    "references/stage-checklist.md",
    "references/evidence-rigor.md",
    "references/outcome-delivery.md",
    "references/skill-sourcing.md",
    "references/mobile-guide.md",
    "stages/stage-0-init.md",
    "stages/stage-1-topic.md",
    "stages/stage-2-literature.md",
    "stages/stage-3-organize.md",
    "stages/stage-4-scale.md",
    "stages/stage-5-questionnaire.md",
    "stages/stage-6-method.md",
    "stages/stage-7-data.md",
    "stages/stage-8-analysis.md",
    "stages/stage-9-writing.md",
    "stages/stage-10-communication.md",
    "stages/stage-11-defense.md",
    "references/ai-basics.md",
    "references/academic-norms.md",
    "references/tools.md",
    "references/faq.md",
    "personalities/default.md",
    "personalities/gentle-patient.md",
    "personalities/concise-direct.md",
    "personalities/lively-warm.md",
    "templates/我的论文进度模板.md",
]

# 不并入合并版的文件（维护者用，学生不需要；self-test 尤其不该给学生看）
EXCLUDE = {"CHANGELOG.md", "README.md", "references/self-test.md"}

HEADER = """# 毕业论文 AI 助手（Thesis AI Coach · 手机合并版）

> **这个文件是完整的技能本体，发给我（AI）之后直接开始用，不需要再传别的文件。**
> 由 `thesis-ai-coach` 豆包 Skill 自动合并生成；内容与技能目录逐字一致，未做改写。

## 规则优先级（冲突时按此顺序）

1. `references/coaching-protocol.md`（强制行为基准：三闸、P0/P1/P2、危机、伦理）
2. `references/companionship.md`（身份与陪伴边界）
3. `stages/stage-N-*.md`（阶段流程）
4. `references/encouragement-guide.md`（鼓励与反馈）
5. 语气文件（default / gentle-patient / concise-direct / lively-warm）：只改说法，不改规则
6. 参考常识（ai-basics / tools / academic-norms / faq / mobile-guide；报数字与下结论前对照 evidence-rigor）

任何语气、任何难度都不得违反第 1、2 层。手机能力边界以本文件"手机能力边界"一节为准。

## 给学生的三句话

1. 把本文件作为附件发给我，然后说：**"请按这个文件当陪我做毕业论文的 AI 助手，一步只推进一步。"**
2. 我是 AI 工具/学习伙伴，不是老师也不是虚拟伴侣；我会先问你 4 个小问题（语气、难度、鼓励档、现在到哪一步），然后从你所在阶段开始带。
3. **手机能做大部分，但有两处必须换电脑**：① 阶段 7 的数据预处理/清洗/反向计分/量表总分；② 阶段 8 的全部统计分析。
   写作、沟通、答辩可在手机起草和演练，但排版、查重、AI 检测、PPT 定稿建议回电脑。详见下面的"手机能力边界"和设备交接单。

## 给 AI 的说明（如果你是读取本文件的 AI）

- 本文件 = 入口（SKILL.md）+ 身份与陪伴边界（companionship）+ 强制行为基准（coaching-protocol / encouragement-guide）+
  阶段速查 + 手机使用说明 + 12 个阶段文件 + 常识参考 + 默认自然语气与三种可选语气 + 进度文件模板，**已按顺序完整拼接**。
- 各段以 `<!-- 来源: 路径 -->` 标注出处；各段内部的 `references/xxx.md`、`stages/xxx.md` 引用，
  **对应本文件后面的同名小节**，直接在本文件内查找即可，不需要外部文件。
- 你是**工具/学习伙伴，不自称老师/导师，不扮演恋人/亲人，不制造情感依赖**（见 companionship 小节）。
- 用**本文件的"手机能力边界"一节**约束自己：阶段 0–6 手机可全程完成；阶段 7 只有收数、监控、备份、导出原始数据可在手机，
  **预处理、五指标清洗、反向计分、量表总分必须回电脑**；阶段 8 的全部统计分析与出图必须回电脑；
  写作、沟通、答辩可在手机起草演练，但排版、查重、AI 检测、PPT 定稿建议回电脑。不要假装能算、不要凭学生口述的数字估结果。
- 学生明显在手机上（说"我只有手机"）时：阶段 0–6 照常引导、不降标准；**在阶段 6 开题通过后就主动提醒并带他填设备交接单**，
  不要拖到阶段 7 结束。

---

"""


def read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else None


def collect_files():
    """返回 [(相对路径, 文本)] ；ORDER 里的先按序，其余 .md 追加在后面。"""
    seen, out = set(), []
    for rel in ORDER:
        t = read(rel)
        if t is None:
            print("  ⚠ 缺失文件（跳过）: %s" % rel)
            continue
        out.append((rel, t))
        seen.add(rel)
    for p in sorted(ROOT.rglob("*.md")):
        rel = p.relative_to(ROOT).as_posix()
        if rel in seen or rel in EXCLUDE or rel == DEFAULT_NAME:
            continue
        out.append((rel, p.read_text(encoding="utf-8")))
        seen.add(rel)
    return out


def fingerprint(files):
    h = hashlib.sha256()
    for rel, txt in files:
        h.update(rel.encode("utf-8"))
        h.update(txt.encode("utf-8"))
    return h.hexdigest()[:16]


def build():
    files = collect_files()
    fp = fingerprint(files)
    parts = [HEADER, "<!-- 内容指纹: %s -->\n" % fp]
    for rel, txt in files:
        parts.append("\n---\n\n<!-- 来源: %s -->\n\n" % rel)
        parts.append(txt.rstrip() + "\n")
    parts.append("\n<!-- 合并版结束；共 %d 个源文件 -->\n" % len(files))
    return "".join(parts), fp, len(files)


def main():
    ap = argparse.ArgumentParser(description="把 Skill 合并成单个 Markdown 文件（手机 AI 用）")
    ap.add_argument("--out", default=str(ROOT / DEFAULT_NAME),
                    help="输出文件路径，默认本技能目录下的 %s（显式给相对路径时按当前目录解析）" % DEFAULT_NAME)
    ap.add_argument("--check", action="store_true", help="只校验：目标文件是否与源文件同步")
    args = ap.parse_args()

    text, fp, n = build()
    out = Path(args.out)
    if not out.is_absolute():
        out = Path.cwd() / out

    if args.check:
        if not out.exists():
            print("✗ 合并版不存在：%s" % out)
            return 1
        old = out.read_text(encoding="utf-8")
        same = ("内容指纹: %s" % fp) in old
        print("%s 合并版与源文件%s（指纹 %s，源文件 %d 个）"
              % ("✓" if same else "✗", "同步" if same else "**不同步，请重新生成**", fp, n))
        return 0 if same else 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print("✓ 已生成：%s" % out)
    print("  源文件 %d 个｜输出 %.0f KB｜汉字 %d 个｜指纹 %s"
          % (n, out.stat().st_size / 1024,
             sum(1 for c in text if "\u4e00" <= c <= "\u9fa5"), fp))
    print("  用法：把该文件作为附件发给手机 AI，说「请按这个文件当陪我做毕业论文的 AI 助手」。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
