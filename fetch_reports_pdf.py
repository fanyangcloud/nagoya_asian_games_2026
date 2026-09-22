#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nagoya Asian Games 2026 - Gold Medal Official Reports (PDF) Pipeline
精准爆破版：直接调用官方 Reports 内部接口，100% 精准下载最终成绩 PDF 公报
"""

from __future__ import annotations  # 👈 加上这行，完美兼容 Python 3.7/3.8/3.9
import os
import sys
import glob
import json
import time
import zlib
import requests
from typing import Optional, List, Dict

# 兼容 Windows 控制台 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

# 官方 Reports 内部清单接口
REPORTS_API_URL = "https://back.results.asiangames2026.org/s/AG2026/en/{disc}/reports/unit/{key}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Referer": "https://results.asiangames2026.org/",
}

def decompress_payload(raw_text: str):
    """还原经过 latin1/zlib 编码的官方二进制数据"""
    raw_bytes = raw_text.encode("latin1")
    try:
        decompressed = zlib.decompress(raw_bytes)
    except zlib.error:
        decompressed = zlib.decompress(raw_bytes, -15)
    return json.loads(decompressed.decode("utf-8"))

def fetch_report_list(disc: str, key: str, session: requests.Session) -> list:
    """获取该比赛所有已生成的官方 PDF 公报清单"""
    url = REPORTS_API_URL.format(disc=disc, key=key)
    try:
        res = session.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            return decompress_payload(res.text)
    except Exception:
        pass
    return []

def pick_best_final_pdf(report_groups: list) -> Optional[dict]:
    """
    从官方给出的丰富 PDF 清单中，智能选出最权威的【最终赛果公报】(Final Results)
    优先命中: C74, C73FA, C73A1, C73A, C73B, C74B 等核心决赛公报
    """
    all_reports = []
    for grp in report_groups:
        for r in grp.get("Reports", []):
            all_reports.append(r)

    if not all_reports:
        return None

    # 1. 优先按官方 Oris 核心代码权重排序
    priority_oris = [
        "C74",    # 现代五项/对抗赛 最终总成绩 (Final Results)
        "C73FA",  # 射击等打分项目 决赛公报 (Final Results)
        "C73A1",  # 游泳等分段 最终成绩
        "C73A",   # 通用最终单项决赛成绩
        "C74B",   # 团队决赛成绩 (Team Results Final)
        "C73B",   # 详细决赛成绩 (如武术、体操)
        "C73",    # 基础决赛成绩
        "C73D",   # 分项核心成绩
        "C92A",   # 奖牌获得者名单 (Medalists)
    ]

    for target_oris in priority_oris:
        for r in all_reports:
            if r.get("Oris") == target_oris and r.get("URL"):
                return r

    # 2. 次选：描述里含有 Final Results 的
    for r in all_reports:
        desc = r.get("Desc", "").lower()
        if "final results" in desc and r.get("URL"):
            return r

    # 3. 兜底：含有 Results 的任何报表
    for r in all_reports:
        desc = r.get("Desc", "").lower()
        if "results" in desc and r.get("URL"):
            return r

    # 4. 终极兜底：第一个有效的 PDF
    return all_reports[0] if all_reports and all_reports[0].get("URL") else None

def download_file(url: str, target_path: str, session: requests.Session) -> bool:
    """流式安全下载 PDF"""
    try:
        res = session.get(url, headers=HEADERS, timeout=20, stream=True)
        if res.status_code == 200:
            first_bytes = res.raw.read(4)
            if first_bytes == b"%PDF":
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "wb") as fp:
                    fp.write(first_bytes)
                    for chunk in res.iter_content(chunk_size=8192):
                        fp.write(chunk)
                return True
    except Exception:
        pass
    return False

def sync_gold_reports(target_date: str = None):
    print("=" * 68)
    print("🚀 名古屋亚运会 2026 - 官方赛果技术公报 (PDF) 100% 精准归档")
    print("=" * 68)

    # 1. 扫描所有赛程
    if target_date:
        schedule_files = [os.path.join(DATA_DIR, f"schedule_{target_date}.json")]
    else:
        schedule_files = sorted(glob.glob(os.path.join(DATA_DIR, "schedule_*.json")))

    if not schedule_files:
        print("❌ 未在 data/ 目录下找到任何 schedule_*.json 赛程文件！")
        return

    gold_matches = []
    seen_keys = set()

    for s_file in schedule_files:
        if not os.path.exists(s_file):
            continue
        try:
            with open(s_file, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                if isinstance(data, list):
                    for m in data:
                        if m.get("Medal") == "1" and m.get("Status") == "OFFICIAL":
                            key = m.get("Key")
                            if key and key not in seen_keys:
                                seen_keys.add(key)
                                gold_matches.append(m)
        except Exception:
            continue

    print(f"📊 累计扫描到已决出金牌的比赛: {len(gold_matches)} 场\n")

    session = requests.Session()
    success_cnt = 0
    skip_cnt = 0
    not_ready_cnt = 0

    for idx, match in enumerate(gold_matches, 1):
        disc = match.get("Disc", "")
        key = match.get("Key", "")
        event_desc = match.get("EventDesc", "")
        target_pdf = os.path.join(RESULTS_DIR, f"{key}.pdf")

        # 增量跳过：已存在且大于 15KB
        if os.path.exists(target_pdf) and os.path.getsize(target_pdf) > 15 * 1024:
            skip_cnt += 1
            continue

        print(f"[{idx}/{len(gold_matches)}] 🥇 [{disc}] {event_desc} ...", end=" ", flush=True)

        # 1. 调取官方报告列表
        report_groups = fetch_report_list(disc, key, session)
        if not report_groups:
            print("⏳ 官方公报尚未生成 (API 暂无数据)")
            not_ready_cnt += 1
            time.sleep(0.3)
            continue

        # 2. 挑选最佳最终成绩公报
        best_report = pick_best_final_pdf(report_groups)
        if not best_report or not best_report.get("URL"):
            print("⚪ 清单中暂未包含结果 PDF")
            not_ready_cnt += 1
            time.sleep(0.3)
            continue

        pdf_url = best_report.get("URL")
        oris = best_report.get("Oris", "Report")
        desc = best_report.get("Desc", "")
        ver = best_report.get("v", "")

        # 3. 极速下载
        ok = download_file(pdf_url, target_pdf, session)
        if ok:
            size_kb = round(os.path.getsize(target_pdf) / 1024, 1)
            print(f"✅ 成功! [{oris}] {desc} (v{ver}) -> {size_kb} KB")
            success_cnt += 1
        else:
            print("❌ 下载失败")

        time.sleep(0.4) # 礼貌延时

    print("\n" + "=" * 68)
    print(f"🎉 归档完毕！本次新增: {success_cnt} 份，已有跳过: {skip_cnt} 份，生成中: {not_ready_cnt} 份")
    print(f"📂 成果目录: [data/results/*.pdf]")
    print("=" * 68)

if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sync_gold_reports(date_arg)