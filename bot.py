# ==========================================
# 0. RENDER / MUHIT SOZLAMALARI
# ==========================================
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import html
from io import BytesIO, StringIO
import json
import logging
import math
import os
import pickle
import re
import threading
import time

from google import genai
import numpy as np
from openpyxl.utils import get_column_letter
import pandas as pd
import requests
import telebot
from telebot import types
import yfinance as yf


def _env(name, default=""):
  v = os.environ.get(name)
  return v.strip() if v and str(v).strip() else default


# ==========================================
# 1. STATIK JSON BAZANI O'QISH
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DATA_PATH = os.path.join(BASE_DIR, "static", "static_data.json")


def load_static_data():
  if os.path.exists(STATIC_DATA_PATH):
    try:
      with open(STATIC_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
      if isinstance(data, dict):
        return {
            "sectors": data.get("sectors") or {},
            "industries": data.get("industries") or {},
            "stocks": data.get("stocks") or {},
        }
    except Exception as e:
      logging.error("static_data.json xatosi: %s", e)
  return {"sectors": {}, "industries": {}, "stocks": {}}


# ==========================================
# 2. SOZLAMALAR, BAZA VA LIMITLAR
# ==========================================
TELEGRAM_TOKEN = _env("TELEGRAM_TOKEN")
GEMINI_API_KEY = _env("GEMINI_API_KEY")
if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
  raise ValueError("TELEGRAM_TOKEN va GEMINI_API_KEY muhitda bo'lishi shart!")

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
ADMIN_ID = 745170275
ADMIN_IDS = {ADMIN_ID}
ADMIN_LINK = "EAA_7879"

SIGNAL_PE_MIN, SIGNAL_PE_MAX = 10.0, 25.0
SIGNAL_RSI_MIN, SIGNAL_RSI_MAX = 20.0, 30.0
REFERRAL_REWARD_COINS = 10.0
DAILY_FREE_LIMIT = 5
MONTHLY_FREE_LIMIT = 20

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

USAGE_FILE = "/tmp/bot_usage.json"
INDEX_CACHE = {}
INDUSTRY_CACHE = {}
INDEX_DISK_CACHE = "/tmp/indices.pkl"
INDEX_CACHE_TTL = 86400

NEWS_CACHE = {
    "data": (
        "📰 <b>Global Bozor Yangiliklari:</b>\n\nHozircha yangiliklar"
        " yuklanmoqda, birozdan so'ng qayta tekshiring."
    ),
    "last_updated": 0,
}
NEWS_TTL = 1800  # 30 daqiqa

HARAM_KEYWORDS = {
    "financial services",
    "banks",
    "bank",
    "insurance",
    "credit services",
    "capital markets",
    "mortgage",
    "asset management",
    "gambling",
    "casinos",
    "resorts & casinos",
    "tobacco",
    "beverages - wineries",
    "beverages - brewers",
    "alcohol",
    "aerospace & defense",
}
HARAM_TICKERS = {
    "JPM",
    "BAC",
    "WFC",
    "C",
    "GS",
    "MS",
    "V",
    "MA",
    "AXP",
    "BRK-B",
    "BRK.B",
    "PM",
    "MO",
    "BTI",
    "BUD",
    "DEO",
    "STZ",
    "MGM",
    "LVS",
    "WYNN",
    "DKNG",
    "LMT",
    "RTX",
    "NOC",
    "GD",
}

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
SECTOR_UZ = {
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
    "Communication Services": "Aloqa va media",
}
INDUSTRY_UZ = {
    "Semiconductors": "Yarimo'tkazgichlar",
    "Consumer Electronics": "Maishiy elektronika",
    "Software - Infrastructure": "Dasturiy ta'minot (Infratuzilma)",
    "Software - Application": "Dasturiy ta'minot (Ilovalar)",
    "Auto Manufacturers": "Avtomobil ishlab chiqarish",
    "Drug Manufacturers - General": "Farmatsevtika",
    "Oil & Gas Integrated": "Neft va gaz",
}

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)
bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

USER_STATE = {}
ADMIN_AWAITING_CMD = set()

BTN_AI_ANALYSIS = "🧠 AI Tahlil"
BTN_ALGO_SIGNALS = "📊 Algoritmik signallar"
BTN_AI_HELP = "💬 AI Yordam"
BTN_BALANCE = "💰 Balans"
BTN_REFERRAL = "🔗 Referal tizim"
BTN_ADMIN = "⚙️ Admin Panel"
BTN_NEWS = "📰 Global Yangiliklar"

LVL_BASIC = "🟢 Boshlang'ich"
LVL_MID = "🟡 O'rta"
LVL_HIGH = "🔴 Yuqori (Excel)"


class _HealthHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "text/plain; charset=utf-8")
    self.end_headers()
    self.wfile.write(b"OK")

  def do_HEAD(self):
    self.send_response(200)
    self.end_headers()

  def log_message(self, *args):
    return


def _start_keep_alive():
  port = int(os.environ.get("PORT", 10000))
  HTTPServer(("0.0.0.0", port), _HealthHandler).serve_forever()


def generate_gemini_text(prompt, retries=2):
  last_err = None
  for model in GEMINI_MODELS:
    for i in range(retries):
      try:
        r = client.models.generate_content(model=model, contents=prompt)
        if r.text and r.text.strip():
          return r.text.strip()
      except Exception as e:
        last_err = e
        s = str(e)
        if "404" in s or "NOT_FOUND" in s:
          break
        if any(
            k in s for k in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")
        ):
          time.sleep(1.5 * (i + 1))
          continue
        raise
  if last_err:
    raise last_err
  return ""


def fetch_and_cache_news():
  global NEWS_CACHE
  while True:
    try:
      prompt = (
          "Qisqa va tushunarli o'zbek tilida so'nggi 24-48 soat ichidagi eng"
          " muhim global iqtisodiy va aksiya bozori yangiliklarini yozib ber."
          " AQSh fond bozori, inflyatsiya tendensiyalari va yirik"
          " kompaniyalar yangiliklariga urg'u ber. Har bir yangilikning"
          " aksiyalarga ehtimoliy ta'sirini qisqa ko'rsat."
      )
      res = generate_gemini_text(prompt)
      if res:
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        NEWS_CACHE["data"] = (
            f"📰 <b>Global Bozor Yangiliklari</b> <i>({updated_at})</i>:\n\n"
            f"{html.escape(res)}"
        )
        NEWS_CACHE["last_updated"] = time.time()
    except Exception as e:
      logger.error("Yangiliklarni yangilashda xato: %s", e)
    time.sleep(NEWS_TTL)


