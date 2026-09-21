#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nagoya Asian Games 2026 - Dataset Inspector & i18n Seed Generator
全景赛程审计与多语言项目字典生成器
"""

from __future__ import annotations
import os
import glob
import json
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_DICT_FILE = os.path.join(DATA_DIR, "disciplines_i18n_seed.json")

def analyze():
    json_files = sorted(glob.glob(os.path.join(DATA_DIR, "schedule_*.json")))
    
    if not json_files:
        print("❌ 未在 data 目录下找到任何赛程 JSON 文件！")
        return

    total_matches = 0
    total_medal_events = 0
    h2h_matches = 0
    non_h2h_matches = 0
    
    # 统计大项信息: code -> { 'en': name, 'count': 0, 'medal_count': 0 }
    disciplines = {}
    daily_stats = []
    venues = set()

    for file_path in json_files:
        date_str = os.path.basename(file_path).replace("schedule_", "").replace(".json", "")
        with open(file_path, "r", encoding="utf-8") as f:
            matches = json.load(f)
            
        day_match_cnt = len(matches)
        day_medal_cnt = 0
        total_matches += day_match_cnt

        for m in matches:
            disc_code = m.get("Disc", "UNKNOWN")
            disc_desc = m.get("DiscDesc", "Unknown")
            is_medal = (m.get("Medal") == "1")
            is_h2h = m.get("isH2H", False)
            venue = m.get("VenueDesc")

            if venue:
                venues.add(venue)

            if is_medal:
                total_medal_events += 1
                day_medal_cnt += 1

            if is_h2h:
                h2h_matches += 1
            else:
                non_h2h_matches += 1

            if disc_code not in disciplines:
                disciplines[disc_code] = {
                    "code": disc_code,
                    "name_en": disc_desc,
                    "name_zh": "", # 待填充中文
                    "name_ko": "", # 待填充韩文
                    "name_vi": "", # 待填充越南文
                    "name_th": "", # 待填充泰文
                    "match_count": 0,
                    "medal_event_count": 0
                }

            disciplines[disc_code]["match_count"] += 1
            if is_medal:
                disciplines[disc_code]["medal_event_count"] += 1

        daily_stats.append((date_str, day_match_cnt, day_medal_cnt))

    # 输出审计报告
    print("=" * 65)
    print("📊 2026 名古屋亚运会数据底盘全景审计报告")
    print("=" * 65)
    print(f"🏟️  比赛场馆总数: {len(venues)} 个")
    print(f"🏅 运动大项总数: {len(disciplines)} 个大项")
    print(f"⚔️  比赛单元总数: {total_matches} 场 (对抗类: {h2h_matches}, 竞速/打分类: {non_h2h_matches})")
    print(f"🥇 金牌决胜场次: {total_medal_events} 场")
    print("-" * 65)
    print("📅 每日赛程与金牌分布:")
    for date_str, m_cnt, g_cnt in daily_stats:
        medal_flag = f"🔥 产生 {g_cnt:>2d} 枚金牌" if g_cnt > 0 else "⚪ 无金牌产生"
        print(f"  {date_str} | 比赛: {m_cnt:>3d} 场 | {medal_flag}")

    # 保存多语言字典种子文件
    i18n_seed = list(disciplines.values())
    i18n_seed.sort(key=lambda x: x["code"])
    
    with open(OUTPUT_DICT_FILE, "w", encoding="utf-8") as f:
        json.dump(i18n_seed, f, ensure_ascii=False, indent=2)

    print("-" * 65)
    print(f"✅ 已自动生成多语言大项字典种子模板: [data/disciplines_i18n_seed.json]")
    print("=" * 65)

if __name__ == "__main__":
    analyze()
