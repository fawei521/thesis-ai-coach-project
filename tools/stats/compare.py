# -*- coding: utf-8 -*-
"""组间差异检验与卡方独立性检验

Levene/Brown-Forsythe 方差齐性、独立样本 t 与 Welch t、
单因素 ANOVA 与 Welch ANOVA、Cohen's d 与 η²、Bonferroni 事后；
非参数 Mann-Whitney U 与 Kruskal-Wallis H（含结校正）；
人口学交叉卡方 χ²/Cramér's V（2×2 Yates 校正）。

本模块由 tools/auto_stats.py 拆分而来（v1.53.1），函数体逐行未改动。
"""

import csv
import math

from .mathx import _rankdata, _tie_term_from_ranks, chi2_sf, f_p_value, fmt_p, mean, sig_mark, stdev, t_p_two_sided, variance

# ============ 组间差异检验与卡方独立性检验 ============

def _detect_group_cols(headers, data, matrix, scales):
    """识别人口学分组列（非量表题、2类及以上且数值≤4类/文本≤10类），
    返回 [(列名, 每样本组标签序列(缺失None))]。"""
    scale_items = set()
    for conf in scales.values():
        scale_items.update(conf["items"])
    out = []
    for ci, c in enumerate(headers):
        if c in scale_items:
            continue
        col = matrix.get(c)
        labels, numeric = [], True
        if col and any(v is not None for v in col):
            for v in col:
                if v is None:
                    labels.append(None)
                else:
                    labels.append(str(int(v)) if float(v).is_integer() else str(v))
        else:
            numeric = False
            for r in data:
                t = r[ci].strip() if ci < len(r) else ""
                labels.append(t if t else None)
        vals = [x for x in labels if x is not None]
        if not vals:
            continue
        uniq = set(vals)
        max_cat = 10 if not numeric else 4
        if 2 <= len(uniq) <= max_cat:
            out.append((c, labels))
    return out


def _cohens_d(a, b):
    n1, n2 = len(a), len(b)
    v1, v2 = variance(a), variance(b)
    sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)
    if sp2 <= 0:
        return None
    return (mean(a) - mean(b)) / math.sqrt(sp2)


