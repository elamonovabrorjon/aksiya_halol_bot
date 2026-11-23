# ==========================================
# 0. RENDER / MUHIT SOZLAMALARI
# ==========================================
import calendar
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import html
from io import StringIO
import json
import logging
import os
import pickle
import re
import threading
import time
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

from google import genai
import numpy as np
import pandas as pd
import requests
import telebot
from telebot import types
import yfinance as yf


def _get_env_or_default(var_name, default_val=""):
  val = os.environ.get(var_name)
  if val and str(val).strip():
    return str(val).strip()
  return default_val


# ==========================================
# 2. SOZLAMALAR, KANAL VA LIMITLAR
# ==========================================
TELEGRAM_TOKEN = _get_env_or_default("TELEGRAM_TOKEN")
GEMINI_API_KEY = _get_env_or_default("GEMINI_API_KEY")

if not TELEGRAM_TOKEN:
  raise ValueError(
      "TELEGRAM_TOKEN muhit o'zgaruvchisi (Environment Variable) kiritilmagan!"
  )
if not GEMINI_API_KEY:
  raise ValueError(
      "GEMINI_API_KEY muhit o'zgaruvchisi (Environment Variable) kiritilmagan!"
  )

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

ADMIN_ID = 745170275
ADMIN_IDS = {ADMIN_ID}
ADMIN_LINK = "EAA_7879"

# Bloomberg UZ kanali ID
CHANNEL_ID = "-1003705704983"

# AI Algoritm strategiya filtri: P/E [10..25] va RSI [20..30]
SIGNAL_PE_MIN = 10.0
SIGNAL_PE_MAX = 25.0
SIGNAL_RSI_MIN = 20.0
SIGNAL_RSI_MAX = 30.0

SCAN_WATCHLIST = [
    "AAPL",
    "MSFT",
    "NVDA",
    "INTC",
    "AVGO",
    "MU",
    "TSM",
    "MRK",
    "JNJ",
    "CF",
    "AMZN",
    "GOOGL",
    "META",
    "AMD",
    "UNH",
]

DAILY_FREE_LIMIT = 5
MONTHLY_FREE_LIMIT = 20

USAGE_FILE = "/tmp/bot_usage.json"
INDEX_CACHE = {}
INDUSTRY_TRANSLATION_CACHE = {}
INDEX_DISK_CACHE = "/tmp/indices.pkl"
INDEX_CACHE_TTL = 60 * 60 * 24

SEGMENT_MIX_FALLBACK = {
    "AAPL": [
        "iPhone (~50–52%)",
        "Services (~24–26%)",
        "Mac & iPad (~14–16%)",
        "Wearables, Home & Accessories (~8–10%)",
    ],
    "INTC": [
        "Client Computing / CCPG (~49% segment ulushi)",
        "Data Center & AI / DCAI (~44% segment ulushi)",
        "Intel Foundry (~41% segment ulushi; ichki eliminatsiyalar hisobga olingan)",
    ],
    "NVDA": [
        "Data Center (~85–90%)",
        "Gaming & AI PC (~8–10%)",
        "Professional Visualization & Automotive (~3–5%)",
    ],
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

USER_MODES = {}
USER_BALANCES = {}
USER_REFERRALS = {}
ADMIN_AWAITING_CMD = set()

BTN_AI_ANALYSIS = "🧠 AI Tahlil"
BTN_ALGO_SIGNALS = "📊 Algoritmik signallar"
BTN_AI_HELP = "💬 AI Yordam"
BTN_BALANCE = "💰 Balans"
BTN_REFERRAL = "🔗 Referal tizim"
BTN_ADMIN = "⚙️ Admin Panel"

ALIAS_AI_ANALYSIS = {
    "🧠 ai tahlil",
    "🧠 ai таҳлил",
    "ai tahlil",
    "ai таҳлил",
}
ALIAS_ALGO_SIGNALS = {
    "📊 algoritmik signallar",
    "📊 алгоритмик сигналлар",
    "algoritmik signallar",
    "алгоритмик сигналлар",
}
ALIAS_AI_HELP = {"💬 ai yordam", "💬 ai ёрдам", "ai yordam", "ai ёрдам"}
ALIAS_BALANCE = {"💰 balans", "💰 баланс", "balans", "баланс"}
ALIAS_REFERRAL = {
    "🔗 referal tizim",
    "🔗 реферал тизим",
    "referal tizim",
    "реферал тизим",
}
ALIAS_ADMIN = {
    "⚙️ admin panel",
    "⚙️ админ панел",
    "admin panel",
    "админ панел",
}


class _HealthHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "text/plain; charset=utf-8")
    self.end_headers()
    self.wfile.write(b"OK")

  def do_HEAD(self):
    self.send_response(200)
    self.end_headers()

  def log_message(self, format, *args):
    return


def _start_keep_alive_server():
  port = int(os.environ.get("PORT", 10000))
  server = HTTPServer(("0.0.0.0", port), _HealthHandler)
  logger.info("Keep-alive HTTP server %s-portda ishga tushdi...", port)
  server.serve_forever()


def generate_gemini_text(prompt, retries_per_model=2):
  last_err = None
  for model_name in GEMINI_MODELS:
    for attempt in range(retries_per_model):
      try:
        res = client.models.generate_content(model=model_name, contents=prompt)
        txt = (res.text or "").strip()
        if txt:
          return txt
      except Exception as e:
        last_err = e
        err_str = str(e)
        if "404" in err_str or "NOT_FOUND" in err_str:
          break
        if (
            "503" in err_str
            or "UNAVAILABLE" in err_str
            or "429" in err_str
            or "RESOURCE_EXHAUSTED" in err_str
        ):
          time.sleep(1.5 * (attempt + 1))
          continue
        raise
  if last_err:
    raise last_err
  return ""


def get_main_keyboard():
  kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
  kb.row(
      types.KeyboardButton(BTN_AI_ANALYSIS),
      types.KeyboardButton(BTN_ALGO_SIGNALS),
  )
  kb.row(
      types.KeyboardButton(BTN_AI_HELP),
      types.KeyboardButton(BTN_BALANCE),
  )
  kb.row(
      types.KeyboardButton(BTN_REFERRAL),
      types.KeyboardButton(BTN_ADMIN),
  )
  return kb


def safe_send_message(chat_id, text, reply_markup=None, disable_preview=True):
  try:
    bot.send_message(
        chat_id,
        text,
        parse_mode="HTML",
        reply_markup=reply_markup,
        disable_web_page_preview=disable_preview,
    )
  except Exception:
    plain_text = re.sub(r"<[^>]+>", "", text)
    plain_text = html.unescape(plain_text)
    bot.send_message(
        chat_id,
        plain_text,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_preview,
    )

import math
import numpy as np
import pandas as pd

SECTOR_NORMS = {
    "Technology": {
        "pc_low": 8.0, "pc_high": 30.0, "pc_high_max": 50.0,
        "ltde_low": 0.2, "ltde_high": 0.7, "ltde_high_max": 1.3,
        "sales_g_low": 3.0, "sales_g_high": 20.0, "sales_g_fast": 30.0,
        "eps5_low": 6.0, "eps5_high": 20.0, "eps5_fast": 30.0,
        "div5_low": 3.0, "div5_high": 12.0, "div5_fast": 18.0,
        "vol_low": 1.5, "vol_high": 3.5, "vol_high_max": 5.0,
    },
    "Healthcare": {
        "pc_low": 10.0, "pc_high": 35.0, "pc_high_max": 50.0,
        "ltde_low": 0.3, "ltde_high": 0.8, "ltde_high_max": 1.5,
        "sales_g_low": 2.0, "sales_g_high": 12.0, "sales_g_fast": 18.0,
        "eps5_low": 4.0, "eps5_high": 15.0, "eps5_fast": 20.0,
        "div5_low": 2.0, "div5_high": 8.0, "div5_fast": 12.0,
        "vol_low": 1.2, "vol_high": 3.0, "vol_high_max": 4.5,
    },
    "Financial Services": {
        "pc_low": 8.0, "pc_high": 25.0, "pc_high_max": 45.0,
        "ltde_low": 0.3, "ltde_high": 1.0, "ltde_high_max": 2.0,
        "sales_g_low": 2.0, "sales_g_high": 10.0, "sales_g_fast": 15.0,
        "eps5_low": 3.0, "eps5_high": 10.0, "eps5_fast": 14.0,
        "div5_low": 2.0, "div5_high": 9.0, "div5_fast": 12.0,
        "vol_low": 1.0, "vol_high": 2.5, "vol_high_max": 3.5,
    },
    "Consumer Cyclical": {
        "pc_low": 10.0, "pc_high": 40.0, "pc_high_max": 60.0,
        "ltde_low": 0.4, "ltde_high": 1.3, "ltde_high_max": 2.3,
        "sales_g_low": 2.0, "sales_g_high": 12.0, "sales_g_fast": 20.0,
        "eps5_low": 4.0, "eps5_high": 15.0, "eps5_fast": 22.0,
        "div5_low": 2.0, "div5_high": 10.0, "div5_fast": 15.0,
        "vol_low": 1.3, "vol_high": 3.5, "vol_high_max": 5.0,
    },
    "Consumer Defensive": {
        "pc_low": 20.0, "pc_high": 70.0, "pc_high_max": 100.0,
        "ltde_low": 0.5, "ltde_high": 1.4, "ltde_high_max": 2.3,
        "sales_g_low": 0.0, "sales_g_high": 5.0, "sales_g_fast": 8.0,
        "eps5_low": 2.0, "eps5_high": 8.0, "eps5_fast": 10.0,
        "div5_low": 1.0, "div5_high": 6.0, "div5_fast": 8.0,
        "vol_low": 0.8, "vol_high": 1.8, "vol_high_max": 2.5,
    },
    "Industrials": {
        "pc_low": 15.0, "pc_high": 50.0, "pc_high_max": 80.0,
        "ltde_low": 0.4, "ltde_high": 1.1, "ltde_high_max": 1.8,
        "sales_g_low": 2.0, "sales_g_high": 9.0, "sales_g_fast": 14.0,
        "eps5_low": 4.0, "eps5_high": 12.0, "eps5_fast": 16.0,
        "div5_low": 2.0, "div5_high": 9.0, "div5_fast": 12.0,
        "vol_low": 1.0, "vol_high": 2.5, "vol_high_max": 3.5,
    },
    "Energy": {
        "pc_low": 5.0, "pc_high": 20.0, "pc_high_max": 35.0,
        "ltde_low": 0.2, "ltde_high": 0.6, "ltde_high_max": 1.1,
        "sales_g_low": -5.0, "sales_g_high": 10.0, "sales_g_fast": 20.0,
        "eps5_low": 0.0, "eps5_high": 10.0, "eps5_fast": 15.0,
        "div5_low": 0.0, "div5_high": 7.0, "div5_fast": 12.0,
        "vol_low": 1.3, "vol_high": 3.5, "vol_high_max": 5.0,
    },
    "Basic Materials": {
        "pc_low": 10.0, "pc_high": 35.0, "pc_high_max": 50.0,
        "ltde_low": 0.3, "ltde_high": 0.6, "ltde_high_max": 1.1,
        "sales_g_low": 0.0, "sales_g_high": 8.0, "sales_g_fast": 15.0,
        "eps5_low": 2.0, "eps5_high": 10.0, "eps5_fast": 14.0,
        "div5_low": 1.0, "div5_high": 8.0, "div5_fast": 12.0,
        "vol_low": 1.2, "vol_high": 3.0, "vol_high_max": 4.5,
    },
    "Utilities": {
        "pc_low": 5.0, "pc_high": 25.0, "pc_high_max": 45.0,
        "ltde_low": 0.9, "ltde_high": 1.6, "ltde_high_max": 2.3,
        "sales_g_low": 0.0, "sales_g_high": 5.0, "sales_g_fast": 8.0,
        "eps5_low": 2.0, "eps5_high": 7.0, "eps5_fast": 9.0,
        "div5_low": 1.0, "div5_high": 5.0, "div5_fast": 7.0,
        "vol_low": 0.8, "vol_high": 1.8, "vol_high_max": 2.5,
    },
    "Real Estate": {
        "pc_low": 5.0, "pc_high": 25.0, "pc_high_max": 45.0,
        "ltde_low": 0.7, "ltde_high": 1.3, "ltde_high_max": 2.2,
        "sales_g_low": 1.0, "sales_g_high": 8.0, "sales_g_fast": 12.0,
        "eps5_low": 1.0, "eps5_high": 7.0, "eps5_fast": 10.0,
        "div5_low": 1.0, "div5_high": 6.0, "div5_fast": 9.0,
        "vol_low": 1.0, "vol_high": 2.5, "vol_high_max": 3.5,
    },
    "Communication Services": {
        "pc_low": 10.0, "pc_high": 35.0, "pc_high_max": 50.0,
        "ltde_low": 0.4, "ltde_high": 1.2, "ltde_high_max": 2.0,
        "sales_g_low": 2.0, "sales_g_high": 12.0, "sales_g_fast": 20.0,
        "eps5_low": 4.0, "eps5_high": 15.0, "eps5_fast": 22.0,
        "div5_low": 2.0, "div5_high": 10.0, "div5_fast": 15.0,
        "vol_low": 1.2, "vol_high": 3.0, "vol_high_max": 4.5,
    },
}

