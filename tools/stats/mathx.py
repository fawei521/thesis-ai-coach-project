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
