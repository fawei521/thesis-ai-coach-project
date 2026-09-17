# -*- coding: utf-8 -*-
"""信度分析

Cronbach's α、逐题 CITC 与删题后 α、分半信度（前后半/奇偶，
Spearman-Brown 与 Guttman λ4）、量表总分计算与数据集导出。

本模块由 tools/auto_stats.py 拆分而来（v1.53.1），函数体逐行未改动。
"""

import csv

from .dataio import recoded_item_series
from .mathx import pearson_r, variance

# ============ 信度分析 ============

def cronbach_alpha(items_data):
    """
    Cronbach's α
    items_data: list of lists，每个子列表是一个题目的所有作答
    """
    k = len(items_data)
    if k < 2:
        return None
    n = len(items_data[0])
    item_vars = []
    total_scores = [0.0] * n
    valid_count = 0
    for i in range(n):
        row_vals = [items_data[j][i] for j in range(k) if items_data[j][i] is not None]
        if len(row_vals) == k:
            total_scores[i] = sum(row_vals)
            valid_count += 1
        else:
            total_scores[i] = None
    for item in items_data:
        vals = [v for v in item if v is not None]
        item_vars.append(variance(vals))
    valid_totals = [t for t in total_scores if t is not None]
    if len(valid_totals) < 3:
        return None
    total_var = variance(valid_totals)
    if total_var == 0:
        return None
    alpha = (k / (k - 1)) * (1 - sum(item_vars) / total_var)
    return alpha


def build_scale_scores(matrix, scales):
    """用反向计分后的题目计算每个量表的总分/均分。
    返回 score_matrix：{“量表总分”:[...], “量表均分”:[...]}；题目有缺失则该样本为None。"""
    n = len(next(iter(matrix.values()))) if matrix else 0
    score_matrix = {}
    for name, conf in scales.items():
        available = [it for it in conf["items"] if it in matrix]
        rec = recoded_item_series(matrix, conf) if available else []
        totals, means = [], []
        for i in range(n):
            vals = [rec[j][i] for j in range(len(rec)) if rec[j][i] is not None]
            if len(rec) >= 2 and len(vals) == len(rec):
                totals.append(round(sum(vals), 3))
                means.append(round(sum(vals) / len(vals), 3))
            else:
                totals.append(None)
                means.append(None)
        score_matrix[f"{name}总分"] = totals
        score_matrix[f"{name}均分"] = means
    return score_matrix, n


def split_half(items_data):
    """分半信度。items_data 为反向计分后的题目列（每列一个题，含 None 缺失）。
    返回前后半（SPSS 口径，前 floor(k/2) 题 vs 其余）的两半 α、两半总分相关 r、
    Spearman-Brown 等长系数 2r/(1+r)、Guttman λ4=2(1−(var1+var2)/varTotal)，
    以及奇偶分半（题序奇偶）的 r 与 SB（奇数题时两半等长或仅差1题，更稳健）。"""
    k = len(items_data)
    if k < 4:
        return None
    n = len(items_data[0])

    cut = k // 2
    front = list(range(0, cut))
    back = list(range(cut, k))
    odd = list(range(0, k, 2))
    even = list(range(1, k, 2))

    def pack(ia, ib):
        # 只用两半题目都完整的同一批样本算两半 α、相关与 λ4，保证口径一致
        complete = []
        for r in range(n):
            vals = [items_data[j][r] for j in ia + ib]
            if all(v is not None for v in vals):
                complete.append(vals)
        if len(complete) < 4:
            return None
        na = len(ia)
        h1 = [sum(row[:na]) for row in complete]
        h2 = [sum(row[na:]) for row in complete]
        tot = [a + b for a, b in zip(h1, h2)]
        r, _ = pearson_r(h1, h2)
        if r is None:
            return None
        sb = 2 * r / (1 + r)
        v1, v2, vt = variance(h1), variance(h2), variance(tot)
        gutt = 2 * (1 - (v1 + v2) / vt) if vt > 0 else None
        cols1 = [[row[i] for row in complete] for i in range(na)]
        cols2 = [[row[na + i] for row in complete] for i in range(len(ib))]
        a1 = cronbach_alpha(cols1)
        a2 = cronbach_alpha(cols2)
        return {"r": r, "sb": sb, "guttman_lambda4": gutt,
                "alpha_half1": a1, "alpha_half2": a2,
                "n_items1": len(ia), "n_items2": len(ib), "n": len(complete)}

    front_back = pack(front, back)
    odd_even = pack(odd, even) if len(odd) >= 2 and len(even) >= 2 else None
    return {"front_back": front_back, "odd_even": odd_even}


