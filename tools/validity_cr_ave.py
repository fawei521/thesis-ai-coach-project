#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚合效度（收敛效度）与区分效度计算工具（心理学问卷 / CFA-SEM）

用途：
  验证性因子分析（AMOS / Mplus / JASP / lavaan / SmartPLS）给出【标准化因子载荷】后，
  用它计算论文"效度分析"必须报告的三个量，并做 Fornell-Larcker 区分效度判定：
    - CR（Composite Reliability，组合信度）
    - AVE（Average Variance Extracted，平均方差抽取量）
    - √AVE（AVE 的平方根，用于区分效度对照）
  再结合"因子间相关系数"，输出 Fornell-Larcker 区分效度矩阵（对角 √AVE、其余为相关 r）。

公式（标准化载荷 λ，测量误差 θ=1-λ²）：
    CR  = (Σλ)² / [ (Σλ)² + Σ(1-λ²) ]
    AVE = Σλ² / n
    区分效度（Fornell & Larcker, 1981）：每个因子的 √AVE 应大于它与其它任何因子相关的 |r|。

判定口径（方法学界通行，写进结果时建议同时给原始值）：
    CR  ≥ .70 良好；.60–.70 探索性研究可接受（Bagozzi & Yi, 1988；Hair 等）；<.60 偏低。
    AVE ≥ .50 严格达标；.36–.50 临界（若 CR 良好，Fornell & Larcker 1981 认为收敛效度尚可，需在文中说明）；<.36 不足。
    区分效度：√AVE > 该因子与其它因子的 |r| 即成立；否则提示两因子区分不足。
    更现代的区分效度指标是 HTMT（Henseler 等, 2015，通常 <.85 保守 / <.90），
    更现代的区分效度指标是 HTMT（Henseler 等, 2015，通常 <.85 保守 / <.90）：用本工具的
    --htmt 模式可直接由原始问卷数据（配合 scales.txt）逐对计算并给 Bootstrap 95%CI（上限<1）。

特点：纯 Python 标准库；确定性计算；只做由"真实 CFA 输出"出发的换算，不碰原始问卷数据。

两种喂数方式（可混用）：
  1) 命令行直接给（适合题项少、菜单引导）：
     python tools\\validity_cr_ave.py --factor "学习投入=0.72,0.68,0.74,0.70" ^
                                       --factor "学业倦怠=0.60,0.65,0.58,0.62" ^
                                       --corr "学习投入,学业倦怠,0.45"
  2) 给 CSV（适合题项多）：
     - 载荷表 --loadings-csv load.csv：表头需含 因子、题项、载荷 三列（factor/item/loading 亦可），
       每行一道题，如： 因子,题项,载荷 / 学习投入,Q1,0.72
     - 因子相关阵 --corr-csv corr.csv：第一行是因子名（首格留空或写"因子"），
       其后每行 因子名,r1,r2,...，给一个对称相关矩阵（可用下三角或全矩阵，缺的按对称补）。
  可选 --csv-out 结果.csv：把每因子 CR/AVE/√AVE 与判定另存一份（默认文件名后缀 _聚合区分效度.csv）。

