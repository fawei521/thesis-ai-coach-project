# -*- coding: utf-8 -*-
"""描述统计、频数表与三线表导出

数据画像、人口学频数表、M/SD 与偏度峰度正态性判读、
描述＋相关＋α 整合三线表（论文表1/表2 口径）。

本模块由 tools/auto_stats.py 拆分而来（v1.53.1），函数体逐行未改动。
"""

import csv
import math

from .mathx import mean, normality_tag, pearson_r, sig_mark, skew_kurt, stdev, t_p_two_sided

# ============ 描述统计、频数表与三线表导出 ============

def data_profile(headers, data, matrix, num_cols):
    print("\n" + "=" * 60)
    print("一、数据画像")
    print("=" * 60)
    print(f"总样本量：{len(data)}")
    print(f"总变量数：{len(headers)}")
    print(f"数值变量：{len(num_cols)}个")
    print(f"非数值变量：{len(headers) - len(num_cols)}个")

    print("\n缺失值情况：")
    total_missing = 0
    for h in num_cols:
        miss = sum(1 for v in matrix[h] if v is None)
        total_missing += miss
        if miss > 0:
            pct = miss / len(matrix[h]) * 100
            print(f"  {h}：缺失{miss}个（{pct:.1f}%）")
    if total_missing == 0:
        print("  无缺失值")


def frequency_analysis(headers, data, matrix, scales, output=None):
    """人口学/分类变量频数分析。自动识别量表题目之外、取值种类≤10的列
    （性别、年级、生源地、是否独生子女、专业等，兼容文本和1/2编码），
    输出频数与百分比并导出，供论文“研究对象/样本构成”部分直接使用。"""
    scale_items = set()
    for conf in scales.values():
        scale_items.update(conf["items"])

    sections = []
    table_rows = []
    for ci, c in enumerate(headers):
        if c in scale_items:
            continue
        col = matrix.get(c, [])
        if any(v is not None for v in col):
            vals = [v for v in col if v is not None]
            numeric = True
        else:
            vals = []
            for r in data:
                if ci < len(r):
                    t = r[ci].strip()
                    if t:
                        vals.append(t)
            numeric = False
        if not vals:
            continue
        uniq = set(vals)
        # 文本分类列（性别/生源地等）取值≤10类；数值编码列（性别1/2、年级1-4）取值≤4类，
        # 以排除5点/7点Likert题（量表题另外已通过scale_items排除）
        max_cat = 10 if not numeric else 4
        if len(uniq) > max_cat:
            continue
        n = len(vals)
        counts = {}
        for v in vals:
            counts[v] = counts.get(v, 0) + 1
        keys = sorted(counts) if numeric else sorted(counts, key=lambda k: -counts[k])
        lines = []
        for k in keys:
            pct = counts[k] / n * 100
            label = str(int(k)) if numeric and float(k).is_integer() else str(k)
            lines.append(f"    {label}：{counts[k]}人（{pct:.1f}%）")
            table_rows.append({"变量": c, "取值": label, "频数": counts[k],
                               "百分比%": round(pct, 1)})
        sections.append((c, n, lines))

    if not sections:
        return None
    print("\n" + "=" * 60)
    print("研究对象（人口学/分类变量频数）")
    print("=" * 60)
    for c, n, lines in sections:
        print(f"\n{c}（N={n}）")
        for ln in lines:
            print(ln)
    if output:
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["变量", "取值", "频数", "百分比%"])
            w.writeheader()
            w.writerows(table_rows)
        print(f"\n频数表已导出：{output}")
    return table_rows


def descriptive(matrix, num_cols):
    print("\n" + "=" * 60)
    print("描述统计（含偏度/峰度正态性；Kline判据 |偏度|<3、|峰度|<10）")
    print("=" * 60)
    print(f"{'变量':<12}{'N':>6}{'均值':>9}{'标准差':>9}{'最小':>7}{'最大':>7}{'偏度':>8}{'峰度':>8}")
    print("-" * 70)
    results = []
    for h in num_cols:
        vals = [v for v in matrix[h] if v is not None]
        if not vals:
            continue
        m, sd = mean(vals), stdev(vals)
        g1, g2 = skew_kurt(vals)
        g1t = f"{g1:>8.2f}" if g1 is not None else f"{'NA':>8}"
        g2t = f"{g2:>8.2f}" if g2 is not None else f"{'NA':>8}"
        print(f"{h:<12}{len(vals):>6}{m:>9.3f}{sd:>9.3f}{min(vals):>7.1f}{max(vals):>7.1f}{g1t}{g2t}")
        results.append({"变量": h, "N": len(vals),
                        "均值": round(m, 3), "标准差": round(sd, 3),
                        "最小值": min(vals), "最大值": max(vals),
                        "偏度": round(g1, 3) if g1 is not None else "",
                        "峰度": round(g2, 3) if g2 is not None else "",
                        "正态性": normality_tag(g1, g2)})
    return results


def export_three_line_table(desc, corr, output, matrix=None, score_cols=None, alpha_map=None):
    """导出三线表：表1描述统计与正态性；表2描述+相关矩阵+信度(对角α)；表3相关明细(含p)。"""
    with open(output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["表1 描述统计与正态性"])
        w.writerow(["变量", "N", "均值", "标准差", "最小值", "最大值", "偏度", "峰度", "正态性判读"])
        for d in desc:
            w.writerow([d["变量"], d["N"], d["均值"], d["标准差"],
                        d.get("最小值", ""), d.get("最大值", ""),
                        d.get("偏度", ""), d.get("峰度", ""), d.get("正态性", "")])
        w.writerow([])

        if matrix is not None and score_cols:
            cols = [c for c in score_cols if c in matrix]
            if cols:
                dmap = {d["变量"]: d for d in desc}
                w.writerow(["表2 描述统计、相关矩阵与信度（对角括号内为Cronbach's α，下三角为Pearson r，*p<.05 **p<.01 ***p<.001）"])
                w.writerow(["变量", "均值M", "标准差SD"] + [str(i + 1) for i in range(len(cols))])
                for i, ci in enumerate(cols):
                    row = [ci, dmap.get(ci, {}).get("均值", ""), dmap.get(ci, {}).get("标准差", "")]
                    for j, cj in enumerate(cols):
                        if j > i:
                            row.append("")
                        elif j == i:
                            a = alpha_map.get(ci) if alpha_map else None
                            row.append(f"({a:.3f})" if a is not None else "1")
                        else:
                            r, nn = pearson_r(matrix[ci], matrix[cj])
                            if r is not None and nn and nn > 2:
                                t = r * math.sqrt((nn - 2) / max(1 - r * r, 1e-12))
                                star = sig_mark(t_p_two_sided(t, nn - 2))
                            else:
                                star = ""
                            row.append(f"{r:.3f}{star}" if r is not None else "")
                    w.writerow(row)
                w.writerow([])
                w.writerow(["变量编号"] + [f"{i + 1}={c}" for i, c in enumerate(cols)])
                w.writerow([])

        w.writerow(["表3 相关分析明细（r, 双尾p, 成对N）"])
        w.writerow(["变量1", "变量2", "r", "p", "显著性", "N"])
        for c in corr:
            w.writerow([c["变量1"], c["变量2"], c["r"], c["p"], c["显著性"], c["N"]])
    print(f"\n三线表已导出：{output}")
