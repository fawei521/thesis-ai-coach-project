# -*- coding: utf-8 -*-
"""case_34 · 台账断更闸：加了断言就得记账，"哪一版没记"由机器数（待办 P41）。

**为什么要有这一片**：`tests/e2e-test.md` 是断言的账本，可从 v1.99 起断了六版——测试97 停在 v1.98、
测试98 直接跳到 v1.105，中间那 224 条断言（2026-10-02 现量，逐版读数在
`维护档案/e2e-test-断更补记-v1.99至v1.105.md`）没有测试号可查。`case_15` 那两条只查"编号都在索引里、
不重不漏"，它量的是**行的形状**，不是"版本有没有被行罩住"，所以整版缺席永远不红。
补记把旧账接上，这一片负责让**再断一版当场露头**。

**判据只有一条不变量**：自台账自己声明的"逐版覆盖起点"起，凡在 `tests/` 下新增过断言名的 tag，
索引里必须至少有一行的用例列点名它。抽名字与算差集都在本片里现做，一个数字都不抄。

**行里的"+N"不参与对账**：那是登记当时的读数，改判据的人不一定会回来更新它。拿它对账只会养出
一见数字不符就红、于是没人敢改判据的尺——所以本片只判"点名了没有"。

五件必备，顺序不许倒（先验抽取器量得到东西，再验真账，最后验它不空转、也不冤枉）：
  ① 起点那句话在位、且指的是一个真实 tag——**删掉这句闸判红**，不许静默把整片让给"全绿"；
  ② 抽取器量得到东西：起点之后确实量到"新增过断言"的版本；
  ③ 真账过：现量没有新增过断言却没人点名的版本；
  ④ 阴性两格：抹掉最新那版的索引行 → 它立刻被点出来；把所有行的版本号遮掉 → 名单恰好罩住
     全部有新增的版本（证明名单是算出来的，不是写死的）；
  ⑤ 阳性一格：把起点推到最新 tag → 名单立刻空，**红来自差集而不是名单**。

只在开发树跑：学生副本既没有 `.git` 也拿不到历史 tag，按 `case_30` 的先例跳过而不是崩。
变量前缀 _h106c*：片段与壳共用 globals，撞名会静默改掉后面片段的运行环境（case_20 的教训）。
"""
import re as _re34
import subprocess as _sp34
from collections import Counter as _Cnt34

# 断言名＝tests/ 下每个断言调用（登记函数在 full_e2e.py 里）的第一个字符串字面量，f-string 前缀一并吃进正则。
# 截到 70 字：两侧同一把刀，既不因整句改写而算成"新增"，也不短到让不同判据撞成同名。
_PAT34 = r'''check\([ \t]*[a-zA-Z]*["'][^"']+["']'''
_ANCHOR34 = _re34.compile(r"逐版覆盖起点：(v\d+(?:\.\d+)+)")
_VER34 = _re34.compile(r"v\d+(?:\.\d+)+")


def _git34(args):
    return _sp34.run(["git", "-C", str(ROOT)] + args, capture_output=True) \
        .stdout.decode("utf-8", "replace")


def _key34(v):
    return tuple(int(x) for x in v.lstrip("v").split("."))


def _tags34():
    ts = [t for t in _git34(["tag", "--list", "v1.*"]).split() if _re34.fullmatch(r"v[\d.]+", t)]
    return sorted(ts, key=_key34)


def _names34(ref):
    """该 ref 下 tests/ 里的全部断言名。一次 git grep 量完，不按文件开进程。"""
    out = _git34(["grep", "-H", "-o", "-E", "-e", _PAT34, ref, "--", "tests/"])
    names = []
    for ln in out.splitlines():
        parts = ln.split(":", 2)
        if len(parts) != 3:
            continue
        m = _re34.search(r'''["'](.+)''', parts[2])
        if m:
            names.append(_re34.sub(r"\s+", " ", m.group(1))[:70])
    return names


def _delta34(tags):
    """{tag: 比上一个 tag 新增几条断言名}——滚动比较，同一个 ref 只取一次。"""
    out, prev = {}, _Cnt34()
    for t in tags:
        cur = _Cnt34(_names34(t))
        out[t] = sum((cur - prev).values())
        prev = cur
    return out


