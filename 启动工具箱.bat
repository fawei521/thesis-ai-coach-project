@echo off
chcp 65001 >nul
title 毕业论文工具箱
cd /d "%~dp0"

echo ================================================================
echo            毕业论文工具箱（心理学问卷研究）
echo ================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [提示] 这台电脑还没装 Python，或安装时没勾选 Add Python to PATH。
    echo 请回到AI对话，让导师带你按 环境搭建指南 安装（只需一次）。
    echo.
    pause
    exit /b
)

python tools\menu.py

echo.
echo 工具箱已退出。
pause