def get_main_keyboard():
  kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
  kb.row(
      types.KeyboardButton(BTN_AI_ANALYSIS),
      types.KeyboardButton(BTN_ALGO_SIGNALS),
  )
  kb.row(types.KeyboardButton(BTN_AI_HELP), types.KeyboardButton(BTN_BALANCE))
  kb.row(types.KeyboardButton(BTN_REFERRAL), types.KeyboardButton(BTN_ADMIN))
  kb.row(types.KeyboardButton(BTN_NEWS))
  return kb


def get_level_keyboard():
  kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
  kb.row(types.KeyboardButton(LVL_BASIC), types.KeyboardButton(LVL_MID))
  kb.row(types.KeyboardButton(LVL_HIGH))
  return kb


def safe_send(chat_id, text, reply_markup=None):
  try:
    bot.send_message(
        chat_id,
        text,
        parse_mode="HTML",
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )
  except Exception:
    bot.send_message(
        chat_id,
        html.unescape(re.sub(r"<[^>]+>", "", text)),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )


def _today():
  return datetime.now().strftime("%Y-%m-%d")


def _month():
  return datetime.now().strftime("%Y-%m")


def load_store():
  base = {
      "vip_users": [ADMIN_ID],
      "known_chats": [],
      "users": {},
      "balances": {},
      "referrals": {},
      "referred_by": {},
  }
  if os.path.exists(USAGE_FILE):
    try:
      with open(USAGE_FILE, "r", encoding="utf-8") as f:
        d = json.load(f)
      if isinstance(d, dict):
        base.update(d)
    except Exception:
      pass
  return base


def save_store(d):
  try:
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
      json.dump(d, f, ensure_ascii=False, indent=2)
  except Exception as e:
    logger.warning("Store saqlash xatosi: %s", e)


STORE = load_store()


def get_coins(uid):
  return float(STORE.setdefault("balances", {}).get(str(int(uid)), 0.0))


def add_coins(uid, amt):
  bals = STORE.setdefault("balances", {})
  k = str(int(uid))
  bals[k] = float(bals.get(k, 0.0)) + float(amt)
  save_store(STORE)
  return bals[k]


def register_referral(ref_id, new_id):
  try:
    r_id, n_id = int(ref_id), int(new_id)
  except Exception:
    return False
  if r_id == n_id or str(n_id) in STORE.setdefault("referred_by", {}):
    return False
  STORE["referred_by"][str(n_id)] = r_id
  refs = STORE.setdefault("referrals", {})
  refs[str(r_id)] = int(refs.get(str(r_id), 0)) + 1
  add_coins(r_id, REFERRAL_REWARD_COINS)
  save_store(STORE)
  return True


def register_chat(cid):
  s = set(STORE.get("known_chats", []))
  if int(cid) not in s:
    s.add(int(cid))
    STORE["known_chats"] = sorted(s)
    save_store(STORE)


def is_admin(uid):
  return int(uid) in ADMIN_IDS


def is_vip(uid):
  return int(uid) in ADMIN_IDS or int(uid) in STORE.get("vip_users", [])


def set_vip(uid, flag=True):
  s = set(STORE.get("vip_users", []))
  if flag:
    s.add(int(uid))
  else:
    s.discard(int(uid))
  STORE["vip_users"] = sorted(s)
  save_store(STORE)


def _usage_rec(uid):
  rec = STORE.setdefault("users", {}).setdefault(
      str(int(uid)),
      {
          "day": _today(),
          "daily": 0,
          "month": _month(),
          "monthly": 0,
      },
  )
  if rec.get("day") != _today():
    rec["day"], rec["daily"] = _today(), 0
  if rec.get("month") != _month():
    rec["month"], rec["monthly"] = _month(), 0
  return rec


def reset_limit(uid):
  rec = _usage_rec(uid)
  rec["daily"], rec["monthly"] = 0, 0
  save_store(STORE)


def consume_quota(uid):
  rec = _usage_rec(uid)
  if is_vip(uid):
    return (
        True,
        "",
        {
            "is_vip": True,
            "daily_used": rec["daily"],
            "monthly_used": rec["monthly"],
        },
    )
  if rec["daily"] >= DAILY_FREE_LIMIT:
    return (
        False,
        (
            f"⛔ <b>Kunlik limit tugadi!</b> ({rec['daily']}/{DAILY_FREE_LIMIT})."
            f" VIP uchun: @{ADMIN_LINK}"
        ),
        {"is_vip": False},
    )
  if rec["monthly"] >= MONTHLY_FREE_LIMIT:
    return (
        False,
        (
            f"⛔ <b>Oylik limit tugadi!</b>"
            f" ({rec['monthly']}/{MONTHLY_FREE_LIMIT}). VIP uchun:"
            f" @{ADMIN_LINK}"
        ),
        {"is_vip": False},
    )
  rec["daily"] += 1
  rec["monthly"] += 1
  save_store(STORE)
  return (
      True,
      "",
      {
          "is_vip": False,
          "daily_used": rec["daily"],
          "daily_left": DAILY_FREE_LIMIT - rec["daily"],
          "monthly_used": rec["monthly"],
          "monthly_left": MONTHLY_FREE_LIMIT - rec["monthly"],
      },
  )


# ==========================================
# 3. INDEKSLAR, TARJIMA VA STATIC JSON
# ==========================================
def load_indices(force=False):
  global INDEX_CACHE
  if INDEX_CACHE and not force:
    return INDEX_CACHE
  if not force and os.path.exists(INDEX_DISK_CACHE):
    try:
      with open(INDEX_DISK_CACHE, "rb") as f:
        d = pickle.load(f)
      if time.time() - d.get("ts", 0) < INDEX_CACHE_TTL:
        INDEX_CACHE = d["indices"]
        return INDEX_CACHE
    except Exception:
      pass
  headers = {"User-Agent": "Mozilla/5.0"}
  out = {}
  wiki_sources = {
      "S&P 500": (
          "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
          "Symbol",
      ),
      "Dow Jones (DJI)": (
          "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
          "Symbol",
      ),
      "NASDAQ-100": ("https://en.wikipedia.org/wiki/Nasdaq-100", "Ticker"),
  }
  for name, (url, col) in wiki_sources.items():
    try:
      r = requests.get(url, headers=headers, timeout=10)
      found = set()
      for tbl in pd.read_html(StringIO(r.text)):
        c = (
            col
            if col in tbl.columns
            else ("Symbol" if "Symbol" in tbl.columns else None)
        )
        if c:
          found = set(tbl[c].dropna().astype(str).str.upper().str.strip())
          break
      out[name] = found
    except Exception:
      out[name] = set()
  INDEX_CACHE = out
  try:
    with open(INDEX_DISK_CACHE, "wb") as f:
      pickle.dump({"ts": time.time(), "indices": out}, f)
  except Exception:
    pass
  return out


