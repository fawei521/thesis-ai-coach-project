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
if (ROOT / ".git").exists():  # 只在有仓库的形态跑：`git archive` 要读仓库；阶段 G 的验证副本没有 .git，整段跳过
    import io, tarfile, fnmatch
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
              "core/coach-rules/tones.md", "core/coach-rules/emergency.md",
              "workflows/literature-auto-search.md", "tools/menu.py", "tools/setup_workspace.py",
              "tools/stats/mediation.py", "templates/progress-template.md", "templates/检索记录模板.md",
              "psychology/scale-library.md", "我的工作区/先读我.md", "我的工作区/09-导师沟通记录/把导师沟通记录放这里.txt",
              "doubao-skill/SKILL.md", "doubao-skill/validate.py", "doubao-skill/thesis-ai-coach-手机版.md"]
    check("v193学生要用的都在包里", not [m for m in must93 if m not in names93],
          str([m for m in must93 if m not in names93])[:200])
    # 上限随内容动，但**每次抬高都要在 CHANGELOG 写出为什么**——这条闸的全部意义是拦"顺手塞东西进包"。
    # v1.93 定 2_200_000（当时 2074 KB）；v1.94 加 5 份学生侧文档（成果交付/外部技能各两份 + 材料清单）
    # 实测 148 件 / 2154 KB，抬到 2_350_000（≈ 余量 190 KB）。件数上限 160 未动。
    # v1.99 件数 160 → **170**：文献知识库随包新增 8 件，全是学生侧要用的东西，不是维护者文件——
    #   core/literature-kb.md、workflows/knowledge-base-setup.md、doubao-skill/references/literature-kb.md、
    #   templates/文献卡片模板.md、tools/kb_search.py、tools/kb_index.py、tools/menu_kb.py、
    #   我的工作区/10-知识库/把文献卡片放这里.txt。实测 166 件 / 2282 KB（体积仍在 2_350_000 内）。
    # ⚠ 这条量的是 `git archive HEAD`，**提交前跑全量它看的是上一版**：v1.99 发版时就这样躲过去一次
    #   （提交前 937 全绿、提交后立刻红）。所以发版顺序里"打完 tag 必须再跑一遍全量"是硬步骤，见 P28。
    # 09-22 实测：HEAD 在 45fd6d5 时已 167 件 / 2298 KB（超 2_350_000 ≈ 2294 KB），
    #   106336b 加进 `tools/folder_audit.py`（11 KB）＋ `templates/目录模板.md`（2 KB）后 169 件 / 2312 KB。
    #   抬到 2_420_000（≈ 余量 105 KB）：新增的都是学生侧要用的东西，不是维护者文件塞进包——
    #   维护者侧的 `tools/changelog_build.py` 已由 .gitattributes export-ignore 挡在包外。
    check("v194包体积上限随内容上调并写明理由",
          100 <= len(names93) <= 170 and sum(m.size for m in _mem93) < 2_420_000,
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

    # ================= 门禁凭证审计（2026-09-20 加）=================
    # 要治的是"沉默式跳闸"：动了该跑全量的东西、只跑秒级就说通过了——这种事本身不留痕迹，
    # 于是只能靠人盯着。这里把"跑过"变成一个**没跑就凑不出来的字符串**，事后任何一轮回归都能追查到。
    # 判据的 L1 路径**不另抄一份**：现读 DEVELOPMENT.md 阶段 T 那张表（和 consistency_check 读
    # .gitattributes、setup_workspace.GENERATED 被两处复用是同一个套路——名单只有一份）。
    def l1_globs_from_table(dev_text):
        """取第二列含 `**全量**` 的表格行，收回格一里用反引号包着的路径。"""
        globs = []
        for line in dev_text.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or "**全量**" not in cells[1]:
                continue          # "smoke 即可；收尾补一次全量"那行没有粗体，天然被排除
            globs += [g for g in re.findall(r"`([^`]+)`", cells[0])
                      if "/" in g or g.endswith((".py", ".md"))]
        return sorted(set(globs))

    def cert_missing(table_globs, commits):
        """commits: [(hash, parent_full, msg, files)]。返回没带凭证的 commit 短描述。"""
        def hit(f):   # fnmatch 语义就够：表里写的是 tools/**.py、core/**.md 这种
            return any(fnmatch.fnmatch(f, g) or f.startswith(g.rstrip("/*/") + "/") for g in table_globs)
        bad = []
        for h, par, msg, files in commits:
            touched = sorted({f for f in files if hit(f)})
            if not touched:
                continue
            m = re.search(r"\[门禁凭证\] head=(\S+) smoke=\S+ full=(\d+)/(\d+)", msg)
            if not m:
                bad.append("%s 动了 L1(%s) 却没有凭证" % (h[:7], ",".join(touched[:3])))
            elif not (par.startswith(m.group(1)) and len(m.group(1)) >= 7):
                bad.append("%s 凭证里的 head=%s 对不上父提交 %s（＝凭证不是这一笔之前跑的）"
                           % (h[:7], m.group(1), par[:7]))
            elif m.group(2) != m.group(3):
                bad.append("%s 凭证写着 full=%s/%s，不是零失败" % (h[:7], m.group(2), m.group(3)))
        return bad

    _tab21 = [p for p in ("DEVELOPMENT.md",) if (ROOT / p).exists()]
    if _tab21:
        _g21 = l1_globs_from_table(tx("DEVELOPMENT.md"))
        check("定闸表能解析出 L1 路径", len(_g21) >= 8, "%d 条：%s" % (len(_g21), _g21))
        # 锚点＝**引入"门禁凭证"这个字符串的那个 commit**（git -S 找得到，就不必写死 hash、也不必给历史补凭证）
        _anc_p = subprocess.run(["git", "-c", "core.quotepath=false",
                                 "log", "-S", "门禁凭证", "--format=%H", "--reverse"],
                                cwd=str(ROOT), capture_output=True, timeout=120)
        _anc = _anc_p.stdout.decode("utf-8", "replace").split()[:1]
        _rng = ("%s..HEAD" % _anc[0]) if _anc else ""
        _lst = subprocess.run(["git", "rev-list", _rng], cwd=str(ROOT), capture_output=True,
                              timeout=120).stdout.decode("utf-8", "replace").split() if _rng else []
        _cs = []
        for _h in _lst:
            _meta = subprocess.run(["git", "show", "-s", "--format=%H%x00%P", _h],
                                   cwd=str(ROOT), capture_output=True, timeout=60)
            _hh, _par = (_meta.stdout.decode("utf-8", "replace").split("\x00") + [""])[:2]
            _msg = subprocess.run(["git", "show", "-s", "--format=%B", _h], cwd=str(ROOT),
                                  capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
            _fl = subprocess.run(["git", "-c", "core.quotepath=false",       # 不开这个，中文路径会变成
                                  "show", "--name-only", "--format=", _h],   # "\347\273\264…" 而谁也匹配不上
                                 cwd=str(ROOT), capture_output=True, timeout=60)
            _cs.append((_hh, _par.split()[0] if _par.strip() else "", _msg,
                        [x.strip().replace("\\", "/") for x in _fl.stdout.decode("utf-8", "replace").splitlines()
                         if x.strip()]))
        # 凭证豁免是一份**冻结的历史债清单**（和 tests/size_baseline.txt 同一个路子）：每笔写明
        # "当时为什么凑不出零失败"，且必须真在历史里、确实被这把尺点过名；表外的新违规照抓。
        # 为什么非要有它：这条尺要求 `full=N/N`，可历史上一旦留下一笔不合规，往后**每一笔**
        # 都再也拿不到零失败的凭证——2026-09-22 实测就是这个死锁（两笔在前，第三笔发不出去），
        # 闸把自己锁死了。改历史会让凭证变成编出来的数，所以选择登记，不选择抹平。
        _CERT_WAIVERS = {
            "45fd6d5": "动了 L1 没带凭证；当时包体积已超上限（HEAD 实测 167 件/2298 KB > 2294 KB），跑不出零失败",
            "106336b": "凭证写 full=978/980 非零失败——提交者没先读第三条件；事后补一个没跑过的数就是造假，只能登记",
        }
        _unwaived = cert_missing(_g21, _cs)
        _bad = [b for b in _unwaived if not any(b.startswith(h + " ") for h in _CERT_WAIVERS)]
        check("动了L1的commit都带门禁凭证（历史债按冻结清单豁免）",
              not _bad, ("；".join(_bad))[:300] or "锚点后 %d 笔，除登记在案的 %d 笔历史债外全部合规"
                        % (len(_cs), len(_CERT_WAIVERS)))
        # 豁免清单自己也不许空转：每条必须对得上一笔**真实**违规（hash 在范围内且确实被点过名），
        # 所以拿它藏新账、或塞一条编造的 hash，这条断言会红。
        _waiv_stale = [w for w in _CERT_WAIVERS
                       if not any(c[0].startswith(w) for c in _cs)
                       or not any(x.startswith(w + " ") for x in _unwaived)
                       or not _CERT_WAIVERS[w].strip()]
        check("凭证豁免清单不养闲条目（每条＝一笔真实违规＋一句理由）",
              not _waiv_stale, "对不上真实违规或没写理由：%s" % _waiv_stale)
        # 尺子不许空转：同一把函数喂一份"改了 tools 却没凭证"的假清单，必须抓到
        _fake = [("abcd1234" * 5, "ffff9999" * 5, "修了个统计脚本", ["tools/auto_stats.py", "README.md"])]
        check("凭证审计抓得到植入", len(cert_missing(["tools/**.py", "README.md"], _fake)) == 1,
              "对植入无反应＝这条断言是假的")
        _fake2 = [("abcd1234" * 5, "ffff9999" * 5,
                   "修了个统计脚本\n[门禁凭证] head=ffff999 smoke=9/9 full=780/780",
                   ["tools/auto_stats.py"])]
        check("凭证审计放过合规的", cert_missing(["tools/**.py"], _fake2) == [], "合规清单被误判＝天天误报")
