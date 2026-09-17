# -*- coding: utf-8 -*-
"""
sample_size.py —— 心理学问卷研究样本量 / 统计功效估算（G*Power 等价，纯标准库）

用途：开题报告"需要多少份问卷"的先验功效分析（a priori power analysis），
      与 G*Power 3.1 的非中心分布算法等价，可直接在开题里写"用 G*Power 3.1
      估算，效应量取 X，α=.05，power=.80，至少需要 N=…"。

支持四种最常见设计：
  1. 相关          两个变量的相关（Pearson r），Fisher z 近似
  2. regression    多元回归总体 R²（检验整个回归 / 一组预测变量）
  3. r2-change     多元回归 R² 增量（检验新增的 1 个或几个预测变量，如交互项、中介路径之外的新增变量）
  4. anova         单因素方差分析（k 个组，Cohen f）

效应量基准（Cohen，务必结合本方向已发表研究 / 预实验确定，不能拍脑袋）：
  相关 r：小 .10 / 中 .30 / 大 .50
  回归 f²：小 .02 / 中 .15 / 大 .35（f²=R²/(1-R²)；R²增量用 ΔR²/(1-R²_全模型)）
  ANOVA f：小 .10 / 中 .25 / 大 .40

重要提醒：
  - 功效分析给的是"统计上的最小 N"，问卷研究还要考虑：无效问卷（建议多收 10%–20%）、
    每个量表条目 5–10 倍样本、结构方程/验证性因子分析通常建议 ≥200、Bootstrap 中介
    建议 ≥200（链式/复杂模型 ≥300–500，见 Fritz & Mackinnon, 2007）。
  - 本脚本数值用非中心 F（Poisson 混合，与 scipy.stats.ncf 逐位一致）与 Fisher z；
    正式开题建议再用 G*Power 3.1（免费）复核并截图附在开题报告里。
  - 效应量宁可保守（取小效应）估，样本量留足；不要为了少收问卷而故意取大效应。

用法示例：
  python tools/sample_size.py                         # 打印三档效应量速查表 + 实操建议
  python tools/sample_size.py --design regression --predictors 5
  python tools/sample_size.py --design regression --predictors 5 --effect 0.15
  python tools/sample_size.py --design r2-change --tested 1 --total 6 --effect 0.02
  python tools/sample_size.py --design anova --groups 4
  python tools/sample_size.py --design correlation --effect 0.3
  python tools/sample_size.py --design regression --predictors 4 --power 0.9 --extra 0.2
"""
import os
import sys
import math
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats.mathx import betai, f_p_value  # 复用经过黄金验证的不完全 beta / F 上尾 p
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ALPHA_DEFAULT = 0.05
POWER_DEFAULT = 0.80


def f_critical(df1, df2, alpha=ALPHA_DEFAULT):
    """中心 F 分布的上 alpha 临界值（对 f_p_value 二分求逆）。"""
    lo, hi = 1e-4, 60.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if f_p_value(mid, df1, df2) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _ncf_cdf(F, d1, d2, lam):
    """非中心 F 的 CDF，Poisson 混合表示：
    CDF = Σ_j Pois(j; λ/2) · I_z(d1/2+j, d2/2)，z=d1·F/(d1·F+d2)。
    λ=0 时退化为中心 F。"""
    if d2 <= 0:
        return 1.0
    z = d1 * F / (d1 * F + d2)
    mu = lam / 2.0
    if mu <= 0:
        return betai(d1 / 2.0, d2 / 2.0, z)
    total = 0.0
    w = math.exp(-mu)          # P(J=0)
    j = 0
    stop_after = mu + 10.0 * math.sqrt(mu) + 20.0
    while j < 5000:
        total += w * betai(d1 / 2.0 + j, d2 / 2.0, z)
        if j > stop_after and w < 1e-14:
            break
        w *= mu / (j + 1)
        j += 1
    return min(max(total, 0.0), 1.0)


