#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问卷数据去标识化工具（隐私保护，发给 AI / 上传 / 给外校前的一道隐私闸）
====================================================================
它解决什么：
  问卷里常有能直接认出"这是谁"的列——姓名、学号、手机号、邮箱、身份证、
  微信/QQ、IP、详细住址、出生日期（抽奖、课程学分、前后测配对、花名册合并时很常见）。
  问卷星预处理只会丢掉它认识的平台元数据列；同学自己加的姓名/手机等列会原样保留。
  本工具把这些【直接标识符】假名化或删除，并对性别/年级/专业/生源等
  【准标识符】做 k-匿名风险体检（这些列分析要用，默认保留、只提示风险）。

两条法律/方法学口径（《个人信息保护法》第七十三条）：
  · 去标识化：处理后不借助额外信息无法识别特定个人——保留"假名对照表"时属此列，仍可复原；
  · 匿名化：处理后无法识别且不能复原——删除对照表、准标识符组合也无法识别后才接近。

安全设计（与项目宪法第七条一致）：
  · 只读入原文件，绝不修改、删除原数据；结果写入【新文件】；
  · 假名编号与个人信息无关（顺序生成的 P001…，不用手机号/生日/姓名缩写派生）；
  · 假名对照表单独成文，默认生成以便前后测配对，用完应尽早单独删除（--no-key 可彻底不生成）。

用法：
  python anonymize_data.py 数据.csv                  # 自动识别并处理，输出新文件
  python anonymize_data.py 数据.csv --dry-run        # 只体检、不写任何文件
  python anonymize_data.py 数据.csv --no-key         # 不生成假名对照表（更接近匿名化）
  python anonymize_data.py 数据.csv --k 5            # 准标识符 k-匿名阈值改为 5（默认3）
  python anonymize_data.py 数据.csv --columns "手机号:mask;班级:drop;备注:keep"
      手动指定列动作：pseudo 假名化 / mask 部分打码 / drop 删除 / keep 原样保留