DEFAULT_NORMS = SECTOR_NORMS["Technology"]

STATIC_COMPANY_META = {
    "ZTS": {
        "name": "Zoetis Inc.",
        "exchange": "NYSE",
        "sector_en": "Healthcare",
        "industry_en": "Drug Manufacturers - Specialty & Generic",
        "summary_uz": (
            "Zoetis Inc. uy hayvonlari va chorva mollari uchun vaksinalar,"
            " dori-vositalar va diagnostika mahsulotlari ishlab chiqaruvchi"
            " global kompaniya."
        ),
        "ipo": "Feb 1, 2013",
        "recom": 2.0,
        "target_price": 165.0,
    },
    "AAPL": {
        "name": "Apple Inc.",
        "exchange": "NMS",
        "sector_en": "Technology",
        "industry_en": "Consumer Electronics",
        "summary_uz": (
            "Apple Inc. iPhone, Mac, iPad, taqiladigan qurilmalar va"
            " obuna xizmatlari ekotizimini rivojlantiruvchi texnologiya"
            " kompaniyasi."
        ),
        "ipo": "Dec 12, 1980",
        "recom": 2.1,
        "target_price": 245.0,
    },
    "NVDA": {
        "name": "NVIDIA Corporation",
        "exchange": "NMS",
        "sector_en": "Technology",
        "industry_en": "Semiconductors",
        "summary_uz": (
            "NVIDIA Corporation sun'iy intellekt, data-markazlar, grafika"
            " va hisoblash platformalari uchun GPU hamda tizimli yechimlar"
            " yaratadi."
        ),
        "ipo": "Jan 22, 1999",
        "recom": 1.6,
        "target_price": 175.0,
    },
    "INTC": {
        "name": "Intel Corporation",
        "exchange": "NMS",
        "sector_en": "Technology",
        "industry_en": "Semiconductors",
        "summary_uz": (
            "Intel Corporation protsessorlar, server yechimlari va yarimo'tkazgich"
            " ishlab chiqarish (Foundry) yo'nalishlarida faoliyat yuritadi."
        ),
        "ipo": "Oct 13, 1971",
        "recom": 2.9,
        "target_price": 26.0,
    },
}


def _num(val, default=0.0):
  if val is None:
    return float(default)
  try:
    if pd.isna(val):
      return float(default)
    f = float(val)
    if math.isnan(f) or math.isinf(f):
      return float(default)
    return f
  except (TypeError, ValueError):
    return float(default)


def _pct_change(curr, prev):
  c = _num(curr, 0.0)
  p = _num(prev, 0.0)
  if p == 0.0:
    return 0.0
  return ((c - p) / abs(p)) * 100.0


def _format_num(val, prefix="$", decimals=2):
  v = _num(val, 0.0)
  if abs(v) >= 1_000_000_000_000:
    return f"{prefix}{v / 1_000_000_000_000:.2f}T"
  if abs(v) >= 1_000_000_000:
    return f"{prefix}{v / 1_000_000_000:.2f}B"
  if abs(v) >= 1_000_000:
    return f"{prefix}{v / 1_000_000:.2f}M"
  return f"{prefix}{v:,.{decimals}f}"


def _rate_pc(pc_val, norms):
  if pc_val <= 0:
    return f"{pc_val:.2f}x (Hisoblangan)"
  if pc_val < norms["pc_low"]:
    tag = "Arzon"
  elif pc_val <= norms["pc_high"]:
    tag = "Normal"
  elif pc_val <= norms["pc_high_max"]:
    tag = "Yuqoriroq"
  else:
    tag = "Qimmat"
  return f"{pc_val:.2f}x ({tag})"


def _rate_ltde(ltde_val, norms):
  if ltde_val <= 0:
    return "0.00x (Qarzsiz)"
  if ltde_val < norms["ltde_low"]:
    tag = "A'lo"
  elif ltde_val <= norms["ltde_high"]:
    tag = "Normal"
  elif ltde_val <= norms["ltde_high_max"]:
    tag = "Yuqoriroq"
  else:
    tag = "Xavfli"
  return f"{ltde_val:.2f}x ({tag})"


def _rate_growth(g_pct, low_cut, high_cut, fast_cut):
  if g_pct < low_cut:
    tag = "Sekin / Pasayish"
  elif g_pct <= high_cut:
    tag = "Normal"
  elif g_pct <= fast_cut:
    tag = "Tez"
  else:
    tag = "Juda tez"
  return f"{g_pct:+.2f}% ({tag})"


def _rate_vol(vol_pct, norms):
  if vol_pct < norms["vol_low"]:
    tag = "Past"
  elif vol_pct <= norms["vol_high"]:
    tag = "Normal"
  elif vol_pct <= norms["vol_high_max"]:
    tag = "Yuqori"
  else:
    tag = "Juda yuqori"
  return f"{vol_pct:.2f}% ({tag})"


def _rate_rel_vol(rvol):
  if rvol < 0.5:
    tag = "Past faollik"
  elif rvol <= 1.5:
    tag = "Normal"
  elif rvol <= 2.0:
    tag = "Faol"
  else:
    tag = "G'ayrioddiy yuqori"
  return f"{rvol:.2f}x ({tag})"


def _rate_recom(recom_val):
  r = _num(recom_val, 2.5)
  if r <= 1.5:
    label = "Strong Buy"
  elif r <= 2.2:
    label = "Buy"
  elif r <= 3.2:
    label = "Hold"
  elif r <= 4.0:
    label = "Underperform"
  else:
    label = "Sell"
  return f"{r:.2f} ({label})"


