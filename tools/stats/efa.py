# -*- coding: utf-8 -*-
"""结构效度与探索性因子分析

KMO、Bartlett 球形检验、Varimax 旋转载荷、共同度、交叉载荷标记、
Horn 平行分析定因子数、碎石图编排、Harman 共同方法偏差检验。

本模块由 tools/auto_stats.py 拆分而来（v1.53.1），函数体逐行未改动。
"""

import csv
import math
import os
import random

from .dataio import _safe_filename, recoded_item_series
from .linalg import _eigen_sym, _first_pc, determinant, invert_matrix
from .mathx import chi2_pvalue
from .plots import _plot_scree

# ============ 结构效度与探索性因子分析 ============

def kmo_value(corr):
    """KMO抽样适合度：基于相关系数平方和与偏相关系数平方和。"""
    p = len(corr)
    try:
        inv = invert_matrix(corr)
    except Exception:
        inv = None
    if inv is None:
        return None  # 相关矩阵奇异（题目高度共线/全同或样本不足），无法算偏相关
    sum_r2 = sum_p2 = 0.0
    for i in range(p):
        for j in range(i + 1, p):
            denom = math.sqrt(inv[i][i] * inv[j][j])
            q = (-inv[i][j] / denom) if denom > 0 else 0.0
            r = corr[i][j]
            sum_r2 += r * r
            sum_p2 += q * q
    denom = sum_r2 + sum_p2
    return sum_r2 / denom if denom > 0 else None


def _varimax(loadings, normalize=True, max_iter=100, tol=1e-7):
    """Kaiser归一化的最大方差正交旋转（varimax，Kaiser 1958逐对旋转）。
    输入未旋转载荷[题×因子]，返回旋转后载荷（已统一符号、按解释方差降序）。"""
    p, k = len(loadings), len(loadings[0])
    if k <= 1:
        return [row[:] for row in loadings]
    h = [math.sqrt(sum(loadings[i][j] ** 2 for j in range(k))) for i in range(p)]
    X = [[loadings[i][j] / h[i] if normalize and h[i] > 1e-12 else loadings[i][j]
          for j in range(k)] for i in range(p)]

    def v_criterion(M):
        v = 0.0
        for j in range(k):
            v += sum(M[i][j] ** 4 for i in range(p)) / p \
                - (sum(M[i][j] ** 2 for i in range(p)) / p) ** 2
        return v

    prev_v = v_criterion(X)
    for _ in range(max_iter):
        max_theta = 0.0
        for a in range(k - 1):
            for b in range(a + 1, k):
                u = [X[i][a] ** 2 - X[i][b] ** 2 for i in range(p)]
                v = [2.0 * X[i][a] * X[i][b] for i in range(p)]
                As = sum(u)
                Bs = sum(v)
                Cs = sum(u[i] ** 2 - v[i] ** 2 for i in range(p))
                Ds = 2.0 * sum(u[i] * v[i] for i in range(p))
                num = Ds - 2.0 * As * Bs / p
                den = Cs - (As * As - Bs * Bs) / p
                theta = math.atan2(num, den) / 4.0
                max_theta = max(max_theta, abs(theta))
                if abs(theta) > 1e-12:
                    c, s = math.cos(theta), math.sin(theta)
                    for i in range(p):  # 旋转方向经Wolfram/暴力扫描验证为单调上升方向
                        xa, xb = X[i][a], X[i][b]
                        X[i][a] = c * xa + s * xb
                        X[i][b] = -s * xa + c * xb
        cur_v = v_criterion(X)
        if max_theta < tol or abs(cur_v - prev_v) < 1e-10:
            break
        prev_v = cur_v
    Lr = [[X[i][j] * (h[i] if normalize else 1.0) for j in range(k)] for i in range(p)]
    # 符号统一：每列载荷和为负则翻转
    for j in range(k):
        if sum(Lr[i][j] for i in range(p)) < 0:
            for i in range(p):
                Lr[i][j] = -Lr[i][j]
    # 按旋转后各因子载荷平方和降序排列因子
    ss = [sum(Lr[i][j] ** 2 for i in range(p)) for j in range(k)]
    order = sorted(range(k), key=lambda j: -ss[j])
    Lr = [[Lr[i][order[j]] for j in range(k)] for i in range(p)]
    return Lr


