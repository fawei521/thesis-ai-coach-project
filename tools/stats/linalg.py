# -*- coding: utf-8 -*-
"""线性代数与矩阵分解

行列式、矩阵求逆（高斯-约当）、最小二乘解、对称矩阵 Jacobi 特征分解、
幂迭代第一主成分。无第三方依赖。

本模块由 tools/auto_stats.py 拆分而来（v1.53.1），函数体逐行未改动。
"""

import math

# ============ 线性代数与矩阵分解 ============

def determinant(m):
    """方阵行列式（高斯消元，部分选主元）。"""
    n = len(m)
    a = [row[:] for row in m]
    det = 1.0
    for i in range(n):
        piv = max(range(i, n), key=lambda r: abs(a[r][i]))
        if abs(a[piv][i]) < 1e-12:
            return 0.0
        if piv != i:
            a[i], a[piv] = a[piv], a[i]
            det = -det
        det *= a[i][i]
        for r in range(i + 1, n):
            factor = a[r][i] / a[i][i]
            for c in range(i, n):
                a[r][c] -= factor * a[i][c]
    return det


def invert_matrix(A):
    """高斯-约当消元求逆矩阵"""
    n = len(A)
    M = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(A)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < 1e-12:
            return None
        M[col], M[pivot] = M[pivot], M[col]
        pivot_val = M[col][col]
        M[col] = [v / pivot_val for v in M[col]]
        for r in range(n):
            if r != col:
                factor = M[r][col]
                M[r] = [M[r][j] - factor * M[col][j] for j in range(2 * n)]
    return [row[n:] for row in M]


def solve_least_squares(X, y):
    """最小二乘：β=(X'X)^-1 X'y"""
    n = len(X)
    p = len(X[0])
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(p)] for a in range(p)]
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(p)]
    inv = invert_matrix(XtX)
    if inv is None:
        return None
    return [sum(inv[a][b] * Xty[b] for b in range(p)) for a in range(p)]


def _ols_beta(y, Xpred):
    """最小二乘系数，返回 [截距, 预测变量1系数, ...]。Xpred为预测变量列的列表。"""
    n = len(y)
    X = [[1.0] + [Xpred[j][i] for j in range(len(Xpred))] for i in range(n)]
    return solve_least_squares(X, y)


def _eigen_sym(A, tol=1e-11, max_sweep=100):
    """对称矩阵全部特征值/特征向量（循环Jacobi法，纯标准库）。
    返回 (特征值降序列表, 向量矩阵[行=变量,列=对应特征向量])。"""
    n = len(A)
    a = [row[:] for row in A]
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(max_sweep):
        off = math.sqrt(sum(a[p][q] ** 2 for p in range(n) for q in range(p + 1, n)))
        if off < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if abs(apq) < 1e-14:
                    continue
                app, aqq = a[p][p], a[q][q]
                tau = (aqq - app) / (2.0 * apq)
                if tau >= 0:
                    t = 1.0 / (tau + math.sqrt(1 + tau * tau))
                else:
                    t = 1.0 / (tau - math.sqrt(1 + tau * tau))
                c = 1.0 / math.sqrt(1 + t * t)
                s = t * c
                for i in range(n):  # 列旋转
                    aip, aiq = a[i][p], a[i][q]
                    a[i][p] = c * aip - s * aiq
                    a[i][q] = s * aip + c * aiq
                for i in range(n):  # 行旋转
                    api, aqi = a[p][i], a[q][i]
                    a[p][i] = c * api - s * aqi
                    a[q][i] = s * api + c * aqi
                for i in range(n):  # 累积特征向量
                    vip, viq = V[i][p], V[i][q]
                    V[i][p] = c * vip - s * viq
                    V[i][q] = s * vip + c * viq
    eig = [a[i][i] for i in range(n)]
    order = sorted(range(n), key=lambda i: -eig[i])
    eig_sorted = [eig[i] for i in order]
    vecs = [[V[r][order[j]] for j in range(n)] for r in range(n)]
    return eig_sorted, vecs


def _first_pc(R):
    """幂迭代求相关矩阵R的最大特征值与特征向量。"""
    p = len(R)
    vec = [1.0 / math.sqrt(p)] * p
    lam = 0.0
    for _ in range(1000):
        nv = [sum(R[a][b] * vec[b] for b in range(p)) for a in range(p)]
        norm = math.sqrt(sum(x * x for x in nv))
        if norm < 1e-12:
            break
        nv = [x / norm for x in nv]
        nl = sum(nv[a] * sum(R[a][b] * nv[b] for b in range(p)) for a in range(p))
        vec = nv
        if abs(nl - lam) < 1e-10:
            lam = nl
            break
        lam = nl
    return lam, vec
