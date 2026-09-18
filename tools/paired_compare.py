#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配对设计差异检验工具（前后测 / 两条件）
======================================
干预研究、重复测量设计里最常见的问题：同一批人前测与后测（或实验条件 A/B）
有没有显著变化。本工具对每一对配对变量一次算齐：

  - 配对样本 t 检验（等价于差值的单样本 t，H0：差值均值=0）：
    t = mean(d) / (sd(d)/√n)，df = n−1，双侧 p；
  - 效应量 Cohen's d_z = mean(d)/sd(d)（差值口径，通常比独立组 d 大），
    附近似 95%CI（SE≈√(1/n + d_z²/2n)，Becker 近似，精确 CI 以 JASP/SPSS 为准）；
  - 差值正态性 Shapiro-Wilk（配对 t 的前提是【差值】近似正态，不是原始分数）；
  - Wilcoxon 符号秩检验（配对非参数）：n≤25 且无结给精确双侧 p，
    否则给正态近似 z（含结校正与连续性校正，SPSS 口径），并给效应量
    rank-biserial 相关 r_rb=（W+−W−）/（W++W−）（符号同差值方向，
    |r| .1/.3/.5 为小/中/大，与 R effectsize::rank_biserial 同口径）。

数据口径（两种模式）：
  1) 单文件宽表（同一批人的前/后测列都在一个 CSV）：
       python tools/paired_compare.py 数据.csv --pairs 前测孤独:后测孤独,前测反刍:后测反刍
     可选 --id 编号（按编号配对，缺一方的人剔除并计数；不给则按行顺序配对）；
     可选 --group 组别 --level 实验组（只在某一组内做前后测）。
  2) 两个文件（前测.csv、后测.csv，必须 --id 按编号配对）：
       python tools/paired_compare.py 前测.csv 后测.csv --id 编号 --scales scales.txt
     给 --scales 时对每个量表按反向计分题项算均分再配对；
     不给 --scales 时用 --pairs 列名:列名（两文件同名列）。
  3) 单样本（一组分数与固定常数比较，如 Likert 中值 3、常模分；等价于对 x−C
     做单样本 t / Wilcoxon，复用同一套前提与效应量）：
       python tools/paired_compare.py 数据.csv --onesample 孤独感,反刍 --constant 3
     可配 --group/--level 只在某一组内检验。

解释红线：
  - 配对 t 的前提是【差值】近似正态；Shapiro 大样本过敏感，结合偏度峰度/Q-Q 图。
  - 配对必须是同一个体；无法配对的记录一律剔除并如实报告 n，不得按行硬凑。
  - Wilcoxon 检验的是差值分布是否关于 0 对称（位置移动），不直接检验均值差。
  - 3 个及以上时点用重复测量方差分析/线性混合模型，不要反复做配对 t；
    若必须两两比较，Bonferroni 校正 α（k 次比较用 α/k）。
  - “实验组变化比对照组变化更大”要比较两组差值（独立样本 t on 差值）或
    组别×时点交互作用，不能只报组内前后测显著。

