#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
thesis-ai-coach 豆包 Skill 结构自检（轻量版自己的 L7 门禁）。

纯标准库，直接运行：
    python validate.py
退出码 0 = 全部通过；1 = 发现问题（打印清单）。

检查项：
  1. SKILL.md frontmatter（name 与目录名一致、description 非空且含触发词）
  2. 必备文件齐全（人格/阶段/参考资料）
  3. 阶段文件编号 0-11 连续，且含准入、准出与三闸 checkbox
  4. 全部 md 的内部 .md 引用（链接与反引号）真实存在
  5. 鼓励系统默认打开且可关闭、安全口径存在
  6. 无 TODO/TBD/待补充 等占位残留
"""
import re
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 默认 GBK） ---
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
problems = []

REQUIRED_REFERENCES = [
    "coaching-protocol.md", "encouragement-guide.md", "stage-checklist.md",
    "ai-basics.md", "tools.md", "academic-norms.md", "faq.md", "self-test.md",
    "mobile-guide.md",
]
REQUIRED_TEMPLATES = ["我的论文进度模板.md"]
REQUIRED_PERSONALITIES = ["default.md", "strict-ceo.md", "gentle-sister.md", "puppy.md"]
STAGE_COUNT = 12


def read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def md_files():
    return sorted(ROOT.rglob("*.md"))


# 1. frontmatter -------------------------------------------------------
skill = ROOT / "SKILL.md"
if not skill.exists():
    problems.append("缺少 SKILL.md")
    print("FATAL: 缺少 SKILL.md，无法继续。")
    sys.exit(1)

skill_text = skill.read_text(encoding="utf-8")
fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", skill_text, flags=re.S)
if not fm:
    problems.append("SKILL.md 缺少 YAML frontmatter（--- 包裹的 name/description）")
else:
    head = fm.group(1)
    m_name = re.search(r"^name:\s*(\S+)\s*$", head, flags=re.M)
    m_desc = re.search(r"^description:\s*(.+?)\s*$", head, flags=re.M)
    if not m_name:
        problems.append("frontmatter 缺少 name 字段")
    elif m_name.group(1) != "thesis-ai-coach":
        problems.append(f"frontmatter name={m_name.group(1)}，应为 thesis-ai-coach")
    if not m_desc or len(m_desc.group(1)) < 40:
        problems.append("frontmatter description 缺失或过短（应含触发场景描述）")
    elif not any(k in m_desc.group(1) for k in ("毕业论文", "论文", "答辩")):
        problems.append("frontmatter description 缺少触发词（毕业论文/论文/答辩）")

# 2. 必备文件 -----------------------------------------------------------
for f in REQUIRED_PERSONALITIES:
    if not (ROOT / "personalities" / f).exists():
        problems.append(f"缺少人格文件 personalities/{f}")
for f in REQUIRED_REFERENCES:
    if not (ROOT / "references" / f).exists():
        problems.append(f"缺少参考文件 references/{f}")
for f in REQUIRED_TEMPLATES:
    if not (ROOT / "templates" / f).exists():
        problems.append(f"缺少模板 templates/{f}")

# 3. 阶段文件 -----------------------------------------------------------
stage_files = list((ROOT / "stages").glob("stage-*.md")) if (ROOT / "stages").exists() else []
stage_nums = []
for p in stage_files:
    m = re.match(r"stage-(\d+)-", p.name)
    if m:
        stage_nums.append(int(m.group(1)))
stage_files = [p for _, p in sorted(zip(stage_nums, stage_files))]
stage_nums = sorted(stage_nums)
if stage_nums != list(range(STAGE_COUNT)):
    problems.append(f"阶段编号不连续：实际 {stage_nums}，应为 0..{STAGE_COUNT - 1}")
for p in stage_files:
    t = p.read_text(encoding="utf-8")
    rel = f"stages/{p.name}"
    for kw in ("准入", "准出", "动机闸", "质量闸", "留痕闸"):
        if kw not in t:
            problems.append(f"{rel} 缺少关键字「{kw}」")
    if t.count("- [ ]") < 3:
        problems.append(f"{rel} 准出/准入 checkbox 不足 3 项")
    if "红线" not in t:
        problems.append(f"{rel} 缺少「红线」小节")

# 4. 内部 .md 引用必须存在 ---------------------------------------------
name_index = {p.name: p for p in ROOT.rglob("*") if p.is_file()}


# 学生侧自建产物 / 生成产物：轻量版里不实物存在，不算断链
STUDENT_ARTIFACTS = {
    "我的论文进度.md",              # 学生自建
    "thesis-ai-coach-手机版.md",    # 由 build_mobile_single.py 生成的合并单文件
}
FULL_PACKAGE_PATHS = ("我的工作区/",)
# 示意性写法（花括号枚举、stage-N 模式）不算引用
def is_pattern_ref(ref: str):
    return ("{" in ref or "}" in ref or "*" in ref
            or re.search(r"stage-N", ref) or "名称" in ref)


def ref_exists(md_path: Path, ref: str):
    ref = ref.strip().replace("\\", "/").split("#", 1)[0]
    if not ref or ref.startswith(("http", "<")):
        return True
    if is_pattern_ref(ref):
        return True
    if Path(ref).name in STUDENT_ARTIFACTS or ref.startswith(FULL_PACKAGE_PATHS):
        return True
    cands = [md_path.parent / ref, ROOT / ref]
    return any(c.exists() for c in cands) or Path(ref).name in name_index


for md in md_files():
    text = md.read_text(encoding="utf-8")
    refs = re.findall(r"\]\(([^)\s#]+\.md)(?:#[^)]*)?\)", text)
    refs += re.findall(r"`([^`\n\s]+\.md)`", text)
    for ref in refs:
        if not ref_exists(md, ref):
            problems.append(f"[{md.relative_to(ROOT)}] 引用了不存在的文档 {ref}")

# 5. 鼓励系统与安全口径 -------------------------------------------------
if "标准（默认" not in skill_text or "关闭" not in skill_text:
    problems.append("SKILL.md 未体现鼓励反馈「标准默认、可关闭」")
enc = read("references/encouragement-guide.md")
for kw in ("标准", "精简", "关闭", "P0 不包装", "成长型思维"):
    if kw not in enc:
        problems.append(f"encouragement-guide.md 缺少关键内容「{kw}」")
proto = read("references/coaching-protocol.md")
for kw in ("12356", "120 或 110", "紧急模式", "P0", "进度", "告知"):
    if kw not in proto:
        problems.append(f"coaching-protocol.md 缺少关键内容「{kw}」")
# 默认自然风格：SKILL 与 default 人格不得把角色扮演设为默认
if "默认不套任何人设" not in proto and "默认不套任何人设" not in skill_text:
    problems.append("未声明「默认不套人设、使用自然专业风格」")
checklist = read("references/stage-checklist.md")
for i in range(STAGE_COUNT):
    if f"**{i} " not in checklist:
        problems.append(f"stage-checklist.md 缺少阶段 {i} 行")

# 6. 占位符残留 ---------------------------------------------------------
# 只认真正的"没写完"标记。**不要**把 \bXXX\b、【】这类**模板填空位**算作残留——
# 模板里本来就该留空让学生填，误报会让维护者免疫真问题。
PLACEHOLDER = re.compile(r"TODO|TBD|待补充|待完善|FIXME")
for md in md_files():
    if md.name == "self-test.md":
        continue  # 测试用例文件本身需要描述"检查什么"，含占位符字样属正常
    text = md.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), 1):
        if PLACEHOLDER.search(line):
            problems.append(f"[{md.relative_to(ROOT)}:{i}] 疑似占位残留：{line.strip()[:40]}")

# 7. 手机独立版能力边界 -------------------------------------------------
# 手机做不了统计是本技能对外承诺的硬边界，必须三处一致地写清楚：
# SKILL.md（行为约束）、mobile-guide.md（学生可见说明）、stage-8（阶段内拦截）
mg = read("references/mobile-guide.md")
if not mg:
    problems.append("缺少 references/mobile-guide.md（手机版使用说明）")
else:
    for kw in ("手机上能完成", "手机上做不了", "必须回电脑", "不要相信"):
        if kw not in mg:
            problems.append(f"mobile-guide.md 缺少关键内容「{kw}」")
for rel, kws in [
    ("SKILL.md", ("手机做不了", "第 8 阶段只能做一半")),
    ("stages/stage-8-analysis.md", ("本阶段需要电脑", "JASP")),
    ("stages/stage-7-data.md", ("必须回电脑", "预处理", "清洗")),
    ("references/mobile-guide.md", ("必须回电脑", "手机上做不了")),
]:
    t = read(rel)
    for kw in kws:
        if kw not in t:
            problems.append(f"{rel} 未写明手机能力边界关键句「{kw}」")
# 手机端不得把电脑专属工具写成可用的必经步骤
mg_all = (mg or "") + read("references/tools.md")
if "手机上也能跑 SPSS" in mg_all and "不要相信" not in mg_all:
    problems.append("mobile-guide/tools 提到了「手机上也能跑 SPSS」，未同时否定")

# 8. 合并单文件：生成器存在；若产物已在目录内，必须与源同步 -------
_builder = ROOT / "build_mobile_single.py"
if not _builder.exists():
    problems.append("缺少 build_mobile_single.py（手机合并单文件生成器）")
_single = ROOT / "thesis-ai-coach-手机版.md"
if _single.exists():
    import subprocess
    r = subprocess.run([sys.executable, str(_builder), "--check", "--out", str(_single)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0:
        problems.append("合并单文件 thesis-ai-coach-手机版.md 与源文件不同步，请重新生成")

# 汇总 -----------------------------------------------------------------
print("=" * 56)
print("thesis-ai-coach Skill 结构自检")
print("=" * 56)
print(f"Markdown {len(md_files())} 个；阶段文件 {len(stage_files)} 个。")
problems = sorted(set(problems))
if problems:
    print(f"\n发现 {len(problems)} 处问题：")
    for p in problems:
        print("  [问题] " + p)
    print("\n结论：自检未通过，修正后再同步/发布。")
    sys.exit(1)
print("\n结论：全部通过，可以单独分发 / 同步到 .user_skills。")
sys.exit(0)