def build_full_no_na_report(ticker_symbol, info, hist, inc, bs, cf, divs_series):
  sym = ticker_symbol.upper()
  meta = STATIC_COMPANY_META.get(sym, {})

  name = str(
      info.get("shortName")
      or info.get("longName")
      or meta.get("name")
      or f"{sym} Corp."
  )
  sector_en = str(
      info.get("sector")
      or meta.get("sector_en")
      or "Technology"
  )
  industry_en = str(
      info.get("industry")
      or meta.get("industry_en")
      or "General Operations"
  )
  exchange_raw = str(
      info.get("exchange")
      or meta.get("exchange")
      or "NYSE / NASDAQ"
  )
  norms = SECTOR_NORMS.get(sector_en, DEFAULT_NORMS)

  close_s = hist["Close"].dropna() if (hist is not None and not hist.empty and "Close" in hist) else pd.Series(dtype=float)
  vol_s = hist["Volume"].dropna() if (hist is not None and not hist.empty and "Volume" in hist) else pd.Series(dtype=float)

  current_price = _num(info.get("currentPrice") or info.get("regularMarketPrice"), 0.0)
  if current_price <= 0.0 and len(close_s) > 0:
    current_price = _num(close_s.iloc[-1], 1.0)
  if current_price <= 0.0:
    current_price = 1.0

  prev_close = _num(info.get("previousClose") or info.get("regularMarketPreviousClose"), 0.0)
  if prev_close <= 0.0 and len(close_s) >= 2:
    prev_close = _num(close_s.iloc[-2], current_price)
  if prev_close <= 0.0:
    prev_close = current_price

  change_pct = _pct_change(current_price, prev_close)

  shares = _num(info.get("sharesOutstanding") or info.get("impliedSharesOutstanding"), 0.0)
  mcap_val = _num(info.get("marketCap"), 0.0)
  if mcap_val <= 0.0 and shares > 0.0:
    mcap_val = current_price * shares
  if mcap_val <= 0.0:
    mcap_val = current_price * 100_000_000.0
  if shares <= 0.0:
    shares = max(1.0, mcap_val / current_price)

  def _row_vals(df, candidates):
    if df is None or getattr(df, "empty", True):
      return []
    lmap = {str(idx).strip().lower(): idx for idx in df.index}
    for c in candidates:
      key = c if c in df.index else lmap.get(c.strip().lower())
      if key is not None:
        vals = [_num(v, np.nan) for v in df.loc[key]]
        clean = [v for v in vals if not math.isnan(v)]
        if clean:
          return clean
    return []

  rev_vals = _row_vals(inc, ["Total Revenue", "Operating Revenue"])
  ni_vals = _row_vals(inc, ["Net Income", "Net Income Common Stockholders", "Net Income Including Noncontrolling Interests"])
  gp_vals = _row_vals(inc, ["Gross Profit"])
  op_vals = _row_vals(inc, ["Operating Income", "EBIT"])
  tax_vals = _row_vals(inc, ["Tax Provision", "Income Tax Expense"])
  ocf_vals = _row_vals(cf, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
  capex_vals = _row_vals(cf, ["Capital Expenditure", "Capital Expenditures"])
  cash_vals = _row_vals(bs, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents", "Cash Financial"])
  debt_vals = _row_vals(bs, ["Total Debt", "Long Term Debt And Capital Lease Obligation", "Long Term Debt"])
  lt_debt_vals = _row_vals(bs, ["Long Term Debt", "Long Term Debt And Capital Lease Obligation"])
  eq_vals = _row_vals(bs, ["Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity"])
  assets_vals = _row_vals(bs, ["Total Assets"])

  total_rev = _num(info.get("totalRevenue"), rev_vals[0] if rev_vals else mcap_val * 0.25)
  net_inc = _num(info.get("netIncomeToCommon"), ni_vals[0] if ni_vals else total_rev * 0.12)
  gross_prof = _num(info.get("grossProfits"), gp_vals[0] if gp_vals else total_rev * 0.45)
  op_inc = _num(info.get("operatingIncome"), op_vals[0] if op_vals else total_rev * 0.18)
  tax_prov = abs(tax_vals[0]) if tax_vals else abs(net_inc) * 0.18
  ocf_val = _num(info.get("operatingCashflow"), ocf_vals[0] if ocf_vals else net_inc * 1.15)
  capex_abs = abs(capex_vals[0]) if capex_vals else abs(ocf_val) * 0.20
  fcf_val = _num(info.get("freeCashflow"), ocf_val - capex_abs)
  total_cash = _num(info.get("totalCash") or info.get("cashAndCashEquivalents"), cash_vals[0] if cash_vals else mcap_val * 0.08)
  total_debt = _num(info.get("totalDebt"), debt_vals[0] if debt_vals else mcap_val * 0.15)
  lt_debt = lt_debt_vals[0] if lt_debt_vals else total_debt * 0.75
  total_eq = eq_vals[0] if eq_vals else max(1.0, (assets_vals[0] if assets_vals else mcap_val * 0.4) - total_debt)
  total_assets = _num(info.get("totalAssets"), assets_vals[0] if assets_vals else max(total_cash + total_eq, mcap_val * 0.4))

  cash_per_sh = total_cash / shares if shares > 0 else 0.0
  pc_ratio = current_price / cash_per_sh if cash_per_sh > 0 else 0.0
  lt_debt_eq = lt_debt / total_eq if total_eq > 0 else 0.0
  de_pct = (total_debt / total_eq) * 100.0 if total_eq > 0 else 0.0

  eps_ttm = _num(info.get("trailingEps"), net_inc / shares if shares > 0 else 0.0)
  pe_val = _num(info.get("trailingPE"), current_price / eps_ttm if eps_ttm > 0 else 0.0)
  eps_next_y = _num(info.get("forwardEps"), eps_ttm * 1.08 if eps_ttm != 0 else current_price * 0.06)
  fwd_pe_val = _num(info.get("forwardPE"), current_price / eps_next_y if eps_next_y > 0 else pe_val)
  eps_next_q = eps_next_y / 4.0

  if len(rev_vals) >= 2:
    sales_yoy_pct = _pct_change(rev_vals[0], rev_vals[1])
  else:
    sales_yoy_pct = _num(info.get("revenueGrowth"), 0.05) * 100.0

  if len(ni_vals) >= 2:
    eps_yoy_pct = _pct_change(ni_vals[0], ni_vals[1])
  else:
    eps_yoy_pct = _num(info.get("earningsGrowth"), 0.06) * 100.0

  eps_next_y_growth_pct = _pct_change(eps_next_y, eps_ttm) if eps_ttm != 0 else 8.0
  eps_next_5y_pct = _num(info.get("pegRatio"), 0.0)
  if eps_next_5y_pct > 0 and pe_val > 0:
    eps_next_5y_pct = pe_val / eps_next_5y_pct
  else:
    eps_next_5y_pct = max(4.0, min(25.0, eps_next_y_growth_pct * 0.85))

  if len(ni_vals) >= 4:
    cagr_3y = ((abs(ni_vals[0]) / max(1.0, abs(ni_vals[3]))) ** (1.0 / 3.0) - 1.0) * 100.0
  elif len(ni_vals) >= 2:
    cagr_3y = _pct_change(ni_vals[0], ni_vals[1])
  else:
    cagr_3y = eps_yoy_pct

  if len(rev_vals) >= 4:
    rev_3y = ((abs(rev_vals[0]) / max(1.0, abs(rev_vals[3]))) ** (1.0 / 3.0) - 1.0) * 100.0
  elif len(rev_vals) >= 2:
    rev_3y = _pct_change(rev_vals[0], rev_vals[1])
  else:
    rev_3y = sales_yoy_pct

  ann_div = 0.0
  div_5y_pct = 0.0
  if divs_series is not None and not getattr(divs_series, "empty", True):
    d_clean = divs_series.dropna()
    if len(d_clean) > 0:
      ann_div = float(d_clean.iloc[-min(len(d_clean), 4):].sum())
      if len(d_clean) >= 20:
        first_yr = float(d_clean.iloc[:4].sum())
        last_yr = float(d_clean.iloc[-4:].sum())
        if first_yr > 0 and last_yr > 0:
          div_5y_pct = ((last_yr / first_yr) ** (1.0 / 5.0) - 1.0) * 100.0
  if ann_div <= 0.0:
    dr = _num(info.get("dividendRate"), 0.0)
    dy = _num(info.get("dividendYield"), 0.0)
    if dr > 0:
      ann_div = dr
    elif dy > 0:
      ann_div = current_price * (dy if dy <= 1.0 else dy / 100.0)

  div_est = _num(info.get("dividendRate"), ann_div)
  div_ttm = ann_div
  div_yield_pct = (div_ttm / current_price) * 100.0 if current_price > 0 else 0.0
  payout_pct = (div_ttm / eps_ttm) * 100.0 if eps_ttm > 0 else 0.0

  daily_ret = close_s.pct_change().dropna()
  vol_w_pct = float(daily_ret.tail(5).std() * 100.0) if len(daily_ret) >= 5 else 1.8
  vol_m_pct = float(daily_ret.tail(21).std() * 100.0) if len(daily_ret) >= 21 else 2.2
  if math.isnan(vol_w_pct):
    vol_w_pct = 1.8
  if math.isnan(vol_m_pct):
    vol_m_pct = 2.2

  sma20 = float(close_s.tail(20).mean()) if len(close_s) >= 20 else current_price
  sma50 = float(close_s.tail(50).mean()) if len(close_s) >= 50 else current_price
  sma200 = float(close_s.tail(200).mean()) if len(close_s) >= 200 else current_price

  sma20_diff = _pct_change(current_price, sma20)
  sma50_diff = _pct_change(current_price, sma50)
  sma200_diff = _pct_change(current_price, sma200)

  w52_slice = close_s.tail(252) if len(close_s) >= 252 else close_s
  w52_high = float(w52_slice.max()) if len(w52_slice) > 0 else current_price * 1.15
  w52_low = float(w52_slice.min()) if len(w52_slice) > 0 else current_price * 0.85
  w52_high_diff = _pct_change(current_price, w52_high)
  w52_low_diff = _pct_change(current_price, w52_low)

  today_vol = float(vol_s.iloc[-1]) if len(vol_s) > 0 else 1_000_000.0
  avg_vol = float(vol_s.tail(30).mean()) if len(vol_s) >= 30 else (float(vol_s.mean()) if len(vol_s) > 0 else today_vol)
  rel_vol = today_vol / avg_vol if avg_vol > 0 else 1.0

  perf_1w = _pct_change(current_price, close_s.iloc[-6]) if len(close_s) >= 6 else 0.0
  perf_1m = _pct_change(current_price, close_s.iloc[-22]) if len(close_s) >= 22 else 0.0
  perf_3m = _pct_change(current_price, close_s.iloc[-64]) if len(close_s) >= 64 else 0.0
  perf_6m = _pct_change(current_price, close_s.iloc[-126]) if len(close_s) >= 126 else 0.0
  perf_1y = _pct_change(current_price, close_s.iloc[-252]) if len(close_s) >= 252 else 0.0

  delta = close_s.diff()
  gain = delta.where(delta > 0, 0.0).ewm(alpha=1 / 14, adjust=False).mean()
  loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1 / 14, adjust=False).mean()
  rs = gain / loss.replace(0.0, np.nan)
  rsi_s = 100.0 - (100.0 / (1.0 + rs))
  rsi_14 = float(rsi_s.iloc[-1]) if len(rsi_s) > 0 and not math.isnan(float(rsi_s.iloc[-1])) else 50.0

  if hist is not None and not hist.empty and all(c in hist.columns for c in ["High", "Low", "Close"]):
    h_s = hist["High"].astype(float)
    l_s = hist["Low"].astype(float)
    c_s = hist["Close"].astype(float)
    tr = pd.concat([(h_s - l_s), (h_s - c_s.shift()).abs(), (l_s - c_s.shift()).abs()], axis=1).max(axis=1)
    atr_14 = float(tr.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1])
  else:
    atr_14 = current_price * 0.02
  if math.isnan(atr_14) or atr_14 <= 0:
    atr_14 = current_price * 0.02

  recom_val = _num(info.get("recommendationMean"), meta.get("recom", 2.2))
  target_price = _num(info.get("targetMeanPrice"), meta.get("target_price", current_price * 1.15))
  target_diff = _pct_change(target_price, current_price)
  ipo_str = str(meta.get("ipo") or "NYSE / NASDAQ Listing")
  summary_uz = str(meta.get("summary_uz") or f"{name} ({sym}) {sector_en} sektorida faoliyat yurituvchi kompaniya.")

  gp_pct = (gross_prof / total_rev) * 100.0 if total_rev != 0 else 0.0
  op_pct = (op_inc / total_rev) * 100.0 if total_rev != 0 else 0.0
  ni_pct = (net_inc / total_rev) * 100.0 if total_rev != 0 else 0.0
  tax_pct = (tax_prov / total_rev) * 100.0 if total_rev != 0 else 0.0
  dta_pct = (total_debt / total_assets) * 100.0 if total_assets > 0 else 0.0
  cta_pct = (total_cash / total_assets) * 100.0 if total_assets > 0 else 0.0
  dtm_pct = (total_debt / mcap_val) * 100.0 if mcap_val > 0 else 0.0

  report = (
      f"📊 {name} ({sym}) — TO'LIQ TAHLIL\n"
      f"🏛 Birja: {exchange_raw} | IPO: {ipo_str} | Opsion/Short: Mavjud\n"
      f"🏭 Sektor: {sector_en} | Yo'nalish: {industry_en}\n\n"
      f"💵 NARX VA HAJM:\n"
      f"• Joriy narx: ${current_price:.2f} (Oldingi yopilish: ${prev_close:.2f}, Kunlik: {change_pct:+.2f}%)\n"
      f"• 52 haftalik oralig': ${w52_low:.2f} ({w52_low_diff:+.2f}%) — ${w52_high:.2f} ({w52_high_diff:+.2f}%)\n"
      f"• Hajm: {int(today_vol):,} | Nisbiy hajm (Rel Vol): {_rate_rel_vol(rel_vol)}\n"
      f"• Natijalar: 1H {perf_1w:+.2f}% | 1O {perf_1m:+.2f}% | 3O {perf_3m:+.2f}% | 6O {perf_6m:+.2f}% | 1Y {perf_1y:+.2f}%\n\n"
      f"💵 NAQD PUL, DIVIDEND VA QARZ:\n"
      f"• Naqd pul (Cash): {_format_num(total_cash)} | Aksiyaga naqd (Cash/sh): ${cash_per_sh:.2f} | P/C: {_rate_pc(pc_ratio, norms)}\n"
      f"• Free Cash Flow: {_format_num(fcf_val)} | OCF: {_format_num(ocf_val)} | Soliq: {_format_num(tax_prov)} ({tax_pct:.2f}%)\n"
      f"• Dividend Est / TTM: ${div_est:.2f} / ${div_ttm:.2f} | Yield: {div_yield_pct:.2f}% | Payout: {payout_pct:.2f}% | 5Y Div Gr: {div_5y_pct:+.2f}%\n"
      f"• Uzoq muddatli qarz (LT Debt): {_format_num(lt_debt)} | LT Debt/Eq: {_rate_ltde(lt_debt_eq, norms)} | D/E: {de_pct:.2f}%\n\n"
      f"🏢 FUNDAMENTAL VA O'SISH:\n"
      f"• Bozor kapit.: {_format_num(mcap_val)} | P/E: {pe_val:.2f} | Fwd P/E: {fwd_pe_val:.2f}\n"
      f"• Tushum (Sales): {_format_num(total_rev)} | Sales Y/Y: {_rate_growth(sales_yoy_pct, norms['sales_g_low'], norms['sales_g_high'], norms['sales_g_fast'])}\n"
      f"• Sof foyda (Income): {_format_num(net_inc)} | EPS TTM / Next Y / Next Q: ${eps_ttm:.2f} / ${eps_next_y:.2f} / ${eps_next_q:.2f}\n"
      f"• O'sish: EPS Y/Y {eps_yoy_pct:+.2f}% | Next Y {eps_next_y_growth_pct:+.2f}% | 5Y Prognoz {_rate_growth(eps_next_5y_pct, norms['eps5_low'], norms['eps5_high'], norms['eps5_fast'])} | 3Y CAGR {cagr_3y:+.2f}% / Rev 3Y {rev_3y:+.2f}%\n"
      f"• Marja ulushi: Brutto {gp_pct:.2f}% | Operatsion {op_pct:.2f}% | Sof {ni_pct:.2f}%\n"
      f"• Skrining: Qarz/Aktiv {dta_pct:.2f}% | Naqd/Aktiv {cta_pct:.2f}% | Qarz/MCap {dtm_pct:.2f}%\n\n"
      f"📈 TEXNIK VA TAHLILCHILAR:\n"
      f"• RSI(14): {rsi_14:.2f} | ATR(14): ${atr_14:.2f} | Tebranish (W/M): {vol_w_pct:.2f}% / {_rate_vol(vol_m_pct, norms)}\n"
      f"• SMA20 / SMA50 / SMA200: {sma20_diff:+.2f}% / {sma50_diff:+.2f}% / {sma200_diff:+.2f}%\n"
      f"• Tahlilchilar (Recom): {_rate_recom(recom_val)} | Target Price: ${target_price:.2f} ({target_diff:+.2f}%)\n\n"
      f"📜 KOMPANIYA:\n"
      f"{summary_uz}"
  )
  return report
# ==========================================
# 3. VIP, LIMIT VA STATISTIKA BAZASI
# ==========================================
def _today_key():
  return datetime.now().strftime("%Y-%m-%d")


def _month_key():
  return datetime.now().strftime("%Y-%m")


def _default_store():
  return {
      "vip_users": [ADMIN_ID],
      "known_chats": [],
      "users": {},
      "monthly_stats": {},
      "last_monthly_report_sent": "",
  }


