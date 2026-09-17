# -*- coding: utf-8 -*-
"""auto_stats 的统计实现包（v1.53.1 由单文件 2694 行拆分而来）。

分工：
  mathx       基础统计量与分布函数
  linalg      矩阵运算与特征分解
  dataio      数据读写、编码兼容、scales.txt 解析
  desc        描述统计、频数表、三线表导出
  reliability 信度（α/CITC/分半）与量表总分
  plots       碎石图、热图、简单斜率图（matplotlib 可选）
  efa         效度与探索性因子分析、Harman
  compare     差异检验（t/Welch/ANOVA/非参数）与卡方
  regress     相关、偏相关、回归、中介、调节

CLI 入口仍是 tools/auto_stats.py，用法完全不变。
"""
