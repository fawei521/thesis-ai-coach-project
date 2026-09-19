# -*- coding: utf-8 -*-
"""
thesis-ai-coach 全量端到端回归（测试金字塔 L7）。
随项目包分发：开发仓库根目录或解压后的干净副本里都能直接运行：
    python tests/full_e2e.py
覆盖：统计/清洗/样本量/模型图/文献脚本真实运行 + 文档-代码一致性 + 合规与事实断言。
约需 3-5 分钟（含 Bootstrap 5000、英文文献联网检索、缺库降级回归）。
退出码 0 = 全部通过；非 0 = 有失败项（见 FAIL 行）。
运行中会在 tests/test-data 生成并自动清理临时产物，结束时恢复被跟踪的基准样例。
"""
import os, sys, subprocess, csv, re, shutil, time, random, math
from pathlib import Path
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
TD = ROOT / "tests" / "test-data"
results = []

def check(n, c, e=""):
    results.append((n, bool(c), e)); print(("PASS " if c else "FAIL ") + n + ("  " + str(e) if e and not c else ""))

def run(a, t=240):
    try:
        return subprocess.run([sys.executable] + a, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=t)
    except subprocess.TimeoutExpired as ex:
        class R:
            returncode = "TIMEOUT"
            stdout = ex.stdout if isinstance(ex.stdout, str) else ""
            stderr = "timeout"
        return R()

def tx(rr): return (ROOT / rr).read_text(encoding="utf-8")
def rt(p): return Path(p).read_text(encoding="utf-8-sig", errors="replace") if Path(p).exists() else ""
def tdoc(rr):
    """v1.84：把"主文件 + 同名子目录里的 .md 分片"拼成一份逻辑文档再返回。
    `core/coach-rules.md` 的流程性三节已下沉为按需读（AI 进到哪个阶段才读哪一节），
    盯这些正文的断言因此一律改用本函数——正文位置变了，断言的名字与内容一条都不动。"""
    d = (ROOT / rr).with_suffix("")
    if not d.is_dir():
        return tx(rr)
    return "\n".join([tx(rr)] + [tx((d / p.name).as_posix()) for p in sorted(d.glob("*.md"))])

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

# 顺序片段清单——顺序即原 full_e2e.py 里各版本块的先后顺序，不得重排。
FRAGMENTS = [
    "case_01.py",  # 首段·夹具与基准样例
    "case_02.py",  # v1.62 现代信效度：McDonald's ω（随 auto_st
    "case_03.py",  # 账号密码红线（P0）：项目任何文件都不得出现"AI 代填/凭据文件"
    "case_04.py",  # v1.63 量表库三扩：10 个高频量表(29→39组、10→11大
    "case_05.py",  # v1.54 学生自己做网页：引导手册 + 预览器 + 三个范例 + 
    "case_06.py",  # v1.56.2 本体口径硬化：人格与挫折协议一致 + 反攀比回归 +
    "case_07.py",  # v1.61 补丁集：手机边界修正/规则优先级/语气去人设命名/阈值争
    "case_08.py",  # v1.65 GB/T 7714-2015 参考文献格式化工具（详见 
    "case_09.py",  # v1.66 缺失值分析与 Little's MCAR =======
    "case_10.py",  # v1.67 参数检验前提假设（正态性/方差齐性） =========
    "case_11.py",  # v1.68 配对设计差异检验（前后测/两条件） ==========
    "case_12.py",  # v1.69 多重比较校正（Bonferroni/Holm/BH/BY
    "case_13.py",  # v1.72 单样本模式（--onesample/--constant
    "case_14.py",  # 并行复核会话交付物：行为锁定（防退回） ==========
    "case_15.py",  # v1.83 记账归档
    "case_16.py",  # v1.84 coach-rules 流程三节下沉为按需读
    "case_17.py",  # v1.85 开题就绪度自检工具
    "case_18.py",  # v1.89 轻量版口径追平＋点名的完整版能力核对＋行尾单一
]

try:
    # ---- 断言主体已按主题切成顺序片段（见 tests/e2e_cases/）：原 612+ 条断言逐字节未改，
    # 仍按原顺序 exec 进本模块命名空间，语义与拆分前的单文件扁平脚本一致。
    _ns = globals()
    for _fn in FRAGMENTS:
        _p = ROOT / "tests" / "e2e_cases" / _fn
        exec(compile(_p.read_text(encoding="utf-8"), "tests/e2e_cases/" + _fn, "exec"), _ns)


finally:
    cleanup()

fails = [x for x in results if not x[1]]
print(f"\n==== 共 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)} ====")
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

stray = _stray_files()
if stray:
    print("FAIL 测试临时文件残留：" + str(sorted(stray)))
    fails.append(("测试临时文件残留", False))
    print(f"==== 修正后：共 {len(results)} 项，失败 {len(fails)} ====")
sys.exit(1 if fails else 0)

