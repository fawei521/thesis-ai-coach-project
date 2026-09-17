# -*- coding: utf-8 -*-
"""
优雅降级与菜单1端到端回归测试（v1.36）。

验证两条小白真实路径：
1. 学生只装了 Python、没装 matplotlib/numpy/scipy 时：
   - auto_stats.py 数值结果（信度/相关/中介等 CSV）必须照常产出、退出0、无 Traceback，
     仅跳过图表并给出 pip install matplotlib 提示；
   - chart_generator.py 必须友好报错退出1（提示 pip install），不得抛 Traceback。
2. 菜单1 wjx_preprocess.py 对问卷星样例数据端到端可用（纯标准库）。
3. 菜单7生成演示数据 → 菜单3统计的练手闭环可一键跑通（含图表）。
4. paper_search 导出到尚不存在的目录时自动建目录，不崩溃。

运行：python tests/test_graceful_degradation.py ；退出码 0 = 全部通过。
临时文件全部写在系统 temp，结束自动清理。
"""
import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TD = ROOT / "tests" / "test-data"
fails = []


def check(name, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  [{extra}]"))
    if not cond:
        fails.append(name)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="coach_deg_"))
    try:
        # 阻断第三方库的 wrapper（修正 argv 后 runpy 运行目标脚本）
        block = tmp / "_block.py"
        block.write_text(
            "import builtins,runpy,sys\n"
            "_i=builtins.__import__\n"
            "BLOCK={'matplotlib','numpy','scipy','pandas','pingouin','statsmodels'}\n"
            "def _b(name,*a,**k):\n"
            "    if name.split('.')[0] in BLOCK: raise ImportError('BLOCKED '+name)\n"
            "    return _i(name,*a,**k)\n"
            "builtins.__import__=_b\n"
            "script=sys.argv[1]; sys.argv=[script]+sys.argv[2:]\n"
            "runpy.run_path(script,run_name='__main__')\n",
            encoding="utf-8")

        py = sys.executable

        # 1a. auto_stats 在无第三方库下：复制 demo 到临时目录，使导出落在临时目录
        shutil.copy(TD / "demo_survey.csv", tmp / "demo_survey.csv")
        shutil.copy(TD / "demo_scales.txt", tmp / "demo_scales.txt")
        cmd = [py, str(block), str(ROOT / "tools" / "auto_stats.py"),
               str(tmp / "demo_survey.csv"), "--scales", str(tmp / "demo_scales.txt"),
               "--y", "NSSI", "--x", "AI情感依赖",
               "--mediators", "孤独感,反刍思维", "--boot", "200"]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(tmp), timeout=150)
        check("缺库 auto_stats 退出0", r.returncode == 0, f"rc={r.returncode} {r.stderr[-200:]}")
        check("缺库 auto_stats 无Traceback", "Traceback" not in r.stderr, r.stderr[-200:])
        check("缺库仍产出数值CSV（信度/中介）",
              (tmp / "demo_survey_信度分析.csv").exists() and
              (tmp / "demo_survey_中介效应.csv").exists() and
              (tmp / "demo_survey_统计结果.csv").exists())
        check("缺库跳过热图（不生成PNG）", not (tmp / "demo_survey_相关热图.png").exists())
        check("缺库给出matplotlib提示", "matplotlib" in r.stdout, r.stdout[-200:])

        # 1b. chart_generator 在无 matplotlib 下友好报错
        cmd2 = [py, str(block), str(ROOT / "tools" / "chart_generator.py"),
                "--variables", "A,B,C,D", "--output", str(tmp / "x.png")]
        r2 = subprocess.run(cmd2, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", cwd=str(tmp), timeout=60)
        check("缺库 chart_generator 退出1", r2.returncode == 1, f"rc={r2.returncode}")
        check("chart 提示pip安装且无Traceback",
              "pip install matplotlib" in r2.stdout and "Traceback" not in r2.stderr,
              r2.stdout[-150:] + r2.stderr[-150:])

        # 2. 菜单1 问卷星预处理端到端（正常环境，纯标准库）
        cmd3 = [py, str(ROOT / "tools" / "wjx_preprocess.py"),
                str(TD / "sample_wjx_raw.csv"),
                "--output", str(tmp / "wjx_clean.csv"),
                "--report", str(tmp / "wjx_report.txt")]
        r3 = subprocess.run(cmd3, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", cwd=str(tmp), timeout=60)
        check("菜单1 wjx_preprocess 退出0", r3.returncode == 0, f"rc={r3.returncode} {r3.stderr[-200:]}")
        check("菜单1 产出clean与report",
              (tmp / "wjx_clean.csv").exists() and (tmp / "wjx_report.txt").exists())

        # 3. 菜单7演示数据 → 菜单3统计 的练手闭环（正常库环境）
        loop = tmp / "loop"
        r4 = subprocess.run([py, str(ROOT / "tools" / "generate_demo_data.py"),
                             "--outdir", str(loop)], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", cwd=str(tmp), timeout=60)
        check("菜单7生成演示数据", r4.returncode == 0 and
              (loop / "demo_survey.csv").exists() and (loop / "demo_scales.txt").exists(),
              r4.stderr[-200:])
        r5 = subprocess.run([py, str(ROOT / "tools" / "auto_stats.py"),
                             str(loop / "demo_survey.csv"), "--scales", str(loop / "demo_scales.txt"),
                             "--y", "NSSI", "--x", "AI情感依赖",
                             "--mediators", "孤独感,反刍思维", "--boot", "300"],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=str(loop), timeout=150)
        check("演示数据统计闭环退出0", r5.returncode == 0 and "Traceback" not in r5.stderr,
              f"rc={r5.returncode} {r5.stderr[-200:]}")
        check("闭环产出中介CSV与热图",
              (loop / "demo_survey_中介效应.csv").exists() and
              (loop / "demo_survey_信度分析.csv").exists() and
              (loop / "demo_survey_相关热图.png").exists())

        # 4. paper_search 导出到尚不存在的目录时自动建目录（离线直接调 export_csv）
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "paper_search_under_test", str(ROOT / "tools" / "paper_search.py"))
        ps = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ps)
        nest = tmp / "nest" / "sub" / "英文文献.csv"
        ps.export_csv([{"标题": "a"}, {"标题": "b"}], str(nest))
        check("检索结果自动建目录", nest.exists())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n==== 优雅降级测试：{len(fails)} 项失败 ====")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
