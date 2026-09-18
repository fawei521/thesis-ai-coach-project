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
import os, sys, subprocess, csv, re, shutil, time
from pathlib import Path
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
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

try:
    for pat in ["_e2e*", "demo_survey_*.csv", "demo_survey_*.png"]:
        for f in TD.glob(pat):
            if f.is_file(): f.unlink()
    r = run(["tools/data_cleaner.py", str(TD / "demo_survey.csv"), "--scales", str(TD / "demo_scales.txt"),
             "-o", str(TD / "_e2e_cleaned.csv")])
    nrows = 0; p = TD / "_e2e_cleaned.csv"
    if p.exists(): nrows = sum(1 for _ in csv.reader(open(p, encoding="utf-8-sig"))) - 1
    check("清洗后192份", nrows == 192, f"rows={nrows} rc={r.returncode}")
    check("清洗报告生成", (TD / "demo_survey_清洗报告.csv").exists())
    r = run(["tools/auto_stats.py", str(TD / "demo_survey.csv"), "--scales", str(TD / "demo_scales.txt"),
             "--y", "NSSI", "--x", "AI情感依赖", "--mediators", "孤独感,反刍思维", "--boot", "5000"], 300)
    stat = rt(TD / "demo_survey_统计结果.csv"); rel = rt(TD / "demo_survey_信度分析.csv")
    med = rt(TD / "demo_survey_中介效应.csv"); chi = rt(TD / "demo_survey_卡方检验.csv")
    check("auto_stats退出0", r.returncode == 0, r.stderr[-300:])
    alpha = {}
    try:
        for row in csv.DictReader(open(TD / "demo_survey_信度分析.csv", encoding="utf-8-sig")):
            alpha[row["量表"]] = float(row["Cronbach_alpha"])
    except Exception: pass
    ea = {"AI情感依赖": .93, "孤独感": .925, "反刍思维": .938, "NSSI": .933}
    check("α基准", all(alpha.get(k) is not None and abs(alpha[k] - v) < .0051 for k, v in ea.items()), str(alpha))
    check("分半SB列", "分半SpearmanBrown" in rel)
    check("Harman38.49", "38.49" in r.stdout)
    check("相关基准", all(s in stat for s in [".269", ".459", ".393"]))
    check("链式基准", ".034" in med and ".012" in med and ".063" in med)
    check("卡方p.418", ".418" in chi)
    heat = TD / "demo_survey_相关热图.png"
    check("热图生成", heat.exists() and heat.stat().st_size > 50000)
    try:
        import matplotlib.image as mi
        im = mi.imread(str(heat)); check("热图像素>300", im.shape[0] > 300, im.shape)
    except Exception as e:
        check("热图读取", False, str(e))
    r3 = run(["tools/sample_size.py"]); check("样本量速查", r3.returncode == 0 and ("85" in r3.stdout or "179" in r3.stdout))
    # v1.60 样本量补 t 检验设计（t²=F 复用非中心F，黄金值对照 scipy.stats.nct）
    ss_ind = run(["tools/sample_size.py", "--design", "ttest-ind", "--effect", "0.5"])
    check("独立t样本量", ss_ind.returncode == 0 and "N=128" in ss_ind.stdout and "每组至少 64 人" in ss_ind.stdout)
    ss_pair = run(["tools/sample_size.py", "--design", "ttest-paired", "--effect", "0.5"])
    check("配对t样本量", ss_pair.returncode == 0 and "N=34" in ss_pair.stdout)
    ss_ind3 = run(["tools/sample_size.py", "--design", "ttest-ind"])
    check("独立t三档", ss_ind3.returncode == 0 and all(s in ss_ind3.stdout for s in ["788", "128", "52"]))
    ss_bad = run(["tools/sample_size.py", "--design", "ttest-paired", "--effect", "0"])
    check("t样本量坏参守卫", ss_bad.returncode == 1 and "d（配对为 dz）" in ss_bad.stdout
          and "Traceback" not in (ss_bad.stdout or "") + (ss_bad.stderr or ""))
    # Welch ANOVA 数值回归：强异方差下锁定 F/df1/df2/p，防止分母自由度公式退回 (k^3-k)/(3D)
    # 历史缺陷：df2 被放大 k 倍、p 系统性偏小（强异方差时可翻转显著性）；基准经教科书公式＋scipy 三方核对
    try:
        if str(ROOT / "tools") not in sys.path:
            sys.path.insert(0, str(ROOT / "tools"))
        import stats.compare as _wcmp
        _wg = [[1, 2, 2, 3, 2, 1, 3, 2], [6, 9, 14, 7, 12, 5, 13, 8], [2, 3, 1, 4, 2, 3, 2, 3]]
        _wF, _wd1, _wd2, _wp = _wcmp._welch_anova(_wg)
        check("Welch强异方差数值基准", _wF is not None and abs(_wF - 16.7979) < 2e-3 and _wd1 == 2
              and abs(_wd2 - 12.5210) < 2e-3 and _wp is not None and abs(_wp - 2.8522e-4) < 2e-5,
              f"F={_wF} df1={_wd1} df2={_wd2} p={_wp}（错误式会得 df2≈37.56、p≈6.1e-6）")
    except Exception as _we:
        check("Welch强异方差数值基准", False, repr(_we))
    # ---- Mahalanobis 多元异常值筛查（纯标准库；D²/标记已用 numpy/scipy 黄金对照；只标记不删）----
    import random as _rnd
    mdir = new_tmp("mahalanobis")
    _rgen = _rnd.Random(20260918)
    def _ih(): return _rgen.random() + _rgen.random() + _rgen.random() - 1.5
    mrows = []
    for _ in range(80):
        _z1 = _ih(); _z2 = 0.6 * _z1 + 0.4 * _ih(); _z3 = 0.3 * _z1 + 0.7 * _ih()
        mrows.append([round(20 + 5 * _z1, 2), round(15 + 4 * _z2, 2), round(10 + 3 * _z3, 2)])
    mrows.append([45, 35, 28])  # 极端多元异常点（最后一行→数据行号82）
    with open(mdir / "mah.csv", "w", encoding="utf-8-sig", newline="") as _mf:
        _mw = csv.writer(_mf); _mw.writerow(["V1", "V2", "V3"]); _mw.writerows(mrows)
    rdef = run(["tools/auto_stats.py", str(mdir / "mah.csv")], 200)
    check("Mahalanobis默认关闭", "多元异常值筛查" not in (rdef.stdout or "")
          and not (mdir / "mah_多元异常值.csv").exists())
    rmh = run(["tools/auto_stats.py", str(mdir / "mah.csv"), "--mahalanobis"], 200)
    check("Mahalanobis检出极端点", rmh.returncode == 0 and "发现 1 个多元异常个案" in (rmh.stdout or "")
          and "数据行号 82" in (rmh.stdout or ""), (rmh.stderr or "")[-200:])
    with open(mdir / "mah_多元异常值.csv", encoding="utf-8-sig") as _mf:
        mout = list(csv.reader(_mf))
    mflag = [row for row in mout[1:] if row[-1] == "是"]
    check("Mahalanobis仅标记极端点",
          mout[0] == ["数据行号", "D2", "df", "p", "是否多元异常值"] and len(mflag) == 1 and mflag[0][0] == "82",
          str(mflag))
    check("Mahalanobis不删原数据", sum(1 for _ in open(mdir / "mah.csv", encoding="utf-8-sig")) - 1 == 81)
    rtwo = run(["tools/auto_stats.py", str(mdir / "mah.csv"), "--mahalanobis", "V1", "V2"], 200)
    check("Mahalanobis指定变量", rtwo.returncode == 0 and "变量 2 个" in (rtwo.stdout or ""))
    rbad = run(["tools/auto_stats.py", str(mdir / "mah.csv"), "--mahalanobis", "--mah-alpha", "1.5"], 200)
    check("Mahalanobis坏alpha守卫", "--mah-alpha" in (rbad.stdout or "") and "0 与 1" in (rbad.stdout or ""))
    check("Mahalanobis只标记不删口径",
          "不能为了让模型好看而删点" in (rmh.stdout or "") and "敏感性分析" in (rmh.stdout or ""))
    # ---- 效应量换算/复核 effect_size.py（纯标准库；关键数值已用 numpy/scipy 黄金对照）----
    esd = run(["tools/effect_size.py", "d", "--m1", "10", "--sd1", "2", "--n1", "30",
               "--m2", "9", "--sd2", "2", "--n2", "30"])
    check("效应量d均值换算", esd.returncode == 0 and "Cohen's d = 0.500" in esd.stdout
          and "Hedges' g = 0.494" in esd.stdout and ".2/.5/.8" in esd.stdout)
    esdt = run(["tools/effect_size.py", "d-t", "--t", "2.65", "--n1", "60", "--n2", "60"])
    check("效应量d由t换算", esdt.returncode == 0 and "Cohen's d = 0.484" in esdt.stdout)
    esr = run(["tools/effect_size.py", "r", "--r", "0.34", "--n", "120"])
    check("效应量r的Fisher区间", esr.returncode == 0 and "[0.171, 0.489]" in esr.stdout
          and "d ≈ 0.723" in esr.stdout)
    ese = run(["tools/effect_size.py", "eta", "--F", "5.20", "--df1", "2", "--df2", "117"])
    check("效应量偏eta2", ese.returncode == 0 and "= 0.082" in ese.stdout and ".01/.06/.14" in ese.stdout)
    esv = run(["tools/effect_size.py", "v", "--chi2", "6.10", "--n", "200", "--rows", "2", "--cols", "2"])
    check("效应量CramersV", esv.returncode == 0 and "Cramér's V = √(χ²/(N·df_min)) = 0.175" in esv.stdout
          and "φ(phi) = √(χ²/N) = 0.175" in esv.stdout)
    esbad = run(["tools/effect_size.py", "r", "--r", "0.9", "--n", "2"])
    check("效应量坏参守卫", esbad.returncode == 0 and "Traceback" not in (esbad.stdout or "")
          and "n>3" in (esbad.stdout or ""))
    # ---- 聚合/区分效度 validity_cr_ave.py（纯标准库；CR/AVE 公式已用 numpy 黄金对照）----
    vca_src = tx("tools/validity_cr_ave.py")
    check("效度工具纯标准库", "import csv" in vca_src and "matplotlib" not in vca_src and "pandas" not in vca_src)
    check("效度工具公式与红线", "(Σλ" in vca_src and "Fornell" in vca_src and "真实 CFA" in vca_src)
    vca_ok = run(["tools/validity_cr_ave.py",
                  "--factor", "学习投入=0.72,0.68,0.74,0.70",
                  "--factor", "学业倦怠=0.60,0.65,0.58,0.62",
                  "--corr", "学习投入,学业倦怠,0.45"])
    check("效度CR_AVE黄金值", vca_ok.returncode == 0 and all(s in vca_ok.stdout for s in
          ["0.803", "0.505", "0.710", "0.706", "0.376", "0.613"]), (vca_ok.stderr or "")[-200:])
    check("效度区分成立", "区分效度成立" in vca_ok.stdout and "Fornell-Larcker" in vca_ok.stdout)
    vca_bad_disc = run(["tools/validity_cr_ave.py",
                        "--factor", "学习投入=0.72,0.68,0.74,0.70",
                        "--factor", "学业倦怠=0.60,0.65,0.58,0.62",
                        "--corr", "学习投入,学业倦怠,0.65"])
    check("效度区分存疑能识别", vca_bad_disc.returncode == 0 and "区分效度存疑" in vca_bad_disc.stdout
          and "0.613" in vca_bad_disc.stdout and "0.650" in vca_bad_disc.stdout)
    vca_bad_load = run(["tools/validity_cr_ave.py", "--factor", "X=1.02,0.7"])
    check("效度坏载荷守卫", vca_bad_load.returncode == 1 and "标准化载荷" in vca_bad_load.stdout
          and "Traceback" not in (vca_bad_load.stdout or "") + (vca_bad_load.stderr or ""))
    vca_bad_fac = run(["tools/validity_cr_ave.py", "--factor", "X=0.7,0.6", "--corr", "X,Y,0.3"])
    check("效度未知因子守卫", vca_bad_fac.returncode == 1 and "未提供载荷" in vca_bad_fac.stdout
          and "Traceback" not in (vca_bad_fac.stdout or "") + (vca_bad_fac.stderr or ""))
    vca_neg = run(["tools/validity_cr_ave.py", "--factor", "X=0.72,-0.68,0.74"])
    check("效度负载荷警示", vca_neg.returncode == 0 and "负载荷" in vca_neg.stdout
          and "反向题" in vca_neg.stdout)
    vca_nofile = run(["tools/validity_cr_ave.py", "--loadings-csv", " definitely_missing_xyz.csv"])
    check("效度缺文件守卫", vca_nofile.returncode == 1 and vca_nofile.stdout.lstrip().startswith("✗")
          and "Traceback" not in (vca_nofile.stdout or "") + (vca_nofile.stderr or ""))
    vca_dir = new_tmp("validity")
    vca_csv = run(["tools/validity_cr_ave.py",
                   "--factor", "学习投入=0.72,0.68,0.74,0.70",
                   "--factor", "学业倦怠=0.60,0.65,0.58,0.62",
                   "--corr", "学习投入,学业倦怠,0.45",
                   "--csv-out", str(vca_dir)])
    vca_out = vca_dir / "_聚合区分效度.csv" if (vca_dir / "_聚合区分效度.csv").exists() else None
    check("效度CSV导出", vca_csv.returncode == 0 and vca_out is not None and vca_out.exists())
    if vca_out:
        vca_rows = list(csv.reader(open(vca_out, encoding="utf-8-sig")))
        check("效度CSV内容", vca_rows[0][:5] == ["因子", "题项数", "CR组合信度", "AVE平均方差抽取", "√AVE"]
              and vca_rows[1][0] == "学习投入" and abs(float(vca_rows[1][2]) - 0.803) < 5e-3
              and "成立" in vca_rows[1][7], str(vca_rows[:2]))

    # ---- v1.62 现代信效度：McDonald's ω（随 auto_stats 信度节产出）+ HTMT（--htmt 模式）----
    # ω 在上面的 demo_survey 主回归里已随信度分析产出，这里核列、数值关系与纯标准库实现
    check("ω进入信度CSV", "McDonald_ω" in rel)
    omega = {}
    try:
        for row in csv.DictReader(open(TD / "demo_survey_信度分析.csv", encoding="utf-8-sig")):
            if row.get("McDonald_ω"):
                omega[row["量表"]] = float(row["McDonald_ω"])
    except Exception:
        pass
    check("ω数值合理", all(omega.get(k, 0) >= .70 for k in ["AI情感依赖", "孤独感", "反刍思维", "NSSI"])
          and all(omega[k] >= alpha[k] - .02 for k in omega if k in alpha), str(omega))
    check("ω进入stdout", "McDonald" in r.stdout and "ω" in r.stdout)
    rel_src = tx("tools/stats/reliability.py")
    check("ω纯标准库PAF", "def mcdonald_omega" in rel_src and "_paf_one_factor" in rel_src
          and "numpy" not in rel_src and "scipy" not in rel_src)
    # HTMT 固定夹具：两个正交 4 题构念（n=220），点估计黄金值 0.088（numpy 独立实现核对）
    hdir = new_tmp("htmt")
    for fn in ["demo_htmt.csv", "htmt_scales.txt"]:
        shutil.copy2(TD / fn, hdir / fn)
    hok = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "demo_htmt.csv"),
               "--scales", str(hdir / "htmt_scales.txt"), "--boot", "300"], 120)
    check("HTMT正交夹具", hok.returncode == 0 and "0.088" in hok.stdout and "区分效度成立" in hok.stdout
          and "CI上限" in hok.stdout, (hok.stderr or "")[-200:])
    mci = re.search(r"\[0\.\d{3}, (0\.\d{3})\]", hok.stdout)
    check("HTMT的CI上限<1", bool(mci) and float(mci.group(1)) < 0.5, hok.stdout[-400:])
    hcsv = hdir / "demo_htmt_HTMT区分效度.csv"
    check("HTMT导出CSV", hcsv.exists())
    if hcsv.exists():
        hrows = list(csv.reader(open(hcsv, encoding="utf-8-sig")))
        check("HTMT表内容", hrows[0][:6] == ["构念A", "构念B", "完整N", "HTMT", "CI下限", "CI上限"]
              and hrows[1][0] == "构念A" and abs(float(hrows[1][3]) - 0.0882) < .01, str(hrows[:2]))
    # 反向计分不变性：B 构念题项整体反向（6−x），scales 标 (R)，HTMT 点估计应保持一致
    with open(hdir / "demo_htmt.csv", encoding="utf-8-sig") as f:
        rdr = list(csv.reader(f)); hdr = rdr[0]; body = rdr[1:]
    bidx = [hdr.index(c) for c in ["B1", "B2", "B3", "B4"]]
    for row in body:
        for bi in bidx:
            row[bi] = str(6 - int(row[bi]))
    with open(hdir / "demo_htmt_rev.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(hdr); w.writerows(body)
    with open(hdir / "htmt_rev_scales.txt", "w", encoding="utf-8") as f:
        f.write("构念A:5=A1,A2,A3,A4\n构念B:5=B1(R),B2(R),B3(R),B4(R)\n")
    hrev = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "demo_htmt_rev.csv"),
                "--scales", str(hdir / "htmt_rev_scales.txt"), "--boot", "0"], 60)
    check("HTMT反向题等价", hrev.returncode == 0 and "0.088" in hrev.stdout, (hrev.stderr or "")[-200:])
    # 阴性夹具：同一因子拆成两个"量表"（n=220，固定随机种子），HTMT 应≥.90 且 CI 上限≥1
    import random as _rnd
    _rnd.seed(7)
    _lam = [0.74, 0.71, 0.69, 0.73, 0.67, 0.70]
    with open(hdir / "neg.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["id", "X1", "X2", "X3", "Y1", "Y2", "Y3"])
        for i in range(220):
            g = _rnd.gauss(0, 1); row = [i + 1]
            for L in _lam:
                v = 3 + .9 * (L * g + (1 - L * L) ** .5 * _rnd.gauss(0, 1))
                row.append(max(1, min(5, round(v))))
            w.writerow(row)
    with open(hdir / "neg_scales.txt", "w", encoding="utf-8") as f:
        f.write("构念X:5=X1,X2,X3\n构念Y:5=Y1,Y2,Y3\n")
    hneg = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "neg.csv"),
                "--scales", str(hdir / "neg_scales.txt"), "--boot", "300"], 120)
    check("HTMT同因子判失败", hneg.returncode == 0 and "不足" in hneg.stdout and "不通过" in hneg.stdout,
          hneg.stdout[-300:])
    # 守卫：缺 scales / 单量表 / boot 负数，均给中文提示且无 Traceback
    h_nosc = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "demo_htmt.csv")])
    check("HTMT缺scales守卫", h_nosc.returncode == 1 and "--scales" in h_nosc.stdout
          and "Traceback" not in (h_nosc.stdout or "") + (h_nosc.stderr or ""))
    with open(hdir / "one_scales.txt", "w", encoding="utf-8") as f:
        f.write("构念A:5=A1,A2,A3,A4\n")
    h_one = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "demo_htmt.csv"),
                 "--scales", str(hdir / "one_scales.txt")])
    check("HTMT单量表守卫", h_one.returncode == 1 and "不足 2 个" in h_one.stdout)
    h_negboot = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "demo_htmt.csv"),
                     "--scales", str(hdir / "htmt_scales.txt"), "--boot", "-1"])
    check("HTMT负boot守卫", h_negboot.returncode == 1 and "不能为负" in h_negboot.stdout
          and "Traceback" not in (h_negboot.stdout or "") + (h_negboot.stderr or ""))

    # ---- v1.60 预试项目分析工具 item_analysis.py（菜单14），决断值CR经 scipy 黄金核对 ----
    ia_src = tx("tools/item_analysis.py")
    check("项目分析纯标准库且复用stats", "import csv" in ia_src and "matplotlib" not in ia_src
          and "from stats.reliability import cronbach_alpha" in ia_src and "t_p_two_sided" in ia_src)
    ia_dir = new_tmp("item")
    ia_ok = run(["tools/item_analysis.py", str(TD / "demo_survey.csv"),
                 "--scales", str(TD / "demo_scales.txt"), "--only", "孤独感",
                 "--csv-out", str(ia_dir)])
    check("项目分析决断值", ia_ok.returncode == 0 and "18.519" in ia_ok.stdout
          and "决断值" in ia_ok.stdout and "高/低分组各 54 人" in ia_ok.stdout and "保留" in ia_ok.stdout)
    ia_out = ia_dir / "demo_survey_项目分析.csv"
    check("项目分析CSV导出", ia_out.exists())
    if ia_out.exists():
        ia_rows = list(csv.reader(open(ia_out, encoding="utf-8-sig")))
        check("项目分析CSV内容", ia_rows[0][:6] == ["量表", "题项", "均值", "标准差", "决断值CR", "自由度df"]
              and len(ia_rows) == 5 and all(r[10] == "保留" for r in ia_rows[1:]), str(ia_rows[:2]))
    ia_badg = run(["tools/item_analysis.py", str(TD / "demo_survey.csv"),
                   "--scales", str(TD / "demo_scales.txt"), "--group", "0.9"])
    check("项目分析坏比例守卫", ia_badg.returncode == 1 and "0.10" in ia_badg.stdout
          and "Traceback" not in (ia_badg.stdout or "") + (ia_badg.stderr or ""))
    ia_noscale = run(["tools/item_analysis.py", str(TD / "demo_survey.csv")])
    check("项目分析缺配置守卫", ia_noscale.returncode == 1 and "--scales" in ia_noscale.stdout)

    # ---- v1.60 自编量表内容效度 content_cvi.py（菜单15），黄金值对照 Lynn/Polit 算例 ----
    cvi_src = tx("tools/content_cvi.py")
    check("内容效度纯标准库", "import csv" in cvi_src and "matplotlib" not in cvi_src
          and "math.comb" in cvi_src and "read_data" in cvi_src)
    cvi_dir = new_tmp("cvi")
    cvi_ok = run(["tools/content_cvi.py", str(TD / "demo_cvi.csv"), "--csv-out", str(cvi_dir)])
    # 5专家×4题：A=5,5,4,2 → I-CVI 1/1/.8/.4；κ*=1/1/.763/.127；S-CVI/Ave=.80、UA=.50
    check("内容效度指数", cvi_ok.returncode == 0 and "I-CVI=1.000" in cvi_ok.stdout
          and "I-CVI=0.800" in cvi_ok.stdout and "κ*=0.763" in cvi_ok.stdout
          and "κ*=0.127" in cvi_ok.stdout and "S-CVI/Ave=0.800" in cvi_ok.stdout
          and "S-CVI/UA=0.500" in cvi_ok.stdout)
    cvi_out = cvi_dir / "demo_cvi_内容效度CVI.csv"
    check("内容效度CSV导出", cvi_out.exists())
    if cvi_out.exists():
        cvi_rows = list(csv.reader(open(cvi_out, encoding="utf-8-sig")))
        check("内容效度CSV内容", cvi_rows[0][:5] == ["条目", "专家数N", "评相关人数A", "I-CVI", "机遇一致Pc"]
              and len(cvi_rows) == 5 and cvi_rows[3][3] == "0.8" and cvi_rows[4][3] == "0.4"
              and cvi_rows[1][7] == "0.8", str(cvi_rows))
    cvi_bad = run(["tools/content_cvi.py", str(TD / "demo_cvi.csv"), "--threshold", "5"])
    check("内容效度坏阈值守卫", cvi_bad.returncode == 1 and "--threshold" in cvi_bad.stdout
          and "Traceback" not in (cvi_bad.stdout or "") + (cvi_bad.stderr or ""))

    p1 = run(["tests/consistency_check.py"]); check("一致性0", p1.returncode == 0, p1.stdout[-200:])
    g = ROOT / "_ghost_doc_xyz.md"
    g.write_text("运行 `tools/ghost_tool_xyz.py --fake-switch-xyz`，导出 `_幽灵分析.csv`，见 [假文档](ghost_page_xyz.md)，路径 `我的工作区/99-ghost/`", encoding="utf-8")
    p2 = run(["tests/consistency_check.py"]); g.unlink(); o2 = p2.stdout
    for nm, s in [("幽灵脚本", "ghost_tool_xyz.py"), ("假开关", "--fake-switch-xyz"), ("假导出", "幽灵分析.csv"),
                  ("假文档", "ghost_page_xyz.md"), ("假路径", "99-ghost")]:
        check("变异抓" + nm, s in o2)
    check("变异非0", p2.returncode != 0)
    qt = tx("templates/questionnaire-template.md")
    check("问卷注意力题", "注意力检查" in qt and "质量控制题" in qt)
    check("问卷时长埋点", "作答时长" in qt)
    check("问卷多选题示例", "可多选" in qt and "不计入任何量表" in qt)
    cr = tx("core/coach-rules.md")
    check("coach5埋点", "注意力检查题" in cr and "作答时长" in cr)
    check("coach5多选填空", "多选题" in cr and "scales.txt 时勿列入" in cr)
    check("coach6样本量", "sample_size.py" in cr)
    check("coach7五指标", "低变异" in cr and "注意力检查题答错" in cr)
    menu = tx("tools/menu.py"); check("menu第8项", "【8/15】" in menu and "sample_size.py" in menu)
    qs = tx("QUICKSTART.md"); check("QS菜单8", "8. 开题样本量" in qs)
    check("QS流程顺序", qs.find("查文献读文献") < qs.find("开题报告/开题答辩"))
    bad = []
    for md in ROOT.rglob("*.md"):
        t = md.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"0[123](?!-)(?:文献PDF|问卷数据|分析结果)", t): bad.append(md.name)
        if re.search(r"(?<!-)(?<!\d)文献PDF/", t): bad.append(md.name + ":裸")
    check("目录名统一", not bad, str(sorted(set(bad))))
    st = tx("START.md"); check("START第七步", "## 第七步：开始引导" in st and "第五步半" not in st)
    las = tx("workflows/literature-auto-search.md"); check("知网落点", "我的工作区/01-文献PDF/" in las and "`文献PDF/`" not in las)
    check("批量下载红线阈值", "单次登录全文下载不超过约 **30 篇**" in las and "30-50 篇以内" in las and "永久封禁" in las)
    check("全文不传播不批量工具", "不得传播、上传到公开网络" in las and "禁用迅雷" in las and "不整期/整卷下载" in las)
    check("题录总表归文献区", "文献总表 CSV 都归文献区" in las and "文献总表 CSV 放 `我的工作区/03" not in las)
    # ---- 账号密码红线（P0）：项目任何文件都不得出现"AI 代填/凭据文件"这类写法 ----
    # 起因：并行会话把"AI 读取本地凭据文件代填图书馆密码"写进了 literature-auto-search，
    # 与 CONSTITUTION 第七条、ai-literacy、behavior-self-test T25 三处直接冲突。
    # 该缺陷此前能一路过关，是因为没有任何断言守这条红线——本组断言即为它补的闸。
    cred_md = [p for p in ROOT.rglob("*.md")
               if "CHANGELOG" not in p.name and p.name not in ("e2e-test.md", "behavior-self-test.md")
               and "doubao-skill" not in p.parts]
    cred_hits = []
    for p in cred_md:
        t = p.read_text(encoding="utf-8", errors="ignore")
        for bad in ("AI代填", "授权AI代填", "library-login.local.json", "代填并提交", "读取凭据文件"):
            if bad in t:
                cred_hits.append(f"{p.name}:{bad}")
    check("凭据代填红线", not cred_hits, str(sorted(set(cred_hits))))
    check("登录交学生本人", "登录一律由学生本人" in las or "学生本人输入" in las)
    check("拒绝代填明确入工作流", "不索取、不接受、不存储、不代填" in las and "T25" in las)
    check("检索记录预置存在", (ROOT / "我的工作区" / "01-文献PDF" / "检索记录.md").exists())
    check("检索记录模板存在", (ROOT / "templates" / "检索记录模板.md").exists())
    check("检索记录入口", "检索记录.md" in las and "检索记录.md" in tx("我的工作区/先读我.md"))
    check("进度卡接检索留痕", "文献与检索留痕" in tx("我的工作区/我的论文进度.md"))
    check("菜单5接受CSV", "标准 CSV" in menu and "txt" in menu)
    # 发布形态安全：预置文件必须在 git 索引里，否则 git archive 打出的包会缺它，
    # 而开发树里看着"明明存在"（.gitignore 的目录级排除曾把新建的 检索记录.md 挡在包外）。
    if (ROOT / ".git").exists():
        ls = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", cwd=str(ROOT))
        tracked = set(ls.stdout.split("\0")) if ls.returncode == 0 else set()
        want = {"我的工作区/01-文献PDF/检索记录.md", "templates/检索记录模板.md",
                "我的工作区/先读我.md", "我的工作区/我的论文进度.md"}
        check("预置文件已入库", want <= tracked, str(sorted(want - tracked)))
        # 反向：学生本人的数据/成果/凭据不得入库（题录 txt、CSV、真实数据）
        leak = [t for t in tracked if t.startswith("我的工作区/")
                and not (t.endswith("把论文PDF放这里.txt") or t.endswith("把问卷数据放这里.txt")
                         or t.endswith("把分析结果放这里.txt") or t.endswith("把网页放这里.txt")
                         or t.endswith("先读我.md") or t.endswith("我的论文进度.md")
                         or t.endswith("检索记录.md"))]
        check("学生数据不入库", not leak, str(sorted(leak)))
    for d in ["01-文献PDF", "02-问卷数据", "03-分析结果"]: check("目录" + d, (ROOT / "我的工作区" / d).is_dir())
    bat = (ROOT / "启动工具箱.bat").read_bytes(); cc = bat.count(b"\r\n"); lo = bat.count(b"\n") - cc
    check("bat编码行尾", bat[:3] != b"\xef\xbb\xbf" and cc > 20 and lo == 0, f"crlf={cc} lf={lo}")
    df = tx("workflows/defense-guide.md")
    check("答辩24问+伦理", "24问" in df and "监护人书面知情同意" in df and "剔除" in df and "数据怎么保管" in df)
    et = tx("psychology/ethics.md")
    check("热线12356首选", "12356" in et and "国卫医政函" in et)
    check("400不误标全国", "全国心理援助热线：400-161-9995" not in et and "希望24热线（社会公益热线）" in et)
    check("即刻危机120/110", "120或110" in et)
    check("未成年人assent分层", "书面 assent" in et and "尊重未成年人的拒绝（dissent）" in et and "学生本人同意（assent）简短模板" in et)
    check("敏感话题风险预案", "研究前先定风险预案" in et and "校园投放伦理" in et)
    check("数据保存年限口径", "不少于5年" in et and "至少保存3年" not in et)
    check("问卷模板12356", "12356" in qt)
    check("问卷模板学段适配", "学段" in qt and "中学生版" in qt and "大学生版" in qt and "仅大学生填写；中学生样本删除" in qt)
    check("问卷性别第三项与最小化", "其他/不愿透露" in qt and "个人信息最小化" in qt)
    check("答辩答法12356", "12356" in df)
    es = tx("workflows/environment-setup.md")
    check("JASP中介内置+PROCESS可选", "Regression → Mediation" in es and "PROCESS 模块" in es and "Model 6" in es)
    check("Mac不预装Python", "不再预装" in es and "python3" in es)
    check("Zotero样式非插件", "引用样式" in es and "Zotero Style" not in es)
    check("Python勾选PATH", "Add python.exe to PATH" in es)
    check("只从官网下载", "只从官网下载" in es)
    check("coach答辩24问", "24个高频问题库" in cr and "20个高频问题库" not in cr)
    check("README能力表24", "24个高频问题" in tx("README.md"))
    check("coach12阶段", "12阶段工作流" in cr and "阶段11：答辩准备" in cr)
    check("coach三检查闸", "动机闸" in cr and "质量闸" in cr and "留痕闸" in cr)
    check("coach文献量口径", "至少 90 篇候选池" in cr and "10–20 篇重点" in cr and "多词交叉核验" in cr)
    pg = tx("workflows/proposal-guide.md")
    check("开题脚本不进论文", "不写进开题报告" in pg and "公认软件" in pg)
    check("量表授权邮件", "书面许可" in pg and "授权邮件" in pg)
    check("开题八节对应", "预期困难与对策" in pg and "研究创新点" in pg)
    check("样本量口径统一", "sample_size.py" in pg and "链式≥300" in pg and "G*Power" in pg)
    ad = tx("templates/ai-usage-declaration.md")
    check("AI声明如实口径", "核心学术贡献由本人独立完成" in ad and "AI未参与的内容" not in ad)
    check("AI声明亲自核实", "亲自检索、阅读与核实" in ad)
    check("AI声明三版本", "详细版" in ad and "简洁版" in ad and "学校有固定格式" in ad)
    pr = tx("workflows/paper-reading-guide.md")
    check("精读IMRaD卡片", "IMRaD" in pr and "与本研究的关系" in pr)
    check("精读分层数量", "精读（10–20 篇，从约 90 篇候选池中筛）" in pr and "泛读（20-40篇）" in pr)
    check("进度卡12阶段", "11 答辩准备" in tx("我的工作区/我的论文进度.md"))
    cm = ROOT / "workflows" / "communication-guide.md"
    check("沟通指南文件存在", cm.exists())
    if cm.exists():
        cg = cm.read_text(encoding="utf-8")
        check("沟通12场景", all(s in cg for s in ["场景1", "场景12", "带选择题", "12356", "关键决策日志"]))
        check("沟通原则与礼仪", "定期" in cg and "附件命名" in cg and "对事不对人" in cg)
    check("coach阶段10引用", "workflows/communication-guide.md" in cr)
    check("START导航沟通", "communication-guide.md" in st)
    rm = tx("README.md"); check("README沟通清单", "communication-guide.md" in rm)
    check("README数字修正", "16种" in rm and "10种统计方法" not in rm)
    daa = tx("workflows/data-analysis-auto.md")
    check("分析流程多选说明", "多选题" in daa and "开放填空题" in daa and "scales.txt" in daa)
    check("JASP链式走Process模块", "Process 模块后选 Model 6" in daa and "原生支持链式中介" not in daa)
    check("PROCESS官网域名", "processmacro.org" in daa and "hayesprocess.com" not in daa)
    check("样本量质量闸口径", "链式等复杂模型建议 300" in daa and "至少>150" not in daa)
    wg = tx("workflows/writing-guide.md")
    check("写作结果章节", "简单斜率" in wg and "热图" in wg and "卡方" in wg)
    check("结果章顺序规范", "人口学差异（t/方差分析/卡方等）→相关" in wg)
    sp = run(["tests/test_special_columns.py"]); check("特殊列测试0", sp.returncode == 0, (sp.stdout or "")[-300:] + (sp.stderr or "")[-200:])
    wp = tx("tools/wjx_preprocess.py"); dc = tx("tools/data_cleaner.py")
    check("预处理特殊列识别", "detect_special_column" in wp and "multi" in wp)
    check("清洗器排除0/1", "{0.0, 1.0}" in dc and "可多选" in dc)
    check("紧急三红线", "不可破的三条红线" in cr and "不编造" in cr and "延期" in cr)
    check("紧急逐日任务", "D1" in cr and "7天版" in cr and "1天版" in cr and "3天版" in cr)
    sl = tx("psychology/scale-library.md")
    check("NSSI循证量表", all(s in sl for s in ["FASM", "C-FASM", "DSHI", "ISAS", "Klonsky"]))
    check("幻觉量表已删", "ASFQ" not in sl and "SBI" not in sl and "Nixon" not in sl)
    check("RRQ修正24题", "24 | 自我反刍" in sl and "RRQ-C" in sl)
    check("RRQ旧10题删除", "反刍思维量表（RRQ） | 10" not in sl)
    check("AAS18题", "成人依恋量表（AAS） | 18" in sl and "各6题" in sl)
    check("FASM拼写Kelley", "Lloyd, Kelley & Hope, 1997" in sl and "Lloyd, Kelly" not in sl)
    check("UCLA第3版1996", "Russell, 1996（V3" in sl and "R-UCLA，第3版" not in sl)
    check("CDRISC简版作者", "Campbell-Sills & Stein, 2007" in sl)
    check("MPAI原始Leung", "Leung, 2008" in sl)
    # ---- v1.59 量表库扩充：8 个新小节(17-24)+BSMAS，硬事实逐条锁定（均经联网核查）----
    check("DASS21事实", all(s in sl for s in [
        "DASS-21", "龚栩等, 2010", "21（抑郁/焦虑/压力各7题）", "求和后**×2**", "不作临床诊断"]))
    check("PSS10事实", all(s in sl for s in [
        "PSS-10", "Cohen & Williamson, 1988", "失控/无助感（6个负向题：1,2,3,6,9,10）",
        "4个正向题反向计分", "过去一个月"]))
    check("SCSQ事实", all(s in sl for s in [
        "SCSQ", "解亚宁, 1998", "积极应对1-12题", "消极应对13-20题", "0=不采取"]))
    check("ERQ事实且区别CERQ", all(s in sl for s in [
        "ERQ", "王力等, 2007", "认知重评6题：1,3,5,7,8,10", "表达抑制4题：2,4,6,9",
        "**7点计分**", "不可混用或互相替代引用"]))
    check("SCS谭树华19题", all(s in sl for s in [
        "谭树华、郭永玉, 2008", "节制娱乐(6)", "专注工作(4)", "谭树华**19题**中文版", "BSCS 为13题"]))
    check("CSES中文10题", all(s in sl for s in [
        "CSES", "杜建政、张翔、赵燕, 2012", "中文版10题（原版12题", "第2,3,5,7,8,10题为反向计分"]))
    check("SWLS事实", all(s in sl for s in [
        "SWLS", "Diener, Emmons, Larsen & Griffin, 1985", "总分5-35", "30-35非常满意"]))
    check("BPNS题数存疑标注", all(s in sl for s in [
        "BPNS", "刘俊升、林丽玲、吕媛等, 2013", "自主7+胜任6+关系8", "多被记为19题",
        "必须查刘俊升2013原文确认总题数"]))
    check("BSMAS六要素", all(s in sl for s in [
        "BSMAS", "Andreassen等, 2016", "显著性+心境改变", "耐受+戒断+冲突+复发", "总分6-30"]))
    check("量表库编号到29且十大类", "### 28. 基本心理需要" in sl and "### 29. 睡眠质量（PSQI）" in sl
          and "## 九、自我评价、幸福感与基本需要类" in sl and "## 十、睡眠与心身健康类" in sl
          and "## 七、负性情绪综合筛查" in sl and "## 八、压力、应对与自我调节类" in sl)
    # ---- v1.60 量表库再扩充：5 个高频量表(PANAS/IRI-C/GQ-6/GHQ-12/PSQI)，硬事实逐条锁定（均经联网核查）----
    check("PANAS事实", all(s in sl for s in [
        "PANAS", "Watson, Clark & Tellegen, 1988", "20（正性10+负性10）",
        "张卫东、刁静、Schick, 2004", "各 10-50"]))
    check("IRIC事实", all(s in sl for s in [
        "IRI-C", "Davis, 1980", "22（PT5＋FS5＋EC6＋PD6）",
        "28（4 维度各 7 题）", "张凤凤、董毅等, 2010"]))
    check("GQ6事实", all(s in sl for s in [
        "GQ-6", "McCullough, Emmons & Tsang, 2002", "第 3、6 题反向计分", "总分 6-42"]))
    check("GHQ12事实", all(s in sl for s in [
        "GHQ-12", "12（6 正向＋6 负向）", "GHQ 双峰法 0-0-1-1",
        "Likert 法 0-1-2-3", "总分 0-36", "不作临床诊断"]))
    check("PSQI事实", all(s in sl for s in [
        "PSQI", "Buysse 等, 1989", "刘贤臣、唐茂芹等, 1999",
        "19 个自评＋5 个他评（仅 18 个自评条目计分）", "总分 0-21"]))
    po0 = tx("templates/paper-outline.md")
    check("大纲伦理埋点", "监护人书面知情同意" in po0 and "注意力检查题" in po0 and "Bootstrap 5000" in po0)
    check("大纲结果章完整", all(s in po0 for s in ["平行分析", "Games-Howell", "卡方", "简单斜率", "偏态"]))
    sg = tx("psychology/stats-guide.md")
    # v1.53.1：auto_stats 已拆为 tools/stats/ 包，实现函数按所属模块核对（不再只看 CLI 入口）
    acmp = tx("tools/stats/compare.py"); areg = tx("tools/stats/regress.py")
    check("stats能力真实", "Welch" in sg and "_welch_anova" in acmp and "_levene" in acmp and "_welch_t" in acmp)
    check("GamesHowell引导JASP", "Games-Howell" in sg and "JASP" in sg)
    check("正态性边界引导JASP", "Shapiro-Wilk" in sg and "Q-Q" in sg and "JASP" in sg)
    check("stats指南PROCESS域名", "processmacro.org" in sg and "hayesprocess.com" not in sg)
    check("网络分析稳定性检验", "corStability" in sg and "expected influence" in sg and "CS>.25" in sg)
    lit = tx("core/ai-literacy.md")
    check("AI素养agentic去魅", all(s in lit for s in ["能联网", "虚拟电脑", "关键动作", "动手查", "动手算"]))
    check("AI素养隐私去标识化", all(s in lit for s in ["去标识化", "身份证号", "验证码"]))
    check("START能力清单VIF真实", "_vif" in areg and "VIF" in st and "Bonferroni" in acmp)
    pt = tx("templates/proposal-template.md")
    check("开题功效依据", "G*Power" in pt and "300" in pt and "15%" in pt)
    check("开题伦理不预填α", "监护人书面知情同意" in pt and "注意力检查题" in pt and "不要预先填写" in pt and "慎用" in pt)
    check("开题数据处理补全", all(s in pt for s in ["分半", "探索性因子分析", "Welch", "卡方", "模型 1"]))
    pp = tx("templates/defense-ppt-outline.md")
    check("PPT伦理合规", ("监护人书面同意" in pp or "监护人书面知情同意" in pp) and "心理援助" in pp)
    check("PPT空白谨慎", "较少有研究" in pp and "差异" in pp)
    prt = tx("templates/progress-template.md")
    check("进度卡五指标功效分半", "长直线" in prt and "注意力题答错" in prt and "功效" in prt and "分半" in prt and "剔除" in prt)
    tc = tx("workflows/toolchain-guide.md")
    check("工具链脚本真实", "literature_organizer.py" in tc and (ROOT / "tools" / "literature_organizer.py").exists())
    check("工具链区分插件职责", "只负责把 Zotero 里的文献信息和 PDF 标注" in tc and "没有 \"Insert Citation\" 命令" in tc)
    check("工具链引用插件指引", "Citations** 插件" in tc and "Zotero Citations" in tc and "Add/Edit Citation" in tc)
    check("工具链Zotero7菜单", "设置（Zotero 6 旧版叫" in tc)
    cg2 = "tools/chart_generator.py"; cd = TD / "_chart"; cd.mkdir(exist_ok=True)
    o1 = cd / "m1.png"; r = run([cg2, "--variables", "AI,孤独,反刍,NSSI", "--type", "chain", "--output", str(o1)])
    check("模型图不传系数出图", r.returncode == 0 and o1.exists() and o1.stat().st_size > 5000, (r.stderr or "")[-200:])
    o2 = cd / "m2.png"; r = run([cg2, "-v", "AI,孤独,反刍,NSSI", "-c", "0.2,0.3", "-o", str(o2)])
    check("模型图少填补0", r.returncode == 0 and o2.exists(), (r.stderr or "")[-200:])
    r = run([cg2, "-v", "AI,孤独,反刍,NSSI", "-c", "a,b,c,d", "-o", str(cd / "m3.png")])
    check("非数字系数友好报错", r.returncode != 0 and "Traceback" not in (r.stderr or "") and "数字" in (r.stdout or ""))
    csrc = tx("tools/chart_generator.py")
    check("模型图无bold且系数可选", "fontweight='bold'" not in csrc and "default=None" in csrc)
    dd = TD / "_demo"; r = run(["tools/generate_demo_data.py", "--outdir", str(dd)])
    check("菜单7演示数据", r.returncode == 0 and (dd / "demo_survey.csv").exists() and (dd / "demo_scales.txt").exists(), (r.stderr or "")[-200:])
    check("菜单7默认归位工作区02", "我的工作区/02-问卷数据" in menu)
    r = run(["tools/literature_organizer.py", str(TD / "sample_literature.txt")])
    check("菜单5文献整理", r.returncode == 0 and "去重" in (r.stdout or ""), (r.stderr or "")[-200:])
    # 文献整理器吃"带中文表头的CSV"（paper_search 导出 / 知网导出 / Excel 另存）
    # 关键回归点：识别列名与解析必须用同一编码，否则 GBK 导出会静默导出 0 篇
    lit_tmp = new_tmp("litcsv")
    try:
        utf8_csv = lit_tmp / "utf8.csv"
        utf8_csv.write_text("序号,标题,作者,年份,期刊,DOI\n1,大学生AI依赖与孤独感,张三,2025,心理科学,10.1/x\n"
                            "2,反刍思维的中介作用,李四,2024,心理学报,\n", encoding="utf-8")
        r = run(["tools/literature_organizer.py", str(utf8_csv), "-o", str(lit_tmp / "o1.csv")])
        check("整理器吃UTF8标准CSV", r.returncode == 0 and "读取文献：2篇" in (r.stdout or ""), (r.stdout or "")[-200:])
        # 知网/Excel 另存的 GBK CSV：必须同样读出 2 篇（此前会解成乱码、静默 0 篇）
        gbk_csv = lit_tmp / "gbk.csv"
        gbk_csv.write_bytes("序号,标题,作者,年份,期刊\n1,大学生AI依赖与孤独感,张三,2025,心理科学\n"
                            "2,反刍思维的中介作用,李四,2024,心理学报\n".encode("gb18030"))
        r = run(["tools/literature_organizer.py", str(gbk_csv), "-o", str(lit_tmp / "o2.csv")])
        check("整理器吃GBK中文CSV", r.returncode == 0 and "读取文献：2篇" in (r.stdout or ""), (r.stdout or "")[-240:])
        # 有表头但无内容：必须中文提示而不是静默吐出 0 篇整理表
        empty_csv = lit_tmp / "empty.csv"
        empty_csv.write_text("序号,标题,作者\n1,,\n", encoding="utf-8")
        r = run(["tools/literature_organizer.py", str(empty_csv), "-o", str(lit_tmp / "o3.csv")])
        check("整理器空表不静默", r.returncode != 0 or "读取文献：0篇" not in (r.stdout or ""),
              (r.stdout or "")[-200:])
    finally:
        shutil.rmtree(lit_tmp, ignore_errors=True)
    check("菜单6提示回车", "直接回车" in menu)
    r = run(["tools/paper_search.py", "--query", "AI dependence", "--limit", "2", "--output", str(TD / "_ps.csv")], 90)
    check("菜单4英文检索不崩", r.returncode == 0 or "Traceback" not in (r.stderr or ""), (r.stderr or "")[-200:])
    psrc = tx("tools/paper_search.py")
    check("菜单4默认归位01", "我的工作区/01-文献PDF/英文文献.csv" in menu)
    check("去Sci-Hub改合法途径", "Sci-Hub" not in psrc and "馆际互借" in psrc and "mkdir" in psrc)
    gd = run(["tests/test_graceful_degradation.py"], 260)
    check("降级与闭环回归测试0", gd.returncode == 0, ((gd.stdout or "")[-600:]) + ((gd.stderr or "")[-200:]))

    # ---- v1.53.1 工程化：编码守卫 + auto_stats 拆包 ----
    # 覆盖 tools/、tests/ 与 doubao-skill/（轻量版自带 validate.py 也必须有守卫；
    # 此前只扫前两个目录，validate.py 的守卫存在与否没有回归保护）
    guard_paths = (sorted((ROOT / "tools").glob("*.py"))
                   + sorted((ROOT / "tests").glob("*.py"))
                   + sorted((ROOT / "doubao-skill").glob("*.py")))
    no_guard = [str(p.relative_to(ROOT)) for p in guard_paths
                if "输出编码守卫" not in p.read_text(encoding="utf-8")]
    check("全部脚本有编码守卫", not no_guard, str(no_guard))
    # 管道运行不得因 GBK 崩溃：默认编码下跑一致性自检，退出码必须为 0
    env_min = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    pc = subprocess.run([sys.executable, "tests/consistency_check.py"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", timeout=120, env=env_min)
    check("管道下一致性自检不崩", pc.returncode == 0 and "Traceback" not in (pc.stderr or ""),
          (pc.stderr or "")[-200:])
    check("管道下输出中文正常", "一致性自检" in (pc.stdout or "") and "\ufffd" not in (pc.stdout or ""))
    stats_pkg = ROOT / "tools" / "stats"
    check("auto_stats已拆包", stats_pkg.is_dir() and len(list(stats_pkg.glob("*.py"))) >= 10,
          "modules=%d" % len(list(stats_pkg.glob("*.py"))))
    check("CLI入口瘦身", len((ROOT / "tools" / "auto_stats.py").read_text(encoding="utf-8").splitlines()) < 300,
          "lines=%d" % len((ROOT / "tools" / "auto_stats.py").read_text(encoding="utf-8").splitlines()))
    check("原大文件已分解", not any(len(p.read_text(encoding="utf-8").splitlines()) > 700
                                 for p in list((ROOT / "tools").glob("*.py")) + list(stats_pkg.glob("*.py"))))
    check("sample_size复用路径已更新", "from stats.mathx import" in tx("tools/sample_size.py"))
    check("一致性检查覆盖子包", "rglob" in tx("tests/consistency_check.py"))
    # auto_stats 拆包后必须能被 runpy.run_path 调用：runpy 不把脚本目录加入 sys.path，
    # 少了显式 sys.path 引导就会 ModuleNotFoundError: stats（tests/test_graceful_degradation.py 走的正是这条路）
    rpy = subprocess.run(
        [sys.executable, "-c",
         "import runpy,sys; sys.argv=['auto_stats.py','tests/test-data/demo_survey.csv','--profile'];"
         " runpy.run_path('tools/auto_stats.py', run_name='__main__')"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    check("auto_stats可被runpy调用", rpy.returncode == 0 and "ModuleNotFoundError" not in (rpy.stderr or ""),
          (rpy.stderr or "")[-250:])
    # ---- v1.53.1 版本日志单文件化：CHANGELOG.md 是唯一版本历史，其余人只留指针 ----
    chg = tx("CHANGELOG.md")
    check("CHANGELOG存在且带日期索引", "版本索引（含日期）" in chg and "_发布包" in chg)
    check("README指向CHANGELOG", "CHANGELOG.md" in rm)
    check("ROADMAP指向CHANGELOG", "CHANGELOG.md" in tx("ROADMAP.md"))
    check("PROJECT_PLAN指向CHANGELOG", "CHANGELOG.md" in tx("PROJECT_PLAN.md"))
    check("版本历史不再四处重复", len(tx("ROADMAP.md").splitlines()) < 60
          and len(tx("README.md").splitlines()) < 200, "roadmap=%d readme=%d" % (
              len(tx("ROADMAP.md").splitlines()), len(tx("README.md").splitlines())))
    # 版本号三处一致：从 START.md 解析当前版本，要求 CHANGELOG 与 README 都能对上
    # （不写死版本号，避免每次发版都要改断言）
    mver = re.search(r"版本\s*(v[\d.]+)", st)
    cur_ver = mver.group(1) if mver else ""
    check("版本号三处一致", bool(cur_ver) and cur_ver in chg and cur_ver in rm,
          "解析到 START=%s, CHANGELOG命中=%s, README命中=%s" % (
              cur_ver or "(未解析到)", cur_ver in chg, cur_ver in rm))
    check("DEVELOPMENT引用CHANGELOG", "CHANGELOG.md" in tx("DEVELOPMENT.md"))

    # ---- v1.54 学生自己做网页：引导手册 + 预览器 + 三个范例 + 工作区 ----
    wg = tx("workflows/webpage-guide.md")
    check("网页指南含硬规矩", all(s in wg for s in ["单文件", "自包含", "不引用外部资源", "不放个人隐私", "网页不是论文成果"]))
    check("网页指南含五类网页", all(s in wg for s in ["文献笔记网页", "数据分析结果看板", "研究流程图", "量表与问卷速查", "论文进度看板"]))
    check("网页指南含三闸", all(s in wg for s in ["闸 1 动机闸", "闸 2 质量闸", "闸 3 留痕闸"]))
    check("网页指南警示勿抄范例", "不要抄" in wg)
    ex = ROOT / "templates" / "网页范例"
    ex_pages = [ex / "01-文献笔记网页" / "index.html",
                ex / "02-术语词典网页" / "index.html",
                ex / "03-研究流程图" / "research-flow.html",
                ex / "04-统计方法选择器" / "index.html"]
    check("四个网页范例齐备", all(p.exists() for p in ex_pages),
          str([p.name for p in ex_pages if not p.exists()]))
    check("范例带勿直接使用标注",
          all("范例，请勿直接使用" in p.read_text(encoding="utf-8", errors="replace") for p in ex_pages))
    check("范例README提示只学做法",
          "只用来学" in tx("templates/网页范例/README.md") or
          ("可以学的是" in tx("templates/网页范例/README.md")
           and "只能参考代码结构与交互设计" in tx("templates/网页范例/README.md")))
    sel = tx("templates/网页范例/04-统计方法选择器/index.html")
    check("方法选择器范例标注", "范例，请勿直接使用" in sel)
    check("方法选择器自包含无外链", not any(s in sel for s in
          ['src="http', 'href="http', "<link", "@import", "cdn", "<script src"]))
    check("方法选择器决策覆盖", all(s in sel for s in
          ["Welch t", "Mann-Whitney", "Kruskal-Wallis", "Games-Howell", "Cramér",
           "模型6", "Mahalanobis", "Spearman", "偏相关", "Fisher", "不显著也是结果"]))
    pw = tx("tools/webpage_preview.py")
    check("预览器只读", "SimpleHTTPRequestHandler" in pw and "do_POST" not in pw and "do_PUT" not in pw)
    check("预览器默认只绑本机", "127.0.0.1" in pw and "--lan" in pw)
    check("预览器防路径穿越", "normpath" in pw and "relative_to" in pw and "反斜杠" in pw)
    check("预览器声明charset", "charset=utf-8" in pw)
    pl = run(["tools/webpage_preview.py", "templates/网页范例", "--list"])
    check("预览器--list可运行", pl.returncode == 0 and "index.html" in (pl.stdout or ""), (pl.stderr or "")[-200:])
    wdir = ROOT / "我的工作区" / "04-网页"
    check("工作区04-网页就位", wdir.is_dir() and (wdir / "把网页放这里.txt").exists())
    check("菜单第9项", "【9/15】" in menu and "webpage_preview.py" in menu)
    check("网页能力已登记到入口",
          "webpage-guide.md" in st and "webpage_preview.py" in st and "webpage-guide.md" in cr)
    check("README登记网页能力", "webpage-guide.md" in rm and "webpage_preview.py" in rm)
    check("QUICKSTART登记第9项", "预览我做的网页" in tx("QUICKSTART.md"))
    check("工作区说明含04-网页", "04-网页" in tx("我的工作区/先读我.md"))

    # ---- v1.59 数据去标识化工具（隐私闸：假名化/删除直接标识符 + 准标识符 k-匿名体检）----
    an_src = tx("tools/anonymize_data.py")
    check("脱敏工具纯标准库", "import csv" in an_src and "matplotlib" not in an_src and "pandas" not in an_src)
    check("脱敏工具有安全开关", all(s in an_src for s in ["--dry-run", "--no-key", "--columns", "--k"]))
    check("脱敏工具另存不改原文件", "_去标识化.csv" in an_src and "同名同路径" in an_src)
    check("菜单第11项去标识化", "【11/15】" in menu and "anonymize_data.py" in menu and "去标识化" in menu)
    check("菜单第12项效应量", "【12/15】" in menu and "effect_size.py" in menu and "效应量" in menu)
    check("菜单第13项效度", "【13/15】" in menu and "validity_cr_ave.py" in menu and "区分效度" in menu)
    check("菜单13含HTMT", "HTMT" in menu)
    check("菜单第14项项目分析", "【14/15】" in menu and "item_analysis.py" in menu and "决断值" in menu)
    check("菜单第15项内容效度", "【15/15】" in menu and "content_cvi.py" in menu and "CVI" in menu)
    check("START登记去标识化", "anonymize_data.py" in st and "去标识化" in st)
    check("QUICKSTART登记第11项", "去标识化" in tx("QUICKSTART.md"))
    check("AI素养接线去标识化工具", "anonymize_data.py" in tx("core/ai-literacy.md"))
    check("数据工作流接线去标识化", "anonymize_data.py" in tx("workflows/data-analysis-auto.md"))

    pii_fixture = ROOT / "tests/test-data/sample_pii.csv"
    check("脱敏夹具就位", pii_fixture.exists())
    an_dir = new_tmp("anonymize")
    an_dry = run(["tools/anonymize_data.py", str(pii_fixture), "--dry-run", "-o", str(an_dir / "dry.csv")])
    check("脱敏dry-run退出0", an_dry.returncode == 0, (an_dry.stderr or "")[-200:])
    check("脱敏dry-run零写入", not (an_dir / "dry.csv").exists() and "体检模式" in (an_dry.stdout or "")
          and "k-匿名" in (an_dry.stdout or ""))
    an_r = run(["tools/anonymize_data.py", str(pii_fixture), "-o", str(an_dir / "out.csv"),
                "--report", str(an_dir / "r.txt"), "--key", str(an_dir / "key.csv")])
    check("脱敏正式运行退出0", an_r.returncode == 0 and (an_dir / "out.csv").exists(), (an_r.stderr or "")[-300:])
    with open(an_dir / "out.csv", encoding="utf-8-sig") as an_f:
        an_out_rows = list(csv.reader(an_f))
    an_out_header, an_out_body = an_out_rows[0], an_out_rows[1:]
    an_out_text = "\n".join([",".join(an_out_header)] + [",".join(x) for x in an_out_body])
    check("脱敏行数守恒", len(an_out_body) == 12, "rows=%d" % len(an_out_body))
    for an_removed in ["姓名", "学号", "手机号", "邮箱", "身份证号", "微信号", "QQ", "IP地址", "C1"]:
        check("脱敏删除列_" + an_removed, an_removed not in an_out_header, "header=%s" % an_out_header)
    check("脱敏保留编号与分析列", all(c in an_out_header for c in ["编号", "序号", "性别", "年级", "专业", "生源地", "Q1"]))
    for an_leak in ["张三", "李四", "13800000001", "13900000001", "zhangsan", "110101200001011234",
                    "zhangsan_wx", "192.168.1.10", "20210101"]:
        check("脱敏无泄漏_" + an_leak, an_leak not in an_out_text, "found %s" % an_leak)
    check("脱敏编号形如P码", all(row[an_out_header.index("编号")].startswith("P") for row in an_out_body if row))
    with open(an_dir / "key.csv", encoding="utf-8-sig") as an_kf:
        an_key_text = "\n".join([",".join(x) for x in list(csv.reader(an_kf))])
    check("假名对照表可还原", "P001" in an_key_text and "张三" in an_key_text and "原姓名" in an_key_text)
    an_nk = run(["tools/anonymize_data.py", str(pii_fixture), "-o", str(an_dir / "nk.csv"),
                 "--report", str(an_dir / "nk_r.txt"), "--no-key"])
    check("no-key退出0且无对照表", an_nk.returncode == 0 and (an_dir / "nk.csv").exists()
          and not (an_dir / "sample_pii_假名对照表.csv").exists() and "不可复原" in (an_nk.stdout or ""))
    an_refuse = run(["tools/anonymize_data.py", str(pii_fixture), "-o", str(pii_fixture)])
    check("脱敏拒绝覆盖原文件", an_refuse.returncode != 0 and "同名同路径" in (an_refuse.stdout or ""))
    (an_dir / "gbk.csv").write_bytes("姓名,手机号,性别,Q1\n张三,13812345678,男,4\n李四,13987654321,女,5\n".encode("gbk"))
    an_gbk_run = run(["tools/anonymize_data.py", str(an_dir / "gbk.csv"), "-o", str(an_dir / "gbk_out.csv"),
                      "--report", str(an_dir / "gbk_r.txt"), "--key", str(an_dir / "gbk_key.csv")])
    an_gbk_text = (an_dir / "gbk_out.csv").read_text(encoding="utf-8-sig") if (an_dir / "gbk_out.csv").exists() else ""
    check("脱敏兼容GBK", an_gbk_run.returncode == 0 and "编号" in an_gbk_text and "手机号" not in an_gbk_text
          and "13812345678" not in an_gbk_text, (an_gbk_run.stderr or "")[-200:])
    (an_dir / "nopii.csv").write_text("性别,年级,Q1\n男,大四,4\n女,大三,5\n男,大四,3\n", encoding="utf-8")
    an_nopii_run = run(["tools/anonymize_data.py", str(an_dir / "nopii.csv"), "-o", str(an_dir / "nopii_out.csv"),
                        "--report", str(an_dir / "nopii_r.txt")])
    check("脱敏无标识符友好退出", an_nopii_run.returncode == 0 and not (an_dir / "nopii_out.csv").exists()
          and "未发现" in (an_nopii_run.stdout or ""))
    an_mask_run = run(["tools/anonymize_data.py", str(pii_fixture), "-o", str(an_dir / "mask.csv"),
                       "--report", str(an_dir / "mask_r.txt"), "--no-key",
                       "--columns", "手机号:mask;姓名:drop;学号:drop"])
    an_mask_text = (an_dir / "mask.csv").read_text(encoding="utf-8-sig") if (an_dir / "mask.csv").exists() else ""
    check("脱敏mask打码", an_mask_run.returncode == 0 and "手机号" in an_mask_text and "138****0001" in an_mask_text
          and "13800000001" not in an_mask_text, (an_mask_run.stderr or "")[-200:])
    check("k匿名识别稀有组合", "考古学" in (an_r.stdout or "") and "最小等价类 k = 1" in (an_r.stdout or ""))
    an_raw = pii_fixture.read_text(encoding="utf-8")
    check("脱敏原文件不变", "张三" in an_raw and "13800000001" in an_raw)

    # ---- v1.55 豆包 Skill 轻量版（doubao-skill/ 独立分发子包，自带 validate.py 门禁）----
    SK = ROOT / "doubao-skill"
    check("Skill目录就位", SK.is_dir() and (SK / "SKILL.md").exists())
    skr = run(["doubao-skill/validate.py"], 120)
    check("Skill自检退出0", skr.returncode == 0 and "全部通过" in (skr.stdout or ""),
          ((skr.stdout or "")[-400:]) + ((skr.stderr or "")[-200:]))
    skm = (SK / "SKILL.md").read_text(encoding="utf-8")
    check("Skill默认自然语气", "自然（默认" in skm and "不套任何人设" in skm)
    check("Skill鼓励默认可关", "标准（默认" in skm and "关闭鼓励" in skm)
    stage_list = list((SK / "stages").glob("stage-*.md"))
    check("Skill阶段12个", len(stage_list) == 12, "n=%d" % len(stage_list))
    check("Skill三闸入阶段", all(all(g in p.read_text(encoding="utf-8") for g in ("动机闸", "质量闸", "留痕闸"))
                                  for p in stage_list))
    skp = (SK / "references" / "coaching-protocol.md").read_text(encoding="utf-8")
    check("Skill危机与紧急", all(s in skp for s in ("12356", "120 或 110", "紧急模式")))
    ske = (SK / "references" / "encouragement-guide.md").read_text(encoding="utf-8")
    check("Skill鼓励P0不包装", "P0 不包装" in ske and "成长型思维" in ske)
    check("Skill进度模板", (SK / "templates" / "我的论文进度模板.md").exists())
    check("Skill轻量版不虚构工具", "不含脚本" in (SK / "references" / "tools.md").read_text(encoding="utf-8"))
    # 阴性测试：在临时副本植入断链与占位，validate.py 必须判失败（防止自检是空壳）
    # 临时目录用**系统临时区**，不放 tests/test-data：实测 Windows 下在仓库内 mkdtemp + copytree
    # 会被杀软/索引器短暂锁住（WinError 5），既可能打断回归、又会留下删不掉的目录污染仓库。
    neg = new_tmp("skill_neg")
    try:
        # copytree 到刚建的目录仍可能被瞬时占用，保留小退避重试（此前无重试，直接抛 PermissionError 打断全量回归）
        copied = False
        for attempt in range(5):
            try:
                shutil.copytree(SK, neg / "doubao-skill")
                copied = True
                break
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(0.4 * (attempt + 1))
        check("Skill阴性副本就位", copied)
        vf = neg / "doubao-skill" / "SKILL.md"
        vf.write_text(vf.read_text(encoding="utf-8") + "\n见 `ghost-ref-xyz.md`，TODO 待补充\n",
                      encoding="utf-8")
        nr = run([str(neg / "doubao-skill" / "validate.py")], 60)
        check("Skill自检能抓变异", nr.returncode != 0 and "ghost-ref-xyz.md" in (nr.stdout or ""),
              "rc=%s" % nr.returncode)
    finally:
        if not rmtree_retry(neg):
            print("WARN 阴性测试临时目录未能删除（请手动清理）：" + str(neg))
    check("一致性检查跳过Skill子包", "doubao-skill" in tx("tests/consistency_check.py"))

    # ---- v1.56 本体反馈协议+鼓励系统（学习成熟技能范式：强制基准/分级/门禁/行为自测）----
    cp_path = ROOT / "core" / "coaching-protocol.md"
    eg_path = ROOT / "core" / "encouragement-guide.md"
    bt_path = ROOT / "tests" / "behavior-self-test.md"
    check("v156反馈协议文件", cp_path.exists() and bt_path.exists() and eg_path.exists())
    cp = cp_path.read_text(encoding="utf-8")
    eg = eg_path.read_text(encoding="utf-8")
    bt = bt_path.read_text(encoding="utf-8")
    check("v156协议核心结构", all(s in cp for s in ("引导循环", "反馈三段式", "P0", "P1", "P2", "回复前门禁")))
    check("v156协议触发与边界", all(s in cp for s in ("触发边界", "边界情况", "学生长时间失联", "复合请求")))
    check("v156协议学生指令", "关闭鼓励" in cp and "读进度卡继续" in cp and "跳到第 N 步" in cp)
    check("v156协议危机口径", "12356" in cp and "120 或 110" in cp and "不允诺保密" in cp)
    check("v156鼓励四理论依据", all(s in eg for s in ("正强化", "成长型思维", "反馈干预理论", "自我决定理论")))
    check("v156鼓励三档与默认", all(s in eg for s in ("标准", "精简", "关闭", "默认")))
    check("v156鼓励切换指令", all(s in eg for s in ("关闭鼓励", "鼓励精简一点", "开启鼓励")))
    check("v156鼓励P0不包装与奖赏", "P0 不包装" in eg and "里程碑" in eg and "挫折时刻协议" in eg)
    check("v156鼓励禁夸天赋且去机械计数", "禁止夸天赋" in eg and "每轮至多一次肯定" not in eg and "密度自然" in eg)
    check("v158鼓励四语气措辞", all(s in eg for s in ("自然（默认）", "简洁直接（可选）", "温和耐心（可选）", "活泼热情（可选）"))
          and "专业导师（默认）" not in eg and "小奶狗（可选）" not in eg)
    check("v156行为自测用例与声明", "T1 " in bt and "T32" in bt and "测试计划" in bt and "不是" in bt)
    check("v156coach人格鼓励正交", "人格只管" in cr and "鼓励档" in cr and "core/encouragement-guide.md" in cr)
    check("v156coach旧鼓励表述移除", "不给无意义鼓励" not in cr)
    check("v156coach卡壳临时降档", "临时降一档" in cr)
    check("v156coach阶段0鼓励档", "鼓励档（默认" in cr)
    check("v156coach引用反馈协议", "core/coaching-protocol.md" in cr and "反馈三段式" in cr)
    check("v156START必读六份", "先读这六份" in st and "core/companionship.md" in st and "core/coaching-protocol.md" in st and "core/encouragement-guide.md" in st)
    check("v156START开场第五问", "关闭鼓励" in st and "反馈方式" in st)
    card_t = tx("templates/progress-template.md"); card_w = tx("我的工作区/我的论文进度.md")
    check("v156双进度卡鼓励档行", "鼓励反馈档" in card_t and "鼓励反馈档" in card_w)
    check("v156入口登记齐全", all(s in tx("AGENTS.md") for s in ("coaching-protocol.md", "encouragement-guide.md"))
          and "关闭鼓励" in rm and "关闭鼓励" in tx("QUICKSTART.md"))
    check("v156鼓励与Skill口径一致",
          "鼓励精简一点" in eg and "鼓励精简一点" in skm and "反馈三段式" in skp and "P0/P1/P2" in skp)
    # 注意：不能用 `"T1" in bt` 这类子串判断（"T1" 会匹配上 T10–T19），
    # 必须真正抽出编号再验连续性，否则删掉中间某条也发现不了
    bt_nums = sorted(int(x) for x in re.findall(r"\| T(\d+) \|", bt))
    check("v156自测用例编号连续", bt_nums == list(range(1, len(bt_nums) + 1)) and len(bt_nums) >= 32,
          "n=%d nums=%s" % (len(bt_nums), bt_nums[:5]))
    check("v156情绪与挫折用例", "T31" in bt and "T32" in bt and "接住情绪" in bt and "不得评价情绪本身" in bt)

    # ---- v1.56.2 本体口径硬化：人格与挫折协议一致 + 反攀比回归 + 规则单源 ----
    check("v1562霸道总裁情绪口径", "会怼回去" not in cr and "正常化情绪" in cr and "我卡在哪" in cr)
    check("v1562反攀比无凭据比较", "大半同级学生" not in eg and "攀比式表达" in eg)
    check("v1562专业导师焦虑先接情绪", "先一句话正常化" in eg)
    check("v1562规则单源不重复", "第三节为唯一来源" in eg and "coach-rules.md` 第四节" in cp
          and "主动临时降一档把这一步讲透" not in cp)

    # ---- v1.56.4 规则接线：core规则真正接入10个workflow（统一指针，不复制正文）+ 鼓励理论规范出处 + 防假空白 ----
    wf_all = sorted(p for p in (ROOT / "workflows").glob("*.md"))
    check("v1564工作流十份", len(wf_all) == 10, "n=%d" % len(wf_all))
    check("v1564工作流全部接带教约定",
          all(all(s in p.read_text(encoding="utf-8") for s in
                  ("**带教约定**", "core/coaching-protocol.md", "core/encouragement-guide.md",
                   "反馈三段式", "P0/P1/P2", "core/coach-rules.md")) for p in wf_all))
    _conv = [[l for l in p.read_text(encoding="utf-8").splitlines() if "**带教约定**" in l]
             for p in wf_all]
    check("v1564带教约定指针逐字一致",
          all(len(x) == 1 for x in _conv) and len({x[0].strip() for x in _conv}) == 1)
    check("v1564鼓励理论规范出处", all(s in eg for s in (
        "10.1037/0033-2909.119.2.254", "10.1037/0022-3514.75.1.33",
        "Mueller, C. M., & Dweck, C. S. (1998)", "Kluger, A. N., & DeNisi, A. (1996)",
        "Ryan, R. M., & Deci, E. L. (2000)", "Skinner, B. F. (1953)")))
    check("v1564理论出处带核对日期", "核对" in eg and "勿与上面 Ryan & Deci (2000) 混写" in eg)
    check("v1564文献防假空白反查", all(s in tx("workflows/literature-auto-search.md")
                                  for s in ("假空白", "0 命中", "上位词")))

    # ---- v1.56.6 专业文档接线 + 行为自测补盲与可追溯走查 ----
    psy = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "psychology").glob("*.md")}
    check("v1566专业文档三份", set(psy) == {"ethics.md", "scale-library.md", "stats-guide.md"}, str(set(psy)))
    check("v1566专业文档使用约定指针",
          all("**使用约定**" in t and "core/coaching-protocol.md" in t for t in psy.values()))
    check("v1566伦理危机口径", "12356" in psy["ethics.md"] and "不做临床诊断" in psy["ethics.md"])
    check("v1566统计数据真实性P0",
          "P0 红线" in psy["stats-guide.md"] and "不显著也是结果" in psy["stats-guide.md"])
    check("v1566量表库需核实", "需核实" in psy["scale-library.md"])
    check("v1566自测用例扩至38且连续", len(bt_nums) >= 38 and bt_nums[:38] == list(range(1, 39)),
          "n=%d" % len(bt_nums))
    check("v1566自测新增六场景", all(s in bt for s in ("T33", "T34", "T35", "T36", "T37", "T38")))
    check("v158自测用例扩至45且连续", len(bt_nums) == 45 and bt_nums == list(range(1, 46)),
          "n=%d" % len(bt_nums))
    check("v158自测新增七场景", all(("T%d" % i) in bt for i in range(39, 46)))
    check("v1566走查记录诚实标注",
          "桌面静态走查" in bt and "非真人" in bt and "最高优先级遗留" in bt)

    # ---- v1.2 手机独立版：能力边界三处一致 + 合并单文件可生成且自包含 ----
    mgp = ROOT / "doubao-skill" / "references" / "mobile-guide.md"
    check("v12手机说明文件", mgp.exists())
    mg = mgp.read_text(encoding="utf-8") if mgp.exists() else ""
    check("v12手机能力边界齐全", all(s in mg for s in ("手机上能完成", "手机上做不了", "必须回电脑", "手机装不了")))
    check("v12统计回电脑的理由", "JASP" in mg and "SPSS" in mg and "PROCESS" in mg and "电脑软件" in mg)
    check("v12只有手机时的出路", all(s in mg for s in ("必须找一台电脑", "带回手机", "跟导师说明")))
    check("v12安装方式含保底单文件", "合并单文件" in mg and "thesis-ai-coach-手机版.md" in mg)
    check("v12安装入口标注需核实", "[需核实]" in mg)
    check("v12三处边界一致",
          "手机可做一半" in skm and "必须回电脑" in skm
          and "本阶段需要电脑" in tx("doubao-skill/stages/stage-8-analysis.md")
          and "必须回电脑" in tx("doubao-skill/stages/stage-7-data.md")
          and "预处理" in tx("doubao-skill/stages/stage-7-data.md"))
    check("v12工具表含手机对照", "手机上能用什么" in tx("doubao-skill/references/tools.md"))
    check("v12学校示例不绑定某校", "九江" not in tx("doubao-skill/references/tools.md"))
    # 合并单文件：生成到临时目录（不依赖项目外的 _发布包/，保证干净副本也能跑）
    bsp = ROOT / "doubao-skill" / "build_mobile_single.py"
    check("v12合并单文件生成器存在", bsp.exists())
    if bsp.exists():
        md_dir = new_tmp("v12mobile")
        try:
            tg = md_dir / "single.md"
            rg = run(["doubao-skill/build_mobile_single.py", "--out", str(tg)], 120)
            check("v12合并单文件可生成", rg.returncode == 0 and tg.exists(), (rg.stderr or "")[-200:])
            stext = tg.read_text(encoding="utf-8") if tg.exists() else ""
            check("v12合并单文件自包含",
                  all(s in stext for s in ("手机上做不了", "引导循环", "阶段 11：答辩准备", "concise-direct", "规则优先级")),
                  "len=%d" % len(stext))
            check("v12合并单文件规模合理", len(stext) > 50000, "chars=%d" % len(stext))
            check("v12合并版排除维护者文件", "Skill 行为自测用例" not in stext)
            rc2 = run(["doubao-skill/build_mobile_single.py", "--check", "--out", str(tg)], 60)
            check("v12合并版同步校验通过", rc2.returncode == 0, (rc2.stdout or "")[-150:])
        finally:
            if not rmtree_retry(md_dir):
                print("WARN 手机版构建临时目录未能删除（请手动清理）：" + str(md_dir))

    # ---- v1.58 身份/稳定陪伴/鼓励自然化/多词检索/90篇候选池/重点卡片/手机原生适配 ----
    companionship = ROOT / "core" / "companionship.md"
    skill_comp = SK / "references" / "companionship.md"
    check("v158陪伴文件存在", companionship.exists() and skill_comp.exists())
    ct = companionship.read_text(encoding="utf-8") if companionship.exists() else ""
    check("v158陪伴身份与边界", all(s in ct for s in ("不是老师", "虚拟伴侣", "脚手架", "情感依赖", "12356")))
    sct = skill_comp.read_text(encoding="utf-8") if skill_comp.exists() else ""
    check("v158skill陪伴口径", all(s in sct for s in ("不是老师", "虚拟伴侣", "脚手架", "情感依赖")))
    check("v158陪伴登记入规则与入口",
          "core/companionship.md" in cr and "core/companionship.md" in st and "companionship.md" in skm)
    for _nm, _txt in (("coach-rules", cr), ("coaching-protocol", cp), ("START", st), ("SKILL", skm)):
        check("v158去旧人格:" + _nm, not any(x in _txt for x in ("霸道总裁", "知心姐姐", "小奶狗")))
    check("v158START不自称导师", "毕业论文AI导师" not in st and "毕业论文 AI 导师" not in st and "AI 助手" in st)
    check("v158鼓励原则化自然化", "密度自然" in eg and "每轮至多一次肯定" not in eg)
    # 多词检索 + ≥90 候选池（文档口径 + 脚本开关）
    check("v158工作流多词与90池",
          all(s in las for s in ("--queries", "--source all", "--min 90", "至少 3 组", "候选池")))
    check("v158量表多词检索纪律", "量表检索纪律" in sl and "同义词" in sl and "OR" in sl and "AND" in sl)
    check("v158检索脚本多词开关", all(x in psrc for x in ('--queries', '--source', '--min', 'action="append"')))
    check("v158卡片脚本与菜单项",
          (ROOT / "tools" / "literature_cards.py").exists() and "literature_cards.py" in menu and "【10/15】" in menu)
    check("v158卡片接入网页指南且不增类型", "literature_cards.py" in wg and "文献笔记网页" in wg)
    check("v158手机交接单与原生做法", all(s in mg for s in ("设备交接单", "全球学术快报", "literature_cards")))

    # ---- v1.61 补丁集：手机边界修正/规则优先级/语气去人设命名/阈值争议/授权分级/进度卡更新块/AI 正文草稿边界 ----
    check("v161手机边界两处换电脑",
          all(s in skm for s in ("手机可全程完成", "手机可做一半", "必须回电脑", "手机起草 + 电脑定稿"))
          and "第 8 阶段只能做一半" not in skm)
    check("v161规则优先级入入口", "规则优先级" in skm and "coaching-protocol.md" in skm)
    for oldnm, newnm in (("gentle-sister", "gentle-patient"),
                         ("strict-ceo", "concise-direct"),
                         ("puppy", "lively-warm")):
        check("v161语气文件改名_" + newnm,
              (SK / "personalities" / (newnm + ".md")).exists()
              and not (SK / "personalities" / (oldnm + ".md")).exists())
    check("v161旧语气名清零(除版本历史)",
          all(oldnm not in p.read_text(encoding="utf-8")
              for p in SK.rglob("*.md") if p.name not in ("CHANGELOG.md", "README.md")
              for oldnm in ("strict-ceo", "gentle-sister", "puppy")))
    s8 = tx("doubao-skill/stages/stage-8-analysis.md")
    check("v161统计阈值标争议",
          "判读标准说明" in s8 and s8.count("阈值因教材而异，结合导师意见") == 4)
    s4 = tx("doubao-skill/stages/stage-4-scale.md")
    check("v161授权分级本地化", "授权与使用许可（分级处理）" in s4 and "以本校文件为准" in s4)
    check("v161进度卡更新块", "进度卡更新块" in skp and "过闸日期" in skp
          and "进度卡更新块" in tx("core/coach-rules.md"))
    an = tx("doubao-skill/references/academic-norms.md")
    check("v161AI正文草稿边界",
          all(s in an for s in ("AI 可做与不可做", "可编辑的论文正文草稿", "报告风险", "不可直接提交")))
    check("v161完整版草稿边界同步",
          "正文可起草、不可代交" in tx("core/coach-rules.md")
          and "可编辑草稿" in tx("core/coaching-protocol.md")
          and "可编辑草稿" in tx("workflows/writing-guide.md"))
    mg2 = tx("doubao-skill/references/mobile-guide.md")
    check("v161手机截断提示", "只读到一半" in mg2 and "分步喂" in mg2)
    check("v161完整版获取校验", "核对版本号与校验值" in tx("doubao-skill/references/tools.md"))

    # paper_search 纯函数 + collect 注入假 fetcher（离线、确定性）
    try:
        if str(ROOT / "tools") not in sys.path:
            sys.path.insert(0, str(ROOT / "tools"))
        import paper_search as psearch
        ql = psearch.split_queries(["AI dependence;AI attachment", "chatbot reliance", "AI attachment"])
        check("v158多词拆分去重", ql == ["AI dependence", "AI attachment", "chatbot reliance"], str(ql))
        check("v158DOI规范化",
              psearch.normalize_doi("https://doi.org/10.1/X") == "10.1/x"
              and psearch.normalize_doi("doi: 10.2/Y") == "10.2/y")
        bk = {}
        r_a = {"title": "Same Paper", "doi": "10.9/z", "cited": 5, "source_api": ["OpenAlex"]}
        r_b = {"title": "Same Paper", "doi": "10.9/Z", "cited": 9, "source_api": ["Semantic Scholar"]}
        psearch.add_record(bk, r_a); psearch.add_record(bk, r_b)
        merged_one = bk.get(psearch.dedup_key(r_a))
        check("v158跨源DOI去重合并", len(bk) == 1 and int(merged_one["cited"]) == 9
              and set(merged_one["source_api"]) == {"OpenAlex", "Semantic Scholar"}, "n=%d" % len(bk))
        _cnt = {"i": 0}
        def _fake_fetcher(source, query, offset, per_page, year):
            if offset:
                return []  # 第二页空 → 该"来源×词"穷尽
            out = []
            for _ in range(50):
                _cnt["i"] += 1
                out.append({"title": "Paper %d" % _cnt["i"], "doi": "10.7/%d" % _cnt["i"],
                            "cited": 1, "year": 2024, "source_api": [source]})
            return out  # 50 < per_page(100) → 首页即穷尽
        recs_p, stats_p = psearch.collect(["q1", "q2"], ["openalex", "semantic"], 90, 100,
                                          fetcher=_fake_fetcher, sleeper=lambda s: None, verbose=False)
        check("v158collect凑够90且去重", len(recs_p) >= 90 and len(stats_p) >= 2, "n=%d" % len(recs_p))
        check("v158不足目标非静默", "未达到目标" in psrc and "补" in psrc)
    except Exception as _pe:
        check("v158paper_search离线纯函数", False, repr(_pe))

    # literature_cards 端到端（UTF-8-sig + GBK、跨文件重复 DOI、强制精读入选）
    card_tmp = new_tmp("cards")
    try:
        import literature_cards as lc
        f_utf8 = card_tmp / "cand_utf8.csv"
        lines = ["标题,作者,年份,期刊/会议,DOI,链接,被引数,摘要,来源API,命中检索词,检索日期"]
        for i in range(1, 13):
            forced = "（强制精读）" if i == 12 else ""
            cited = 0 if i == 12 else (200 - i * 10)
            year = 2000 if i == 12 else 2020 + (i % 6)
            ab = "" if i == 12 else "摘要内容 AI dependence %d" % i
            lines.append("文献标题%d%s,作者%d,%d,期刊%d,10.5/%d,https://doi.org/10.5/%d,%d,%s,OpenAlex,q1,2026-09-17"
                         % (i, forced, i, year, i, i, i, cited, ab))
        f_utf8.write_text("\n".join(lines), encoding="utf-8-sig")
        gbk_lines = ["标题,作者,年份,期刊,DOI,被引数,摘要,是否精读",
                     "文献标题12（强制精读）,作者12,2000,期刊12,10.5/12,0,,是",
                     "文献标题1,作者1,2021,期刊1,10.5/1,190,摘要内容 AI dependence 1,"]
        f_gbk = card_tmp / "org_gbk.csv"
        f_gbk.write_bytes("\n".join(gbk_lines).encode("gb18030"))
        out_html = card_tmp / "cards.html"
        rc_c = run(["tools/literature_cards.py", str(f_utf8), str(f_gbk),
                    "--focus", "AI dependence", "--top", "5", "--output", str(out_html)], 90)
        check("v158卡片CLI退出0", rc_c.returncode == 0 and out_html.exists(), (rc_c.stderr or "")[-240:])
        htxt = out_html.read_text(encoding="utf-8") if out_html.exists() else ""
        check("v158卡片单文件无外网",
              all(x not in htxt for x in ("<script src=", "<link", "@import", "url(http", "https://cdn")),
              "len=%d" % len(htxt))
        check("v158卡片移动友好与可追溯",
              all(x in htxt for x in ("width=device-width", "application/json", "modal", "⭐",
                                      "不构成论文引用依据", "textContent")))
        papers_c, probs_c = lc.load_papers([f_utf8, f_gbk])
        check("v158卡片读GBK且跨文件去重", not probs_c and len(papers_c) == 12,
              "n=%d problems=%s" % (len(papers_c), probs_c))
        focus_c = lc.parse_focus("AI dependence")
        star_idx_c = lc.pick_stars(papers_c, focus_c, 5)
        data_c, cats_c = lc.build_payload(papers_c, star_idx_c, focus_c)
        forced_c = [d for d in data_c if "强制精读" in d["title"]]
        n_star = sum(1 for d in data_c if d["star"])
        check("v158卡片强制精读入选且篇数受控",
              len(forced_c) == 1 and forced_c[0]["star"] is True and n_star == 5, "stars=%d" % n_star)
    except Exception as _ce:
        check("v158literature_cards端到端", False, repr(_ce))
    finally:
        shutil.rmtree(card_tmp, ignore_errors=True)
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
