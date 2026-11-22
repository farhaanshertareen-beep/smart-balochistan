import streamlit as st
import sqlite3
import requests
import json
import hashlib
import secrets
import base64
import re
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import streamlit.components.v1 as components

DB = Path(__file__).with_name("highway_alerts.db")
API = "https://api.open-meteo.com/v1/forecast"

ROUTES_DATA = {
    "Quetta–Karachi (N-25)": {
        "code": "N-25",
        "distance": "688 km",
        "alt_route": "Quetta → Sibi (N-65) → Jacobabad → Sukkur → Karachi (N-5/M-9) [All-Weather Bypass]",
        "alt_reason": "Bypasses Kalat/Surab snowfall and Khuzdar/Wadh flash-flood/landslide zones via low-elevation Indus Highway.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Mastung", "lat": 29.7997, "lon": 66.8455, "elevation": "1,701m"},
            {"name": "Kalat", "lat": 29.0266, "lon": 66.5936, "elevation": "2,007m"},
            {"name": "Surab", "lat": 28.4914, "lon": 66.2585, "elevation": "1,750m"},
            {"name": "Khuzdar", "lat": 27.8000, "lon": 66.6167, "elevation": "1,237m"},
            {"name": "Wadh", "lat": 27.3436, "lon": 66.3708, "elevation": "1,220m"},
            {"name": "Lasbela", "lat": 26.2289, "lon": 66.3106, "elevation": "87m"},
            {"name": "Hub", "lat": 25.0244, "lon": 66.8906, "elevation": "24m"},
        ]
    },
    "Quetta–Zhob (N-50)": {
        "code": "N-50",
        "distance": "331 km",
        "alt_route": "Quetta → Ziarat Cross → Loralai (N-70) → Mekhtar → Zhob Link Road",
        "alt_reason": "Avoids Khan Mehtarzai (2,224m) heavy snowfall and landslide-prone mountain pass.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kuchlak", "lat": 30.3125, "lon": 67.0114, "elevation": "1,560m"},
            {"name": "Khan Mehtarzai", "lat": 30.4833, "lon": 67.6167, "elevation": "2,224m"},
            {"name": "Muslim Bagh", "lat": 30.8317, "lon": 67.7408, "elevation": "1,787m"},
            {"name": "Qilla Saifullah", "lat": 30.7000, "lon": 68.3600, "elevation": "1,550m"},
            {"name": "Zhob", "lat": 31.3411, "lon": 69.4481, "elevation": "1,426m"},
        ]
    },
    "Quetta–Sibi (N-65)": {
        "code": "N-65",
        "distance": "163 km",
        "alt_route": "Quetta → Harnai → Shahrag → Sibi (via Ziarat–Harnai Corridor)",
        "alt_reason": "Verified detour when Kolpur / Bolan Pass is blocked due to rain, flooding, or rockslides.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kolpur (Bolan Pass)", "lat": 29.9000, "lon": 67.1500, "elevation": "1,790m"},
            {"name": "Mach", "lat": 29.8637, "lon": 67.3302, "elevation": "1,006m"},
            {"name": "Dhadar", "lat": 29.4749, "lon": 67.6514, "elevation": "132m"},
            {"name": "Sibi", "lat": 29.5430, "lon": 67.8773, "elevation": "130m"},
        ]
    },
    "Quetta–Chaman (N-25 North)": {
        "code": "N-25N",
        "distance": "125 km",
        "alt_route": "Quetta → Kuchlak → Pishin → Gulistan → Boghra Pass → Chaman",
        "alt_reason": "Bypasses Khojak Pass (2,290m) during heavy snowfall or landslides.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kuchlak", "lat": 30.3125, "lon": 67.0114, "elevation": "1,560m"},
            {"name": "Khojak Pass (Shelabagh)", "lat": 30.8050, "lon": 66.5680, "elevation": "2,290m"},
            {"name": "Chaman", "lat": 30.9177, "lon": 66.4526, "elevation": "1,338m"},
        ]
    },
    "Quetta–Nushki–Taftan (N-40)": {
        "code": "N-40",
        "distance": "610 km",
        "alt_route": "Quetta → Mastung → Khuzdar → Basima → Washuk → Dalbandin Link",
        "alt_reason": "Southern accessible route when Lakpass or Nushki sector faces flash rain or sandstorms.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Lakpass", "lat": 29.9650, "lon": 66.8200, "elevation": "1,810m"},
            {"name": "Nushki", "lat": 29.5522, "lon": 66.0215, "elevation": "1,020m"},
            {"name": "Dalbandin", "lat": 28.8885, "lon": 64.4062, "elevation": "843m"},
            {"name": "Nok Kundi", "lat": 28.8261, "lon": 62.7489, "elevation": "680m"},
            {"name": "Taftan", "lat": 28.9667, "lon": 61.5833, "elevation": "910m"},
        ]
    },
    "Quetta–Loralai–DG Khan (N-70)": {
        "code": "N-70",
        "distance": "425 km",
        "alt_route": "Quetta → Sibi (N-65) → Jacobabad → Kashmore → Rajanpur → DG Khan (N-55)",
        "alt_reason": "Lowland accessible route during Fort Munro / Rakhni landslides and hill torrents.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Ziarat Cross", "lat": 30.3824, "lon": 67.7256, "elevation": "2,450m"},
            {"name": "Sanjawi", "lat": 30.2856, "lon": 68.3489, "elevation": "1,620m"},
            {"name": "Loralai", "lat": 30.3705, "lon": 68.5979, "elevation": "1,430m"},
            {"name": "Rakhni", "lat": 30.0683, "lon": 69.9214, "elevation": "1,110m"},
        ]
    },
}

NEARBY_FACILITIES = [
    {"route": "Quetta–Karachi (N-25)", "sector": "Quetta", "type": "Hospital", "name": "Bolan Medical Complex (BMC) Trauma Center", "lat": 30.1845, "lon": 66.9680, "phone": "081-9213030", "notes": "24/7 Emergency & Ambulance"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Mastung", "type": "Rest Area", "name": "Mastung NHA Toll Plaza & Safe Rest Area", "lat": 29.8050, "lon": 66.8500, "phone": "130 (NHA)", "notes": "Secure parking, mosque & Levies post"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Kalat", "type": "Hospital", "name": "DHQ Hospital Kalat Emergency Wing", "lat": 29.0290, "lon": 66.5910, "phone": "0844-210222", "notes": "24/7 Emergency & Cold-Weather Care"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Surab", "type": "Petrol Pump", "name": "PSO Highway Petrol & Diesel Station Surab", "lat": 28.4940, "lon": 66.2610, "phone": "0844-410115", "notes": "24/7 Fuel & Tire Air"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Khuzdar", "type": "Hospital", "name": "Teaching Hospital Khuzdar Trauma Unit", "lat": 27.8040, "lon": 66.6120, "phone": "0848-412555", "notes": "Regional Trauma & Rescue 1122"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Khuzdar", "type": "Repair Workshop", "name": "Al-Baloch Heavy Vehicle Repair Workshop", "lat": 27.7950, "lon": 66.6210, "phone": "0333-7891102", "notes": "24/7 Mechanic, Brake & Recovery Crane"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Lasbela", "type": "Rest Area", "name": "Uthal Highway Rest Area & Fuel Stop", "lat": 25.8070, "lon": 66.6210, "phone": "0853-610400", "notes": "Safe rest area & diner"},
    {"route": "Quetta–Zhob (N-50)", "sector": "Khan Mehtarzai", "type": "Rest Area", "name": "PDMA Shelter & Highway Rest Stop", "lat": 30.4850, "lon": 67.6190, "phone": "1122 / PDMA", "notes": "Heated shelter & snow clearance base"},
    {"route": "Quetta–Zhob (N-50)", "sector": "Qilla Saifullah", "type": "Hospital", "name": "DHQ Hospital Qilla Saifullah", "lat": 30.7040, "lon": 68.3580, "phone": "0823-610333", "notes": "24/7 Emergency Ward"},
    {"route": "Quetta–Zhob (N-50)", "sector": "Zhob", "type": "Petrol Pump", "name": "Shell Highway Petrol Pump & Workshop Zhob", "lat": 31.3390, "lon": 69.4450, "phone": "0822-412890", "notes": "Fuel, mechanic & rest area"},
    {"route": "Quetta–Sibi (N-65)", "sector": "Kolpur (Bolan Pass)", "type": "Rest Area", "name": "Kolpur NHA Safe Rest Area", "lat": 29.9030, "lon": 67.1520, "phone": "130 (NHA)", "notes": "Safe waiting zone during rain/landslides"},
    {"route": "Quetta–Sibi (N-65)", "sector": "Mach", "type": "Hospital", "name": "Civil Hospital Mach & Rescue 1122", "lat": 29.8650, "lon": 67.3320, "phone": "0832-210112", "notes": "Bolan Pass emergency medical aid"},
    {"route": "Quetta–Sibi (N-65)", "sector": "Sibi", "type": "Repair Workshop", "name": "Sibi Highway Auto & Truck Workshop", "lat": 29.5450, "lon": 67.8750, "phone": "0833-412770", "notes": "Engine, radiator & breakdown recovery"},
    {"route": "Quetta–Chaman (N-25 North)", "sector": "Khojak Pass (Shelabagh)", "type": "Rest Area", "name": "Shelabagh Safe Rest & Recovery Post", "lat": 30.8070, "lon": 66.5660, "phone": "130 / Levies", "notes": "Emergency towing & shelter"},
    {"route": "Quetta–Chaman (N-25 North)", "sector": "Chaman", "type": "Hospital", "name": "DHQ Hospital Chaman Emergency", "lat": 30.9190, "lon": 66.4540, "phone": "0826-613222", "notes": "24/7 Trauma & Ambulance"},
    {"route": "Quetta–Nushki–Taftan (N-40)", "sector": "Nushki", "type": "Hospital", "name": "DHQ Hospital Nushki", "lat": 29.5550, "lon": 66.0240, "phone": "0825-871444", "notes": "24/7 Emergency Unit"},
    {"route": "Quetta–Nushki–Taftan (N-40)", "sector": "Dalbandin", "type": "Petrol Pump", "name": "PSO Highway Petrol Pump & Rest Area", "lat": 28.8900, "lon": 64.4090, "phone": "0825-210300", "notes": "Fuel, water & safe rest area"},
    {"route": "Quetta–Loralai–DG Khan (N-70)", "sector": "Loralai", "type": "Hospital", "name": "Teaching Hospital Loralai", "lat": 30.3720, "lon": 68.5990, "phone": "0824-660555", "notes": "24/7 Emergency & Trauma"},
]

