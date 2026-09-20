# -*- coding: utf-8 -*-
"""发布包形态核对（v1.93 · 待办 P16）----
full_e2e.py 顺序片段 21/21（由壳按序 exec，不单独运行）。

盯的是**发出去那份包里到底有什么**，不是仓库里有什么：
- 开发文件不得进包：`tests/` 与 `DEVELOPMENT.md`。前者是回归断言与**故意编出来的假数字夹具**
  （`rigor_experiment.py` 里那些 α/N 是用来考 AI 的靶子，长得却和真数据一样），
  后者是维护者的九阶段门——学生的 AI 通读文件夹时会把两者当规则或当数据引用；
- 学生要用的必须在：入口文档、core/、workflows/、tools/、templates/、psychology/、
  `我的工作区/` 预置、启动器、轻量版子包与手机合并单文件；
- export-ignore 名单只有一份（`.gitattributes`）：这里与 `consistency_check.py` 都从它解析，改哪边都能被发现。

只在有 `.git` 的形态跑（要读仓库）；包内副本没有 .git，整段自然跳过。
**不落盘**：`git archive --format=tar` 直接读进内存——在 `tests/.tmp_e2e/` 留一个 zip 会被收尾自检判成临时文件残留。
"""
if True:  # 容器不产生作用域，与其余片段一致
    import io, tarfile
    # `--worktree-attributes`：包形态由**工作树里的 .gitattributes** 决定，改了打包规则还没提交的当口就能验
    # （正式产物从 tag 打，那时工作树是干净的，两者结果一致）。
    _ar93 = subprocess.run(["git", "archive", "--worktree-attributes",
                            "--prefix=thesis-ai-coach-project/", "--format=tar", "HEAD"],
                           cwd=str(ROOT), capture_output=True, timeout=180)
    check("v193发布包能打出来（tar 流进内存）", _ar93.returncode == 0 and len(_ar93.stdout) > 10000,
          (_ar93.stderr or b"")[:150].decode("utf-8", "replace"))
    _pfx = "thesis-ai-coach-project/"
    _tf93 = tarfile.open(fileobj=io.BytesIO(_ar93.stdout)) if _ar93.returncode == 0 else None
    _mem93 = _tf93.getmembers() if _tf93 else []
    _map93 = {m.name[len(_pfx):]: m for m in _mem93 if m.isfile()}
    names93 = list(_map93)
    dirs93 = [m.name[len(_pfx):] for m in _mem93 if m.isdir()]

    # 判定函数只写一次：既核对真包，也用它验"尺子抓得到植入"
    def dev_leaks(ns):
        return [n for n in ns if n.startswith("tests/") or n in ("DEVELOPMENT.md", "维护档案")]
    check("v193开发文件不在发布包里", not dev_leaks(names93), str(dev_leaks(names93))[:160])
    check("v193同一把尺量植入要能抓到",
          dev_leaks(["tests/full_e2e.py", "DEVELOPMENT.md", "维护档案"]) ==
          ["tests/full_e2e.py", "DEVELOPMENT.md", "维护档案"], "尺子对植入无反应＝本条空转")
    check("v193没有只留空目录的残留",
          not [d for d in dirs93 if d.rstrip("/").rsplit("/", 1)[-1] in ("tests", "维护档案")],
          str([d for d in dirs93 if "tests" in d])[:120])

    must93 = ["START.md", "QUICKSTART.md", "README.md", "CONSTITUTION.md", "AGENTS.md", "CHANGELOG.md",
              "LICENSE", "requirements.txt", "启动工具箱.bat", ".gitattributes", ".gitignore",
              "core/coach-rules.md", "core/evidence-rigor.md", "core/coach-rules/stage-playbook.md",
              "workflows/literature-auto-search.md", "tools/menu.py", "tools/setup_workspace.py",
              "tools/stats/mediation.py", "templates/progress-template.md", "templates/检索记录模板.md",
              "psychology/scale-library.md", "我的工作区/先读我.md", "我的工作区/09-导师沟通记录/把导师沟通记录放这里.txt",
              "doubao-skill/SKILL.md", "doubao-skill/validate.py", "doubao-skill/thesis-ai-coach-手机版.md"]
    check("v193学生要用的都在包里", not [m for m in must93 if m not in names93],
          str([m for m in must93 if m not in names93])[:200])
    check("v193包确实瘦下来了（件数与解压体积都盯）",
          100 <= len(names93) <= 160 and sum(m.size for m in _mem93) < 2_200_000,
          "件数=%d 解压=%d KB" % (len(names93), sum(m.size for m in _mem93) // 1024))

    def _read93(name):
        _f = _tf93.extractfile(_map93[name])
        return _f.read().decode("utf-8", "ignore") if _f else ""
    check("v193假数字实验夹具一个字节都不外发",
          not [n for n in names93 if n.endswith(".md")
               and any(k in _read93(n) for k in ("NRS-20", "TFD-21", "GDS-7"))],
          "包内文档出现了只用于考 AI 的合成量表名")

    attr93 = tx(".gitattributes").replace("\r\n", "\n").split("\n")
    ign93 = {l.split()[0] for l in attr93 if l.endswith("export-ignore") and not l.startswith("#")}
    check("v193export-ignore 名单齐且目录各写两行",
          {"tests/**", "tests", "DEVELOPMENT.md", "维护档案/**", "维护档案"} <= ign93
          and all((p in ign93 and p.rstrip("/*") in ign93) for p in ("tests/**", "维护档案/**")),
          str(sorted(ign93)))
    check("v193一致性自检从同一份名单取豁免",
          "REPO_ONLY" in tx("tests/consistency_check.py")
          and ".gitattributes" in tx("tests/consistency_check.py"))
    check("v193阶段 G 已改成双产物口径",
          "补回" in tx("DEVELOPMENT.md") and "export-ignore" in tx("DEVELOPMENT.md"))
