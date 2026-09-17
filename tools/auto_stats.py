#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化统计分析工具（心理学问卷研究）
功能：数据画像、描述统计、Cronbach's α信度、Pearson相关矩阵、线性回归
输出：控制台结果 + CSV三线表
特点：纯Python标准库实现，无需安装numpy/scipy/pandas

用法：
  python auto_stats.py data.csv                          # 全自动分析所有数值列
  python auto_stats.py data.csv --scales scales.txt      # 按量表分组算信度
  python auto_stats.py data.csv --profile                # 只看数据画像
  python auto_stats.py data.csv --output 结果.csv

量表配置文件 scales.txt 格式（每行：量表名=列1,列2,列3）：
  AI情感依赖=Q1,Q2,Q3,Q4,Q5
  孤独感=Q6,Q7,Q8,Q9,Q10,Q11

进阶（反向题与量表点数）：
  - 题目后加 (R) 或 * 表示反向题，算α和总分前会自动反向计分（5点：6-原值）
  - 量表名后用 :点数 指定是几点量表（默认5点），反向计分=点数+1-原值
  示例：
  孤独感:5=ULS1,ULS2(R),ULS3,ULS4(R),ULS5
  生活满意度:7=LS1,LS2*,LS3

提供 --scales 时会：
  1) 对反向题计分后再算 Cronbach's α（否则含反向题的α是错的）
  2) 自动计算每个量表的总分/均分，导出“_量表总分.csv”（供JASP/SPSS/PROCESS直接用）
  3) 描述统计、相关、回归在“量表总分”层面进行（论文表1表2用这个）