def reliability_analysis(matrix, scales_config, item_output=None, rel_output=None):
    print("\n" + "=" * 60)
    print("二、信度分析（Cronbach's α，反向题已先反向计分）")
    print("=" * 60)
    if not scales_config:
        print("未提供量表配置，跳过。")
        print("配置方法：创建scales.txt，每行写 量表名=题1,题2,题3；反向题加(R)")
        return []

    results = []
    all_item_rows = []
    for scale_name, conf in scales_config.items():
        items = conf["items"]
        reverse = conf.get("reverse", {})
        likert = conf.get("likert", 5)
        available = [it for it in items if it in matrix]
        missing_items = [it for it in items if it not in matrix]
        if missing_items:
            print(f"⚠ {scale_name}：以下题目在数据中找不到：{missing_items}")
        if len(available) < 2:
            print(f"✗ {scale_name}：可用题目不足2个，无法计算α")
            continue
        # 关键：反向计分后的题目数据
        items_data = recoded_item_series(matrix, conf)
        alpha = cronbach_alpha(items_data)

        kk = len(available)
        ncol = len(items_data[0]) if items_data else 0
        rev_names = [it for it in available if reverse.get(it)]
        rev_tip = f"，反向题{len(rev_names)}道已按{likert}点反转" if rev_names else ""
        if alpha is not None:
            rating = "优秀" if alpha >= 0.9 else "良好" if alpha >= 0.8 else "可接受" if alpha >= 0.7 else "偏低，需检查"
            print(f"\n{scale_name}（{kk}题{rev_tip}）：α = {alpha:.3f}  [{rating}]")
            print("    题项分析（CITC校正项总相关建议≥.40；删题后α不应高于总α）：")
            min_citc = None
            for idx, it in enumerate(available):
                rest_data = [items_data[j] for j in range(kk) if j != idx]
                a_del = cronbach_alpha(rest_data)
                rest_total = []
                for r in range(ncol):
                    vals = [items_data[j][r] for j in range(kk) if j != idx]
                    rest_total.append(sum(vals) if all(v is not None for v in vals) else None)
                citc, _ = pearson_r(items_data[idx], rest_total)
                flags = []
                if citc is not None and citc < .4:
                    flags.append("CITC<.40偏低")
                if a_del is not None and a_del > alpha + .02:
                    flags.append("删题后α升高")
                if citc is not None and (min_citc is None or citc < min_citc):
                    min_citc = citc
                rtag = "(反向)" if reverse.get(it) else ""
                citc_txt = f"{citc:.3f}" if citc is not None else "NA"
                a_txt = f"{a_del:.3f}" if a_del is not None else "NA"
                mark = "；".join(flags)
                tail = f"  ← {mark}，结合理论检查该题" if mark else ""
                print(f"    {it}{rtag}：CITC={citc_txt}，删题后α={a_txt}{tail}")
                all_item_rows.append({
                    "量表": scale_name, "题项": it + rtag,
                    "CITC校正项总相关": round(citc, 3) if citc is not None else "",
                    "删题后alpha": round(a_del, 3) if a_del is not None else "",
                    "量表alpha": round(alpha, 3), "提示": mark})
            sh = split_half(items_data)
            sb_val = gutt_val = half_a = ""
            if sh and sh.get("front_back"):
                fb = sh["front_back"]
                sb_val = round(fb["sb"], 3)
                gutt_val = round(fb["guttman_lambda4"], 3) if fb["guttman_lambda4"] is not None else ""
                a1 = f"{fb['alpha_half1']:.3f}" if fb["alpha_half1"] is not None else "NA"
                a2 = f"{fb['alpha_half2']:.3f}" if fb["alpha_half2"] is not None else "NA"
                half_a = f"{a1}/{a2}"
                print(f"    分半信度（前后半，SPSS口径，{fb['n_items1']}+{fb['n_items2']}题）："
                      f"两半α={a1}/{a2}，两半相关r={fb['r']:.3f}，"
                      f"Spearman-Brown={fb['sb']:.3f}，Guttman λ4={fb['guttman_lambda4']:.3f}")
                if kk % 2 == 1 and sh.get("odd_even"):
                    oe = sh["odd_even"]
                    print(f"      （题数为奇数，另报奇偶分半以保证两半等长："
                          f"r={oe['r']:.3f}，Spearman-Brown={oe['sb']:.3f}，Guttman λ4={oe['guttman_lambda4']:.3f}）")
                if fb["sb"] < .7:
                    print("      ⚠ Spearman-Brown 分半信度<.70，建议结合α与题项分析检查题目同质性")
            results.append({"量表": scale_name, "题数": kk,
                            "Cronbach_alpha": round(alpha, 3),
                            "最低CITC": round(min_citc, 3) if min_citc is not None else "",
                            "分半SpearmanBrown": sb_val, "分半Guttmanλ4": gutt_val,
                            "两半alpha": half_a,
                            "评价": rating})
    if item_output and all_item_rows:
        with open(item_output, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["量表", "题项", "CITC校正项总相关",
                                              "删题后alpha", "量表alpha", "提示"])
            w.writeheader()
            w.writerows(all_item_rows)
        print(f"\n题项分析表（CITC/删题α）已导出：{item_output}")
    if rel_output and results:
        with open(rel_output, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["量表", "题数", "Cronbach_alpha",
                                              "最低CITC", "两半alpha",
                                              "分半SpearmanBrown", "分半Guttmanλ4", "评价"])
            w.writeheader()
            w.writerows(results)
        print(f"量表信度汇总（α/分半Spearman-Brown/Guttman λ4）已导出：{rel_output}")
    return results


def export_scale_dataset(src_path, headers, data, score_matrix, scales):
    """导出含量表总分/均分的分析数据集（保留原始所有列），供JASP/SPSS/PROCESS使用。"""
    out_path = src_path.with_name(src_path.stem + "_量表总分.csv")
    new_cols = []
    for name in scales:
        new_cols += [f"{name}总分", f"{name}均分"]
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers + new_cols)
        for i, row in enumerate(data):
            extra = []
            for c in new_cols:
                v = score_matrix[c][i]
                extra.append("" if v is None else v)
            w.writerow(row + extra)
    return out_path