def _parallel_analysis(R, n, n_rep=500, base_seed=20260917):
    """Horn 平行分析：生成 n_rep 个与原数据同 N、同题数、题间独立的随机数据，
    求每个位置特征值的均值与95%分位；真实特征值超过随机95%分位的连续成分数即建议因子数。
    返回 real/mean/p95 特征值与按均值、按95%分位的建议因子数（95%更保守，Glorfeld 1995）。"""
    k = len(R)
    real, _ = _eigen_sym(R)
    sims = []
    for i in range(n_rep):
        rng = random.Random(base_seed + i + 1)
        Z = []
        for _a in range(k):
            col = [rng.gauss(0.0, 1.0) for _ in range(n)]
            mm = sum(col) / n
            sd = math.sqrt(sum((x - mm) ** 2 for x in col) / (n - 1))
            Z.append([(x - mm) / sd if sd > 0 else 0.0 for x in col])
        M = [[0.0] * k for _ in range(k)]
        for a in range(k):
            za = Z[a]
            for b in range(a, k):
                rr = sum(za[j] * Z[b][j] for j in range(n)) / (n - 1)
                M[a][b] = rr
                M[b][a] = rr
        ev, _ = _eigen_sym(M)
        sims.append(ev)
    mean_e, p95_e = [], []
    for j in range(k):
        col = sorted(s[j] for s in sims)
        mean_e.append(sum(col) / n_rep)
        p95_e.append(col[min(n_rep - 1, int(0.95 * n_rep))])

    def _count(thr):
        c = 0
        for j in range(k):
            if real[j] > thr[j]:
                c = j + 1
            else:
                break
        return c

    return {"real": real, "mean": mean_e, "p95": p95_e,
            "nfac_mean": _count(mean_e), "nfac_p95": _count(p95_e)}