def power_f(d1, d2, lam, alpha=ALPHA_DEFAULT):
    """非中心 F 检验的功效 = 1 - CDF(Fcrit)。"""
    if d2 <= 0:
        return 0.0
    fc = f_critical(d1, d2, alpha)
    return 1.0 - _ncf_cdf(fc, d1, d2, lam)


def min_n_f(d1, df2_at_n, f2, alpha, power, n_start):
    """通用：给定分子自由度 d1、由 N 决定分母自由度的函数 df2_at_n、非中心参数=f²·N，
    求使功效≥power 的最小 N。"""
    N = max(n_start, d1 + 3)
    while N < 20000:
        d2 = df2_at_n(N)
        if d2 > 0 and power_f(d1, d2, f2 * N, alpha) >= power:
            return N
        N += 1
    return None


def min_n_correlation(r, alpha=ALPHA_DEFAULT, power=POWER_DEFAULT):
    """双侧相关检验最小 N，Fisher z 近似：λ_z=atanh(r)·√(N-3)。"""
    if r <= 0:
        return None
    za = normal_quantile(1 - alpha / 2)
    lam = math.atanh(abs(r))
    N = 5
    while N < 20000:
        lz = lam * math.sqrt(N - 3)
        pw = normal_cdf(lz - za) + normal_cdf(-lz - za)
        if pw >= power:
            return N
        N += 1
    return None


def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_quantile(p):
    """标准正态分位数（Acklam 近似，精度 ~1e-9）。"""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p <= phigh:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
               (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
           ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)


def round_up_10(n):
    return int(math.ceil(n / 10.0) * 10)


def recommend_collect(n_min, extra=0.15, floor=None):
    """建议发放量：统计最小 N 基础上预留无效问卷，再取整到 10。"""
    base = n_min * (1.0 + extra)
    if floor:
        base = max(base, floor)
    return round_up_10(base)


def effect_label(kind, e):
    table = {
        "r": [(0.10, "小"), (0.30, "中"), (0.50, "大")],
        "f2": [(0.02, "小"), (0.15, "中"), (0.35, "大")],
        "f": [(0.10, "小"), (0.25, "中"), (0.40, "大")],
    }
    lab = "小"
    for thr, name in table[kind]:
        if e >= thr - 1e-9:
            lab = name
    return lab


def design_table(design, alpha, power, **kw):
    """返回三档效应量 (标签, 效应值, 最小N) 列表。"""
    out = []
    if design == "correlation":
        for e in (0.10, 0.30, 0.50):
            out.append((effect_label("r", e), f"r={e:.2f}",
                        min_n_correlation(e, alpha, power)))
    elif design == "regression":
        u = kw["predictors"]
        for e in (0.02, 0.15, 0.35):
            n = min_n_f(u, lambda N, u=u: N - u - 1, e, alpha, power, u + 4)
            out.append((effect_label("f2", e), f"f²={e:.2f}", n))
    elif design == "r2-change":
        u, t = kw["tested"], kw["total"]
        for e in (0.02, 0.15, 0.35):
            n = min_n_f(u, lambda N, t=t: N - t - 1, e, alpha, power, t + 4)
            out.append((effect_label("f2", e), f"f²={e:.2f}", n))
    elif design == "anova":
        k = kw["groups"]
        for f in (0.10, 0.25, 0.40):
            n = min_n_f(k - 1, lambda N, k=k: N - k, f * f, alpha, power, k + 3)
            out.append((effect_label("f", f), f"f={f:.2f}", n))
    return out


DESIGN_NAME = {
    "correlation": "相关分析（Pearson r，双侧）",
    "regression": f"多元回归总体 R²",
    "r2-change": "多元回归 R² 增量",
    "anova": "单因素方差分析 ANOVA",
}