====================================================================
"""

import csv
import re
import sys
import argparse
from pathlib import Path
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ============ 一、列识别（表头关键词；先按表头判定，再对剩余列做内容模式识别）============

# 直接标识符——可充当"这一行是谁"的身份列（优先级从高到低，取第一个做假名化）
IDENTITY_KW = [
    "姓名", "名字", "真实姓名", "学生姓名", "name", "full name", "fullname",
]
# 直接标识符——学籍/工号类编号（本身也是编号，但在校内可直接定位到人）
CODEID_KW = [
    "学号", "学籍号", "考生号", "考号", "工号", "会员号", "借书证号",
    "student id", "studentid", "student no", "studentno", "student number",
    "staff id", "staffid", "employee id", "sid", "user id", "userid", "uid",
]
# 已经是无害编号（问卷星序号/自编号），原样保留，不再生成新编号
BENIGN_CODE_KW = [
    "序号", "编号", "被试编号", "样本编号", "问卷编号", "id", "id号", "no.", "number",
]
# 直接标识符——默认删除（分析用不到，且能直接联系/定位个人）
DROP_KW = [
    # 证件
    "身份证", "证件号", "护照", "passport", "id card", "idcard", "ssn",
    # 联系方式
    "手机", "电话", "联系方式", "联系号码", "mobile", "phone", "tel", "telephone", "cell",
    # 网络账号
    "微信", "wechat", "weixin", "qq", "whatsapp", "line", "抖音", "微博", "快手",
    "社交账号", "网络账号", "账号", "帐户", "账户", "用户名", "username", "昵称", "nickname",
    "openid", "unionid",
    # 邮箱
    "邮箱", "电子邮件", "邮件", "email", "e-mail", "mail",
    # 精确位置 / 住址
    "详细地址", "家庭住址", "住址", "宿舍", "门牌号", "门牌", "address",
    "来自ip", "ip地址", "ip", "longitude", "latitude", "经纬度", "gps", "精确定位",
    # 金融
    "银行卡", "银行账号", "卡号", "支付宝", "银行账户",
    # 精确生日 / 生物影像
    "出生日期", "生日", "出生年月", "birthday", "birth date", "date of birth", "dob",
    "照片", "头像", "手写签名", "签名",
]
# 准标识符——单独看不能认出人，组合起来可能识别；它们往往是分析变量，默认【保留】只做风险体检
QUASI_KW = [
    "性别", "gender", "sex",
    "年级", "grade",
    "年龄", "岁数", "age",
    "专业", "major",
    "学院", "院系", "college", "faculty", "department",
    "班级", "class",
    "生源", "籍贯", "省份", "省", "城市", "市", "地区", "地域", "region", "province",
    "city", "hometown", "zip", "邮编", "邮政编码",
    "民族", "ethnic",
    "政治面貌", "政治",
    "独生子女", "独生",
    "家庭经济", "经济状况", "月收入", "家庭收入", "收入", "ses", "社会经济",
    "学历", "education",
    "入学年份", "哪一届", "届别",
    "婚姻", "恋爱状况", "恋爱",
]

RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RE_MOBILE = re.compile(r"^(?:\+?86[-\s]?)?1[3-9]\d{9}$")
RE_IDCARD = re.compile(r"^\d{17}[\dXx]$")
RE_LONGDIGIT = re.compile(r"^\d{14,19}$")   # 银行卡等长数字
RE_QQDIGIT = re.compile(r"^[1-9]\d{4,11}$")  # QQ 号 5-12 位


def _norm(s):
    return (s or "").strip().lower()


def header_kind(h):
    """按表头关键词判定列类别：identity / codeid / benigncode / directdrop / quasi / normal。"""
    t = _norm(h)
    if not t:
        return "normal"
    if any(k in t for k in IDENTITY_KW):
        return "identity"
    if any(k in t for k in CODEID_KW):
        return "codeid"
    if any(k == t or k in t for k in BENIGN_CODE_KW):
        return "benigncode"
    if any(k in t for k in DROP_KW):
        return "directdrop"
    if any(k in t for k in QUASI_KW):
        return "quasi"
    return "normal"


def _nonempty(values):
    return [v for v in values if v is not None and v.strip() != ""]


def content_direct_kind(values):
    """对表头没暴露身份的列，按内容模式识别直接标识符；识别不出返回 None。
    只认真正的强模式（邮箱/手机/身份证/长数字/高唯一短数字串），Likert(1-7)、年龄等不会误伤。"""
    vals = _nonempty(values)
    if len(vals) < 3:
        return None
    def frac(pred):
        return sum(1 for v in vals if pred(_norm(v).replace(" ", "").replace("-", ""))) / len(vals)
    if frac(lambda v: bool(RE_EMAIL.match(v))) >= 0.6:
        return "邮箱（按内容识别）"
    if frac(lambda v: bool(RE_MOBILE.match(v))) >= 0.6:
        return "手机号（按内容识别）"
    if frac(lambda v: bool(RE_IDCARD.match(v))) >= 0.6:
        return "身份证号（按内容识别）"
    if frac(lambda v: bool(RE_LONGDIGIT.match(v))) >= 0.6:
        return "长数字账号/卡号（按内容识别）"
    # 高唯一的 5-12 位数字（QQ 等）：要求近乎唯一，避免把普通数值列误判
    uniq = len(set(vals)) / len(vals)
    if uniq >= 0.9 and frac(lambda v: bool(RE_QQDIGIT.match(v))) >= 0.6:
        return "疑似QQ/数字账号（按内容识别）"
    return None


# ============ 二、打码与假名化 ============

def mask_value(v, subtype=""):
    """部分打码，保留少量前后字符用于人工核对，隐去主体。"""
    s = (v or "").strip()
    if s == "":
        return ""
    t = s.replace(" ", "")
    if "手机" in subtype or RE_MOBILE.match(t) or (len(t) == 11 and t.isdigit() and t[0] == "1"):
        return t[:3] + "****" + t[-4:]
    if "邮箱" in subtype or "@" in s:
        local, _, domain = s.partition("@")
        return (local[0] if local else "") + "***@" + domain
    if "身份证" in subtype or RE_IDCARD.match(t):
        return t[:6] + "********" + t[-4:]
    if "长数字" in subtype or RE_LONGDIGIT.match(t) or (t.isdigit() and len(t) >= 8):
        return t[:2] + "*" * (len(t) - 4) + t[-2:] if len(t) > 4 else "*" * len(t)
    if "姓名" in subtype or (re.fullmatch(r"[一-龥·]{2,6}", s) and len(s) <= 6):
        return s[0] + "*" * (len(s) - 1)
    if len(s) <= 2:
        return s[0] + "*"
    return s[0] + "*" * (len(s) - 2) + s[-1]


def build_plan(headers, rows, manual):
    """生成每列处理计划：[{index,header,kind,action,reason}]，action∈pseudo/mask/drop/keep。"""
    n = len(headers)
    col_values = [[r[j] if j < len(r) else "" for r in rows] for j in range(n)]
    plan = []
    for j, h in enumerate(headers):
        kind = header_kind(h)
        if kind == "normal":
            ck = content_direct_kind(col_values[j])
            if ck:
                kind = "directdrop"
                reason = ck
            else:
                reason = ""
        else:
            reason = ""
        plan.append({"index": j, "header": h, "kind": kind, "action": None, "reason": reason})

    # 默认动作
    for c in plan:
        if c["kind"] in ("identity", "codeid"):
            c["action"] = "pseudo"
        elif c["kind"] == "directdrop":
            c["action"] = "drop"
        else:  # benigncode / quasi / normal
            c["action"] = "keep"

    # 身份列：第一个始终假名化为“编号”（对应 ai-literacy“用编号代替姓名”，
    # 即使已有“序号”也保留假名化，便于前后测按人配对）；其余身份/学号类删除，避免重复可识别列。
    pseudo_cols = [c for c in plan if c["action"] == "pseudo"]
    if pseudo_cols:
        for c in pseudo_cols[1:]:
            c["action"] = "drop"

    # 手动覆盖（--columns "列名:动作;..."）
    valid = {"pseudo", "mask", "drop", "keep"}
    name_to_col = {c["header"]: c for c in plan}
    warnings = []
    for spec in manual:
        if not spec.strip() or ":" not in spec:
            continue
        name, act = spec.split(":", 1)
        name, act = name.strip(), act.strip().lower()
        if name not in name_to_col:
            warnings.append(f"手动指定的列“{name}”未找到，已忽略")
            continue
        if act not in valid:
            warnings.append(f"列“{name}”的动作“{act}”无效（应为 pseudo/mask/drop/keep），已忽略")
            continue
        name_to_col[name]["action"] = act
        name_to_col[name]["reason"] = "手动指定"
    # 手动 pseudo 至多一个
    man_pseudo = [c for c in plan if c["action"] == "pseudo"]
    if len(man_pseudo) > 1:
        for c in man_pseudo[1:]:
            c["action"] = "drop"
            warnings.append(f"只能有一个假名化列，多余的“{c['header']}”改为删除")
    return plan, warnings


def kanon_report(headers, rows, plan, k):
    """对保留下来的准标识符列做 k-匿名体检，返回 (结论文本, 风险组数, 风险行数)。"""
    qcols = [c for c in plan if c["kind"] == "quasi" and c["action"] != "drop"]
    if not qcols:
        return "未检测到性别/年级/专业/生源等准标识符列，跳过 k-匿名体检。", 0, 0
    groups = {}
    for r in rows:
        key = tuple((r[c["index"]].strip() if c["index"] < len(r) and r[c["index"]].strip() else "缺失")
                    for c in qcols)
        groups[key] = groups.get(key, 0) + 1
    k_actual = min(groups.values()) if groups else 0
    risky = {key: cnt for key, cnt in groups.items() if cnt < k}
    risky_rows = sum(risky.values())
    labels = [c["header"] for c in qcols]
    lines = [
        f"准标识符列（{len(qcols)}个，默认保留用于分析）：{ '、'.join(labels) }",
        f"共 {len(rows)} 份问卷，按上述列组合后最小等价类 k = {k_actual}（阈值 k={k}）。",
    ]
    if not risky:
        lines.append(f"✔ 每个“{ '＋'.join(labels) }”组合都至少有 {k} 人，k-匿名体检通过。")
    else:
        lines.append(f"⚠ 有 {len(risky)} 个组合少于 {k} 人、涉及 {risky_rows} 份问卷，"
                     f"这些组合里的同学可能被“对号入座”：")
        for key, cnt in list(risky.items())[:20]:
            desc = "、".join(f"{lab}={val}" for lab, val in zip(labels, key))
            lines.append(f"    · {desc}：{cnt} 人")
        if len(risky) > 20:
            lines.append(f"    · 其余 {len(risky) - 20} 个组合见数据自查")
        lines.append("  建议（任选，分析变量能不动就不动）：合并稀有类别（如把很少的生源地合并为“其他”）、")
        lines.append("  对年龄分段、删去一个识别力过强的准标识符，或在数据管理说明中如实标注该风险。")
    lines.append("  注意：k-匿名只评估“人口学组合再识别”，挡不住掌握额外信息的定向识别，")
    lines.append("  不能替代知情同意、伦理审查与数据保管义务（见 psychology/ethics.md）。")
    return "\n".join(lines), len(risky), risky_rows


# ============ 三、读写 ============

def read_csv(filepath):
    """读取 CSV，自动兼容 UTF-8(含BOM)/GB18030/GBK；返回 (表头, 数据行)。"""
    last = None
    for enc in ("utf-8-sig", "gb18030", "gbk"):
        try:
            with open(filepath, "r", encoding=enc, newline="") as f:
                rows = list(csv.reader(f))
            if rows:
                return rows[0], rows[1:]
            return [], []
        except (UnicodeDecodeError, UnicodeError) as e:
            last = e
            continue
    raise ValueError(f"无法识别文件编码，请把 CSV 另存为 UTF-8 后重试（{last}）")


def subtype_for(c):
    if c["reason"]:
        return c["reason"]
    return c["header"]


def main():
    parser = argparse.ArgumentParser(description="问卷数据去标识化工具（隐去直接标识符＋准标识符 k-匿名体检）")
    parser.add_argument("input", help="输入 CSV 文件路径（原始数据，不会被改动）")
    parser.add_argument("--output", "-o", help="去标识化数据输出路径（默认：输入文件旁 <名>_去标识化.csv）")
    parser.add_argument("--report", help="去标识化报告输出路径（默认：<名>_去标识化报告.txt）")
    parser.add_argument("--key", help="假名对照表输出路径（默认：<名>_假名对照表.csv）")
    parser.add_argument("--no-key", action="store_true", help="不生成假名对照表（彻底不可复原，更接近匿名化）")
    parser.add_argument("--dry-run", action="store_true", help="只识别与体检，不写任何文件")
    parser.add_argument("--k", type=int, default=3, help="准标识符 k-匿名阈值，默认 3（常用 3 或 5）")
    parser.add_argument("--columns", default="",
                        help='手动指定列动作，格式 "列名:动作;列名:动作"，动作=pseudo/mask/drop/keep')
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"错误：文件不存在 {args.input}")
        sys.exit(1)
    if args.k < 1:
        print("错误：--k 必须是不小于 1 的整数（常用 3 或 5）")
        sys.exit(1)

    try:
        headers, rows = read_csv(str(in_path))
    except ValueError as e:
        print(f"错误：{e}")
        sys.exit(1)
    if not headers:
        print("错误：文件是空的，或没有表头行。")
        sys.exit(1)

    manual = [s for s in re.split(r"[;；]", args.columns) if s.strip()]
    plan, warns = build_plan(headers, rows, manual)

    out_path = Path(args.output) if args.output else in_path.with_name(in_path.stem + "_去标识化.csv")
    report_path = Path(args.report) if args.report else in_path.with_name(in_path.stem + "_去标识化报告.txt")
    key_path = Path(args.key) if args.key else in_path.with_name(in_path.stem + "_假名对照表.csv")
    try:
        if out_path.resolve() == in_path.resolve():
            print("错误：输出文件与原文件同名同路径，去标识化必须另存为新文件，以免覆盖原始数据。")
            sys.exit(1)
    except OSError:
        pass

    changed = [c for c in plan if c["action"] in ("pseudo", "mask", "drop")]
    pseudo_col = next((c for c in plan if c["action"] == "pseudo"), None)

    # ---------- 屏幕报告 ----------
    print("=" * 60)
    print("问卷数据去标识化工具")
    print("=" * 60)
    print(f"读取数据：{len(headers)} 列，{len(rows)} 行　|　k-匿名阈值 k={args.k}")
    print("-" * 60)
    kind_name = {"identity": "身份列", "codeid": "学号/工号", "benigncode": "已有编号",
                 "directdrop": "直接标识符", "quasi": "准标识符(保留)", "normal": "普通作答列"}
    action_name = {"pseudo": "假名化为编号", "mask": "部分打码", "drop": "删除", "keep": "保留"}
    for c in plan:
        if c["kind"] in ("normal", "benigncode") and c["action"] == "keep":
            continue
        label = kind_name.get(c["kind"], "")
        extra = f"（{c['reason']}）" if c["reason"] and c["reason"] != label else ""
        print(f"  [{action_name[c['action']]}] {c['header']}　← {label}{extra}")
    if not changed:
        print("  未发现姓名/学号/手机/邮箱/身份证等直接标识符列。")
    for w in warns:
        print("  ⚠ " + w)
    print("-" * 60)
    ktext, n_risky, _ = kanon_report(headers, rows, plan, args.k)
    print(ktext)

    if args.dry_run:
        print("-" * 60)
        print("--dry-run 体检模式：未写出任何文件，原数据未改动。")
        sys.exit(0)

    if not changed:
        print("-" * 60)
        print("没有需要删除/假名化/打码的列，未生成新文件；请结合上面的 k-匿名体检自行判断。")
        sys.exit(0)

    # ---------- 生成假名映射 ----------
    code_map = {}   # 原值 -> 编号
    if pseudo_col:
        src = pseudo_col["index"]
        seen = []
        for r in rows:
            v = r[src].strip() if src < len(r) else ""
            if v and v not in code_map:
                code_map[v] = f"P{len(seen) + 1:03d}"
                seen.append(v)

    # ---------- 写出去标识化数据 ----------
    out_headers, out_rows = [], []
    for c in plan:
        if c["action"] == "drop":
            continue
        if c is pseudo_col:
            out_headers.append("编号")
        else:
            out_headers.append(c["header"])
    for r in rows:
        nr = []
        for c in plan:
            if c["action"] == "drop":
                continue
            v = r[c["index"]] if c["index"] < len(r) else ""
            if c is pseudo_col:
                nr.append(code_map.get(v.strip(), ""))
            elif c["action"] == "mask":
                nr.append(mask_value(v, subtype_for(c)))
            else:
                nr.append(v)
        out_rows.append(nr)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(out_headers)
        w.writerows(out_rows)

    # ---------- 写出假名对照表（默认生成，--no-key 可关）----------
    key_written = False
    if pseudo_col and not args.no_key:
        with open(key_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["编号", f"原{pseudo_col['header']}"])
            for orig, code in code_map.items():
                w.writerow([code, orig])
        key_written = True

    # ---------- 写出去标识化报告（可放进方法/数据管理留痕）----------
    rpt = []
    rpt.append("问卷数据去标识化报告")
    rpt.append("=" * 40)
    rpt.append(f"原始文件：{in_path.name}　数据行数：{len(rows)}　k-匿名阈值：{args.k}")
    rpt.append("处理明细：")
    for c in plan:
        if c["action"] == "keep" and c["kind"] in ("normal", "benigncode"):
            continue
        tag = c["reason"] or kind_name.get(c["kind"], "")
        rpt.append(f"  · {c['header']}：{action_name[c['action']]}（{tag}）")
    rpt.append("")
    rpt.append(ktext)
    rpt.append("")
    rpt.append("隐私口径与保管要求：")
    rpt.append("  1. 本处理为《个人信息保护法》第七十三条所指“去标识化”；保留假名对照表时数据仍可复原，")
    rpt.append("     只有删除对照表、且准标识符组合也无法识别时，才接近“匿名化”。")
    if key_written:
        rpt.append(f"  2. 假名对照表（{key_path.name}）是唯一能把编号还原到个人的钥匙，")
        rpt.append("     必须与数据分开、离线单独保管，绝不随数据发给 AI / 上传 / 外发，配对完成后尽早删除。")
    else:
        rpt.append("  2. 本次未生成假名对照表（--no-key），处理不可复原，更接近匿名化；无法再做跨数据配对。")
    rpt.append("  3. 去标识化不免除知情同意、伦理审查与数据保存义务（见 psychology/ethics.md）。")
    report_path.write_text("\n".join(rpt), encoding="utf-8-sig")

    # ---------- 收尾提示 ----------
    print("-" * 60)
    print(f"✔ 去标识化数据已保存：{out_path}")
    print(f"✔ 处理报告已保存：{report_path}")
    if key_written:
        print(f"✔ 假名对照表已保存：{key_path}")
        print("  ⚠ 对照表是唯一复原钥匙：单独离线保存，绝不发给 AI / 上传，用完尽早删除！")
    elif pseudo_col:
        print("ℹ 已按 --no-key 不生成假名对照表，编号不可复原。")
    print("  发给 AI / 上传 / 给外校前，请打开输出文件确认：无姓名、学号、手机、邮箱、身份证等列。")
    print("  原始文件保持不变。")


if __name__ == "__main__":
    main()