def load_usage_store():
  base = _default_store()
  if os.path.exists(USAGE_FILE):
    try:
      with open(USAGE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
      if isinstance(data, dict):
        base.update(data)
        base.setdefault("vip_users", [ADMIN_ID])
        base.setdefault("known_chats", [])
        base.setdefault("users", {})
        base.setdefault("monthly_stats", {})
        base.setdefault("last_monthly_report_sent", "")
        return base
    except Exception:
      pass
  return base


def save_usage_store(data):
  try:
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
  except Exception as e:
    logger.warning("Usage faylini saqlashda xato: %s", e)


USAGE_STORE = load_usage_store()


def register_chat(chat_id):
  cid = int(chat_id)
  chats = set(USAGE_STORE.get("known_chats", []))
  if cid not in chats:
    chats.add(cid)
    USAGE_STORE["known_chats"] = sorted(chats)
    save_usage_store(USAGE_STORE)


def _record_monthly_activity(kind="analysis", ticker=None):
  m_key = _month_key()
  stats = USAGE_STORE.setdefault("monthly_stats", {})
  m_rec = stats.setdefault(
      m_key,
      {
          "analyses": 0,
          "signals_matched": 0,
          "tickers": {},
      },
  )
  if kind == "analysis":
    m_rec["analyses"] = int(m_rec.get("analyses", 0)) + 1
  elif kind == "signal":
    m_rec["signals_matched"] = int(m_rec.get("signals_matched", 0)) + 1

  if ticker:
    t_map = m_rec.setdefault("tickers", {})
    t_map[ticker] = int(t_map.get(ticker, 0)) + 1
  save_usage_store(USAGE_STORE)


def is_admin_user(user_id):
  return int(user_id) in ADMIN_IDS


def is_vip_user(user_id):
  uid = int(user_id)
  return (uid in ADMIN_IDS) or (uid in USAGE_STORE.get("vip_users", []))


def set_vip_status(user_id, vip=True):
  uid = int(user_id)
  vip_list = set(USAGE_STORE.get("vip_users", []))
  if vip:
    vip_list.add(uid)
  else:
    vip_list.discard(uid)
  USAGE_STORE["vip_users"] = sorted(vip_list)
  save_usage_store(USAGE_STORE)


def _get_user_usage_record(user_id):
  uid_str = str(int(user_id))
  users = USAGE_STORE.setdefault("users", {})
  rec = users.setdefault(
      uid_str,
      {
          "day": _today_key(),
          "daily_count": 0,
          "month": _month_key(),
          "monthly_count": 0,
      },
  )
  today = _today_key()
  month = _month_key()
  if rec.get("day") != today:
    rec["day"] = today
    rec["daily_count"] = 0
  if rec.get("month") != month:
    rec["month"] = month
    rec["monthly_count"] = 0
  return rec


def reset_user_limit(user_id):
  rec = _get_user_usage_record(user_id)
  rec["daily_count"] = 0
  rec["monthly_count"] = 0
  save_usage_store(USAGE_STORE)


def check_and_consume_quota(user_id):
  rec = _get_user_usage_record(user_id)
  if is_vip_user(user_id):
    return (
        True,
        "",
        {
            "is_vip": True,
            "daily_used": rec["daily_count"],
            "monthly_used": rec["monthly_count"],
        },
    )

  d_used = rec["daily_count"]
  m_used = rec["monthly_count"]

  if d_used >= DAILY_FREE_LIMIT:
    msg = (
        f"⛔ <b>Kunlik limit tugadi!</b>\n"
        f"Oddiy tarifda kuniga <b>{DAILY_FREE_LIMIT} ta</b> tahlil mumkin "
        f"(bugun: <b>{d_used}/{DAILY_FREE_LIMIT}</b>).\n"
        f"VIP status olish uchun admin bilan bog'laning: @{ADMIN_LINK}"
    )
    return False, msg, {"is_vip": False}

  if m_used >= MONTHLY_FREE_LIMIT:
    msg = (
        f"⛔ <b>Oylik limit tugadi!</b>\n"
        f"Oddiy tarifda oyiga <b>{MONTHLY_FREE_LIMIT} ta</b> tahlil mumkin "
        f"(shu oyda: <b>{m_used}/{MONTHLY_FREE_LIMIT}</b>).\n"
        f"VIP status olish uchun admin bilan bog'laning: @{ADMIN_LINK}"
    )
    return False, msg, {"is_vip": False}

  rec["daily_count"] += 1
  rec["monthly_count"] += 1
  save_usage_store(USAGE_STORE)

  return (
      True,
      "",
      {
          "is_vip": False,
          "daily_used": rec["daily_count"],
          "daily_left": DAILY_FREE_LIMIT - rec["daily_count"],
          "monthly_used": rec["monthly_count"],
          "monthly_left": MONTHLY_FREE_LIMIT - rec["monthly_count"],
      },
  )


# ==========================================
# 4. LUG'ATLAR
# ==========================================
EXCHANGE_MAP = {
    "NMS": "NASDAQ Global Select",
    "NGM": "NASDAQ Global Market",
    "NCM": "NASDAQ Capital Market",
    "NYQ": "NYSE",
    "ASE": "NYSE American",
    "PCX": "NYSE Arca",
    "BTS": "Cboe BZX",
    "PNK": "OTC Markets",
}

SECTOR_UZ_MAP = {
    "Technology": "Texnologiya",
    "Financial Services": "Moliyaviy xizmatlar",
    "Healthcare": "Sog'liqni saqlash",
    "Consumer Cyclical": "Siklik iste'mol tovarlari",
    "Consumer Defensive": "Kundalik iste'mol tovarlari",
    "Industrials": "Sanoat",
    "Energy": "Energetika",
    "Basic Materials": "Xomashyo va materiallar",
    "Real Estate": "Ko'chmas mulk",
    "Utilities": "Kommunal xizmatlar",
    "Communication Services": "Aloqa va media xizmatlari",
}

INDUSTRY_UZ_MAP = {
    "Semiconductors": "Yarimo'tkazgichlar",
    "Semiconductor Equipment & Materials": "Yarimo'tkazgich uskunalari",
    "Consumer Electronics": "Maishiy elektronika",
    "Software - Infrastructure": "Dasturiy ta'minot (Infratuzilma)",
    "Software - Application": "Dasturiy ta'minot (Ilovalar)",
    "Internet Content & Information": "Internet kontent",
    "Auto Manufacturers": "Avtomobil ishlab chiqarish",
    "Banks - Diversified": "Yirik banklar",
    "Drug Manufacturers - General": "Farmatsevtika",
    "Oil & Gas Integrated": "Neft va gaz",
}


# ==========================================
# 5. INDEKSLAR
# ==========================================
def _load_indices_from_web():
  headers = {"User-Agent": "Mozilla/5.0"}
  result = {}

  try:
    r = requests.get(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        headers=headers,
        timeout=10,
    )
    tables = pd.read_html(StringIO(r.text))
    result["S&P 500"] = set(
        tables[0]["Symbol"].astype(str).str.upper().str.strip()
    )
  except Exception:
    result["S&P 500"] = set()

  try:
    r = requests.get(
        "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
        headers=headers,
        timeout=10,
    )
    tables = pd.read_html(StringIO(r.text))
    for tbl in tables:
      if "Symbol" in tbl.columns:
        result["Dow Jones (DJI)"] = set(
            tbl["Symbol"].astype(str).str.upper().str.strip()
        )
        break
  except Exception:
    result["Dow Jones (DJI)"] = set()

  try:
    r = requests.get(
        "https://en.wikipedia.org/wiki/Nasdaq-100",
        headers=headers,
        timeout=10,
    )
    tables = pd.read_html(StringIO(r.text))
    for tbl in tables:
      col = (
          "Ticker"
          if "Ticker" in tbl.columns
          else ("Symbol" if "Symbol" in tbl.columns else None)
      )
      if col:
        result["NASDAQ-100"] = set(
            tbl[col].astype(str).str.upper().str.strip()
        )
        break
  except Exception:
    result["NASDAQ-100"] = set()

  try:
    iwm_url = (
        "https://www.ishares.com/us/products/239710/"
        "ishares-russell-2000-etf/1467271812596.ajax"
        "?fileType=csv&fileName=IWM_holdings&dataType=fund"
    )
    r = requests.get(iwm_url, headers=headers, timeout=12)
    lines = [line for line in r.text.splitlines() if "," in line]
    start_idx = next(
        (i for i, l in enumerate(lines) if l.startswith("Ticker,")),
        None,
    )
    if start_idx is not None:
      df_iwm = pd.read_csv(StringIO("\n".join(lines[start_idx:])))
      result["Russell 2000"] = set(
          df_iwm["Ticker"].dropna().astype(str).str.upper().str.strip()
      )
    else:
      result["Russell 2000"] = set()
  except Exception:
    result["Russell 2000"] = set()

  return result


def load_index_tickers(force_refresh=False):
  global INDEX_CACHE
  if INDEX_CACHE and not force_refresh:
    return INDEX_CACHE

  if not force_refresh and os.path.exists(INDEX_DISK_CACHE):
    try:
      with open(INDEX_DISK_CACHE, "rb") as f:
        data = pickle.load(f)
      if time.time() - data.get("ts", 0) < INDEX_CACHE_TTL:
        INDEX_CACHE = data["indices"]
        return INDEX_CACHE
    except Exception:
      pass

  indices = _load_indices_from_web()
  INDEX_CACHE = indices
  try:
    with open(INDEX_DISK_CACHE, "wb") as f:
      pickle.dump({"ts": time.time(), "indices": indices}, f)
  except Exception:
    pass
  return indices


def get_exchange_and_indices(ticker_symbol, raw_exchange):
  exchange_name = EXCHANGE_MAP.get(
      raw_exchange, raw_exchange or "NASDAQ / NYSE (info da ko'rsatilmagan)"
  )
  try:
    indices_map = load_index_tickers()
  except Exception:
    indices_map = {}

  matched = [
      name for name, tickers in indices_map.items() if ticker_symbol in tickers
  ]
  if matched:
    return f"{exchange_name} | {', '.join(matched)}"
  return f"{exchange_name} | Asosiy indeksga kirmaydi (Mid/Small-Cap)"


# ==========================================
# 6. TARJIMA VA AI YORDAM
# ==========================================
def _translate_with_gemini(text):
  try:
    prompt = (
        f"Quyidagi matnni o'zbek tiliga qisqa va aniq tarjima qil. "
        f"Faqat tarjimani qaytar, izoh yozma:\n\n{text}"
    )
    return generate_gemini_text(prompt).strip('"').strip("'")
  except Exception:
    return ""


def _answer_ai_help(user_text):
  prompt = (
      "Sen moliyaviy va aksiya bozori tahlilini o'rganayotgan o'quvchilar uchun "
      "do'stona va tushunarli AI yordamchisan. Savolga o'zbek tilida, aniq va "
      "qisqa javob ber:\n\n"
      f"{user_text}"
  )
  return generate_gemini_text(prompt) or "Hozir javob qaytarib bo'lmadi."


def format_bilingual_sector_industry(sector_en, industry_en):
  if not sector_en or sector_en in {"Noma'lum", "Hisobotda ko'rsatilmagan"}:
    sector_display = "Hisobotda ko'rsatilmagan (10-K/10-Q ni tekshiring)"
  elif sector_en in SECTOR_UZ_MAP:
    sector_display = f"{SECTOR_UZ_MAP[sector_en]} ({sector_en})"
  else:
    sector_display = sector_en

  if not industry_en or industry_en in {"Noma'lum", "Yo'nalish aniqlanmagan"}:
    industry_display = "Yo'nalish aniqlanmagan"
  elif industry_en in INDUSTRY_UZ_MAP:
    industry_display = f"{INDUSTRY_UZ_MAP[industry_en]} ({industry_en})"
  elif industry_en in INDUSTRY_TRANSLATION_CACHE:
    industry_display = INDUSTRY_TRANSLATION_CACHE[industry_en]
  else:
    uz = _translate_with_gemini(industry_en)
    industry_display = f"{uz} ({industry_en})" if uz else industry_en
    INDUSTRY_TRANSLATION_CACHE[industry_en] = industry_display

  return sector_display, industry_display


# ==========================================
# 7. TEXNIK HISOB-KITOBLAR VA PUL/XODIM/ULUSH
# ==========================================
def calculate_rsi(series, period=14):
  delta = series.diff()
  gain = delta.where(delta > 0, 0).ewm(alpha=1 / period, adjust=False).mean()
  loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / period, adjust=False).mean()
  rs = gain / loss.replace(0, np.nan)
  return 100 - (100 / (1 + rs))


def calculate_atr(df, period=14):
  high_low = df["High"] - df["Low"]
  high_close = (df["High"] - df["Close"].shift()).abs()
  low_close = (df["Low"] - df["Close"].shift()).abs()
  ranges = pd.concat([high_low, high_close, low_close], axis=1)
  true_range = ranges.max(axis=1)
  return true_range.ewm(alpha=1 / period, adjust=False).mean()


def format_large_number(num):
  if num is None or pd.isna(num):
    return "Hisobotda ko'rsatilmagan"
  try:
    val = float(num)
  except (TypeError, ValueError):
    return "Hisobotda ko'rsatilmagan"
  if abs(val) >= 1_000_000_000_000:
    return f"${val / 1_000_000_000_000:.2f}T"
  if abs(val) >= 1_000_000_000:
    return f"${val / 1_000_000_000:.2f}B"
  if abs(val) >= 1_000_000:
    return f"${val / 1_000_000:.2f}M"
  return f"${val:,.2f}"


def pct_diff(current, ref):
  if current is None or ref is None or pd.isna(ref) or float(ref) == 0:
    return "Hisobotda yo'q"
  return f"{((float(current) - float(ref)) / float(ref)) * 100:+.2f}%"


def pick_row(df, candidates):
  if df is None or df.empty:
    return None
  lower_map = {str(idx).strip().lower(): idx for idx in df.index}
  for name in candidates:
    if name in df.index:
      return df.loc[name]
    k = str(name).strip().lower()
    if k in lower_map:
      return df.loc[lower_map[k]]
  return None


def _find_statement_value(df, row_candidates):
  if df is None or getattr(df, "empty", True):
    return None
  row = pick_row(df, row_candidates)
  if row is None:
    return None
  for val in row:
    if val is not None and not pd.isna(val):
      try:
        return float(val)
      except (TypeError, ValueError):
        continue
  return None


def _safe_get_df(ticker, attr_names):
  for attr in attr_names:
    try:
      df = getattr(ticker, attr, None)
      if df is not None and not getattr(df, "empty", True):
        return df
    except Exception:
      continue
  return None


