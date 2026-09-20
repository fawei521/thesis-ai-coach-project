# -*- coding: utf-8 -*-
"""开题就绪度自检的实现包（v1.94 起从 tools/proposal_readiness.py 拆出）。

CLI 入口与菜单第 23 项仍是 `tools/proposal_readiness.py`。拆包原因：入口文件贴住
`tests/size_ratchet.py` 的 220 行闸（实测正好 220），而报告体口径要新增一整层检查。
检查逻辑只在本包里写一遍，入口只做读文件、选口径、打印。
"""