def _translate(txt):
  if not txt:
    return ""
  if txt in INDUSTRY_CACHE:
    return INDUSTRY_CACHE[txt]
  try:
    res = generate_gemini_text(
        f"Quyidagi so'z/ibora birikmasini o'zbek tiliga qisqa va aniq tarjima"
        f" qil, faqat tarjimani yoz:\n{txt}"
    )
    if res:
      INDUSTRY_CACHE[txt] = res.strip("\"'")
      return INDUSTRY_CACHE[txt]
  except Exception:
    pass
  return txt


def resolve_company_meta(sym, info):
  sym = sym.upper()
  st = load_static_data()
  stock_st = st.get("stocks", {}).get(sym, {})
  sec_map = st.get("sectors", {})
  ind_map = st.get("industries", {})

  raw_sec = info.get("sector") or stock_st.get("sector") or ""
  raw_ind = info.get("industry") or stock_st.get("industry") or ""
  raw_ex = info.get("exchange") or stock_st.get("exchange") or "NYSE / NASDAQ"
  ipo_date = stock_st.get("ipo_date") or "—"
  emp_st = stock_st.get("employees") or info.get("fullTimeEmployees")

  if raw_sec in sec_map:
    sec_disp = f"{sec_map[raw_sec]} ({raw_sec})"
  elif raw_sec in SECTOR_UZ:
    sec_disp = f"{SECTOR_UZ[raw_sec]} ({raw_sec})"
  elif raw_sec:
    sec_disp = raw_sec
  else:
    sec_disp = "Umumiy sektor (10-K)"

  if raw_ind in ind_map:
    ind_disp = f"{ind_map[raw_ind]} ({raw_ind})"
  elif raw_ind in INDUSTRY_UZ:
    ind_disp = f"{INDUSTRY_UZ[raw_ind]} ({raw_ind})"
  elif raw_ind:
    uz = _translate(raw_ind)
    ind_disp = f"{uz} ({raw_ind})" if uz and uz != raw_ind else raw_ind
  else:
    ind_disp = "Asosiy yo'nalish"

  ex_name = EXCHANGE_MAP.get(raw_ex, raw_ex)
  try:
    idx_map = load_indices()
    matched = [k for k, v in idx_map.items() if sym in v]
  except Exception:
    matched = []
  ex_idx = (
      f"{ex_name} | {', '.join(matched)}"
      if matched
      else f"{ex_name} | Asosiy indeks emas"
  )

  return {
      "sec_disp": sec_disp,
      "ind_disp": ind_disp,
      "raw_sec": raw_sec,
      "raw_ind": raw_ind,
      "ex_idx": ex_idx,
      "ipo_date": ipo_date,
      "employees": emp_st,
  }


# ==========================================
# 4. TEXNIK, FUNDAMENTAL, HALOL VA KIRISH NARXI
# ==========================================
def calc_rsi(series, period=14):
  delta = series.diff()
  gain = delta.where(delta > 0, 0).ewm(alpha=1 / period, adjust=False).mean()
  loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / period, adjust=False).mean()
  return 100 - (100 / (1 + gain / loss.replace(0, np.nan)))


def calc_atr(df, period=14):
  tr = pd.concat(
      [
          df["High"] - df["Low"],
          (df["High"] - df["Close"].shift()).abs(),
          (df["Low"] - df["Close"].shift()).abs(),
      ],
      axis=1,
  ).max(axis=1)
  return tr.ewm(alpha=1 / period, adjust=False).mean()


def fmt_num(n, fallback="$0.00"):
  if n is None or pd.isna(n):
    return fallback
  try:
    v = float(n)
    if math.isnan(v) or math.isinf(v):
      return fallback
  except Exception:
    return fallback
  if abs(v) >= 1e12:
    return f"${v/1e12:.2f}T"
  if abs(v) >= 1e9:
    return f"${v/1e9:.2f}B"
  if abs(v) >= 1e6:
    return f"${v/1e6:.2f}M"
  return f"${v:,.2f}"


def _df_attr(tk, names):
  for a in names:
    try:
      df = getattr(tk, a, None)
      if df is not None and not getattr(df, "empty", True):
        return df
    except Exception:
      continue
  return None


def _row_val(df, names, col_idx=0):
  if df is None or df.empty:
    return None
  low = {str(i).strip().lower(): i for i in df.index}
  for n in names:
    idx = n if n in df.index else low.get(str(n).strip().lower())
    if idx is not None:
      vals = [
          float(x)
          for x in df.loc[idx]
          if x is not None and not pd.isna(x) and math.isfinite(float(x))
      ]
      if len(vals) > col_idx:
        return vals[col_idx]
  return None


def compute_entry_levels(hist, price, atr):
  lows_20 = hist["Low"].tail(20)
  highs_20 = hist["High"].tail(20)
  support_20 = float(lows_20.min()) if not lows_20.empty else price * 0.96
  resist_20 = float(highs_20.max()) if not highs_20.empty else price * 1.05

  closes_30 = hist["Close"].tail(30).to_numpy(dtype=float)
  if len(closes_30) >= 5:
    x = np.arange(len(closes_30), dtype=float)
    slope, intercept = np.polyfit(x, closes_30, 1)
    trend_val = float(slope * (len(closes_30) - 1) + intercept)
    trend_dir = (
        "Ko'tariluvchi trend"
        if slope > 0
        else ("Pasayuvchi trend" if slope < 0 else "Yonlama trend")
    )
  else:
    trend_val = price
    trend_dir = "Yonlama trend"

  candidates = [v for v in (support_20, trend_val) if 0 < v <= price * 1.02]
  if candidates:
    raw_entry = min(candidates) if support_20 < price else max(candidates)
  else:
    raw_entry = price - (atr * 0.5 if atr > 0 else price * 0.02)

  entry_price = max(min(raw_entry, price), price * 0.80)
  entry_low = entry_price * 0.992
  entry_high = min(price, entry_price * 1.008)
  stop_loss = min(
      support_20 * 0.99,
      entry_price - (atr * 1.2 if atr > 0 else entry_price * 0.03),
  )
  target_1 = max(price * 1.03, resist_20)

  return {
      "support_20": support_20,
      "resist_20": resist_20,
      "trend_val": trend_val,
      "trend_dir": trend_dir,
      "entry_price": entry_price,
      "entry_low": entry_low,
      "entry_high": entry_high,
      "stop_loss": stop_loss,
      "target_1": target_1,
  }


