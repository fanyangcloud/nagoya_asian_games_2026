#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nagoya Asian Games 2026 - Gold Medal Results Harvester
专门定向抓取 453 场金牌决赛的终局战报与选手成绩单
"""

from __future__ import annotations
import os
import glob
import time
import json
import zlib
import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RESULTS_DIR = os.path.join(DATA_DIR, "results")
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

def run():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    schedule_files = sorted(glob.glob(os.path.join(DATA_DIR, "schedule_*.json")))

    # 1. 收集所有金牌赛任务
    tasks = []
    for sf in schedule_files:
        with open(sf, "r", encoding="utf-8") as fp:
            matches = json.load(fp)
            for m in matches:
                # 只要是金牌赛
                if m.get("Medal") == "1":
                    disc = m.get("Disc")
                    key = m.get("Key")
                    desc = m.get("EventDesc")
                    date_str = m.get("DateTimeRaw", "")[:10]
                    if disc and key:
                        tasks.append({
                            "disc": disc,
                            "key": key,
                            "desc": desc,
                            "date": date_str
                        })

    total_tasks = len(tasks)
    print("=" * 65)
    print("🥇 名古屋亚运会 2026 - 金牌决赛战报定向收割引擎")
    print(f"🎯 待抓取金牌赛总数: {total_tasks} 场")
    print(f"📁 战报归档目录: {RESULTS_DIR}")
    print("=" * 65)

    success_cnt = 0
    skip_cnt = 0

    for idx, t in enumerate(tasks, start=1):
        disc = t["disc"]
        key = t["key"]
        desc = t["desc"]
        target_file = os.path.join(RESULTS_DIR, f"{key}.json")

        # 断点续传：若已存在则跳过
        if os.path.exists(target_file) and os.path.getsize(target_file) > 10:
            skip_cnt += 1
            print(f"[{idx:03d}/{total_tasks:03d}] ⏩ [{disc}] {desc} 已存在本地，跳过")
            continue

        url = BASE_RESULT_URL.format(disc=disc, key=key)
        print(f"[{idx:03d}/{total_tasks:03d}] 正在同步 [{disc}] {desc} ...", end=" ", flush=True)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                result_data = decompress_payload(resp.text)
                with open(target_file, "w", encoding="utf-8") as fp:
                    json.dump(result_data, fp, ensure_ascii=False, indent=2)
                print("✅ 成功归档!")
                success_cnt += 1
            elif resp.status_code == 404:
                print("⚪ 官方暂未录入该决赛结果 (404)")
            else:
                print(f"❌ 失败 (HTTP {resp.status_code})")
        except Exception as e:
            print(f"💥 异常: {e}")

        # 礼貌抓取间隔
        time.sleep(1.0)

    print("=" * 65)
    print(f"🎉 金牌战报归档完成！成功: {success_cnt} 场，已跳过: {skip_cnt} 场")
    print("=" * 65)

if __name__ == "__main__":
    run()
