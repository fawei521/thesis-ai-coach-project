# -*- coding: utf-8 -*-
"""Bootstrap 中介分析（模型4/6）

简单中介（模型4）与链式中介（模型6）的 Bootstrap 百分位 95%CI；
路径系数与间接效应分解、完全/部分中介判定。
由 tools/stats/regress.py 拆分而来（拆分批1 大文件拆分），函数体逐行未改动。
"""

import csv
import random


from .linalg import _ols_beta
from .mathx import _z

# ============ Bootstrap 中介分析（模型4/6） ============

def _mediation_effects(x, ms, y, idx):
    """对给定样本索引计算中介效应。ms长度1=简单中介(模型4)，长度2=链式中介(模型6)。"""
    gx = [x[i] for i in idx]
    gy = [y[i] for i in idx]
    gms = [[m[i] for i in idx] for m in ms]
    eff = {}
    eff["c(总效应)"] = _ols_beta(gy, [gx])[1]
    if len(gms) == 1:
        m1 = gms[0]
        eff["a(X→M)"] = _ols_beta(m1, [gx])[1]
        bY = _ols_beta(gy, [gx, m1])
        eff["c'(直接效应)"] = bY[1]
        eff["b(M→Y)"] = bY[2]
        eff["间接(a*b)"] = eff["a(X→M)"] * eff["b(M→Y)"]
    else:
        m1, m2 = gms[0], gms[1]
        eff["a1(X→M1)"] = _ols_beta(m1, [gx])[1]
        r2 = _ols_beta(m2, [gx, m1])
        eff["a2(X→M2)"] = r2[1]
        eff["d21(M1→M2)"] = r2[2]
        rY = _ols_beta(gy, [gx, m1, m2])
        eff["c'(直接效应)"] = rY[1]
        eff["b1(M1→Y)"] = rY[2]
        eff["b2(M2→Y)"] = rY[3]
        eff["间接:X→M1→Y(a1*b1)"] = eff["a1(X→M1)"] * eff["b1(M1→Y)"]
        eff["间接:X→M2→Y(a2*b2)"] = eff["a2(X→M2)"] * eff["b2(M2→Y)"]
        eff["间接:链式X→M1→M2→Y"] = eff["a1(X→M1)"] * eff["d21(M1→M2)"] * eff["b2(M2→Y)"]
        eff["间接合计"] = (eff["间接:X→M1→Y(a1*b1)"] + eff["间接:X→M2→Y(a2*b2)"]
                          + eff["间接:链式X→M1→M2→Y"])
    return eff


def mediation_analysis(matrix, x_col, m_cols, y_col, reps=5000, seed=20260917, output=None):
    """Bootstrap中介分析（模型4简单中介 / 模型6链式中介），百分位95%CI。"""
    cols = [x_col] + m_cols + [y_col]
    missing = [c for c in cols if not isinstance(c, str) or c not in matrix]
    if missing:
        print("✗ 中介分析失败：存在无法识别的量表名/列名，请对照 scales.txt 与数据表头检查 --x/--y/--mediators。")
        return None
    rows = [i for i in range(len(matrix[x_col]))
            if all(matrix[c][i] is not None for c in cols)]
    n = len(rows)
    if n < 30:
        print(f"⚠ 有效样本仅{n}（<30），Bootstrap结果不稳定，建议加大样本。")
    x = [matrix[x_col][i] for i in rows]
    y = [matrix[y_col][i] for i in rows]
    ms = [[matrix[m][i] for i in rows] for m in m_cols]

    model = "模型6（链式中介）" if len(m_cols) == 2 else "模型4（简单中介）"
    print("\n" + "=" * 60)
    print(f"七、Bootstrap中介分析（PROCESS {model}）")
    print("=" * 60)
    print(f"X={x_col}  中介={'→'.join(m_cols)}  Y={y_col}")
    print(f"N={n}，Bootstrap={reps}次，95%置信区间（百分位法），随机种子={seed}")

    point = _mediation_effects(x, ms, y, list(range(n)))

    # 标准化点估计（路径展示用β）
    zx, zy, zms = _z(x), _z(y), [_z(m) for m in ms]
    zpoint = _mediation_effects(zx, zms, zy, list(range(n)))

    rng = random.Random(seed)
    boots = {k: [] for k in point}
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        e = _mediation_effects(x, ms, y, idx)
        for k in boots:
            boots[k].append(e[k])

    def ci(k):
        s = sorted(boots[k])
        lo = s[int(0.025 * reps)]
        hi = s[int(0.975 * reps) - 1]
        return lo, hi

    def sig(lo, hi):
        return "显著（CI不含0）" if (lo > 0 or hi < 0) else "不显著（CI含0）"

    print("\n路径系数（点估计；括号内为标准化β）：")
    path_keys = [k for k in point if not k.startswith("间接")]
    for k in path_keys:
        print(f"  {k:<16} B={point[k]:.3f}   β={zpoint[k]:.3f}")

    print("\n中介效应分解（未标准化，Bootstrap 95%CI）：")
    rows_out = []
    ind_keys = [k for k in point if k.startswith("间接")]
    for k in ind_keys + ["c'(直接效应)", "c(总效应)"]:
        lo, hi = ci(k)
        se = (sum((v - point[k]) ** 2 for v in boots[k]) / (reps - 1)) ** 0.5
        mark = "★" if k.startswith("间接") and (lo > 0 or hi < 0) else " "
        print(f"  {mark}{k:<22} 效应={point[k]:.3f}  BootSE={se:.3f}  "
              f"95%CI=[{lo:.3f}, {hi:.3f}]  {sig(lo, hi) if k.startswith('间接') else ''}")
        rows_out.append({"效应": k, "效应值": round(point[k], 3), "BootSE": round(se, 3),
                         "CI下限": round(lo, 3), "CI上限": round(hi, 3),
                         "显著性": sig(lo, hi) if k.startswith("间接") else ""})

    # 结论
    if len(m_cols) == 1:
        lo, hi = ci("间接(a*b)")
        ind_sig = lo > 0 or hi < 0
        direct_lo, direct_hi = ci("c'(直接效应)")
        direct_sig = direct_lo > 0 or direct_hi < 0
        if ind_sig and not direct_sig:
            kind = "完全中介（间接效应显著、直接效应不显著）"
        elif ind_sig and direct_sig:
            kind = "部分中介（间接、直接效应均显著）"
        else:
            kind = "中介效应不显著"
        print(f"\n结论：{kind}。")
    else:
        chain_lo, chain_hi = ci("间接:链式X→M1→M2→Y")
        print(f"\n链式中介路径X→M1→M2→Y：{sig(chain_lo, chain_hi)}。")
    print("提示：脚本用于快速预览，正式结果建议用JASP/SPSS PROCESS复核（含偏差校正CI）。")

    if output:
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["效应", "效应值", "BootSE", "CI下限", "CI上限", "显著性"])
            w.writeheader()
            w.writerows(rows_out)
        print(f"中介效应表已导出：{output}")
    return rows_out