def eval_halal(sym, sec_en, ind_en, rev, int_inc, debt, cash, mcap, assets):
  s, i = (sec_en or "").lower(), (ind_en or "").lower()
  sec_haram = sym.upper() in HARAM_TICKERS or any(
      k in s or k in i for k in HARAM_KEYWORDS
  )
  d_mcap = (
      (float(debt) / float(mcap) * 100)
      if mcap and float(mcap) > 0 and debt is not None
      else None
  )
  d_rev = (
      (float(debt) / float(rev) * 100)
      if rev and float(rev) > 0 and debt is not None
      else None
  )
  c_mcap = (
      (float(cash) / float(mcap) * 100)
      if mcap and float(mcap) > 0 and cash is not None
      else None
  )
  h_inc = (
      (float(int_inc) / float(rev) * 100)
      if rev
      and float(rev) > 0
      and int_inc is not None
      and float(int_inc) > 0
      else 0.0
  )

  reasons = []
  if sec_haram:
    reasons.append("Soha AAOIFI me'yorlariga mos emas")
  if d_mcap is not None and d_mcap > 30.0:
    reasons.append(f"Qarz/MCap {d_mcap:.2f}% (>30%)")
  if c_mcap is not None and c_mcap > 30.0:
    reasons.append(f"Naqd/MCap {c_mcap:.2f}% (>30%)")
  if h_inc > 5.0:
    reasons.append(f"Foiz daromadi {h_inc:.2f}% (>5%)")

  halal = len(reasons) == 0
  return halal, reasons, d_mcap, d_rev, c_mcap, h_inc


def _auto_fit_columns(ws, min_width=14, max_width=65, padding=4):
  for col in ws.columns:
    col_idx = col[0].column
    col_letter = get_column_letter(col_idx)
    max_len = 0
    for cell in col:
      val = "" if cell.value is None else str(cell.value)
      for line in val.splitlines():
        if len(line) > max_len:
          max_len = len(line)
    ws.column_dimensions[col_letter].width = max(
        min_width, min(max_width, max_len + padding)
    )


