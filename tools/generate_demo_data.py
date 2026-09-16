#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_demo_data.py — 生成一份结构真实的问卷演示数据（供练手和测试，勿用于真实研究）

用途：
  在还没收回真实问卷时，用它生成一份“已知答案”的模拟数据，
  跑通 auto_stats.py 的反向计分、信度、共同方法偏差、相关、回归全流程。
  数据内置“AI情感依赖(X)→孤独感(M)→NSSI(Y)”的链式相关结构，
  其中 X 含2道反向题、Y 含1道反向题。

用法：
  python tools/generate_demo_data.py
  python tools/generate_demo_data.py --n 150 --seed 20260917 --outdir tests/test-data

输出（默认当前目录）：
  demo_survey.csv            模拟问卷原始数据（题目级）
  demo_scales.txt            配套量表配置（含反向题标记）

注意：这是模拟数据，只能用于学习和测试工具，严禁当作真实研究结果写进论文。
"""
import csv
import random
import argparse
from pathlib import Path


def generate(n=150, seed=20260917):
    random.seed(seed)

    def z():
        return random.gauss(0, 1)

    # 三个相关的潜变量（标准化），构成 X→M→Y 的链式结构
    zx = [z() for _ in range(n)]
    zm = [0.30 * zx[i] + 0.954 * z() for i in range(n)]
    zy = [0.32 * zm[i] + 0.22 * zx[i] + 0.921 * z() for i in range(n)]

    def likert(v):
        x = int(round(v * 0.82 + 3))
        return max(1, min(5, x))

    rows = []
    for i in range(n):
        # X 5题，X2、X4反向
        X = [likert(zx[i] + random.gauss(0, 0.42)) for _ in range(5)]
        X[1] = 6 - likert(zx[i] + random.gauss(0, 0.42))
        X[3] = 6 - likert(zx[i] + random.gauss(0, 0.42))
        # M 4题，无反向
        M = [likert(zm[i] + random.gauss(0, 0.42)) for _ in range(4)]
        # Y 5题，Y3反向
        Y = [likert(zy[i] + random.gauss(0, 0.42)) for _ in range(5)]
        Y[2] = 6 - likert(zy[i] + random.gauss(0, 0.42))
        rows.append([random.randint(95, 420)] + X + M + Y)

    header = ["用时(秒)"] + [f"X{i}" for i in range(1, 6)] + \
             [f"M{i}" for i in range(1, 5)] + [f"Y{i}" for i in range(1, 6)]
    return header, rows


SCALES_TXT = """# 演示量表配置：X含X2/X4反向题，Y含Y3反向题，均为5点
AI情感依赖:5=X1,X2(R),X3,X4(R),X5
孤独感:5=M1,M2,M3,M4
NSSI:5=Y1,Y2,Y3(R),Y4,Y5
"""


def main():
    ap = argparse.ArgumentParser(description="生成结构真实的问卷演示数据（仅用于学习/测试）")
    ap.add_argument("--n", type=int, default=150, help="样本量（默认150）")
    ap.add_argument("--seed", type=int, default=20260917, help="随机种子（默认固定，结果可复现）")
    ap.add_argument("--outdir", default=".", help="输出目录（默认当前目录）")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    data_path = outdir / "demo_survey.csv"
    scales_path = outdir / "demo_scales.txt"

    header, rows = generate(args.n, args.seed)
    with open(data_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    with open(scales_path, "w", encoding="utf-8-sig") as f:
        f.write(SCALES_TXT)

    print(f"已生成演示数据（N={args.n}, seed={args.seed}）：")
    print(f"  {data_path}")
    print(f"  {scales_path}")
    print("\n下一步（跑完整统计流程）：")
    print(f"  python tools/auto_stats.py \"{data_path}\" --scales \"{scales_path}\" "
          f"--y NSSI --x \"AI情感依赖,孤独感\"")
    print("\n参考结果（N=150, seed=20260917）：α约0.90-0.94，Harman约39%，")
    print("  X-M/M-Y/X-Y相关约0.21-0.25均显著，回归孤独感显著、控制后AI依赖减弱（典型中介模式）。")
    print("\n⚠ 这是模拟数据，只能练手，严禁写进真实论文。")


if __name__ == "__main__":
    main()