def print_report(design, alpha, power, extra, effect, **kw):
    print("=" * 64)
    print("样本量 / 统计功效估算（G*Power 等价，α=%.2f，目标功效=%.2f）" % (alpha, power))
    print("=" * 64)
    name = DESIGN_NAME[design]
    if design == "regression":
        name += "（预测变量数 u=%d）" % kw["predictors"]
    elif design == "r2-change":
        name += "（新增检验变量 %d 个，全模型共 %d 个预测变量）" % (kw["tested"], kw["total"])
    elif design == "anova":
        name += "（组数 k=%d）" % kw["groups"]
    print("设计：" + name)
    print("-" * 64)
    table = design_table(design, alpha, power, **kw)
    print(f"{'效应量':<6}{'取值':<10}{'统计最小N':>10}{'建议发放(含无效卷)':>20}")
    chosen = None
    for lab, val, n in table:
        rec = recommend_collect(n, extra)
        mark = ""
        if effect is not None and abs(_val_of(val) - effect) < 1e-9:
            chosen = n
            mark = "  ← 你指定"
        print(f"{lab+'效应':<7}{val:<10}{n:>10}{rec:>18}{mark}")
    print("-" * 64)
    if effect is not None:
        # 精确按用户给的效应量算
        if design == "correlation":
            nmin = min_n_correlation(effect, alpha, power)
            note = f"r={effect:.3f}"
        elif design == "regression":
            u = kw["predictors"]
            nmin = min_n_f(u, lambda N, u=u: N - u - 1, effect, alpha, power, u + 4)
            note = f"f²={effect:.3f}"
        elif design == "r2-change":
            u, t = kw["tested"], kw["total"]
            nmin = min_n_f(u, lambda N, t=t: N - t - 1, effect, alpha, power, t + 4)
            note = f"f²={effect:.3f}"
        else:
            k = kw["groups"]
            nmin = min_n_f(k - 1, lambda N, k=k: N - k, effect * effect, alpha, power, k + 3)
            note = f"f={effect:.3f}"
        if nmin is None:
            print("按该效应量在 20000 样本内仍达不到目标功效，请检查效应量是否过小（不得为 0 或越界）。")
            print_practice_notes()
            return
        rec = recommend_collect(nmin, extra)
        print(f"按你指定的 {note}：统计最小 N={nmin}；预留 {int(extra*100)}% 无效卷，"
              f"建议实际发放 ≈ {rec} 份。")
        print("    若本研究还包含 Bootstrap 中介/调节/SEM，请与经验下限（中介≥200、"
              "链式中介≥300）取较大值。")
    print_practice_notes()


def _val_of(s):
    return float(s.split("=")[1])


def print_practice_notes():
    print("-" * 64)
    print("实操与口径提醒：")
    print("1. 效应量要来自本方向已发表研究、预实验或 Cohen 惯例；开题通常取小到中等效应")
    print("   做保守估计（样本量留足），不要为少收问卷而取大效应。")
    print("2. 问卷研究通用下限：样本量 ≥ 量表最长条目数的 5–10 倍；做 EFA/CFA/SEM ≥200。")
    print("3. Bootstrap 中介（模型4/6）建议 N≥200，链式中介/调节中介等复杂模型建议 300–500")
    print("   （Fritz & Mackinnon, 2007）；本工具箱 auto_stats.py 的中介/调节为快速预览，")
    print("   正式结果以 PROCESS / JASP 5000 次以上 Bootstrap 复核为准。")
    print("4. 多组比较（ANOVA）样本尽量各组均衡；人口学分组某组过少会影响检验。")
    print("5. 正式开题请用 G*Power 3.1（免费）按同样参数复核并截图附在报告里。")
    print("6. 本估算针对横断面问卷的相关/差异/回归类设计；纵向、实验、多层模型请单独估算。")


def print_cheatsheet(alpha, power, extra):
    print("=" * 64)
    print("心理学问卷研究样本量速查（α=.05，功效=.80，Cohen 小/中/大效应）")
    print("=" * 64)
    rows = [
        ("相关 r", "correlation", {}, [("小 r=.10", None), ("中 r=.30", None), ("大 r=.50", None)]),
        ("回归(3预测)", "regression", {"predictors": 3}, None),
        ("回归(5预测)", "regression", {"predictors": 5}, None),
        ("R²增量(全模型6)", "r2-change", {"tested": 1, "total": 6}, None),
        ("ANOVA(3组)", "anova", {"groups": 3}, None),
        ("ANOVA(4组)", "anova", {"groups": 4}, None),
    ]
    for label, design, kw, _ in rows:
        t = design_table(design, alpha, power, **kw)
        ns = " / ".join(f"{l}{n}" for l, _, n in t)
        print(f"{label:<16}最小N：{ns}")
    print("-" * 64)
    print("说明：上表为统计最小样本；实际发放请再加 10%–20% 无效卷冗余。")
    print_practice_notes()
    print("-" * 64)
    print("用 --design 看某个设计的完整三档表，例如：")
    print("  python tools/sample_size.py --design regression --predictors 5 --effect 0.15")