def _levene(groups, center="median"):
    """Levene/Brown-Forsythe 方差齐性检验。center='median' 即 Brown-Forsythe
    （更稳健、推荐），'mean' 为传统 Levene。对绝对离差做单因素 ANOVA，
    统计量服从 F(k-1, N-k)。返回 (W, p)。"""
    use = [g for g in groups if len(g) >= 2]
    k = len(use)
    if k < 2:
        return None, None
    zgroups = []
    for g in use:
        if center == "median":
            sg = sorted(g)
            m_ = len(sg)
            c = sg[m_ // 2] if m_ % 2 else (sg[m_ // 2 - 1] + sg[m_ // 2]) / 2
        else:
            c = mean(g)
        zgroups.append([abs(x - c) for x in g])
    N = sum(len(z) for z in zgroups)
    grand_z = sum(sum(z) for z in zgroups) / N
    ssb = sum(len(z) * (mean(z) - grand_z) ** 2 for z in zgroups)
    ssw = sum(sum((x - mean(z)) ** 2 for x in z) for z in zgroups)
    dfb, dfw = k - 1, N - k
    if dfw <= 0 or ssw <= 0:
        return None, None
    W = (ssb / dfb) / (ssw / dfw)
    return W, f_p_value(W, dfb, dfw)


def _welch_t(a, b):
    """Welch 独立样本 t（不要求等方差），返回 (t, df, p)。"""
    n1, n2 = len(a), len(b)
    v1, v2 = variance(a), variance(b)
    a1, a2 = v1 / n1, v2 / n2
    se2 = a1 + a2
    if se2 <= 0:
        return None, None, None
    t = (mean(a) - mean(b)) / math.sqrt(se2)
    df = se2 ** 2 / (a1 ** 2 / (n1 - 1) + a2 ** 2 / (n2 - 1))
    return t, df, t_p_two_sided(t, df)


def _welch_anova(groups):
    """Welch 单因素方差分析（不要求等方差），返回 (F, df1, df2, p)。
    公式见 Liu (2015) / R oneway.test。"""
    use = [g for g in groups if len(g) >= 2]
    k = len(use)
    if k < 2:
        return None, None, None, None
    w = [len(g) / variance(g) if variance(g) > 0 else 0.0 for g in use]
    wtot = sum(w)
    if wtot <= 0:
        return None, None, None, None
    xw = sum(w[j] * mean(use[j]) for j in range(k)) / wtot
    num = sum(w[j] * (mean(use[j]) - xw) ** 2 for j in range(k)) / (k - 1)
    D = sum((1.0 / (len(use[j]) - 1)) * (1.0 - w[j] / wtot) ** 2
            for j in range(k))
    den = 1.0 + 2.0 * (k - 2) / (k ** 2 - 1) * D
    F = num / den
    df1 = k - 1
    df2 = (k ** 3 - k) / (3.0 * D) if D > 0 else float("inf")
    p = f_p_value(F, df1, df2) if df2 != float("inf") else None
    return F, df1, df2, p


def mann_whitney_u(a, b):
    """Mann-Whitney U（两独立样本，非参数 t 替代）。
    返回 (U, z, p双侧, r效应量)；大样本正态近似（含结校正与连续性校正），
    与 scipy.stats.mannwhitneyu(method='asymptotic') 一致。n<20 建议用 JASP 精确检验。"""
    n1, n2 = len(a), len(b)
    N = n1 + n2
    ranks = _rankdata(a + b)
    R1 = sum(ranks[:n1])
    U1 = R1 - n1 * (n1 + 1) / 2.0
    U2 = n1 * n2 - U1
    U = min(U1, U2)
    mu = n1 * n2 / 2.0
    T = _tie_term_from_ranks(ranks)
    var = n1 * n2 / 12.0 * ((N + 1) - T / (N * (N - 1))) if N > 1 else 0.0
    if var <= 0:
        return U, None, None, None
    cc = 0.5 if U < mu else -0.5
    z = (U - mu + cc) / math.sqrt(var)
    p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))
    r_eff = abs(z) / math.sqrt(N)
    return U, z, min(max(p, 0.0), 1.0), r_eff


def kruskal_wallis(groups):
    """Kruskal-Wallis H（k 个独立样本，ANOVA 的非参数替代）。
    返回 (H校正结, df, p, ε²效应量)，与 scipy.stats.kruskal 一致。"""
    use = [g for g in groups if len(g) >= 1]
    k = len(use)
    N = sum(len(g) for g in use)
    if k < 2 or N <= k:
        return None, k - 1, None, None
    comb = [v for g in use for v in g]
    ranks = _rankdata(comb)
    idx = 0
    H = 0.0
    for g in use:
        n = len(g)
        R = sum(ranks[idx:idx + n])
        idx += n
        H += R * R / n
    H = 12.0 / (N * (N + 1)) * H - 3.0 * (N + 1)
    T = _tie_term_from_ranks(ranks)
    denom = N ** 3 - N
    C = 1.0 - T / denom if denom > 0 else 1.0
    Hc = H / C if C > 0 else H
    p = chi2_sf(Hc, k - 1)
    eps = (Hc - k + 1) / (N - k) if N > k else 0.0
    eps = max(eps, 0.0)  # 完全无效应时 epsilon² 可能为微小负（估计偏差），截断为0
    return Hc, k - 1, p, eps


