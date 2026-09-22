@echo off
chcp 65001 >nul
echo 正在准备增量同步名古屋亚运会数据...

REM 1. 尝试激活 Windows 虚拟环境
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM 2. 执行同步脚本
python sync_daily.py
if %ERRORLEVEL% NEQ 0 (
    echo [错误] Python 同步脚本执行失败！
    pause
    exit /b %ERRORLEVEL%
)

REM 3. Git 提交并推送
git add data/
for /f "tokens=1-4 delims=/ " %%i in ('date /t') do set mydate=%%i-%%j-%%k
git commit -m "chore: auto-update daily matches and medal results [%mydate%]"
git push origin main

if %ERRORLEVEL% EQU 0 (
    echo ==========================================
    echo [成功] 更新成功！GitHub Pages 即将自动上线！
    echo 访问地址: https://fanyangcloud.github.io/nagoya_asian_games_2026/
    echo ==========================================
) else (
    echo [警告] Git Push 失败，请检查网络连接！
)
pause