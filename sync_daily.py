#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nagoya Asian Games 2026 - Daily Auto-Sync Pipeline (Full Edition)
一键全自动流水线：赛程更新 -> 赛果 JSON -> 官方公报 PDF -> AI 增量翻译（全平台兼容）
"""

from __future__ import annotations
import os
import sys
import glob
import json
import time
import zlib
import subprocess
from datetime import date, timedelta
from typing import Optional, List, Dict
import requests

# 1. 兼容 Windows 控制台 UTF-8 输出，防止 Emoji 导致 UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# 2. 原生轻量加载 .env 文件
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

BASE_SCHEDULE_URL = "https://back.results.asiangames2026.org/s/AG2026/en/ALL/schedule/day/{date_str}"
BASE_RESULT_URL = "https://back.results.asiangames2026.org/s/AG2026/en/{disc}/results/{key}"
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
    """还原经过 latin1/zlib 压缩的二进制官方数据"""
    raw_bytes = raw_text.encode("latin1")
    try:
        decompressed = zlib.decompress(raw_bytes)
    except zlib.error:
        decompressed = zlib.decompress(raw_bytes, -15)
    return json.loads(decompressed.decode("utf-8"))

def sync_schedule_for_date(d_str: str, session: requests.Session) -> list:
    """拉取指定日期的最新赛程（覆盖更新）"""
    url = BASE_SCHEDULE_URL.format(date_str=d_str)
    target_file = os.path.join(DATA_DIR, f"schedule_{d_str}.json")
    print(f"📅 同步 [{d_str}] 赛程表 ...", end=" ", flush=True)
    try:
        res = session.get(url, headers=HEADERS, timeout=15)
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

def pick_best_final_pdf(report_groups: list) -> Optional[dict]:
    """从官方公报清单中筛选出最权威的【最终赛果公报】"""
    all_reports = []
    for grp in report_groups:
        for r in grp.get("Reports", []):
            all_reports.append(r)

    if not all_reports:
        return None

    # 优先代码权重
    priority_oris = [
        "C74", "C73FA", "C73A1", "C73A", "C74B", "C73B", "C73", "C73D", "C92A"
    ]
    for target_oris in priority_oris:
        for r in all_reports:
            if r.get("Oris") == target_oris and r.get("URL"):
                return r

    for r in all_reports:
        if "final results" in r.get("Desc", "").lower() and r.get("URL"):
            return r

    for r in all_reports:
        if "results" in r.get("Desc", "").lower() and r.get("URL"):
            return r

    return all_reports[0] if all_reports and all_reports[0].get("URL") else None

def sync_gold_match_data(matches: list, session: requests.Session):
    """
    全量/增量同步金牌战的 JSON 战报与官方 PDF 原始技术公报
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    json_updated = 0
    pdf_updated = 0

    # 提取已决出金牌的比赛
    gold_matches = [
        m for m in matches 
        if m.get("Medal") == "1" and m.get("Status") == "OFFICIAL"
    ]
    
    if not gold_matches:
        print("☕ 暂无新决出的金牌赛事。")
        return

    print(f"\n📊 正在巡检金牌战数据 (本轮共 {len(gold_matches)} 场金牌赛) ...")

    for m in gold_matches:
        disc = m.get("Disc")
        key = m.get("Key")
        desc = m.get("EventDesc")
        target_json = os.path.join(RESULTS_DIR, f"{key}.json")
        target_pdf = os.path.join(RESULTS_DIR, f"{key}.pdf")

        # 1. 同步 JSON 战报
        need_json = not os.path.exists(target_json) or os.path.getsize(target_json) < 50
        if need_json:
            print(f"🥇 同步战报JSON [{disc}] {desc} ...", end=" ", flush=True)
            url = BASE_RESULT_URL.format(disc=disc, key=key)
            try:
                res = session.get(url, headers=HEADERS, timeout=15)
                if res.status_code == 200:
                    r_data = decompress_payload(res.text)
                    with open(target_json, "w", encoding="utf-8") as fp:
                        json.dump(r_data, fp, ensure_ascii=False, indent=2)
                    print("✅")
                    json_updated += 1
                else:
                    print(f"⚪ (HTTP {res.status_code})")
            except Exception as e:
                print(f"❌ {e}")
            time.sleep(0.4)

        # 2. 同步官方 PDF 技术公报
        need_pdf = not os.path.exists(target_pdf) or os.path.getsize(target_pdf) < 15 * 1024
        if need_pdf:
            print(f"📄 提取官方PDF  [{disc}] {desc} ...", end=" ", flush=True)
            report_url = REPORTS_API_URL.format(disc=disc, key=key)
            try:
                res = session.get(report_url, headers=HEADERS, timeout=15)
                if res.status_code == 200:
                    report_groups = decompress_payload(res.text)
                    best_pdf = pick_best_final_pdf(report_groups)
                    if best_pdf and best_pdf.get("URL"):
                        pdf_download_url = best_pdf.get("URL")
                        p_res = session.get(pdf_download_url, headers=HEADERS, timeout=20, stream=True)
                        if p_res.status_code == 200:
                            first_bytes = p_res.raw.read(4)
                            if first_bytes == b"%PDF":
                                with open(target_pdf, "wb") as fp:
                                    fp.write(first_bytes)
                                    for chunk in p_res.iter_content(chunk_size=8192):
                                        fp.write(chunk)
                                size_kb = round(os.path.getsize(target_pdf) / 1024, 1)
                                print(f"✅ [{best_pdf.get('Oris')}] ({size_kb} KB)")
                                pdf_updated += 1
                            else:
                                print("❌ 校验失败")
                        else:
                            print(f"❌ 下载HTTP {p_res.status_code}")
                    else:
                        print("⚪ 暂无结果PDF")
                else:
                    print("⏳ 官方清单生成中")
            except Exception as e:
                print(f"❌ {e}")
            time.sleep(0.4)

    print(f"📈 本轮战报归档小结: 新增 JSON {json_updated} 份，新增 PDF {pdf_updated} 份\n")