def _efa_one(name, items, conf, Z, R, n, pa_rep=500):
    """对单个量表做完整探索性因子分析（PCA提取+varimax旋转），打印并返回结果行。"""
    k = len(items)
    kmo = kmo_value(R)
    if kmo is None:
        print(f"\n{'─' * 58}")
        print(f"【完整EFA】{name}（{k}题，N={n}）：相关矩阵奇异，无法做因子分析。")
        print("  常见原因：有题目高度雷同/所有作答全同、有效样本过少或题目数超过样本数。")
        print("  请先做数据清洗、检查题目，再重跑。")
        return None
    det = determinant(R)
    dfb = k * (k - 1) / 2
    if det > 1e-300:
        chi2 = -(n - 1 - (2 * k + 5) / 6.0) * math.log(det)
        pval = chi2_pvalue(chi2, dfb)
    else:
        chi2, pval = float("inf"), 0.0

    eigvals, eigvecs = _eigen_sym(R)
    nfac = sum(1 for e in eigvals if e >= 1.0)
    nfac = max(1, min(nfac, k))
    # 未旋转载荷（主成分）：L0[:,j]=v_j*sqrt(λ_j)
    L0 = [[eigvecs[i][j] * math.sqrt(max(eigvals[j], 0)) for j in range(nfac)]
          for i in range(k)]
    # 共同度（提取nfac个因子，正交旋转不变）
    comm = [sum(L0[i][j] ** 2 for j in range(nfac)) for i in range(k)]
    Lr = _varimax(L0, normalize=True) if nfac > 1 else [[L0[i][0]] for i in range(k)]
    ss = [sum(Lr[i][j] ** 2 for i in range(k)) for j in range(nfac)]

    kmo_txt = f"{kmo:.3f}" if kmo is not None else "无法计算"
    if kmo is not None:
        rate = "极佳" if kmo >= .9 else "适合" if kmo >= .8 else "可接受" if kmo >= .7 \
            else "勉强(需谨慎)" if kmo >= .6 else "不适合因子分析"
    else:
        rate = ""
    bart = "p<.001" if pval < .001 else f"p={pval:.3f}"
    print(f"\n{'─' * 58}")
    print(f"【完整EFA】{name}（{k}题，N={n}）  提取：主成分分析  旋转：最大方差法Varimax")
    print(f"  KMO = {kmo_txt}  [{rate}]；Bartlett球形检验：χ²={chi2:.1f}"
          f"（df={int(dfb)}），{bart}（需p<.05）")
    ratio = n / k
    if ratio < 5:
        print(f"  ⚠ 样本量/题数={ratio:.1f}，偏少（建议≥5，理想≥10，N≥200），结果可能不稳定")
    # 特征值/碎石
    eig_str = "，".join(f"λ{i+1}={eigvals[i]:.2f}" for i in range(min(k, 8)))
    print(f"  特征值（Kaiser准则保留≥1，共{nfac}个）：{eig_str}" + ("…" if k > 8 else ""))
    pa = None
    if pa_rep and pa_rep > 0:
        print(f"  平行分析(Horn)模拟中（{pa_rep}次随机数据，约数秒）…")
        pa = _parallel_analysis(R, n, pa_rep)
        show = min(k, max(nfac + 2, 5))
        print("    成分   真实λ / 随机均值 / 随机95%分位")
        for j in range(show):
            keep = "保留" if pa["real"][j] > pa["p95"][j] else "—"
            print(f"     {j+1:>2}    {pa['real'][j]:5.2f} / {pa['mean'][j]:5.2f} / "
                  f"{pa['p95'][j]:5.2f}   {keep}")
        print(f"    →平行分析建议保留 {pa['nfac_p95']} 个因子（95%分位准则，更保守）；"
              f"均值准则 {pa['nfac_mean']} 个")
    # 总方差解释（旋转后）
    cum = 0.0
    var_line = []
    for j in range(nfac):
        pct = ss[j] / k * 100
        cum += pct
        var_line.append(f"因子{j+1}={pct:.1f}%")
    print(f"  旋转后方差解释率：{'，'.join(var_line)}；累计={cum:.1f}%"
          f"（社会科学建议≥50%~60%）")
    # 旋转载荷矩阵
    header = "  题项".ljust(10) + "".join(f"因子{j+1}".rjust(9) for j in range(nfac)) \
        + "共同度".rjust(8) + "  归属/提示"
    print(header)
    rows = []
    for i, it in enumerate(items):
        vals = [Lr[i][j] for j in range(nfac)]
        order_abs = sorted(range(nfac), key=lambda j: -abs(vals[j]))
        top, second = order_abs[0], order_abs[1] if nfac > 1 else None
        tag = "(反向)" if conf["reverse"].get(it) else ""
        flags = []
        if abs(vals[top]) < .4:
            flags.append("载荷<.4，考虑删题")
        if second is not None and abs(vals[second]) >= .4 and \
                abs(vals[top]) - abs(vals[second]) < .2:
            flags.append(f"交叉载荷(因子{top+1}/因子{second+1})")
        note = f"→因子{top+1}" + ("；" + "；".join(flags) if flags else "")
        cells = "".join(f"{vals[j]:9.3f}" for j in range(nfac))
        print(f"  {it[:8]}{tag}".ljust(10) + cells + f"{comm[i]:8.3f}  {note}")
        row = {"量表": name, "题项": it + tag}
        for j in range(nfac):
            row[f"因子{j+1}载荷"] = round(vals[j], 3)
        row["共同度"] = round(comm[i], 3)
        row["归属因子"] = top + 1
        row["提示"] = "；".join(flags)
        rows.append(row)
    if cum < 50:
        print("  ⚠ 累计方差解释率低于50%，结构解释力偏弱，需检查题目或因子数")
    if pa is not None:
        print(f"  因子数三依据：Kaiser特征值≥1→{nfac}个；碎石拐点→见碎石图；"
              f"平行分析→{pa['nfac_p95']}个。三者不一致时结合理论、优先平行分析，"
              f"并在JASP固定因子数复核。")
    print("  注：脚本用于快速预览/教学；碎石图"
          + ("（含平行分析线）" if pa is not None else "") + "已随结果导出PNG。")
    print("      固定因子数、斜交promax旋转、CFA验证性因子分析请在JASP/SPSS复核。")
    return {"量表": name, "题数": k, "N": n, "KMO": round(kmo, 3) if kmo else "",
            "Bartlett_p": "<.001" if pval < .001 else round(pval, 3),
            "因子数": nfac, "累计方差%": round(cum, 2),
            "平行分析因子数": pa["nfac_p95"] if pa else "",
            "特征值": [round(e, 4) for e in eigvals],
            "PA": pa, "rows": rows}