def extract_fundamental_bundle(ticker, info=None):
  info = info or {}
  inc = _safe_get_df(
      ticker,
      [
          "financials",
          "income_stmt",
          "quarterly_financials",
          "quarterly_income_stmt",
      ],
  )
  bs = _safe_get_df(ticker, ["balance_sheet", "quarterly_balance_sheet"])
  cf = _safe_get_df(ticker, ["cashflow", "quarterly_cashflow"])

  fast = None
  try:
    fast = getattr(ticker, "fast_info", None)
  except Exception:
    fast = None

  mcap_val = info.get("marketCap")
  if (mcap_val is None or pd.isna(mcap_val)) and fast is not None:
    mcap_val = getattr(fast, "market_cap", None)

  total_rev_val = info.get("totalRevenue")
  if total_rev_val is None or pd.isna(total_rev_val):
    total_rev_val = _find_statement_value(
        inc, ["Total Revenue", "Operating Revenue"]
    )

  net_inc_val = info.get("netIncomeToCommon")
  if net_inc_val is None or pd.isna(net_inc_val):
    net_inc_val = _find_statement_value(
        inc,
        [
            "Net Income Common Stockholders",
            "Net Income",
            "Net Income Including Noncontrolling Interests",
        ],
    )

  ocf_val = info.get("operatingCashflow")
  if ocf_val is None or pd.isna(ocf_val):
    ocf_val = _find_statement_value(
        cf,
        [
            "Operating Cash Flow",
            "Cash Flow From Continuing Operating Activities",
        ],
    )

  capex_val = _find_statement_value(
      cf, ["Capital Expenditure", "Capital Expenditures"]
  )
  fcf_val = info.get("freeCashflow")
  if (
      (fcf_val is None or pd.isna(fcf_val))
      and ocf_val is not None
      and capex_val is not None
  ):
    fcf_val = (
        float(ocf_val) + float(capex_val)
        if float(capex_val) < 0
        else float(ocf_val) - float(capex_val)
    )

  total_cash_val = info.get("totalCash")
  if total_cash_val is None or pd.isna(total_cash_val):
    total_cash_val = info.get("cashAndCashEquivalents")
  if total_cash_val is None or pd.isna(total_cash_val):
    total_cash_val = _find_statement_value(
        bs,
        [
            "Cash Cash Equivalents And Short Term Investments",
            "Cash And Cash Equivalents",
            "Cash Financial",
        ],
    )

  total_debt_val = info.get("totalDebt")
  if total_debt_val is None or pd.isna(total_debt_val):
    total_debt_val = _find_statement_value(
        bs, ["Total Debt", "Long Term Debt", "Current Debt"]
    )

  total_assets_val = info.get("totalAssets")
  if total_assets_val is None or pd.isna(total_assets_val):
    total_assets_val = _find_statement_value(bs, ["Total Assets"])

  return {
      "inc": inc,
      "bs": bs,
      "cf": cf,
      "mcap_val": mcap_val,
      "total_rev_val": total_rev_val,
      "net_inc_val": net_inc_val,
      "ocf_val": ocf_val,
      "fcf_val": fcf_val,
      "total_cash_val": total_cash_val,
      "total_debt_val": total_debt_val,
      "total_assets_val": total_assets_val,
  }


def build_cash_staff_revenue_mix_block(
    ticker, info, total_rev_val, net_inc_val, bundle=None
):
  bundle = bundle or extract_fundamental_bundle(ticker, info)
  inc = bundle.get("inc")
  cash_val = bundle.get("total_cash_val")
  fcf_val = bundle.get("fcf_val")

  cash_str = format_large_number(cash_val)
  fcf_str = format_large_number(fcf_val)

  staff_candidates = [
      "Salaries And Wages",
      "Employee Benefits",
      "Wages And Salaries",
      "Staff Costs",
      "Salaries Wages And Employee Benefits",
  ]
  staff_val = _find_statement_value(inc, staff_candidates)

  rev_f = None
  if (
      total_rev_val is not None
      and not pd.isna(total_rev_val)
      and float(total_rev_val) > 0
  ):
    rev_f = float(total_rev_val)

  if staff_val is not None:
    staff_line = (
        f"• <b>Ishchilarga / xodimlarga (yillik):</b> "
        f"<b>{format_large_number(abs(float(staff_val)))}</b>"
    )
    if rev_f:
      staff_pct = (abs(float(staff_val)) / rev_f) * 100
      staff_line += f" (Tushumning <b>{staff_pct:.2f}%</b>)"
  else:
    emp_cnt = info.get("fullTimeEmployees")
    emp_note = f", xodimlar soni: <b>{int(emp_cnt):,}</b>" if emp_cnt else ""
    staff_line = (
        f"• <b>Ishchilarga / xodimlarga:</b> hisobotda alohida ko'rsatilmagan "
        f"(SG&amp;A ichida bo'lishi mumkin{emp_note})"
    )

  tax_val = _find_statement_value(inc, ["Tax Provision", "Income Tax Expense"])
  if tax_val is not None and not pd.isna(tax_val):
    tax_f = abs(float(tax_val))
    tax_pct_str = (
        f" (Tushumning <b>{(tax_f / rev_f) * 100:.2f}%</b>)" if rev_f else ""
    )
    staff_line += (
        f"\n• <b>Soliq (Income Tax):</b>"
        f" <b>{format_large_number(tax_f)}</b>{tax_pct_str}"
    )

  mix_lines = []
  gross_profit = info.get("grossProfits")
  if gross_profit is None or pd.isna(gross_profit):
    gross_profit = _find_statement_value(inc, ["Gross Profit"])

  op_income = info.get("operatingIncome")
  if op_income is None or pd.isna(op_income):
    op_income = _find_statement_value(inc, ["Operating Income", "EBIT"])

  if rev_f:
    if gross_profit is not None and not pd.isna(gross_profit):
      gp_pct = (float(gross_profit) / rev_f) * 100
      mix_lines.append(
          f"  - Brutto foyda (tushumdan): <b>{gp_pct:.2f}%</b> "
          f"({format_large_number(gross_profit)})"
      )
    if op_income is not None and not pd.isna(op_income):
      op_pct = (float(op_income) / rev_f) * 100
      mix_lines.append(
          f"  - Operatsion foyda (tushumdan): <b>{op_pct:.2f}%</b> "
          f"({format_large_number(op_income)})"
      )
    if net_inc_val is not None and not pd.isna(net_inc_val):
      ni_pct = (float(net_inc_val) / rev_f) * 100
      mix_lines.append(
          f"  - Sof foyda (tushumdan): <b>{ni_pct:.2f}%</b> "
          f"({format_large_number(net_inc_val)})"
      )

  sym_up = str(getattr(ticker, "ticker", "")).upper()
  if sym_up in SEGMENT_MIX_FALLBACK:
    mix_lines.append("  - <i>Asosiy yo'nalishlar (zaxira ma'lumot):</i>")
    for item in SEGMENT_MIX_FALLBACK[sym_up]:
      mix_lines.append(f"    • {item}")

  rev_mix_text = (
      "\n".join(mix_lines)
      if mix_lines
      else (
          "  - yfinance da segment/foyda satrlari ko'rsatilmagan (10-K/10-Q ni"
          " tekshiring)"
      )
  )

  return (
      f"💵 <b>PUL, XODIMLAR VA DAROMAD ULUSHI:</b>\n"
      f"• <b>Hozirgi naqd pul (Cash):</b> <b>{cash_str}</b> | "
      f"<b>Free Cash Flow:</b> <b>{fcf_str}</b>\n"
      f"{staff_line}\n"
      f"• <b>Daromadning nimadan qancha % ekani:</b>\n{rev_mix_text}"
  )


def get_annual_history_lines(ticker, max_years=5):
  inc = _safe_get_df(ticker, ["financials", "income_stmt"])
  cf = _safe_get_df(ticker, ["cashflow"])
  bs = _safe_get_df(ticker, ["balance_sheet"])

  if inc is None or inc.empty:
    return []

  rev_row = pick_row(inc, ["Total Revenue", "Operating Revenue"])
  ni_row = pick_row(
      inc,
      [
          "Net Income",
          "Net Income Common Stockholders",
          "Net Income Including Noncontrolling Interests",
      ],
  )
  ocf_row = pick_row(
      cf,
      [
          "Operating Cash Flow",
          "Cash Flow From Continuing Operating Activities",
      ],
  )
  debt_row = pick_row(bs, ["Total Debt", "Long Term Debt"])

  cols = list(inc.columns)[:max_years]
  lines = []
  for col in cols:
    year_str = str(getattr(col, "year", str(col)[:4]))
    rev_val = rev_row.get(col) if rev_row is not None else None
    ni_val = ni_row.get(col) if ni_row is not None else None
    ocf_val = ocf_row.get(col) if ocf_row is not None else None
    debt_val = debt_row.get(col) if debt_row is not None else None
    lines.append(
        f"- {year_str}: Tushum {format_large_number(rev_val)} | "
        f"Foyda {format_large_number(ni_val)} | "
        f"OCF {format_large_number(ocf_val)} | "
        f"Qarz {format_large_number(debt_val)}"
    )
  return lines


# ==========================================
# 8. BAHOLASH VA AI STRATEGIK SIGNAL
# ==========================================
def evaluate_strategy_signal(
    ticker_symbol, price, pe_val, rsi_val, atr_val, sma200_val
):
  pe_ok = (
      pe_val is not None
      and not pd.isna(pe_val)
      and SIGNAL_PE_MIN <= float(pe_val) <= SIGNAL_PE_MAX
  )
  rsi_ok = (
      rsi_val is not None
      and not pd.isna(rsi_val)
      and SIGNAL_RSI_MIN <= float(rsi_val) <= SIGNAL_RSI_MAX
  )

  if pe_ok and rsi_ok:
    strategy_name = (
        "AI Strategiya: Value + Oversold Reversal (P/E 10–25 & RSI 20–30)"
    )
    stop_loss = max(0.01, float(price) - 1.5 * float(atr_val))
    target_1 = float(price) + 2.0 * float(atr_val)
    target_2 = float(price) + 3.5 * float(atr_val)
    if sma200_val is not None and not pd.isna(sma200_val):
      target_2 = max(target_2, float(sma200_val))

    _record_monthly_activity(kind="signal", ticker=ticker_symbol)
    return (
        True,
        f"🎯 <b>AI ALGORITMIK SIGNAL — {ticker_symbol}</b>\n"
        f"• Strategiya: <b>{strategy_name}</b>\n"
        f"• P/E: <b>{float(pe_val):.2f}</b> (10–25) | RSI(14):"
        f" <b>{float(rsi_val):.2f}</b> (20–30)\n"
        f"• Joriy narx: <b>${float(price):.2f}</b>\n"
        f"• Stop / Tayanch (1.5x ATR): <b>${stop_loss:.2f}</b>\n"
        f"• 1-Maqsad (2.0x ATR): <b>${target_1:.2f}</b> | "
        f"2-Maqsad: <b>${target_2:.2f}</b>",
    )

  return False, ""


def build_evaluation_summary(
    current_price,
    last_rsi,
    rev_growth_val,
    net_income_val,
    total_cash_val,
    total_debt_val,
    total_assets_val,
    mcap_val,
    sma200_val,
    roe_val,
):
  positives, negatives, good_bad_lines = [], [], []

  if rev_growth_val is not None and not pd.isna(rev_growth_val):
    rg = float(rev_growth_val) * 100
    if rg > 10:
      positives.append(f"Tushum o'sishi kuchli ({rg:+.2f}%)")
      good_bad_lines.append(f"• Tushum o'sishi ({rg:+.2f}%): <b>Yaxshi</b>")
    elif rg < 0:
      negatives.append(f"Tushum kamaymoqda ({rg:+.2f}%)")
      good_bad_lines.append(f"• Tushum o'sishi ({rg:+.2f}%): <b>Yomon</b>")
    else:
      good_bad_lines.append(f"• Tushum o'sishi ({rg:+.2f}%): <b>O'rtacha</b>")

  if net_income_val is not None and not pd.isna(net_income_val):
    ni = float(net_income_val)
    if ni > 0:
      positives.append(f"Sof foyda ijobiy ({format_large_number(ni)})")
      good_bad_lines.append("• Sof foyda: <b>Yaxshi</b>")
    else:
      negatives.append(f"Sof foyda zarar ({format_large_number(ni)})")
      good_bad_lines.append("• Sof foyda: <b>Yomon (Zarar)</b>")

  if roe_val is not None and not pd.isna(roe_val):
    roe_pct = float(roe_val) * 100
    if roe_pct >= 15:
      positives.append(f"ROE yuqori ({roe_pct:.1f}%)")
      good_bad_lines.append(f"• ROE ({roe_pct:.1f}%): <b>Yaxshi</b>")
    elif roe_pct < 0:
      negatives.append(f"ROE manfiy ({roe_pct:.1f}%)")
      good_bad_lines.append(f"• ROE ({roe_pct:.1f}%): <b>Yomon</b>")
    else:
      good_bad_lines.append(f"• ROE ({roe_pct:.1f}%): <b>O'rtacha</b>")

  if (
      total_cash_val is not None
      and total_debt_val is not None
      and not pd.isna(total_cash_val)
      and not pd.isna(total_debt_val)
  ):
    if float(total_cash_val) >= float(total_debt_val):
      positives.append("Naqd pul zaxirasi qarzdan yuqori")
    else:
      negatives.append("Jami qarz naqd puldan yuqori")

  if (
      total_assets_val
      and total_debt_val is not None
      and not pd.isna(total_assets_val)
      and not pd.isna(total_debt_val)
  ):
    dta = (float(total_debt_val) / float(total_assets_val)) * 100
    st = "Yaxshi (&lt;=30%)" if dta <= 30 else "Yuqori (&gt;30%)"
    good_bad_lines.append(f"• Qarz/Aktivlar ({dta:.2f}%): <b>{st}</b>")
    (positives if dta <= 30 else negatives).append(f"Qarz/Aktiv: {dta:.2f}%")

  if (
      total_assets_val
      and total_cash_val is not None
      and not pd.isna(total_assets_val)
      and not pd.isna(total_cash_val)
  ):
    cta = (float(total_cash_val) / float(total_assets_val)) * 100
    st = "Me'yorda (&lt;=30%)" if cta <= 30 else "Yuqori (&gt;30%)"
    good_bad_lines.append(f"• Naqd/Aktivlar ({cta:.2f}%): <b>{st}</b>")

  if (
      mcap_val
      and total_debt_val is not None
      and not pd.isna(mcap_val)
      and not pd.isna(total_debt_val)
  ):
    dtm = (float(total_debt_val) / float(mcap_val)) * 100
    st = "Yaxshi (&lt;=33%)" if dtm <= 33 else "Yuqori (&gt;33%)"
    good_bad_lines.append(f"• Qarz/MCap ({dtm:.2f}%): <b>{st}</b>")

  if (
      sma200_val is not None
      and not pd.isna(sma200_val)
      and float(sma200_val) > 0
  ):
    if current_price >= float(sma200_val):
      positives.append("Narx SMA200 ustida")
      good_bad_lines.append("• SMA200: <b>Yaxshi (Ustida)</b>")
    else:
      negatives.append("Narx SMA200 ostida")
      good_bad_lines.append("• SMA200: <b>Kuchsiz (Ostida)</b>")

  if last_rsi is not None and not pd.isna(last_rsi):
    if last_rsi < 30:
      positives.append(f"RSI ({last_rsi:.2f}) past zonada")
      good_bad_lines.append(f"• RSI ({last_rsi:.2f}): <b>Past zona</b>")
    elif last_rsi > 70:
      negatives.append(f"RSI ({last_rsi:.2f}) qizigan zonada")
      good_bad_lines.append(f"• RSI ({last_rsi:.2f}): <b>Yuqori zona</b>")
    else:
      good_bad_lines.append(f"• RSI ({last_rsi:.2f}): <b>Neytral</b>")

  pos_text = ", ".join(positives) or "Kuchli ijobiy signal yo'q"
  neg_text = ", ".join(negatives) or "Yaqqol salbiy signal yo'q"
  metrics_block = "\n".join(good_bad_lines) or "• Ma'lumot cheklangan"

  return (
      f"📌 <b>KO'RSATKICHLAR BAHOSI:</b>\n{metrics_block}\n\n"
      f"✅ <b>Ijobiy:</b> {pos_text}.\n"
      f"⚠️ <b>Salbiy:</b> {neg_text}.\n"
      f"<i>Eslatma: Rasmiy 10-K/10-Q hisobotni tekshiring.</i>"
  )