红线：载荷必须来自你自己的真实 CFA/测量模型输出，不得为了让 AVE≥.5、√AVE>r 而手改载荷；
不达标就如实报告并按方法学处理（删题/合并因子/改用 HTMT 说明），本工具只帮你算和对照。
"""

import argparse
import csv
import io
import math
import os
import sys
import random

# 让本脚本在项目根目录被调用时也能导入 stats 子包（与 item_analysis.py 同款处理）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats.dataio import parse_scales, read_data, recoded_item_series, to_float_matrix  # noqa: E402

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与 auto_stats.py / effect_size.py 同款）---
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_CSV_SUFFIX = "_聚合区分效度.csv"


# --------------------------- 纯计算函数 ---------------------------
def cr_ave(loadings):
    """由一个因子的标准化载荷列表返回 n/Σλ/Σλ²/CR/AVE/√AVE。loadings 为非零 float 列表。"""
    n = len(loadings)
    if n == 0:
        raise ValueError("该因子没有任何载荷")
    sum_l = sum(loadings)
    sum_l2 = sum(x * x for x in loadings)
    sum_err = n - sum_l2                      # Σ(1-λ²) = n - Σλ²
    denom = sum_l * sum_l + sum_err
    cr = (sum_l * sum_l) / denom if denom > 0 else float("nan")
    ave = sum_l2 / n
    return {"n": n, "sum_l": sum_l, "sum_l2": sum_l2,
            "cr": cr, "ave": ave, "sqrt_ave": math.sqrt(ave) if ave >= 0 else float("nan")}


def cr_verdict(cr):
    if cr >= .70:
        return "良好(≥.70)"
    if cr >= .60:
        return "探索性可接受(.60–.70)"
    return "偏低(<.60)"


def ave_verdict(ave):
    if ave >= .50:
        return "严格达标(≥.50)"
    if ave >= .36:
        return "临界(.36–.50，CR良好时可接受)"
    return "不足(<.36)"


def fornell_violations(names, sqrt_ave_by_name, corr):
    """返回区分效度问题清单。corr 为 {(a,b): r}（无序对）。每个因子 √AVE 须 > 与他人的 |r|。"""
    issues = []
    for (a, b), r in corr.items():
        if a not in sqrt_ave_by_name or b not in sqrt_ave_by_name:
            continue
        ar = abs(r)
        if ar >= sqrt_ave_by_name[a]:
            issues.append((a, b, r, sqrt_ave_by_name[a], a))
        if ar >= sqrt_ave_by_name[b]:
            issues.append((b, a, r, sqrt_ave_by_name[b], b))
    return issues


# --------------------------- 输入解析 ---------------------------
def _read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_factor_spec(spec):
    """'名称=0.72,0.68,...' -> (名称, [载荷...])。"""
    if "=" not in spec:
        raise ValueError(f"因子参数格式应为 名称=载荷1,载荷2,...：{spec}")
    name, vals = spec.split("=", 1)
    name = name.strip()
    loadings = []
    for v in vals.replace("，", ",").split(","):
        v = v.strip()
        if v:
            loadings.append(float(v))
    if not name:
        raise ValueError("因子名称为空")
    return name, loadings


def parse_corr_spec(spec):
    """'A,B,r' -> (A, B, r)。"""
    parts = [p.strip() for p in spec.replace("，", ",").split(",")]
    if len(parts) != 3:
        raise ValueError(f"相关参数格式应为 因子A,因子B,相关系数：{spec}")
    a, b, r = parts[0], parts[1], float(parts[2])
    return a, b, r


def load_loadings_csv(path):
    """读载荷表，返回 {因子名: [载荷...]}（按出现顺序）。表头识别 因子/factor、题项/item、载荷/loading。"""
    text = _read_text(path)
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        raise ValueError(f"载荷表为空：{path}")
    header = [c.strip().lower() for c in rows[0]]

    def col(keys):
        for i, h in enumerate(header):
            if any(k in h for k in keys):
                return i
        return None

    cf = col(["因子", "维度", "构念", "factor", "construct", "latent"])
    cl = col(["载荷", "loading", "λ", "标准化"])
    if cf is None or cl is None:
        raise ValueError("载荷表需含 因子 与 载荷 两列（factor/loading 亦可）：%s" % path)
    groups = {}
    order = []
    for r in rows[1:]:
        if len(r) <= max(cf, cl):
            continue
        name = r[cf].strip()
        try:
            val = float(r[cl].strip())
        except ValueError:
            continue
        if not name:
            continue
        if name not in groups:
            groups[name] = []
            order.append(name)
        groups[name].append(val)
    return {k: groups[k] for k in order}


def load_corr_csv(path):
    """读因子相关方阵，返回 (名称顺序, {(a,b): r})。首行首格为角，其余为因子名。"""
    text = _read_text(path)
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise ValueError(f"相关阵为空：{path}")
    names = [c.strip() for c in rows[0][1:]]
    corr = {}
    label_rows = {}
    for r in rows[1:]:
        label = r[0].strip()
        label_rows[label] = [c.strip() for c in r[1:]]
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i == j:
                continue
            val = None
            if a in label_rows and j < len(label_rows[a]) and label_rows[a][j]:
                val = label_rows[a][j]
            elif b in label_rows and i < len(label_rows[b]) and label_rows[b][i]:
                val = label_rows[b][i]   # 对称补全
            if val is not None:
                try:
                    corr[tuple(sorted((a, b)))] = float(val)
                except ValueError:
                    pass
    return names, corr


# --------------------------- 校验 ---------------------------
def validate_loadings(factors):
    for name, vals in factors.items():
        if len(vals) < 1:
            raise ValueError(f"因子「{name}」没有载荷")
        for x in vals:
            if not (0.0 < abs(x) < 1.0):
                raise ValueError(
                    f"因子「{name}」出现标准化载荷 {x}，应在 (0,1)（标准化载荷绝对值不可能≥1；请检查是否误用了非标准化载荷）")
        neg = [x for x in vals if x < 0]
        if neg:
            print(f"⚠ 因子「{name}」出现 {len(neg)} 个负载荷（如 {neg[0]:.3f}）。CR 公式默认各题载荷同向；"
                  f"负载荷通常意味着反向题未先反向计分（或为错误的解），请在 CFA 前对反向题重编码后重估，否则 CR 会被低估。")
        low = [x for x in vals if abs(x) < .50]
        if low:
            print(f"⚠ 因子「{name}」有 {len(low)} 道题 |载荷|<.50（题项信度 λ²<.25），"
                  f"建议结合 CFA 修正指数与题项分析考虑删题，勿静默保留。")


def merge_factors(*dicts):
    out = {}
    for d in dicts:
        for k, v in d.items():
            out.setdefault(k, []).extend(v)
    return out


# --------------------------- 报告 ---------------------------
def _header(title):
    print("=" * 66)
    print(title)
    print("=" * 66)


def report(factors, corr, csv_out=None):
    _header("聚合效度：组合信度 CR / 平均方差抽取 AVE")
    names = list(factors.keys())
    stats = {}
    header = f"{'因子':<12}{'题数':>4}{'CR':>9}{'AVE':>9}{'√AVE':>9}   CR判定 / AVE判定"
    print(header)
    print("-" * 66)
    for name in names:
        st = cr_ave(factors[name])
        stats[name] = st
        print(f"{name:<12}{st['n']:>4}{st['cr']:>9.3f}{st['ave']:>9.3f}{st['sqrt_ave']:>9.3f}"
              f"   {cr_verdict(st['cr'])} / {ave_verdict(st['ave'])}")
    print("-" * 66)
    weak_cr = [n for n in names if stats[n]["cr"] < .60]
    weak_ave = [n for n in names if stats[n]["ave"] < .36]
    if not weak_cr and not weak_ave:
        print("✔ 各因子 CR 与 AVE 整体达到通行门槛（临界值见上表标注）。")
    else:
        if weak_cr:
            print(f"✗ CR 偏低（<.60）：{('、'.join(weak_cr))}，需增删题项或重构因子。")
        if weak_ave:
            print(f"✗ AVE 不足（<.36）：{('、'.join(weak_ave))}，收敛效度存疑，需处理后重估。")

    # Fornell-Larcker 区分效度
    print()
    _header("区分效度：Fornell-Larcker 矩阵（对角=√AVE，其余=因子间相关 r）")
    sqrt_map = {n: stats[n]["sqrt_ave"] for n in names}
    short = {n: (n if len(n) <= 6 else n[:6] + "…") for n in names}
    width = 9
    print(" " * 10 + "".join(f"{short[n]:>{width}}" for n in names))
    for a in names:
        cells = ""
        for b in names:
            if a == b:
                cells += f"{sqrt_map[a]:>{width}.3f}"
            else:
                r = corr.get(tuple(sorted((a, b))))
                cells += (f"{r:>{width}.3f}" if r is not None else f"{'-':>{width}}")
        print(f"{short[a]:<10}{cells}")
    print("-" * 66)
    missing_pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]
                     if tuple(sorted((a, b))) not in corr]
    issues = fornell_violations(names, sqrt_map, corr)
    if not corr:
        print("ℹ 未提供因子间相关（用 --corr 或 --corr-csv），本次只算聚合效度，未做区分效度判定。")
    else:
        if not issues:
            print("✔ Fornell-Larcker 判定：各因子 √AVE 均大于它与其它因子的 |r|，区分效度成立。")
        else:
            print("✗ 区分效度存疑（√AVE 未大于对应 |r|）：")
            for owner, other, r, sa, _ in issues:
                print(f"   - 「{owner}」√AVE={sa:.3f} 未大于 与「{other}」的 |r|={abs(r):.3f}")
            print("  建议：检查两因子是否过度重叠（合并/删题/改模型），并补充报告 HTMT。")
        if missing_pairs:
            print("⚠ 以下因子对缺少相关系数，未参与判定："
                  + "；".join(f"{a}↔{b}" for a, b in missing_pairs))

    print()
    print("说明：CR/AVE 基于标准化载荷；AVE≥.50 为严格门槛，.36–.50 且 CR 良好时 Fornell &")
    print("Larcker(1981) 认为可接受但需说明；区分效度建议同时报告更现代的 HTMT(<.85/.90)。")
    print("红线：载荷须来自真实 CFA 输出，不得为达标手改；不达标如实报告并做模型处理。")

    if csv_out:
        write_csv(csv_out, names, stats, corr, sqrt_map, issues)


def write_csv(path, names, stats, corr, sqrt_map, issues):
    # 给的是目录（含尚不存在的目录）→ 用默认文件名；给 .csv 文件路径则直接用
    if not path.lower().endswith(".csv"):
        os.makedirs(path, exist_ok=True)
        path = os.path.join(path, DEFAULT_CSV_SUFFIX)
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    bad_owners = {owner for owner, *_ in issues}
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["因子", "题项数", "CR组合信度", "AVE平均方差抽取", "√AVE",
                    "CR判定", "AVE判定", "Fornell区分效度"])
        for n in names:
            st = stats[n]
            disc = "存疑(√AVE≤某|r|)" if n in bad_owners else ("成立" if corr else "未判定(缺相关)")
            w.writerow([n, st["n"], f"{st['cr']:.4f}", f"{st['ave']:.4f}", f"{st['sqrt_ave']:.4f}",
                        cr_verdict(st["cr"]), ave_verdict(st["ave"]), disc])
    print(f"\n已另存：{path}")


# --------------------------- HTMT（由原始题项数据算区分效度）---------------------------
HTMT_CSV_SUFFIX = "_HTMT区分效度.csv"


def _htmt_full_item_matrix(matrix, scales):
    """汇集所有量表题目（反向计分后），取全部题项完整作答的样本。
    返回 (量表名顺序, {量表: [题项名]}, 行数据[行][题序], 题项顺序)；样本不足返回 None。"""
    names = list(scales.keys())
    items_by_scale, all_items = {}, []
    for name in names:
        conf = scales[name]
        avail = [it for it in conf["items"] if it in matrix]
        if len(avail) < 2:
            print(f"⚠ {name}：可用题目不足 2 题，不参与 HTMT 计算。")
            continue
        items_by_scale[name] = avail
        all_items.extend(avail)
    if len(items_by_scale) < 2:
        return None
    n_rows = len(matrix[all_items[0]])
    complete = [i for i in range(n_rows)
                if all((matrix[it][i] is not None) for it in all_items)]
    if len(complete) < 10:
        return None
    # 反向计分后的原始取值（保留 Likert 量纲，相关分析对线性变换不敏感）
    recoded = {}
    for name in items_by_scale:
        series = recoded_item_series(matrix, scales[name])
        for j, it in enumerate([x for x in scales[name]["items"] if x in matrix]):
            recoded[it] = series[j]
    rows = [[recoded[it][i] for it in all_items] for i in complete]
    return list(items_by_scale.keys()), items_by_scale, rows, all_items, len(complete)


def _corr_matrix_from_rows(rows, items_index):
    """对 行×题 的原始数据做 z 标准化并求 Pearson 相关阵（题序同 items_index）。"""
    n = len(rows)
    p = len(items_index)
    cols = [[rows[i][j] for i in range(n)] for j in range(p)]
    Z = []
    for col in cols:
        m = sum(col) / n
        sd = math.sqrt(sum((v - m) ** 2 for v in col) / (n - 1)) if n > 1 else 0.0
        Z.append([(v - m) / sd if sd > 0 else 0.0 for v in col])
    R = [[0.0] * p for _ in range(p)]
    for a in range(p):
        R[a][a] = 1.0
        for b in range(a + 1, p):
            r = sum(Z[a][i] * Z[b][i] for i in range(n)) / (n - 1) if n > 1 else 0.0
            R[a][b] = r
            R[b][a] = r
    return R


def _htmt_from_corr(R, index_map, items_a, items_b):
    """由题项相关阵算一对构念的 HTMT（Henseler 等 2015，块内/跨块均取 |r| 的均值）。
    返回 (htmt, 跨块均值, 块内A均值, 块内B均值, 块内A有符号均值, 块内B有符号均值)。"""
    ia = [index_map[it] for it in items_a]
    ib = [index_map[it] for it in items_b]

    def within(idx):
        vals_abs, vals_signed = [], []
        for u in range(len(idx)):
            for v in range(u + 1, len(idx)):
                rr = R[idx[u]][idx[v]]
                vals_abs.append(abs(rr))
                vals_signed.append(rr)
        return (sum(vals_abs) / len(vals_abs) if vals_abs else 0.0,
                sum(vals_signed) / len(vals_signed) if vals_signed else 0.0)

    cross = []
    for u in ia:
        for v in ib:
            cross.append(abs(R[u][v]))
    cross_mean = sum(cross) / len(cross)
    wa_abs, wa_sign = within(ia)
    wb_abs, wb_sign = within(ib)
    denom = math.sqrt(wa_abs * wb_abs)
    htmt = cross_mean / denom if denom > 0 else None
    return htmt, cross_mean, wa_abs, wb_abs, wa_sign, wb_sign


def _htmt_verdict(htmt, ci_hi):
    """点估计按 .85/.90 双门槛判读，Bootstrap 95%CI 上限须 <1。"""
    if htmt is None:
        return "无法计算（块内相关非正，检查反向题）", "—"
    if htmt < .85:
        point = "成立（<.85 保守标准）"
    elif htmt < .90:
        point = "临界（.85–.90，构念相近时可接受）"
    else:
        point = "不足（≥.90，两构念可能重叠）"
    if ci_hi is None:
        ci_verdict = "未做Bootstrap"
    elif ci_hi < 1.0:
        ci_verdict = f"CI上限{ci_hi:.3f}<1，通过"
    else:
        ci_verdict = f"CI上限{ci_hi:.3f}≥1，不通过（不能拒绝两构念相同）"
    return point, ci_verdict


def htmt_report(matrix, scales, data_stem, boot=2000, seed=20260918, csv_out=None,
                only_scales=None):
    """由原始问卷数据计算全部量表对的 HTMT 及 Bootstrap 95%CI 并导出。"""
    if only_scales:
        wanted = {s.strip() for s in only_scales.replace("，", ",").split(",") if s.strip()}
        missing = wanted - set(scales)
        if missing:
            raise ValueError(f"--only-scales 中的量表不在配置中：{ '、'.join(sorted(missing)) }")
        scales = {k: v for k, v in scales.items() if k in wanted}
    packed = _htmt_full_item_matrix(matrix, scales)
    if packed is None:
        raise ValueError("可计算 HTMT 的量表不足 2 个，或全部题项完整作答的样本不足 10 份；"
                         "请检查 scales.txt 题项名与数据列名是否一致、先做数据清洗。")
    names, items_by_scale, rows, all_items, n = packed
    if len(names) < 2:
        raise ValueError("至少需要 2 个各含 2 题以上的量表才能计算 HTMT。")
    index_map = {it: j for j, it in enumerate(all_items)}

    print("=" * 66)
    print(f"HTMT 区分效度（Henseler, Ringle & Sarstedt, 2015）｜完整样本 N={n}")
    print("=" * 66)
    R0 = _corr_matrix_from_rows(rows, all_items)

    pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
    point = {}
    for a, b in pairs:
        htmt, cm, wa, wb, wa_s, wb_s = _htmt_from_corr(
            R0, index_map, items_by_scale[a], items_by_scale[b])
        point[(a, b)] = htmt
        if wa_s <= 0 or wb_s <= 0:
            print(f"⚠ {a} ↔ {b}：某构念块内题项平均相关≤0（A={wa_s:.3f}, B={wb_s:.3f}），"
                  "HTMT 不可解释，最常见原因是反向题未在 scales.txt 标 (R)。")

    # Bootstrap 百分位 CI（对行有放回重抽样，固定种子可复现）
    ci = {}
    if boot and boot > 0:
        print(f"Bootstrap 重抽样 {boot} 次（固定种子 {seed}，计算 95% 百分位区间）…")
        rng = random.Random(seed)
        boots = {pair: [] for pair in pairs}
        for _ in range(boot):
            idx = [rng.randrange(n) for _ in range(n)]
            resample = [rows[i] for i in idx]
            Rb = _corr_matrix_from_rows(resample, all_items)
            for pair in pairs:
                a, b = pair
                h, *_ = _htmt_from_corr(Rb, index_map, items_by_scale[a], items_by_scale[b])
                if h is not None:
                    boots[pair].append(h)
        for pair, vals in boots.items():
            if len(vals) >= 20:
                vals.sort()
                ci[pair] = (vals[int(0.025 * len(vals))], vals[min(len(vals) - 1,
                                                                     int(0.975 * len(vals)))])
            else:
                ci[pair] = (None, None)

    print("-" * 66)
    print(f"{'构念A':<11}{'构念B':<11}{'HTMT':>8}  {'95%CI':>15}  判定")
    print("-" * 66)
    out_rows = []
    n_fail = 0
    for a, b in pairs:
        h = point[(a, b)]
        lo, hi = ci.get((a, b), (None, None))
        pv, cv = _htmt_verdict(h, hi)
        if h is not None and (h >= .90 or (hi is not None and hi >= 1.0)):
            n_fail += 1
        ci_txt = "—" if lo is None else f"[{lo:.3f}, {hi:.3f}]"
        h_txt = "无法计算" if h is None else f"{h:.3f}"
        print(f"{a:<11}{b:<11}{h_txt:>8}  {ci_txt:>15}  {pv}；{cv}")
        out_rows.append({"构念A": a, "构念B": b, "完整N": n, "HTMT": f"{h:.4f}" if h is not None else "",
                         "CI下限": f"{lo:.4f}" if lo is not None else "",
                         "CI上限": f"{hi:.4f}" if hi is not None else "",
                         "点估计判定": pv, "CI判定": cv})
    print("-" * 66)
    if n_fail == 0:
        if boot and boot > 0:
            print("✔ 各构念对 HTMT 均低于 .90 且 Bootstrap 95%CI 上限<1，区分效度成立。")
        else:
            print("✔ 各构念对 HTMT 点估计均低于 .90（未做 Bootstrap，建议补算 CI，以上限<1 作推断标准）。")
    else:
        print("✗ 存在区分效度不足的构念对（HTMT≥.90 或 CI 上限≥1），")
        print("  应结合理论考虑合并构念、删改交叉题项或重构模型，并在 CFA 软件复核，不得只挑好看的报告。")
    print("判读：构念明显不同用保守门槛 .85；构念相近可用 .90；更严格的推断标准是 CI 上限<1。")
    print("说明：本工具对 Likert 题项用 Pearson 相关（预览/教学口径）；有序类别数据的正式")
    print("      HTMT（polychoric/HTMT2）请在 R lavaan/semTools 或 SmartPLS 中复核。")

    if csv_out is None:
        csv_out = data_stem + HTMT_CSV_SUFFIX
    if not csv_out.lower().endswith(".csv"):
        os.makedirs(csv_out, exist_ok=True)
        csv_out = os.path.join(csv_out, os.path.basename(data_stem) + HTMT_CSV_SUFFIX)
    d = os.path.dirname(os.path.abspath(csv_out))
    os.makedirs(d, exist_ok=True)
    with open(csv_out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["构念A", "构念B", "完整N", "HTMT",
                                          "CI下限", "CI上限", "点估计判定", "CI判定"])
        w.writeheader()
        w.writerows(out_rows)
    print(f"\n已另存：{csv_out}")
    print("红线：HTMT 只量化区分效度，不达标须如实报告并做模型处理，不得删题凑数。")


# --------------------------- CLI ---------------------------
def build_parser():
    p = argparse.ArgumentParser(
        description="聚合/区分效度工具（由标准化因子载荷算 CR、AVE、√AVE，并做 Fornell-Larcker 判定，纯标准库）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--factor", action="append", default=[],
                   help="一个因子，格式 '名称=载荷1,载荷2,...'，可重复")
    p.add_argument("--corr", action="append", default=[],
                   help="因子间相关，格式 '因子A,因子B,r'，可重复")
    p.add_argument("--loadings-csv", default=None, help="载荷表 CSV（因子,题项,载荷）")
    p.add_argument("--corr-csv", default=None, help="因子相关方阵 CSV")
    p.add_argument("--csv-out", default=None, help="把结果另存为 CSV（给目录则用默认文件名）")
    return p


def main():
    parser = build_parser()
    # HTMT 原始数据模式参数（由原始问卷数据直接算区分效度）
    parser.add_argument("--htmt", metavar="数据CSV", default=None,
                        help="HTMT 模式：原始问卷数据 CSV（配合 --scales）")
    parser.add_argument("--scales", default=None,
                        help="HTMT 模式必填：量表配置 scales.txt（反向题用 (R) 标记）")
    parser.add_argument("--boot", type=int, default=2000,
                        help="HTMT 的 Bootstrap 次数（默认 2000，0=不算 CI）")
    parser.add_argument("--seed", type=int, default=20260918,
                        help="HTMT Bootstrap 随机种子（默认固定，可复现）")
    parser.add_argument("--only-scales", dest="only_scales", default=None,
                        help="HTMT 模式只分析指定量表（逗号分隔，默认全部量表两两配对）")
    a = parser.parse_args()

    # ---- HTMT 原始数据模式：与 CR/AVE（载荷模式）互斥，单独走一条报告流程 ----
    if a.htmt:
        if not a.scales:
            raise ValueError("HTMT 模式需要 --scales scales.txt（反向题用 (R) 标记）。")
        scales_path = a.scales
        if not os.path.exists(scales_path):
            raise ValueError(f"找不到量表配置文件：{scales_path}")
        if not os.path.exists(a.htmt):
            raise ValueError(f"找不到数据文件：{a.htmt}")
        if a.boot < 0:
            raise ValueError("--boot 次数不能为负（0 表示不计算置信区间）。")
        scales = parse_scales(scales_path)
        if not scales:
            raise ValueError(f"未能从 {scales_path} 读到任何量表，请检查格式。")
        headers, data = read_data(a.htmt)
        matrix = to_float_matrix(headers, data)
        data_stem = os.path.splitext(a.htmt)[0]
        htmt_report(matrix, scales, data_stem, boot=a.boot, seed=a.seed,
                    csv_out=a.csv_out, only_scales=a.only_scales)
        return

    factors = {}
    for spec in a.factor:
        name, vals = parse_factor_spec(spec)
        factors.setdefault(name, []).extend(vals)
    if a.loadings_csv:
        factors = merge_factors(factors, load_loadings_csv(a.loadings_csv))

    corr = {}
    for spec in a.corr:
        x, y, r = parse_corr_spec(spec)
        if not -1.0 <= r <= 1.0:
            raise ValueError(f"相关系数须在 [-1,1]：{x}↔{y}={r}")
        corr[tuple(sorted((x, y)))] = r
    if a.corr_csv:
        _, file_corr = load_corr_csv(a.corr_csv)
        corr.update(file_corr)

    if not factors:
        parser.print_help()
        return
    validate_loadings(factors)
    # 相关里引用了不存在的因子，直接报错（防止静默漏判）
    known = set(factors)
    for (x, y) in corr:
        if x not in known or y not in known:
            raise ValueError(f"相关系数引用了未提供载荷的因子：{x}、{y}（请先用 --factor/--loadings-csv 给出）")
    report(factors, corr, csv_out=a.csv_out)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as e:
        print(f"✗ {e}")
        sys.exit(1)
