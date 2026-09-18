# -*- coding: utf-8 -*-
"""基础统计量、分布函数与格式助手

纯标准库实现：均值/方差/偏度峰度、Pearson/Spearman 相关、
不完全 beta 与 t/F 分布上尾 p、卡方上尾 p（正则不完全 gamma）、
秩变换与结校正、显著性星号与 p 值格式化。

本模块由 tools/auto_stats.py 拆分而来（v1.53.1），函数体逐行未改动。
"""

import math

# ============ 基础统计量、分布函数与格式助手 ============

def mean(values):
    return sum(values) / len(values) if values else 0.0


def variance(values, ddof=1):
    if len(values) <= ddof:
        return 0.0
    m = mean(values)
    return sum((x - m) ** 2 for x in values) / (len(values) - ddof)


def stdev(values, ddof=1):
    return math.sqrt(variance(values, ddof))


def skew_kurt(values):
    """SPSS/Excel 口径的调整偏度 G1 与超额峰度 G2（Fisher-Pearson 近似无偏）。
    用样本标准差(ddof=1)标准化；n<3 偏度为 None，n<4 峰度为 None。"""
    vals = [v for v in values if v is not None]
    n = len(vals)
    if n < 3:
        return None, None
    m = mean(vals)
    sd = stdev(vals)
    if sd == 0:
        return None, None
    z = [(x - m) / sd for x in vals]
    s3 = sum(t ** 3 for t in z)
    g1 = n / ((n - 1) * (n - 2)) * s3
    g2 = None
    if n >= 4:
        g2 = (n * (n + 1)) / ((n - 1) * (n - 2) * (n - 3)) * sum(t ** 4 for t in z) \
             - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))
    return g1, g2


def normality_tag(g1, g2):
    """社科常用 Kline 判据：|偏度|<3 且 |峰度|<10 视为不严重偏离正态。"""
    if g1 is None or g2 is None:
        return "样本不足"
    if abs(g1) < 3 and abs(g2) < 10:
        return "可接受(|S|<3,|K|<10)"
    return "偏离正态，用Bootstrap/稳健法"


def pearson_r(x, y):
    """Pearson相关系数，成对删除缺失"""
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    if n < 3:
        return None, n
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = mean(xs), mean(ys)
    num = sum((a - mx) * (b - my) for a, b in pairs)
    den_x = math.sqrt(sum((a - mx) ** 2 for a in xs))
    den_y = math.sqrt(sum((b - my) ** 2 for b in ys))
    if den_x == 0 or den_y == 0:
        return None, n
    return num / (den_x * den_y), n


def spearman_r(x, y):
    """Spearman 秩相关（结取平均秩），等价对秩做 Pearson；成对删除缺失。
    适合偏态、有序等级或单调非线性关系；与 scipy.stats.spearmanr 一致。"""
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    if n < 3:
        return None, n
    rx = _rankdata([p[0] for p in pairs])
    ry = _rankdata([p[1] for p in pairs])
    r, _ = pearson_r(rx, ry)
    return r, n