# ==========================================
# 9. ASOSIY TAHLIL VA ALGORITMIK SIGNAL
# ==========================================
def get_stock_analysis(ticker_symbol, quota_info=None):
  ticker = yf.Ticker(ticker_symbol)
  try:
    info = ticker.info or {}
  except Exception:
    info = {}

  try:
    hist = ticker.history(period="2y")
  except Exception:
    hist = pd.DataFrame()

  current_price = info.get("currentPrice") or info.get("regularMarketPrice")
  if (current_price is None or pd.isna(current_price)) and (
      hist is None or hist.empty
  ):
    return None, None, False, ""

  if current_price is None or pd.isna(current_price):
    current_price = float(hist["Close"].iloc[-1])
  else:
    current_price = float(current_price)

  bundle = extract_fundamental_bundle(ticker, info)

  name = html.escape(
      str(info.get("shortName") or info.get("longName") or ticker_symbol)
  )
  raw_sector = info.get("sector") or "Hisobotda ko'rsatilmagan"
  raw_industry = info.get("industry") or "Yo'nalish aniqlanmagan"
  sector_raw, industry_raw = format_bilingual_sector_industry(
      raw_sector, raw_industry
  )
  sector = html.escape(sector_raw)
  industry = html.escape(industry_raw)

  exchange_and_indices = html.escape(
      get_exchange_and_indices(ticker_symbol, info.get("exchange"))
  )

  bid = info.get("bid") or 0
  ask = info.get("ask") or 0
  bid_size = info.get("bidSize") or 0
  ask_size = info.get("askSize") or 0

  mcap_val = bundle["mcap_val"]
  market_cap = format_large_number(mcap_val)
  pe_raw = info.get("trailingPE")
  pe_ratio = f"{float(pe_raw):.2f}" if pe_raw else "Hisobotda yo'q"
  forward_pe = (
      f"{float(info.get('forwardPE')):.2f}"
      if info.get("forwardPE")
      else "Hisobotda yo'q"
  )

  rev_growth_val = info.get("revenueGrowth")
  total_rev_val = bundle["total_rev_val"]
  total_revenue = format_large_number(total_rev_val)
  rev_growth = (
      f"{float(rev_growth_val) * 100:+.2f}%"
      if rev_growth_val is not None and not pd.isna(rev_growth_val)
      else "Hisobotda yo'q"
  )

  net_income_val = bundle["net_inc_val"]
  net_income = format_large_number(net_income_val)
  ocf_str = format_large_number(bundle["ocf_val"])

  total_cash_val = bundle["total_cash_val"]
  total_debt_val = bundle["total_debt_val"]
  total_assets_val = bundle["total_assets_val"]
  roe_val = info.get("returnOnEquity")

  total_cash = format_large_number(total_cash_val)
  total_debt = format_large_number(total_debt_val)
  total_assets = format_large_number(total_assets_val)

  debt_to_equity = (
      f"{float(info.get('debtToEquity')):.2f}%"
      if info.get("debtToEquity") is not None
      else "Hisobotda yo'q"
  )

  dta_str = (
      f"{(float(total_debt_val) / float(total_assets_val)) * 100:.2f}%"
      if total_assets_val and total_debt_val is not None
      else "Hisobotda yo'q"
  )
  cta_str = (
      f"{(float(total_cash_val) / float(total_assets_val)) * 100:.2f}%"
      if total_assets_val and total_cash_val is not None
      else "Hisobotda yo'q"
  )
  dtm_str = (
      f"{(float(total_debt_val) / float(mcap_val)) * 100:.2f}%"
      if mcap_val and total_debt_val is not None
      else "Hisobotda yo'q"
  )

  div_yield_raw = info.get("dividendYield")
  if div_yield_raw is not None and not pd.isna(div_yield_raw):
    val = float(div_yield_raw)
    div_pct = val * 100 if val <= 1 else val
    div_yield = f"{div_pct:.2f}%" if div_pct > 0 else "To'lamaydi (0%)"
  else:
    div_yield = "To'lamaydi (0%)"

  payout_raw = info.get("payoutRatio")
  if payout_raw is not None and not pd.isna(payout_raw):
    p_val = float(payout_raw)
    payout_pct = p_val * 100 if p_val <= 1 else p_val
    payout_ratio = f"{payout_pct:.2f}%"
  else:
    payout_ratio = "0%"

  cash_staff_block = build_cash_staff_revenue_mix_block(
      ticker=ticker,
      info=info,
      total_rev_val=total_rev_val,
      net_inc_val=net_income_val,
      bundle=bundle,
  )

  summary_en = (info.get("longBusinessSummary") or "")[:600]
  if summary_en.strip():
    history_uz_raw = (
        _translate_with_gemini(
            f"Quyidagi kompaniya tavsifini 2 ta sodda gap bilan "
            f"o'zbek tilida qisqacha ber:\n{summary_en}"
        )
        or (
            f"{ticker_symbol} bo'yicha qisqa tavsif 10-K/10-Q rasmiy hisobotida"
            " keltirilgan."
        )
    )
  else:
    history_uz_raw = (
        f"{ticker_symbol} bo'yicha qisqa tavsif yfinance info da berilmagan; "
        f"rasmiy 10-K/10-Q hisobotga qarang."
    )
  history_uz = html.escape(history_uz_raw)

  sma200_val = None
  last_rsi = 0.0
  last_atr = 0.0
  year_change = 0.0
  sma20_diff = sma50_diff = sma200_diff = "Hisobotda yo'q"
  trend = "Ma'lumot yetarli emas"
  rsi_status = "-"

  if hist is not None and not hist.empty:
    hist["RSI"] = calculate_rsi(hist["Close"])
    hist["ATR"] = calculate_atr(hist)
    hist["SMA20"] = hist["Close"].rolling(window=20).mean()
    hist["SMA50"] = hist["Close"].rolling(window=50).mean()
    hist["SMA200"] = hist["Close"].rolling(window=200).mean()

    last_rsi = (
        float(hist["RSI"].iloc[-1]) if not pd.isna(hist["RSI"].iloc[-1]) else 0.0
    )
    last_atr = (
        float(hist["ATR"].iloc[-1]) if not pd.isna(hist["ATR"].iloc[-1]) else 0.0
    )
    sma20_val = hist["SMA20"].iloc[-1]
    sma50_val = hist["SMA50"].iloc[-1]
    sma200_val = hist["SMA200"].iloc[-1]

    sma20_diff = pct_diff(current_price, sma20_val)
    sma50_diff = pct_diff(current_price, sma50_val)
    sma200_diff = pct_diff(current_price, sma200_val)

    if len(hist) >= 252:
      year_start_price = float(hist["Close"].iloc[-252])
      year_change = (
          (current_price - year_start_price) / year_start_price * 100
          if year_start_price
          else 0.0
      )

    if (
        pd.notna(sma50_val)
        and pd.notna(sma200_val)
        and current_price > float(sma50_val)
        and float(sma50_val) > float(sma200_val)
    ):
      trend = "📈 Kuchli o'sish (Buqa trendi)"
    elif (
        pd.notna(sma50_val)
        and pd.notna(sma200_val)
        and current_price < float(sma50_val)
        and float(sma50_val) < float(sma200_val)
    ):
      trend = "📉 Tushish (Ayiq trendi)"
    else:
      trend = "↔️ Yonlama / Konsolidatsiya"

    if last_rsi > 70:
      rsi_status = "Haddan tashqari qimmat"
    elif last_rsi < 30:
      rsi_status = "Haddan tashqari arzon"
    else:
      rsi_status = "Neytral zona"

  is_matched, strat_info = evaluate_strategy_signal(
      ticker_symbol=ticker_symbol,
      price=current_price,
      pe_val=pe_raw,
      rsi_val=last_rsi,
      atr_val=last_atr,
      sma200_val=sma200_val,
  )

  history_lines = [
      html.escape(line) for line in get_annual_history_lines(ticker, max_years=5)
  ]
  history_block = (
      "\n".join(history_lines) if history_lines else "- Yillik jadval topilmadi"
  )

  eval_block = build_evaluation_summary(
      current_price=current_price,
      last_rsi=last_rsi,
      rev_growth_val=rev_growth_val,
      net_income_val=net_income_val,
      total_cash_val=total_cash_val,
      total_debt_val=total_debt_val,
      total_assets_val=total_assets_val,
      mcap_val=mcap_val,
      sma200_val=sma200_val,
      roe_val=roe_val,
  )

  if quota_info and quota_info.get("is_vip"):
    limit_line = "👑 <b>Tarif:</b> VIP (Cheklovsiz)\n"
  elif quota_info:
    limit_line = (
        f"🎟 <b>Limit:</b> Bugun {quota_info['daily_left']}/{DAILY_FREE_LIMIT}"
        f" qoldi | Oy {quota_info['monthly_left']}/{MONTHLY_FREE_LIMIT}"
        " qoldi\n"
    )
  else:
    limit_line = ""

  signal_line = f"\n{strat_info}\n" if is_matched else ""

  chart_url = (
      f"https://finviz.com/chart.ashx?t={ticker_symbol}&ty=c&ta=1&p=d&s=l"
  )

  report = (
      f"📊 <b>{name} ({ticker_symbol}) — TO'LIQ TAHLIL</b>\n"
      f"{limit_line}"
      f"🏛 <b>Birja:</b> {exchange_and_indices}\n"
      f"🏭 <b>Sektor:</b> {sector}\n"
      f"⚙️ <b>Yo'nalish:</b> {industry}\n\n"
      f"💵 <b>Joriy narx:</b> ${current_price:.2f} "
      f"(1 yillik: {year_change:+.2f}%)\n"
      f"📖 <b>Stakan:</b> ${bid} ({bid_size}) / ${ask} ({ask_size})\n\n"
      f"{cash_staff_block}\n\n"
      f"🏢 <b>FUNDAMENTAL:</b>\n"
      f"• <b>Bozor kapit.:</b> {market_cap}\n"
      f"• <b>P/E | Fwd P/E:</b> {pe_ratio} | {forward_pe}\n"
      f"• <b>Revenue:</b> {total_revenue} (O'sish: {rev_growth})\n"
      f"• <b>Sof foyda:</b> {net_income}\n"
      f"• <b>OCF:</b> {ocf_str}\n"
      f"• <b>Naqd/Qarz/Aktiv:</b> {total_cash} / {total_debt} / {total_assets}\n"
      f"• <b>D/E:</b> {debt_to_equity}\n"
      f"• <b>Skrining:</b> Qarz/Aktiv {dta_str} (&lt;=30%) | "
      f"Naqd/Aktiv {cta_str} (&lt;=30%) | Qarz/MCap {dtm_str} (&lt;=33%)\n\n"
      f"💰 <b>DIVIDENDLAR:</b>\n"
      f"• <b>Yield:</b> {div_yield}\n"
      f"• <b>Payout:</b> {payout_ratio}\n\n"
      f"📈 <b>TEXNIK (D1):</b>\n"
      f"• <b>Trend:</b> {trend}\n"
      f"• <b>RSI(14):</b> {last_rsi:.2f} — <i>{rsi_status}</i>\n"
      f"• <b>ATR(14):</b> {last_atr:.2f}\n"
      f"• <b>SMA20/50/200:</b> {sma20_diff} / {sma50_diff} / {sma200_diff}"
      f"{signal_line}\n"
      f"🗂 <b>YILLIK DINAMIKA:</b>\n{history_block}\n\n"
      f"📜 <b>KOMPANIYA:</b>\n<i>{history_uz}</i>\n\n"
      f"{eval_block}"
  )

  _record_monthly_activity(kind="analysis", ticker=ticker_symbol) 
  divs_series = None
  try:
      divs_series = ticker.dividends
  except Exception:
       divs_series = None
       inc = None
       bs = None
       cf= None
       return build_full_no_na_report( 
        ticker_symbol=ticker_symbol,
        info=info or {},
        hist=hist,
        inc=inc,
        bs=bs,
        cf=cf,
        divs_series=divs_series,
    )