def run():
    print("=" * 65)
    print("🚀 名古屋亚运会 2026 - 每日赛况与金牌公报一键增量同步")
    print("=" * 65)

    session = requests.Session()

    # 1. 同步今天与昨天的最新赛程（覆盖更新）
    today = date.today()
    yesterday = today - timedelta(days=1)
    dates_to_sync = [yesterday.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")]

    for d_str in dates_to_sync:
        sync_schedule_for_date(d_str, session)
        time.sleep(0.5)

    # 2. 收集本地所有的赛程数据，确保历史金牌战和新金牌战都不遗漏
    all_schedule_matches = []
    seen_keys = set()
    schedule_files = sorted(glob.glob(os.path.join(DATA_DIR, "schedule_*.json")))
    for sf in schedule_files:
        try:
            with open(sf, "r", encoding="utf-8") as fp:
                s_data = json.load(fp)
                if isinstance(s_data, list):
                    for m in s_data:
                        k = m.get("Key")
                        if k and k not in seen_keys:
                            seen_keys.add(k)
                            all_schedule_matches.append(m)
        except Exception:
            pass

    # 3. 增量同步金牌战的 JSON 与官方 PDF
    sync_gold_match_data(all_schedule_matches, session)

    # 4. 自动触发 DeepSeek 多语言增量翻译
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        print("🤖 检测到 DeepSeek 密钥，自动触发增量翻译检查...")
        translate_script = os.path.join(BASE_DIR, "translate_athletes.py")
        subprocess.run([sys.executable, translate_script])
    else:
        print("⚪ 未配置 DEEPSEEK_API_KEY，跳过 AI 翻译环节。")

    print("=" * 65)
    print("🎉 每日增量数据与金牌公报同步完毕！")
    print("=" * 65)

if __name__ == "__main__":
    run()