def build_excel_report(sym, payload):
  wb_buf = BytesIO()
  m = payload["meta"]
  f = payload["fund"]
  t = payload["tech"]
  e = payload["entry"]

  definitions = [
      [
          "Atama / Ko'rsatkich",
          "O'zbekcha Ma'nosi / Ta'rifi",
          "Misol / Izoh",
      ],
      [
          "Sektor",
          "Kompaniya faoliyat yuritadigan keng iqtisodiy soha",
          (
              "Masalan: Texnologiya (Apple, NVIDIA) yoki Sog'liqni saqlash"
              " (Johnson & Johnson)."
          ),
      ],
      [
          "Industriya",
          "Sektor ichidagi aniqroq biznes yo'nalishi",
          (
              "Masalan: Yarimo'tkazgichlar (chip ishlab chiqarish) yoki"
              " Farmatsevtika."
          ),
      ],
      [
          "Market Cap (Bozor Kapitallashuvi)",
          "Kompaniyaning umumiy bozor qiymati (Narx × Aksiyalar soni)",
          (
              "Masalan: $500B+ yirik kompaniya hisoblanadi; hajm barqarorlikni"
              " ko'rsatadi."
          ),
      ],
      [
          "Total Revenue (Yillik Tushum)",
          "Xarajatlar va soliqlar ayrilgungacha bo'lgan umumiy savdo/tushum",
          (
              "Masalan: yillik tushum $80B bo'lsa, kompaniya mahsulot/xizmatidan"
              " shuncha tushum olgan."
          ),
      ],
      [
          "Net Income (Sof Foyda)",
          "Barcha xarajatlar, soliq va foizlar to'langach qolgan yakuniy foyda",
          (
              "Masalan: tushum $80B va sof foyda $20B bo'lsa, foyda marjasi 25%."
              " Minus bo'lsa zarar."
          ),
      ],
      [
          "Operating Cash Flow (OCF)",
          "Asosiy operatsion faoliyatdan kelib tushgan va sarflangan real naqd"
          " pul",
          (
              "Masalan: OCF $351M bo'lsa, asosiy ish jarayoni $351M real pul"
              " oqimi yaratgan."
          ),
      ],
      [
          "Free Cash Flow (FCF)",
          "OCFdan kapital xarajatlar (Capex) ayrilgach qolgan erkin naqd pul",
          (
              "Masalan: FCF ijobiy bo'lsa, kompaniya qarz to'lash, dividend yoki"
              " investitsiyaga erkin pulga ega."
          ),
      ],
      [
          "Total Cash (Naqd Pul)",
          "Kompaniya hisobidagi naqd mablag' va tez naqdlashtiriladigan"
          " aktivlar",
          (
              "Masalan: $735M naqd pul kutilmagan xarajatlarga qarshi moliyaviy"
              " zaxira."
          ),
      ],
      [
          "Total Debt (Umumiy Qarz)",
          "Kompaniyaning qisqa va uzoq muddatli jami qarz majburiyatlari",
          (
              "Masalan: $4.30B qarzni naqd pul va FCF bilan solishtirib qarz"
              " yukini baholash mumkin."
          ),
      ],
      [
          "P/E Ratio (TTM)",
          "Aksiya narxining 1 aksiyaga to'g'ri keladigan yillik foydaga nisbati",
          (
              "Masalan: P/E = 20 bo'lsa, $1 foyda uchun bozorda $20"
              " to'lanmoqda; manfiy bo'lsa sof foyda minusda."
          ),
      ],
      [
          "SMA20 / SMA50 / SMA200",
          "Oxirgi 20, 50 va 200 kundagi o'rtacha yopilish narxlari",
          (
              "Masalan: narx SMA200 dan yuqorida bo'lsa, uzoq muddatli o'sish"
              " trendi ustun hisoblanadi."
          ),
      ],
      [
          "RSI (14)",
          "Narx tezlashuvi va kuchini 0–100 oralig'ida o'lchovchi indikator",
          (
              "Masalan: RSI 30 dan past — haddan tashqari sotilgan zona, 70 dan"
              " yuqori — qizigan zona."
          ),
      ],
      [
          "ATR (14)",
          "Aksiyaning o'rtacha kunlik narx tebranish kengligi (volatillik)",
          (
              "Masalan: ATR $2.50 bo'lsa, kunlik harakat o'rtacha shu atrofda"
              " kechishi mumkin."
          ),
      ],
      [
          "Support (20k) / Trendline (30k)",
          "20 kunlik eng past narx zonasi va 30 kunlik chiziqli trend chizig'i",
          (
              "Masalan: kirish narxi pastki tayanch va trend chizig'iga yaqin"
              " nuqtadan belgilanadi."
          ),
      ],
      [
          "Stop-Loss / Maqsad 1",
          "Zararni cheklash nuqtasi va birinchi mo'ljallangan foyda darajasi",
          (
              "Masalan: narx Stop-Loss ostiga tushsa pozitsiya xavfini cheklash"
              " haqida o'ylanadi."
          ),
      ],
  ]

  summary_rows = [
      ["Ticker", sym, "Kompaniya / Indeks", m["ex_idx"]],
      ["Sektor", m["sec_disp"], "Industriya", m["ind_disp"]],
      ["IPO sanasi", m["ipo_date"], "Xodimlar soni", m["employees"] or "—"],
      [
          "Joriy narx ($)",
          round(t["price"], 2),
          "Kunlik o'zgarish (%)",
          round(t["chg_pct"], 2),
      ],
      [
          "Tavsiya etilgan kirish ($)",
          round(e["entry_price"], 2),
          "Kirish zonasi ($)",
          f"{e['entry_low']:.2f} – {e['entry_high']:.2f}",
      ],
      [
          "Support (20 kun) ($)",
          round(e["support_20"], 2),
          "Trendline (30 kun) ($)",
          round(e["trend_val"], 2),
      ],
      [
          "Stop-Loss ($)",
          round(e["stop_loss"], 2),
          "Maqsad (Target 1) ($)",
          round(e["target_1"], 2),
      ],
      ["SMA20 ($)", round(t["sma20"], 2), "SMA50 ($)", round(t["sma50"], 2)],
      [
          "SMA200 ($)",
          round(t["sma200"], 2),
          "AAOIFI Halol status",
          "HALOL" if payload["halal"][0] else "MOS EMAS",
      ],
      ["RSI (14)", round(t["rsi"], 2), "ATR (14) ($)", round(t["atr"], 2)],
  ]

  fund_rows = [
      ["Bozor kapitallashuvi (Market Cap)", fmt_num(f["mcap"])],
      ["Yillik tushum (Total Revenue)", fmt_num(f["rev"])],
      ["Sof foyda (Net Income)", fmt_num(f["net_inc"])],
      ["Naqd pul (Total Cash)", fmt_num(f["cash"])],
      ["Umumiy qarz (Total Debt)", fmt_num(f["debt"])],
      ["Operating Cash Flow (OCF)", fmt_num(f["ocf"])],
      ["Free Cash Flow (FCF)", fmt_num(f["fcf"])],
      ["P/E (TTM)", f"{f['pe']:.2f}" if f["pe"] is not None else "Minus / Yo'q"],
      [
          "Forward P/E",
          f"{f['fpe']:.2f}" if f["fpe"] is not None else "Minus / Yo'q",
      ],
  ]

  with pd.ExcelWriter(wb_buf, engine="openpyxl") as writer:
    pd.DataFrame(
        summary_rows,
        columns=["Ko'rsatkich", "Qiymat", "Ko'rsatkich 2", "Qiymat 2"],
    ).to_excel(writer, sheet_name="Asosiy_Tahlil", index=False)
    pd.DataFrame(
        fund_rows, columns=["Fundamental Ko'rsatkich", "Qiymat"]
    ).to_excel(writer, sheet_name="Fundamental", index=False)
    pd.DataFrame(
        definitions, columns=["Atama", "O'zbekcha Ma'nosi", "Misol / Izoh"]
    ).to_excel(writer, sheet_name="Atamalar_Lug'ati", index=False)

    for ws in writer.sheets.values():
      _auto_fit_columns(ws)

  wb_buf.seek(0)
  return wb_buf


def gather_stock_data(sym):
  sym = sym.upper().strip()
  tk = yf.Ticker(sym)
  info = {}
  try:
    info = tk.info or {}
  except Exception:
    info = {}

  hist = tk.history(period="1y")
  if hist is None or hist.empty or len(hist) < 20:
    return None

  close = hist["Close"].astype(float)
  price = float(close.iloc[-1])
  prev_close = float(close.iloc[-2]) if len(close) > 1 else price
  chg_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

  rsi_s = calc_rsi(close)
  atr_s = calc_atr(hist)
  rsi = float(rsi_s.iloc[-1]) if not pd.isna(rsi_s.iloc[-1]) else 50.0
  atr = float(atr_s.iloc[-1]) if not pd.isna(atr_s.iloc[-1]) else 0.0
  sma20 = float(close.rolling(20).mean().iloc[-1])
  sma50 = (
      float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma20
  )
  sma200 = (
      float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else sma50
  )

  inc = _df_attr(tk, ["financials", "income_stmt", "quarterly_financials"])
  bs = _df_attr(tk, ["balance_sheet", "quarterly_balance_sheet"])
  cf = _df_attr(tk, ["cashflow", "quarterly_cashflow"])

  shares = info.get("sharesOutstanding")
  mcap = info.get("marketCap") or (
      float(shares) * price if shares and price > 0 else None
  )
  rev = info.get("totalRevenue") or _row_val(
      inc, ["Total Revenue", "Operating Revenue"]
  )
  net_inc = info.get("netIncomeToCommon") or _row_val(
      inc, ["Net Income Common Stockholders", "Net Income"]
  )
  int_inc = _row_val(inc, ["Interest Income", "Interest Income Non Operating"])
  cash = (
      info.get("totalCash")
      or info.get("cashAndCashEquivalents")
      or _row_val(bs, ["Cash And Cash Equivalents", "Cash Financial"])
  )
  debt = info.get("totalDebt") or _row_val(
      bs, ["Total Debt", "Long Term Debt And Capital Lease Obligation"]
  )
  assets = info.get("totalAssets") or _row_val(bs, ["Total Assets"])
  ocf = info.get("operatingCashflow") or _row_val(cf, ["Operating Cash Flow"])
  capex = _row_val(cf, ["Capital Expenditure", "Capital Expenditures"])
  fcf = info.get("freeCashflow")
  if fcf is None and ocf is not None and capex is not None:
    fcf = (
        float(ocf) + float(capex)
        if float(capex) < 0
        else float(ocf) - float(capex)
    )

  pe = info.get("trailingPE")
  if pe is not None and float(pe) < 0:
    pe = None
  if pe is None and net_inc and shares and float(shares) > 0 and float(net_inc) > 0:
    pe = price / (float(net_inc) / float(shares))

  fpe = info.get("forwardPE")
  if fpe is not None and float(fpe) < 0:
    fpe = None

  meta = resolve_company_meta(sym, info)
  entry = compute_entry_levels(hist, price, atr)
  halal = eval_halal(
      sym, meta["raw_sec"], meta["raw_ind"], rev, int_inc, debt, cash, mcap, assets
  )

  return {
      "sym": sym,
      "name": info.get("shortName") or info.get("longName") or sym,
      "meta": meta,
      "entry": entry,
      "halal": halal,
      "tech": {
          "price": price,
          "chg_pct": chg_pct,
          "rsi": rsi,
          "atr": atr,
          "sma20": sma20,
          "sma50": sma50,
          "sma200": sma200,
      },
      "fund": {
          "mcap": mcap,
          "rev": rev,
          "net_inc": net_inc,
          "cash": cash,
          "debt": debt,
          "ocf": ocf,
          "fcf": fcf,
          "pe": pe,
          "fpe": fpe,
      },
  }