def build_algo_signal(ticker_symbol):
  ticker = yf.Ticker(ticker_symbol)
  try:
    info = ticker.info or {}
  except Exception:
    info = {}
  pe_val = info.get("trailingPE")

  hist = ticker.history(period="1y")
  if hist is None or hist.empty or len(hist) < 25:
    return None

  close = hist["Close"]
  price = float(close.iloc[-1])
  rsi = float(calculate_rsi(close).iloc[-1])
  atr = float(calculate_atr(hist).iloc[-1])
  sma20 = float(close.rolling(20).mean().iloc[-1])
  sma50 = (
      float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma20
  )
  sma200 = (
      float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else sma50
  )

  score = 0
  reasons = []
  if price > sma20:
    score += 1
    reasons.append("Narx SMA20 ustida")
  else:
    score -= 1
    reasons.append("Narx SMA20 ostida")

  if price > sma50:
    score += 1
    reasons.append("Narx SMA50 ustida")
  else:
    score -= 1
    reasons.append("Narx SMA50 ostida")

  if rsi < 35:
    score += 1
    reasons.append(f"RSI ({rsi:.1f}) past zonaga yaqin")
  elif rsi > 70:
    score -= 1
    reasons.append(f"RSI ({rsi:.1f}) haddan tashqari qizigan")
  else:
    reasons.append(f"RSI ({rsi:.1f}) neytral")

  if score >= 2:
    verdict = "🟢 <b>BUQA / O'SISH SIGNALI</b>"
  elif score <= -2:
    verdict = "🔴 <b>AYIQ / EHTIYOT SIGNALI</b>"
  else:
    verdict = "🟡 <b>KUTISH / NEYTRAL SIGNAL</b>"

  stop_loss = max(0.01, price - 1.5 * atr)
  target_1 = price + 2.0 * atr

  matched, strat_box = evaluate_strategy_signal(
      ticker_symbol=ticker_symbol,
      price=price,
      pe_val=pe_val,
      rsi_val=rsi,
      atr_val=atr,
      sma200_val=sma200,
  )
  extra_strat = f"\n{strat_box}" if matched else ""

  return (
      f"📊 <b>ALGORITMIK SIGNAL — {ticker_symbol} (D1)</b>\n"
      f"• Holat: {verdict} (Ball: {score:+d})\n"
      f"• Joriy narx: <b>${price:.2f}</b>\n"
      f"• Taxminiy tayanch (1.5x ATR): <b>${stop_loss:.2f}</b>\n"
      f"• Taxminiy mo'ljal (2.0x ATR): <b>${target_1:.2f}</b>\n"
      f"• Asoslar: {', '.join(reasons)}"
      f"{extra_strat}\n"
      f"<i>O'quv maqsadidagi algoritmik model; moliyaviy maslahat emas.</i>"
  )


def run_strategy_scanner():
  found = []
  for sym in SCAN_WATCHLIST:
    try:
      tk = yf.Ticker(sym)
      info = tk.info or {}
      pe_val = info.get("trailingPE")
      hist = tk.history(period="6mo")
      if hist is None or hist.empty or len(hist) < 20:
        continue
      price = float(hist["Close"].iloc[-1])
      rsi = float(calculate_rsi(hist["Close"]).iloc[-1])
      atr = float(calculate_atr(hist).iloc[-1])
      sma200 = (
          float(hist["Close"].rolling(200).mean().iloc[-1])
          if len(hist) >= 200
          else None
      )
      ok, msg = evaluate_strategy_signal(sym, price, pe_val, rsi, atr, sma200)
      if ok:
        found.append(msg)
    except Exception:
      continue
  return found


# ==========================================
# 10. KANAL, BROADCAST VA OYLIK HISOBOT
# ==========================================
def send_to_channel(text):
  if not CHANNEL_ID:
    return False
  try:
    for chunk in split_html_message(text, limit=3900):
      safe_send_message(CHANNEL_ID, chunk, disable_preview=True)
    return True
  except Exception as e:
    logger.warning("Kanalga yuborishda xato: %s", e)
    return False


def broadcast_to_users(text, include_channel=True):
  sent_count = 0
  for cid in USAGE_STORE.get("known_chats", []):
    try:
      for chunk in split_html_message(text, limit=3900):
        safe_send_message(cid, chunk, disable_preview=True)
      sent_count += 1
      time.sleep(0.05)
    except Exception:
      continue
  chan_ok = send_to_channel(text) if include_channel else False
  return sent_count, chan_ok


def build_monthly_report_text(month_key=None):
  m_key = month_key or _month_key()
  stats = USAGE_STORE.get("monthly_stats", {}).get(m_key, {})
  analyses = int(stats.get("analyses", 0))
  signals_matched = int(stats.get("signals_matched", 0))
  tickers_map = stats.get("tickers", {})
  top_tickers = sorted(tickers_map.items(), key=lambda x: x[1], reverse=True)[
      :5
  ]
  top_str = (
      ", ".join([f"{k} ({v})" for k, v in top_tickers])
      if top_tickers
      else "Ma'lumot yo'q"
  )
  users_cnt = len(USAGE_STORE.get("known_chats", []))
  vip_cnt = len(USAGE_STORE.get("vip_users", []))

  return (
      f"🗓 <b>OYLIK HISOBOT — {m_key}</b>\n"
      f"• Faol foydalanuvchilar (chatlar): <b>{users_cnt}</b>\n"
      f"• VIP foydalanuvchilar: <b>{vip_cnt}</b>\n"
      f"• Jami tahlillar soni: <b>{analyses}</b>\n"
      f"• AI Strategik signallari: <b>{signals_matched}</b>\n"
      f"• Eng ko'p tahlil qilingan tikerlar: <b>{top_str}</b>"
  )


def _is_last_day_of_month(dt):
  last_day = calendar.monthrange(dt.year, dt.month)[1]
  return dt.day == last_day


def _monthly_scheduler_loop():
  while True:
    try:
      now = datetime.now()
      m_key = _month_key()
      if _is_last_day_of_month(now) and now.hour >= 20:
        if USAGE_STORE.get("last_monthly_report_sent") != m_key:
          rep = build_monthly_report_text(m_key)
          broadcast_to_users(
              f"📌 <b>OY YAKUNI AVTOMATIK HISOBOTI</b>\n\n{rep}",
              include_channel=True,
          )
          USAGE_STORE["last_monthly_report_sent"] = m_key
          save_usage_store(USAGE_STORE)
    except Exception as e:
      logger.warning("Oylik scheduler xatosi: %s", e)
    time.sleep(3600)


# ==========================================
# 11. YANGILIKLAR VA XABARNI BO'LISH
# ==========================================
def get_google_news_fallback(ticker_symbol, limit=5):
  query = quote_plus(f"{ticker_symbol} stock news")
  url = (
      f"https://news.google.com/rss/search"
      f"?q={query}&hl=en-US&gl=US&ceid=US:en"
  )
  headers = {"User-Agent": "Mozilla/5.0"}
  resp = requests.get(url, headers=headers, timeout=10)
  resp.raise_for_status()

  root = ET.fromstring(resp.content)
  items = root.findall(".//item")[:limit]
  if not items:
    return ""

  raw = ""
  for idx, item in enumerate(items, 1):
    title = item.findtext("title") or "Sarlavhasiz"
    link = item.findtext("link") or ""
    source_el = item.find("source")
    provider = (
        source_el.text
        if (source_el is not None and source_el.text)
        else "Google News"
    )
    raw += f"{idx}. [{provider}] {title} (Link: {link})\n"
  return raw


def split_html_message(text, limit=3900):
  parts, current = [], ""
  for line in text.splitlines(keepends=True):
    if len(current) + len(line) > limit:
      if current:
        parts.append(current)
      current = line
    else:
      current += line
  if current:
    parts.append(current)
  return parts or [text]


# ==========================================
# 12. BOT HANDLERLARI VA AVTOMATIK QAYTA ULANISH
# ==========================================
@bot.message_handler(commands=["start"])
def send_welcome(message):
  register_chat(message.chat.id)
  USER_MODES[message.chat.id] = "analysis"
  USER_BALANCES.setdefault(message.chat.id, 0.0)
  USER_REFERRALS.setdefault(message.chat.id, 0)
  _get_user_usage_record(message.from_user.id)
  save_usage_store(USAGE_STORE)

  vip_badge = "👑 VIP" if is_vip_user(message.from_user.id) else "🆓 Oddiy"
  safe_send_message(
      message.chat.id,
      f"Assalomu alaykum! 📈 ({vip_badge})\n"
      "Aksiya tikerini yuboring (masalan:"
      " <code>AAPL</code>, <code>NVDA</code>, <code>INTC</code>) yoki"
      " quyidagi tugmalardan birini tanlang:\n"
      f"Admin: @{ADMIN_LINK}",
      reply_markup=get_main_keyboard(),
  )


@bot.message_handler(
    func=lambda m: (m.text or "").strip().lower() in ALIAS_AI_ANALYSIS
)
def handle_btn_ai_analysis(message):
  register_chat(message.chat.id)
  USER_MODES[message.chat.id] = "analysis"
  safe_send_message(
      message.chat.id,
      "🧠 <b>AI Tahlil</b> rejimi faol.\n"
      "To'liq fundamental va texnik tahlil olish uchun aksiya tikerini"
      " yuboring (masalan:"
      " <code>AAPL</code>, <code>NVDA</code>, <code>INTC</code>, <code>MU</code>).",
      reply_markup=get_main_keyboard(),
  )


@bot.message_handler(
    func=lambda m: (m.text or "").strip().lower() in ALIAS_ALGO_SIGNALS
)
def handle_btn_algo_signals(message):
  register_chat(message.chat.id)
  USER_MODES[message.chat.id] = "algo"
  safe_send_message(
      message.chat.id,
      "📊 <b>Algoritmik signallar</b> rejimi faol.\n"
      "SMA20/50, RSI(14), ATR(14) va AI strategiya signalini ko'rish uchun"
      " tiker yuboring (masalan: <code>AAPL</code> yoki <code>NVDA</code>).",
      reply_markup=get_main_keyboard(),
  )


@bot.message_handler(
    func=lambda m: (m.text or "").strip().lower() in ALIAS_AI_HELP
)
def handle_btn_ai_help(message):
  register_chat(message.chat.id)
  USER_MODES[message.chat.id] = "ai_help"
  safe_send_message(
      message.chat.id,
      "💬 <b>AI Yordam</b> rejimi faol.\n"
      "Savolingizni erkin yozing — moliya, aksiyalar yoki indikatorlar bo'yicha"
      " javob beraman.",
      reply_markup=get_main_keyboard(),
  )


@bot.message_handler(
    func=lambda m: (m.text or "").strip().lower() in ALIAS_BALANCE
)
def handle_btn_balance(message):
  register_chat(message.chat.id)
  uid = message.from_user.id
  bal = USER_BALANCES.get(message.chat.id, 0.0)
  refs = USER_REFERRALS.get(message.chat.id, 0)
  rec = _get_user_usage_record(uid)

  if is_vip_user(uid):
    tariff_line = "👑 Tarif: <b>VIP (Cheklovsiz tahlil)</b>"
    quota_line = (
        f"📊 Bugun qilingan tahlillar: <b>{rec['daily_count']}</b> (cheklovsiz)"
    )
  else:
    d_left = max(0, DAILY_FREE_LIMIT - rec["daily_count"])
    m_left = max(0, MONTHLY_FREE_LIMIT - rec["monthly_count"])
    tariff_line = "🆓 Tarif: <b>Oddiy</b>"
    quota_line = (
        f"📅 Kunlik limit: <b>{rec['daily_count']}/{DAILY_FREE_LIMIT}</b> "
        f"(qoldi: <b>{d_left}</b>)\n"
        f"🗓 Oylik limit: <b>{rec['monthly_count']}/{MONTHLY_FREE_LIMIT}</b> "
        f"(qoldi: <b>{m_left}</b>)"
    )

  safe_send_message(
      message.chat.id,
      f"💰 <b>Hisob va limit ma'lumotlari</b>\n"
      f"• ID: <code>{uid}</code>\n"
      f"• {tariff_line}\n"
      f"• {quota_line}\n"
      f"• Balans: <b>${bal:.2f}</b> | Takliflar: <b>{refs}</b>\n"
      f"• Admin: @{ADMIN_LINK}",
      reply_markup=get_main_keyboard(),
  )