def group_difference_analysis(headers, data, matrix, scales, score_matrix,
                              total_cols, output=None, nonparametric=False):
    """人口学差异：2组用独立样本t检验(等方差)+Cohen's d；
    3组及以上用单因素方差分析(ANOVA)+η²+Bonferroni校正事后两两比较。
    nonparametric=True 时改用非参数检验（不要求正态/方差齐）：
    2组 Mann-Whitney U（效应量 r），3组及以上 Kruskal-Wallis H（效应量 ε²）。
    对每个人口学分组列 × 每个量表总分进行。"""
    group_cols = _detect_group_cols(headers, data, matrix, scales)
    if not group_cols or not total_cols:
        return None
    rows = []
    print("\n" + "=" * 60)
    if nonparametric:
        print("七、人口学差异分析（非参数：Mann-Whitney U / Kruskal-Wallis H）")
        print("  适用：因变量明显偏态、有序等级、或 t/ANOVA 正态前提不满足时")
    else:
        print("七、人口学差异分析（独立样本t / 单因素ANOVA）")
    print("=" * 60)
    for gname, glabels in group_cols:
        for ycol in total_cols:
            y = score_matrix.get(ycol)
            if not y:
                continue
            gd = {}
            for i, lab in enumerate(glabels):
                if lab is not None and i < len(y) and y[i] is not None:
                    gd.setdefault(lab, []).append(float(y[i]))
            try:
                keys = sorted(gd, key=lambda k: float(k))
            except ValueError:
                keys = sorted(gd)
            gd = {k: gd[k] for k in keys if len(gd[k]) >= 2}
            if len(gd) < 2 or len(gd) > 8:
                continue
            yshort = ycol.replace("总分", "")
            desc = "；".join(f"{k}组 M={mean(v):.2f},SD={stdev(v):.2f},n={len(v)}"
                             for k, v in gd.items())

            def _mdn(v):
                s = sorted(v)
                n = len(s)
                mid = n // 2
                return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0

            if nonparametric:
                ndesc = "；".join(f"{k}组 中位数={_mdn(v):.2f},n={len(v)}" for k, v in gd.items())
                if len(gd) == 2:
                    (k1, a), (k2, b) = list(gd.items())[0], list(gd.items())[1]
                    U, z, p, r_eff = mann_whitney_u(a, b)
                    if z is None:
                        continue
                    rt = "小" if r_eff < .3 else "中" if r_eff < .5 else "大"
                    sig = "差异显著" if p < .05 else "差异不显著"
                    print(f"\n{gname} × {yshort}（Mann-Whitney U，非参数）：{k1}组 vs {k2}组")
                    print(f"    {ndesc}")
                    print(f"    U={U:.0f}, z={z:.3f}, p={fmt_p(p)}, r={r_eff:.3f}（{rt}效应）→ {sig}")
                    if min(len(a), len(b)) < 20:
                        print("    提示：某组 n<20，建议在 JASP 中改用精确检验（Exact）复核")
                    rows.append({"分组变量": gname, "因变量": yshort,
                                 "检验": "Mann-Whitney U(非参数)", "统计量": f"U={U:.0f}",
                                 "df": "-", "p": fmt_p(p), "效应量": f"r={r_eff:.3f}({rt})",
                                 "方差齐性": "非参数不要求正态/方差齐", "稳健检验(Welch)": "-",
                                 "详情": ndesc + f"；z={z:.3f}；{sig}"})
                else:
                    keys2 = list(gd.keys())
                    groups = [gd[k] for k in keys2]
                    H, dfn, p, eps = kruskal_wallis(groups)
                    if H is None:
                        continue
                    et = "小" if eps < .06 else "中" if eps < .14 else "大"
                    sig = "差异显著" if p < .05 else "差异不显著"
                    print(f"\n{gname} × {yshort}（Kruskal-Wallis H，非参数，{len(groups)}组）")
                    print(f"    {ndesc}")
                    print(f"    H({dfn})={H:.3f}, p={fmt_p(p)}, ε²={eps:.3f}（{et}效应）→ {sig}")
                    print("    事后两两比较请用 Dunn 检验（JASP：非参数检验→独立样本→Dunn事后，含Bonferroni校正）")
                    rows.append({"分组变量": gname, "因变量": yshort,
                                 "检验": "Kruskal-Wallis H(非参数)", "统计量": f"H={H:.3f}",
                                 "df": dfn, "p": fmt_p(p), "效应量": f"ε²={eps:.3f}({et})",
                                 "方差齐性": "非参数不要求正态/方差齐", "稳健检验(Welch)": "-",
                                 "详情": ndesc + f"；{sig}；事后用Dunn检验(JASP)"})
                continue

            if len(gd) == 2:
                (k1, a), (k2, b) = list(gd.items())[0], list(gd.items())[1]
                n1, n2 = len(a), len(b)
                sp2 = ((n1 - 1) * variance(a) + (n2 - 1) * variance(b)) / (n1 + n2 - 2)
                if sp2 <= 0:
                    continue
                t = (mean(a) - mean(b)) / math.sqrt(sp2 * (1 / n1 + 1 / n2))
                df = n1 + n2 - 2
                p = t_p_two_sided(t, df)
                d = _cohens_d(a, b)
                dt = "可忽略" if abs(d) < .2 else "小" if abs(d) < .5 else "中" if abs(d) < .8 else "大"
                lw, levp = _levene([a, b])
                wt, wdf, wp = _welch_t(a, b)
                equal = (levp is None) or (levp >= .05)
                levtxt = ("Levene/Brown-Forsythe：无法计算（按方差齐处理）" if levp is None
                          else f"Levene p={fmt_p(levp)}（方差齐性{'成立' if equal else '不成立'}）")
                welchtxt = f"Welch t({wdf:.0f})={wt:.3f}, p={fmt_p(wp)}"
                if equal:
                    test_name, stat_t, df_t, p_t = "独立样本t", f"t={t:.3f}", df, p
                    rec = "方差齐，采用等方差 t 检验"
                else:
                    test_name, stat_t, df_t, p_t = "独立样本t(Welch)", f"t={wt:.3f}", round(wdf, 1), wp
                    rec = "方差不齐，采用 Welch t 检验"
                sig = "差异显著" if p_t < .05 else "差异不显著"
                print(f"\n{gname} × {yshort}（{test_name}）：{k1}组 vs {k2}组")
                print(f"    {desc}")
                print(f"    {levtxt}")
                print(f"    等方差 t({df})={t:.3f}, p={fmt_p(p)}；{welchtxt}")
                print(f"    Cohen's d={d:.3f}（{dt}效应）→ {sig}（{rec}）")
                rows.append({"分组变量": gname, "因变量": yshort, "检验": test_name,
                             "统计量": stat_t, "df": df_t, "p": fmt_p(p_t),
                             "效应量": f"d={d:.3f}({dt})",
                             "方差齐性": levtxt, "稳健检验(Welch)": welchtxt,
                             "详情": desc + f"；{sig}；{rec}"})
            else:
                keys2 = list(gd.keys())
                groups = [gd[k] for k in keys2]
                N = sum(len(g) for g in groups)
                k = len(groups)
                grand = sum(sum(g) for g in groups) / N
                ssb = sum(len(g) * (mean(g) - grand) ** 2 for g in groups)
                ssw = sum(sum((x - mean(g)) ** 2 for x in g) for g in groups)
                dfb, dfw = k - 1, N - k
                if dfw <= 0 or ssw <= 0:
                    continue
                msw = ssw / dfw
                F = (ssb / dfb) / msw
                p = f_p_value(F, dfb, dfw)
                eta = ssb / (ssb + ssw)
                et = "小" if eta < .06 else "中" if eta < .14 else "大"
                lw, levp = _levene(groups)
                Fw, wd1, wd2, wp = _welch_anova(groups)
                equal = (levp is None) or (levp >= .05)
                levtxt = ("Levene/Brown-Forsythe：无法计算（按方差齐处理）" if levp is None
                          else f"Levene p={fmt_p(levp)}（方差齐性{'成立' if equal else '不成立'}）")
                welchtxt = (f"Welch F({wd1},{wd2:.0f})={Fw:.3f}, p={fmt_p(wp)}"
                           if Fw is not None else "Welch：无法计算")
                post = []
                npairs = k * (k - 1) // 2
                for ii in range(k):
                    for jj in range(ii + 1, k):
                        ga, gb = groups[ii], groups[jj]
                        tt = (mean(ga) - mean(gb)) / math.sqrt(msw * (1 / len(ga) + 1 / len(gb)))
                        pp = t_p_two_sided(tt, dfw)
                        if pp * npairs < .05:
                            post.append(f"{keys2[ii]}组>{keys2[jj]}组" if mean(ga) > mean(gb)
                                        else f"{keys2[jj]}组>{keys2[ii]}组")
                post_txt = "；".join(post) if post else "事后两两均不显著"
                if equal:
                    test_name, stat_F, df_F, p_F = "单因素ANOVA", f"F={F:.3f}", f"{dfb},{dfw}", p
                    rec = "方差齐，采用等方差 ANOVA＋Bonferroni事后"
                    sig = "差异显著" if p < .05 else "差异不显著"
                    post_show = f"Bonferroni事后：{post_txt}"
                else:
                    test_name, stat_F, df_F, p_F = "单因素ANOVA(Welch)", f"F={Fw:.3f}", f"{wd1},{wd2:.0f}", wp
                    rec = "方差不齐，采用 Welch ANOVA；事后请用 Games-Howell（JASP/SPSS）"
                    sig = "差异显著" if (wp is not None and wp < .05) else "差异不显著"
                    post_show = "方差不齐，Bonferroni不适用，事后改用 Games-Howell（JASP：ANOVA→Games-Howell）"
                print(f"\n{gname} × {yshort}（{test_name}，{k}组）")
                print(f"    {desc}")
                print(f"    {levtxt}")
                print(f"    等方差 F({dfb},{dfw})={F:.3f}, p={fmt_p(p)}, η²={eta:.3f}（{et}效应）；{welchtxt}")
                print(f"    {post_show}")
                print(f"    → {sig}（{rec}）")
                rows.append({"分组变量": gname, "因变量": yshort, "检验": test_name,
                             "统计量": stat_F, "df": df_F, "p": fmt_p(p_F),
                             "效应量": f"η²={eta:.3f}({et})",
                             "方差齐性": levtxt, "稳健检验(Welch)": welchtxt,
                             "详情": desc + f"；{sig}；{rec}；{post_show}"})
    if output and rows:
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["分组变量", "因变量", "检验", "统计量",
                                              "df", "p", "效应量", "方差齐性",
                                              "稳健检验(Welch)", "详情"])
            w.writeheader()
            w.writerows(rows)
        print(f"\n人口学差异分析表已导出：{output}")
    return rows


