# -*- coding: utf-8 -*-
"""case_28 · 材料区卫生：只钉"与命名无关的形制"，分类本身交给 AI 判断。

为什么不钉类目名字（2026-09-22 同夹具 A/B 的实测结论）：预先规定四类槽位，得分反而低于自由分类版
（4–5/9 对 6/9），还逼出两种错——为找格子把某份笔记判成"被取代"塞进 `旧版/`（无依据），
以及一次性脚本四类都套不住、三格受试全部原地不动。**格子越硬，越容易削内容去 fit 格子。**

所以这里钉的是查得出的形状：一层一个入口、一份内容一处、移动不是删除、模板四节齐全、
判据要的形制词在、尺子自己咬得住。每条能植入的都已植入过。
"""
import subprocess as _sp28
import sys as _sys28

KB = tx("core/literature-kb.md")
AG = tx("AGENTS.md")
TPL = tx("templates/目录模板.md")
ENTRY = "一层只准有一个入口"

# ---- 一、入口唯一：一个知识点只有一个位置，这条也一样 ----
check("入口唯一这条在库纪律里只写一次", KB.count(ENTRY) == 1, "实际 %d 处（抄第二遍必漂）" % KB.count(ENTRY))
check("上面那道尺不空转（多抄一遍就该红）", (KB + "\n" + ENTRY).count(ENTRY) == 2)
check("AGENTS 那条同词同形、并指向纪律不另立名册",
      ENTRY in AG and "LAYOUT" in AG and "literature-kb.md" in AG and "第九" in AG)

# ---- 二、分类交给判断，但要写理由、不许硬猜 ----
check("分类由 AI 判断写进纪律", "你自己判断" in KB and "为什么这样分" in KB)
check("没依据就写待你定（防套格子式硬猜）", "待你定" in KB and "不许为了套格子硬猜" in AG)
check("移动不是删除两侧都写（AGENTS 与纪律一致）", "移动不是删除" in KB and "移动不是删除" in AG)
check("新建文件名不许写时效词", "本次/最新/终版/最终/新建/副本" in KB)
check("日期与分隔符口径写明", "YYYYMMDD" in KB and "`-` 或 `_`" in KB)

# ---- 三、模板四节齐全，且带着判据要的那个形制词 ----
for _sec in ("一、你要看的", "二、不用当", "三、磁盘实数", "四、这次动了什么"):
    check("目录模板四节齐全 · " + _sec, _sec in TPL, "缺这节 → 下一个 AI 没有入口")
_has_cur = lambda s: "当前版" in s
check("模板含判据要的形制词当前版", _has_cur(TPL))
check("模板缺词时这道断言会红（阴性）", not _has_cur(TPL.replace("当前版", "")))
check("第四节是可逆清单", "动了什么" in TPL and "删除 / 改名" in TPL)

# ---- 四、尺子自己得咬得住：实跑 folder_audit 的阴性自测 ----
_r28 = _sp28.run([_sys28.executable, "tools/folder_audit.py", "--selftest"],
                 cwd=str(ROOT), capture_output=True, timeout=120)
# 必须自己按 UTF-8 解：`text=True` 会拿系统 locale（中文 Windows 是 GBK）去解子进程的 UTF-8 输出，
# 中文全成乱码，"全部判据都咬住"匹配不上——rc=0 却判红（判据只能读自己解出来的文本）。
_out28 = (_r28.stdout or b"").decode("utf-8", "replace") + (_r28.stderr or b"").decode("utf-8", "replace")
# 结论句**不写条数**（09-23 那批改动加到十条时，旧句里的"八条"就成了说谎的字面量）：
# 这里改成核"清单与实现两边相等"，条数由尺子自己数。
check("folder_audit 每条判据都被自测咬住", _r28.returncode == 0 and "全部判据都咬住" in _out28,
      "rc=%s %s" % (_r28.returncode, _out28.strip()[-160:]))
_FA = tx("tools/folder_audit.py")
_doc_rules = set(re.findall(r"^  (R\d+) [红黄] ", _FA, re.M))
_code_rules = set(re.findall(r'hits\.append\(\(".", "(R\d+)"', _FA))
check("判据清单与实现两头相等（写文档没实现、或实现没写文档都红）",
      _doc_rules == _code_rules and len(_doc_rules) >= 10,
      "文档 %s ／代码 %s" % (sorted(_doc_rules), sorted(_code_rules)))
check("R9 与 R10 在案（临时区过期脚本／根一层放脚本）", {"R9", "R10"} <= _code_rules, str(sorted(_code_rules)))
check("夹具也配了 R9/R10（自测报告里能看见它们命中）",
      "'R9'" in _out28 and "'R10'" in _out28, _out28[-200:])
check("豁免只给当前版类：archived() 自己写明时效类照抓",
      "时效类" in _FA and "当前版类" in _FA and "R9" in _FA.split("def archived")[1].split("def walk")[0],
      "拆不干净就会退回整层豁免——临时区里放烂的脚本就再也查不到")
# 阳性侧：一份**刚写的**临时区脚本与一份干净目录，都不该被判红。
# 只测"抓得住坏"会养出一见脚本就红的尺，学生第二天就不敢用临时区了。
_ws102 = new_tmp("v102clean") / "我的工作区"
(_ws102 / "01-文献PDF").mkdir(parents=True)
(_ws102 / "01-文献PDF" / "新笔记.md").write_text("x", encoding="utf-8")
(_ws102 / "_scratch").mkdir()
(_ws102 / "_scratch" / "今天刚写的核验.py").write_text("#", encoding="utf-8")
_r102 = _sp28.run([_sys28.executable, "tools/folder_audit.py", str(_ws102)],
                  cwd=str(ROOT), capture_output=True, timeout=120)
_o102 = (_r102.stdout or b"").decode("utf-8", "replace")
check("刚写的临时脚本与单份笔记不该判红（阳性）",
      "R9" not in _o102 and "R10" not in _o102, _o102.strip()[-200:])
check("菜单第 30 项的帮助不抄条数（条数漂了就没人回来改）",
      "八条" not in tx("tools/menu_thesis.py") and "七条" not in _FA)
check("尺子挂在图形菜单第 30 项（学生双击就能跑）",
      "t_audit" in tx("tools/menu.py") and "【30/30】" in tx("tools/menu_thesis.py")
      and '"30"' in tx("tools/menu.py"))
check("跨副本双卡那条也在尺子上（今天这摊乱的根因）", "跨副本也咬住" in _out28)