@bot.message_handler(
    func=lambda m: (m.text or "").strip().lower() in ALIAS_REFERRAL
)
def handle_btn_referral(message):
  register_chat(message.chat.id)
  bot_username = bot.get_me().username or "bot"
  ref_link = f"https://t.me/{bot_username}?start=ref_{message.from_user.id}"
  refs = USER_REFERRALS.get(message.chat.id, 0)
  safe_send_message(
      message.chat.id,
      f"🔗 <b>Referal tizim</b>\n"
      f"• Taklif havolangiz:\n<code>{ref_link}</code>\n"
      f"• Taklif qilinganlar: <b>{refs}</b> ta\n"
      f"• Admin bilan aloqa: @{ADMIN_LINK}",
      reply_markup=get_main_keyboard(),
  )


@bot.message_handler(
    func=lambda m: (m.text or "").strip().lower() in ALIAS_ADMIN
)
def handle_btn_admin(message):
  register_chat(message.chat.id)
  uid = message.from_user.id
  if not is_admin_user(uid):
    safe_send_message(
        message.chat.id,
        f"⛔ Bu bo'lim faqat administrator uchun (@{ADMIN_LINK}).",
        reply_markup=get_main_keyboard(),
    )
    return

  ADMIN_AWAITING_CMD.add(uid)
  vip_count = len(USAGE_STORE.get("vip_users", []))
  safe_send_message(
      message.chat.id,
      f"⚙️ <b>Admin Panel</b> (@{ADMIN_LINK})\n"
      f"• VIP foydalanuvchilar: <b>{vip_count}</b> | Kanal:"
      f" <code>{CHANNEL_ID}</code>\n"
      f"• Oddiy limit: kuniga <b>{DAILY_FREE_LIMIT}</b>, oyiga"
      f" <b>{MONTHLY_FREE_LIMIT}</b>\n\n"
      f"Buyruq yuboring:\n"
      f"• <code>vip 123456789</code> — VIP berish\n"
      f"• <code>unvip 123456789</code> — VIP olish\n"
      f"• <code>reset 123456789</code> — limitni tozalash\n"
      f"• <code>all Matn</code> — barcha foydalanuvchilar va kanalga xabar\n"
      f"• <code>chan Matn</code> — faqat kanalga xabar\n"
      f"• <code>scan</code> — strategik signallarni skanerlash\n"
      f"• <code>month</code> — joriy oylik hisobotni yuborish",
      reply_markup=get_main_keyboard(),
  )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
  register_chat(message.chat.id)
  raw_text = (message.text or "").strip()
  if not raw_text:
    return

  uid = message.from_user.id
  if uid in ADMIN_AWAITING_CMD and is_admin_user(uid):
    parts = raw_text.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in {"vip", "unvip", "reset"} and arg.isdigit():
      target_id = int(arg)
      ADMIN_AWAITING_CMD.discard(uid)
      if cmd == "vip":
        set_vip_status(target_id, True)
        safe_send_message(
            message.chat.id,
            f"👑 <code>{target_id}</code> ga <b>VIP</b> berildi.",
        )
      elif cmd == "unvip":
        set_vip_status(target_id, False)
        safe_send_message(
            message.chat.id,
            f"🆓 <code>{target_id}</code> dan <b>VIP</b> olindi.",
        )
      elif cmd == "reset":
        reset_user_limit(target_id)
        safe_send_message(
            message.chat.id,
            f"🔄 <code>{target_id}</code> limiti tozalandi.",
        )
      return

    if cmd == "all" and arg:
      ADMIN_AWAITING_CMD.discard(uid)
      sent_u, sent_c = broadcast_to_users(
          f"📢 <b>E'LON:</b>\n\n{html.escape(arg)}", include_channel=True
      )
      safe_send_message(
          message.chat.id,
          f"✅ Xabar <b>{sent_u}</b> ta foydalanuvchiga yuborildi"
          f"{' va kanalga chiqdi' if sent_c else ''}.",
      )
      return

    if cmd == "chan" and arg:
      ADMIN_AWAITING_CMD.discard(uid)
      ok = send_to_channel(f"📢 <b>KANAL XABARI:</b>\n\n{html.escape(arg)}")
      safe_send_message(
          message.chat.id,
          (
              "✅ Xabar kanalga yuborildi."
              if ok
              else (
                  "⚠️ Kanalga yuborilmadi — bot kanalda admin ekanligini"
                  " tekshiring."
              )
          ),
      )
      return

    if cmd == "scan":
      ADMIN_AWAITING_CMD.discard(uid)
      wait_s = bot.reply_to(message, "⏳ Strategik signallar skanerlanmoqda...")
      matches = run_strategy_scanner()
      if not matches:
        bot.edit_message_text(
            "📭 Hozircha strategiya filtriga mos aksiya topilmadi.",
            message.chat.id,
            wait_s.message_id,
        )
        return
      summary_txt = (
          "🎯 <b>TOPILGAN STRATEGIK SIGNALLAR</b>\n\n" + "\n\n".join(matches)
      )
      try:
        bot.delete_message(message.chat.id, wait_s.message_id)
      except Exception:
        pass
      for chunk in split_html_message(summary_txt, limit=3900):
        safe_send_message(message.chat.id, chunk, disable_preview=True)
      send_to_channel(summary_txt)
      return

    if cmd == "month":
      ADMIN_AWAITING_CMD.discard(uid)
      rep = build_monthly_report_text()
      safe_send_message(message.chat.id, rep, disable_preview=True)
      send_to_channel(rep)
      return

  mode = USER_MODES.get(message.chat.id, "analysis")
  is_explicit_ticker = (
      raw_text.isupper() and raw_text.isalpha() and len(raw_text) <= 6
  )

  if mode == "ai_help" and not is_explicit_ticker:
    wait_msg = bot.reply_to(message, "⏳ AI Yordam javob tayyorlamoqda...")
    try:
      answer = _answer_ai_help(raw_text)
      bot.edit_message_text(answer, message.chat.id, wait_msg.message_id)
    except Exception as e:
      logger.exception("AI Yordam xatosi: %s", e)
      bot.edit_message_text(
          f"⚠️ AI Yordam xatosi: {str(e)}",
          message.chat.id,
          wait_msg.message_id,
      )
    return

  ticker_symbol = raw_text.upper()
  if not ticker_symbol.isalpha() or len(ticker_symbol) > 6:
    safe_send_message(
        message.chat.id,
        "Aksiya tikerini kiriting (masalan: <code>AAPL</code>) yoki menyudagi"
        " tugmalardan birini bosing.",
        reply_markup=get_main_keyboard(),
    )
    return

  allowed, block_msg, quota_info = check_and_consume_quota(uid)
  if not allowed:
    safe_send_message(
        message.chat.id,
        block_msg,
        reply_markup=get_main_keyboard(),
    )
    return

  if mode == "algo":
    wait_msg = bot.reply_to(
        message,
        f"⏳ <b>{ticker_symbol}</b> uchun algoritmik signal hisoblanmoqda...",
        parse_mode="HTML",
    )
    try:
      sig_msg = build_algo_signal(ticker_symbol)
      if not sig_msg:
        bot.edit_message_text(
            f"❌ {ticker_symbol} bo'yicha signal ma'lumoti topilmadi.",
            message.chat.id,
            wait_msg.message_id,
        )
        return
      try:
        bot.delete_message(message.chat.id, wait_msg.message_id)
      except Exception:
        pass
      safe_send_message(message.chat.id, sig_msg, disable_preview=True)
      if "AI ALGORITMIK SIGNAL" in sig_msg:
        send_to_channel(sig_msg)
    except Exception as e:
      logger.exception("Signal xatosi: %s", e)
      safe_send_message(message.chat.id, f"⚠️ Signal xatosi: {str(e)}")
    return

  USER_MODES[message.chat.id] = "analysis"
  wait_msg = bot.reply_to(
      message,
      f"⏳ <b>{ticker_symbol}</b> tahlil qilinmoqda...",
      parse_mode="HTML",
  )

  try:
      res = get_stock_analysis(ticker_symbol, quota_info=quota_info) 
      if not res:
          return safe_send_message(message.chat.id, f"❌ <b>{ticker_symbol}</b> bo'yicha ma'lumot topilmadi.", parse_mode="HTML")
      report, chart_url, is_matched, strat_info = res    
      try:
        bot.delete_message(message.chat.id, wait_msg.message_id)
      except Exception:
        pass
      safe_send_message(
          message.chat.id,
          f"❌ <b>{ticker_symbol}</b> bo'yicha ma'lumot topilmadi.",
      )
      return

      markup = types.InlineKeyboardMarkup()
      markup.add(
        types.InlineKeyboardButton(
            text="📰 So'nggi yangiliklar (O'zbekcha)",
            callback_data=f"news_{ticker_symbol}",
        )
    )
       try:
    headers = {"User-Agent": "Mozilla/5.0"}
      img_data = requests.get(chart_url, headers=headers, timeout=10).content
      bot.send_photo(
          message.chat.id,
          img_data,
          caption=f"📉 {ticker_symbol} — Kunlik (D1) grafik",
      )
    except Exception:
      pass

    chunks = split_html_message(report, limit=3900)
    for idx, chunk in enumerate(chunks):
      is_last = idx == len(chunks) - 1
      safe_send_message(
          message.chat.id,
          chunk,
          reply_markup=markup if is_last else None,
          disable_preview=True,
      )

    try:
      bot.delete_message(message.chat.id, wait_msg.message_id)
    except Exception:
      pass

    if is_matched:
      send_to_channel(strat_info)

  except Exception as e:
    logger.exception("Tahlil xatosi: %s", e)
    safe_send_message(
        message.chat.id,
        f"⚠️ <b>{ticker_symbol}</b> tahlilida xatolik:"
        f" <code>{html.escape(str(e))}</code>",
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("news_"))
def handle_news_callback(call):
  ticker_symbol = call.data.split("_", 1)[1]
  bot.answer_callback_query(call.id, f"{ticker_symbol} yangiliklari...")

  try:
    raw_news = ""
    try:
      ticker = yf.Ticker(ticker_symbol)
      news_list = ticker.news or []
      for idx, item in enumerate(news_list[:5], 1):
        content = item.get("content", {})
        title = content.get("title") or item.get("title")
        if not title:
          continue
        provider = (
            content.get("provider", {}).get("displayName")
            or item.get("publisher")
            or "Yahoo Finance"
        )
        link = (
            content.get("canonicalUrl", {}).get("url")
            or item.get("clickThroughUrl", {}).get("url")
            or item.get("link")
            or ""
        )
        raw_news += f"{idx}. [{provider}] {title} (Link: {link})\n"
    except Exception:
      raw_news = ""

    if not raw_news.strip():
      raw_news = get_google_news_fallback(ticker_symbol, limit=5)

    if not raw_news.strip():
      safe_send_message(
          call.message.chat.id,
          f"📭 <b>{ticker_symbol}</b> bo'yicha yangilik topilmadi.",
      )
      return

    prompt = (
        f"Quyidagi {ticker_symbol} aksiyasiga oid yangiliklarni o'zbek tiliga"
        " tarjima qil. Har birini qisqa va tushunarli yoz, havolani <a"
        " href='...'>Manba</a> ko'rinishida qoldir. Faqat tayyor Telegram HTML"
        f" matnini qaytar:\n\n{raw_news}"
    )
    ai_response_text = generate_gemini_text(prompt)
    news_msg = (
        f"📰 <b>{ticker_symbol} — YANGILIKLAR:</b>\n\n{ai_response_text}"
    )
    for chunk in split_html_message(news_msg, limit=3900):
      safe_send_message(call.message.chat.id, chunk, disable_preview=True)

  except Exception as e:
    logger.exception("Yangilik xatosi: %s", e)
    safe_send_message(
        call.message.chat.id, f"⚠️ Yangilik xatosi: {html.escape(str(e))}"
    )


def run_bot_forever():
  threading.Thread(target=_start_keep_alive_server, daemon=True).start()
  threading.Thread(target=_monthly_scheduler_loop, daemon=True).start()
  logger.info("Bot muvaffaqiyatli ishga tushdi...")
  while True:
    try:
      bot.infinity_polling(
          skip_pending=True,
          timeout=20,
          long_polling_timeout=20,
      )
    except Exception as e:
      logger.warning("Polling uzildi, 5 soniyadan keyin qayta ulanadi: %s", e)
      time.sleep(5)


if __name__ == "__main__":
  run_bot_forever()
