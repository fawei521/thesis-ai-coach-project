# -*- coding: utf-8 -*-
"""相关/回归/中介/调节/多元异常值的历史入口。

本文件原为 700 行的统计实现（v1.53.1 由 auto_stats.py 拆出，v1.73 起撞到 700 行上限）。
拆分批1 大文件拆分后按主题搬到 5 个模块，每个 ≤220 行：

  correlation   Pearson/Spearman 相关矩阵、偏相关
  regression    多元线性回归、VIF 共线性、残差 DW/SW 诊断
  mediation     Bootstrap 中介（模型4/6）
  moderation    调节效应（模型1，简单斜率与斜率图）
  outliers      Mahalanobis D² 多元异常值筛查

函数体逐行未改动。此处只做再导出，让既有文档引用与 `from stats.regress import X`
的写法继续可用；新代码请直接 import 对应主题模块。
"""

from .correlation import correlation_matrix, partial_correlation_analysis
from .mediation import mediation_analysis
from .moderation import moderation_analysis
from .outliers import mahalanobis_outliers
from .regression import linear_regression