def validity_analysis(matrix, scales, efa_names=None, efa_output=None, pa_rep=500):
    """结构效度。默认对每个量表（反向计分后题目）做单维检查：KMO、Bartlett、第一主成分载荷。
    efa_names: None=全部走单维；'__ALL__'=全部做完整EFA；集合/列表=指定量表做完整EFA
    （主成分提取+特征值≥1定因子数+varimax旋转+共同度+交叉载荷）。"""
    print("\n" + "=" * 60)
    print("三、结构效度检验（各量表内部，反向计分后题目）")
    print("=" * 60)
    if efa_names:
        print("（已开启完整探索性因子分析EFA：主成分提取 + Varimax正交旋转）")
    rows = []
    efa_summaries = []
    efa_item_rows = []
    scree_pngs = []
    scree_fail = False
    for name, conf in scales.items():
        items = [it for it in conf["items"] if it in matrix]
        if len(items) < 3:
            print(f"\n{name}：题目不足3题，跳过因子分析。")
            continue
        series = recoded_item_series(matrix, conf)
        k = len(series)
        rows = [i for i in range(len(series[0])) if all(c[i] is not None for c in series)]
        n = len(rows)
        Z = []
        for col in series:
            vals = [col[i] for i in rows]
            mm = sum(vals) / n
            sd = math.sqrt(sum((v - mm) ** 2 for v in vals) / (n - 1)) if n > 1 else 0
            Z.append([(v - mm) / sd if sd > 0 else 0.0 for v in vals])
        R = [[0.0] * k for _ in range(k)]
        for a in range(k):
            for b in range(a, k):
                r = sum(Z[a][i] * Z[b][i] for i in range(n)) / (n - 1) if n > 1 else 0
                R[a][b] = r
                R[b][a] = r

        do_efa = bool(efa_names) and (efa_names == "__ALL__" or name in efa_names)
        if do_efa:
            res = _efa_one(name, items, conf, Z, R, n, pa_rep=pa_rep)
            if res is not None:
                efa_summaries.append({kk: vv for kk, vv in res.items()
                                      if kk not in ("rows", "PA")})
                efa_item_rows.extend(res["rows"])
                if efa_output:
                    if efa_output.endswith("_因子分析.csv"):
                        stem = efa_output[:-len("_因子分析.csv")]
                    else:
                        stem = os.path.splitext(efa_output)[0]
                    png = stem + "_" + _safe_filename(name) + "_碎石图.png"
                    pa = res.get("PA")
                    hl = pa["nfac_p95"] if pa else res["因子数"]
                    ok = _plot_scree(name, res["特征值"], hl, png,
                                     pa_mean=pa["mean"] if pa else None,
                                     pa_p95=pa["p95"] if pa else None)
                    if ok:
                        scree_pngs.append(png)
                    else:
                        scree_fail = True
            continue

        kmo = kmo_value(R)
        det = determinant(R)
        df = k * (k - 1) / 2
        if det > 1e-300:
            chi2 = -(n - 1 - (2 * k + 5) / 6.0) * math.log(det)
            pval = chi2_pvalue(chi2, df)
        else:
            chi2, pval = float("inf"), 0.0
        eigval, eigvec = _first_pc(R)
        if sum(eigvec) < 0:
            eigvec = [-v for v in eigvec]
        loadings = [eigvec[i] * math.sqrt(max(eigval, 0)) for i in range(k)]
        var_pct = eigval / k * 100

        kmo_txt = f"{kmo:.3f}" if kmo is not None else "无法计算"
        if kmo is not None:
            rate = "极佳" if kmo >= .9 else "适合" if kmo >= .8 else "可接受" if kmo >= .7 \
                else "勉强" if kmo >= .6 else "不适合因子分析"
        else:
            rate = ""
        bart = "p<.001" if pval < .001 else f"p={pval:.3f}"
        print(f"\n{name}（{k}题，N={n}）")
        print(f"  KMO = {kmo_txt}  [{rate}]")
        print(f"  Bartlett球形检验：χ²={chi2:.1f}（df={int(df)}），{bart}（需p<.05）")
        print(f"  第一主成分特征值={eigval:.3f}，方差解释率={var_pct:.2f}%"
              f"（单维量表建议>50%~60%）")
        low = []
        for idx, it in enumerate(items):
            tag = "(反向)" if conf["reverse"].get(it) else ""
            flag = "  ←载荷<.5，检查" if loadings[idx] < .5 else ""
            if loadings[idx] < .5:
                low.append(it)
            print(f"    {it}{tag}：因子载荷={loadings[idx]:.3f}{flag}")
        rows.append({"量表": name, "KMO": round(kmo, 3) if kmo else "",
                     "Bartlett_chi2": round(chi2, 1) if chi2 != float("inf") else "很大",
                     "Bartlett_p": "<.001" if pval < .001 else round(pval, 3),
                     "第一因子解释率%": round(var_pct, 2),
                     "低载荷题": ",".join(low)})
    if efa_item_rows:
        if efa_output:
            nfac_max = max(len([k for k in r if k.startswith("因子") and k.endswith("载荷")])
                           for r in efa_item_rows)
            fields = ["量表", "题项"] + [f"因子{j+1}载荷" for j in range(nfac_max)] + \
                     ["共同度", "归属因子", "提示"]
            with open(efa_output, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                w.writeheader()
                w.writerows(efa_item_rows)
            print(f"\nEFA旋转载荷矩阵已导出：{efa_output}")
        for png in scree_pngs:
            print(f"碎石图已导出：{png}（300dpi，可直接插入论文；结合λ=1线与拐点定因子数）")
        if scree_fail and not scree_pngs:
            print("\n未安装 matplotlib，未生成碎石图（不影响上面的数值结果）。")
            print("  安装后重跑即可出图：pip install matplotlib；或在 JASP Factor 中查看碎石图。")
        print("EFA摘要：" + "；".join(
            f"{s['量表']}→{s['因子数']}因子/累计{s['累计方差%']}%/KMO={s['KMO']}"
            for s in efa_summaries))
        print("提示：因子归属应与理论维度一致；交叉载荷、低载荷题目需结合理论删改后重跑。")
    print("\n提示：引用成熟量表通常报告KMO、Bartlett显著、各题载荷>.5即可；")
    print("  自编/重大修订量表用 --efa 做完整探索性因子分析；CFA验证性因子分析请用JASP/lavaan。")
    return rows


def first_pc_variance_ratio(item_cols_data):
    """Harman单因子检验：对题目做未旋转主成分分析，返回第一主成分方差解释率。
    基于相关矩阵（题目先z标准化），用幂迭代求最大特征值λ1，
    第一因子解释率 = λ1 / 题目数（相关矩阵迹=题目数）。"""
    p = len(item_cols_data)
    if p < 2:
        return None
    # 列表删除缺失行
    rows = [i for i in range(len(item_cols_data[0]))
            if all(c[i] is not None for c in item_cols_data)]
    n = len(rows)
    if n < 3:
        return None
    # z标准化
    Z = []
    for col in item_cols_data:
        vals = [col[i] for i in rows]
        m = sum(vals) / n
        sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1)) if n > 1 else 0
        Z.append([(v - m) / sd if sd > 0 else 0.0 for v in vals])
    # 相关矩阵
    R = [[0.0] * p for _ in range(p)]
    for a in range(p):
        for b in range(a, p):
            r = sum(Z[a][i] * Z[b][i] for i in range(n)) / (n - 1) if n > 1 else 0
            R[a][b] = r
            R[b][a] = r
    # 幂迭代求最大特征值
    vec = [1.0 / math.sqrt(p)] * p
    lam = 0.0
    for _ in range(1000):
        nv = [sum(R[a][b] * vec[b] for b in range(p)) for a in range(p)]
        norm = math.sqrt(sum(x * x for x in nv))
        if norm < 1e-12:
            break
        nv = [x / norm for x in nv]
        new_lam = sum(nv[a] * sum(R[a][b] * nv[b] for b in range(p)) for a in range(p))
        vec = nv
        if abs(new_lam - lam) < 1e-10:
            lam = new_lam
            break
        lam = new_lam
    return lam / p


