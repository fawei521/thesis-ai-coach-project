#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
效应量换算与复核工具（心理学问卷研究）

用途：
  当你已经从 JASP/SPSS 输出或文献里拿到 t、F、χ²、r，或两组的均值/标准差/n 时，
  用它换算论文必须报告的效应量及其置信区间，并给出小/中/大口判：
    - Cohen's d / Hedges' g（两独立组，可由均值标准差或 t 值换算）
    - 配对 d_z（前后测/两条件）
    - 相关 r（可直接给 r 和 n 求置信区间，或由 t 值换算；r↔d 互转）
    - η² / 偏 η² / ε²（方差分析，可由 F 值或平方和换算）
    - Cramér's V / φ（卡方检验）

特点：纯 Python 标准库；确定性计算；只做换算与教学复核，不碰原始数据。
口径与 psychology/stats-guide.md、tools/stats/compare.py 完全一致：
  r：.1/.3/.5 为小/中/大；d：.2/.5/.8；η²、ε²：.01/.06/.14；Cramér's V：.1/.3/.5。

常用示例（PowerShell，在项目根目录）：
  # 两组均值标准差 -> d、g、95%CI
  python tools\\effect_size.py d --m1 3.8 --sd1 0.9 --n1 60 --m2 3.3 --sd2 0.85 --n2 60
  # 已知独立样本 t(118)=2.65 -> d
  python tools\\effect_size.py d-t --t 2.65 --n1 60 --n2 60
  # 配对：前后差值均值 0.4、差值标准差 1.1、n=60
  python tools\\effect_size.py paired-d --mean-diff 0.4 --sd-diff 1.1 --n 60
  # 相关 r=.34，n=120，求 95%CI
  python tools\\effect_size.py r --r 0.34 --n 120
  # 由 t(118)=2.65 反推 r
  python tools\\effect_size.py r-t --t 2.65 --df 118
  # 单因素方差 F(2,117)=5.20 -> 偏 η²
  python tools\\effect_size.py eta --F 5.20 --df1 2 --df2 117
  # 卡方 χ²(1)=6.10，N=200，2×2 表 -> φ 与 Cramér's V
  python tools\\effect_size.py v --chi2 6.10 --n 200 --rows 2 --cols 2
  # r 与 d 互转
  python tools\\effect_size.py convert --r 0.30
  python tools\\effect_size.py convert --d 0.50

