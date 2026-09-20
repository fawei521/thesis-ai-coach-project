# -*- coding: utf-8 -*-
"""改动中途跑的秒级门禁（L0）。**不含全量回归。**

    python tests/smoke_check.py

**本文件不复制任何检查逻辑**——只是把现成的检查器按序调用一遍、汇总成一句结论。
把逻辑抄一份到这里，就又造出一个会和原件漂移的副本（教训见
`维护档案/评估结论-外部账本治理建议-2026-09-20.md`）。

覆盖 9 项、实测约 5 秒：全脚本语法编译、文档↔代码一致性、尺寸棘轮（含阴性自测）、
轻量版口径同源（含阴性自测）、Skill 结构自检、两个工具行为脚本。

**盖不住什么**：`tests/e2e_cases/` 里那 700 多条事实与口径断言（量表数、报告措辞、
红线文案、发布包形态…）——那些只在 `python tests/full_e2e.py` 里跑。
什么时候必须跑全量，照 `DEVELOPMENT.md` 阶段 T 的"改动面 → 闸"表判，**不要凭感觉**。
"""
import subprocess
import sys
import time
from pathlib import Path

# --- 输出编码守卫：中文 Windows 控制台默认 GBK，管道/重定向时遇 ² χ² ⚠ 会 UnicodeEncodeError ---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]

# (显示名, 命令行, 是否允许跳过)。“命令”一律是仓库里现成的脚本或 -m 模块，不在此 reimplement。
GATES = [
    ("文档↔代码一致性", ["tests/consistency_check.py"]),
    ("文件尺寸棘轮", ["tests/size_ratchet.py"]),
    ("尺寸棘轮·阴性自测", ["tests/size_ratchet.py", "--selftest"]),
    ("轻量版口径同源", ["tests/skill_sync_check.py"]),
    ("轻量版口径·阴性自测", ["tests/skill_sync_check.py", "--selftest"]),
    ("Skill 结构自检", ["doubao-skill/validate.py"]),
    ("工具优雅降级", ["tests/test_graceful_degradation.py"]),
    ("特殊列处理", ["tests/test_special_columns.py"]),
]


def py_compile_args():
    """全脚本语法编译。用 rglob 而不是 shell 通配符：连 tests/e2e_cases/ 片段一起编。"""
    dirs = ("tools", "tests", "doubao-skill")
    files = sorted(str(p.relative_to(ROOT)).replace("\\", "/")
                   for d in dirs for p in (ROOT / d).rglob("*.py"))
    return (["-m", "py_compile", "-q"] + files, len(files))


def last_line(out):
    lines = [x.strip() for x in (out or "").splitlines() if x.strip()]
    return lines[-1][:78] if lines else ""


def main():
    args, nfiles = py_compile_args()
    plan = [("全脚本语法编译(%d 个 .py)" % nfiles, args)] + GATES
    if nfiles == 0:
        # 扫空也算“通过”是最坏的一种假绿，这里直接判红而不是交给下游断言。
        print("FAIL 全脚本语法编译：一个 .py 都没扫到（目录名写错？检查 GATES 与 ROOT）")
        return 1

    fails = []
    t_all = time.perf_counter()
    print("=" * 60)
    print("秒级门禁 smoke_check（不含全量回归）")
    print("=" * 60)
    for name, cmd in plan:
        t0 = time.perf_counter()
        try:
            p = subprocess.run([sys.executable] + cmd, cwd=str(ROOT), capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=180)
            rc, out, err = p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired as ex:
            rc, out, err = "TIMEOUT", ex.stdout if isinstance(ex.stdout, str) else "", "超时"
        dt = time.perf_counter() - t0
        ok = rc == 0
        verdict = last_line(out if ok else (err or out))
        print("%-4s %-32s %5.1fs  %s" % ("PASS" if ok else "FAIL", name, dt, verdict))
        if not ok:
            fails.append(name)

    total = time.perf_counter() - t_all
    print("==== smoke 共 %d 项，通过 %d，失败 %d ｜ 用时 %.1f 秒 ===="
          % (len(plan), len(plan) - len(fails), len(fails), total))
    if fails:
        print("失败项：" + "、".join(fails))
        print("→ 这几项各自的输出已在上面给出结论行；要定位细节就单独跑那一条命令。")
    else:
        print("→ 秒级门禁绿。**这不等于全量通过**：是否还要跑 full_e2e 看 DEVELOPMENT.md 阶段 T 的表。")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