def format_analysis_by_level(p, level):
  sym = p["sym"]
  m, t, f, e = p["meta"], p["tech"], p["fund"], p["entry"]
  halal_ok, reasons, d_mcap, d_rev, c_mcap, h_inc = p["halal"]

  pe_str = f"{f['pe']:.2f}" if f.get("pe") is not None else "Minus / Yo'q"
  fpe_str = f"{f['fpe']:.2f}" if f.get("fpe") is not None else "Minus / Yo'q"
  d_str = f"{d_mcap:.2f}%" if d_mcap is not None else "—"
  d_rev_str = f"{d_rev:.2f}%" if d_rev is not None else "—"
  c_str = f"{c_mcap:.2f}%" if c_mcap is not None else "—"

  entry_block = (
      f"🎯 <b>Kirish narxi (Support &amp; Trendline):</b>"
      f" <b>${e['entry_price']:.2f}</b>"
      f" (Zona: ${e['entry_low']:.2f} – ${e['entry_high']:.2f})\n"
      f"  <i>Support (20k): ${e['support_20']:.2f} | Trendline (30k):"
      f" ${e['trend_val']:.2f} ({e['trend_dir']})</i>\n"
      f"  <i>Stop-Loss: ${e['stop_loss']:.2f} | Maqsad 1:"
      f" ${e['target_1']:.2f}</i>"
  )

  halal_line = (
      "✅ <b>HALOL (AAOIFI)</b>"
      if halal_ok
      else f"❌ <b>MOS EMAS</b> ({html.escape(', '.join(reasons))})"
  )
  halal_calc = (
      f"<i>Hisob: Qarz/MCap = {d_str} (lim &le;30%), Qarz/Tushum ="
      f" {d_rev_str}, Naqd/MCap = {c_str} (lim &le;30%), Foiz/Tushum ="
      f" {h_inc:.2f}% (lim &le;5%)</i>"
  )

  footer_help = (
      "\n\n💡 <b>Eslatma:</b> Agarda bu ko'rsatkichlarni tushunmagan bo'lsangiz,"
      " <b>💬 AI Yordam</b> bo'limiga o'tib, ushbu tahlil matnini"
      " kopirovat qilib tashlang — AI sizga barchasini bafurja tushuntirib"
      " beradi."
  )

  if level == "basic":
    ai_note = generate_gemini_text(
        f"{sym} aksiyasini boshlang'ich o'quvchi uchun juda sodda o'zbek"
        f" tilida 3-4 gapda tushuntir: narx ${t['price']:.2f}, kirish"
        f" ${e['entry_price']:.2f}, RSI {t['rsi']:.1f}, sektor {m['sec_disp']}."
    )
    return (
        f"🟢 <b>{sym} — BOSHLANG'ICH TAHLIL</b>\n"
        f"• <b>Sektor / Industriya:</b> {html.escape(m['sec_disp'])} /"
        f" {html.escape(m['ind_disp'])}\n"
        f"• <b>Narx:</b> <b>${t['price']:.2f}</b> ({t['chg_pct']:+.2f}%)"
        f" | <b>Halollik:</b> {halal_line}\n"
        f"{entry_block}\n"
        f"• <b>RSI (14):</b> {t['rsi']:.1f} <i>(30 dan past — arzonlashgan,"
        f" 70 dan yuqori — qimmatlashgan zona)</i>\n"
        f"• <b>Foyda va qarz (qisqa):</b> Tushum {fmt_num(f['rev'])}, Sof foyda"
        f" {fmt_num(f['net_inc'])}, Qarz {fmt_num(f['debt'])}\n"
        f"{halal_calc}\n\n"
        f"💡 <b>Oddiy izoh:</b> {html.escape(ai_note)}{footer_help}"
    )

  if level == "mid":
    ai_note = generate_gemini_text(
        f"{sym} uchun o'rta darajadagi treyder/investor tahlili (o'zbek"
        f" tilida, 4-5 gap): narx ${t['price']:.2f}, SMA20/50/200:"
        f" {t['sma20']:.2f}/{t['sma50']:.2f}/{t['sma200']:.2f}, RSI"
        f" {t['rsi']:.1f}, P/E {pe_str}, kirish ${e['entry_price']:.2f}."
    )
    return (
        f"🟡 <b>{sym} — O'RTA DARAJADAGI TAHLIL</b>\n"
        f"• <b>Indeks / Soha:</b> {html.escape(m['ex_idx'])} |"
        f" {html.escape(m['sec_disp'])}\n"
        f"• <b>Narx:</b> <b>${t['price']:.2f}</b> ({t['chg_pct']:+.2f}%)"
        f" | <b>ATR (14):</b> ${t['atr']:.2f}\n"
        f"{entry_block}\n"
        f"• <b>SMA20 / SMA50 / SMA200:</b> ${t['sma20']:.2f} /"
        f" ${t['sma50']:.2f} / ${t['sma200']:.2f}"
        f" <i>(Uzoq muddatli trend ko'rsatkichlari)</i>\n"
        f"• <b>P/E (TTM):</b> {pe_str}"
        f" <i>(1 dollar foydaga qancha to'lanayotgani)</i> | <b>FCF:</b>"
        f" {fmt_num(f['fcf'])}\n"
        f"• <b>AAOIFI:</b> {halal_line}\n"
        f"{halal_calc}\n\n"
        f"🧠 <b>O'rta daraja xulosasi:</b> {html.escape(ai_note)}{footer_help}"
    )

  ai_note = generate_gemini_text(
      f"{sym} bo'yicha chuqur institutsional va texnik tahlil (o'zbek"
      f" tilida, 5-6 gap): narx ${t['price']:.2f}, kirish"
      f" ${e['entry_price']:.2f}, support ${e['support_20']:.2f}, trendline"
      f" ${e['trend_val']:.2f}, RSI {t['rsi']:.1f}, P/E {pe_str}, Cash"
      f" {fmt_num(f['cash'])}, Debt {fmt_num(f['debt'])}, FCF"
      f" {fmt_num(f['fcf'])}."
  )
  return (
      f"🔴 <b>{sym} — YUQORI DARAJADAGI TAHLIL (+ EXCEL)</b>\n"
      f"• <b>Birja / Indeks:</b> {html.escape(m['ex_idx'])}\n"
      f"• <b>Sektor / Industriya:</b> {html.escape(m['sec_disp'])} /"
      f" {html.escape(m['ind_disp'])}\n"
      f"• <b>IPO:</b> {html.escape(str(m['ipo_date']))} | <b>Xodimlar:</b>"
      f" {html.escape(str(m['employees'] or '—'))}\n"
      f"• <b>Narx:</b> <b>${t['price']:.2f}</b> ({t['chg_pct']:+.2f}%) |"
      f" <b>RSI (14):</b> {t['rsi']:.2f} | <b>ATR (14):</b> ${t['atr']:.2f}\n"
      f"{entry_block}\n"
      f"• <b>SMA20 / SMA50 / SMA200:</b> ${t['sma20']:.2f} /"
      f" ${t['sma50']:.2f} / ${t['sma200']:.2f}\n"
      f"• <b>Kapital / Tushum / Sof foyda:</b> {fmt_num(f['mcap'])} /"
      f" {fmt_num(f['rev'])} / {fmt_num(f['net_inc'])}\n"
      f"• <b>Naqd pul / Qarz / FCF:</b> {fmt_num(f['cash'])} /"
      f" {fmt_num(f['debt'])} / {fmt_num(f['fcf'])}\n"
      f"• <b>P/E / Fwd P/E:</b> {pe_str} / {fpe_str}\n"
      f"• <b>AAOIFI Halollik:</b> {halal_line}\n"
      f"{halal_calc}\n\n"
      f"📑 <b>Chuqur AI xulosasi:</b> {html.escape(ai_note)}{footer_help}"
  )


