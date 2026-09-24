#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件尺寸分层门禁（棘轮：存量冻结，只减不增）。

口径来源：用户 2026-09-19 拍板"新文件 ≤220 行硬闸、存量收 400 且只减不增"；
外部依据见 _归档/审查报告/2026-09-19 大文件拆分体检报告.md 第 1、4 节。

**220 与 300 是两种成本，不是大小写（2026-09-24 用户拍板分档）**：
  LIMIT_MD = 220 —— 出处就是上面那条"给 AI 读的文件每份 ≤220 行"：它管的是**上下文成本**，
    规则文档长一行＝全体学生**每一轮**多读一行，所以这一档不抬。
  LIMIT_PY = 300 —— `.py` 不进每轮上下文，它**被运行**而不是被通读，成本落在维护者改一次要翻多远，
    所以这里是可维护性启发式而非 context 预算。定 300 的实测依据（09-24）：`tools/menu_lit.py` 220 行里
    143 行是字符串（提示语与报告文案），`doubao-skill/validate.py` 最长函数仅 10 行、零个函数超 40 行——
    **卡死的文件早已拆到位，长是因为要对学生把话说清**，而文案正是产品价值本身。按函数长度设限对这两处
    都无效（原地照样顶闸），故抬这一档；判据仍按四类口径，只减不增与拆完收紧不变。
    ⚠ 不建第三档、也不许按文件名/目录单独开口子：名单会漂，形状不会。

规则：
  1. 不在存量清单里的文件      → 不得超过所属档的上限（新账不欠）。
  2. 在存量清单里的文件        → 不得超过清单记录的行数（只减不增）；
                                一旦降到本档上限以下，必须跑 --write 把它移出清单（棘轮收紧）。
  3. 记账类文件（LEDGER：CHANGELOG/PROJECT_PLAN/e2e-test）→ 不套行数闸：它们每版必须
                                追加，靠"重复只写一遍 + 正文移入 维护档案/"治理。
  4. 维护档案/ 整目录豁免：v1.83 起历史正文归档在这里（git 追踪、export-ignore 不进包）。
  5. 用量超过适用上限的 85%    → 打 WARN 不判红，让下一个人在**撞线之前**去拆。

