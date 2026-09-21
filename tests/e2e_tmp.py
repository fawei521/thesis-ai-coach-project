# -*- coding: utf-8 -*-
"""回归壳的临时目录与收尾清理实现（v1.95 从 `tests/full_e2e.py` 原样搬出，逻辑一字未改）。

为什么搬：壳 220 行正好贴满棘轮硬闸，而**每注册一个新片段就要多占一行**——再拆一次之前，
先把这段"只有 cleanup 用得到"的实现挪出去，让壳只剩骨架与 `FRAGMENTS` 顺序清单。
片段仍从壳的 globals() 里取 `new_tmp` / `rmtree_retry`（由壳 import 进来，等价于原地定义）。
"""
import os
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TD = ROOT / "tests" / "test-data"

# 备份可能被覆盖的被跟踪基准样例，结束时恢复（干净副本无 git，靠这里还原）
BACKUP = {}
for name in ["demo_survey.csv", "demo_scales.txt", "sample_literature.txt"]:
    f = TD / name
    if f.exists():
        BACKUP[name] = f.read_bytes()

def new_tmp(name):
    """给测试准备一个固定名字的临时目录（`tests/.tmp_e2e/<name>/`），已存在则先清空。

    为什么不用 `tempfile.mkdtemp()`：
    1. 系统临时区在本项目可能的运行环境里可能只读/半隔离（实测 mkdtemp 出的目录写文件直接 PermissionError）；
    2. tests/test-data 的 `_*` 被 .gitignore 整体排除，子目录无法用 `!` 白名单救回；
    3. 更关键的是 Windows 语义：目录删除后有一段"delete-pending"窗口（句柄未释放前，目录名仍在、
       且**对它及其子路径的一切访问都报拒绝**）。一次回归里反复 mkdtemp + rmtree，
       新建目录就可能撞上刚删掉还没消失的旧目录，导致写入/删除随机 PermissionError。
    改用固定目录名 + 全程复用 + 只清内容不删目录，就完全避开这个窗口。"""
    d = ROOT / "tests" / ".tmp_e2e" / name
    if d.exists():
        for child in d.iterdir():
            if child.is_dir():
                rmtree_retry(child)
            else:
                try: child.unlink()
                except OSError: pass
    d.mkdir(parents=True, exist_ok=True)
    return d

def rmtree_retry(d, tries=5):
    """删目录：Windows 上刚用完的目录可能被杀软/索引器/子进程短暂占用（WinError 5）。
    ignore_errors 会让它**静默留下残留目录**污染仓库，故改为小退避重试并回报。"""
    d = Path(d)
    for i in range(tries):
        try:
            shutil.rmtree(d)
            return True
        except FileNotFoundError:
            return True
        except OSError:
            if i == tries - 1:
                return False
            time.sleep(0.4 * (i + 1))
    return False

def dir_state(d):
    """区分"真残留"与"删除挂起"。
    Windows 上删除目录后，若仍有句柄未释放，目录名会保留在父目录里且**连列目录都被拒绝**
    （delete-pending 状态，句柄一关就自动消失）。这种情况既不是测试失败、也无法强行清理，
    只能报告；能正常列出内容却删不掉的，才是需要人工处理的真残留。
    本函数与 `leftover_dirs` 一律吞掉 OSError：清理阶段的探测本身绝不能抛异常打断回归。"""
    d = Path(d)
    try:
        if not d.exists():
            return "gone"
    except OSError:
        return "pending"
    try:
        list(os.scandir(d))
        return "leftover"
    except OSError:
        return "pending"

def leftover_dirs(sub, prefixes):
    out = []
    try:
        for pre in prefixes:
            for x in sub.glob(pre + "*"):
                try:
                    if x.is_dir():
                        out.append(x)
                except OSError:
                    continue
    except OSError:
        pass
    return out

def cleanup():
    # demo_survey_*.csv/png 只匹配带下划线后缀的生成物，不会动基准 demo_survey.csv
    for pat in ["_e2e*", "_special*", "_ps.csv", "demo_survey_*.csv", "demo_survey_*.png", "demo_survey_cleaned.csv"]:
        for f in TD.glob(pat):
            if f.is_file() and f.name != "demo_survey.csv":
                try: f.unlink()
                except OSError: pass
    for d in [TD / "_chart", TD / "_demo"]:
        rmtree_retry(d)
    # 测试自身的临时目录（阴性测试 / 文献CSV / 手机版构建）：用 tests/.tmp_e2e/ 下固定名目录，
    # 只清内容、不删目录（避免 Windows delete-pending 窗口撞车，见 new_tmp）；
    # 同时兜底扫一遍 test-data 的历史前缀（旧版残留、外部脚本留下的目录）。
    tmp_base = ROOT / "tests" / ".tmp_e2e"
    for d in leftover_dirs(tmp_base, [""]):
        for child in leftover_dirs(d, [""]):
            rmtree_retry(child)
        try:
            for f in os.scandir(d):
                if f.is_file():
                    try: os.unlink(f.path)
                    except OSError: pass
        except OSError:
            pass
    for d in leftover_dirs(TD, ["_skill_neg_", "_litcsv_", "_v12mobile_"]):
        if rmtree_retry(d):
            continue
        st = dir_state(d)
        if st == "pending":
            print("NOTE 测试临时目录处于系统删除挂起态（句柄释放后自行消失，非残留）：" + d.name)
        else:
            print("WARN 测试临时目录未能删除（Windows 占用，请手动清理）：" + str(d))
    for name, b in BACKUP.items():
        (TD / name).write_bytes(b)
    for d in ROOT.rglob("__pycache__"):
        rmtree_retry(d)

# 收尾自检：测试产生的临时**文件**必须已被清掉。
# 只查文件、不要求目录消失：Windows 上刚删过的目录会有一段 delete-pending 窗口，
# 这时连列目录都被拒绝，把"目录名还在"当失败会误报（实测踩过）；而文件残留才是真污染。
def _stray_files():
    out = []
    for d in leftover_dirs(ROOT / "tests" / ".tmp_e2e", [""]):
        try:
            out += [f.name for f in os.scandir(d) if f.is_file()]
        except OSError:
            continue
    out += [f.name for f in leftover_dirs(TD, ["_skill_neg_", "_litcsv_", "_v12mobile_"])
            if dir_state(f) == "leftover"]
    return out