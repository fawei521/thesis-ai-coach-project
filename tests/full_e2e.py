# -*- coding: utf-8 -*-
"""
thesis-ai-coach 全量端到端回归（测试金字塔 L7）。**只在仓库里**（v1.93 起 `tests/` 不随发布包分发）：
    python tests/full_e2e.py
覆盖：统计/清洗/样本量/模型图/文献脚本真实运行 + 文档-代码一致性 + 合规与事实断言。约需 3-5 分钟
（含 Bootstrap 5000、英文文献联网检索、缺库降级回归）。退出码 0 = 全部通过；非 0 = 有失败项（见 FAIL 行）。
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

# 临时目录与收尾清理的实现见 tests/e2e_tmp.py（从本壳原样搬出，逻辑一字未改）。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from e2e_tmp import BACKUP, new_tmp, rmtree_retry, dir_state, leftover_dirs, cleanup, _stray_files


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
    "case_19.py",  # v1.90 证据与核验纪律：三查/切片禁令/[需核实] 门禁
    "case_20.py",  # v1.91 宪法级严谨性条款＋可复跑的 A/B 对照实验
    "case_21.py",  # v1.93 发布包形态：开发文件不进包、学生要用的都在、export-ignore 名单同源
    "case_22.py",  # v1.94 成果交付纪律/外部技能/PPT底线与风格化/材料清单
    "case_23.py",  # v1.96 AI 腔体检/写作留痕/"不做降率"这条红线的形制
    "case_24.py",  # v1.98 原文可得性探测/题录双源核验/占位与标注分开数
    "case_25.py",  # v1.99 文献知识库：卡片Schema/只读检索/清点对账/两侧镜像/菜单分母同源
]

try:
    # ---- 断言主体已按主题切成顺序片段（见 tests/e2e_cases/）：原 612+ 条断言逐字节未改，
    # 仍按原顺序 exec 进本模块命名空间，语义与拆分前的单文件扁平脚本一致。
    # 这里**必须直接写 globals()**：v1.91 的 case_20 曾有一句 `_ns = {}` 顶掉循环命名空间、之后的片段全在空字典里跑（v1.93 加 case_21 才炸出来），守卫断言写在 case_20
    for _fn in FRAGMENTS:
        _p = ROOT / "tests" / "e2e_cases" / _fn
        exec(compile(_p.read_text(encoding="utf-8"), "tests/e2e_cases/" + _fn, "exec"), globals())


finally:
    cleanup()

fails = [x for x in results if not x[1]]
print(f"\n==== 共 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)} ====")

stray = _stray_files()
if stray:
    print("FAIL 测试临时文件残留：" + str(sorted(stray)))
    fails.append(("测试临时文件残留", False))
    print(f"==== 修正后：共 {len(results)} 项，失败 {len(fails)} ====")
sys.exit(1 if fails else 0)