"""

from pathlib import Path
import argparse
import os
import sys

# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 把本脚本所在目录加入 sys.path，确保 stats 包可导入。
# 直接 `python tools/auto_stats.py` 时 sys.path[0] 已是该目录，但通过
# runpy.run_path（tests/test_graceful_degradation.py 的缺库阻断 wrapper 就是这么跑的）
# 或从别处导入时不会自动加入，必须显式声明，否则 ModuleNotFoundError: stats。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============ 拆分后的实现模块（详见 tools/stats/__init__.py）============
from stats.compare import chi_square_analysis, group_difference_analysis
from stats.dataio import numeric_columns, parse_scales, read_data, resolve_col, to_float_matrix
from stats.desc import data_profile, descriptive, export_three_line_table, frequency_analysis
from stats.efa import harman_test, validity_analysis
from stats.plots import _plot_corr_heatmap
from stats.regress import correlation_matrix, linear_regression, mediation_analysis, moderation_analysis, partial_correlation_analysis
from stats.reliability import build_scale_scores, export_scale_dataset, reliability_analysis

# ============ 主程序 ============

def main():
    parser = argparse.ArgumentParser(description="自动化统计分析工具（心理学问卷）")
    parser.add_argument("data", help="CSV数据文件")
    parser.add_argument("--scales", help="量表配置文件（算信度用）")
    parser.add_argument("--y", help="回归/中介因变量列名（可传量表名）")
    parser.add_argument("--x", help="回归自变量列名，逗号分隔（中介时只取第一个作X）")
    parser.add_argument("--mediators", help="中介变量，逗号分隔；1个=模型4简单中介，2个=模型6链式中介")
    parser.add_argument("--moderator", help="调节变量W（配合--x X --y Y做PROCESS模型1：中心化交互项+±1SD简单斜率）")
    parser.add_argument("--nonparametric", action="store_true",
                        help="人口学差异改用非参数检验（2组Mann-Whitney U、3+组Kruskal-Wallis H），用于因变量明显偏态/有序等级")
    parser.add_argument("--spearman", action="store_true",
                        help="相关分析改用 Spearman 秩相关（偏态/有序等级时）")
    parser.add_argument("--partial", help="偏相关：控制变量列名，逗号分隔（如 性别,年级 或 孤独感），输出控制后的净相关矩阵与_偏相关.csv")
    parser.add_argument("--boot", type=int, default=5000, help="Bootstrap次数（默认5000）")
    parser.add_argument("--seed", type=int, default=20260917, help="Bootstrap随机种子（默认固定，可复现）")
    parser.add_argument("--profile", action="store_true", help="只输出数据画像")
    parser.add_argument("--efa", nargs="*", default=None,
                        help="完整探索性因子分析：不跟量表名=对全部量表；也可跟量表名（空格或逗号分隔）")
    parser.add_argument("--pa-rep", type=int, default=500,
                        help="平行分析随机模拟次数（默认500，越大越稳但越慢；0=关闭平行分析）")
    parser.add_argument("--output", "-o", help="三线表输出路径")
    args = parser.parse_args()

    path = Path(args.data)
    if not path.exists():
        print(f"错误：文件不存在 {args.data}")
        sys.exit(1)

    print("=" * 60)
    print("自动化统计分析工具（心理学问卷研究）")
    print("=" * 60)

    headers, data = read_data(str(path))
    matrix = to_float_matrix(headers, data)
    num_cols = numeric_columns(matrix, headers)

    data_profile(headers, data, matrix, num_cols)
    if args.profile:
        return

    scales = parse_scales(args.scales) if args.scales else {}

    # 人口学/分类变量频数（独立于量表，两个分支都做）
    freq_out = str(path.with_name(path.stem + "_频数表.csv"))
    frequency_analysis(headers, data, matrix, scales, output=freq_out)

    # 完整EFA：--efa（全部）或 --efa 量表A 量表B / --efa 量表A,量表B
    efa_names = None
    if args.efa is not None:
        if len(args.efa) == 0:
            efa_names = "__ALL__"
        else:
            efa_names = set()
            for tok in args.efa:
                for sub in tok.split(","):
                    if sub.strip():
                        efa_names.add(sub.strip())
    efa_out = str(path.with_name(path.stem + "_因子分析.csv")) if efa_names else None
    item_out = str(path.with_name(path.stem + "_题项分析.csv"))
    rel_out = str(path.with_name(path.stem + "_信度分析.csv"))

    # 有量表配置：反向计分→信度→量表总分→在总分层面做描述/相关/回归
    if scales:
        rel = reliability_analysis(matrix, scales, item_output=item_out,
                                   rel_output=rel_out)
        validity_analysis(matrix, scales, efa_names=efa_names,
                          efa_output=efa_out, pa_rep=args.pa_rep)
        harman_test(matrix, scales)
        score_matrix, _ = build_scale_scores(matrix, scales)
        scale_total_cols = [f"{name}总分" for name in scales]
        dataset = export_scale_dataset(path, headers, data, score_matrix, scales)
        print(f"\n含量表总分的分析数据集已导出：{dataset}")
        print("  （JASP/SPSS做中介、PROCESS时直接打开这个文件，用各量表“总分”列）")

        print("\n" + "=" * 60)
        print("五、描述统计与相关分析（量表总分层面）")
        print("=" * 60)
        desc = descriptive(score_matrix, scale_total_cols)
        corr = correlation_matrix(score_matrix, scale_total_cols,
                                  method=("spearman" if args.spearman else "pearson"))
        # 相关矩阵下三角热图（对角线 α），matplotlib 缺失时静默跳过
        heat_png = str(path.with_name(path.stem + "_相关热图.png"))
        _alpha_for_heat = {f"{r['量表']}总分": r.get("Cronbach_alpha")
                          for r in rel if r.get("Cronbach_alpha") is not None}
        if _plot_corr_heatmap(score_matrix, scale_total_cols, heat_png,
                              method=("spearman" if args.spearman else "pearson"),
                              alpha_map=_alpha_for_heat):
            print(f"相关矩阵热图已导出：{heat_png}")
        else:
            print("（未安装 matplotlib，跳过相关热图；数值相关矩阵见上表，可用 JASP 出图）")
        if args.spearman:
            print("  （本节为 Spearman 秩相关；M/SD/相关/α 整合三线表仍报 Pearson，二者可并列于附录）")

        if args.y and args.x:
            y_col = resolve_col(args.y, scales, score_matrix)
            x_cols = [resolve_col(c, scales, score_matrix) for c in args.x.split(",")]
            print("\n" + "=" * 60)
            print("六、回归分析（量表总分层面）")
            print("=" * 60)
            linear_regression(score_matrix, x_cols, y_col)
        active_matrix = score_matrix
        active_cols = scale_total_cols
        diff_suffix = "_差异分析_非参数.csv" if args.nonparametric else "_差异分析.csv"
        diff_out = str(path.with_name(path.stem + diff_suffix))
        group_difference_analysis(headers, data, matrix, scales, score_matrix,
                                  scale_total_cols, output=diff_out,
                                  nonparametric=args.nonparametric)
        if args.partial:
            pout = str(path.with_name(path.stem + "_偏相关.csv"))
            partial_correlation_analysis(score_matrix, scale_total_cols,
                                         args.partial.split(","), scales=scales,
                                         extra_matrix=matrix, output=pout)
        chi_out = str(path.with_name(path.stem + "_卡方检验.csv"))
        chi_square_analysis(headers, data, matrix, scales, output=chi_out)
    else:
        # 无量表配置：题目级全量分析（降级模式，建议提供 --scales）
        print("\n提示：提供 --scales 量表配置后，将自动反向计分、算信度效度和量表总分。")
        print("\n" + "=" * 60)
        print("二、描述统计与相关分析（题目级）")
        print("=" * 60)
        desc = descriptive(matrix, num_cols)
        corr = correlation_matrix(matrix, num_cols)
        if args.y and args.x:
            x_cols = [c.strip() for c in args.x.split(",")]
            print("\n" + "=" * 60)
            print("三、回归分析")
            print("=" * 60)
            linear_regression(matrix, x_cols, args.y)
        active_matrix = matrix
        active_cols = num_cols

    alpha_map = None
    if scales:
        alpha_map = {f"{r['量表']}总分": r.get("Cronbach_alpha")
                     for r in rel if r.get("Cronbach_alpha") is not None}
    output = args.output or str(path.with_name(path.stem + "_统计结果.csv"))
    export_three_line_table(desc, corr, output, matrix=active_matrix,
                            score_cols=active_cols, alpha_map=alpha_map)

    # 中介分析（模型4/6，Bootstrap）
    if args.mediators and args.y and args.x:
        x_first = resolve_col(args.x.split(",")[0], scales, active_matrix)
        y_col = resolve_col(args.y, scales, active_matrix)
        m_cols = [resolve_col(c, scales, active_matrix) for c in args.mediators.split(",")]
        if len(m_cols) > 2:
            print("\n⚠ 链式中介最多支持2个中介变量（模型6），已取前两个。")
            m_cols = m_cols[:2]
        med_out = str(path.with_name(path.stem + "_中介效应.csv"))
        mediation_analysis(active_matrix, x_first, m_cols, y_col,
                           reps=args.boot, seed=args.seed, output=med_out)

    # 调节分析（PROCESS模型1：X、W中心化+交互项+±1SD简单斜率）
    if args.moderator and args.y and args.x:
        x_first = resolve_col(args.x.split(",")[0], scales, active_matrix)
        w_col = resolve_col(args.moderator, scales, active_matrix)
        y_col = resolve_col(args.y, scales, active_matrix)
        mod_out = str(path.with_name(path.stem + "_调节效应.csv"))
        moderation_analysis(active_matrix, x_first, w_col, y_col,
                            reps=args.boot, seed=args.seed, output=mod_out)

    print("\n" + "=" * 60)
    print("分析完成。提示：")
    print("- 已用 --mediators 自动做Bootstrap中介；正式结果建议JASP/SPSS PROCESS复核")
    print("- 反向题已按scales.txt的(R)标记处理；请核对反向题是否标对")
    print("- 结果需人工核对，p值为近似计算，精确值以SPSS/JASP为准")


if __name__ == "__main__":
    main()
