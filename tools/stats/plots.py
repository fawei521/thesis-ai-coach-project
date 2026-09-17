# -*- coding: utf-8 -*-
"""绘图（matplotlib 为可选依赖，缺失时返回 False 不影响数值结果）

碎石图（可叠加平行分析随机均值/95%分位线）、
相关矩阵下三角热图（系数＋显著性星号，对角 Cronbach α）、
调节效应简单斜率图。

本模块由 tools/auto_stats.py 拆分而来（v1.53.1），函数体逐行未改动。
"""

import math

from .mathx import pearson_r, sig_mark, spearman_r, t_p_two_sided

# ============ 绘图（matplotlib 为可选依赖，缺失时返回 False 不影响数值结果） ============

def _plot_scree(name, eigvals, nfac, out_png, pa_mean=None, pa_p95=None):
    """画碎石图（Cattell scree plot）：折线+数据点+Kaiser λ=1 参考线，高亮保留因子。
    若提供 pa_mean/pa_p95（平行分析随机特征值），叠加随机均值与95%分位线。
    matplotlib 为可选依赖，未安装时返回 False（不影响数值结果）。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False
    k = len(eigvals)
    x = list(range(1, k + 1))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, eigvals, "-", color="#9bb8d3", linewidth=1.6, zorder=2)
    ax.plot(x, eigvals, "o", color="#1f4e79", markersize=6, zorder=3, label="真实特征值")
    ax.axhline(1.0, color="#C62828", linestyle="--", linewidth=1.3, zorder=1,
               label="Kaiser 基准 λ=1")
    if pa_mean is not None:
        ax.plot(x, pa_mean, "--", color="#ef6c00", linewidth=1.3, zorder=2,
                label="平行分析 随机均值")
    if pa_p95 is not None:
        ax.plot(x, pa_p95, ":", color="#6a1b9a", linewidth=1.5, zorder=2,
                label="平行分析 随机95%分位")
    ax.plot(x[:nfac], eigvals[:nfac], "o", color="#2e7d32", markersize=12,
            markerfacecolor="none", markeredgewidth=1.8, zorder=4,
            label=f"保留 {nfac} 个因子")
    # 题数少时标注每个特征值，题数多时只标前10个避免重叠
    for xi, yi in zip(x, eigvals):
        if k <= 15 or xi <= 10:
            ax.annotate(f"{yi:.2f}", (xi, yi), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=8, color="#333")
    ax.set_xticks(x)
    ax.set_xlabel("成分序号", fontsize=11)
    ax.set_ylabel("特征值", fontsize=11)
    title = f"{name} 碎石图（Scree Plot）"
    if pa_p95 is not None:
        title += "＋平行分析"
    ax.set_title(title, fontsize=13)
    ax.set_ylim(0, max(eigvals) * 1.15)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True


def _plot_simple_slopes(x_col, w_col, y_col, sdx, sdw, b0, b1, b2, b3,
                        slope_marks, mod_sig, b3_p_txt, out_png):
    """调节效应（模型1）简单斜率图：W 低(-1SD)/均值/高(+1SD) 三条回归线，
    横轴为中心化后的 X，纵轴为预测的 Y。斜率 θ=b1+b3·w。
    matplotlib 为可选依赖，未安装时返回 False（不影响数值结果）。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False
    xgrid = [(-1.5 + 3.0 * i / 100.0) * sdx for i in range(101)]
    conds = [(-sdw, "低（-1SD）", "#1565c0", "low"),
             (0.0, "均值", "#2e7d32", "mid"),
             (sdw, "高（+1SD）", "#c62828", "high")]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for w, lab, color, key in conds:
        theta = b1 + b3 * w
        line = [b0 + b2 * w + theta * xc for xc in xgrid]
        mk = slope_marks.get(key, "")
        ax.plot(xgrid, line, "-", color=color, linewidth=2.0,
                label=f"{w_col}{lab}：斜率={theta:.3f}{('（'+mk+'）') if mk else ''}")
    ax.axvline(0, color="#999999", linestyle=":", linewidth=1.0)
    ax.axhline(b0, color="#cccccc", linestyle=":", linewidth=0.9)
    ax.set_xlabel(f"{x_col}（中心化值，0 = 均值；±{sdx:.1f} 为 ±1SD）", fontsize=11)
    ax.set_ylabel(f"{y_col}（预测值）", fontsize=11)
    verdict = "调节效应成立" if mod_sig else "调节效应未达稳健显著"
    ax.set_title(f"{x_col} × {w_col} → {y_col} 简单斜率图（交互项 p={b3_p_txt}，{verdict}）",
                 fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True


def _plot_corr_heatmap(matrix, cols, out_png, method="pearson", alpha_map=None,
                       max_cols=12):
    """画研究变量（量表总分）相关矩阵下三角热图：下三角为相关系数＋显著性星号，
    对角线为 Cronbach α（无则 1），上三角留白。matplotlib/numpy 为可选依赖，
    缺失时返回 False，不影响数值结果。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception:
        return False
    corr_fn = spearman_r if method == "spearman" else pearson_r
    use_cols = cols[:max_cols]
    k = len(use_cols)
    if k < 2:
        return False
    R = np.full((k, k), np.nan)
    P = np.full((k, k), np.nan)
    diag_alpha = {}
    for i in range(k):
        for j in range(k):
            if j < i:
                r, nn = corr_fn(matrix[use_cols[i]], matrix[use_cols[j]])
                if r is not None and nn and nn > 2:
                    R[i, j] = r
                    t = r * math.sqrt((nn - 2) / max(1 - r * r, 1e-12))
                    P[i, j] = t_p_two_sided(t, nn - 2)
    # 短名：去掉“总分/均分”后缀
    def short(c):
        return c.replace("总分", "").replace("均分", "")
    labels = [short(c) for c in use_cols]
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False
    masked = np.ma.array(R, mask=np.isnan(R))
    cmap = plt.get_cmap("RdBu_r").copy()
    cmap.set_bad(color="#f2f2f2")
    fig, ax = plt.subplots(figsize=(max(6.2, 1.05 * k + 1.6), max(5.6, 0.92 * k + 1.4)))
    im = ax.imshow(masked, cmap=cmap, vmin=-1, vmax=1)
    ax.set_xticks(range(k)); ax.set_yticks(range(k))
    ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=10)
    ax.set_yticklabels(labels, fontsize=10)
    for i in range(k):
        for j in range(k):
            if j < i and not np.isnan(R[i, j]):
                p = P[i, j]
                mark = sig_mark(p) if not np.isnan(p) else ""
                color = "white" if abs(R[i, j]) >= 0.55 else "#222"
                ax.text(j, i, f"{R[i, j]:.2f}{mark}", ha="center", va="center",
                        fontsize=9.5, color=color)
            elif j == i:
                a = None
                if alpha_map:
                    a = alpha_map.get(use_cols[i])
                txt = f"α={a:.3f}" if isinstance(a, (int, float)) else "1"
                ax.text(j, i, txt, ha="center", va="center", fontsize=9,
                        color="#555", style="italic")
    ax.set_xticks(np.arange(-0.5, k, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, k, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", length=0)
    for spine in ax.spines.values():
        spine.set_color("#cccccc")
    kind = "Spearman" if method == "spearman" else "Pearson"
    ax.set_title(f"研究变量相关矩阵热图（{kind}）\n对角线为 Cronbach α；*p<.05  **p<.01  ***p<.001",
                 fontsize=12)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("相关系数", fontsize=10)
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True