def run_scanner():
  out = []
  for sym in SCAN_WATCHLIST:
    try:
      p = gather_stock_data(sym)
      if not p:
        continue
      pe, rsi = p["fund"]["pe"], p["tech"]["rsi"]
      if (
          pe is not None
          and SIGNAL_PE_MIN <= pe <= SIGNAL_PE_MAX
          and SIGNAL_RSI_MIN <= rsi <= SIGNAL_RSI_MAX
      ):
        out.append(
            f"• <b>{sym}</b>: ${p['tech']['price']:.2f} | RSI {rsi:.1f} |"
            f" P/E {pe:.2f} | Kirish ${p['entry']['entry_price']:.2f}"
        )
    except Exception:
      continue
  return out


# ==========================================
# 5. TELEGRAM HANDLERLAR
# ==========================================
@bot.message_handler(commands=["start"])
def cmd_start(msg):
  uid, cid = msg.from_user.id, msg.chat.id
  register_chat(cid)
  parts = (msg.text or "").split(maxsplit=1)
  if len(parts) > 1 and parts[1].startswith("ref_"):
    try:
      ref_id = int(parts[1].replace("ref_", "").strip())
      if register_referral(ref_id, uid):
        safe_send(
            ref_id,
            f"🎉 Yangi referal! +{REFERRAL_REWARD_COINS:.0f} tanga qo'shildi.",
        )
    except Exception:
      pass
  USER_STATE[cid] = {"mode": "analysis", "level": "basic"}
  safe_send(
      cid,
      "👋 Assalomu alaykum! AI aksiya tahlil tizimiga xush kelibsiz.\n"
      "Avval <b>🧠 AI Tahlil</b> tugmasini bosib darajani tanlang"
      " (<i>Boshlang'ich, O'rta, Yuqori — Excel hisobot bilan</i>).",
      reply_markup=get_main_keyboard(),
  )


