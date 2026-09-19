# -*- coding: utf-8 -*-
"""相关矩阵与偏相关

Pearson/Spearman 相关矩阵（带显著性标记）；偏相关（控制一组变量后的净相关，
相关矩阵求逆法 r_ij·Z = −Pij/√(Pii·Pjj)，df = n−2−k）。
由 tools/stats/regress.py 拆分而来（v1.82 大文件拆分），函数体逐行未改动。
"""

import csv
import math


from .linalg import invert_matrix
from .mathx import fmt_p, pearson_r, sig_mark, spearman_r, t_p_two_sided

# ============ 相关矩阵与偏相关 ============

def correlation_matrix(matrix, num_cols, max_cols=15, method="pearson"):
    corr_fn = spearman_r if method == "spearman" else pearson_r
    label = "Spearman 秩相关（偏态/有序时的稳健相关）" if method == "spearman" else "Pearson"
    print("\n" + "=" * 60)
    print(f"相关分析（{label}）")
    print("=" * 60)
    cols = num_cols[:max_cols]
    if len(num_cols) > max_cols:
        print(f"（变量较多，只显示前{max_cols}个，建议用量表总分做相关）")

    results = []
    # 打印矩阵
    short = {c: c[:8] for c in cols}
    header_row = "          " + "".join(f"{short[c]:>10}" for c in cols)
    print(header_row)
    for i, c1 in enumerate(cols):
        row_str = f"{short[c1]:<10}"
        for j, c2 in enumerate(cols):
            if j > i:
                row_str += "       -  "
            else:
                r, n = corr_fn(matrix[c1], matrix[c2])
                if r is None:
                    row_str += "     n/a  "
                elif i == j:
                    row_str += "    1.000  "
                else:
                    t = r * math.sqrt((n - 2) / max(1 - r * r, 1e-12))
                    p = t_p_two_sided(t, n - 2)
                    mark = sig_mark(p)
                    row_str += f"{r:>7.3f}{mark:<3}"
                    results.append({"变量1": c1, "变量2": c2, "r": round(r, 3),
                                    "p": fmt_p(p), "显著性": mark, "N": n})
        print(row_str)
    print("\n注：*p<.05  **p<.01  ***p<.001")
    return results


def _resolve_colname(name, pool, scales):
    """把用户输入解析成 pool 中真实列名：量表名→量表总分，其次原样。"""
    if name in pool:
        return name
    cand = name + "总分"
    if cand in pool:
        return cand
    if scales and name in scales and cand in pool:
        return cand
    return None


def partial_correlation_analysis(score_matrix, target_cols, control_names,
                                 scales=None, extra_matrix=None, output=None):
    """偏相关：在控制一组变量后，目标变量两两之间的净相关（相关矩阵求逆法）。
    控制变量可以是量表总分，也可以是 extra_matrix 中的数值型人口学列（性别/年级，需已编码为数字）。
    r_ij·Z = −Pij/√(Pii·Pjj)，P 为 [目标i,目标j,控制…] 相关矩阵的逆；
    显著性 t=r·√((n−2−k)/(1−r²))，df=n−2−k。"""
    pool = dict(score_matrix)
    if extra_matrix:
        for k, v in extra_matrix.items():
            pool.setdefault(k, v)
    targets = [c for c in target_cols if c in pool]
    controls = []
    skipped = []
    for c in control_names:
        rc = _resolve_colname(c.strip(), pool, scales)
        if rc and rc not in controls and rc not in targets:
            controls.append(rc)
        elif not rc:
            skipped.append(c)
    if len(targets) < 2:
        print("\n偏相关：可分析的目标变量不足2个，跳过。")
        return None
    if control_names and not controls:
        print("\n偏相关：控制变量均无效（找不到或与目标重名），已跳过；"
              "人口学变量需已预处理为数字编码。")
        return None
    print("\n" + "=" * 60)
    print(f"偏相关分析（控制变量：{('、'.join(controls) if controls else '无')}）")
    if skipped:
        print(f"  ⚠ 以下控制变量找不到或与目标重名，已跳过：{skipped}（人口学变量需已预处理为数字编码）")
    print("=" * 60)
    k = len(controls)
    rows = []
    short = {c: c.replace("总分", "")[:8] for c in targets}
    print("          " + "".join(f"{short[c]:>10}" for c in targets))
    for i, c1 in enumerate(targets):
        row_str = f"{short[c1]:<10}"
        for j, c2 in enumerate(targets):
            if j > i:
                row_str += "       -  "
                continue
            if i == j:
                row_str += "    1.000  "
                continue
            vars_ = [c1, c2] + controls
            nrows = len(pool[c1])
            cases = []
            for r in range(nrows):
                vals = []
                ok = True
                for v in vars_:
                    x = pool[v][r] if r < len(pool[v]) else None
                    try:
                        x = float(x)
                    except (TypeError, ValueError):
                        ok = False
                        break
                    if x is None:
                        ok = False
                        break
                    vals.append(x)
                if ok:
                    cases.append(vals)
            n = len(cases)
            df = n - 2 - k
            if n < k + 4 or df <= 0:
                row_str += "     n/a  "
                continue
            m = len(vars_)
            R = [[0.0] * m for _ in range(m)]
            for a in range(m):
                for b in range(m):
                    if a == b:
                        R[a][b] = 1.0
                    else:
                        ca = [row[a] for row in cases]
                        cb = [row[b] for row in cases]
                        rr, _ = pearson_r(ca, cb)
                        R[a][b] = rr if rr is not None else 0.0
            P = invert_matrix(R)
            if P is None:
                row_str += "     n/a  "
                continue
            pr = -P[0][1] / math.sqrt(max(P[0][0] * P[1][1], 1e-12))
            pr = max(min(pr, 1.0), -1.0)
            t = pr * math.sqrt(df / max(1 - pr * pr, 1e-12))
            p = t_p_two_sided(t, df)
            mark = sig_mark(p)
            row_str += f"{pr:>7.3f}{mark:<3}"
            rows.append({"变量1": c1, "变量2": c2, "偏r": round(pr, 3),
                         "df": df, "p": fmt_p(p), "显著性": mark, "N": n,
                         "控制变量": "、".join(controls)})
        print(row_str)
    print(f"\n注：表中为控制 {('、'.join(controls) if controls else '无')} 后的偏相关系数；*p<.05 **p<.01 ***p<.001")
    if output and rows:
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["变量1", "变量2", "偏r", "df", "p",
                                              "显著性", "N", "控制变量"])
            w.writeheader()
            w.writerows(rows)
        print(f"偏相关表已导出：{output}")
    return rows
