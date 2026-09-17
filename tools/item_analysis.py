# -*- coding: utf-8 -*-
"""问卷预试「项目分析」工具（纯 Python 标准库）

预试问卷回收后、正式分析前，需要逐题做项目分析以决定删改哪些题。本工具把教材里
分散的几步一次性算齐，并导出可直接放进论文的项目分析表：

  1) 决断值 CR（临界比）：按量表总分把完整作答者由低到高排序，取前 27%（低分组）
     与后 27%（高分组），对每一题做独立样本 t 检验，t 即决断值 CR；常用保留标准
     为 |CR|≥3 且 p<.05（题项能区分高/低特质者）。
  2) CITC 校正项总相关：该题与「其余题目总分」的相关，建议 ≥.40。
  3) 删题后 α：删掉该题后整表的 Cronbach's α，不应明显高于整表 α。
  4) 题项均值、标准差。
  综合给出「保留 / 建议结合理论讨论删改」，但删题必须同时看内容效度与专业理论，
  不能只凭数字删题。

用法（在项目根目录）：
  python tools/item_analysis.py 数据.csv --scales scales.txt
  python tools/item_analysis.py 数据.csv --scales scales.txt --only 孤独感
  python tools/item_analysis.py 数据.csv --scales scales.txt --group 0.27 --csv-out 结果目录

scales.txt 格式与 auto_stats 相同，每行：量表名[:点数]=题1,题2(R),题3
反向题必须用 (R) 或 * 标对，否则决断值方向会反。默认在数据同目录导出
「<数据名>_项目分析.csv」（UTF-8-BOM，Excel 可直接打开）。

红线：本工具只用于预试问卷的题项甄别；决断值/CITC 不达标只提示讨论，不替你删题；
正式施测数据不要再用预试的删题标准反复筛；任何数字不得为达标而篡改。
"""

from pathlib import Path
import argparse
import csv
import math
import os
import sys

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与 auto_stats.py 同款，避免 GBK 崩溃）---
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stats.dataio import parse_scales, read_data, recoded_item_series, to_float_matrix  # noqa: E402
from stats.mathx import fmt_p, mean, pearson_r, stdev, t_p_two_sided  # noqa: E402
from stats.reliability import cronbach_alpha  # noqa: E402

DEFAULT_CSV_SUFFIX = "_项目分析.csv"


def pooled_independent_t(low, high):
    """等方差独立样本 t（经典决断值 CR 口径）。返回 (t, df)；方差为 0 无法算则 None。"""
    n1, n2 = len(low), len(high)
    if n1 < 2 or n2 < 2:
        return None
    v1, v2 = stdev(low) ** 2, stdev(high) ** 2
    df = n1 + n2 - 2
    sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / df
    if sp2 <= 0:
        return None
    t = (mean(high) - mean(low)) / math.sqrt(sp2 * (1.0 / n1 + 1.0 / n2))
    return t, df


