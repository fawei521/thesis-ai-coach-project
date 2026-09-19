#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多重比较校正工具（Bonferroni / Holm / Benjamini-Hochberg FDR / BY）
==================================================================
同一家族做了多个统计检验时（多组两两比较、多个量表同时比较、多个相关
系数、多个时点重复配对 t），"只要有一个 p<.05 就显著"会让假阳性随检验
次数膨胀。本工具对一组原始 p 值统一做多重比较校正，并给可粘论文的结论。

方法（与 R p.adjust / scipy.stats.false_discovery_control 同口径）：
  - bonferroni：p_adj = min(1, m·p)。控制族系错误率 FWER，最简单也最保守；
    等价于把显著性阈值收紧到 α/m。检验数少（≤5）、要严格控制假阳性时用。
  - holm：Holm 逐步法（step-down），同样严格控制 FWER，但比 Bonferroni
    更有功效，是 Bonferroni 的直接替代（R p.adjust("holm")，默认推荐）。
  - bh：Benjamini-Hochberg 逐步法（step-up），控制错误发现率 FDR
    （显著结果中预期假阳性比例），探索性分析、检验数多（如相关矩阵、
    多量表筛查）时用；R p.adjust("BH")/scipy false_discovery_control。
  - by：Benjamini-Yekutieli，在任意相关结构下控制 FDR，比 BH 保守
    （除以调和数 c(m)=Σ1/i）；检验间明显相关且要稳健时用。

红线（工具只做校正，不替你挑结果）：
  - 校正方法必须在看结果之前确定，不能三种都跑、挑最宽松的报；
  - 报告时同时给原始 p 与校正后 p（或注明校正方法与阈值），不得只报显著的；
  - "一个家族"包含哪些检验要事先界定（同一研究问题下的一组比较才算一个家族）；
  - 校正后不显著也是结果，不得回头删比较凑显著。

用法（项目根目录）：
  python tools/mult_compare.py --ps .032,.001,.45,.12
  python tools/mult_compare.py 差异分析.csv --pcol p值 --namecol 对比
  python tools/mult_compare.py --ps .01,.04 --method holm --alpha 0.05
