#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nagoya Asian Games 2026 - Daily Auto-Sync Pipeline
一键自动同步：赛程更新 -> 赛果下载 -> AI 增量翻译（全平台兼容版）
"""

from __future__ import annotations
import os
import sys
import json
import time
import zlib
import subprocess
from datetime import date, timedelta
import requests

# 1. 兼容 Windows 控制台 UTF-8 输出，防止 Emoji 导致 UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# 2. 原生轻量加载 .env 文件（无需额外 pip install python-dotenv）
def load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key not in os.environ:
                        os.environ[key] = val

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(DATA_DIR, "results")
ATHLETES_FILE = os.path.join(DATA_DIR, "athletes_i18n.json")

BASE_SCHEDULE_URL = "https://back.results.asiangames2026.org/s/AG2026/en/ALL/schedule/day/{date_str}"
BASE_RESULT_URL = "https://back.results.asiangames2026.org/s/AG2026/en/{disc}/results/{key}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://results.asiangames2026.org/",
}

def decompress_payload(raw_text: str):
    raw_bytes = raw_text.encode("latin1")
    try:
        decompressed = zlib.decompress(raw_bytes)
    except zlib.error:
        decompressed = zlib.decompress(raw_bytes, -15)
    return json.loads(decompressed.decode("utf-8"))

def sync_schedule_for_date(d_str: str) -> list:
    """拉取指定日期的最新赛程（覆盖更新）"""
    url = BASE_SCHEDULE_URL.format(date_str=d_str)
    target_file = os.path.join(DATA_DIR, f"schedule_{d_str}.json")
    print(f"📅 正在同步 [{d_str}] 赛程表 ...", end=" ", flush=True)
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            data = decompress_payload(res.text)
            if isinstance(data, list):
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(target_file, "w", encoding="utf-8") as fp:
                    json.dump(data, fp, ensure_ascii=False, indent=2)
                print(f"✅ 成功! (共 {len(data)} 场)")
                return data
    except Exception as e:
        print(f"❌ 失败: {e}")
    return []

def sync_results_for_matches(matches: list):
    """只抓取已完赛且决出奖牌的战报"""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    updated_cnt = 0
    for m in matches:
        if m.get("Medal") == "1" and m.get("Status") == "OFFICIAL":
            disc = m.get("Disc")
            key = m.get("Key")
            target_file = os.path.join(RESULTS_DIR, f"{key}.json")
            
            if not os.path.exists(target_file) or os.path.getsize(target_file) < 50:
                print(f"🥇 同步金牌战报 [{disc}] {m.get('EventDesc')} ...", end=" ", flush=True)
                url = BASE_RESULT_URL.format(disc=disc, key=key)
                try:
                    res = requests.get(url, headers=HEADERS, timeout=15)
                    if res.status_code == 200:
                        r_data = decompress_payload(res.text)
                        with open(target_file, "w", encoding="utf-8") as fp:
                            json.dump(r_data, fp, ensure_ascii=False, indent=2)
                        print("✅")
                        updated_cnt += 1
                        time.sleep(0.5)
                except Exception as e:
                    print(f"❌ {e}")
    print(f"📊 本轮新增战报归档: {updated_cnt} 场")

def run():
    print("=" * 60)
    print("🚀 名古屋亚运会 2026 - 每日赛况一键增量同步")
    print("=" * 60)
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    dates_to_sync = [yesterday.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")]
    
    all_matches = []
    for d_str in dates_to_sync:
        matches = sync_schedule_for_date(d_str)
        all_matches.extend(matches)
        time.sleep(1)

    # 同步最新战报
    sync_results_for_matches(all_matches)
    
    # 动态检查 Key 并调用翻译脚本（跨平台安全调用）
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        print("🤖 检测到 DeepSeek 密钥，自动触发增量翻译检查...")
        translate_script = os.path.join(BASE_DIR, "translate_athletes.py")
        # 使用 sys.executable，跨平台且自动继承当前虚拟环境 Python
        subprocess.run([sys.executable, translate_script])
    else:
        print("⚪ 未配置 DEEPSEEK_API_KEY，跳过 AI 翻译环节。")

    print("=" * 60)
    print("🎉 每日增量数据同步完毕！")

if __name__ == "__main__":
    run()