# 🏅 2026 Aichi-Nagoya Asian Games Live Tracker
### 2026 名古屋亚运会 · 多语言全赛程与成绩聚合看板 (Unofficial)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![GitHub Pages](https://img.shields.io/badge/Demo-GitHub%20Pages-success)](https://fanyangcloud.github.io/nagoya_asian_games_2026/)
[![Languages](https://img.shields.io/badge/Languages-ZH%20%7C%20KO%20%7C%20VI%20%7C%20TH-orange)](#-原生多语言支持)

专为亚洲体育迷设计的轻量级、零编译（Zero-Build）、极致秒开的爱知·名古屋亚运会全景赛程与比分看板。

🌐 **在线体验 (Live Demo)**: [https://fanyangcloud.github.io/nagoya_asian_games_2026/](https://fanyangcloud.github.io/nagoya_asian_games_2026/)

---

## ✨ 核心特性

- ⚡ **零编译架构 (Zero-Build)**：基于原生 HTML5 + Tailwind CSS (CDN) 驱动，无需任何打包工具，秒级加载，弱网极速首屏。
- 🌐 **原生四国语言支持**：深度覆盖 **中文 (🇨🇳) / 한국어 (🇰🇷) / Tiếng Việt (🇻🇳) / ภาษาไทย (🇹🇭)**，项目名、轮次、泳姿、场馆完全本地化，告别生硬英文缩写。
- 📅 **全量赛程覆盖**：完整收录 25 天（2026-09-10 ~ 2026-10-04）全部 **59 个运动大项、6,869 场比赛单元**。
- 🥇 **一键金牌赛过滤**：直达核心焦点，瞬间筛选出全赛期全部 **453 场金牌决胜赛**。
- 📊 **权威战报下钻**：支持弹窗秒查详细成绩单（奖牌归属、分段用时、出发反应时间、打破纪录标记等）。
- 📱 **移动端深度优化**：自适应横向日期滑块与流式卡片，完美契合手机端竖屏查分场景。

---

## 📂 项目结构

```text
nagoya_asian_games_2026/
├── index.html                   # 核心前端页面 (多语言引擎、日期选择、卡片渲染)
├── data/
│   ├── disciplines_i18n.json    # 59 个大项四国语言翻译与场次/金牌数资产库
│   ├── schedule_2026-09-10.json # 每日赛程全量数据 (至 10-04，共25天)
│   └── results/                 # 453 场金牌决胜赛详细成绩归档库
├── fetch_schedules.py           # 赛程增量与断点续传爬虫
├── fetch_medal_results.py       # 金牌决赛战报收割脚本
├── analyze_schedules.py         # 赛程全景审计工具
├── requirements.txt             # Python 依赖清单
├── LICENSE                      # MIT 授权协议
└── README.md                    # 项目说明文档
🚀 本地快速启动
克隆本项目，无需配置任何 Node.js 编译环境，直接在本地启动服务：
code
Bash
# 1. 克隆仓库
git clone https://github.com/fanyangcloud/nagoya_asian_games_2026.git
cd nagoya_asian_games_2026

# 2. 使用 Python 启动静态文件服务器
python3 -m http.server 8000
打开浏览器访问 http://localhost:8000 即可畅爽体验。
🤝 参与贡献 (Contributing)
欢迎提交 Issue 和 Pull Request！特别是如果您发现韩语、泰语或越南语的体育术语有待润色，欢迎完善 data/disciplines_i18n.json 或 index.html 中的词典。
📄 免责声明 (Disclaimer)
This is an open-source, non-profit, unofficial fan project created solely for informational purposes and sports enthusiasts. It is not affiliated with, endorsed by, or sponsored by the Olympic Council of Asia (OCA) or the 20th Aichi-Nagoya Asian Games Organizing Committee (AINAGOC). All match data and competitor information belong to their respective copyright holders.
