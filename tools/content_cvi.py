# -*- coding: utf-8 -*-
"""自编量表「内容效度指数 CVI」工具（纯 Python 标准库）

自编/修订量表在做 EFA、CFA 等结构效度之前，先要请一组专家对每一条目的**相关性**
打分（4 级：1=不相关，2=弱相关，3=较强相关，4=非常相关），据此算内容效度。
本工具把教材与期刊常用的几个指数一次算齐，并导出可直接写进论文的内容效度表：

  1) I-CVI（条目水平内容效度指数，Lynn, 1986）：该条目被评为 3 或 4 的专家比例。
  2) 校正机遇一致的 κ*（Polit, Beck & Owen, 2007）：
       Pc = C(N,A) · 0.5^N   （N=专家数，A=评 3/4 的专家数）
       κ* = (I-CVI − Pc) / (1 − Pc)
     评价（Cicchetti & Sparrow, 1981）：κ*<.40 差；.40–.59 一般；.60–.74 良好；>.74 优秀。
  3) S-CVI/Ave（量表水平，平均法，Polit & Beck, 2006）：各条目 I-CVI 的平均，≥.90 优秀。
  4) S-CVI/UA（量表水平，全体一致法）：所有专家都评 3/4 的条目比例，≥.80 较好（比 Ave 严格）。

专家人数与 I-CVI 保留线（Lynn, 1986）：至少 3 人、建议 5～10 人；3～5 人时保留条目
要求 I-CVI=1.00；6 人及以上时 I-CVI≥.78 可接受。κ* 以 >.74（优秀）为常用保留参考。

输入 CSV 格式（Excel 另存为 UTF-8 CSV；第一列为专家姓名/编号，其余每列是一个条目）：
    专家,题1,题2,题3,...
    专家1,4,3,4,...
    专家2,3,3,4,...
单元格为 1～4 的整数；留空表示该专家未评此条（按该条实际参评人数计算）。

用法（在项目根目录）：
  python tools/content_cvi.py 专家评分.csv
  python tools/content_cvi.py 专家评分.csv --csv-out 结果目录
  python tools/content_cvi.py 专家评分.csv --threshold 4   # 仅把“4=非常相关”计为相关

红线：内容效度靠的是专家的专业判断与条目对构念的覆盖，CVI 只是把判断量化；
不达标条目应结合专家开放式意见修改或删除后**重新送审**，不得为凑指数改分。
"""

from pathlib import Path
import argparse
import csv
import math
import os
import sys

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与其他工具同款，避免 GBK 崩溃）---
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stats.dataio import read_data  # noqa: E402

DEFAULT_CSV_SUFFIX = "_内容效度CVI.csv"


def kappa_rating(k):
    """Cicchetti & Sparrow (1981)，Polit 等 (2007) 采用的 κ* 分界。"""
    if k is None:
        return "无法计算"
    if k > 0.74:
        return "优秀"
    if k >= 0.60:
        return "良好"
    if k >= 0.40:
        return "一般"
    return "差"


def item_decision(icvi, k, n_experts):
    """结合 I-CVI（随专家人数的 Lynn 标准）与 κ* 给条目处理建议。"""
    if icvi is None:
        return "数据不足"
    # Lynn(1986)：3-5 名专家要求 I-CVI=1；6 名及以上 ≥.78
    icvi_ok = (icvi >= 1.0 - 1e-9) if n_experts <= 5 else (icvi >= 0.78 - 1e-9)
    if k is not None and k > 0.74 and icvi_ok:
        return "保留"
    if k is not None and k > 0.74 and not icvi_ok and n_experts <= 5:
        return "κ*优秀，但专家≤5人时I-CVI须=1.00，建议增补至≥6名专家复核或修改"
    if k is not None and k >= 0.60 and icvi_ok:
        return "保留（κ*良好，可结合意见微调）"
    if k is not None and k >= 0.40:
        return "修改后重新送审"
    return "建议删除或重写后重新送审"


def analyze(headers, rows, threshold, points):
    """第一列为专家标识，其余列为条目；返回 (条目结果list, 量表dict)。"""
    if len(headers) < 2:
        return None, "至少需要两列：第一列专家、其后至少一个条目列。"
    item_names = headers[1:]
    # 收集每个条目的有效评分
    ratings = {name: [] for name in item_names}
    for rno, row in enumerate(rows, start=2):
        for j, name in enumerate(item_names):
            cell = row[j + 1].strip() if j + 1 < len(row) else ""
            if cell == "":
                continue
            try:
                fv = float(cell)
            except ValueError:
                return None, f"第 {rno} 行「{name}」的评分「{cell}」不是 1-{points} 的整数。"
            if fv != int(fv):
                return None, f"第 {rno} 行「{name}」的评分「{cell}」不是整数（专家评分应为 1-{points} 的整数）。"
            v = int(fv)
            if v < 1 or v > points:
                return None, f"第 {rno} 行「{name}」的评分 {v} 超出 1-{points} 范围（可用 --points 指定点数）。"
            ratings[name].append(v)

    results = []
    for name in item_names:
        vals = ratings[name]
        n = len(vals)
        if n == 0:
            return None, f"条目「{name}」没有任何有效评分。"
        a = sum(1 for v in vals if v >= threshold)
        icvi = a / n
        pc = math.comb(n, a) * (0.5 ** n)
        k = (icvi - pc) / (1 - pc) if (1 - pc) > 1e-12 else 0.0
        results.append({
            "条目": name, "专家数N": n, "评相关人数A": a, "I-CVI": round(icvi, 3),
            "机遇一致Pc": round(pc, 4), "校正kappa": round(k, 3),
            "kappa评价": kappa_rating(k), "建议": item_decision(icvi, k, n),
        })

    icvis = [r["I-CVI"] for r in results]
    ks = [r["校正kappa"] for r in results]
    n_items = len(results)
    scvi_ave = sum(icvis) / n_items
    scvi_ua = sum(1 for r in results if r["I-CVI"] >= 1.0 - 1e-9) / n_items
    n_experts = max(r["专家数N"] for r in results)
    scale = {
        "条目数": n_items, "专家数(最多)": n_experts,
        "S-CVI/Ave": round(scvi_ave, 3), "S-CVI/UA": round(scvi_ua, 3),
        "平均kappa": round(sum(ks) / n_items, 3),
    }
    return results, scale