导出：_配对检验.csv（UTF-8-BOM，可直接 Excel 打开）与 _配对检验报告.txt（可粘论文）。
"""
import argparse
import csv
import io
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats.dataio import read_data, to_float_matrix  # noqa: E402
from stats.mathx import (  # noqa: E402
    _rankdata, _tie_term_from_ranks, fmt_p, mean, normal_quantile, normal_sf,
    stdev, t_p_two_sided,
)
from assumption_check import build_dvs, shapiro_wilk  # noqa: E402

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与其他工具同款，避免 GBK 崩溃）---
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ================================================================ Wilcoxon 符号秩
def _exact_signed_rank_p(wplus, n):
    """精确双侧 p：n 个秩 1..n 各以 1/2 概率取正，统计 W+ 的分布（动态规划计数）。

    双侧 p = 2·min(P(W+≤w), P(W+≥w))，与 scipy.stats.wilcoxon(method='exact')
    的双侧口径一致；w 与 T−w 对称。
    """
    total = n * (n + 1) // 2
    # counts[s]：W+ = s 的符号组合数
    counts = [1] + [0] * total
    cap = 0
    for r in range(1, n + 1):
        for s in range(cap, -1, -1):
            counts[s + r] += counts[s]
        cap += r
    denom = 2 ** n
    w = int(round(min(wplus, total - wplus)))
    leq = sum(counts[: w + 1])          # P(W+ ≤ w)
    p = min(1.0, 2.0 * leq / denom)
    return p


def wilcoxon_signed_rank(diffs):
    """Wilcoxon 符号秩检验。

    返回 dict：n（剔除零差值后）、w_plus、w_minus、z（连续性校正，SPSS 口径）、
    z_raw（不校正，scipy 默认口径）、p（双侧）、method（exact/asymptotic）、
    n_ties、n_zero。
    """
    nz = [d for d in diffs if d != 0.0]
    n_zero = len(diffs) - len(nz)
    n = len(nz)
    if n == 0:
        return None
    absd = [abs(d) for d in nz]
    ranks = _rankdata(absd)
    w_plus = sum(r for r, d in zip(ranks, nz) if d > 0)
    w_minus = sum(r for r, d in zip(ranks, nz) if d < 0)
    # 结：|d| 相等（平均秩 >1 个同秩）
    tie_term = _tie_term_from_ranks(ranks)
    n_ties = 0
    rank_count = {}
    for r in ranks:
        rank_count[r] = rank_count.get(r, 0) + 1
    n_ties = sum(1 for c in rank_count.values() if c > 1)

    total = n * (n + 1) / 2.0
    mu = total / 2.0
    var = n * (n + 1) * (2 * n + 1) / 24.0 - tie_term / 48.0
    sigma = math.sqrt(var) if var > 0 else float("nan")
    # 连续性校正（SPSS 口径）：向均值方向收 0.5
    dev_cc = abs(w_plus - mu) - 0.5
    z_cc = dev_cc / sigma if sigma > 0 and dev_cc > 0 else 0.0
    z_raw = (w_plus - mu) / sigma if sigma > 0 else 0.0

    if n <= 25 and tie_term == 0:
        p = _exact_signed_rank_p(w_plus, n)
        method = "exact"
        z_cc = z_raw = float("nan")
    else:
        p = min(1.0, 2.0 * normal_sf(abs(z_cc)))
        method = "asymptotic"
    # rank-biserial r（Kerby 2014 简单差公式；与 R effectsize::rank_biserial、
    # JASP 的 r_rb 同口径）：符号随差值方向（d=后−前，正=后测更高），
    # 幅度 |r|=1−2·min(W+,W−)/T，.1/.3/.5 为小/中/大
    r_rb = (w_plus - w_minus) / total if total > 0 else float("nan")
    return {
        "n": n, "w_plus": w_plus, "w_minus": w_minus, "z": z_cc,
        "z_raw": z_raw, "p": p, "method": method, "n_ties": n_ties,
        "n_zero": n_zero, "r_rb": r_rb,
    }


# ================================================================ 单对配对检验
def paired_test(name, pre, post, alpha=0.05):
    """pre/post 为等长列表，元素为 float 或 None（None 表示该时点缺失，整对剔除）。"""
    pairs = [(a, b) for a, b in zip(pre, post) if a is not None and b is not None]
    n_input = min(len(pre), len(post))
    n = len(pairs)
    row = {"name": name, "n_input": n_input, "n": n, "mode": "paired"}
    if n < 3:
        row["error"] = f"可配对记录仅 {n} 对，至少需要 3 对"
        return row
    d = [b - a for a, b in pairs]
    m_pre = mean([a for a, _ in pairs])
    m_post = mean([b for _, b in pairs])
    md = mean(d)
    sd = stdev(d)
    row.update({"m_pre": m_pre, "m_post": m_post, "mean_diff": md, "sd_diff": sd})
    if sd == 0:
        row["error"] = "差值标准差为 0（前后测完全相同），无法检验"
        return row
    t = md / (sd / math.sqrt(n))
    df = n - 1
    p_t = t_p_two_sided(t, df)
    dz = md / sd
    se_dz = math.sqrt(1.0 / n + dz ** 2 / (2.0 * n))
    zc = normal_quantile(1 - alpha / 2)
    row.update({
        "t": t, "df": df, "p_t": p_t, "dz": dz,
        "dz_lo": dz - zc * se_dz, "dz_hi": dz + zc * se_dz,
    })
    if n >= 3:
        try:
            w, p_sw = shapiro_wilk(d)
            row.update({"sw_W": w, "sw_p": p_sw})
        except Exception:
            row.update({"sw_W": float("nan"), "sw_p": float("nan")})
    row["wilcox"] = wilcoxon_signed_rank(d)
    # 方法建议：差值正态看 Shapiro（大样本结合实际分布），不满足且 n 小时推 Wilcoxon
    if row.get("sw_p") is not None and not math.isnan(row["sw_p"]):
        row["normal_diff"] = row["sw_p"] >= alpha
    else:
        row["normal_diff"] = None
    return row


# ================================================================ 数据组织
def _filter_group(headers, data_rows, group_col, level):
    """按原始字符串值匹配返回该组行下标（分组列常是中文，不能走数值矩阵）。"""
    if group_col not in headers:
        print(f"✗ 分组列「{group_col}」不在数据中，可用列：{ '、'.join(headers[:20]) }")
        sys.exit(1)
    gi = headers.index(group_col)
    idx = [i for i, row in enumerate(data_rows)
           if gi < len(row) and row[gi].strip() == str(level).strip()]
    if not idx:
        print(f"✗ 分组列「{group_col}」中没有取值为「{level}」的记录。")
        sys.exit(1)
    return idx


def _pair_by_id(pre_ids, post_ids, pre_vals, post_vals):
    """按 id 内连接，返回 (pre_aligned, post_aligned, n_pre_only, n_post_only)。"""
    post_map = {}
    for i, pid in enumerate(post_ids):
        if pid is not None and pid not in post_map:
            post_map[pid] = i
    pre_a, post_a = [], []
    used_post = set()
    pre_only = 0
    for i, pid in enumerate(pre_ids):
        if pid is None or pid not in post_map:
            pre_only += 1
            continue
        j = post_map[pid]
        used_post.add(pid)
        pre_a.append(pre_vals[i])
        post_a.append(post_vals[j])
    post_only = sum(1 for pid in post_ids if pid is not None and pid not in used_post)
    return pre_a, post_a, pre_only, post_only


# ================================================================ 呈现
def fmt(v, nd=3):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{nd}f}"


def _dz_tag(dz):
    a = abs(dz)
    if a < 0.2:
        return "可忽略"
    if a < 0.5:
        return "小"
    if a < 0.8:
        return "中"
    return "大"


def _r_tag(r):
    a = abs(r)
    if a < 0.1:
        return "可忽略"
    if a < 0.3:
        return "小"
    if a < 0.5:
        return "中"
    return "大"


def print_rows(rows, alpha):
    one = bool(rows) and rows[0].get("mode") == "onesample"
    if one:
        c0 = rows[0].get("constant")
        print(f"单样本检验（差值 d = 观测值 − 检验常数 {c0:g}；H0：总体均值={c0:g}）")
    else:
        print("配对设计差异检验（差值 d = 后测 − 前测；H0：差值均值=0）")
    print("=" * 78)
    for r in rows:
        if r.get("mode") == "onesample":
            print(f"\n【{r['name']}】有效 n={r['n']}"
                  + (f"（输入 {r['n_input']} 行，剔除缺失 {r['n_input'] - r['n']}）"
                     if r.get("n_input") and r["n_input"] != r["n"] else ""))
        else:
            print(f"\n【{r['name']}】配对数 n={r['n']}"
                  + (f"（输入 {r['n_input']} 行，剔除无法配对/缺失 {r['n_input'] - r['n']}）"
                     if r.get("n_input") and r["n_input"] != r["n"] else ""))
        if "error" in r:
            print(f"  ✗ {r['error']}")
            continue
        if r.get("mode") == "onesample":
            print(f"  检验常数={fmt(r['m_pre'])}　样本 M={fmt(r['m_post'])}　"
                  f"差值 M={fmt(r['mean_diff'])}（SD={fmt(r['sd_diff'])}）")
        else:
            print(f"  前测 M={fmt(r['m_pre'])}　后测 M={fmt(r['m_post'])}　"
                  f"差值 M={fmt(r['mean_diff'])}（SD={fmt(r['sd_diff'])}）")
        t_label = "单样本 t" if r.get("mode") == "onesample" else "配对 t"
        print(f"  {t_label}({r['df']})={fmt(r['t'])}，p={fmt_p(r['p_t'])}；"
              f"d_z={fmt(r['dz'])}（{_dz_tag(r['dz'])}效应），"
              f"{int((1-alpha)*100)}%CI≈[{fmt(r['dz_lo'])}, {fmt(r['dz_hi'])}]")
        sw = ("差值 Shapiro-Wilk 不显著（p=" + fmt_p(r["sw_p"]) + "），差值可视为近似正态"
              ) if r.get("normal_diff") else (
              "差值 Shapiro-Wilk 显著（p=" + fmt_p(r["sw_p"]) + "），建议以 Wilcoxon 为准"
              if r.get("normal_diff") is False else "差值正态性无法检验")
        print(f"  前提：W={fmt(r.get('sw_W'))}，{sw}")
        w = r["wilcox"]
        if w:
            if w["method"] == "exact":
                print(f"  Wilcoxon 符号秩：W+={fmt(w['w_plus'],1)}，W−={fmt(w['w_minus'],1)}，"
                      f"精确双侧 p={fmt_p(w['p'])}（n={w['n']}，零差值 {w['n_zero']} 个已剔除），"
                      f"rank-biserial r={fmt(w['r_rb'])}（{_r_tag(w['r_rb'])}效应）")
            else:
                print(f"  Wilcoxon 符号秩：W+={fmt(w['w_plus'],1)}，W−={fmt(w['w_minus'],1)}，"
                      f"z={fmt(w['z'])}（连续性校正），双侧 p={fmt_p(w['p'])}"
                      f"（n={w['n']}，结 {w['n_ties']} 组、零差值 {w['n_zero']} 个），"
                      f"rank-biserial r={fmt(w['r_rb'])}（{_r_tag(w['r_rb'])}效应）")
                if w["n"] < 30 and w["n_ties"] > 0:
                    print(f"  ⚠ 小样本且有 {w['n_ties']} 组结（|差值|相等，Likert 前后测极常见）："
                          f"有结时精确分布不再适用、只能走正态近似，此口径 p 偏乐观"
                          f"（实测可与精确值差近一倍）。请以 JASP/SPSS 精确法或蒙特卡洛复核，"
                          f"并同时报告配对 t 结果，不要只凭这个 p 下结论。")
    print("\n" + "-" * 78)
    if one:
        print("提示：差值（观测值−常数）正态前提满足报单样本 t（d_z）；不满足且样本小报 Wilcoxon。"
              "Likert 与中值比较时常有大量零差值与结，n<30 以 SPSS/JASP 精确法复核。")
    else:
        print("提示：差值正态前提满足报配对 t（d_z）；不满足且样本小报 Wilcoxon。"
              "3+ 时点用重复测量 ANOVA/混合模型；组间变化幅度比较用差值的独立样本 t 或交互作用。")


def make_paragraph(rows, alpha):
    one = bool(rows) and rows[0].get("mode") == "onesample"
    lines = [("单样本检验结果" if one else "配对设计差异检验结果")
             + "（可粘贴进论文，数字请与 SPSS/JASP 复核）", ""]
    for r in rows:
        if "error" in r:
            lines.append(f"· {r['name']}：{r['error']}。")
            continue
        sig = "差异具有统计学意义" if r["p_t"] < alpha else "差异无统计学意义"
        direction = "上升" if r["mean_diff"] > 0 else "下降"
        if r.get("mode") == "onesample":
            lines.append(
                f"· {r['name']}：单样本 t 检验显示，样本均值（M={r['m_post']:.2f}）与检验常数 "
                f"{r['m_pre']:g} 相比{direction}，t({r['df']})={r['t']:.3f}，{fmt_p(r['p_t'])}，"
                f"{sig}；Cohen's d_z={r['dz']:.3f}（{_dz_tag(r['dz'])}效应），"
                f"d_z 的 {int((1-alpha)*100)}%CI≈[{r['dz_lo']:.3f}, {r['dz_hi']:.3f}]（近似）。"
            )
            continue
        lines.append(
            f"· {r['name']}：前后测配对样本 t 检验显示，后测（M={r['m_post']:.2f}）较前测"
            f"（M={r['m_pre']:.2f}）{direction}，t({r['df']})={r['t']:.3f}，{fmt_p(r['p_t'])}，"
            f"{sig}；Cohen's d_z={r['dz']:.3f}（{_dz_tag(r['dz'])}效应），"
            f"d_z 的 {int((1-alpha)*100)}%CI≈[{r['dz_lo']:.3f}, {r['dz_hi']:.3f}]（近似）。"
        )
        if r.get("normal_diff") is False:
            w = r["wilcox"]
            if w and w["method"] == "exact":
                lines.append(
                    f"  差值 Shapiro-Wilk 检验显著（W={r['sw_W']:.3f}，{fmt_p(r['sw_p'])}），"
                    f"差值不满足正态前提；Wilcoxon 符号秩检验 W+={w['w_plus']:.0f}，"
                    f"精确双侧 p={fmt_p(w['p'])}，rank-biserial r={w['r_rb']:.3f}，"
                    f"结论以非参数检验为准。")
            elif w:
                lines.append(
                    f"  差值 Shapiro-Wilk 检验显著（W={r['sw_W']:.3f}，{fmt_p(r['sw_p'])}），"
                    f"差值不满足正态前提；Wilcoxon 符号秩检验 z={w['z']:.3f}，"
                    f"双侧 p={fmt_p(w['p'])}，rank-biserial r={w['r_rb']:.3f}，"
                    f"结论以非参数检验为准。")
                if w["n"] < 30 and w["n_ties"] > 0:
                    lines.append(
                        f"  （口径说明：因存在 {w['n_ties']} 组结且 n={w['n']}，"
                        f"Wilcoxon 采用含结校正与连续性校正的正态近似而非精确分布，"
                        f"该口径 p 偏乐观，正式结果以 SPSS/JASP 精确法复核为准。）")
    lines.append("")
    if one:
        lines.append("注：单样本 t 的前提是观测值与常数之差近似正态（非原始分数）；"
                     "Likert 数据与常数（如中值）比较时差值常含结，n<30 时以 Wilcoxon 精确法复核为准；"
                     "缺失记录已剔除。")
    else:
        lines.append("注：配对 t 的前提是差值近似正态（非原始分数）；d_z 以差值标准差为分母，"
                     "口径不同于独立组 d；无法配对的记录已整对剔除。多时点或组间变化幅度比较"
                     "请用重复测量 ANOVA/混合模型或组别×时点交互作用。")
    return "\n".join(lines)


def write_csv(path, rows):
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["配对变量", "配对n", "前测M", "后测M", "差值M", "差值SD",
                    "t", "df", "p(t双侧)", "d_z", "d_z_CI下限", "d_z_CI上限",
                    "差值Shapiro_W", "差值Shapiro_p",
                    "Wilcoxon_W+", "Wilcoxon_W-", "Wilcoxon_z(校正)", "Wilcoxon_p",
                    "Wilcoxon_r_rb", "Wilcoxon方法", "备注"])
        for r in rows:
            wc = r.get("wilcox") or {}
            note = r.get("error", "")
            if not note:
                note = "差值正态" if r.get("normal_diff") else (
                    "差值非正态，以Wilcoxon为准" if r.get("normal_diff") is False else "")
                if r.get("mode") == "onesample":
                    note = f"单样本(vs {r.get('constant'):g})；{note}"
            w.writerow([
                r["name"], r.get("n", ""),
                fmt(r.get("m_pre"), 4), fmt(r.get("m_post"), 4),
                fmt(r.get("mean_diff"), 4), fmt(r.get("sd_diff"), 4),
                fmt(r.get("t"), 4), r.get("df", ""),
                fmt(r.get("p_t"), 6), fmt(r.get("dz"), 4),
                fmt(r.get("dz_lo"), 4), fmt(r.get("dz_hi"), 4),
                fmt(r.get("sw_W"), 4), fmt(r.get("sw_p"), 6),
                fmt(wc.get("w_plus"), 2), fmt(wc.get("w_minus"), 2),
                fmt(wc.get("z"), 4), fmt(wc.get("p"), 6), fmt(wc.get("r_rb"), 4),
                {"exact": "精确", "asymptotic": "正态近似"}.get(wc.get("method"), ""),
                note,
            ])


# ================================================================ 主流程
def main():
    ap = argparse.ArgumentParser(
        description="配对设计差异检验（前后测/两条件：配对 t＋d_z＋差值正态性＋Wilcoxon 符号秩）")
    ap.add_argument("input", help="数据 CSV（单文件宽表）；两文件模式下为【前测】CSV")
    ap.add_argument("post_file", nargs="?", help="可选：【后测】CSV（两文件模式，必须配 --id）")
    ap.add_argument("--pairs", help="配对列，格式 前测列:后测列，多对用逗号分隔（单文件模式）；"
                                    "两文件模式下可给两文件同名列，逗号分隔")
    ap.add_argument("--onesample", help="单样本模式：要检验的列，逗号分隔（如 孤独感,反刍）；与 --constant 同用")
    ap.add_argument("--constant", type=float, help="单样本模式的检验常数（如 Likert 中值 3、常模分）")
    ap.add_argument("--scales", help="scales.txt（两文件模式按题项算量表均分；单文件模式不适用）")
    ap.add_argument("--id", dest="id_col", help="配对编号列名（两文件模式必填；单文件不给则按行配对）")
    ap.add_argument("--group", help="只分析某一组：分组列名（如 组别）")
    ap.add_argument("--level", help="只分析某一组：组取值（如 实验组），与 --group 同用")
    ap.add_argument("--alpha", type=float, default=0.05, help="显著性水平（默认 .05）")
    ap.add_argument("--csv-out", help="结果 CSV 导出路径（默认与输入同目录 _配对检验.csv）")
    ap.add_argument("--report", help="可粘论文报告 txt 路径（默认与输入同目录 _配对检验报告.txt）")
    a = ap.parse_args()

    if not (0 < a.alpha < 1):
        print("✗ --alpha 必须在 0 与 1 之间（如 .05）。")
        sys.exit(1)
    if a.onesample and a.constant is None:
        print("✗ 单样本模式必须用 --constant 给检验常数（如 --constant 3）。")
        sys.exit(1)
    if a.constant is not None and not a.onesample:
        print("✗ --constant 只能与 --onesample 同用（单样本模式）。")
        sys.exit(1)
    if a.onesample and (a.post_file or a.scales or a.id_col):
        print("✗ 单样本模式只支持单文件，不能与两文件/--scales/--id 同用。")
        sys.exit(1)
    if not Path(a.input).exists():
        print(f"✗ 找不到文件：{a.input}")
        sys.exit(1)
    if a.group and not a.level:
        print("✗ 用了 --group 就必须给 --level（如 --group 组别 --level 实验组）。")
        sys.exit(1)
    if bool(a.group) != bool(a.level):
        print("✗ --group 与 --level 必须同时使用。")
        sys.exit(1)

    rows = []
    if a.post_file:
        if not Path(a.post_file).exists():
            print(f"✗ 找不到后测文件：{a.post_file}")
            sys.exit(1)
        if not a.id_col:
            print("✗ 两文件模式必须用 --id 指定配对编号列（如 --id 编号），禁止按行顺序硬凑。")
            sys.exit(1)
        if a.pairs and a.scales:
            print("✗ --pairs 与 --scales 二选一。")
            sys.exit(1)
        if not a.pairs and not a.scales:
            print("✗ 两文件模式需要 --scales scales.txt 或 --pairs 列名。")
            sys.exit(1)
        # 先读原始数据校验编号列（分组列按中文字符串匹配）
        hpre, dpre = read_data(a.input)
        hpost, dpost = read_data(a.post_file)
        if a.group:
            ipre = _filter_group(hpre, dpre, a.group, a.level)
            ipost = _filter_group(hpost, dpost, a.group, a.level)
            dpre = [dpre[i] for i in ipre]
            dpost = [dpost[i] for i in ipost]
        if a.id_col not in hpre or a.id_col not in hpost:
            print(f"✗ 编号列「{a.id_col}」必须同时存在于前测与后测文件。")
            sys.exit(1)
        pre_ids = [r[hpre.index(a.id_col)].strip() if hpre.index(a.id_col) < len(r) else None
                   for r in dpre]
        post_ids = [r[hpost.index(a.id_col)].strip() if hpost.index(a.id_col) < len(r) else None
                    for r in dpost]
        mpre = to_float_matrix(hpre, dpre)
        mpost = to_float_matrix(hpost, dpost)
        if a.scales:
            pre_series = dict(build_dvs(hpre, mpre, a.scales, None))
            post_series = dict(build_dvs(hpost, mpost, a.scales, None))
            pair_specs = [(nm, nm, nm) for nm in pre_series if nm in post_series]
            if not pair_specs:
                print("✗ 两个文件按 scales 算不出共同量表（题项列名需一致）。")
                sys.exit(1)
        else:
            pair_specs = []
            for tok in a.pairs.split(","):
                tok = tok.strip()
                if ":" in tok:
                    c0, c1 = [s.strip() for s in tok.split(":", 1)]
                else:
                    c0 = c1 = tok
                if c0 not in mpre:
                    print(f"✗ 前测文件中找不到列「{c0}」，可用列：{ '、'.join(hpre[:20]) }")
                    sys.exit(1)
                if c1 not in mpost:
                    print(f"✗ 后测文件中找不到列「{c1}」，可用列：{ '、'.join(hpost[:20]) }")
                    sys.exit(1)
                pair_specs.append((f"{c0} → {c1}", c0, c1))
        for label, c0, c1 in pair_specs:
            pre_vals = pre_series[c0] if a.scales else mpre[c0]
            post_vals = post_series[c1] if a.scales else mpost[c1]
            pa, pb, po, qo = _pair_by_id(pre_ids, post_ids, pre_vals, post_vals)
            r = paired_test(label, pa, pb, a.alpha)
            r["n_input"] = len(pa)
            if po or qo:
                r["id_note"] = f"前测独有 {po} 人、后测独有 {qo} 人未纳入"
            rows.append(r)
        base = Path(a.input)
    else:
        if a.scales:
            print("✗ 单文件宽表模式不支持 --scales（量表均分请先跑 auto_stats 导出 _量表总分.csv，"
                  "或改用两文件模式）。")
            sys.exit(1)
        if a.onesample:
            headers, data_rows = read_data(a.input)
            matrix = to_float_matrix(headers, data_rows)
            if a.group:
                idx = _filter_group(headers, data_rows, a.group, a.level)
                matrix = {k: [v[i] for i in idx] for k, v in matrix.items()}
            c = float(a.constant)
            for col in [s.strip() for s in a.onesample.split(",") if s.strip()]:
                if col not in matrix:
                    print(f"✗ 列「{col}」不在数据中，可用列：{ '、'.join(headers[:20]) }")
                    sys.exit(1)
                xv = matrix[col]
                r = paired_test(f"{col}（vs {c:g}）", [c] * len(xv), xv, a.alpha)
                r["mode"] = "onesample"
                r["constant"] = c
                rows.append(r)
            base = Path(a.input)
            print_rows(rows, a.alpha)
            csv_out = a.csv_out or str(base.with_name(base.stem + "_配对检验.csv"))
            rpt_out = a.report or str(base.with_name(base.stem + "_配对检验报告.txt"))
            write_csv(csv_out, rows)
            with io.open(rpt_out, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(make_paragraph(rows, a.alpha) + "\n")
            print(f"\n已导出：{csv_out}")
            print(f"已导出：{rpt_out}")
            return
        if not a.pairs:
            print("✗ 单文件模式需要 --pairs 前测列:后测列（多对用逗号分隔），"
                  "或 --onesample 列 --constant 常数（单样本检验）。")
            sys.exit(1)
        headers, data_rows = read_data(a.input)
        matrix = to_float_matrix(headers, data_rows)
        if a.group:
            idx = _filter_group(headers, data_rows, a.group, a.level)
            matrix = {k: [v[i] for i in idx] for k, v in matrix.items()}
        id_map = None
        if a.id_col:
            if a.id_col not in matrix:
                print(f"✗ 编号列「{a.id_col}」不在数据中。")
                sys.exit(1)
            id_map = [str(v).strip() if v is not None else None for v in matrix[a.id_col]]
        for spec in a.pairs.split(","):
            if ":" not in spec:
                print(f"✗ --pairs 格式应为 前测列:后测列，收到「{spec.strip()}」")
                sys.exit(1)
            c0, c1 = [s.strip() for s in spec.split(":", 1)]
            for c in (c0, c1):
                if c not in matrix:
                    print(f"✗ 列「{c}」不在数据中，可用列：{ '、'.join(headers[:20]) }")
                    sys.exit(1)
            pre_v, post_v = matrix[c0], matrix[c1]
            name = f"{c0} → {c1}"
            if id_map:
                pre_v, post_v, po, qo = _pair_by_id(id_map, id_map, pre_v, post_v)
                r = paired_test(name, pre_v, post_v, a.alpha)
                if po:
                    r["id_note"] = f"{po} 个编号缺一方未纳入"
            else:
                if len(matrix[c0]) != len(matrix[c1]):
                    print(f"✗ 列「{c0}」与「{c1}」行数不同，单文件模式请用 --id 显式配对。")
                    sys.exit(1)
                r = paired_test(name, pre_v, post_v, a.alpha)
            rows.append(r)
        base = Path(a.input)

    print_rows(rows, a.alpha)
    for r in rows:
        if r.get("id_note"):
            print(f"  注（{r['name']}）：{r['id_note']}")

    csv_out = a.csv_out or str(base.with_name(base.stem + "_配对检验.csv"))
    rpt_out = a.report or str(base.with_name(base.stem + "_配对检验报告.txt"))
    write_csv(csv_out, rows)
    with io.open(rpt_out, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(make_paragraph(rows, a.alpha) + "\n")
    print(f"\n已导出：{csv_out}")
    print(f"已导出：{rpt_out}")


if __name__ == "__main__":
    main()