说明：d、r 的置信区间为教科书常用近似（d 用 Borenstein 方差近似，r 用 Fisher z 变换），
精确区间请以 JASP/SPSS 输出为准。效应量必须来自你自己的真实检验结果，
不得为了凑“中/大效应”而反推或篡改数字；不显著也要如实报告效应量与区间。
"""

import argparse
import math
import os
import sys

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与 auto_stats.py 同款，避免 χ² η φ 崩）---
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 常用置信水平的标准正态临界值 z
_Z_CRIT = {90: 1.6448536269514722, 95: 1.959963984540054, 99: 2.5758293035489004}


def _z(level):
    if level not in _Z_CRIT:
        raise ValueError("置信水平仅支持 90 / 95 / 99（默认 95）")
    return _Z_CRIT[level]


def _ci_str(lo, hi, unit=""):
    return f"[{lo:.3f}, {hi:.3f}]{unit}"


# ---------------- 口判（阈值与 stats-guide / compare.py 一致）----------------
def tag_r(value):
    a = abs(value)
    return "可忽略(≈0)" if a < .1 else "小效应" if a < .3 else "中效应" if a < .5 else "大效应"


def tag_d(value):
    a = abs(value)
    return "可忽略(≈0)" if a < .2 else "小效应" if a < .5 else "中效应" if a < .8 else "大效应"


def tag_eta(value):
    a = abs(value)
    return "可忽略(≈0)" if a < .01 else "小效应" if a < .06 else "中效应" if a < .14 else "大效应"


def tag_v(value):
    a = abs(value)
    return "可忽略(≈0)" if a < .1 else "小效应" if a < .3 else "中效应" if a < .5 else "大效应"


def _header(title):
    print("=" * 64)
    print(title)
    print("=" * 64)


def _footer():
    print("-" * 64)
    print("口径：r .1/.3/.5、d .2/.5/.8、η²与ε² .01/.06/.14、V .1/.3/.5 为小/中/大。")
    print("脚本用于快速预览与教学复核，精确数值以 JASP/SPSS 正式输出为准；")
    print("效应量必须来自真实检验结果，不显著也如实报告，不得为凑阈值反推或改数。")


# ---------------- Cohen's d（两独立组，由均值标准差）----------------
def cohens_d_from_means(a):
    for nm in ("m1", "sd1", "n1", "m2", "sd2", "n2"):
        if getattr(a, nm) is None:
            raise ValueError(f"缺少参数 --{nm}")
    m1, sd1, n1, m2, sd2, n2 = a.m1, a.sd1, a.n1, a.m2, a.sd2, a.n2
    if n1 < 2 or n2 < 2:
        raise ValueError("每组样本量需 ≥2")
    if sd1 <= 0 or sd2 <= 0:
        raise ValueError("标准差必须为正数")
    df = n1 + n2 - 2
    sp2 = ((n1 - 1) * sd1 ** 2 + (n2 - 1) * sd2 ** 2) / df
    sp = math.sqrt(sp2)
    d = (m1 - m2) / sp
    _report_d(d, n1, n2, df, sp, source="两组均值/标准差（合并标准差 Sp）", ci=a.ci)


def _report_d(d, n1, n2, df, sp=None, source="", ci=95):
    j = 1.0 - 3.0 / (4.0 * (n1 + n2) - 9.0)   # Hedges 校正因子 J
    g = j * d
    se = math.sqrt((n1 + n2) / (n1 * n2) + d ** 2 / (2.0 * (n1 + n2)))
    zc = _z(ci)
    lo, hi = d - zc * se, d + zc * se
    _header("Cohen's d（两独立组）")
    print(f"数据来源：{source}")
    if sp is not None:
        print(f"合并标准差 Sp = {sp:.3f}")
    print(f"自由度 df = {df}")
    print(f"Cohen's d = {d:.3f}　→　{tag_d(d)}")
    print(f"Hedges' g = {g:.3f}（小样本校正后，通常与 d 并列报告）")
    print(f"d 的 {ci}%CI ≈ {_ci_str(lo, hi)}（Borenstein 方差近似，SE={se:.3f}）")
    print(f"论文可写：两组差异{'' if abs(d) >= .2 else '（按效应量）'}为{tag_d(d).replace('效应','')}效应（d={d:.2f}，"
          f"95%CI[{lo:.2f}, {hi:.2f}]）。")
    _footer()


# ---------------- d 由独立样本 t 值 ----------------
def cohens_d_from_t(a):
    if a.t is None or a.n1 is None or a.n2 is None:
        raise ValueError("需要 --t、--n1、--n2")
    if a.n1 < 2 or a.n2 < 2:
        raise ValueError("每组样本量需 ≥2")
    n1, n2, t = a.n1, a.n2, a.t
    d = t * math.sqrt(1.0 / n1 + 1.0 / n2)   # 独立样本 t 与 d 的精确关系
    df = n1 + n2 - 2
    _report_d(d, n1, n2, df, sp=None, source=f"独立样本 t={t:.3f}（d=t·√(1/n1+1/n2)）", ci=a.ci)


# ---------------- 配对 d_z ----------------
def paired_d(a):
    n = a.n
    if n is None or n < 2:
        raise ValueError("需要 --n 且 ≥2")
    if a.t is not None:
        dz = a.t / math.sqrt(n)
        src = f"配对 t={a.t:.3f}（d_z=t/√n）"
    elif a.mean_diff is not None and a.sd_diff is not None and a.sd_diff > 0:
        dz = a.mean_diff / a.sd_diff
        src = "前后差值均值 / 差值标准差"
    else:
        raise ValueError("请提供 --t 或同时提供 --mean-diff 与 --sd-diff（且差值标准差>0）")
    df = n - 1
    se = math.sqrt(1.0 / n + dz ** 2 / (2.0 * n))   # 近似 SE
    zc = _z(a.ci)
    lo, hi = dz - zc * se, dz + zc * se
    _header("配对 Cohen's d_z（前后测 / 两条件）")
    print(f"数据来源：{src}")
    print(f"自由度 df = {df}")
    print(f"配对 d_z = {dz:.3f}　→　{tag_d(dz)}（注意 d_z 用差值标准差，口径不同于独立组 d）")
    print(f"d_z 的 {a.ci}%CI ≈ {_ci_str(lo, hi)}（近似，建议以 JASP/SPSS 配对检验输出为准）")
    _footer()


# ---------------- 相关 r（Fisher z 置信区间 + 换算 d）----------------
def report_r(r, n, ci, source=""):
    if n is None or n <= 3:
        raise ValueError("求相关的置信区间需要 n>3")
    if not -1.0 < r < 1.0:
        raise ValueError("r 必须在 (-1,1) 之间")
    zf = math.atanh(r)                 # Fisher z
    se = 1.0 / math.sqrt(n - 3)
    zc = _z(ci)
    lo = math.tanh(zf - zc * se)
    hi = math.tanh(zf + zc * se)
    d_from_r = 2.0 * r / math.sqrt(1.0 - r ** 2)
    _header("Pearson 相关 r")
    if source:
        print(f"数据来源：{source}")
    print(f"r = {r:.3f}　→　{tag_r(r)}，n = {n}")
    print(f"r 的 {ci}%CI ≈ {_ci_str(lo, hi)}（Fisher z 变换）")
    print(f"换算为标准化均数差参考：d ≈ {d_from_r:.3f}（{tag_d(d_from_r)}）")
    _footer()


def r_from_args(a):
    if a.r is None or a.n is None:
        raise ValueError("需要 --r 与 --n")
    report_r(a.r, a.n, a.ci)


def r_from_t(a):
    if a.t is None or a.df is None or a.df <= 0:
        raise ValueError("需要 --t 与 --df（df>0）")
    t, df = a.t, a.df
    r = math.copysign(math.sqrt(t ** 2 / (t ** 2 + df)), t)
    n = a.n if a.n is not None else df + 2   # 简单 Pearson：检验 df=N-2
    report_r(r, n, a.ci, source=f"t={t:.3f}, df={df}（r=sign(t)·√(t²/(t²+df))）")


# ---------------- 方差分析效应量 ----------------
def eta(a):
    if a.F is None or a.df1 is None or a.df2 is None:
        if a.ss_between is None or a.ss_within is None:
            raise ValueError("请提供 --F --df1 --df2，或提供 --ss-between --ss-within（及 --df1 --df2）")
    _header("方差分析效应量")
    if a.F is not None and a.df1 is not None and a.df2 is not None and a.df2 > 0:
        peta = (a.F * a.df1) / (a.F * a.df1 + a.df2)
        print(f"由 F({a.df1},{a.df2})={a.F:.3f}：")
        print(f"偏 η²(partial η²) = F·df1/(F·df1+df2) = {peta:.3f}　→　{tag_eta(peta)}")
        print("（单因素被试间设计中 偏η² = η²；多因素设计里此值是偏η²，勿与η²混用）")
    if a.ss_between is not None and a.ss_within is not None:
        ssb, ssw = a.ss_between, a.ss_within
        sst = ssb + ssw
        eta2 = ssb / sst if sst > 0 else float("nan")
        print(f"由平方和 SS组间={ssb:.3f}, SS组内={ssw:.3f}：")
        print(f"η² = SS组间/SS总 = {eta2:.3f}　→　{tag_eta(eta2)}")
        if a.df1 is not None and a.df2 is not None and a.df2 > 0:
            msw = ssw / a.df2
            eps2 = (ssb - a.df1 * msw) / sst if sst > 0 else float("nan")
            eps2 = max(eps2, 0.0)   # 无效应时 ε² 估计可能微负，截断为 0（与 compare.py 一致）
            print(f"ε² = (SS组间-df组间·MS组内)/SS总 = {eps2:.3f}　→　{tag_eta(eps2)}（推荐，偏差更小）")
    _footer()


# ---------------- 卡方效应量 ----------------
def cramers_v(a):
    if a.chi2 is None or a.n is None or a.rows is None or a.cols is None:
        raise ValueError("需要 --chi2 --n --rows --cols")
    chi2, n, r, c = a.chi2, a.n, a.rows, a.cols
    if n <= 0 or r < 2 or c < 2:
        raise ValueError("n 需为正，行数/列数需 ≥2")
    dfmin = min(r - 1, c - 1)
    v = math.sqrt(chi2 / (n * dfmin))
    phi = math.sqrt(chi2 / n)
    df_chi = (r - 1) * (c - 1)
    _header("卡方检验效应量")
    print(f"χ²(df={df_chi})={chi2:.3f}，N={n}，列联表 {r}×{c}")
    print(f"Cramér's V = √(χ²/(N·df_min)) = {v:.3f}，df_min={dfmin}　→　{tag_v(v)}")
    if r == 2 and c == 2:
        print(f"φ(phi) = √(χ²/N) = {phi:.3f}（2×2 表通常报告 φ；φ 与此时的 V 相等）")
    print("卡方只回答“是否关联”，V/φ 回答“关联多强”，两者都要报告。")
    _footer()


# ---------------- r <-> d 互转 ----------------
def convert(a):
    _header("r ↔ d 互转（等价换算，bivariate 关系）")
    if a.r is not None:
        if not -1 < a.r < 1:
            raise ValueError("r 必须在 (-1,1) 之间")
        d = 2 * a.r / math.sqrt(1 - a.r ** 2)
        print(f"r = {a.r:.3f}  →  d = 2r/√(1-r²) = {d:.3f}（{tag_d(d)}）")
    elif a.d is not None:
        r = a.d / math.sqrt(a.d ** 2 + 4)
        print(f"d = {a.d:.3f}  →  r = d/√(d²+4) = {r:.3f}（{tag_r(r)}）")
    else:
        raise ValueError("请提供 --r 或 --d")
    print("注意：该换算基于等价的二变量关系假设，仅用于跨研究效应量粗比，勿替代原始检验。")
    _footer()


def build_parser():
    p = argparse.ArgumentParser(
        description="效应量换算与复核工具（d/g/d_z、r、η²/ε²、Cramér's V/φ，纯标准库）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("d", help="两独立组：由均值标准差求 Cohen's d / Hedges' g 与 CI")
    sp.add_argument("--m1", type=float, help="第1组均值"); sp.add_argument("--sd1", type=float, help="第1组标准差")
    sp.add_argument("--n1", type=int, help="第1组样本量"); sp.add_argument("--m2", type=float, help="第2组均值")
    sp.add_argument("--sd2", type=float, help="第2组标准差"); sp.add_argument("--n2", type=int, help="第2组样本量")
    sp.add_argument("--ci", type=int, default=95, help="置信水平 90/95/99，默认95")
    sp.set_defaults(func=cohens_d_from_means)

    sp = sub.add_parser("d-t", help="两独立组：由 t 值求 d")
    sp.add_argument("--t", type=float, help="独立样本 t 值（带符号）")
    sp.add_argument("--n1", type=int); sp.add_argument("--n2", type=int)
    sp.add_argument("--ci", type=int, default=95)
    sp.set_defaults(func=cohens_d_from_t)

    sp = sub.add_parser("paired-d", help="配对设计：求 d_z（给差值或配对t）")
    sp.add_argument("--mean-diff", type=float, help="前后差值均值")
    sp.add_argument("--sd-diff", type=float, help="前后差值标准差")
    sp.add_argument("--t", type=float, help="或直接给配对 t 值")
    sp.add_argument("--n", type=int)
    sp.add_argument("--ci", type=int, default=95)
    sp.set_defaults(func=paired_d)

    sp = sub.add_parser("r", help="由 r 与 n 求置信区间并换算 d")
    sp.add_argument("--r", type=float); sp.add_argument("--n", type=int)
    sp.add_argument("--ci", type=int, default=95)
    sp.set_defaults(func=r_from_args)

    sp = sub.add_parser("r-t", help="由 t、df 反推 r")
    sp.add_argument("--t", type=float); sp.add_argument("--df", type=int)
    sp.add_argument("--n", type=int, default=None, help="默认 df+2（简单相关）")
    sp.add_argument("--ci", type=int, default=95)
    sp.set_defaults(func=r_from_t)

    sp = sub.add_parser("eta", help="方差分析：由 F 或平方和求 偏η² / η² / ε²")
    sp.add_argument("--F", type=float); sp.add_argument("--df1", type=int); sp.add_argument("--df2", type=int)
    sp.add_argument("--ss-between", type=float); sp.add_argument("--ss-within", type=float)
    sp.set_defaults(func=eta)

    sp = sub.add_parser("v", help="卡方：求 Cramér's V（2×2 同时给 φ）")
    sp.add_argument("--chi2", type=float); sp.add_argument("--n", type=int)
    sp.add_argument("--rows", type=int); sp.add_argument("--cols", type=int)
    sp.set_defaults(func=cramers_v)

    sp = sub.add_parser("convert", help="r 与 d 互转")
    sp.add_argument("--r", type=float); sp.add_argument("--d", type=float)
    sp.set_defaults(func=convert)
    return p


def main():
    parser = build_parser()
    a = parser.parse_args()
    if not getattr(a, "func", None):
        parser.print_help()
        return
    try:
        a.func(a)
    except ValueError as e:
        print(f"✗ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