def betacf(a, b, x, max_iter=200, eps=3e-12):
    """不完全beta函数的连分数展开（Numerical Recipes）"""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betai(a, b, x):
    """正则化不完全beta函数 I_x(a,b)"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    bt = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * betacf(a, b, x) / a
    else:
        return 1.0 - bt * betacf(b, a, 1.0 - x) / b


def t_p_two_sided(t, df):
    """t统计量的双尾p值"""
    if df <= 0:
        return None
    x = df / (df + t * t)
    return betai(df / 2.0, 0.5, x)


def sig_mark(p):
    """显著性标记"""
    if p is None:
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def fmt_p(p):
    if p is None:
        return ""
    if p < 0.001:
        return "<.001"
    return f"{p:.3f}".lstrip("0")



def normal_sf(z):
    """标准正态上尾概率 P(Z>z)，用 math.erfc，双精度。"""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def normal_quantile(p):
    """标准正态分位数 Φ⁻¹(p)（Peter Acklam 有理逼近，精度约 1e-9）。"""
    if not 0.0 < p < 1.0:
        return None
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1.0 - 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    if p <= phigh:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
               (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
           ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)


def f_p_value(f, df1, df2):
    """F检验p值"""
    if f <= 0:
        return 1.0
    x = df2 / (df2 + df1 * f)
    return betai(df2 / 2.0, df1 / 2.0, x)


def chi2_pvalue(chi2, df):
    """卡方检验p值，Wilson-Hilferty正态近似（df较大时足够准确）。"""
    if df <= 0 or chi2 <= 0:
        return 1.0
    t = (chi2 / df) ** (1.0 / 3.0)
    z = (t - (1 - 2.0 / (9 * df))) / math.sqrt(2.0 / (9 * df))
    return 1 - 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _rankdata(x):
    """平均秩（结取平均秩，1 基），等价 scipy.stats.rankdata(method='average')。"""
    n = len(x)
    order = sorted(range(n), key=lambda i: x[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and x[order[j + 1]] == x[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _gamma_series(a, x):
    """正则化下不完全 gamma P(a,x) 的级数展开（Numerical Recipes gser）。"""
    ap, s, d = a, 1.0 / a, 1.0 / a
    for _ in range(400):
        ap += 1.0
        d *= x / ap
        s += d
        if abs(d) < abs(s) * 1e-14:
            break
    return s * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_cf(a, x):
    """正则化上不完全 gamma Q(a,x) 的连分式展开（Numerical Recipes gcf）。"""
    fpmin = 1e-300
    b = x + 1.0 - a
    c = 1.0 / fpmin
    d = 1.0 / b
    h = d
    for i in range(1, 401):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < fpmin:
            d = fpmin
        c = b + an / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delt = d * c
        h *= delt
        if abs(delt - 1.0) < 1e-14:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_sf(x, df):
    """卡方分布上尾概率 p=P(χ²_df ≥ x)。"""
    if x <= 0:
        return 1.0
    a, xx = df / 2.0, x / 2.0
    if xx < a + 1.0:
        return 1.0 - _gamma_series(a, xx)
    return _gamma_cf(a, xx)


def _tie_term_from_ranks(ranks):
    """结校正项 Σ(t³−t)，t 为每个结的大小（按平均秩分组）。"""
    counts = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1
    return sum(c ** 3 - c for c in counts.values() if c > 1)


def _z(vals):
    n = len(vals)
    m = sum(vals) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1)) if n > 1 else 0
    return [(v - m) / sd if sd > 0 else 0.0 for v in vals]

# ================================================================ Shapiro-Wilk
# Royston AS R94 实现（v1.73 自 tools/assumption_check.py 下沉到本模块，
# 供前提检验与回归残差正态性复用；权重多项式近似 EnvStats 写法，p 用 Royston 1992/AS R94）
# ================================================================ Shapiro-Wilk
# Royston AS R94 多项式系数（与 R src/library/stats/src/swilk.c、
# scipy 编译的 swilk.f、EnvStats::swGofTestStatistic 同源）
_C1 = [0.0, 0.221157, -0.147981, -2.071190, 4.434685, -2.706056]
_C2 = [0.0, 0.042981, -0.293762, -1.752461, 5.682633, -3.582633]
_C3 = [0.5440, -0.39978, 0.025054, -6.714e-4]      # n 4..11：均值
_C4 = [1.3822, -0.77857, 0.062767, -0.0020322]     # n 4..11：对数标准差
_C5 = [-1.5861, -0.31082, -0.083751, 0.0038915]    # n≥12：均值（关于 ln n）
_C6 = [-0.4803, -0.082676, 0.0030302]              # n≥12：对数标准差
_G = [-2.273, 0.459]                               # n 4..11：gamma 截距
_P_MIN = 1e-19


def _poly(c, x):
    """常数项在前的系数表的 Horner 求值。"""
    r = c[-1]
    for v in reversed(c[:-1]):
        r = r * x + v
    return r


def _norm_upper(z):
    """标准正态上尾概率。z≤1.28 用 erfc（双精度）；z>1.28 用 AS66 的
    Mills 比连分式（与 swilk.f 的 alnorm 同系数），可算到约 1e-150，
    避免极小 p 被过早截到 1e-19。"""
    if z <= 1.28:
        return normal_sf(z)
    r = 0.398942280385
    c1, c2, c3, c4, c5, c6 = (-3.8052e-8, 3.98064794e-4, -0.151679116635,
                              4.8385912808, 0.742380924027, 3.99019417011)
    d1, d2, d3, d4, d5 = (1.00000615302, 1.98615381364, 5.29330324926,
                          -15.1508972451, 30.789933034)
    if z > 18.66:
        return 0.0
    return r * math.exp(-0.5 * z * z) / (
        z + c1 + d1 / (z + c2 + d2 / (z + c3 + d3 / (
            z + c4 + d4 / (z + c5 + d5 / (z + c6))))))


def shapiro_wilk(values):
    """Shapiro-Wilk 正态性检验，返回 (W, p)；n<3 或常量返回 (None, None)。

    权重用 Royston 对期望正态序次统计量的多项式近似（EnvStats 写法）；
    p 值用 Royston (1992) 正态化变换（AS R94），n=3 用精确分布。
    """
    x = sorted(float(v) for v in values)
    n = len(x)
    if n < 3:
        return None, None
    xbar = sum(x) / n
    s2 = sum((v - xbar) ** 2 for v in x) / (n - 1)
    if s2 <= 0:
        return None, None
    # 期望正态序次统计量 m_i = Φ⁻¹((i−3/8)/(n+1/4))
    m = [normal_quantile((i - 0.375) / (n + 0.25)) for i in range(1, n + 1)]
    ssm = sum(v * v for v in m)
    cvec = [v / math.sqrt(ssm) for v in m]
    a = [0.0] * n
    if n == 3:
        # AS R94 特例：权重恰为 ±1/√2（Fortran swilk 的 n==3 分支）
        a = [math.sqrt(0.5), 0.0, -math.sqrt(0.5)]
    else:
        y = 1.0 / math.sqrt(n)
        a[n - 1] = cvec[n - 1] + _poly(_C1, y)
        a[0] = -a[n - 1]
    if n == 3:
        pass
    elif n <= 5:
        phi = (ssm - 2.0 * m[n - 1] ** 2) / (1.0 - 2.0 * a[n - 1] ** 2)
        for i in range(1, n - 1):
            a[i] = m[i] / math.sqrt(phi)
    else:
        a[n - 2] = cvec[n - 2] + _poly(_C2, y)
        phi = (ssm - 2.0 * m[n - 1] ** 2 - 2.0 * m[n - 2] ** 2) / \
              (1.0 - 2.0 * a[n - 1] ** 2 - 2.0 * a[n - 2] ** 2)
        for i in range(2, n - 2):
            a[i] = m[i] / math.sqrt(phi)
        a[1] = -a[n - 2]
    num = sum(a[i] * x[i] for i in range(n))
    w = num * num / ((n - 1) * s2)
    if w > 1.0:
        w = 1.0
    w1 = 1.0 - w
    if w1 <= 0:
        return w, 1.0
    if n == 3:
        # 精确 p：6/π·(arcsin(√W) − π/3)
        p = (6.0 / math.pi) * (math.asin(math.sqrt(w)) - math.pi / 3.0)
        return w, min(1.0, max(_P_MIN, p))
    ylog = math.log(w1)
    if n <= 11:
        gamma = _poly(_G, float(n))
        if ylog >= gamma:
            p = _P_MIN
        else:
            zeta = -math.log(gamma - ylog)
            mu = _poly(_C3, float(n))
            sd = math.exp(_poly(_C4, float(n)))
            p = _norm_upper((zeta - mu) / sd)
    else:
        xx = math.log(float(n))
        mu = _poly(_C5, xx)
        sd = math.exp(_poly(_C6, xx))
        p = _norm_upper((ylog - mu) / sd)
    # n≤11 分支按 AS R94 在 gamma 处截到 1e-19；n≥12 允许报告更小的 p（远尾展开）
    p = min(1.0, p)
    if n <= 11:
        p = max(_P_MIN, p)
    return w, p


def durbin_watson(residuals):
    """Durbin-Watson 统计量 DW=Σ(e_i−e_{i-1})²/Σe_i²；n<2 或残差常量返回 None。

    取值 0~4：接近 2 表示残差无一阶自相关；明显 <1 正自相关、>3 负自相关。
    严格判定应对照 Durbin-Watson 临界值表（dL/dU，随 n 与预测变量数变化），
    1.5~2.5 只是论文中常见的经验可接受区间，不是统一标准。
    """
    n = len(residuals)
    if n < 2:
        return None
    den = sum(e * e for e in residuals)
    if den <= 0:
        return None
    return sum((residuals[i] - residuals[i - 1]) ** 2 for i in range(1, n)) / den
