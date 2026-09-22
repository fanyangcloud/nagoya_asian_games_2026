#!/bin/bash

# 1. 跨平台激活 Python 虚拟环境 (兼容 Mac/Linux 与 Windows Git Bash)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# 2. 自动匹配 python 命令（兼容 Windows 下叫 python，Mac 下叫 python3）
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
else
    PY_CMD="python"
fi

# 3. 执行每日数据增量同步
$PY_CMD sync_daily.py

# 4. 自动提交并推送到 GitHub
git add data/

# 检查是否有改动需要提交
if git diff --cached --quiet; then
    echo "☕ 数据无变动，无需提交。"
else
    git commit -m "chore: auto-update daily matches and medal results [$(date +'%Y-%m-%d %H:%M')]"
    git push origin main
fi

echo "=========================================="
echo "🚀 更新成功！GitHub Pages 将在 1 分钟后自动上线！"
echo "🌐 访问地址: https://fanyangcloud.github.io/nagoya_asian_games_2026/"
echo "=========================================="