# -*- coding: utf-8 -*-
"""case_30 · 发版与记账的边界：说了"不发版"就必须当日登记。

判据就写在 `DEVELOPMENT.md` 阶段 G 第 2 步（一句话：学生或学生的 AI 读得到的东西变了，必须随下一次发版带走），
**不另立判据文档**——2026-09-28 用户否掉了单独那份，理由：这件事不该长成一堆文档。
"哪些路径算读得到"的名单唯一出处就是本片段的 `_STUDENT30`，DEVELOPMENT.md 指过来、不抄第二份。

**这把尺不判"该不该发版"**——那是维护者的决定，机器不替人拍板。它只查一件可验的事：
自最新 tag 以来，若提交动过"学生读得到"的路径，`02-维护决定.md` 里必须有不早于该提交的当日条目。
学生副本与包形态下 `维护档案/` 与 `.git` 都不存在（`export-ignore`），按 `case_15` 的先例跳过而不是崩。
"""
import re as _re30
import subprocess as _sp30

# 学生或学生的 AI 读得到的路径前缀（名单唯一出处＝本片段，判据文档里那句是同一件事的自然语言版）
# CHANGELOG.md 也在这：它随包分发、学生的 AI 会读——"维护决定（不发版）"那节正是靠它才被学生看到。
_STUDENT30 = ("START.md", "QUICKSTART.md", "README.md", "AGENTS.md", "CONSTITUTION.md", "CHANGELOG.md",
              "core/", "workflows/", "psychology/", "templates/", "doubao-skill/", "我的工作区/")

_arch30 = ROOT / "维护档案"
_git30 = ROOT / ".git"
_dec30 = _arch30 / "CHANGELOG" / "02-维护决定.md"


def _tag30():
    r = _sp30.run(["git", "-c", "core.quotepath=false", "describe", "--tags", "--abbrev=0"],
                  cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else ""


def _student_touches30(rng):
    """返回 [(短号, 日期)]：该区间内动过"学生读得到"路径的提交。"""
    r = _sp30.run(["git", "-c", "core.quotepath=false", "log", "--format=C|%H|%ad",
                   "--name-only", "--date=short", rng],
                  cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    hits, cur = [], None
    for ln in (r.stdout or "").splitlines():
        ln = ln.strip()
        if ln.startswith("C|"):
            _, h, d = ln.split("|", 2)
            cur = (h[:8], d)
        elif ln and cur:
            if any(ln.replace("\\", "/").startswith(p) for p in _STUDENT30):
                hits.append(cur)
                cur = None      # 一个提交只记一次
    return sorted(set(hits))


def _uncovered30(touches, decided):
    """每个动过学生侧的提交，都要有一条"当日或更晚"的维护决定条目罩着；罩不住的返回出来。"""
    if not decided:
        return list(touches)
    newest = max(decided)
    return [t for t in touches if t[1] > newest]


if not _arch30.is_dir() or not _git30.exists():   # P3（2026-10-03）：.git 在 worktree 里是文件，is_dir() 会把开发树判成副本
    # 包内／学生副本：判据文档与 git 历史都不在，但"未生效"这句话必须让学生读到
    _chg30 = tx("CHANGELOG.md")
    check("包内 CHANGELOG 写明『维护决定（不发版）』条目可能尚未进本包",
          "维护决定（不发版）" in _chg30 and "还没进你手上这个包" in _chg30,
          "in_pkg：学生读不到判据文档，至少要读得到'未生效'")
else:
    _txt30 = _dec30.read_text(encoding="utf-8") if _dec30.is_file() else ""
    _dates30 = _re30.findall(r"^\*\*(\d{4}-\d{2}-\d{2})", _txt30, _re30.M)
    _tagv = _tag30()
    _touches = _student_touches30(_tagv + "..HEAD") if _tagv else []
    _miss = _uncovered30(_touches, _dates30)
    check("动过学生侧却没发版时，02-维护决定.md 有罩得住的当日条目",
          not _miss, "自 %s 起动了学生侧的提交 %d 笔，未被罩住：%s"
                    % (_tagv, len(_touches), _miss or "无"))
    _dev30 = tx("DEVELOPMENT.md")
    check("判据就地写在 DEVELOPMENT.md 阶段 G，且不另立判据文档、不留指向已删文档的指针",
          "读得到的东西变了" in _dev30 and "随下一次发版带走" in _dev30
          and "维护决定-发版与记账的边界" not in _dev30
          and not (_arch30 / "维护决定-发版与记账的边界-2026-09-28.md").exists())
    # 阴性：尺子必须咬得住——把登记日期全抹掉，同一批提交就该被判红
    check("上面那道尺不空转（抹掉当日条目即判红）",
          bool(_uncovered30(_touches or [("fake", "2099-01-01")], []))
          and _uncovered30([("fake", "2099-01-01")], ["2020-01-01"]) == [("fake", "2099-01-01")],
          "罩不住=%s" % _uncovered30([("fake", "2099-01-01")], ["2020-01-01"]))