ROUTES = list(ROUTES_DATA.keys())
LANGUAGES = ["Urdu", "English", "Balochi", "Pashto"]
ROAD_STATUSES = ["Open (Verified)", "Restricted — Caution", "Blocked — Rain/Snow/Landslide"]
SOS_TYPES = ["Accident", "Vehicle Breakdown", "Medical Emergency"]

st.set_page_config(
    page_title="Balochistan Smart Highway Watch",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

LOGO_PATH = Path(__file__).with_name("logo.png")

@st.cache_data(show_spinner=False)
def get_logo_b64() -> str:
    if LOGO_PATH.exists():
        return base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return ""

def logo_svg(size=44):
    b64 = get_logo_b64()
    if b64:
        return (
            f'<img src="data:image/png;base64,{b64}" '
            f'style="width:{size}px;height:{size}px;object-fit:cover;border-radius:12px;'
            f'border:1px solid rgba(56,189,248,0.38);" alt="Logo"/>'
        )
    return ""

def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"

def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    if not stored_hash:
        return (False, False)
    if stored_hash.startswith("pbkdf2_sha256$"):
        parts = stored_hash.split("$", 2)
        if len(parts) != 3:
            return (False, False)
        _, salt, expected_hex = parts
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
        return (secrets.compare_digest(dk.hex(), expected_hex), False)
    legacy_hex = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if secrets.compare_digest(legacy_hex, stored_hash):
        return (True, True)
    return (False, False)

def is_valid_username(username: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", username))

def is_valid_pk_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-()]", "", phone.strip())
    return bool(re.fullmatch(r"(\+92|0092|0)?3\d{9}", cleaned))

def is_valid_plate(plate: str) -> bool:
    cleaned = re.sub(r"\s+", "", plate.strip().upper())
    return bool(re.fullmatch(r"[A-Z]{2,5}-?\d{2,4}[A-Z]?", cleaned))

def connect():
    con = sqlite3.connect(DB, timeout=15, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with connect() as con:
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            department TEXT DEFAULT 'PDMA / NHA Operations',
            role TEXT DEFAULT 'Control Room Operator',
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_code TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            vehicle_type TEXT DEFAULT 'Heavy Transport',
            route TEXT NOT NULL,
            language TEXT NOT NULL,
            status TEXT DEFAULT 'Active on Route',
            current_sector TEXT DEFAULT 'Quetta',
            next_checkpoint TEXT DEFAULT 'Mastung',
            expected_eta TEXT,
            last_checkin TEXT,
            created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS road_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route TEXT NOT NULL,
            area TEXT NOT NULL,
            status TEXT NOT NULL,
            risk_score INTEGER DEFAULT 2,
            authority_note TEXT NOT NULL,
            verified_by TEXT DEFAULT 'Control Room Quetta',
            updated_at TEXT NOT NULL,
            UNIQUE(route, area))""")
        con.execute("""CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER,
            route TEXT NOT NULL,
            language TEXT DEFAULT 'Urdu',
            severity TEXT DEFAULT 'Advisory',
            message TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE SET NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS sos_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sos_code TEXT UNIQUE,
            driver_id INTEGER,
            driver_name TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            phone TEXT NOT NULL,
            route TEXT NOT NULL,
            sector TEXT NOT NULL,
            lat REAL,
            lon REAL,
            emergency_type TEXT NOT NULL,
            source TEXT DEFAULT 'Driver SOS Button',
            details TEXT,
            status TEXT DEFAULT 'ACTIVE SOS',
            dispatched_unit TEXT DEFAULT 'Pending Dispatch',
            created_at TEXT NOT NULL,
            FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE SET NULL)""")

        existing_cols = {
            "drivers": [r[1] for r in con.execute("PRAGMA table_info(drivers)").fetchall()],
            "road_status": [r[1] for r in con.execute("PRAGMA table_info(road_status)").fetchall()],
            "alerts": [r[1] for r in con.execute("PRAGMA table_info(alerts)").fetchall()],
        }
        migrations = [
            ("drivers", "driver_code", "TEXT"),
            ("drivers", "vehicle_type", "TEXT DEFAULT 'Heavy Transport'"),
            ("drivers", "status", "TEXT DEFAULT 'Active on Route'"),
            ("drivers", "current_sector", "TEXT DEFAULT 'Quetta'"),
            ("drivers", "next_checkpoint", "TEXT DEFAULT 'Mastung'"),
            ("drivers", "expected_eta", "TEXT"),
            ("drivers", "last_checkin", "TEXT"),
            ("road_status", "risk_score", "INTEGER DEFAULT 2"),
            ("road_status", "verified_by", "TEXT DEFAULT 'Control Room Quetta'"),
            ("alerts", "language", "TEXT DEFAULT 'Urdu'"),
            ("alerts", "severity", "TEXT DEFAULT 'Advisory'"),
        ]
        for tbl, col, col_def in migrations:
            if col not in existing_cols[tbl]:
                con.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def}")

        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_road_route_area ON road_status(route, area)")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_driver_code ON drivers(driver_code)")

def rows(q, p=()):
    with connect() as con:
        return [dict(x) for x in con.execute(q, p).fetchall()]

def run(q, p=()):
    with connect() as con:
        cur = con.execute(q, p)
        con.commit()
        return cur.lastrowid

def seed():
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M")
    if not rows("SELECT id FROM users LIMIT 1"):
        run(
            "INSERT OR IGNORE INTO users(full_name,username,department,role,password_hash,created_at) VALUES(?,?,?,?,?,?)",
            ("Quetta Control Admin", "admin", "PDMA / NHA Balochistan", "Chief Command Officer", hash_password("admin123"), now_str)
        )
    if not rows("SELECT id FROM road_status LIMIT 1"):
        for route, rdata in ROUTES_DATA.items():
            for pt in rdata["points"]:
                default_status = "Open (Verified)"
                default_risk = 2
                note = "Road open and verified clear."
                if "Khan Mehtarzai" in pt["name"] or "Khojak" in pt["name"]:
                    default_status = "Restricted — Caution"
                    default_risk = 6
                    note = "High-altitude pass; snowfall & crosswind caution."
                run(
                    "INSERT OR IGNORE INTO road_status(route,area,status,risk_score,authority_note,verified_by,updated_at) VALUES(?,?,?,?,?,?,?)",
                    (route, pt["name"], default_status, default_risk, note, "Control Room Quetta", now_str)
                )
    if not rows("SELECT id FROM drivers LIMIT 1"):
        future_eta = (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        overdue_eta = (now - timedelta(minutes=35)).strftime("%Y-%m-%d %H:%M")
        sample_drivers = [
            ("BHW-2401", "Haji Abdul Wahid", "0300-8381920", "QTA-4821", "Cargo Truck", "Quetta–Karachi (N-25)", "Urdu", "Active on Route", "Mastung", "Kalat", future_eta, now_str),
            ("BHW-2402", "Sardar Khan Kakar", "0333-7812094", "ZHB-1190", "Passenger Coach", "Quetta–Zhob (N-50)", "Pashto", "Overdue — Welfare Check", "Khan Mehtarzai", "Muslim Bagh", overdue_eta, (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")),
            ("BHW-2403", "Mirwais Baloch", "0321-8904412", "KZD-7734", "Oil Tanker", "Quetta–Nushki–Taftan (N-40)", "Balochi", "Active on Route", "Nushki", "Dalbandin", future_eta, now_str),
        ]
        for d in sample_drivers:
            run(
                """INSERT OR IGNORE INTO drivers
                (driver_code,name,phone,vehicle,vehicle_type,route,language,status,current_sector,next_checkpoint,expected_eta,last_checkin,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (*d, now_str)
            )
    if not rows("SELECT id FROM sos_incidents LIMIT 1"):
        run(
            """INSERT OR IGNORE INTO sos_incidents
            (sos_code,driver_id,driver_name,vehicle,phone,route,sector,lat,lon,emergency_type,source,details,status,dispatched_unit,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("SOS-901", 2, "Sardar Khan Kakar", "ZHB-1190", "0333-7812094", "Quetta–Zhob (N-50)", "Khan Mehtarzai", 30.4833, 67.6167,
             "Vehicle Breakdown", "Automatic Checkpoint Monitor", "Missed Muslim Bagh checkpoint ETA by 35 mins — flagged for welfare check.",
             "ACTIVE SOS", "Levies Patrol #4 Dispatched", now_str)
        )

def generate_unique_driver_code() -> str:
    existing = {r["driver_code"] for r in rows("SELECT driver_code FROM drivers WHERE driver_code IS NOT NULL")}
    num = 2401 + len(rows("SELECT id FROM drivers"))
    while f"BHW-{num}" in existing:
        num += 1
    return f"BHW-{num}"

def generate_unique_sos_code() -> str:
    existing = {r["sos_code"] for r in rows("SELECT sos_code FROM sos_incidents WHERE sos_code IS NOT NULL")}
    num = 901 + len(rows("SELECT id FROM sos_incidents"))
    while f"SOS-{num}" in existing:
        num += 1
    return f"SOS-{num}"

@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
        "timezone": "Asia/Karachi"
    }
    response = requests.get(API, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def safe_float(val, default=None):
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default

def weather_info(code):
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = -1
    if code == 0:
        return ("Clear Sky", "صاف موسم", "☀️", 1)
    if code in (1, 2, 3):
        return ("Partly Cloudy", "ابر آلود", "⛅", 2)
    if code in (45, 48):
        return ("Dense Fog", "گہری دھند", "🌫️", 6)
    if code in (51, 53, 55, 56, 57):
        return ("Light Drizzle", "ہلکی بوندا باندی", "🌦️", 4)
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return ("Heavy Rain", "تیز بارش", "🌧️", 8)
    if code in (71, 73, 75, 77, 85, 86):
        return ("Snowfall", "برف باری", "❄️", 9)
    if code in (95, 96, 99):
        return ("Thunderstorm", "آندھی اور طوفان", "⛈️", 9)
    return ("Normal Weather", "موسم", "🌤️", 2)

def compute_risk_score(cur, road_status_str, manual_risk=None):
    if "Blocked" in (road_status_str or "") or "Closed" in (road_status_str or ""):
        return 10
    score = 1
    if "Restricted" in (road_status_str or ""):
        score = max(score, 6)
    if manual_risk is not None:
        try:
            score = max(score, int(manual_risk))
        except (TypeError, ValueError):
            pass
    if cur:
        code = cur.get("weather_code")
        if code is not None:
            _, _, _, w_risk = weather_info(code)
            score = max(score, w_risk)
        wind = safe_float(cur.get("wind_speed_10m"), 0.0)
        precip = safe_float(cur.get("precipitation"), 0.0)
        if wind > 35:
            score = max(score, 7)
        if precip > 2.0:
            score = max(score, 8)
    return max(1, min(int(score), 10))

def journey_risk_tier(score: int) -> tuple[str, str, str]:
    if score <= 3:
        return ("LOW", "#10b981", "rgba(16,185,129,0.16)")
    if score <= 6:
        return ("MODERATE", "#f59e0b", "rgba(245,158,11,0.18)")
    if score <= 8:
        return ("HIGH", "#f97316", "rgba(249,115,22,0.22)")
    return ("SEVERE", "#ef4444", "rgba(239,68,68,0.24)")

def get_overdue_drivers(drivers_list):
    now = datetime.now()
    overdue = []
    for d in drivers_list:
        st_val = d.get("status") or ""
        if "Safe" in st_val or "Completed" in st_val:
            continue
        eta_str = d.get("expected_eta")
        is_flagged = "Overdue" in st_val
        mins_late = 0
        if eta_str:
            try:
                eta_dt = datetime.strptime(eta_str, "%Y-%m-%d %H:%M")
                if now > eta_dt:
                    is_flagged = True
                    mins_late = int((now - eta_dt).total_seconds() // 60)
            except ValueError:
                pass
        if is_flagged:
            d_copy = dict(d)
            d_copy["mins_late"] = max(mins_late, 15)
            overdue.append(d_copy)
    return overdue

def localize_weather_term(weather_en: str, lang: str) -> str:
    mapping = {
        "Clear Sky": {"Urdu": "صاف موسم", "English": "Clear Sky", "Pashto": "ساحو هوا", "Balochi": "ساپیں موسم"},
        "Partly Cloudy": {"Urdu": "ابر آلود", "English": "Partly Cloudy", "Pashto": "نیمه وریځ", "Balochi": "نيم جمبر"},
        "Dense Fog": {"Urdu": "گہری دھند", "English": "Dense Fog", "Pashto": "سخته لړه", "Balochi": "گورم ءُ دنز"},
        "Light Drizzle": {"Urdu": "ہلکی بارش", "English": "Light Drizzle", "Pashto": "نرم باران", "Balochi": "هورتیں هور"},
        "Heavy Rain": {"Urdu": "تیز بارش", "English": "Heavy Rain", "Pashto": "تیز باران", "Balochi": "تيزیں هور"},
        "Snowfall": {"Urdu": "برف باری", "English": "Snowfall", "Pashto": "واوره", "Balochi": "برپ باری"},
        "Thunderstorm": {"Urdu": "آندھی اور طوفان", "English": "Thunderstorm", "Pashto": "توفان", "Balochi": "توپان"},
    }
    return mapping.get(weather_en, {}).get(lang, weather_en)

def generate_multilingual_alert(area, route, weather_en, road, lang):
    w_local = localize_weather_term(weather_en, lang)
    alt_str = ROUTES_DATA[route]["alt_route"]
    if lang == "English":
        if "Blocked" in road:
            return f"EMERGENCY ALERT ({route}): Road at {area} is BLOCKED due to {w_local} / landslide. Use verified accessible route: {alt_str}."
        if "Restricted" in road:
            return f"TRAVEL WARNING ({route}): Caution at {area} due to {w_local}. Reduce speed or stop at nearest safe rest area."
        return f"HIGHWAY UPDATE ({route}): {area} sector is OPEN ({w_local}). Drive safely."
    elif lang == "Urdu":
        if "Blocked" in road:
            return f"ہنگامی الرٹ ({route}): {area} کے مقام پر سڑک {w_local} / لینڈ سلائیڈنگ کے باعث بند ہے۔ متبادل محفوظ راستہ اختیار کریں: {alt_str}۔"
        if "Restricted" in road:
            return f"سفری انتباہ ({route}): {area} سیکٹر میں {w_local} کے باعث احتیاط برتیں اور قریبی محفوظ ریسٹ ایریا پر رکیں۔"
        return f"موسمی اپ ڈیٹ ({route}): {area} میں موسم {w_local} ہے اور شاہراہ کھلی ہے۔"
    elif lang == "Pashto":
        if "Blocked" in road:
            return f"بیړنی خبرتیا ({route}): د {area} په سیمه کې لاره د {w_local} / ځمکې ښویدنې له امله تړل شوې ده. بدیله خوندي لاره وکاروئ: {alt_str}."
        if "Restricted" in road:
            return f"د احتیاط خبرتیا ({route}): د {area} په سیمه کې د {w_local} له امله سرعت کم کړئ او په خوندي ځای کې ودریږئ."
        return f"د لارې تازه معلومات ({route}): د {area} لاره خلاصه ده او هوا {w_local} ده."
    else:
        if "Blocked" in road:
            return f"هنگامی حال ({route}): {area} ءِ دمگ ءَ راه {w_local} / لینڈ سلائیڈنگ ءِ سوب ءَ بند انت۔ دومی محفوظیں راه ءَ بہ رو ات: {alt_str}۔"
        if "Restricted" in road:
            return f"هوشیاری حال ({route}): {area} ءِ دمگ ءَ {w_local} ءِ سوب ءَ هوشیاری بہ کن ات ءُ نزیکیں ریسٹ ایریا ءَ اوشت ات۔"
        return f"موسمی ءُ راه ءِ حال ({route}): {area} ءِ دمگ ءَ راه پچ انت ءُ موسم {w_local} انت۔"

def render_balochistan_map(selected_route, weather_cache, road_map, sos_list=None, facilities_list=None, show_facilities=True):
    routes_payload = []
    for r_name, r_data in ROUTES_DATA.items():
        pts_out = []
        max_r = 1
        for pt in r_data["points"]:
            w_cur = weather_cache.get(pt["name"], {})
            r_row = road_map.get((r_name, pt["name"]), {})
            r_stat = r_row.get("status", "Open (Verified)")
            r_score = compute_risk_score(w_cur, r_stat, r_row.get("risk_score"))
            max_r = max(max_r, r_score)
            label_txt, _, _, _ = weather_info(w_cur.get("weather_code")) if w_cur else ("Normal", "", "", 2)
            temp_disp = f"{safe_float(w_cur.get('temperature_2m')):.1f}" if safe_float(w_cur.get("temperature_2m")) is not None else "—"
            tier_lbl, _, _ = journey_risk_tier(r_score)
            pts_out.append({
                "name": pt["name"], "lat": pt["lat"], "lon": pt["lon"], "elev": pt["elevation"],
                "temp": temp_disp, "weather": label_txt, "status": r_stat, "risk": r_score, "tier": tier_lbl
            })
        _, color_hex, _ = journey_risk_tier(max_r)
        routes_payload.append({
            "name": r_name, "code": r_data["code"], "distance": r_data["distance"],
            "selected": (r_name == selected_route), "color": color_hex, "max_risk": max_r, "points": pts_out
        })

    sos_payload = [
        {"code": s.get("sos_code", "SOS"), "driver": s.get("driver_name", ""), "vehicle": s.get("vehicle", ""),
         "type": s.get("emergency_type", ""), "sector": s.get("sector", ""), "lat": float(s["lat"]), "lon": float(s["lon"]), "details": s.get("details", "")}
        for s in (sos_list or []) if s.get("status") == "ACTIVE SOS" and s.get("lat") and s.get("lon")
    ]

    fac_payload = [
        {"type": fc["type"], "name": fc["name"], "sector": fc["sector"], "phone": fc["phone"], "notes": fc["notes"], "lat": fc["lat"], "lon": fc["lon"]}
        for fc in (facilities_list or []) if show_facilities
    ]

    r_json = json.dumps(routes_payload).replace("</", "<\\/")
    s_json = json.dumps(sos_payload).replace("</", "<\\/")
    f_json = json.dumps(fac_payload).replace("</", "<\\/")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <style>
        html, body, #map {{ height: 100%; width: 100%; margin: 0; padding: 0; background: #060e1a; font-family: 'Inter', sans-serif; }}
        .legend-bar {{
          position: absolute; top: 12px; left: 52px; z-index: 999;
          background: rgba(9, 20, 36, 0.92); border: 1px solid rgba(56, 189, 248, 0.25);
          border-radius: 10px; padding: 7px 13px; color: #e2e8f0; font-size: 11px;
          display: flex; align-items: center; gap: 9px;
        }}
        .pill {{ padding: 2px 8px; border-radius: 5px; font-weight: 800; font-size: 10px; }}
        .custom-popup .leaflet-popup-content-wrapper {{ background: #0b192c; color: #f1f5f9; border: 1px solid #1e3a5f; border-radius: 12px; }}
        .custom-popup .leaflet-popup-tip {{ background: #0b192c; }}
        .sos-badge-icon {{
          background: #ef4444; color: #fff; font-weight: 900; font-size: 10px;
          border: 2px solid #fff; border-radius: 50%; width: 28px; height: 28px;
          display: flex; align-items: center; justify-content: center; box-shadow: 0 0 15px #ef4444;
        }}
        .fac-badge-icon {{
          background: #0284c7; color: #fff; font-size: 11px; border: 1.5px solid #bae6fd;
          border-radius: 6px; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center;
        }}
      </style>
    </head>
    <body>
      <div id="map"></div>
      <div class="legend-bar">
        <span style="font-weight:700;color:#94a3b8;">RISK RATING:</span>
        <span class="pill" style="background:rgba(16,185,129,0.2);color:#34d399;border:1px solid #10b981;">LOW</span>
        <span class="pill" style="background:rgba(245,158,11,0.2);color:#fbbf24;border:1px solid #f59e0b;">MODERATE</span>
        <span class="pill" style="background:rgba(249,115,22,0.22);color:#fb923c;border:1px solid #f97316;">HIGH</span>
        <span class="pill" style="background:rgba(239,68,68,0.25);color:#f87171;border:1px solid #ef4444;">SEVERE</span>
        <span>🏥 Hospital • ⛽ Petrol • 🔧 Workshop • 🛡️ Rest Area</span>
      </div>
      <script>
        const routesData = {r_json};
        const sosData = {s_json};
        const facData = {f_json};

        const map = L.map('map', {{ center: [28.95, 65.85], zoom: 6 }});
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
          attribution: '&copy; OpenStreetMap &copy; CARTO', subdomains: 'abcd', maxZoom: 18
        }}).addTo(map);

        let selectedBounds = [];
        routesData.forEach(route => {{
          const latlngs = route.points.map(p => [p.lat, p.lon]);
          const isSel = route.selected;
          L.polyline(latlngs, {{
            color: route.color, weight: isSel ? 4.5 : 2.5, opacity: isSel ? 0.95 : 0.6, dashArray: isSel ? null : '6, 6'
          }}).addTo(map);

          route.points.forEach(pt => {{
            if (isSel) selectedBounds.push([pt.lat, pt.lon]);
            let ptColor = pt.risk >= 9 ? '#ef4444' : (pt.risk >= 7 ? '#f97316' : (pt.risk >= 4 ? '#f59e0b' : '#10b981'));
            const marker = L.circleMarker([pt.lat, pt.lon], {{
              radius: isSel ? 7.5 : 5, fillColor: ptColor, color: '#ffffff', weight: 1.5, fillOpacity: 0.95
            }}).addTo(map);
            marker.bindPopup(`<b>${{pt.name}}</b> (${{pt.elev}})<br/>Temp: ${{pt.temp}}°C • ${{pt.weather}}<br/>Status: <b style="color:${{ptColor}}">${{pt.status}}</b><br/>Risk: <b>${{pt.tier}}</b>`, {{className: 'custom-popup'}});
            if (isSel) marker.bindTooltip(`${{pt.name}} (${{pt.tier}})`, {{permanent: true, direction: 'top', offset: [0, -8]}});
          }});
        }});

        facData.forEach(fc => {{
          let sym = fc.type === 'Petrol Pump' ? '⛽' : (fc.type === 'Repair Workshop' ? '🔧' : (fc.type === 'Rest Area' ? '🛡️' : '🏥'));
          const fIcon = L.divIcon({{ className: '', html: `<div class="fac-badge-icon">${{sym}}</div>`, iconSize: [22, 22], iconAnchor: [11, 11] }});
          L.marker([fc.lat + 0.03, fc.lon + 0.03], {{icon: fIcon}}).addTo(map)
            .bindPopup(`<b>${{fc.name}}</b><br/>Type: ${{fc.type}} (${{fc.sector}})<br/>Phone: <b>${{fc.phone}}</b><br/>${{fc.notes}}`, {{className: 'custom-popup'}});
        }});

        sosData.forEach(s => {{
          const sIcon = L.divIcon({{ className: '', html: `<div class="sos-badge-icon">SOS</div>`, iconSize: [28, 28], iconAnchor: [14, 14] }});
          L.marker([s.lat, s.lon], {{icon: sIcon}}).addTo(map)
            .bindPopup(`<b style="color:#ef4444;">🚨 ACTIVE SOS (${{s.code}})</b><br/>Vehicle: <b>${{s.vehicle}}</b> (${{s.driver}})<br/>Emergency: ${{s.type}}<br/>Location: ${{s.sector}}`, {{className: 'custom-popup'}});
        }});

        if (selectedBounds.length > 1) map.fitBounds(selectedBounds, {{padding: [50, 50]}});
        setTimeout(() => map.invalidateSize(), 200);
      </script>
    </body>
    </html>
    """
    components.html(html, height=450, scrolling=False)

if "_db_initialized" not in st.session_state:
    init_db()
    seed()
    st.session_state["_db_initialized"] = True

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@600;800&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');

.stApp {
  background: linear-gradient(180deg, #050b16 0%, #071122 100%);
  color: #f8fafc;
  font-family: 'Plus Jakarta Sans', sans-serif;
}
[data-testid="stSidebar"] {
  background: #060f1e;
  border-right: 1px solid rgba(6, 182, 212, 0.22);
}
.block-container { padding-top: 0.9rem; padding-bottom: 2rem; max-width: 1550px; }
h1, h2, h3, h4 { color: #f8fafc !important; }

.cmd-topbar {
  background: linear-gradient(105deg, #091527 0%, #0c2138 100%);
  border: 1px solid rgba(6, 182, 212, 0.32);
  border-top: 2px solid #10b981;
  border-radius: 16px;
  padding: 14px 22px;
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stat-card {
  background: #0b182c;
  border: 1px solid rgba(56, 189, 248, 0.22);
  border-top: 2px solid #06b6d4;
  border-radius: 14px;
  padding: 14px 16px;
}
.stat-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8; font-weight: 700; }
.stat-val { font-size: 26px; font-weight: 800; color: #f8fafc; margin: 4px 0; font-family: 'JetBrains Mono', monospace; }
.stat-foot { font-size: 11px; color: #38bdf8; }

.side-panel-card {
  background: #0b182c;
  border: 1px solid rgba(6, 182, 212, 0.24);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 14px;
}
.notif-item {
  background: #0e1f38;
  border-left: 3.5px solid #f59e0b;
  border-radius: 9px;
  padding: 9px 12px;
  margin-bottom: 8px;
}
.notif-item.danger { border-left-color: #ef4444; }
.notif-item.safe { border-left-color: #10b981; }

/* Prominent Circular Red SOS Button Styling (Matches Screenshot #1) */
div[data-testid="stButton"] button[kind="primary"] {
  background: radial-gradient(circle, #ef4444 0%, #b91c1c 100%) !important;
  color: #ffffff !important;
  border: 4px solid #fecaca !important;
  border-radius: 999px !important;
  font-size: 22px !important;
  font-weight: 900 !important;
  letter-spacing: 1.5px !important;
  height: 115px !important;
  width: 115px !important;
  margin: 0 auto !important;
  display: block !important;
  box-shadow: 0 0 0 6px rgba(239, 68, 68, 0.25), 0 10px 28px rgba(239, 68, 68, 0.6) !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover {
  transform: scale(1.05);
  box-shadow: 0 0 0 10px rgba(239, 68, 68, 0.35), 0 14px 34px rgba(239, 68, 68, 0.8) !important;
}

.urdu-box {
  font-family: 'Noto Nastaliq Urdu', sans-serif;
  direction: rtl; text-align: right; line-height: 2.0; font-size: 15px;
  background: #081322; border: 1px solid rgba(16, 185, 129, 0.4);
  border-radius: 12px; padding: 14px 18px; color: #f1f5f9;
}
.ltr-box {
  direction: ltr; text-align: left; line-height: 1.65; font-size: 14px;
  background: #081322; border: 1px solid rgba(6, 182, 212, 0.4);
  border-radius: 12px; padding: 14px 18px; color: #f1f5f9;
}
</style>
""", unsafe_allow_html=True)

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

if st.session_state["auth_user"] is None:
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1.1, 1.3, 1.1])
    with center_col:
        st.markdown(f"""
        <div class="side-panel-card" style="text-align:center;">
          {logo_svg(64)}
          <h3 style="margin:10px 0 4px 0;">Balochistan Smart Highway Watch</h3>
          <div style="font-size:12px;color:#2dd4bf;font-weight:700;">CONTROL ROOM & DRIVER SAFETY PORTAL</div>
          <div style="font-size:12px;color:#cbd5e1;font-style:italic;margin-top:6px;">"We don't just predict dangerous journeys. We help prevent them."</div>
        </div>
        """, unsafe_allow_html=True)
        t1, t2 = st.tabs(["🔐 Sign In", "📝 Sign Up"])
        with t1:
            with st.form("login_f"):
                u_in = st.text_input("Username", placeholder="admin")
                p_in = st.text_input("Password", type="password", placeholder="admin123")
                if st.form_submit_button("Sign In", use_container_width=True):
                    matched = rows("SELECT * FROM users WHERE LOWER(username)=LOWER(?)", (u_in.strip(),))
                    if matched and verify_password(p_in, matched[0]["password_hash"])[0]:
                        st.session_state["auth_user"] = matched[0]
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
            st.caption("Default login: `admin` / `admin123`")
        with t2:
            with st.form("signup_f", clear_on_submit=True):
                fn = st.text_input("Officer Full Name")
                un = st.text_input("Username")
                dept = st.selectbox("Department", ["PDMA Balochistan", "NHA", "Balochistan Levies", "Highway Police"])
                pw1 = st.text_input("Password", type="password")
                pw2 = st.text_input("Confirm Password", type="password")
                if st.form_submit_button("Create Account", use_container_width=True):
                    if fn.strip() and is_valid_username(un.strip()) and len(pw1) >= 6 and pw1 == pw2:
                        try:
                            uid = run("INSERT INTO users(full_name,username,department,role,password_hash,created_at) VALUES(?,?,?,?,?,?)",
                                      (fn.strip(), un.strip(), dept, "Operator", hash_password(pw1), datetime.now().strftime("%Y-%m-%d %H:%M")))
                            st.session_state["auth_user"] = rows("SELECT * FROM users WHERE id=?", (uid,))[0]
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Username already exists.")
                    else:
                        st.error("Check fields (min 6-char matching password & valid username).")
    st.stop()

current_user = st.session_state["auth_user"]
road_rows_all = rows("SELECT * FROM road_status")
road_lookup = {(r["route"], r["area"]): r for r in road_rows_all}
all_drivers_global = rows("SELECT * FROM drivers ORDER BY id DESC")
active_sos_global = rows("SELECT * FROM sos_incidents WHERE status='ACTIVE SOS' ORDER BY id DESC")
overdue_drivers_global = get_overdue_drivers(all_drivers_global)

with st.sidebar:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;padding-bottom:12px;">
      {logo_svg(44)}
      <div>
        <div style="font-weight:800;font-size:14px;">HIGHWAY WATCH</div>
        <div style="font-size:10px;color:#2dd4bf;font-weight:700;">BALOCHISTAN CONTROL</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    sos_tag = f" ({len(active_sos_global)})" if active_sos_global else ""
    nav_choice = st.radio(
        "FEATURES",
        [
            "1. Admin Control Dashboard",
            f"2. Emergency SOS & Auto Monitoring{sos_tag}",
            "3. Alternative Safe Routes & Facilities",
            "4. Multilingual Alerts",
            "5. Journey Risk & Vehicle Registration",
        ]
    )
    st.markdown("---")
    selected_corridor = st.selectbox("Select Highway", ROUTES)
    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state["auth_user"] = None
        st.rerun()

    st.markdown("""
    <div style="margin-top:12px;padding:11px;background:#081322;border:1px solid rgba(56,189,248,0.22);border-radius:12px;font-size:11px;color:#94a3b8;">
      <div style="color:#2dd4bf;font-weight:700;margin-bottom:3px;">VISION STATEMENT</div>
      <div style="font-style:italic;color:#cbd5e1;">"We don't just predict dangerous journeys. We help prevent them."</div>
    </div>
    """, unsafe_allow_html=True)


st.markdown(f"""
<div class="cmd-topbar">
  <div style="display:flex;align-items:center;gap:12px;">
    {logo_svg(42)}
    <div>
      <div style="font-size:18px;font-weight:800;">Balochistan Smart Highway Watch</div>
      <div style="font-size:12px;color:#94a3b8;">"We don't just predict dangerous journeys. We help prevent them." • Operator: {current_user['full_name']}</div>
    </div>
  </div>
  <div style="font-size:12px;color:#34d399;font-weight:800;">● LIVE MONITORING</div>
</div>
""", unsafe_allow_html=True)

def get_corridor_weather(route_name):
    cache = {}
    for pt in ROUTES_DATA[route_name]["points"]:
        try:
            cache[pt["name"]] = fetch_weather(pt["lat"], pt["lon"]).get("current", {})
        except Exception:
            cache[pt["name"]] = {}
    return cache

def compute_corridor_overall_risk(route_name, w_cache):
    max_s = 1
    worst_sector = ROUTES_DATA[route_name]["points"][0]["name"]
    for pt in ROUTES_DATA[route_name]["points"]:
        cur = w_cache.get(pt["name"], {})
        r_obj = road_lookup.get((route_name, pt["name"]), {})
        sc = compute_risk_score(cur, r_obj.get("status", "Open (Verified)"), r_obj.get("risk_score"))
        if sc >= max_s:
            max_s = sc
            worst_sector = pt["name"]
    tier, color, bg = journey_risk_tier(max_s)
    return max_s, tier, color, bg, worst_sector

if nav_choice == "1. Admin Control Dashboard":
    w_cache = get_corridor_weather(selected_corridor)
    c_score, c_tier, c_color, c_bg, c_worst = compute_corridor_overall_risk(selected_corridor, w_cache)
    dangerous_routes = [r for r in road_rows_all if "Blocked" in r["status"] or "Restricted" in r["status"]]

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="stat-card"><div class="stat-label">Registered Vehicles</div><div class="stat-val">{len(all_drivers_global)}</div><div class="stat-foot">Active Journeys Monitored</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="stat-card"><div class="stat-label">Emergency SOS Alerts</div><div class="stat-val" style="color:#ef4444;">{len(active_sos_global)}</div><div class="stat-foot">Active Control Room Queue</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="stat-card"><div class="stat-label">Dangerous Routes</div><div class="stat-val" style="color:#f59e0b;">{len(dangerous_routes)}</div><div class="stat-foot">Blocked / Caution Sectors</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="stat-card"><div class="stat-label">Journey Risk Score</div><div class="stat-val" style="color:{c_color};">{c_tier}</div><div class="stat-foot">Critical Point: {c_worst}</div></div>', unsafe_allow_html=True)

    if c_score >= 6:
        st.warning(f"**⚠️ Dangerous Route Alert ({selected_corridor} — {c_tier} Risk at {c_worst}):** Verified Alternative Safe Route → `{ROUTES_DATA[selected_corridor]['alt_route']}`")

    col_map, col_panel = st.columns([2.1, 1.1], gap="medium")

    with col_map:
        render_balochistan_map(selected_corridor, w_cache, road_lookup, sos_list=active_sos_global, facilities_list=NEARBY_FACILITIES)

        
        # 7 Core Features Showcase (Matching User Screenshots 1-7)
        st.markdown('<div style="font-size:13px;font-weight:800;letter-spacing:0.6px;color:#34d399;margin:14px 0 8px 0;">7 CORE SAFETY FEATURES</div>', unsafe_allow_html=True)
        feat_items = [
            ("1. Emergency SOS", "One-button SOS for accident, breakdown, or medical emergency — sends location & vehicle number to control room."),
            ("2. Alternative Safe Routes", "Verified accessible detour when blocked due to rain, snowfall, or landslides."),
            ("3. Multilingual Alerts", "Warnings in Urdu, English, Balochi, and Pashto."),
            ("4. Admin Control Dashboard", "Registered vehicles, active journeys, emergency alerts, and dangerous routes in one place."),
            ("5. Nearby Facilities", "Hospitals, petrol pumps, repair workshops, and rest areas."),
            ("6. Journey Risk Score", "Low, Moderate, High, or Severe rating based on weather & verified road conditions."),
            ("7. Automatic SOS / Journey Monitoring", "Flags vehicles missing an expected checkpoint for a control room welfare check."),
        ]
        feat_cards_html = "".join([
            f'<div style="background:#0c1b30;border:1px solid rgba(52,211,153,0.25);border-left:3.5px solid #10b981;border-radius:11px;padding:10px 12px;">'
            f'<div style="font-size:12px;font-weight:800;color:#f8fafc;">{ft}</div>'
            f'<div style="font-size:11px;color:#cbd5e1;margin-top:2px;line-height:1.4;">{fd}</div>'
            f'</div>'
            for ft, fd in feat_items
        ])
        st.markdown(f'<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-bottom:10px;">{feat_cards_html}</div>', unsafe_allow_html=True)

        # Har City / Checkpoint ka Live Weather Cards
        st.markdown(f'<div style="font-size:12px;font-weight:800;letter-spacing:0.6px;color:#38bdf8;margin:12px 0 7px 0;">{selected_corridor.upper()} — LIVE WEATHER BY CITY / CHECKPOINT</div>', unsafe_allow_html=True)
        city_pts = ROUTES_DATA[selected_corridor]["points"]
        weather_cards_list = []
        for pt_c in city_pts:
            cur_c = w_cache.get(pt_c["name"], {})
            w_en_c, w_ur_c, w_ico_c, _ = weather_info(cur_c.get("weather_code")) if cur_c else ("Normal", "Mausam", "Cloud", 2)
            t_val = safe_float(cur_c.get("temperature_2m"))
            wind_val = safe_float(cur_c.get("wind_speed_10m"))
            rain_val = safe_float(cur_c.get("precipitation"))
            t_str = f"{t_val:.1f} C" if t_val is not None else "N/A"
            w_str = f"{wind_val:.0f} km/h" if wind_val is not None else "N/A"
            r_str = f"{rain_val:.1f} mm" if rain_val is not None else "0.0 mm"
            r_obj_c = road_lookup.get((selected_corridor, pt_c["name"]), {})
            sc_c = compute_risk_score(cur_c, r_obj_c.get("status", "Open (Verified)"), r_obj_c.get("risk_score"))
            tr_c, col_c, _ = journey_risk_tier(sc_c)
            weather_cards_list.append(
                f'<div style="background:#0b182c;border:1px solid rgba(56,189,248,0.22);border-top:3px solid {col_c};border-radius:12px;padding:10px 12px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="font-size:12px;font-weight:800;color:#f8fafc;">{pt_c["name"]}</span>'
                f'<span style="font-size:10px;font-weight:800;color:{col_c};">{tr_c}</span>'
                f'</div>'
                f'<div style="font-size:17px;font-weight:800;color:#38bdf8;margin:4px 0;font-family:'JetBrains Mono',monospace;">{w_str} • {t_str}</div>'
                f'<div style="font-size:11px;color:#cbd5e1;font-weight:600;">{w_en_c} ({w_ur_c})</div>'
                f'<div style="font-size:10px;color:#94a3b8;margin-top:3px;">Rain: {r_str} • Elev: {pt_c["elevation"]}</div>'
                f'</div>'
            )
        st.markdown(f'<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:10px;">{"".join(weather_cards_list)}</div>', unsafe_allow_html=True)

        # Vision Statement placed cleanly after the 7 features & city weathers
        st.markdown("""
        <div style="margin-top:8px;margin-bottom:12px;padding:14px 18px;background:linear-gradient(90deg,rgba(16,185,129,0.14),rgba(6,182,212,0.14));border:1px solid rgba(52,211,153,0.45);border-radius:14px;text-align:center;">
          <div style="font-size:10px;font-weight:800;letter-spacing:1.2px;color:#34d399;text-transform:uppercase;">VISION STATEMENT</div>
          <div style="font-size:14px;font-weight:700;font-style:italic;color:#f8fafc;margin-top:4px;">"We don't just predict dangerous journeys. We help prevent them."</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🛣️ Update Verified Road Condition (Open / Restricted / Blocked)"):
            all_roads = rows("SELECT * FROM road_status ORDER BY route, id")
            seg_map = {f"{r['route']} | {r['area']} ({r['status']})": r for r in all_roads}
            sel_seg = seg_map[st.selectbox("Select Sector", list(seg_map.keys()))]
            c_u1, c_u2 = st.columns(2)
            new_st = c_u1.selectbox("Road Condition", ROAD_STATUSES, index=ROAD_STATUSES.index(sel_seg["status"]) if sel_seg["status"] in ROAD_STATUSES else 0)
            new_note = c_u2.text_input("Reason (e.g. Rain, Snowfall, Landslide)", value=sel_seg["authority_note"])
            if st.button("Save Road Status", use_container_width=True):
                r_sc = 10 if "Blocked" in new_st else (6 if "Restricted" in new_st else 2)
                run("UPDATE road_status SET status=?, risk_score=?, authority_note=?, updated_at=? WHERE id=?",
                    (new_st, r_sc, new_note, datetime.now().strftime("%Y-%m-%d %H:%M"), sel_seg["id"]))
                st.rerun()

    with col_panel:
        st.markdown('<div class="side-panel-card" style="text-align:center;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:13px;font-weight:800;color:#fca5a5;margin-bottom:4px;">ONE-TAP EMERGENCY SOS</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;color:#94a3b8;margin-bottom:10px;">Sends live GPS location & vehicle number directly to Control Room</div>', unsafe_allow_html=True)
        if st.button("SOS", type="primary", key="quick_dash_sos"):
            top_d = all_drivers_global[0] if all_drivers_global else None
            rt_s = top_d["route"] if top_d else selected_corridor
            sec_s = top_d.get("current_sector", "Quetta") if top_d else ROUTES_DATA[selected_corridor]["points"][0]["name"]
            pt_o = next((p for p in ROUTES_DATA[rt_s]["points"] if p["name"] == sec_s), ROUTES_DATA[rt_s]["points"][0])
            s_c = generate_unique_sos_code()
            now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
            run(
                """INSERT INTO sos_incidents(sos_code,driver_id,driver_name,vehicle,phone,route,sector,lat,lon,emergency_type,source,details,status,dispatched_unit,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (s_c, top_d["id"] if top_d else None, top_d["name"] if top_d else "Highway Driver",
                 top_d["vehicle"] if top_d else "QTA-001", top_d["phone"] if top_d else "0300-0000000",
                 rt_s, sec_s, pt_o["lat"], pt_o["lon"], "Accident / Emergency", "One-Tap Red SOS Button",
                 "Immediate SOS triggered from main screen.", "ACTIVE SOS", "Rescue & Levies Dispatched", now_s)
            )
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="side-panel-card">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:12px;font-weight:800;color:#ef4444;margin-bottom:6px;">🚨 EMERGENCY ALERTS & WELFARE FLAGS</div>', unsafe_allow_html=True)
        for s in active_sos_global[:3]:
            st.markdown(f"""
            <div class="notif-item danger">
              <div style="font-size:12px;font-weight:800;color:#fca5a5;">{s['sos_code']} • {s['vehicle']} ({s['emergency_type']})</div>
              <div style="font-size:11px;color:#e2e8f0;">{s['driver_name']} • Location: <b>{s['sector']}</b></div>
            </div>
            """, unsafe_allow_html=True)
        for od in overdue_drivers_global[:2]:
            st.markdown(f"""
            <div class="notif-item">
              <div style="font-size:11px;font-weight:800;color:#fdba74;">⏱️ Missed Checkpoint: {od['vehicle']} ({od['name']})</div>
              <div style="font-size:10px;color:#94a3b8;">Overdue at {od.get('next_checkpoint')} by {od['mins_late']} mins</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div style="font-size:12px;font-weight:800;color:#38bdf8;margin:10px 0 6px 0;">🚛 ACTIVE JOURNEYS & VEHICLES</div>', unsafe_allow_html=True)
        for d in all_drivers_global[:4]:
            st.markdown(f"""
            <div class="notif-item safe">
              <div style="font-size:11px;font-weight:800;">{d['vehicle']} • {d['name']}</div>
              <div style="font-size:10px;color:#94a3b8;">{d['route']} • Sector: {d.get('current_sector')} ({d['status']})</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div style="font-size:12px;font-weight:800;color:#f59e0b;margin:10px 0 6px 0;">⚠️ DANGEROUS ROUTES</div>', unsafe_allow_html=True)
        for dr in dangerous_routes[:3]:
            st.markdown(f"""
            <div class="notif-item danger">
              <div style="font-size:11px;font-weight:800;color:#fca5a5;">{dr['area']} ({dr['route']})</div>
              <div style="font-size:10px;color:#cbd5e1;">{dr['status']} — {dr['authority_note']}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif nav_choice.startswith("2. Emergency SOS"):
    st.subheader("1. Emergency SOS & Automatic Journey Monitoring")
    c_left, c_right = st.columns([1.05, 1.55], gap="large")

    with c_left:
        st.markdown('<div class="side-panel-card" style="text-align:center;">', unsafe_allow_html=True)
        st.markdown("#### Driver One-Button Emergency SOS")
        st.caption("Press one button to report an accident, vehicle breakdown, or medical emergency. Location & vehicle number go straight to the control room.")

        if all_drivers_global:
            drv_map = {f"{d['vehicle']} — {d['name']}": d for d in all_drivers_global}
            sel_d = drv_map[st.selectbox("Vehicle & Driver", list(drv_map.keys()))]
            def_idx = ROUTES.index(sel_d["route"]) if sel_d["route"] in ROUTES else 0
        else:
            sel_d = None
            def_idx = 0

        sos_rt = st.selectbox("Highway Corridor", ROUTES, index=def_idx)
        sos_sec = st.selectbox("Current Location / Sector", [p["name"] for p in ROUTES_DATA[sos_rt]["points"]])
        sos_cat = st.radio("Emergency Type", SOS_TYPES, horizontal=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("SOS", type="primary", key="big_sos_btn"):
            pt_obj = next((p for p in ROUTES_DATA[sos_rt]["points"] if p["name"] == sos_sec), ROUTES_DATA[sos_rt]["points"][0])
            s_code = generate_unique_sos_code()
            now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
            run(
                """INSERT INTO sos_incidents(sos_code,driver_id,driver_name,vehicle,phone,route,sector,lat,lon,emergency_type,source,details,status,dispatched_unit,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (s_code, sel_d["id"] if sel_d else None, sel_d["name"] if sel_d else "Driver",
                 sel_d["vehicle"] if sel_d else "UNREG-01", sel_d["phone"] if sel_d else "0300-0000000",
                 sos_rt, sos_sec, pt_obj["lat"], pt_obj["lon"], sos_cat, "Driver SOS Button",
                 f"{sos_cat} reported at {sos_sec}. GPS & vehicle number sent to Control Room.",
                 "ACTIVE SOS", "Emergency Response Dispatched", now_s)
            )
            if sel_d:
                run("UPDATE drivers SET status='ACTIVE SOS', current_sector=? WHERE id=?", (sos_sec, sel_d["id"]))
            st.error(f"🚨 SOS {s_code} SENT! Location ({pt_obj['lat']}, {pt_obj['lon']}) & Vehicle {sel_d['vehicle'] if sel_d else ''} transmitted to Control Room.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c_right:
        st.markdown("#### Control Room SOS Incidents")
        for item in rows("SELECT * FROM sos_incidents ORDER BY id DESC"):
            act = item["status"] == "ACTIVE SOS"
            col_b = "#ef4444" if act else "#10b981"
            st.markdown(f"""
            <div style="background:#0b182c;border:1px solid {col_b};border-left:5px solid {col_b};border-radius:12px;padding:12px 15px;margin-bottom:10px;">
              <div style="display:flex;justify-content:space-between;font-weight:800;">
                <span>{item['sos_code']} • Vehicle: {item['vehicle']} ({item['driver_name']})</span>
                <span style="color:{col_b};">{item['status']}</span>
              </div>
              <div style="font-size:12px;color:#cbd5e1;margin-top:4px;">
                <b>Emergency:</b> {item['emergency_type']} | <b>Location:</b> {item['sector']} ({item.get('lat')}, {item.get('lon')}) | <b>Phone:</b> {item['phone']}
              </div>
            </div>
            """, unsafe_allow_html=True)
            if act and st.button(f"✅ Mark {item['sos_code']} Resolved", key=f"res_sos_{item['id']}"):
                run("UPDATE sos_incidents SET status='RESOLVED' WHERE id=?", (item["id"],))
                if item.get("driver_id"):
                    run("UPDATE drivers SET status='Active on Route' WHERE id=?", (item["driver_id"],))
                st.rerun()

        st.markdown("---")
        st.markdown("#### 7. Automatic SOS / Journey Monitoring (Missed Checkpoints)")
        if overdue_drivers_global:
            for od in overdue_drivers_global:
                st.warning(f"**Welfare Check Flag:** Vehicle **{od['vehicle']}** ({od['name']}) missed **{od.get('next_checkpoint')}** checkpoint by **{od['mins_late']} mins**.")
                w1, w2 = st.columns(2)
                if w1.button(f"🚨 Trigger Auto-SOS ({od['vehicle']})", key=f"auto_sos_{od['id']}", use_container_width=True):
                    pt_o = next((p for p in ROUTES_DATA[od["route"]]["points"] if p["name"] == od.get("current_sector")), ROUTES_DATA[od["route"]]["points"][0])
                    run(
                        """INSERT INTO sos_incidents(sos_code,driver_id,driver_name,vehicle,phone,route,sector,lat,lon,emergency_type,source,details,status,dispatched_unit,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (generate_unique_sos_code(), od["id"], od["name"], od["vehicle"], od["phone"], od["route"],
                         od.get("current_sector", "En Route"), pt_o["lat"], pt_o["lon"], "Missed Checkpoint Welfare Check",
                         "Automatic Journey Monitor", f"Missed {od.get('next_checkpoint')} by {od['mins_late']} mins.",
                         "ACTIVE SOS", "Welfare Patrol Dispatched", datetime.now().strftime("%Y-%m-%d %H:%M"))
                    )
                    run("UPDATE drivers SET status='ACTIVE SOS' WHERE id=?", (od["id"],))
                    st.rerun()
                if w2.button(f"✓ Confirm Welfare OK ({od['vehicle']})", key=f"ok_welf_{od['id']}", use_container_width=True):
                    run("UPDATE drivers SET status='Active on Route', expected_eta=? WHERE id=?",
                        ((datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), od["id"]))
                    st.rerun()
        else:
            st.success("No overdue vehicles — all checkpoints on schedule.")

elif nav_choice == "3. Alternative Safe Routes & Facilities":
    st.subheader("2. Alternative Safe Routes & 5. Nearby Facilities")
    c1, c2 = st.columns([1.15, 2.35], gap="medium")

    with c1:
        rt_sel = st.selectbox("Select Highway Corridor", ROUTES, index=ROUTES.index(selected_corridor))
        w_c = get_corridor_weather(rt_sel)
        sc, tr, col_t, bg_t, worst_p = compute_corridor_overall_risk(rt_sel, w_c)

        st.markdown(f"""
        <div style="background:{bg_t};border:1px solid {col_t};border-radius:12px;padding:13px;margin-bottom:12px;">
          <div style="font-size:11px;font-weight:800;color:{col_t};">ROUTE STATUS: {tr} RISK ({worst_p})</div>
          <div style="font-size:13px;font-weight:800;margin-top:6px;">Verified Accessible Alternative Route:</div>
          <div style="font-size:12px;color:#5eead4;margin-top:3px;">{ROUTES_DATA[rt_sel]['alt_route']}</div>
          <div style="font-size:11px;color:#cbd5e1;margin-top:5px;">{ROUTES_DATA[rt_sel]['alt_reason']}</div>
        </div>
        """, unsafe_allow_html=True)

        fac_type = st.selectbox("Filter Nearby Facilities", ["All", "Hospital", "Petrol Pump", "Repair Workshop", "Rest Area"])
        facs = [f for f in NEARBY_FACILITIES if f["route"] == rt_sel and (fac_type == "All" or f["type"] == fac_type)]
        for fc in facs:
            st.markdown(f"""
            <div class="notif-item safe">
              <div style="font-size:12px;font-weight:800;">{fc['name']} <span style="color:#38bdf8;">({fc['type']})</span></div>
              <div style="font-size:11px;color:#2dd4bf;">{fc['sector']} • 📞 {fc['phone']}</div>
              <div style="font-size:10px;color:#94a3b8;">{fc['notes']}</div>
            </div>
            """, unsafe_allow_html=True)

    with c2:
        render_balochistan_map(rt_sel, w_c, road_lookup, sos_list=active_sos_global, facilities_list=facs)

elif nav_choice == "4. Multilingual Alerts":
    st.subheader("3. Multilingual Alerts (Urdu • English • Balochi • Pashto)")
    c1, c2 = st.columns([1.1, 1.4], gap="large")

    with c1:
        al_rt = st.selectbox("Highway Corridor", ROUTES, index=ROUTES.index(selected_corridor))
        al_sec = st.selectbox("Sector / Checkpoint", [p["name"] for p in ROUTES_DATA[al_rt]["points"]])
        al_lang = st.selectbox("Select Language", LANGUAGES)

    with c2:
        w_c = get_corridor_weather(al_rt)
        cur_w = w_c.get(al_sec, {})
        w_en, _, _, _ = weather_info(cur_w.get("weather_code")) if cur_w else ("Clear Sky", "", "", 1)
        r_st = road_lookup.get((al_rt, al_sec), {}).get("status", "Open (Verified)")

        default_txt = generate_multilingual_alert(al_sec, al_rt, w_en, r_st, al_lang)
        msg_txt = st.text_area(f"{al_lang} Warning Message", value=default_txt, height=110)

        box_c = "ltr-box" if al_lang == "English" else "urdu-box"
        st.markdown(f'<div class="{box_c}">{msg_txt}</div>', unsafe_allow_html=True)

        if st.button(f"Send {al_lang} Warning Alert", use_container_width=True):
            if msg_txt.strip():
                run("INSERT INTO alerts(route,language,severity,message,channel,status,created_at) VALUES(?,?,?,?,?,?,?)",
                    (al_rt, al_lang, "Warning", msg_txt.strip(), "SMS & Driver App", "Sent", datetime.now().strftime("%Y-%m-%d %H:%M")))
                st.success(f"Warning sent in {al_lang}!")

elif nav_choice == "5. Journey Risk & Vehicle Registration":
    st.subheader("6. Journey Risk Score & Vehicle Registration")
    c1, c2 = st.columns([1.1, 1.4], gap="large")

    with c1:
        jr_rt = st.selectbox("Evaluate Corridor Risk", ROUTES, index=ROUTES.index(selected_corridor))
        w_c = get_corridor_weather(jr_rt)
        j_sc, j_tr, j_col, j_bg, j_worst = compute_corridor_overall_risk(jr_rt, w_c)
        st.markdown(f"""
        <div style="background:{j_bg};border:2px solid {j_col};border-radius:14px;padding:18px;text-align:center;">
          <div style="font-size:11px;font-weight:700;color:#cbd5e1;">JOURNEY RISK RATING</div>
          <div style="font-size:32px;font-weight:900;color:{j_col};margin:6px 0;">{j_tr}</div>
          <div style="font-size:12px;">Based on live weather & verified road condition at <b>{j_worst}</b></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Checkpoint Arrival Check-In")
        if all_drivers_global:
            d_map = {f"{d['vehicle']} • {d['name']} (Next: {d.get('next_checkpoint')})": d for d in all_drivers_global}
            sel_v = d_map[st.selectbox("Select Vehicle", list(d_map.keys()))]
            if st.button("✅ Confirm Checkpoint Arrival", use_container_width=True):
                pts = ROUTES_DATA[sel_v["route"]]["points"]
                names = [p["name"] for p in pts]
                cur_n = sel_v.get("next_checkpoint") or names[0]
                nxt_n = names[min(names.index(cur_n) + 1, len(names) - 1)] if cur_n in names else names[-1]
                run("UPDATE drivers SET status='Active on Route', current_sector=?, next_checkpoint=?, expected_eta=? WHERE id=?",
                    (cur_n, nxt_n, (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), sel_v["id"]))
                st.success(f"Checked in at {cur_n}! Next checkpoint: {nxt_n}")
                st.rerun()

    with c2:
        st.markdown("#### Register New Vehicle Journey")
        with st.form("reg_veh_form", clear_on_submit=True):
            r1, r2 = st.columns(2)
            dn = r1.text_input("Driver Name")
            dp = r2.text_input("Phone Number", placeholder="0300-1234567")
            r3, r4 = st.columns(2)
            dv = r3.text_input("Vehicle Number", placeholder="QTA-1234")
            dr = r4.selectbox("Route", ROUTES)
            dl = st.selectbox("Preferred Alert Language", LANGUAGES)
            if st.form_submit_button("Register Vehicle", use_container_width=True):
                if dn.strip() and is_valid_pk_phone(dp) and is_valid_plate(dv):
                    pts = ROUTES_DATA[dr]["points"]
                    run(
                        """INSERT INTO drivers(driver_code,name,phone,vehicle,route,language,status,current_sector,next_checkpoint,expected_eta,last_checkin,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (generate_unique_driver_code(), dn.strip(), dp.strip(), dv.strip().upper(), dr, dl,
                         "Active on Route", pts[0]["name"], pts[1]["name"],
                         (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
                         datetime.now().strftime("%Y-%m-%d %H:%M"), datetime.now().strftime("%Y-%m-%d %H:%M"))
                    )
                    st.success("Vehicle registered and active journey tracking started!")
                    st.rerun()
                else:
                    st.error("Please enter valid name, Pakistani mobile number, and vehicle plate.")

        if all_drivers_global:
            df_v = pd.DataFrame(all_drivers_global)[["vehicle", "name", "route", "current_sector", "next_checkpoint", "expected_eta", "status"]]
            df_v.columns = ["Vehicle", "Driver", "Route", "Current Location", "Next Checkpoint", "Expected ETA", "Status"]
            st.dataframe(df_v, use_container_width=True, hide_index=True)