扫描范围：tools/**/*.py、tests/**/*.py（含 e2e_cases 片段）、doubao-skill/*.py、全部 *.md。
豁免：doubao-skill/thesis-ai-coach-手机版.md —— build_mobile_single.py 的构建产物，
      "单文件"就是手机版的产品形态，拆它下次构建就被覆盖。

纯标准库，直接运行：python tests/size_ratchet.py [--write|--selftest]
  （无参数＝检查）退出码 0=通过，1=违规（打印逐个文件与整改命令）。
"""
import argparse
import sys
import os
import io
import tempfile
import shutil

# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 下 stdout 被管道捕获会退回 GBK，遇到 ⚠ → 等字符直接 UnicodeEncodeError；
# tests/full_e2e.py 与 AI 助手都以管道方式读输出，故统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT_PY = 300          # 代码档：成本是"维护者改一次翻多远"，不是每轮上下文
LIMIT_MD = 220          # 文档档：每轮必读的规则文档长一行＝全体学生每轮多读一行，这一档不抬
WARN_RATIO = 0.85
BASELINE = os.path.join(ROOT, "tests", "size_baseline.txt")
BUILD_ARTIFACTS = {"doubao-skill/thesis-ai-coach-手机版.md"}
LEDGER = {
    "CHANGELOG.md": "版本史唯一来源，每版必须追加",
    "PROJECT_PLAN.md": "计划与规格，随版本追加",
    "tests/e2e-test.md": "用例台账只增不减",
}
PY_DIRS = ["tools", "tests", "doubao-skill"]   # 三个目录都递归扫描（含 tools/stats、tests/e2e_cases）
SKIP_DIRS = {"维护档案"}                       # 历史快照目录：本性就长，拆它没有意义（见其 README）


def ceiling_for(rel):
    """两档各管什么，唯一一份定义（别的文件只许引用本函数的数字，别再抄常量）。"""
    return LIMIT_PY if rel.endswith(".py") else LIMIT_MD


def line_count(path):
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def scan(root):
    """返回 {相对路径: 行数}，只收受管文件。"""
    out = {}
    for d in PY_DIRS:
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x != "__pycache__" and x not in SKIP_DIRS]
            for fn in filenames:
                if fn.endswith(".py"):
                    full = os.path.join(dirpath, fn)
                    out[os.path.relpath(full, root).replace("\\", "/")] = line_count(full)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [x for x in dirnames
                       if x not in (".git", "__pycache__") and x not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            out[rel] = line_count(full)
    return out


def load_baseline():
    if not os.path.isfile(BASELINE):
        return {}
    frozen = {}
    with io.open(BASELINE, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            n, _, path = ln.partition("\t")
            if path:
                frozen[path.replace("\\", "/")] = int(n)
    return frozen


def check(sizes, frozen):
    """返回 (违规列表, 告警列表)。"""
    bad, warn = [], []
    for rel, n in sorted(sizes.items()):
        if rel in BUILD_ARTIFACTS or rel in LEDGER:
            continue
        limit = ceiling_for(rel)
        ceiling = frozen.get(rel, limit)
        if n > ceiling:
            if rel in frozen:
                bad.append("%s：%d 行 > 冻结值 %d 行（存量只准减不准增；要加内容请先把这个文件拆了）"
                           % (rel, n, ceiling))
            else:
                bad.append("%s：%d 行 > %s档新文件上限 %d 行（写的时候就拆，别留给下一个人）"
                           % (rel, n, "代码" if rel.endswith(".py") else "文档", limit))
        elif n <= limit and rel in frozen:
            bad.append("%s：已降到 %d 行（≤%d 行的%s档上限），请跑 python tests/size_ratchet.py --write "
                       "把它移出存量清单" % (rel, n, limit, "代码" if rel.endswith(".py") else "文档"))
        # 只对"逼近本档上限"的文件告警：存量文件的冻结值就是它自己的现值，
        # 对它报"已用量 100%"毫无信息量（棘轮已经禁止它增长了）。
        if rel not in frozen and limit * WARN_RATIO < n <= limit:
            warn.append("%s：%d 行，距%s档上限 %d 只剩 %d 行——再往里加之前先拆"
                        % (rel, n, "代码" if rel.endswith(".py") else "文档", limit, limit - n))
    for rel in sorted(frozen):
        if rel not in sizes:
            bad.append("size_baseline.txt 记着 %s（冻结 %d 行），但文件已不存在——"
                       "跑 python tests/size_ratchet.py --write 刷新清单" % (rel, frozen[rel]))
    return bad, warn


def write_baseline(sizes):
    """重新生成存量清单：把当前所有超本档上限且不受豁免的文件按现值冻结。"""
    rows = [(rel, n) for rel, n in sorted(sizes.items())
            if n > ceiling_for(rel) and rel not in LEDGER and rel not in BUILD_ARTIFACTS]
    head = (
        "# 存量超标文件冻结清单（棘轮：只减不增）\n"
        "# 生成命令：python tests/size_ratchet.py --write   —— 不要手改数字\n"
        "# 格式：<行数>\t<相对路径>；文件降到本文件适用档（.py 300 / 其余 220）以下后会被移出，此后按新文件上限管。\n"
        "# 不在此表 = 新文件，按档设硬闸（代码 300 / 文档 220，两档定义只在 tests/size_ratchet.py 一处）。\n"
        "# 记账类（CHANGELOG/PROJECT_PLAN/e2e-test）由 tests/size_ratchet.py 的 LEDGER 豁免：\n"
        "# 它们每版必须追加，靠“重复只写一遍 + 历史移包外”瘦身。\n"
        "# tests/full_e2e.py 已在 v1.82 拆成壳 + 顺序片段，不再豁免。\n")
    body = "".join("%d\t%s\n" % (n, rel) for rel, n in rows)
    with io.open(BASELINE, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(head + body)
    print("存量清单已写入：%d 个文件冻结（超本档上限且不受记账豁免）" % len(rows))
    return 0


def selftest():
    """阴性自测：尺子必须抓得住超标、放过达标，否则就是空转。"""
    tmp = tempfile.mkdtemp(prefix="size_ratchet_selftest_")
    try:
        os.makedirs(os.path.join(tmp, "tools"))
        def mk(rel, n):
            p = os.path.join(tmp, rel.replace("/", os.sep))
            d = os.path.dirname(p)
            if not os.path.isdir(d):
                os.makedirs(d)
            with io.open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join("# line %d" % i for i in range(n)))
            return p
        mk("tools/big.py", 350)          # 超代码档上限 → 必须抓到
        mk("tools/ok.py", 280)           # 代码档内（旧口径 220 会误伤）→ 必须放过
        mk("guide.md", 250)              # 超文档档上限 → 必须抓到（抬代码没顺手抬文档）
        mk("guide_ok.md", 200)           # 文档档内 → 必须放过
        mk("tools/frozen_grew.py", 350)  # 冻结 250 却长到 350 → 必须抓到
        sizes = scan(tmp)
        frozen = {"tools/frozen_grew.py": 250, "tools/ghost.py": 100}
        bad, _ = check(sizes, frozen)
        hits = " ".join(bad)
        cases = [("新文件超代码档被判红", "tools/big.py" in hits),
                 ("代码档 300 不误伤 280 行脚本", not any("tools/ok.py" in b for b in bad)),
                 ("超文档档 220 仍判红（抬代码没抬文档）", "guide.md" in hits),
                 ("文档档不误伤 200 行文档", not any("guide_ok.md" in b for b in bad)),
                 ("冻结文件变大被判红", "frozen_grew" in hits),
                 ("清单里的幽灵路径被判红", "ghost" in hits),
                 ("两档各按扩展名取，且代码档确实高于文档档",
                  ceiling_for("a.py") == LIMIT_PY and ceiling_for("a.md") == LIMIT_MD
                  and LIMIT_PY > LIMIT_MD)]
        for name, ok in cases:
            print(("  OK   " if ok else "  FAIL ") + name)
        if not all(ok for _, ok in cases):
            return 1
        print("阴性自测通过：尺子抓得住超标、放过达标")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="文件尺寸棘轮：新文件按档设限（代码 %d / 文档 %d 行），存量按 tests/size_baseline.txt 冻结只减不增"
                    % (LIMIT_PY, LIMIT_MD))
    ap.add_argument("--write", action="store_true",
                    help="重新生成存量冻结清单（拆完/降下来之后跑一次，棘轮自动收紧）")
    ap.add_argument("--selftest", action="store_true",
                    help="阴性自测：植入超标假文件与幽灵清单项，确认尺子抓得到（防尺子空转）")
    args = ap.parse_args(argv)
    sizes = scan(ROOT)
    if args.selftest:
        return selftest()
    if args.write:
        return write_baseline(sizes)
    bad, warn = check(sizes, load_baseline())
    print("文件尺寸棘轮检查：%d 个受管文件（新文件按档：代码 %d / 文档 %d 行）"
          % (len(sizes), LIMIT_PY, LIMIT_MD))
    for w in warn:
        print("WARN  " + w)
    if not bad:
        print("结论：无新增超标；存量 %d 个文件冻结值未被突破。" % len(load_baseline()))
        return 0
    for b in bad:
        print("FAIL  " + b)
    print("\n结论：文件尺寸门禁 %d 项违规。" % len(bad))
    return 1


if __name__ == "__main__":
    sys.exit(main())
