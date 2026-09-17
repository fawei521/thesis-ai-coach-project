# -*- coding: utf-8 -*-
"""数据读写、编码兼容与 scales.txt 解析

读取 UTF-8(含 BOM)/GB18030/GBK 数据，列名与数值矩阵化，
量表配置文件解析（含反向题 (R) 标记与点数量表），反向计分序列。

本模块由 tools/auto_stats.py 拆分而来（v1.53.1），函数体逐行未改动。
"""

from pathlib import Path
import csv
import re
import sys

# ============ 数据读写、编码兼容与 scales.txt 解析 ============

def read_data(filepath):
    """读取CSV，自动兼容UTF-8(含BOM)与GBK/GB18030（问卷星等中文导出常见编码）。"""
    last_err = None
    for enc in ("utf-8-sig", "gb18030", "gbk"):
        try:
            with open(filepath, "r", encoding=enc, newline="") as f:
                rows = list(csv.reader(f))
            if rows:
                return rows[0], rows[1:]
            return [], []
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            continue
    print(f"错误：无法识别文件编码，请先用菜单第1项预处理，或把CSV另存为UTF-8。({last_err})")
    sys.exit(1)


def to_float_matrix(headers, data):
    """把数据转成数值矩阵，非数值记为None"""
    matrix = {h: [] for h in headers}
    for row in data:
        for j, h in enumerate(headers):
            val = row[j] if j < len(row) else ""
            try:
                matrix[h].append(float(val) if val.strip() != "" else None)
            except (ValueError, AttributeError):
                matrix[h].append(None)
    return matrix


def numeric_columns(matrix, headers):
    """识别数值列（至少80%是数字）"""
    numeric = []
    for h in headers:
        vals = matrix[h]
        valid = [v for v in vals if v is not None]
        if valid and len(valid) >= 0.8 * len(vals):
            numeric.append(h)
    return numeric


def parse_scales(path):
    """解析量表配置，返回 {名称: {"items":[...], "reverse":{题:True}, "likert":点数}}。
    格式：
      量表名=题1,题2,题3
      量表名:5=题1,题2(R),题3*       # :5 指定5点(默认)，(R)或*标记反向题
      量表名:7=题1,题2(R)
    """
    scales = {}
    p = Path(path)
    if not p.exists():
        print(f"⚠ 量表配置文件不存在：{path}")
        return scales
    text = None
    for enc in ("utf-8-sig", "gb18030", "gbk"):
        try:
            text = p.read_text(encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if text is None:
        print(f"⚠ 量表配置文件编码无法识别：{path}，请另存为UTF-8")
        return scales
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        left, right = line.split("=", 1)
        left = left.strip()
        likert = 5
        m = re.match(r"^(.+?)\s*[:：]\s*(\d+)$", left)
        if m:
            left = m.group(1).strip()
            likert = int(m.group(2))
        items, reverse = [], {}
        for tok in right.split(","):
            tok = tok.strip()
            if not tok:
                continue
            is_rev = False
            if tok.endswith("(R)") or tok.endswith("（R）") or tok.endswith("(r)") or tok.endswith("*"):
                is_rev = True
                tok = (tok.replace("(R)", "").replace("（R）", "")
                          .replace("(r)", "").rstrip("*").strip())
            if tok:
                items.append(tok)
                if is_rev:
                    reverse[tok] = True
        if left and items:
            scales[left] = {"items": items, "reverse": reverse, "likert": likert}
    return scales


def resolve_col(name, scales, matrix):
    """学生可能传量表名或具体列名；传量表名时映射到其总分列。"""
    name = name.strip()
    if name in matrix:
        return name
    if scales and name in scales:
        return f"{name}总分"
    if name.endswith("总分") or name.endswith("均分"):
        return name
    return name


def _safe_filename(s):
    """去掉 Windows 文件名非法字符。"""
    return "".join(c for c in s if c not in '\\/:*?"<>|').strip().rstrip(".") or "量表"


def recoded_item_series(matrix, conf):
    """返回某量表【反向计分后】的题目数据（与可用题目同序），缺失保持None。"""
    likert = conf.get("likert", 5)
    reverse = conf.get("reverse", {})
    out = []
    for it in conf["items"]:
        if it not in matrix:
            continue
        col = []
        for v in matrix[it]:
            if v is None:
                col.append(None)
            elif reverse.get(it):
                col.append(float(likert + 1 - v))
            else:
                col.append(float(v))
        out.append(col)
    return out