def chi_square_analysis(headers, data, matrix, scales, output=None):
    """分类×分类变量的卡方独立性检验（人口学变量两两交叉，如性别×年级、性别×是否独生）。
    χ²=Σ(O−E)²/E，df=(r−1)(c−1)，p 用卡方上尾；效应量 Cramér's V=√(χ²/(N·min(r−1,c−1)))，
    .1/.3/.5 为小/中/大；2×2 默认 Yates 连续性校正；期望频数不足时引导 Fisher 精确检验。"""
    group_cols = _detect_group_cols(headers, data, matrix, scales)
    if len(group_cols) < 2:
        print("\n卡方检验：识别到的分类变量不足2个，跳过（需要性别、年级、是否独生等≥2个人口学分类列）。")
        return None
    print("\n" + "=" * 60)
    print("七、人口学分类变量交叉：卡方独立性检验（分类×分类）")
    print("=" * 60)

    def _key(v):
        try:
            return (0, float(v))
        except (TypeError, ValueError):
            return (1, str(v))

    rows = []
    for a in range(len(group_cols)):
        for b in range(a + 1, len(group_cols)):
            name1, lab1 = group_cols[a]
            name2, lab2 = group_cols[b]
            pairs = [(x, y) for x, y in zip(lab1, lab2)
                     if x is not None and y is not None]
            if len(pairs) < 4:
                continue
            lv1 = sorted(set(p[0] for p in pairs), key=_key)
            lv2 = sorted(set(p[1] for p in pairs), key=_key)
            r, c = len(lv1), len(lv2)
            if r < 2 or c < 2:
                continue
            n = len(pairs)
            i1 = {v: i for i, v in enumerate(lv1)}
            i2 = {v: j for j, v in enumerate(lv2)}
            table = [[0] * c for _ in range(r)]
            for x, y in pairs:
                table[i1[x]][i2[y]] += 1
            rt = [sum(table[i]) for i in range(r)]
            ct = [sum(table[i][j] for i in range(r)) for j in range(c)]
            exp = [[rt[i] * ct[j] / n for j in range(c)] for i in range(r)]
            chi = 0.0
            for i in range(r):
                for j in range(c):
                    o, e = table[i][j], exp[i][j]
                    if e <= 0:
                        continue
                    dev = (abs(o - e) - 0.5) if (r == 2 and c == 2) else (o - e)
                    chi += dev * dev / e
            df = (r - 1) * (c - 1)
            p = chi2_sf(chi, df)
            denom = n * min(r - 1, c - 1)
            v = math.sqrt(chi / denom) if denom > 0 else 0.0
            ncells = r * c
            low = sum(1 for i in range(r) for j in range(c) if exp[i][j] < 5)
            min_e = min(exp[i][j] for i in range(r) for j in range(c))
            low_pct = low / ncells
            if r == 2 and c == 2 and (min_e < 5):
                advice = "2×2且有期望频数<5，正式分析请用Fisher精确检验（JASP：Contingency Tables 勾 Fisher；SPSS：交叉表-统计量-Fisher）"
                method = "卡方(Yates校正)"
            elif min_e < 1 or low_pct > 0.2:
                advice = "期望频数不足（最小<1或>20%单元格<5），请合并稀有类别或用Fisher精确检验"
                method = "卡方"
            else:
                size = "小" if v < .3 else ("中" if v < .5 else "大")
                if p < .05:
                    advice = f"两变量显著关联（Cramér's V={v:.3f}，{size}效应）"
                else:
                    advice = "两变量无显著关联（相互独立）"
                method = "卡方(Yates校正)" if (r == 2 and c == 2) else "卡方(Pearson)"
            mark = sig_mark(p)
            print(f"  {name1} × {name2}（{r}×{c}, N={n}）："
                  f"χ²({df})={chi:.3f}, p={fmt_p(p)}, Cramér's V={v:.3f}{mark}  [{method}]")
            if min_e < 5:
                print(f"      ⚠ 最小期望频数={min_e:.2f}，{low}/{ncells}个单元格<5；{advice}")
            rows.append({"变量1": name1, "变量2": name2, "χ²": round(chi, 3),
                         "df": df, "p": fmt_p(p), "显著性": mark,
                         "Cramér's V": round(v, 3), "N": n,
                         "最小期望": round(min_e, 2),
                         "期望<5占比": f"{low_pct*100:.0f}%", "检验方式": method, "建议": advice})
    if not rows:
        print("  没有可交叉的分类变量对。")
        return None
    print("\n解读：Cramér's V .1/.3/.5 为小/中/大效应；卡方只回答'是否关联'，效应量回答'关联多强'。")
    if output:
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["变量1", "变量2", "χ²", "df", "p", "显著性",
                                              "Cramér's V", "N", "最小期望", "期望<5占比",
                                              "检验方式", "建议"])
            w.writeheader()
            w.writerows(rows)
        print(f"卡方检验表已导出：{output}")
    return rows
