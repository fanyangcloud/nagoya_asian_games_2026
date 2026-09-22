#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nagoya Asian Games 2026 - Athlete Name AI Translator (Powered by DeepSeek)
全平台兼容版（原生支持 Windows UTF-8 控制台与自动环境变量注入）
"""

import os
import sys
import glob
import json
import time
import requests

# 1. 兼容 Windows 控制台 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# 2. 原生加载 .env 兜底
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
OUTPUT_FILE = os.path.join(DATA_DIR, "athletes_i18n.json")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

def extract_unique_athletes():
    """从已抓取的战报中提取所有唯一运动员"""
    athletes = {}
    files = glob.glob(os.path.join(RESULTS_DIR, "*.json"))
    
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                competitors = data.get("Competitors", [])
                if competitors and isinstance(competitors, list):
                    for c in competitors:
                        reg = c.get("Reg")
                        name = c.get("Name")
                        org = c.get("Org")
                        if reg and name and reg not in athletes:
                            athletes[reg] = {
                                "reg": reg,
                                "name_en": name,
                                "org": org
                            }
        except Exception:
            continue
            
    return athletes

def translate_batch_with_deepseek(batch_list):
    """调用 DeepSeek 批量翻译运动员"""
    prompt = """你是一个专业的国际综合体育赛事（奥运会/亚运会）官方译名专家。
请根据提供的运动员英文名（全大写或姓名前置格式）以及其代表团国家/地区代码（Org）：
1. 给出符合新华社/官方通译标准的【简体中文名】（特别是中日韩选手，必须还原其真实汉字名，如 XU Jiayu -> 徐嘉余，KOGA Junya -> 古贺淳也）；
2. 给出【韩文名 (ko)】（遵循大韩体育会标准韩文转写，如徐嘉余 -> 쉬자위）；
3. 给出【越南文名 (vi)】；
4. 给出【泰文名 (th)】。

请严格输出 JSON 格式，不要携带任何解释文字，格式如下：
{
  "results": [
    {
      "reg": "选手RegID",
      "zh": "中文名",
      "ko": "한국어",
      "vi": "Tiếng Việt",
      "th": "ภาษาไทย"
    }
  ]
}
待翻译名单如下：
""" + json.dumps(batch_list, ensure_ascii=False)

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a professional sports multi-language localization engine. Output strictly valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
    if resp.status_code == 200:
        result_json = resp.json()
        content = result_json["choices"][0]["message"]["content"]
        return json.loads(content).get("results", [])
    else:
        raise Exception(f"DeepSeek API Error: {resp.status_code} - {resp.text}")

def run():
    print("=" * 65)
    print("🤖 名古屋亚运会 2026 - DeepSeek 运动员姓名多语言翻译引擎")
    print("=" * 65)

    if not DEEPSEEK_API_KEY:
        print("❌ 错误: 未检测到 DEEPSEEK_API_KEY 环境变量！跳过翻译。")
        return

    cached_db = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as fp:
                cached_db = json.load(fp)
        except Exception:
            cached_db = {}

    all_athletes = extract_unique_athletes()
    print(f"📊 本地战报累计发现选手: {len(all_athletes)} 人")

    to_translate = [a for reg, a in all_athletes.items() if reg not in cached_db]
    print(f"⏩ 已有缓存: {len(cached_db)} 人，本次需翻译: {len(to_translate)} 人")

    if not to_translate:
        print("🎉 所有选手姓名均已完成翻译，无需重复调用！")
        return

    batch_size = 25
    for i in range(0, len(to_translate), batch_size):
        batch = to_translate[i : i + batch_size]
        print(f"🚀 正在请求 DeepSeek 翻译批次 [{i+1} ~ {min(i+batch_size, len(to_translate))}] ...", end=" ", flush=True)

        try:
            results = translate_batch_with_deepseek(batch)
            for item in results:
                reg = str(item.get("reg"))
                cached_db[reg] = {
                    "zh": item.get("zh"),
                    "ko": item.get("ko"),
                    "vi": item.get("vi"),
                    "th": item.get("th")
                }

            os.makedirs(DATA_DIR, exist_ok=True)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as fp:
                json.dump(cached_db, fp, ensure_ascii=False, indent=2)
            print("✅ 成功!")

        except Exception as e:
            print(f"💥 翻译异常: {e}")

        time.sleep(1.0)

    print("=" * 65)
    print(f"🎉 翻译完成！已安全归档至: [data/athletes_i18n.json]")
    print("=" * 65)

if __name__ == "__main__":
    run()