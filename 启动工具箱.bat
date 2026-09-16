@echo off
chcp 936 >nul
cd /d "%~dp0"
title 毕业论文工具箱

if not exist "tools\menu.py" (
    echo ================================================================
    echo [提示] 没有找到工具文件，你很可能是直接在压缩包里运行的。
    echo 请先关闭本窗口，把整个压缩包解压到一个文件夹
    echo （右键压缩包，选择 解压到当前文件夹），
    echo 再进入解压出来的 thesis-ai-coach-project 文件夹，双击本启动器。
    echo ================================================================
    echo.
    pause
    exit /b
)

echo ================================================================
echo            毕业论文工具箱（心理学问卷研究）
echo ================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [提示] 这台电脑还没装 Python，或安装时没勾选 Add Python to PATH。
    echo 请回到AI对话，让导师带你按环境搭建指南安装（只需一次）。
    echo.
    pause
    exit /b
)

chcp 65001 >nul
python tools\menu.py

echo.
echo 工具箱已退出。
pause