def resolve_out_path(data_path, csv_out):
    if not csv_out:
        return str(Path(data_path).with_name(Path(data_path).stem + DEFAULT_CSV_SUFFIX))
    if csv_out.lower().endswith(".csv"):
        d = os.path.dirname(os.path.abspath(csv_out))
        os.makedirs(d, exist_ok=True)
        return csv_out
    os.makedirs(csv_out, exist_ok=True)
    return os.path.join(csv_out, Path(data_path).stem + DEFAULT_CSV_SUFFIX)


def write_csv(path, results, scale):
    fields = ["条目", "专家数N", "评相关人数A", "I-CVI", "机遇一致Pc", "校正kappa",
              "kappa评价", "S-CVI/Ave", "S-CVI/UA", "建议"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            row = dict(r)
            row["S-CVI/Ave"] = scale["S-CVI/Ave"]
            row["S-CVI/UA"] = scale["S-CVI/UA"]
            w.writerow(row)


def build_parser():
    p = argparse.ArgumentParser(
        description="自编量表内容效度指数 CVI：I-CVI/校正κ*/S-CVI(Ave、UA)，纯标准库",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("data", nargs="?", help="专家评分 CSV：第一列专家、其余每列一个条目，单元格 1-4")
    p.add_argument("--threshold", type=int, default=3,
                   help="计为“相关”的最低评分，默认 3（即 3/4 相关）；4 级量表常用 3")
    p.add_argument("--points", type=int, default=4,
                   help="评分量表点数，默认 4（1-4 级相关性评分）")
    p.add_argument("--csv-out", dest="csv_out",
                   help="导出路径：给 .csv 文件或目录；默认数据同目录 <数据名>_内容效度CVI.csv")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.data:
        parser.print_help()
        return 0
    if not Path(args.data).exists():
        print(f"✗ 找不到数据文件：{args.data}")
        return 1
    if args.points < 2:
        print("✗ --points 至少为 2。")
        return 1
    if not (2 <= args.threshold <= args.points):
        print(f"✗ --threshold 应在 2 到 {args.points} 之间（4 级量表默认 3）。")
        return 1

    headers, rows = read_data(args.data)
    results, scale_or_msg = analyze(headers, rows, args.threshold, args.points)
    if results is None:
        print(f"✗ {scale_or_msg}")
        return 1
    scale = scale_or_msg

    print("=" * 64)
    print("自编量表内容效度指数 CVI（专家相关性评分）")
    print("=" * 64)
    print(f"专家数 N={scale['专家数(最多)']}，条目数={scale['条目数']}，"
          f"计相关阈值=评分≥{args.threshold}（{args.points} 级量表）")
    print("-" * 64)
    for r in results:
        print(f"  {r['条目']}：I-CVI={r['I-CVI']:.3f}（{r['评相关人数A']}/{r['专家数N']}），"
              f"Pc={r['机遇一致Pc']:.4f}，κ*={r['校正kappa']:.3f}（{r['kappa评价']}）：{r['建议']}")
    print("-" * 64)
    print(f"量表水平：S-CVI/Ave={scale['S-CVI/Ave']:.3f}（≥.90 优秀）；"
          f"S-CVI/UA={scale['S-CVI/UA']:.3f}（≥.80 较好，更严格）；"
          f"平均 κ*={scale['平均kappa']:.3f}")
    if scale["专家数(最多)"] <= 5:
        print("提示：仅 3～5 名专家时，Lynn(1986) 要求保留条目 I-CVI=1.00；条件允许建议邀请 5～10 名专家。")
    if scale["S-CVI/Ave"] >= 0.90:
        print("结论：S-CVI/Ave≥.90，整体内容效度优秀；仍需逐条核对 κ* 与专家意见。")
    else:
        print("结论：S-CVI/Ave 未达 .90，请对 I-CVI/κ* 偏低条目按专家意见修改后重新送审。")
    print("红线：CVI 量化的是专家共识；不达标条目要结合开放式意见修改/删除并重审，不得改分凑指数。")

    out_path = resolve_out_path(args.data, args.csv_out)
    write_csv(out_path, results, scale)
    print(f"\n内容效度表已导出：{out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