@bot.message_handler(func=lambda m: True)
def handle_all(msg):
  uid, cid = msg.from_user.id, msg.chat.id
  txt = (msg.text or "").strip()
  low = txt.lower()
  register_chat(cid)

  if is_admin(uid) and cid in ADMIN_AWAITING_CMD:
    ADMIN_AWAITING_CMD.discard(cid)
    parts = txt.split()
    if len(parts) >= 2 and parts[0].lower() == "vip":
      try:
        set_vip(int(parts[1]), True)
        safe_send(
            cid, f"✅ {parts[1]} VIP qilindi.", reply_markup=get_main_keyboard()
        )
        return
      except Exception:
        pass
    if len(parts) >= 2 and parts[0].lower() == "reset":
      try:
        reset_limit(int(parts[1]))
        safe_send(
            cid,
            f"✅ {parts[1]} limiti tiklandi.",
            reply_markup=get_main_keyboard(),
        )
        return
      except Exception:
        pass

  if low in {"🧠 ai tahlil", "ai tahlil"}:
    USER_STATE[cid] = {"mode": "analysis", "level": "basic"}
    safe_send(
        cid,
        "🎯 <b>Tahlil darajasini tanlang:</b>\n"
        "• <b>🟢 Boshlang'ich</b> — sodda va qisqa tahlil\n"
        "• <b>🟡 O'rta</b> — texnik va asosiy ko'rsatkichlar\n"
        "• <b>🔴 Yuqori (Excel)</b> — chuqur tahlil + <b>.xlsx</b> fayl",
        reply_markup=get_level_keyboard(),
    )
    return

  if txt in {LVL_BASIC, LVL_MID, LVL_HIGH}:
    lvl = (
        "basic"
        if txt == LVL_BASIC
        else ("mid" if txt == LVL_MID else "high")
    )
    USER_STATE[cid] = {"mode": "analysis", "level": lvl}
    note = (
        " (natija bilan birga <b>Excel</b> fayl ham yuboriladi)"
        if lvl == "high"
        else ""
    )
    safe_send(
        cid,
        f"✅ Daraja tanlandi: <b>{txt}</b>{note}.\n"
        "Endi aksiya tickerini yuboring (masalan: <code>AAPL</code>,"
        " <code>NVDA</code>, <code>TSM</code>).",
        reply_markup=get_main_keyboard(),
    )
    return

  if low in {"💬 ai yordam", "ai yordam"}:
    USER_STATE[cid] = {"mode": "help", "level": "basic"}
    safe_send(
        cid,
        "💬 <b>AI Yordam</b> faol. Muammoli tahlil matnini shu yerga tashlang"
        " yoki savolingizni yozing.",
        reply_markup=get_main_keyboard(),
    )
    return

  if low in {"💰 balans", "balans"}:
    rec = _usage_rec(uid)
    safe_send(
        cid,
        f"💰 <b>Balans &amp; Limit</b>\n"
        f"• Tanga: <b>{get_coins(uid):.1f}</b>\n"
        f"• Status: <b>{'VIP' if is_vip(uid) else 'Oddiy'}</b>\n"
        f"• Bugun: <b>{rec['daily']}/{DAILY_FREE_LIMIT}</b> | Oy:"
        f" <b>{rec['monthly']}/{MONTHLY_FREE_LIMIT}</b>",
        reply_markup=get_main_keyboard(),
    )
    return

  if low in {"🔗 referal tizim", "referal tizim"}:
    me = bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{uid}"
    cnt = int(STORE.get("referrals", {}).get(str(uid), 0))
    safe_send(
        cid,
        f"🔗 <b>Referal havola:</b>\n<code>{link}</code>\n"
        f"• Taklif qilinganlar: <b>{cnt}</b> | Mukofot:"
        f" <b>{REFERRAL_REWARD_COINS:.0f} tanga</b>",
        reply_markup=get_main_keyboard(),
    )
    return

  if low in {"📊 algoritmik signallar", "algoritmik signallar"}:
    bot.send_chat_action(cid, "typing")
    matches = run_scanner()
    body = (
        "\n".join(matches)
        if matches
        else "Hozircha filtrga mos aksiya topilmadi."
    )
    safe_send(
        cid,
        f"📊 <b>Algoritmik signallar</b> (RSI {SIGNAL_RSI_MIN}-{SIGNAL_RSI_MAX},"
        f" P/E {SIGNAL_PE_MIN}-{SIGNAL_PE_MAX}):\n{body}",
        reply_markup=get_main_keyboard(),
    )
    return

  if low in {"📰 global yangiliklar", "global yangiliklar", "yangiliklar"}:
    safe_send(cid, NEWS_CACHE["data"], reply_markup=get_main_keyboard())
    return

  if low in {"⚙️ admin panel", "admin panel"}:
    if not is_admin(uid):
      safe_send(cid, "⛔ Bu bo'lim faqat admin uchun.")
      return
    ADMIN_AWAITING_CMD.add(cid)
    safe_send(
        cid,
        "⚙️ <b>Admin Panel</b>\n"
        f"• Foydalanuvchilar: <b>{len(STORE.get('users', {}))}</b> |"
        f" VIP: <b>{len(STORE.get('vip_users', []))}</b>\n"
        "Buyruq yuboring: <code>vip USER_ID</code> yoki"
        " <code>reset USER_ID</code>",
    )
    return

  st = USER_STATE.get(cid, {"mode": "analysis", "level": "basic"})
  if st.get("mode") == "help":
    bot.send_chat_action(cid, "typing")
    ans = generate_gemini_text(
        f"Moliya va aksiyalar bo'yicha foydalanuvchiga tushunarli qilib javob"
        f" ber (agar tahlil natijasi tashlangan bo'lsa, uni tahlil qilib"
        f" tushuntirib ber):\n{txt}"
    )
    safe_send(
        html.escape(ans) if ans else "Javob topilmadi.",
        reply_markup=get_main_keyboard(),
    )
    return

  ticker_cand = txt.upper().replace(".", "-")
  if not re.fullmatch(r"[A-Z0-9\-]{1,10}", ticker_cand):
    safe_send(
        cid,
        "Iltimos, aksiya tickerini kiriting (masalan: <code>AAPL</code>) yoki"
        " menyudan bo'lim tanlang.",
        reply_markup=get_main_keyboard(),
    )
    return

  ok, err_msg, _ = consume_quota(uid)
  if not ok:
    safe_send(cid, err_msg, reply_markup=get_main_keyboard())
    return

  bot.send_chat_action(cid, "typing")
  level = st.get("level", "basic")
  try:
    payload = gather_stock_data(ticker_cand)
    if not payload:
      safe_send(
          cid,
          f"❌ <b>{ticker_cand}</b> bo'yicha ma'lumot topilmadi.",
          reply_markup=get_main_keyboard(),
      )
      return

    report_txt = format_analysis_by_level(payload, level)
    safe_send(cid, report_txt, reply_markup=get_main_keyboard())

    if level == "high":
      bot.send_chat_action(cid, "upload_document")
      excel_io = build_excel_report(ticker_cand, payload)
      bot.send_document(
          cid,
          excel_io,
          visible_file_name=f"{ticker_cand}_Yuqori_Tahlil.xlsx",
          caption=f"📊 <b>{ticker_cand}</b> — Yuqori darajadagi Excel hisobot",
          parse_mode="HTML",
      )
  except Exception as e:
    logger.error("Tahlil xatosi (%s): %s", ticker_cand, e)
    safe_send(
        cid,
        f"❌ Tahlil vaqtida xatolik yuz berdi: <code>{html.escape(str(e))}</code>",
        reply_markup=get_main_keyboard(),
    )


def run_bot_forever():
  threading.Thread(target=_start_keep_alive, daemon=True).start()
  threading.Thread(target=fetch_and_cache_news, daemon=True).start()
  logger.info("Bot ishga tushdi...")
  while True:
    try:
      bot.infinity_polling(
          skip_pending=True, timeout=20, long_polling_timeout=20
      )
    except Exception as e:
      logger.warning("Polling uzildi: %s", e)
      time.sleep(5)


if __name__ == "__main__":
  run_bot_forever()