导出 _多重比较校正.csv（UTF-8-BOM）与 _多重比较报告.txt（可粘论文）。
"""
import argparse
import csv
import io
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats.dataio import read_data  # noqa: E402
from stats.mathx import fmt_p  # noqa: E402

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与其他工具同款，避免 GBK 崩溃）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

METHODS = ["bonferroni", "holm", "bh", "by"]
METHOD_CN = {
    "bonferroni": "Bonferroni",
    "holm": "Holm",
    "bh": "Benjamini-Hochberg FDR",
    "by": "Benjamini-Yekutieli FDR",
}


# ================================================================ 校正算法
def _cap(v):
    return min(1.0, max(0.0, v))


def bonferroni(ps):
    m = len(ps)
    return [_cap(m * p) for p in ps]


def holm(ps):
    """Holm 逐步法：排序后 p_(i) 乘 (m−i+1)，前缀累积取大，再映回原顺序。"""
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj_sorted = [0.0] * m
    run = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * ps[idx]
        run = max(run, val)
        adj_sorted[rank] = _cap(run)
    out = [0.0] * m
    for rank, idx in enumerate(order):
        out[idx] = adj_sorted[rank]
    return out


def _bh_raw(ps):
    """BH 逐步法：从大到小 p_(i)·m/i，后缀累积取小。返回原顺序调整 p。"""
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj_sorted = [0.0] * m
    run = 1.0
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        i = rank + 1
        # 与 scipy false_discovery_control 同运算顺序：先算 m/i 再乘 p，
        # 避免 m*p/i 在临界值上产生 0.049999999999999996 这类边界翻转
        val = ps[idx] * (m / i)
        run = min(run, val)
        adj_sorted[rank] = _cap(run)
    out = [0.0] * m
    for rank, idx in enumerate(order):
        out[idx] = adj_sorted[rank]
    return out


def benjamini_hochberg(ps):
    return _bh_raw(ps)


def benjamini_yekutieli(ps):
    m = len(ps)
    cm = sum(1.0 / i for i in range(1, m + 1))
    return [_cap(q * cm) for q in _bh_raw(ps)]


def adjust(ps, method):
    return {
        "bonferroni": bonferroni,
        "holm": holm,
        "bh": benjamini_hochberg,
        "by": benjamini_yekutieli,
    }[method](ps)


# ================================================================ IO
def read_inputs(a):
    """返回 (names, ps)。"""
    if a.ps:
        try:
            ps = [float(x.strip()) for x in a.ps.split(",") if x.strip() != ""]
        except ValueError:
            print("✗ --ps 必须是逗号分隔的数字（如 .032,.001,.45）。")
            sys.exit(1)
        names = None
        if a.names:
            names = [x.strip() for x in a.names.split(",")]
            if len(names) != len(ps):
                print(f"✗ --names 个数（{len(names)}）与 p 值个数（{len(ps)}）不一致。")
                sys.exit(1)
        return names, ps
    if a.input:
        if not Path(a.input).exists():
            print(f"✗ 找不到文件：{a.input}")
            sys.exit(1)
        headers, rows = read_data(a.input)
        if not rows or not headers:
            print("✗ CSV 为空或读不到表头。")
            sys.exit(1)
        if a.pcol not in headers:
            print(f"✗ p 值列「{a.pcol}」不在 CSV 中，可用列：{ '、'.join(headers) }")
            sys.exit(1)
        pj = headers.index(a.pcol)
        nj = headers.index(a.namecol) if a.namecol else None
        if a.namecol and nj is None:
            print(f"✗ 名称列「{a.namecol}」不在 CSV 中，可用列：{ '、'.join(headers) }")
            sys.exit(1)
        names, ps = [], []
        for r in rows:
            if pj >= len(r) or r[pj].strip() == "":
                continue
            try:
                ps.append(float(r[pj]))
            except ValueError:
                print(f"✗ p 值列第 {len(ps) + 1} 行不是数字：{r[pj]}")
                sys.exit(1)
            names.append(r[nj].strip() if nj is not None and nj < len(r)
                         else f"检验{len(ps)}")
        return names, ps
    print("✗ 请用 --ps 0.01,0.02,... 直接给 p 值，或把 CSV 作为参数并加 --pcol 列名。")
    sys.exit(1)


# ================================================================ 呈现
def print_table(names, ps, res, alpha, method):
    m = len(ps)
    print("多重比较校正（m = %d 个检验，α = %g）" % (m, alpha))
    print("=" * 86)
    head = f"{'#':>2}  {'名称':<16}{'原始p':>10}"
    methods = METHODS if method == "all" else [method]
    for mm in methods:
        head += f"{METHOD_CN[mm].split(' ')[0]:>12}"
    print(head)
    print("-" * 86)
    for i, p in enumerate(ps):
        nm = (names[i] if names else f"检验{i + 1}")
        if len(nm) > 15:
            nm = nm[:15]
        line = f"{i + 1:>2}  {nm:<16}{fmt_p(p):>10}"
        for mm in methods:
            q = res[mm][i]
            mark = "*" if q < alpha else " "
            line += f"{fmt_p(q) + mark:>12}"
        print(line)
    print("-" * 86)
    print("注：* 表示校正后 p<α；Bonferroni/Holm 控制 FWER，BH/BY 控制 FDR。")
    for mm in methods:
        sig = [i for i in range(m) if res[mm][i] < alpha]
        sig_names = "、".join((names[i] if names else f"#{i + 1}") for i in sig) or "无"
        print(f"  {METHOD_CN[mm]}：校正后显著 {len(sig)}/{m}（{sig_names}）")


def make_report(names, ps, res, alpha, method):
    m = len(ps)
    methods = METHODS if method == "all" else [method]
    L = ["多重比较校正结果（可粘贴进论文，数字请与 SPSS/R 复核）", ""]
    label = {
        "bonferroni": "Bonferroni 法",
        "holm": "Holm 逐步法",
        "bh": "Benjamini-Hochberg（FDR）法",
        "by": "Benjamini-Yekutieli（FDR）法",
    }[methods[0] if len(methods) == 1 else "holm"]
    if len(methods) > 1:
        L.append(f"对同一研究问题下的 {m} 个检验分别采用 Bonferroni、Holm、BH（FDR）"
                 f"与 BY 法做多重比较校正（α={alpha:g}），结果见附表；论文中只应报告"
                 "事先选定的一种方法。")
    else:
        mm = methods[0]
        sig = [i for i in range(m) if res[mm][i] < alpha]
        nsig = m - len(sig)
        sig_names = "、".join((names[i] if names else f"检验{i + 1}") for i in sig) or "无"
        L.append(f"采用{label}对 {m} 个检验的 p 值进行多重比较校正（家族显著性水平 "
                 f"α={alpha:g}）。校正后 {len(sig)} 个检验显著、{nsig} 个不显著"
                 f"（显著项：{sig_names}）。原始 p 与校正后 p 见下表。")
        if mm == "bonferroni":
            L.append(f"Bonferroni 校正阈值为 α/m={alpha:g}/{m}={alpha / m:.4f}，"
                     "该法最保守；若与 Holm 结果一致可在文中注明。")
        if mm == "bh":
            L.append("BH 法控制的是错误发现率（FDR）而非族系错误率（FWER），"
                     "适用于探索性、检验数较多的情形；确证性检验建议用 Holm。")
    L.append("")
    L.append("注：校正方法在分析前确定；报告同时保留原始 p 与校正后 p；"
             "校正后不显著也是结果，不得删并检验或改报未校正结论。")
    L.append("")
    L.append("明细：")
    for i, p in enumerate(ps):
        nm = (names[i] if names else f"检验{i + 1}")
        cells = "；".join(f"{METHOD_CN[mm].split(' ')[0]}={fmt_p(res[mm][i])}"
                         for mm in methods)
        L.append(f"· {nm}：原始 p={fmt_p(p)}；{cells}")
    return "\n".join(L)


def write_csv(path, names, ps, res, alpha):
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["序号", "名称", "原始p",
                    "Bonferroni校正p", "Holm校正p", "BH_FDR校正q", "BY_FDR校正q",
                    "Bonferroni显著", "Holm显著", "BH显著", "BY显著"])
        for i, p in enumerate(ps):
            nm = names[i] if names else f"检验{i + 1}"
            w.writerow([i + 1, nm, fmt_p(p), fmt_p(res["bonferroni"][i]),
                        fmt_p(res["holm"][i]), fmt_p(res["bh"][i]), fmt_p(res["by"][i]),
                        "是" if res["bonferroni"][i] < alpha else "否",
                        "是" if res["holm"][i] < alpha else "否",
                        "是" if res["bh"][i] < alpha else "否",
                        "是" if res["by"][i] < alpha else "否"])


# ================================================================ 主流程
def main():
    ap = argparse.ArgumentParser(
        description="多重比较校正（Bonferroni/Holm/BH-FDR/BY-FDR，与 R p.adjust 同口径）")
    ap.add_argument("input", nargs="?", help="含 p 值列的 CSV（如差异分析/相关矩阵导出）")
    src = ap.add_argument_group("p 值来源（二选一）")
    src.add_argument("--ps", help="逗号分隔的原始 p 值，如 .032,.001,.45")
    src.add_argument("--pcol", help="CSV 中 p 值列的列名（--csv 时必填）")
    src.add_argument("--namecol", help="CSV 中检验名称列的列名（可选）")
    src.add_argument("--names", help="--ps 模式下各 p 值的名称，逗号分隔")
    ap.add_argument("--method", choices=METHODS + ["all"], default="holm",
                    help="校正方法：bonferroni/holm/bh/by，默认 holm；all=四种全列")
    ap.add_argument("--alpha", type=float, default=0.05, help="家族显著性水平（默认 .05）")
    ap.add_argument("--csv-out", help="结果 CSV 路径（默认与输入同目录 _多重比较校正.csv）")
    ap.add_argument("--report", help="报告 txt 路径（默认与输入同目录 _多重比较报告.txt）")
    a = ap.parse_args()

    if not (0 < a.alpha < 1):
        print("✗ --alpha 必须在 0 与 1 之间（如 .05）。")
        sys.exit(1)
    if a.input and not a.pcol:
        print("✗ CSV 模式必须用 --pcol 指定 p 值列名。")
        sys.exit(1)
    names, ps = read_inputs(a)
    if not ps:
        print("✗ 没有读到任何 p 值。")
        sys.exit(1)
    bad = [p for p in ps if not (0 <= p <= 1)]
    if bad:
        print(f"✗ p 值必须在 0～1 之间，收到越界值：{bad[:5]}")
        sys.exit(1)
    if len(ps) < 2:
        print("✗ 多重比较校正至少需要 2 个 p 值（只有 1 个检验无需校正）。")
        sys.exit(1)

    res = {mm: adjust(ps, mm) for mm in METHODS}
    print_table(names, ps, res, a.alpha, a.method)

    if a.input:
        base = Path(a.input)
        csv_out = a.csv_out or str(base.with_name(base.stem + "_多重比较校正.csv"))
        rpt_out = a.report or str(base.with_name(base.stem + "_多重比较报告.txt"))
    else:
        # --ps 直给模式没有输入文件，默认落在当前工作目录，下划线前缀便于识别清理
        csv_out = a.csv_out or "_多重比较校正.csv"
        rpt_out = a.report or "_多重比较报告.txt"
    write_csv(csv_out, names, ps, res, a.alpha)
    with io.open(rpt_out, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(make_report(names, ps, res, a.alpha, a.method) + "\n")
    print(f"\n已导出：{csv_out}")
    print(f"已导出：{rpt_out}")


if __name__ == "__main__":
    main()