def main():
    ap = argparse.ArgumentParser(
        description="心理学问卷研究样本量/功效估算（G*Power 等价，纯标准库）")
    ap.add_argument("--design", choices=["correlation", "regression", "r2-change", "anova"],
                    help="研究设计")
    ap.add_argument("--effect", type=float, default=None,
                    help="效应量：相关给 r，回归/增量给 f²，ANOVA 给 f")
    ap.add_argument("--predictors", type=int, default=5, help="regression：预测变量数")
    ap.add_argument("--tested", type=int, default=1, help="r2-change：本次新增检验的预测变量数")
    ap.add_argument("--total", type=int, default=6, help="r2-change：全模型预测变量总数")
    ap.add_argument("--groups", type=int, default=4, help="anova：组数")
    ap.add_argument("--alpha", type=float, default=ALPHA_DEFAULT)
    ap.add_argument("--power", type=float, default=POWER_DEFAULT)
    ap.add_argument("--extra", type=float, default=0.15,
                    help="为无效问卷预留的比例，默认 0.15（15%%）")
    args = ap.parse_args()

    # ---- 入参校验：越界参数给中文友好提示，避免 math.atanh 等抛英文 Traceback ----
    def fail(msg):
        print("错误：" + msg)
        print("示例：相关 --effect 0.3（0<r<1）；回归/增量 --effect 0.15（f²>0）；ANOVA --effect 0.25（f>0）。")
        sys.exit(1)
    if not (0 < args.alpha < 1):
        fail("显著性水平 --alpha 必须在 0 与 1 之间（通常 0.05）。")
    if not (0 < args.power < 1):
        fail("目标功效 --power 必须在 0 与 1 之间（通常 0.80）。")
    if not (0 <= args.extra < 1):
        fail("无效卷预留比例 --extra 必须在 0 与 1 之间（默认 0.15）。")
    if args.design:
        if args.effect is None:
            pass  # 看三档速查表，允许
        elif args.design == "correlation" and not (0 < abs(args.effect) < 1):
            fail("相关效应量 r 必须在 0 与 1 之间（如 0.1 小 / 0.3 中 / 0.5 大）。")
        elif args.design in ("regression", "r2-change") and not (args.effect > 0):
            fail("回归效应量 f² 必须大于 0（如 0.02 小 / 0.15 中 / 0.35 大）。")
        elif args.design == "anova" and not (args.effect > 0):
            fail("ANOVA 效应量 f 必须大于 0（如 0.10 小 / 0.25 中 / 0.40 大）。")
        if args.design == "regression" and args.predictors < 1:
            fail("预测变量数 --predictors 至少为 1。")
        if args.design == "r2-change" and (args.tested < 1 or args.total < args.tested):
            fail("R²增量设计要求 --tested≥1 且 --total（全模型预测变量数）≥ --tested。")
        if args.design == "anova" and args.groups < 2:
            fail("ANOVA 组数 --groups 至少为 2。")

    if not args.design:
        print_cheatsheet(args.alpha, args.power, args.extra)
        return
    kw = {}
    if args.design == "regression":
        kw["predictors"] = args.predictors
    elif args.design == "r2-change":
        kw["tested"], kw["total"] = args.tested, args.total
    elif args.design == "anova":
        kw["groups"] = args.groups
    print_report(args.design, args.alpha, args.power, args.extra, args.effect, **kw)


if __name__ == "__main__":
    main()