def _rowver34(row):
    """索引行的"引入版本"＝**用例列**里第一个左括号之后的第一个版本号。
    只认用例列：正文里提到别版是叙述，文件名里带版本号（补记档案那个名字就有 v1.99）更不是记账。"""
    cols = row.split("|")
    seg = cols[2] if len(cols) > 2 else row
    i = seg.find("（")
    m = _VER34.search(seg[i:] if i >= 0 else seg)
    return m.group(0) if m else ""


def _covered34(ledger):
    return {_rowver34(ln) for ln in ledger.splitlines() if ln.startswith("| 测试")} - {""}


def _missing34(ledger, delta, anchor):
    """缺账名单＝起点之后新增过断言、却没有索引行点名它的版本。起点之前不追溯。"""
    cov = _covered34(ledger)
    return [(t, delta[t]) for t in sorted(delta, key=_key34)
            if _key34(t) >= _key34(anchor) and delta[t] > 0 and t not in cov]


if not (ROOT / ".git").exists():      # P3（2026-10-03）：worktree 的 .git 是文件不是目录，is_dir() 会把开发树当副本
    # 副本里既无 git 也无 维护档案/：判不了账，但"判不了"这件事本身要留一行读数
    check("断更闸只在开发树跑：副本没有 git 历史时跳过而不是崩", True, "无 .git，按 case_30 先例跳过")
else:
    _led34 = tx("tests/e2e-test.md")
    _all34 = _tags34()
    _hit34 = _ANCHOR34.search(_led34)
    _anch34 = _hit34.group(1) if _hit34 else ""
    _okanch = _anch34 in _all34
    check("台账自己声明了逐版覆盖起点，且它是个真实 tag（删掉这句判红，不许静默全绿）",
          _okanch, "起点解析成 %r，它在 tag 里吗：%s" % (_anch34, _okanch))

    if _okanch:
        _i0 = _all34.index(_anch34)
        _win34 = _all34[max(0, _i0 - 1):]      # 起点前一版是它的差集基线
        _dl34 = _delta34(_win34)
        _elig = [t for t in _win34 if t != _win34[0] and _dl34[t] > 0]
        check("抽取器量得到东西：起点之后确实量到有新增断言的版本",
              len(_elig) > 1, "窗口 %s…%s 量到 %d 版有新增" % (_win34[0], _win34[-1], len(_elig)))
        _miss = _missing34(_led34, _dl34, _anch34)
        check("断更闸·真账：起点之后每一版新增的断言都被索引行点名",
              not _miss, "缺账 %d 版：%s" % (len(_miss), _miss or "无"))
        _newest = _elig[-1]
        _cut34 = "\n".join(ln for ln in _led34.splitlines()
                           if not (ln.startswith("| 测试") and _rowver34(ln) == _newest))
        _m2 = _missing34(_cut34, _dl34, _anch34)
        check("断更闸不空转·抹掉最新那版的索引行，那一版立刻被点出来",
              [t for t, _n in _m2] == [_newest], "抹掉 %s 之后名单＝%s" % (_newest, _m2))
        _mask34 = "\n".join(ln.replace("（v", "（x") if ln.startswith("| 测试") else ln
                            for ln in _led34.splitlines())
        _m3 = [t for t, _n in _missing34(_mask34, _dl34, _anch34)]
        check("断更闸不空转·遮掉所有行的版本号，名单恰好罩住全部有新增的版本而不是写死那一串",
              _m3 == _elig and len(_m3) > 1, "遮掉后名单=%s，应有=%s" % (_m3, _elig))
        _m4 = _missing34(_led34, _dl34, _all34[-1])
        check("断更闸·阳性：起点推到最新 tag，缺账名单就该空（红来自差集不是名单）",
              not _m4, "起点=%s 时名单=%s" % (_all34[-1], _m4))
        _arch34 = ROOT / "维护档案" / "e2e-test-断更补记-v1.99至v1.105.md"
        _refs34 = [ln for ln in _led34.splitlines()
                   if ln.startswith("| 测试") and "断更补记" in ln]
        check("补记正文在位，且索引指过去的每一行都落得到（断链或藏进别处即红）",
              _arch34.is_file() and len(_refs34) == 7,
              "档案存在=%s，指向它的索引行=%d 行（补记七行：97a–97f、98b）" % (_arch34.is_file(), len(_refs34)))
