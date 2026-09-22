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
# 中文全成乱码，"八条全咬住"匹配不上——rc=0 却判红，坑在这（case_21 读 git 输出也是自己 decode 的）。
_out28 = (_r28.stdout or b"").decode("utf-8", "replace") + (_r28.stderr or b"").decode("utf-8", "replace")
check("folder_audit 八条形制全部咬住", _r28.returncode == 0 and "八条全咬住" in _out28,
      "rc=%s %s" % (_r28.returncode, _out28.strip()[-160:]))
check("尺子按维护者工具入册（不冒充学生工具）",
      "维护者工具" in tx("tools/folder_audit.py"))
check("跨副本双卡那条也在尺子上（今天这摊乱的根因）", "跨副本也咬住" in _out28)