def analyze_scale(scale_name, conf, matrix, group_prop):
    """对单个量表逐题做项目分析，返回 (行列表, 摘要dict)。"""
    available = [it for it in conf["items"] if it in matrix]
    missing = [it for it in conf["items"] if it not in matrix]
    if missing:
        print(f"⚠ {scale_name}：以下题目在数据中找不到，已跳过：{missing}")
    if len(available) < 2:
        print(f"✗ {scale_name}：可用题目不足 2 个，无法做项目分析。")
        return [], None

    series = recoded_item_series(matrix, conf)  # 反向计分后的题列，与 available 同序
    k = len(series)
    n_rows = len(series[0])

    # 仅用所有题目都作答的完整样本算总分、分组与各指标，保证口径一致
    complete = [i for i in range(n_rows) if all(series[j][i] is not None for j in range(k))]
    n = len(complete)
    if n < 8:
        print(f"✗ {scale_name}：完整作答样本仅 {n} 份，无法可靠划分高低分组（至少需要约 8 份）。")
        return [], None

    totals = {i: sum(series[j][i] for j in range(k)) for i in complete}
    ordered = sorted(complete, key=lambda i: totals[i])
    g = int(round(group_prop * n))
    g = max(2, min(g, n // 2))
    low_idx, high_idx = ordered[:g], ordered[-g:]

    alpha = cronbach_alpha(series)

    print(f"\n{scale_name}（{k} 题，完整样本 N={n}，高/低分组各 {g} 人，整表 α="
          f"{alpha:.3f}）" if alpha is not None else
          f"\n{scale_name}（{k} 题，完整样本 N={n}，高/低分组各 {g} 人，α 无法计算）")
    print("    判定参考：|CR|≥3 且 p<.05；CITC≥.40；删题后α不应明显高于整表α")

    rows, flagged = [], 0
    for idx, name in enumerate(available):
        col = series[idx]
        vals = [col[i] for i in complete]
        m, sd = mean(vals), stdev(vals)
        low_vals = [col[i] for i in low_idx]
        high_vals = [col[i] for i in high_idx]
        tt = pooled_independent_t(low_vals, high_vals)
        if tt is not None:
            cr, df = tt
            p = t_p_two_sided(cr, df)
        else:
            cr = df = p = None
        # CITC：该题与其余题目总分的相关（完整样本）
        rest_totals = [sum(series[j][i] for j in range(k) if j != idx) for i in complete]
        citc, _ = pearson_r(vals, rest_totals)
        # 删题后 α
        others = [series[j] for j in range(k) if j != idx]
        a_del = cronbach_alpha(others)

        flags = []
        if cr is None:
            flags.append("决断值无法计算")
        else:
            if p is not None and p >= 0.05:
                flags.append("CR不显著")
            if abs(cr) < 3:
                flags.append("|CR|<3")
        if citc is not None and citc < 0.40:
            flags.append("CITC<.40")
        if a_del is not None and alpha is not None and a_del > alpha + 0.02:
            flags.append("删题后α升高")
        verdict = "建议结合理论讨论删改" if flags else "保留"
        if flags:
            flagged += 1
        rtag = "(反向)" if conf.get("reverse", {}).get(name) else ""
        cr_txt = f"{cr:.3f}" if cr is not None else "NA"
        p_txt = fmt_p(p) if p is not None else "NA"
        citc_txt = f"{citc:.3f}" if citc is not None else "NA"
        ad_txt = f"{a_del:.3f}" if a_del is not None else "NA"
        mark = "；".join(flags)
        tail = f"  ← {mark}" if mark else ""
        print(f"    {name}{rtag}：M={m:.2f}，SD={sd:.2f}，CR={cr_txt}（df={df}，{p_txt}），"
              f"CITC={citc_txt}，删题后α={ad_txt}：{verdict}{tail}")
        rows.append({
            "量表": scale_name, "题项": name + rtag, "均值": round(m, 3), "标准差": round(sd, 3),
            "决断值CR": round(cr, 3) if cr is not None else "",
            "自由度df": df if df is not None else "",
            "p双侧": (round(p, 4) if p is not None else ""),
            "CITC校正项总相关": round(citc, 3) if citc is not None else "",
            "删题后alpha": round(a_del, 3) if a_del is not None else "",
            "量表alpha": round(alpha, 3) if alpha is not None else "",
            "判定": verdict, "提示": mark,
        })
    summary = {"量表": scale_name, "题数": k, "完整样本N": n, "每组人数": g,
               "Cronbach_alpha": round(alpha, 3) if alpha is not None else "",
               "待讨论题数": flagged}
    return rows, summary


def resolve_out_path(data_path, csv_out):
    """默认写到数据同目录 <stem>_项目分析.csv；--csv-out 给目录或 .csv 路径均可。"""
    if not csv_out:
        return str(Path(data_path).with_name(Path(data_path).stem + DEFAULT_CSV_SUFFIX))
    if csv_out.lower().endswith(".csv"):
        d = os.path.dirname(os.path.abspath(csv_out))
        os.makedirs(d, exist_ok=True)
        return csv_out
    os.makedirs(csv_out, exist_ok=True)
    return os.path.join(csv_out, Path(data_path).stem + DEFAULT_CSV_SUFFIX)


def write_csv(path, rows):
    fields = ["量表", "题项", "均值", "标准差", "决断值CR", "自由度df", "p双侧",
              "CITC校正项总相关", "删题后alpha", "量表alpha", "判定", "提示"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def build_parser():
    p = argparse.ArgumentParser(
        description="问卷预试项目分析：决断值CR(高低27%t检验)+CITC+删题后α，导出项目分析表（纯标准库）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("data", nargs="?", help="预试数据 CSV（UTF-8 或 GBK，题项为列、每行一名被试）")
    p.add_argument("--scales", help="量表配置文件（同 auto_stats 的 scales.txt；反向题用 (R) 标记）")
    p.add_argument("--only", help="只分析指定量表（默认分析配置中的全部量表）")
    p.add_argument("--group", type=float, default=0.27,
                   help="极端组比例，默认 0.27（前后 27%%），可在 0.10-0.50 间调整")
    p.add_argument("--csv-out", dest="csv_out",
                   help="导出路径：给 .csv 文件或目录；默认数据同目录 <数据名>_项目分析.csv")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.data:
        parser.print_help()
        return 0
    if not args.scales:
        print("✗ 缺少量表配置：请用 --scales scales.txt 指定（格式：量表名=题1,题2(R),题3）。")
        return 1
    if not Path(args.data).exists():
        print(f"✗ 找不到数据文件：{args.data}")
        return 1
    if not (0.10 <= args.group <= 0.50):
        print("✗ --group 极端组比例应在 0.10 到 0.50 之间（常用 0.27）。")
        return 1

    scales = parse_scales(args.scales)
    if not scales:
        print(f"✗ 未能从 {args.scales} 读到任何量表，请检查格式（每行：量表名=题1,题2(R),题3）。")
        return 1
    if args.only:
        if args.only not in scales:
            print(f"✗ --only「{args.only}」不在配置中；可用量表：{ '、'.join(scales.keys()) }")
            return 1
        scales = {args.only: scales[args.only]}

    headers, data = read_data(args.data)
    matrix = to_float_matrix(headers, data)

    print("=" * 64)
    print("问卷预试项目分析（决断值CR / CITC / 删题后α）")
    print("=" * 64)
    all_rows, summaries = [], []
    for scale_name, conf in scales.items():
        rows, summ = analyze_scale(scale_name, conf, matrix, args.group)
        all_rows.extend(rows)
        if summ:
            summaries.append(summ)

    if not all_rows:
        print("\n✗ 没有可分析的题目，请检查数据列名与 scales.txt 是否一致。")
        return 1

    out_path = resolve_out_path(args.data, args.csv_out)
    write_csv(out_path, all_rows)

    print("\n" + "-" * 64)
    print("量表小结：")
    for s in summaries:
        print(f"    {s['量表']}：{s['题数']}题，N={s['完整样本N']}，α={s['Cronbach_alpha']}，"
              f"待讨论题 {s['待讨论题数']} 道")
    print(f"\n项目分析表已导出：{out_path}")
    print("红线：① 决断值=高低27%组独立样本t，|CR|≥3且p<.05、CITC≥.40 仅为经验参考；"
          "② 删题须同时结合内容效度与专业理论，不能只凭数字；"
          "③ 反向题务必在 scales.txt 标 (R)；④ 该分析用于预试题项甄别，正式数据不要反复套用删题。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
