# -*- coding: utf-8 -*-
"""case_27 · CHANGELOG 机制：正文一版一个文件（仓库侧），包内 `CHANGELOG.md` 是生成物。

改这套的三条实测病灶（也写在 `tools/changelog_build.py` 里）：加一版要动四处、手工搬运最贵；
"见 CHANGELOG vX"这类引用会跟着滚走的正文断链而没人发现；两个会话同时发版要抢同一个文件。

两棵树都要成立：`tools/changelog_build.py` 与 `维护档案/` 都带 export-ignore，**干净副本里没有它们**——
所以凡是"要跑生成器/要读版本详情目录"的核对都按开发树条件走（沿用 `case_21` 的 `.git` 条件写法：
条件必须落成代码，不能只写在注释里）。
"""
import re as _re27
import shutil as _sh27
import subprocess as _sp27
import sys as _sys27

_attr27 = [ln for ln in tx(".gitattributes").splitlines() if "export-ignore" in ln]
_ign27 = {ln.split()[0] for ln in _attr27}
check("补漏 生成器带 export-ignore（学生包里不该留着能改写版本史的东西）",
      "tools/changelog_build.py" in _ign27, str(sorted(_ign27)))
check("补漏 目录型名单仍各写两行（只写 /** 会漏出空目录）",
      {"维护档案", "维护档案/**"} <= _ign27 and {"tests", "tests/**"} <= _ign27, str(sorted(_ign27)))

_chg27 = tx("CHANGELOG.md")
_det_dir = ROOT / "维护档案" / "CHANGELOG" / "版本详情"
_dev27 = (ROOT / "tools" / "changelog_build.py").exists()

if _dev27:
    # ---------- 开发树：生成物必须等于生成结果 ----------
    _rb27 = run(["tools/changelog_build.py"])
    check("补漏 包内 CHANGELOG 等于生成结果（改了来源没重跑就判红）",
          _rb27.returncode == 0 and "同步" in (_rb27.stdout or ""), (_rb27.stdout or "")[-260:])
    _dets27 = sorted(p.stem for p in _det_dir.glob("*.md"))
    check("补漏 一版一个文件的详情都带主题行与发布日（缺格式拼不回）",
          bool(_dets27) and all(
              _re27.match(r"^\*\*v[\d.]+ .+\*\*$", p.read_text(encoding="utf-8").split("\n")[0].strip())
              and p.read_text(encoding="utf-8").split("\n")[1].startswith("> 发布：")
              for p in _det_dir.glob("*.md")), "目录 %s" % _dets27[:6])
    check("补漏 每个详情版本在索引表里都有一行（生成器自动补，漏了＝没跑）",
          not [v for v in _dets27 if "| **%s** |" % v not in _chg27],
          "索引缺 %s" % [v for v in _dets27 if "| **%s** |" % v not in _chg27])

    def _vkey27(v):
        return tuple([int(x) for x in _re27.findall(r"\d+", v)] + [0] * 4)

    _inpkg27 = _re27.findall(r"^\*\*(v[\d.]+) ", _chg27, _re27.M)
    check("补漏 包内留最新几版、滚出去的写明在哪本档案里",
          bool(_inpkg27) and "## 历史详情档案" in _chg27 and "未拼进本文件的" in _chg27,
          "包内详情 %s" % _inpkg27)

    # ---------- 档案指针由磁盘现算（以前手写、一滚出去就成孤儿） ----------
    def _ptr27(text):
        cited = set(_re27.findall(r"CHANGELOG-历史详情-[\d.v-]+\.md", text))
        disk = {p.name for p in (ROOT / "维护档案").glob("CHANGELOG-历史详情-*.md")}
        return sorted(disk - cited), sorted(cited - disk)

    _orphan27, _broken27 = _ptr27(_chg27)
    check("补漏 生成段与磁盘档案双向对齐（改名/删除当场被抓）",
          not _orphan27 and not _broken27, "孤儿%s 坏链%s" % (_orphan27, _broken27))
    _o2, _b2 = _ptr27(_chg27.replace("CHANGELOG-历史详情-v1.92.md", "CHANGELOG-历史详情-v9.99.md", 1))
    check("补漏 上面那道尺不空转（改名一次同时出坏链与孤儿）",
          _b2 == ["CHANGELOG-历史详情-v9.99.md"] and "CHANGELOG-历史详情-v1.92.md" in _o2,
          "孤儿%s 坏链%s" % (_o2, _b2))

    # ---------- "见 CHANGELOG vX"这类引用不许跟着搬运断链 ----------
    def _dangling(text_by_file):
        have = set(_re27.findall(r"^\*\*(v[\d.]+) ", _chg27, _re27.M))
        return ["%s→%s" % (rel, ver) for rel, body in text_by_file.items()
                for ver in _re27.findall(r"CHANGELOG\s+(v[\d.]+)", body) if ver not in have]

    _scan27 = {rel: tx(rel) for rel in ("ROADMAP.md", "README.md", "PROJECT_PLAN.md",
                                        "AGENTS.md", "QUICKSTART.md", "START.md")}
    check("补漏 别的文档不许引用已滚出包内的版本详情（断链即红）",
          not _dangling(_scan27), "断链：%s" % _dangling(_scan27))
    check("补漏 断链这条尺不空转（不存在的版本必须被抓）",
          "AGENTS.md→v9.99" in _dangling({"AGENTS.md": "详见 CHANGELOG v9.99"}))

    # ---------- 阴性：改了来源不重跑，--check 必须红 ----------
    # 篡改要打在**真的被拼进包内的那一版**上：打在最老那版（已滚出包外）不改输出＝尺子空转，第一次就这么骗过我。
    _tmp27 = ROOT / "tests" / ".tmp_e2e" / "chg27"
    _sh27.rmtree(_tmp27, ignore_errors=True)
    _tmp27.mkdir(parents=True)
    _sh27.copytree(str(ROOT / "维护档案" / "CHANGELOG"), str(_tmp27 / "维护档案" / "CHANGELOG"))
    (_tmp27 / "CHANGELOG.md").write_text(_chg27, encoding="utf-8")
    _newest27 = max(_inpkg27, key=_vkey27)
    _probe27 = ('import sys,pathlib;sys.path.insert(0,r"%s");sys.argv=["x"];'
                "import changelog_build as cb;cb.ROOT=pathlib.Path(r'%s');"
                "cb.SRC=cb.ROOT/'维护档案'/'CHANGELOG';cb.OUT=cb.ROOT/'CHANGELOG.md';"
                "p=cb.SRC/'版本详情'/(r'%s.md');t=p.read_text(encoding='utf-8');"
                "p.write_text(t+chr(10)+'- 偷偷加的一条（没重跑生成器）'+chr(10),encoding='utf-8');"
                "sys.exit(cb.main())") % (str(ROOT / "tools"), str(_tmp27), _newest27)
    _rp27 = _sp27.run([_sys27.executable, "-c", _probe27], capture_output=True, text=True,
                      encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                      timeout=120)
    check("补漏 改了详情文件却不重跑生成器＝--check 判红（尺子不空转）",
          _rp27.returncode != 0 and "不同步" in (_rp27.stdout or ""),
          "打的那版=%s｜%s" % (_newest27, (_rp27.stdout or _rp27.stderr or "")[-200:]))
    _sh27.rmtree(_tmp27, ignore_errors=True)
else:
    # ---------- 干净副本（发布包）：生成器与来源按设计都不在，这里只核"确实不在" ----------
    check("补漏 干净副本不含生成器与版本详情来源（按设计不进包，条件已落成代码）",
          not _dev27 and not _det_dir.exists())