def harman_test(matrix, scales):
    """共同方法偏差Harman单因子检验：所有量表题目（反向计分后）一起做未旋转因子分析。"""
    print("\n" + "=" * 60)
    print("四、共同方法偏差检验（Harman单因子）")
    print("=" * 60)
    item_cols, item_names = [], []
    for name, conf in scales.items():
        rec = recoded_item_series(matrix, conf)
        avail = [it for it in conf["items"] if it in matrix]
        for idx, it in enumerate(avail):
            item_cols.append(rec[idx])
            item_names.append(it)
    if len(item_cols) < 2:
        print("题目不足，跳过。")
        return None
    ratio = first_pc_variance_ratio(item_cols)
    if ratio is None:
        print("有效样本不足，跳过。")
        return None
    pct = ratio * 100
    verdict = "不严重（<40%），可接受" if pct < 40 else "超过40%，需在讨论中说明并强调程序控制"
    print(f"纳入题目数：{len(item_cols)}（反向题已先反向计分）")
    print(f"第一公因子方差解释率：{pct:.2f}%")
    print(f"判断标准：<40% 即共同方法偏差不严重")
    print(f"结论：{verdict}")
    print("论文表述：Harman单因子检验显示，第一公因子解释率为XX%，低于40%临界值，")
    print("          表明本研究不存在严重的共同方法偏差。")
    return round(pct, 2)
