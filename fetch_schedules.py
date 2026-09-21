#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nagoya Asian Games 2026 - Daily Schedule Harvester
支持【断点续传】与【自动故障重试】的健壮版本
"""

from __future__ import annotations
import os
import sys
import time
import json
import zlib
from datetime import date, timedelta
from typing import Union, List, Dict, Any
import requests

BASE_URL = "https://back.results.asiangames2026.org/s/AG2026/en/ALL/schedule/day/{date_str}"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7",
    "Referer": "https://results.asiangames2026.org/",
}

def decompress_payload(raw_text: str) -> Union[List[Any], Dict[str, Any]]:
    raw_bytes = raw_text.encode("latin1")
    try:
        decompressed = zlib.decompress(raw_bytes)
    except zlib.error:
        decompressed = zlib.decompress(raw_bytes, -15)
    return json.loads(decompressed.decode("utf-8"))

def generate_date_range(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)

def run():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    start_d = date(2026, 9, 10)
    end_d = date(2026, 10, 4)
    total_days = (end_d - start_d).days + 1

    print("=" * 65)
    print("🏅 名古屋亚运会 2026 - 增量/断点续传引擎启动")
    print(f"📅 目标区间: {start_d} 至 {end_d} (共 {total_days} 天)")
    print(f"📁 存储目录: {DATA_DIR}")
    print("=" * 65)

    success_days = 0
    total_matches_found = 0

    for index, current_date in enumerate(generate_date_range(start_d, end_d), start=1):
        date_str = current_date.strftime("%Y-%m-%d")
        target_file = os.path.join(DATA_DIR, f"schedule_{date_str}.json")
        request_url = BASE_URL.format(date_str=date_str)

        # 1. 断点续传检查：如果文件已存在且大小大于 10 字节，直接跳过！
        if os.path.exists(target_file) and os.path.getsize(target_file) > 10:
            try:
                with open(target_file, "r", encoding="utf-8") as fp:
                    cached_data = json.load(fp)
                    cnt = len(cached_data) if isinstance(cached_data, list) else 0
                    total_matches_found += cnt
                    success_days += 1
                    print(f"[{index:02d}/{total_days:02d}] {date_str} ⏩ 已存在本地，自动跳过 ({cnt:>3d} 场)")
                    continue
            except Exception:
                pass  # 若文件损坏则重新抓取

        # 2. 失败重试逻辑（最多重试 3 次，防止网络瞬断）
        max_retries = 3
        fetch_success = False

        for attempt in range(1, max_retries + 1):
            print(f"[{index:02d}/{total_days:02d}] 正在同步 {date_str} (第 {attempt} 次尝试) ...", end=" ", flush=True)

            try:
                # 重新建立连接，延长超时时间至 20 秒
                session = requests.Session()
                resp = session.get(request_url, headers=HEADERS, timeout=20)
                
                if resp.status_code == 200:
                    payload = decompress_payload(resp.text)
                    if isinstance(payload, list):
                        match_count = len(payload)
                        total_matches_found += match_count
                        
                        with open(target_file, "w", encoding="utf-8") as fp:
                            json.dump(payload, fp, ensure_ascii=False, indent=2)
                            
                        print(f"✅ 补全成功! 获取场次: {match_count:>3d} 场 -> [data/schedule_{date_str}.json]")
                        success_days += 1
                        fetch_success = True
                        break
                    else:
                        print(f"⚠️ 数据格式非预期的 Array: {type(payload)}")

                elif resp.status_code == 404:
                    print("⚪ 当日无赛事安排 (404 Not Found)")
                    fetch_success = True
                    break
                else:
                    print(f"❌ 响应异常 (HTTP {resp.status_code})")

            except Exception as exc:
                print(f"⚠️ 网络抖动 ({exc.__class__.__name__})，等待重试...")
                time.sleep(2 * attempt)  # 阶梯式延迟重试

        if not fetch_success:
            print(f"💥 {date_str} 经 3 次重试仍未成功，请稍后再试。")

        # 礼貌抓取间隔
        time.sleep(1.2)

    print("=" * 65)
    print("🎉 任务执行完毕!")
    print(f"📊 最终全勤天数: {success_days}/{total_days} 天")
    print(f"🏆 累计捕获比赛单元: {total_matches_found} 场")
    print("=" * 65)

if __name__ == "__main__":
    run()
