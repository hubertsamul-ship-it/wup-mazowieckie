"""
WUP Mazowieckie – Aplikacja Analityczna v3
==========================================
Dyrektor WUP widzi od razu: Pulpit z KPI, mapa Polski, mapa Mazowsza,
trend bezrobocia, szybkie filtry – wszystko w jednym miejscu.

Struktura folderów:
    dane/
    ├── zwolnienia/         ← XLSX zwolnień grupowych
    ├── bezrobocie/         ← XLSX MRPiPS-01
    └── stopa_bezrobocia/   ← XLSX GUS Pow_MM_YYYY
    powiaty.geojson         ← granice powiatów mazowieckich
    wojewodztwa.geojson     ← granice województw Polski

Optymalizacja:
    - Konwersja XLSX → Parquet (uruchom raz: python wup_auto_app.py --convert)
    - @st.cache_data na wszystkich wczytaniach
    - Logika danych oddzielona od UI (funkcje w sekcji DATA_LAYER)
"""

import os, re, glob, json, argparse, sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ══════════════════════════════════════════════════════════
# KONFIGURACJA
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Rynek Pracy Mazowsza – WUP Warszawa",
    page_icon="📊", layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MIESIAC_PL = {
    1:"Styczeń",2:"Luty",3:"Marzec",4:"Kwiecień",5:"Maj",6:"Czerwiec",
    7:"Lipiec",8:"Sierpień",9:"Wrzesień",10:"Październik",11:"Listopad",12:"Grudzień"
}
ROMAN = {"I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,
         "VII":7,"VIII":8,"IX":9,"X":10,"XI":11,"XII":12}
PL_NAMES = {
    "styczen":1,"styczeń":1,"luty":2,"marzec":3,"kwiecien":4,"kwiecień":4,
    "maj":5,"czerwiec":6,"lipiec":7,"sierpien":8,"sierpień":8,
    "wrzesien":9,"wrzesień":9,"pazdziernik":10,"październik":10,
    "listopad":11,"grudzien":12,"grudzień":12,
}

# Kolory brandingowe WUP / Mazowsze
C_RED    = "#c0392b"   # główny akcent – czerwień mazowiecka
C_RED2   = "#e74c3c"   # jaśniejszy czerwony
C_NAVY   = "#1a3a5c"   # granat
C_NAVY2  = "#2c5282"   # jaśniejszy granat
C_BLUE   = "#3b82f6"   # niebieski akcent
C_GREEN  = "#16a34a"   # zielony (dobry wynik)
C_ORANGE = "#d97706"   # pomarańczowy
C_BG     = "#f8fafc"   # tło główne (prawie biały)
C_CARD   = "#ffffff"   # karty

# ══════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Inter', system-ui, sans-serif !important; }

/* ── Tło ── */
.stApp { background: #f8fafc !important; }
.main .block-container { background: #f8fafc !important; padding: 1.2rem 1.8rem 3rem !important; max-width: 100% !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background: #1a3a5c !important; border-right: none !important; }
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 { color: #f1f5f9 !important; font-weight: 700 !important; font-size: 0.7rem !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }
[data-testid="stSidebar"] .stButton button { background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.15) !important; color: #e2e8f0 !important; border-radius: 8px !important; font-size: 0.8rem !important; font-weight: 500 !important; width: 100% !important; transition: all 0.15s !important; }
[data-testid="stSidebar"] .stButton button:hover { background: rgba(255,255,255,0.15) !important; color: #fff !important; }
[data-testid="stSidebar"] .stTextInput input { background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.15) !important; border-radius: 7px !important; color: #e2e8f0 !important; font-size: 0.78rem !important; }
[data-testid="stSidebar"] label { color: #94a3b8 !important; font-size: 0.68rem !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; font-weight: 600 !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.1) !important; margin: 8px 0 !important; }
[data-testid="stSidebar"] .stSuccess { background: rgba(22,163,74,0.15) !important; border: 1px solid rgba(22,163,74,0.3) !important; border-radius: 7px !important; font-size: 0.75rem !important; }
[data-testid="stSidebar"] .stWarning { background: rgba(217,119,6,0.15) !important; border: 1px solid rgba(217,119,6,0.3) !important; border-radius: 7px !important; }
[data-testid="stSidebar"] small, [data-testid="stSidebar"] .stCaption { color: #64748b !important; font-size: 0.7rem !important; }

/* ── Metryki ── */
[data-testid="stMetric"] { background: #fff; border-radius: 12px; padding: 16px 18px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04); border: 1px solid #e2e8f0; }
[data-testid="stMetric"] label { color: #64748b !important; font-size: 0.68rem !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.07em !important; }
[data-testid="stMetricValue"] { color: #0f172a !important; font-size: 1.65rem !important; font-weight: 800 !important; font-family: 'JetBrains Mono', monospace !important; }
[data-testid="stMetricDelta"] { font-size: 0.78rem !important; }

/* ── Zakładki ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] { background: #fff; border-radius: 10px; padding: 4px; gap: 2px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid #e2e8f0; margin-bottom: 16px; }
[data-testid="stTabs"] [data-baseweb="tab"] { border-radius: 7px !important; font-weight: 500 !important; font-size: 0.8rem !important; color: #64748b !important; padding: 7px 14px !important; transition: all 0.15s !important; }
[data-testid="stTabs"] [aria-selected="true"] { background: #1a3a5c !important; color: #fff !important; font-weight: 600 !important; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"], [data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }

/* ── DataFrame ── */
[data-testid="stDataFrame"] { border-radius: 10px !important; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid #e2e8f0 !important; }

/* ── Download button ── */
.stDownloadButton button { background: #fff !important; border: 1.5px solid #1a3a5c !important; color: #1a3a5c !important; border-radius: 7px !important; font-weight: 600 !important; font-size: 0.8rem !important; }
.stDownloadButton button:hover { background: #1a3a5c !important; color: #fff !important; }

/* ── Multiselect tags ── */
[data-baseweb="tag"] { background: #dbeafe !important; color: #1e40af !important; border-radius: 5px !important; font-size: 0.73rem !important; }

/* ── Nagłówki ── */
h1 { color: #0f172a !important; font-weight: 800 !important; letter-spacing: -0.02em; }
h2, h3 { color: #0f172a !important; font-weight: 700 !important; }

/* ── Info/Success/Warning ── */
.stInfo { background: #eff6ff !important; border: 1px solid #bfdbfe !important; border-radius: 9px !important; }
.stSuccess { background: #f0fdf4 !important; border: 1px solid #bbf7d0 !important; border-radius: 9px !important; }
.stWarning { background: #fffbeb !important; border: 1px solid #fde68a !important; border-radius: 9px !important; }

/* ── Divider ── */
hr { border-color: #e2e8f0 !important; margin: 14px 0 !important; }

/* ── Selectbox, radio ── */
[data-testid="stSelectbox"] > div > div { border-radius: 8px !important; border-color: #e2e8f0 !important; background: #fff !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }

/* ── Hero header ── */
.wup-header { background: linear-gradient(135deg, #1a3a5c 0%, #2c5282 60%, #c0392b 100%); border-radius: 14px; padding: 20px 28px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
.wup-header h1 { color: #fff !important; font-size: 1.4rem !important; margin: 0 !important; }
.wup-header p { color: rgba(255,255,255,0.7) !important; font-size: 0.8rem !important; margin: 4px 0 0 0 !important; }
.wup-badge { background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25); border-radius: 20px; padding: 6px 14px; font-size: 0.73rem; color: #fff; font-weight: 600; }

/* ── KPI strip na górze ── */
.kpi-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card { background: #fff; border-radius: 12px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04); border: 1px solid #e2e8f0; border-top: 3px solid #1a3a5c; }
.kpi-card.red-top  { border-top-color: #c0392b; }
.kpi-card.green-top{ border-top-color: #16a34a; }
.kpi-card.blue-top { border-top-color: #3b82f6; }
.kpi-lbl { font-size: 0.62rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin-bottom: 4px; }
.kpi-loc { font-size: 0.68rem; color: #94a3b8; font-weight: 500; margin-bottom: 6px; }
.kpi-val { font-size: 1.8rem; font-weight: 800; color: #0f172a; font-family: 'JetBrains Mono', monospace; letter-spacing: -0.02em; line-height: 1; }
.kpi-unit { font-size: 0.8rem; color: #64748b; font-weight: 500; margin-left: 3px; }
.kpi-delta { font-size: 0.68rem; margin-top: 6px; }
.delta-up   { color: #dc2626; } .delta-down { color: #16a34a; } .delta-eq { color: #94a3b8; }

/* ── Section label ── */
.sec-label { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #94a3b8; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
.sec-label::before { content: ''; display: block; width: 12px; height: 2px; background: #c0392b; border-radius: 1px; }

/* ── Mobile ── */
@media (max-width: 768px) {
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
  .main .block-container { padding: 0.8rem !important; }
  .kpi-val { font-size: 1.4rem; }
  .wup-header h1 { font-size: 1.1rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# DATA LAYER – logika wczytywania (oddzielona od UI)
# ══════════════════════════════════════════════════════════

PKD_OPISY = {
    "6419Z":"Usługi kredytowe","6499Z":"Inne usługi finansowe",
    "6619Z":"Wspomaganie finansów","6622Z":"Agenci ubezpieczeniowi",
    "6110Z":"Telekomunikacja przewodowa","6120Z":"Telekomunikacja bezprzewodowa",
    "6190Z":"Pozostała telekomunikacja","6201Z":"Oprogramowanie",
    "6202Z":"Doradztwo IT","6209Z":"Inne usługi IT",
    "6311Z":"Przetwarzanie danych","6312Z":"Portale internetowe",
    "4711Z":"Handel detaliczny","4719Z":"Handel detaliczny (inne)",
    "4920Z":"Transport kolejowy towarów","5310Z":"Poczta",
    "5320Z":"Usługi kurierskie","2042Z":"Chemia gospodarcza",
    "2222Z":"Opakowania z tworzyw","2351Z":"Produkcja cementu",
    "2910B":"Produkcja pojazdów","7311Z":"Agencje reklamowe",
    "7021Z":"Public relations","8220Z":"Call center",
    "9200Z":"Gry losowe i zakłady",
}

def normalizuj_pkd(pkd):
    return re.sub(r'[.\s]', '', str(pkd).strip()).upper()

def parsuj_nazwe(nazwa):
    m = re.match(r'^(\d{4})[-_.](\d{1,2})$', nazwa)
    if m: return int(m.group(1)), int(m.group(2))
    m = re.match(r'^(\d{1,2})[-_.](\d{4})$', nazwa)
    if m: return int(m.group(2)), int(m.group(1))
    m = re.match(r'^(X{0,3}(?:IX|IV|V?I{0,3}))[-_.](\d{4})$', nazwa, re.IGNORECASE)
    if m and m.group(1).upper() in ROMAN: return int(m.group(2)), ROMAN[m.group(1).upper()]
    m = re.match(r'^([a-ząćęłńóśźż]+)[-_.](\d{4})$', nazwa, re.IGNORECASE)
    if m and m.group(1).lower() in PL_NAMES: return int(m.group(2)), PL_NAMES[m.group(1).lower()]
    return None

def znajdz_pliki(folder):
    wyniki = []
    wszystkie = glob.glob(os.path.join(folder,"*.xlsx")) + glob.glob(os.path.join(folder,"*.xls"))
    seen = set()
    for s in wszystkie:
        if s.lower() not in seen:
            seen.add(s.lower())
            nazwa = os.path.splitext(os.path.basename(s))[0]
            parsed = parsuj_nazwe(nazwa)
            if parsed:
                r,m = parsed
                if 1<=m<=12 and 2000<=r<=2100:
                    wyniki.append({"sciezka":s,"rok":r,"miesiac":m,
                                   "nazwa_pl":f"{MIESIAC_PL[m]} {r}",
                                   "sort_key":r*100+m})
    return sorted(wyniki, key=lambda x: x["sort_key"])

def _parquet_path(xlsx_path):
    d = os.path.join(os.path.dirname(xlsx_path), "__cache__")
    os.makedirs(d, exist_ok=True)
    base = os.path.splitext(os.path.basename(xlsx_path))[0]
    return os.path.join(d, base+".parquet")

def _load_excel_or_parquet(path, **kwargs):
    """Wczytuje z parquet jeśli istnieje i jest nowszy, inaczej z xlsx i zapisuje parquet."""
    pq = _parquet_path(path)
    if os.path.exists(pq) and os.path.getmtime(pq) >= os.path.getmtime(path):
        try: return pd.read_parquet(pq)
        except Exception: pass
    try:
        df = pd.read_excel(path, **kwargs)
        try: df.to_parquet(pq, index=False)
        except Exception: pass
        return df
    except Exception:
        return pd.DataFrame()

GUS_DO_GEO = {
    "białobrzeski":"powiat białobrzeski","ciechanowski":"powiat ciechanowski",
    "garwoliński":"powiat garwoliński","gostyniński":"powiat gostyniński",
    "grodziski":"powiat grodziski","grójecki":"powiat grójecki",
    "kozienicki":"powiat kozienicki","legionowski":"powiat legionowski",
    "lipski":"powiat lipski","łosicki":"powiat łosicki",
    "makowski":"powiat makowski","miński":"powiat miński",
    "mławski":"powiat mławski","nowodworski":"powiat nowodworski",
    "ostrołęcki":"powiat ostrołęcki","ostrowski":"powiat ostrowski",
    "otwocki":"powiat otwocki","piaseczyński":"powiat piaseczyński",
    "płocki":"powiat płocki","płoński":"powiat płoński",
    "pruszkowski":"powiat pruszkowski","przasnyski":"powiat przasnyski",
    "przysuski":"powiat przysuski","pułtuski":"powiat pułtuski",
    "radomski":"powiat radomski","siedlecki":"powiat siedlecki",
    "sierpecki":"powiat sierpecki","sochaczewski":"powiat sochaczewski",
    "sokołowski":"powiat sokołowski","szydłowiecki":"powiat szydłowiecki",
    "warszawski zachodni":"powiat warszawski zachodni",
    "węgrowski":"powiat węgrowski","wołomiński":"powiat wołomiński",
    "wyszkowski":"powiat wyszkowski","zwoleński":"powiat zwoleński",
    "żuromiński":"powiat żuromiński","żyrardowski":"powiat żyrardowski",
    "m. ostrołęka":"powiat Ostrołęka","m. płock":"powiat Płock",
    "m. radom":"powiat Radom","m. siedlce":"powiat Siedlce",
    "m. warszawa":"powiat Warszawa","warszawa":"powiat Warszawa",
}

NUTS2_DO_GEO = {
    "PL21":"małopolskie","PL22":"śląskie","PL41":"wielkopolskie",
    "PL42":"zachodniopomorskie","PL43":"lubuskie","PL51":"dolnośląskie",
    "PL52":"opolskie","PL61":"kujawsko-pomorskie","PL62":"warmińsko-mazurskie",
    "PL63":"pomorskie","PL71":"łódzkie","PL72":"świętokrzyskie",
    "PL81":"lubelskie","PL82":"podkarpackie","PL84":"podlaskie",
    "PL9":"mazowieckie","PL91":"mazowieckie","PL92":"mazowieckie",
}

@st.cache_data(show_spinner=False)
def wczytaj_geojson(sciezka):
    try:
        with open(sciezka,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception: return {}

@st.cache_data(show_spinner=False)
def wczytaj_zwolnienia(folder):
    pliki = znajdz_pliki(folder)
    records = []
    for p in pliki:
        try:
            try: xl = pd.read_excel(p["sciezka"], sheet_name="dane", header=None)
            except Exception: xl = pd.read_excel(p["sciezka"], header=None)
            for i in range(7, len(xl)):
                vals = list(xl.iloc[i])
                powiat = vals[1] if len(vals)>1 else None
                if not isinstance(powiat,str) or len(powiat.strip())<2: continue
                if any(x in powiat.lower() for x in ["powiat","suma","ogółem","razem"]): continue
                def g(idx):
                    v = vals[idx] if idx<len(vals) else None
                    return None if (v is None or (isinstance(v,float) and np.isnan(v))) else v
                pkd_raw = str(g(5) or "").strip()
                pkd = normalizuj_pkd(pkd_raw)
                records.append({
                    "Okres":p["nazwa_pl"],"Rok":p["rok"],"Miesiąc_num":p["miesiac"],
                    "Sort_key":p["sort_key"],"Powiat":str(g(1) or "").strip(),
                    "Nazwa":re.sub(r"\s{2,}"," ",str(g(3) or "").strip())[:70],
                    "PKD":pkd,"PKD_opis":PKD_OPISY.get(pkd,pkd_raw[:30]),
                    "Zgłoszeni":pd.to_numeric(g(6),errors="coerce") or 0,
                    "Wypow_zmieniające":pd.to_numeric(g(7),errors="coerce") or 0,
                    "Zwolnieni":pd.to_numeric(g(8),errors="coerce") or 0,
                    "Monitorowani":pd.to_numeric(g(9),errors="coerce") or 0,
                })
        except Exception: continue
    df = pd.DataFrame(records)
    if not df.empty:
        kolejnosc = list(dict.fromkeys([p["nazwa_pl"] for p in pliki]))
        df["Okres"] = pd.Categorical(df["Okres"],categories=kolejnosc,ordered=True)
        df = df.sort_values("Sort_key")
    return df, pliki

@st.cache_data(show_spinner=False)
def wczytaj_bezrobocie(folder):
    """
    Wczytuje pliki MRPiPS-01.
    Województwo ogółem: arkusz 'WOJEWÓDZTWO OGÓŁEM', row 15, col 12=stan_koniec, col 13=kobiety
    Powiaty: arkusz 'dbf', TABELA=1, NRW=001, ostatni blok per WGM: R1=stan_koniec, R2=kobiety
    Kategorie: NRW=005(wsi), 008(cudzoziemcy), 009(bez_kwalif), 013(do30), 016(pow50), 017(dlugotrwale)
    """
    WGM_MAP = {
        1402:("Białobrzeski","powiat"),   1403:("Ciechanowski","powiat"),
        1404:("Garwoliński","powiat"),    1405:("Gostyniński","powiat"),
        1406:("Grodziski","powiat"),      1407:("Grójecki","powiat"),
        1408:("Kozienicki","powiat"),     1409:("Legionowski","powiat"),
        1410:("Lipski","powiat"),         1411:("Łosicki","powiat"),
        1412:("Makowski","powiat"),       1413:("Miński","powiat"),
        1414:("Mławski","powiat"),        1415:("Nowodworski","powiat"),
        1416:("Ostrołęcki","powiat"),     1417:("Ostrowski","powiat"),
        1418:("Otwocki","powiat"),        1419:("Piaseczyński","powiat"),
        1420:("Płocki","powiat"),         1421:("Płoński","powiat"),
        1422:("Pruszkowski","powiat"),    1423:("Przasnyski","powiat"),
        1424:("Przysuski","powiat"),      1425:("Pułtuski","powiat"),
        1426:("Radomski","powiat"),       1427:("Siedlecki","powiat"),
        1428:("Sierpecki","powiat"),      1429:("Sochaczewski","powiat"),
        1430:("Sokołowski","powiat"),     1432:("Szydłowiecki","powiat"),
        1433:("Warszawski Zachodni","powiat"), 1434:("Węgrowski","powiat"),
        1435:("Wołomiński","powiat"),     1436:("Wyszkowski","powiat"),
        1437:("Zwoleński","powiat"),      1438:("Żuromiński","powiat"),
        1461:("m. Ostrołęka","powiat"),   1462:("m. Płock","powiat"),
        1463:("m. Radom","powiat"),       1464:("m. Siedlce","powiat"),
        1465:("m. Warszawa","powiat"),
    }
    NRW_KAT = {
        "005":"Na_wsi", "008":"Cudzoziemcy", "009":"Bez_kwalif",
        "013":"Do_30_lat", "014":"Do_25_lat",
        "016":"Pow_50_lat", "017":"Dlugoterwale", "018":"Niepelnosprawni",
    }

    pliki = znajdz_pliki(folder)
    records = []

    for p in pliki:
        try:
            xl = pd.ExcelFile(p["sciezka"])
            if "dbf" not in xl.sheet_names:
                continue
            df = xl.parse("dbf", header=0)
            df["NRW"] = df["NRW"].astype(str).str.strip().str.zfill(3)
            df["WGM"] = df["WGM"].astype(int)

            # ── 1. Województwo ogółem z arkusza WOJEWÓDZTWO OGÓŁEM ──
            if "WOJEWÓDZTWO OGÓŁEM" in xl.sheet_names:
                try:
                    df_w = xl.parse("WOJEWÓDZTWO OGÓŁEM", header=None)
                    r = list(df_w.iloc[15])  # Ogółem wiersz
                    def gc(idx):
                        v = r[idx] if idx < len(r) else None
                        return pd.to_numeric(v, errors="coerce")
                    # Zarejestrowani=col8, Wyrej=col10, Stan_koniec=col12, Stan_K=col13
                    zarej_w       = gc(8)
                    wyr_w         = gc(10)
                    stan_koniec_w = gc(12)
                    stan_K_w      = gc(13)
                    z_zasilkiem_w = gc(14)

                    # Kategorie z kolejnych wierszy (col 12 = stan_koniec)
                    def kat_woj(row_idx):
                        try:
                            return pd.to_numeric(list(df_w.iloc[row_idx])[12], errors="coerce")
                        except: return None

                    rec_w = {
                        "Okres":p["nazwa_pl"],"Rok":p["rok"],
                        "Miesiąc_num":p["miesiac"],"Sort_key":p["sort_key"],
                        "Region":"Mazowieckie","Typ":"województwo",
                        "Zarejestrowani":zarej_w,"Wyrejestrowani":wyr_w,
                        "Stan_koniec":stan_koniec_w,"Stan_koniec_K":stan_K_w,
                        "Z_zasilkiem":z_zasilkiem_w,
                        "Na_wsi":     kat_woj(20),
                        "Cudzoziemcy":kat_woj(23),
                        "Bez_kwalif": kat_woj(24),
                        "Do_30_lat":  kat_woj(28),
                        "Do_25_lat":  kat_woj(29),
                        "Pow_50_lat": kat_woj(31),
                        "Dlugoterwale":kat_woj(32),
                        "Niepelnosprawni":kat_woj(33),
                    }
                    records.append(rec_w)
                except Exception:
                    pass

            # ── 2. Powiaty z arkusza dbf ──
            for wgm, (nazwa, typ) in WGM_MAP.items():
                sub = df[(df["WGM"]==wgm) & (df["TABELA"]==1) & (df["NRW"]=="001")]
                if sub.empty:
                    continue
                # Ostatni blok NRW=001: R1=stan_koniec_ogół, R2=stan_K
                r_last = sub.iloc[-1]
                stan_koniec = pd.to_numeric(r_last.get("R1"), errors="coerce")
                stan_K      = pd.to_numeric(r_last.get("R2"), errors="coerce")
                # Pierwszy blok: R1=zarej, R5=wyrej (z zasiłkiem)
                r_first = sub.iloc[0]
                zarej       = pd.to_numeric(r_first.get("R1"), errors="coerce")
                z_zasilkiem = pd.to_numeric(r_first.get("R5"), errors="coerce")

                # Kategorie (NRW=005 itp.) - kolumna R5 = stan_koniec w kategorii
                sub_all = df[(df["WGM"]==wgm) & (df["TABELA"]==1)]
                rec = {
                    "Okres":p["nazwa_pl"],"Rok":p["rok"],
                    "Miesiąc_num":p["miesiac"],"Sort_key":p["sort_key"],
                    "Region":nazwa,"Typ":typ,
                    "Zarejestrowani":zarej,"Stan_koniec":stan_koniec,
                    "Stan_koniec_K":stan_K,"Z_zasilkiem":z_zasilkiem,
                }
                for nrw, col in NRW_KAT.items():
                    rows_nrw = sub_all[sub_all["NRW"]==nrw]
                    if not rows_nrw.empty:
                        rec[col] = pd.to_numeric(rows_nrw.iloc[0].get("R5"), errors="coerce")

                records.append(rec)

        except Exception:
            continue

    df_out = pd.DataFrame(records)
    if not df_out.empty:
        kolejnosc = list(dict.fromkeys([p["nazwa_pl"] for p in pliki]))
        df_out["Okres"] = pd.Categorical(df_out["Okres"], categories=kolejnosc, ordered=True)
        df_out = df_out.sort_values(["Sort_key","Typ"], ascending=[True,False])
    return df_out

@st.cache_data(show_spinner=False)
def wczytaj_stopa_bezrobocia(folder):
    pliki = znajdz_pliki(folder)
    records = []
    for p in pliki:
        try:
            xl = pd.ExcelFile(p["sciezka"])
            if "Tabl.1" in xl.sheet_names:
                df = xl.parse("Tabl.1", header=None)
                for i in range(len(df)):
                    kod = str(df.iloc[i,0]).strip()
                    if not kod.startswith("PL"): continue
                    nazwa = str(df.iloc[i,4]).strip()
                    bezrob = pd.to_numeric(df.iloc[i,5],errors="coerce")
                    stopa  = pd.to_numeric(df.iloc[i,6],errors="coerce")
                    if np.isnan(stopa): continue
                    if len(kod)==4: typ="województwo"; geo=NUTS2_DO_GEO.get(kod)
                    elif kod in ("PL9","PL91","PL92"): typ="województwo"; geo="mazowieckie"
                    else: continue
                    records.append({
                        "Okres":p["nazwa_pl"],"Rok":p["rok"],"Miesiąc_num":p["miesiac"],
                        "Sort_key":p["sort_key"],"Kod":kod,
                        "Nazwa":nazwa.replace("REGION: ","").replace("PODREGION: ","").strip().title(),
                        "Typ":typ,"Bezrobotni_tys":bezrob,"Stopa":stopa,"Geo_nazwa":geo,
                    })
            if "Tabl.1a" in xl.sheet_names:
                df = xl.parse("Tabl.1a", header=None)
                for i in range(len(df)):
                    woj = str(df.iloc[i,0]).strip()
                    if woj!="14": continue
                    pow_kod = str(df.iloc[i,1]).strip()
                    nazwa   = str(df.iloc[i,2]).strip().lower().strip()
                    bezrob  = pd.to_numeric(df.iloc[i,3],errors="coerce")
                    stopa   = pd.to_numeric(df.iloc[i,4],errors="coerce")
                    if np.isnan(stopa): continue
                    typ = "województwo" if pow_kod=="00" else "powiat"
                    geo = GUS_DO_GEO.get(nazwa)
                    records.append({
                        "Okres":p["nazwa_pl"],"Rok":p["rok"],"Miesiąc_num":p["miesiac"],
                        "Sort_key":p["sort_key"],"Kod":f"14{pow_kod}",
                        "Nazwa":nazwa.title(),"Typ":typ,
                        "Bezrobotni_tys":bezrob,"Stopa":stopa,"Geo_nazwa":geo,
                    })
        except Exception: continue
    df = pd.DataFrame(records)
    if not df.empty:
        kolejnosc = list(dict.fromkeys([p["nazwa_pl"] for p in pliki]))
        df["Okres"] = pd.Categorical(df["Okres"],categories=kolejnosc,ordered=True)
        df = df.sort_values("Sort_key")
    return df

# ══════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════

def kpi_html(label, location, value, unit, delta=None, delta_type="eq", color="blue"):
    color_map = {"red":"red-top","green":"green-top","blue":"blue-top"}
    cls = color_map.get(color,"")
    delta_cls = {"up":"delta-up","down":"delta-down","eq":"delta-eq"}.get(delta_type,"delta-eq")
    delta_html = f'<div class="kpi-delta {delta_cls}">{delta}</div>' if delta else ""
    return f"""<div class="kpi-card {cls}">
      <div class="kpi-lbl">{label}</div>
      <div class="kpi-loc">{location}</div>
      <div><span class="kpi-val">{value}</span><span class="kpi-unit">{unit}</span></div>
      {delta_html}
    </div>"""

def rysuj_mape(df_mapa, geojson_data, tytul, zoom, center, height=520,
               color_scale="RdYlGn_r", col="Stopa"):
    if not geojson_data:
        st.warning("⚠️ Brak pliku GeoJSON")
        return
    geo_map = {f["properties"]["nazwa"]: f["properties"]["id"]
               for f in geojson_data["features"]}
    df_mapa = df_mapa.copy()
    df_mapa["geo_id"] = df_mapa["Geo_nazwa"].map(geo_map)
    df_plot = df_mapa.dropna(subset=["geo_id"])
    if df_plot.empty:
        st.warning("Brak dopasowanych danych")
        return
    fig = px.choropleth_mapbox(
        df_plot, geojson=geojson_data, locations="geo_id",
        featureidkey="properties.id", color=col,
        hover_name="Nazwa",
        hover_data={col:":.1f","Bezrobotni_tys":":.1f","geo_id":False},
        color_continuous_scale=color_scale,
        range_color=[df_plot[col].min(), df_plot[col].max()],
        mapbox_style="carto-positron",
        zoom=zoom, center=center, opacity=0.82, height=height,
        labels={col:"Stopa %","Bezrobotni_tys":"Bezrobotni (tys.)"},
    )
    fig.update_layout(
        margin={"r":0,"t":36,"l":0,"b":0},
        title=dict(text=tytul, font=dict(size=13,color="#0f172a"), x=0),
        coloraxis_colorbar=dict(title="Stopa %",thickness=10,len=0.7,tickfont=dict(size=10)),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
    )
    st.plotly_chart(fig, use_container_width=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
    font=dict(family="Inter, system-ui", size=11, color="#475569"),
    hovermode="x unified",
    xaxis=dict(showgrid=False, tickangle=-30, tickfont=dict(size=10,color="#94a3b8")),
)
LEGEND_H = dict(orientation="h", y=-0.25, font=dict(size=10))  # domyślna legenda pozioma

# ══════════════════════════════════════════════════════════
# SIDEBAR – dane + nawigacja
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 4px 12px;border-bottom:1px solid rgba(255,255,255,0.1);margin-bottom:12px;">
      <div style="font-size:0.6rem;font-weight:700;letter-spacing:0.15em;color:#93c5fd;text-transform:uppercase;">WUP Warszawa</div>
      <div style="font-size:1rem;font-weight:800;color:#fff;margin-top:2px;">Rynek Pracy Mazowsza</div>
      <div style="font-size:0.65rem;color:#64748b;margin-top:2px;">Obserwatorium Rynku Pracy</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("⚙️ Foldery danych", expanded=False):
        folder_zwol  = st.text_input("Zwolnienia", value=os.path.join(BASE_DIR,"dane","zwolnienia"))
        folder_bezr  = st.text_input("Bezrobocie MRPiPS", value=os.path.join(BASE_DIR,"dane","bezrobocie"))
        folder_stopa = st.text_input("Stopa bezrobocia", value=os.path.join(BASE_DIR,"dane","stopa_bezrobocia"))

    folder_zwol  = os.path.join(BASE_DIR,"dane","zwolnienia")
    folder_bezr  = os.path.join(BASE_DIR,"dane","bezrobocie")
    folder_stopa = os.path.join(BASE_DIR,"dane","stopa_bezrobocia")

    if st.button("🔄 Odśwież dane", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Wczytaj dane
    df_zwol = pd.DataFrame(); pliki_zwol = []
    df_bezr = pd.DataFrame(); df_stopa = pd.DataFrame()
    geojson = {}; geojson_woj = {}

    # Preferuj powiaty_maz.geojson (tylko mazowieckie, poprawne grodziski/ostrowski)
    geojson_sciezka = os.path.join(BASE_DIR,"powiaty_maz.geojson")
    if not os.path.exists(geojson_sciezka):
        geojson_sciezka = os.path.join(BASE_DIR,"powiaty.geojson")
    geojson_woj_sciezka = os.path.join(BASE_DIR,"wojewodztwa.geojson")

    if os.path.exists(folder_zwol):
        df_zwol, pliki_zwol = wczytaj_zwolnienia(folder_zwol)
    if os.path.exists(folder_bezr):
        df_bezr = wczytaj_bezrobocie(folder_bezr)
    if os.path.exists(folder_stopa):
        df_stopa = wczytaj_stopa_bezrobocia(folder_stopa)
    if os.path.exists(geojson_sciezka):
        geojson = wczytaj_geojson(geojson_sciezka)
    if os.path.exists(geojson_woj_sciezka):
        geojson_woj = wczytaj_geojson(geojson_woj_sciezka)

    st.divider()
    st.markdown("**📊 Nawigacja**")

    nav_items = {
        "🏠 Pulpit":        "pulpit",
        "👥 Bezrobotni":    "bezrobotni",
        "📉 Stopa bezrob.": "stopa",
        "🏭 Zwolnienia":    "zwolnienia",
        "📋 Dane surowe":   "dane",
    }
    if "nav" not in st.session_state:
        st.session_state["nav"] = "pulpit"
    for label, key in nav_items.items():
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state["nav"] = key
            st.rerun()

    st.divider()
    # Status
    if pliki_zwol: st.caption(f"✅ Zwolnienia: {len(pliki_zwol)} mies.")
    if not df_bezr.empty:
        n = df_bezr[["Rok","Miesiąc_num"]].drop_duplicates().shape[0]
        st.caption(f"✅ Bezrobocie: {n} mies.")
    if not df_stopa.empty:
        n = df_stopa[["Rok","Miesiąc_num"]].drop_duplicates().shape[0]
        st.caption(f"✅ Stopa bezr.: {n} mies.")

current_page = st.session_state.get("nav","pulpit")

# Filtrowanie zwolnień (globalne)
dff = df_zwol.copy() if not df_zwol.empty else pd.DataFrame()

# ══════════════════════════════════════════════════════════
# PULPIT
# ══════════════════════════════════════════════════════════
if current_page == "pulpit":
    # Header
    last_date = ""
    if not df_stopa.empty:
        last_date = str(df_stopa.sort_values("Sort_key")["Okres"].iloc[-1])
    elif not df_bezr.empty:
        last_date = str(df_bezr.sort_values("Sort_key")["Okres"].iloc[-1])

    st.markdown(f"""
    <div class="wup-header">
      <div>
        <h1>📊 Rynek Pracy Mazowsza</h1>
        <p>Województwo Mazowieckie · Obserwatorium Rynku Pracy WUP Warszawa</p>
      </div>
      <div class="wup-badge">📅 {last_date or "brak danych"}</div>
    </div>
    """, unsafe_allow_html=True)

    # KPI cards
    kpis = []
    ostatnia_stopa_maz = ostatni_bezr_maz = None
    ostatnia_stopa_wawa = ostatni_bezr_wawa = None

    if not df_stopa.empty:
        woj_s = df_stopa[df_stopa["Typ"]=="województwo"].sort_values("Sort_key")
        pow_s = df_stopa[df_stopa["Typ"]=="powiat"].sort_values("Sort_key")
        if not woj_s.empty:
            ost = woj_s.iloc[-1]
            ostatnia_stopa_maz = ost["Stopa"]
            ostatni_bezr_maz   = ost["Bezrobotni_tys"]
        if not pow_s.empty:
            wawa = pow_s[pow_s["Nazwa"].str.lower().str.contains("warszawa")]
            if not wawa.empty:
                ow = wawa.iloc[-1]
                ostatnia_stopa_wawa = ow["Stopa"]
                ostatni_bezr_wawa   = ow["Bezrobotni_tys"]

    # KPI – natywne st.metric (działa zawsze niezależnie od wersji Streamlit)
    val_bezr      = f"{ostatni_bezr_maz:.1f} tys."   if ostatni_bezr_maz      else "—"
    val_stopa_maz = f"{ostatnia_stopa_maz:.1f} %"    if ostatnia_stopa_maz    else "—"
    val_bezr_wawa = f"{ostatni_bezr_wawa:.1f} tys."  if ostatni_bezr_wawa     else "—"
    val_stopa_wawa= f"{ostatnia_stopa_wawa:.1f} %"   if ostatnia_stopa_wawa   else "—"

    # Oblicz delty jeśli są dane z poprzedniego miesiąca
    def delta_stopa(df, typ, nazwa_contains=None):
        """Liczy zmianę stopy m/m dla konkretnej jednostki (nie średniej!)."""
        WYKLUCZ = ["PL9","PL91","PL92"]
        d = df[
            (df["Typ"]==typ) &
            (~df["Kod"].astype(str).isin(WYKLUCZ))
        ].sort_values("Sort_key")
        if nazwa_contains:
            d = d[d["Nazwa"].str.lower().str.contains(nazwa_contains, na=False)]
        if d.empty:
            return None
        # Bierzemy tylko jeden rekord na miesiąc (unikamy duplikatów)
        d = d.drop_duplicates(subset=["Sort_key"], keep="last")
        if len(d) < 2:
            return None
        v_now  = float(d.iloc[-1]["Stopa"])
        v_prev = float(d.iloc[-2]["Stopa"])
        diff = round(v_now - v_prev, 2)
        return f"{diff:+.2f} pp"

    # Delta bezrobotni m/m
    def delta_bezr(df_b, typ, nazwa=None):
        if df_b is None or df_b.empty: return None
        d = df_b[df_b["Typ"]==typ].sort_values("Sort_key")
        if nazwa: d = d[d["Region"].str.lower().str.contains(nazwa, na=False)]
        d = d.drop_duplicates(subset=["Sort_key"], keep="last")
        if len(d) < 2: return None
        v_now  = float(d.iloc[-1]["Stan_koniec"])
        v_prev = float(d.iloc[-2]["Stan_koniec"])
        diff = int(round(v_now - v_prev))
        return f"{diff:+,}"

    delta_stopa_maz = delta_stopa(df_stopa, "województwo") if not df_stopa.empty else None
    delta_bezr_maz  = delta_bezr(df_bezr, "województwo") if not df_bezr.empty else None
    delta_stopa_waw = delta_stopa(df_stopa, "powiat", "warszawa") if not df_stopa.empty else None
    delta_bezr_waw  = delta_bezr(df_bezr, "powiat", "warszawa") if not df_bezr.empty else None

    kc1, kc2, kc3, kc4 = st.columns(4)
    with kc1:
        st.metric("👥 Bezrobotni – Mazowieckie", val_bezr,
                  delta=delta_bezr_maz, delta_color="inverse")
    with kc2:
        st.metric("📉 Stopa bezrobocia – Mazowieckie", val_stopa_maz,
                  delta=delta_stopa_maz, delta_color="inverse")
    with kc3:
        st.metric("👥 Bezrobotni – m. Warszawa", val_bezr_wawa,
                  delta=delta_bezr_waw, delta_color="inverse")
    with kc4:
        st.metric("📉 Stopa bezrobocia – m. Warszawa", val_stopa_wawa,
                  delta=delta_stopa_waw, delta_color="inverse")

    # Mapy
    if not df_stopa.empty:
        ostatni_key = df_stopa["Sort_key"].max()
        okres_str = str(df_stopa[df_stopa["Sort_key"]==ostatni_key]["Okres"].iloc[0])
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="sec-label">Mapa Polski – stopa bezrobocia wg województw</div>', unsafe_allow_html=True)
            woj_m = df_stopa[(df_stopa["Typ"]=="województwo") & (df_stopa["Sort_key"]==ostatni_key) & df_stopa["Geo_nazwa"].notna()].drop_duplicates("Geo_nazwa")
            rysuj_mape(woj_m, geojson_woj, f"Polska · {okres_str}",
                       zoom=4.6, center={"lat":52.1,"lon":19.4}, height=540)

        with col2:
            st.markdown('<div class="sec-label">Mapa Mazowiecka – stopa bezrobocia wg powiatów</div>', unsafe_allow_html=True)
            pow_m = df_stopa[(df_stopa["Typ"]=="powiat") & (df_stopa["Sort_key"]==ostatni_key)]
            rysuj_mape(pow_m, geojson, f"Mazowieckie · {okres_str}",
                       zoom=6.4, center={"lat":52.1,"lon":21.0}, height=540)
    else:
        st.info("ℹ️ Dodaj pliki GUS do folderu `stopa_bezrobocia/` aby zobaczyć mapy")

    # Trend – wykres liniowy województw (pełna szerokość)
    if not df_stopa.empty:
        WYKLUCZ_MAZ2 = ["PL9","PL91","PL92"]
        woj_trend_all = df_stopa[
            (df_stopa["Typ"]=="województwo") &
            (~df_stopa["Kod"].astype(str).isin(WYKLUCZ_MAZ2))
        ].sort_values("Sort_key")

        st.markdown('<div class="sec-label">Stopa bezrobocia – województwa</div>', unsafe_allow_html=True)
        col_ctrl1, col_ctrl2 = st.columns([4,1])
        with col_ctrl2:
            miara_p = st.radio("Wskaźnik",["Stopa (%)","Bezrobotni (tys.)"],key="pulpit_miara")
        col_field_p = "Stopa" if "Stopa" in miara_p else "Bezrobotni_tys"
        col_label_p = "Stopa %" if "Stopa" in miara_p else "Bezrobotni (tys.)"

        with col_ctrl1:
            lista_woj_p = sorted(woj_trend_all["Nazwa"].dropna().unique())
            wybrane_woj_p = st.multiselect(
                "Województwa",lista_woj_p,
                default=["Mazowieckie"] if "Mazowieckie" in lista_woj_p else lista_woj_p[:3],
                key="pulpit_woj"
            )

        PALETA_P = ["#c0392b","#2980b9","#27ae60","#8e44ad","#e67e22",
                    "#16a085","#d35400","#2c3e50","#f39c12","#1abc9c",
                    "#e74c3c","#3498db","#2ecc71","#9b59b6","#1a3a5c","#795548"]
        fig_pt = go.Figure()
        for i, wn in enumerate(wybrane_woj_p):
            d = woj_trend_all[woj_trend_all["Nazwa"]==wn]
            is_maz = "mazow" in wn.lower()
            fig_pt.add_trace(go.Scatter(
                x=d["Okres"], y=d[col_field_p],
                mode="lines+markers", name=wn,
                line=dict(color=PALETA_P[i%len(PALETA_P)], width=4 if is_maz else 2),
                marker=dict(size=9 if is_maz else 6,
                            line=dict(color="white",width=1.5)),
            ))
        fig_pt.update_layout(
            height=340,
            yaxis=dict(title=col_label_p, gridcolor="#f1f5f9",
                       tickfont=dict(size=10,color="#94a3b8")),
            legend=dict(orientation="h", y=-0.28, font=dict(size=10)),
            margin=dict(t=10,b=10),
            paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", font=dict(family="Inter, system-ui", size=11, color="#475569"), hovermode="x unified", xaxis=dict(showgrid=False, tickangle=-30, tickfont=dict(size=10,color="#94a3b8"))
        )
        st.plotly_chart(fig_pt, use_container_width=True)

# ══════════════════════════════════════════════════════════
# BEZROBOTNI
# ══════════════════════════════════════════════════════════
elif current_page == "bezrobotni":
    st.markdown("## 👥 Bezrobotni – MRPiPS")
    if df_bezr.empty:
        st.info("Brak danych bezrobocia. Dodaj pliki do folderu `bezrobocie/`")
    else:
        woj  = df_bezr[df_bezr["Typ"]=="województwo"].sort_values("Sort_key")
        powiaty = df_bezr[df_bezr["Typ"]=="powiat"].sort_values("Sort_key")

        # Metryki
        if not woj.empty:
            ost = woj.iloc[-1]
            prev = woj.iloc[-2] if len(woj)>1 else None
            delta_s = int(ost["Stan_koniec"]) - int(prev["Stan_koniec"]) if prev is not None else 0
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Stan końcowy – woj.",f"{int(ost['Stan_koniec']):,}",delta=f"{delta_s:+,}")
            c2.metric("Zarejestrowani w mies.",f"{int(ost['Zarejestrowani']):,}" if pd.notna(ost['Zarejestrowani']) else "—")
            c3.metric("Wyrejestrowani w mies.",f"{int(ost['Wyrejestrowani']):,}" if pd.notna(ost['Wyrejestrowani']) else "—")
            c4.metric("Ostatnie dane",str(ost["Okres"]))

        bz1,bz2,bz3,bz4 = st.tabs(["📈 Województwo","🗺️ Powiaty – miesiąc","📊 Trend powiatu","📋 Tabela"])

        with bz1:
            if not woj.empty:
                col_l, col_r = st.columns(2)
                with col_l:
                    fig = make_subplots(specs=[[{"secondary_y":True}]])
                    fig.add_trace(go.Scatter(x=woj["Okres"],y=woj["Stan_koniec"],
                        name="Stan końcowy",mode="lines+markers",
                        line=dict(color=C_RED,width=3),marker=dict(size=8)),secondary_y=False)
                    if "Zarejestrowani" in woj.columns:
                        fig.add_trace(go.Bar(x=woj["Okres"],y=woj["Zarejestrowani"],
                            name="Zarejestrowani",marker_color="#93c5fd",opacity=0.7),secondary_y=True)
                    fig.update_layout(title="Bezrobocie – województwo mazowieckie",height=380,**PLOTLY_LAYOUT)
                    st.plotly_chart(fig,use_container_width=True)
                with col_r:
                    # Kategorie
                    kat_map = {"Bez kwalif.":"Bez_kwalif","Do 30 lat":"Do_30_lat",
                               "Pow. 50 lat":"Pow_50_lat","Na wsi":"Na_wsi",
                               "Długotrwale":"Dlugoterwale","Cudzoziemcy":"Cudzoziemcy"}
                    wybrane = st.multiselect("Kategorie do wykresu",list(kat_map.keys()),
                                             default=["Bez kwalif.","Do 30 lat","Na wsi"])
                    if wybrane:
                        fig2 = go.Figure()
                        for k in wybrane:
                            col = kat_map[k]
                            if col in woj.columns:
                                fig2.add_trace(go.Scatter(x=woj["Okres"],y=woj[col],
                                    name=k,mode="lines+markers",marker=dict(size=7)))
                        fig2.update_layout(title="Kategorie bezrobotnych",height=380,**PLOTLY_LAYOUT)
                        st.plotly_chart(fig2,use_container_width=True)

        with bz2:
            if not powiaty.empty:
                dostepne = list(dict.fromkeys(powiaty.sort_values("Sort_key")["Okres"].astype(str).tolist()))
                wybrany = st.selectbox("Miesiąc",dostepne,index=len(dostepne)-1,key="bz2_okres")
                pow_m = powiaty[powiaty["Okres"].astype(str)==wybrany].copy()
                col_l,col_r = st.columns([3,2])
                with col_l:
                    fig = px.bar(pow_m.sort_values("Stan_koniec"),
                        x="Stan_koniec",y="Region",orientation="h",
                        color="Stan_koniec",color_continuous_scale=["#dbeafe",C_NAVY],
                        height=700,title=f"Bezrobotni wg powiatów – {wybrany}",
                        labels={"Stan_koniec":"Bezrobotni","Region":""})
                    fig.update_layout(coloraxis_showscale=False,**PLOTLY_LAYOUT)
                    st.plotly_chart(fig,use_container_width=True)
                with col_r:
                    st.dataframe(
                        pow_m[["Region","Stan_koniec","Zarejestrowani","Z_zasilkiem","Bez_kwalif","Do_30_lat"]]
                        .sort_values("Stan_koniec",ascending=False)
                        .rename(columns={"Region":"Powiat","Stan_koniec":"Bezrobotni","Z_zasilkiem":"Z zasiłkiem","Bez_kwalif":"Bez kwalif.","Do_30_lat":"Do 30 lat"}),
                        use_container_width=True,hide_index=True,height=680)


        with bz3:
            if not powiaty.empty and powiaty["Okres"].nunique()>1:
                lista_pow = sorted(powiaty["Region"].unique())
                wyb_pow = st.selectbox("Powiat",lista_pow,key="bz3_pow")
                pow_t = powiaty[powiaty["Region"]==wyb_pow].sort_values("Sort_key")
                fig = make_subplots(specs=[[{"secondary_y":True}]])
                fig.add_trace(go.Scatter(x=pow_t["Okres"],y=pow_t["Stan_koniec"],
                    name="Stan końcowy",mode="lines+markers",
                    line=dict(color=C_RED,width=3),marker=dict(size=9)),secondary_y=False)
                fig.add_trace(go.Bar(x=pow_t["Okres"],y=pow_t["Zarejestrowani"],
                    name="Zarejestrowani",marker_color="#93c5fd",opacity=0.7),secondary_y=True)
                fig.update_layout(title=f"Bezrobocie – {wyb_pow}",height=400,**PLOTLY_LAYOUT)
                st.plotly_chart(fig,use_container_width=True)
                st.dataframe(
                    pow_t[["Okres","Stan_koniec","Zarejestrowani","Bez_kwalif","Do_30_lat","Na_wsi","Dlugoterwale"]]
                    .rename(columns={"Stan_koniec":"Stan końcowy","Bez_kwalif":"Bez kwalif.","Do_30_lat":"Do 30 lat","Na_wsi":"Na wsi","Dlugoterwale":"Długotrwale"}),
                    use_container_width=True,hide_index=True)
            else:
                st.info("Potrzeba ≥2 miesięcy danych")

        with bz4:
            typ_f = st.radio("Pokaż",["województwo","powiat"],horizontal=True)
            dt = df_bezr[df_bezr["Typ"]==typ_f].copy()
            cols = ["Okres","Region","Stan_koniec","Stan_koniec_K","Zarejestrowani","Z_zasilkiem","Bez_kwalif","Do_30_lat","Na_wsi","Cudzoziemcy"]
            cols = [c for c in cols if c in dt.columns]
            st.dataframe(dt.sort_values(["Sort_key","Stan_koniec"],ascending=[True,False])[cols].rename(
                columns={"Stan_koniec":"Stan końcowy","Stan_koniec_K":"w tym kobiety","Z_zasilkiem":"Z zasiłkiem","Bez_kwalif":"Bez kwalif.","Do_30_lat":"Do 30 lat","Na_wsi":"Na wsi"}),
                use_container_width=True,hide_index=True,height=500)
            if not dt.empty:
                csv = dt[cols].to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Pobierz CSV",csv,f"bezrobocie_{typ_f}.csv","text/csv")

# ══════════════════════════════════════════════════════════
# STOPA BEZROBOCIA
# ══════════════════════════════════════════════════════════
elif current_page == "stopa":
    st.markdown("## 📉 Stopa bezrobocia – GUS")
    if df_stopa.empty:
        st.info("Brak danych. Dodaj pliki GUS do folderu `stopa_bezrobocia/` i pliki GeoJSON do folderu aplikacji")
    else:
        # Filtrowanie – wykluczamy makroregiony mazowieckie z wykresów województw
        WYKLUCZ_MAZ = ["Region Warszawski Stołeczny","Region Mazowiecki Regionalny",
                       "Makroregion Mazowiecki","Mazowiecki"]
        powiaty_s = df_stopa[df_stopa["Typ"]=="powiat"]
        woj_s     = df_stopa[
            (df_stopa["Typ"]=="województwo") &
            (~df_stopa["Nazwa"].isin(WYKLUCZ_MAZ)) &
            (~df_stopa["Kod"].astype(str).isin(["PL9","PL91","PL92"]))
        ]
        regiony_s = df_stopa[df_stopa["Typ"].isin(["region","podregion"])]

        if not woj_s.empty:
            ost = woj_s.sort_values("Sort_key").iloc[-1]
            c1,c2,c3 = st.columns(3)
            c1.metric("Stopa bezrobocia – Mazowieckie", f"{ost['Stopa']} %")
            c2.metric("Bezrobotni", f"{ost['Bezrobotni_tys']} tys.")
            c3.metric("Liczba miesięcy danych", df_stopa["Okres"].nunique())

        st_tab1, st_tab2, st_tab3 = st.tabs(["📈 Trend", "🗺️ Mapy + Powiaty", "📋 Tabela"])

        # ── TAB 1: TREND ──────────────────────────────────────────────────
        with st_tab1:
            if df_stopa["Okres"].nunique() < 2:
                st.info("Potrzeba ≥2 miesięcy danych do wykresu trendu")
            else:
                # ── Wykres województw ──
                st.markdown('<div class="sec-label">Stopa bezrobocia – województwa</div>',
                            unsafe_allow_html=True)
                woj_all = woj_s.sort_values("Sort_key")
                lista_woj = sorted(woj_all["Nazwa"].dropna().unique())

                # Multiselect NA GÓRZE – pełna szerokość
                wybrane_woj = st.multiselect(
                    "Wybierz województwa",
                    lista_woj,
                    default=["Mazowieckie"] if "Mazowieckie" in lista_woj else lista_woj[:5],
                    key="trend_woj"
                )

                PALETA = [
                    "#c0392b","#2980b9","#27ae60","#8e44ad","#e67e22",
                    "#16a085","#d35400","#2c3e50","#f39c12","#1abc9c",
                    "#e74c3c","#3498db","#2ecc71","#9b59b6","#e74c3c",
                    "#1a3a5c",
                ]

                fig_woj = go.Figure()
                for i, wn in enumerate(wybrane_woj):
                    d = woj_all[woj_all["Nazwa"] == wn]
                    kolor = PALETA[i % len(PALETA)]
                    is_maz = "mazow" in wn.lower()
                    fig_woj.add_trace(go.Scatter(
                        x=d["Okres"], y=d["Stopa"],
                        mode="lines+markers", name=wn,
                        line=dict(color=kolor, width=4 if is_maz else 2),
                        marker=dict(size=9 if is_maz else 6,
                                    symbol="circle",
                                    line=dict(color="white", width=1.5)),
                    ))
                fig_woj.update_layout(
                    height=420,
                    yaxis_title="Stopa bezrobocia (%)",
                    yaxis=dict(gridcolor="#f1f5f9", ticksuffix=" %",
                               tickfont=dict(size=11, color="#94a3b8")),
                    xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#94a3b8")),
                    legend=dict(orientation="h", y=-0.25, font=dict(size=11)),
                    hovermode="x unified",
                    paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                    font=dict(family="Inter, system-ui", size=12, color="#475569"),
                    margin=dict(t=20, b=10),
                )
                st.plotly_chart(fig_woj, use_container_width=True)

                # ── Wykres regionów i podregionów ──
                if not regiony_s.empty and regiony_s["Okres"].nunique() >= 2:
                    st.markdown("---")
                    st.markdown('<div class="sec-label">Stopa bezrobocia – regiony i podregiony mazowieckie</div>',
                                unsafe_allow_html=True)
                    reg_all = regiony_s.sort_values("Sort_key")
                    lista_reg = sorted(reg_all["Nazwa"].dropna().unique())

                    wybrane_reg = st.multiselect(
                        "Wybierz regiony / podregiony",
                        lista_reg,
                        default=lista_reg,
                        key="trend_reg"
                    )
                    fig_reg = go.Figure()
                    for i, rn in enumerate(wybrane_reg):
                        d = reg_all[reg_all["Nazwa"] == rn]
                        fig_reg.add_trace(go.Scatter(
                            x=d["Okres"], y=d["Stopa"],
                            mode="lines+markers", name=rn,
                            line=dict(color=PALETA[i % len(PALETA)], width=2),
                            marker=dict(size=7, line=dict(color="white", width=1.5)),
                            fill="tozeroy",
                            fillcolor=f"rgba({','.join(str(int(PALETA[i%len(PALETA)].lstrip('#')[j:j+2],16)) for j in (0,2,4))},0.06)",
                        ))
                    fig_reg.update_layout(
                        height=380,
                        yaxis_title="Stopa bezrobocia (%)",
                        yaxis=dict(gridcolor="#f1f5f9", ticksuffix=" %",
                                   tickfont=dict(size=11, color="#94a3b8")),
                        xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#94a3b8")),
                        legend=dict(orientation="h", y=-0.28, font=dict(size=11)),
                        hovermode="x unified",
                        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                        font=dict(family="Inter, system-ui", size=12, color="#475569"),
                        margin=dict(t=20, b=10),
                    )
                    st.plotly_chart(fig_reg, use_container_width=True)

        # ── TAB 2: MAPY + POWIATY ─────────────────────────────────────────
        with st_tab2:
            dostepne = list(dict.fromkeys(
                df_stopa.sort_values("Sort_key")["Okres"].astype(str).unique().tolist()
            ))
            wybrany = st.selectbox("Miesiąc", dostepne, index=len(dostepne)-1, key="stopa_okres")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**🇵🇱 Polska – stopa wg województw**")
                woj_m = woj_s[woj_s["Okres"].astype(str)==wybrany].drop_duplicates("Geo_nazwa")
                rysuj_mape(woj_m, geojson_woj, f"Polska · {wybrany}",
                           zoom=4.6, center={"lat":52.1,"lon":19.4}, height=560)
            with col2:
                st.markdown("**📍 Mazowieckie – stopa wg powiatów**")
                pow_m = powiaty_s[powiaty_s["Okres"].astype(str)==wybrany].copy()
                rysuj_mape(pow_m, geojson, f"Mazowieckie · {wybrany}",
                           zoom=6.4, center={"lat":52.1,"lon":21.0}, height=560)

            # Powiaty – ranking + tabela pełna szerokość
            if not pow_m.empty:
                st.markdown("---")
                st.markdown('<div class="sec-label">Ranking powiatów mazowieckich</div>',
                            unsafe_allow_html=True)

                col_bar, col_tbl = st.columns([3, 2])
                with col_bar:
                    fig_bar = px.bar(
                        pow_m.sort_values("Stopa", ascending=False),
                        x="Stopa", y="Nazwa", orientation="h",
                        color="Stopa",
                        color_continuous_scale=["#dbeafe", "#1a3a5c", C_RED],
                        height=max(500, len(pow_m)*22),
                        labels={"Stopa":"Stopa %","Nazwa":""}
                    )
                    fig_bar.update_layout(
                        coloraxis_showscale=False,
                        yaxis=dict(tickfont=dict(size=10), gridcolor="#f1f5f9"),
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

                with col_tbl:
                    # Tabela w stylu Excel – kolorowanie wierszy wg stopy
                    tbl = (pow_m[["Nazwa","Stopa","Bezrobotni_tys"]]
                           .sort_values("Stopa", ascending=False)
                           .rename(columns={"Stopa":"Stopa %","Bezrobotni_tys":"Bezrobotni (tys.)"})
                           .reset_index(drop=True))
                    tbl.index = tbl.index + 1  # numeracja od 1

                    def stopa_color(val):
                        if pd.isna(val): return ""
                        if val >= 15:    return "background-color:#fecaca;color:#991b1b;font-weight:700"
                        if val >= 10:    return "background-color:#fed7aa;color:#92400e;font-weight:600"
                        if val >= 6:     return "background-color:#fef9c3;color:#854d0e"
                        if val <= 3:     return "background-color:#dcfce7;color:#166534;font-weight:600"
                        return ""

                    styled = (tbl.style
                        .applymap(stopa_color, subset=["Stopa %"])
                        .format({"Stopa %": "{:.1f}%", "Bezrobotni (tys.)": "{:.1f}"})
                        .set_properties(**{
                            "font-size":"13px",
                            "font-family":"Inter, sans-serif",
                            "border":"1px solid #e2e8f0",
                            "padding":"6px 10px",
                        })
                        .set_table_styles([
                            {"selector":"thead th","props":[
                                ("background-color","#1a3a5c"),
                                ("color","white"),
                                ("font-weight","700"),
                                ("font-size","12px"),
                                ("padding","8px 10px"),
                                ("text-align","left"),
                            ]},
                            {"selector":"tbody tr:hover td","props":[
                                ("background-color","#f0f9ff !important"),
                            ]},
                            {"selector":"tbody tr:nth-child(even) td","props":[
                                ("background-color","#f8fafc"),
                            ]},
                        ])
                    )
                    st.dataframe(styled, use_container_width=True,
                                 height=max(500, len(tbl)*32+40))

            # Trend powiatów
            if not powiaty_s.empty and powiaty_s["Okres"].nunique() > 1:
                st.markdown("---")
                st.markdown('<div class="sec-label">Trend stopy bezrobocia – powiaty mazowieckie</div>',
                            unsafe_allow_html=True)
                col_l2, col_r2 = st.columns([4, 1])
                lista_pow = sorted(powiaty_s["Nazwa"].dropna().unique())
                with col_r2:
                    wybrane_pow = st.multiselect(
                        "Wybierz powiaty", lista_pow,
                        default=lista_pow[:5] if len(lista_pow) >= 5 else lista_pow,
                        key="trend_pow"
                    )
                with col_l2:
                    fig_pt = go.Figure()
                    for i, pn in enumerate(wybrane_pow):
                        d = powiaty_s[powiaty_s["Nazwa"] == pn].sort_values("Sort_key")
                        fig_pt.add_trace(go.Scatter(
                            x=d["Okres"], y=d["Stopa"],
                            mode="lines+markers", name=pn,
                            line=dict(color=PALETA[i % len(PALETA)], width=2),
                            marker=dict(size=7, line=dict(color="white", width=1.5)),
                        ))
                    fig_pt.update_layout(
                        height=380, yaxis_title="Stopa %",
                        yaxis=dict(gridcolor="#f1f5f9", ticksuffix=" %"),
                        hovermode="x unified",
                        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                        font=dict(family="Inter, system-ui", size=12),
                        legend=dict(orientation="h", y=-0.28, font=dict(size=10)),
                    )
                    st.plotly_chart(fig_pt, use_container_width=True)

        # ── TAB 3: TABELE ────────────────────────────────────────────────
        with st_tab3:
            dostepne_t = list(dict.fromkeys(
                df_stopa.sort_values("Sort_key")["Okres"].astype(str).unique().tolist()
            ))
            wybrany_t = st.selectbox("Miesiąc", dostepne_t,
                                     index=len(dostepne_t)-1, key="stopa_tbl_okres")

            col_t1, col_t2 = st.columns(2)

            def styl_tabeli(df_in, col_stopa="Stopa %"):
                def color_row(val):
                    if pd.isna(val): return ""
                    if val >= 15:    return "background-color:#fecaca;color:#991b1b;font-weight:700"
                    if val >= 10:    return "background-color:#fed7aa;color:#92400e;font-weight:600"
                    if val >= 6:     return "background-color:#fef9c3;color:#854d0e"
                    if val <= 3:     return "background-color:#dcfce7;color:#166534;font-weight:600"
                    return ""
                return (df_in.style
                    .applymap(color_row, subset=[col_stopa])
                    .format({col_stopa: "{:.1f}%", "Bezrobotni (tys.)": "{:.1f}"})
                    .set_properties(**{"font-size":"12px","border":"1px solid #e2e8f0","padding":"5px 9px"})
                    .set_table_styles([
                        {"selector":"thead th","props":[
                            ("background-color","#1a3a5c"),("color","white"),
                            ("font-weight","700"),("padding","7px 9px"),
                        ]},
                        {"selector":"tbody tr:nth-child(even) td","props":[
                            ("background-color","#f8fafc"),
                        ]},
                    ])
                )

            with col_t1:
                st.markdown("**🇵🇱 Województwa**")
                woj_t = woj_s[woj_s["Okres"].astype(str)==wybrany_t].copy()
                if not woj_t.empty:
                    tbl_w = (woj_t[["Nazwa","Stopa","Bezrobotni_tys"]]
                             .sort_values("Stopa", ascending=False)
                             .rename(columns={"Stopa":"Stopa %","Bezrobotni_tys":"Bezrobotni (tys.)"})
                             .reset_index(drop=True))
                    tbl_w.index += 1
                    st.dataframe(styl_tabeli(tbl_w), use_container_width=True, height="content")

            with col_t2:
                st.markdown("**📍 Powiaty mazowieckie**")
                pow_t = powiaty_s[powiaty_s["Okres"].astype(str)==wybrany_t].copy()
                if not pow_t.empty:
                    tbl_p = (pow_t[["Nazwa","Stopa","Bezrobotni_tys"]]
                             .sort_values("Stopa", ascending=False)
                             .rename(columns={"Stopa":"Stopa %","Bezrobotni_tys":"Bezrobotni (tys.)"})
                             .reset_index(drop=True))
                    tbl_p.index += 1
                    st.dataframe(styl_tabeli(tbl_p), use_container_width=True, height="content")

            st.markdown("---")
            if not df_stopa.empty:
                csv = df_stopa.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Pobierz wszystkie dane CSV", csv,
                                   "stopa_bezrobocia.csv","text/csv")

# ══════════════════════════════════════════════════════════
# ZWOLNIENIA
# ══════════════════════════════════════════════════════════
elif current_page == "zwolnienia":
    st.markdown("## 🏭 Zwolnienia grupowe")
    if df_zwol.empty:
        st.info("Brak danych zwolnień. Dodaj pliki do folderu `zwolnienia/`")
    else:
        # ── Przygotowanie list do filtrów ──
        dostepne_okresy = (list(df_zwol["Okres"].cat.categories)
                           if hasattr(df_zwol["Okres"],"cat")
                           else sorted(df_zwol["Okres"].unique()))
        dostepne_lata   = sorted(df_zwol["Rok"].unique())
        dostepne_pkd    = sorted(df_zwol["PKD"].dropna().unique())
        dostepne_firmy  = sorted(df_zwol["Nazwa"].dropna().unique())
        dostepne_pow    = sorted(df_zwol["Powiat"].dropna().unique())

        # ── FILTRY ──
        with st.expander("🔧 Filtry", expanded=True):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                tryb_okresu = st.radio("Zakres czasowy",
                    ["Wszystkie","Konkretny rok","Konkretne miesiące"],
                    horizontal=True, key="zwol_tryb_okresu")
                if tryb_okresu == "Konkretny rok":
                    wybrany_rok = st.selectbox("Rok", dostepne_lata,
                        index=len(dostepne_lata)-1, key="zwol_rok")
                    filtr_okresy = [o for o in dostepne_okresy
                                    if str(wybrany_rok) in str(o)]
                elif tryb_okresu == "Konkretne miesiące":
                    filtr_okresy = st.multiselect("Miesiące", dostepne_okresy,
                        default=dostepne_okresy[-3:] if len(dostepne_okresy)>=3 else dostepne_okresy,
                        key="zwol_mies")
                else:
                    filtr_okresy = dostepne_okresy

            with fc2:
                filtr_pkd = st.multiselect("PKD (sekcja)", dostepne_pkd,
                    default=[], key="zwol_pkd",
                    placeholder="Wszystkie PKD")
                filtr_pow = st.multiselect("Powiaty", dostepne_pow,
                    default=[], key="zwol_pow",
                    placeholder="Wszystkie powiaty")

            with fc3:
                szukaj_firma = st.text_input("🔍 Szukaj firmy", key="zwol_firma")
                filtr_firmy = st.multiselect("Firmy (lista)", dostepne_firmy,
                    default=[], key="zwol_firmy_lista",
                    placeholder="Wszystkie firmy")

        # ── Zastosuj filtry ──
        mask = df_zwol["Okres"].isin(filtr_okresy)
        if filtr_pkd:   mask &= df_zwol["PKD"].isin(filtr_pkd)
        if filtr_pow:   mask &= df_zwol["Powiat"].isin(filtr_pow)
        if filtr_firmy: mask &= df_zwol["Nazwa"].isin(filtr_firmy)
        if szukaj_firma: mask &= df_zwol["Nazwa"].str.contains(szukaj_firma, case=False, na=False)
        dff = df_zwol[mask].copy()

        # ── KPI ──
        if dff.empty:
            st.warning("Brak danych dla wybranych filtrów")
        else:
            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("Miesięcy",  len(dff["Okres"].unique()))
            c2.metric("Zgłoszeni", f"{int(dff['Zgłoszeni'].sum()):,}")
            c3.metric("Wypow. zmien.", f"{int(dff['Wypow_zmieniające'].sum()):,}")
            c4.metric("Zwolnieni", f"{int(dff['Zwolnieni'].sum()):,}")
            c5.metric("Firm",      dff["Nazwa"].nunique())

            tab1, tab2, tab3, tab4 = st.tabs(["📈 Trend miesięczny","🏭 Firmy w czasie","📊 PKD w czasie","🗺️ Powiaty"])

            # ── TAB 1: Trend miesięczny ──────────────────────────
            with tab1:
                monthly = (dff.groupby("Okres", observed=True)
                           .agg(Zwolnieni=("Zwolnieni","sum"),
                                Zgłoszeni=("Zgłoszeni","sum"),
                                Firmy=("Nazwa","nunique"))
                           .reset_index())
                fig = make_subplots(specs=[[{"secondary_y":True}]])
                fig.add_trace(go.Bar(x=monthly["Okres"], y=monthly["Zgłoszeni"],
                    name="Zgłoszeni", marker_color="#93c5fd", opacity=0.6),
                    secondary_y=False)
                fig.add_trace(go.Scatter(x=monthly["Okres"], y=monthly["Zwolnieni"],
                    name="Zwolnieni", mode="lines+markers",
                    line=dict(color=C_RED, width=3), marker=dict(size=8)),
                    secondary_y=True)
                fig.add_trace(go.Scatter(x=monthly["Okres"], y=monthly["Firmy"],
                    name="Liczba firm", mode="lines+markers",
                    line=dict(color=C_GREEN, width=2, dash="dot"), marker=dict(size=6)),
                    secondary_y=True)
                fig.update_layout(height=420,
                    yaxis=dict(title="Zgłoszeni", gridcolor="#f1f5f9"),
                    yaxis2=dict(title="Zwolnieni / Firmy"),
                    **PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(
                    monthly.rename(columns={"Firmy":"Liczba firm"}),
                    use_container_width=True, hide_index=True)

            # ── TAB 2: Firmy w czasie ────────────────────────────
            with tab2:
                st.markdown('<div class="sec-label">Firmy – zwolnienia w podziale na miesiące</div>',
                            unsafe_allow_html=True)
                col_ustawienia, _ = st.columns([2,3])
                with col_ustawienia:
                    n_firm = st.slider("Top N firm", 5, 30, 10, key="zwol_n_firm")
                    miara_firm = st.radio("Miara", ["Zwolnieni","Zgłoszeni","Wypow_zmieniające"],
                        horizontal=True, key="zwol_miara_firm")

                # Top N firm wg sumy
                top_n = (dff.groupby("Nazwa")[miara_firm].sum()
                         .sort_values(ascending=False).head(n_firm).index.tolist())
                df_top = dff[dff["Nazwa"].isin(top_n)].copy()

                # Wykres: grouped bar – firmy per miesiąc
                firm_mies = (df_top.groupby(["Okres","Nazwa"], observed=True)[miara_firm]
                             .sum().reset_index())
                fig_fm = px.bar(firm_mies,
                    x="Okres", y=miara_firm, color="Nazwa",
                    barmode="group", height=480,
                    labels={"Nazwa":"Firma", miara_firm:miara_firm.replace("_"," ")},
                    color_discrete_sequence=px.colors.qualitative.Set2)
                fig_fm.update_layout(
                    yaxis=dict(gridcolor="#f1f5f9"),
                    legend=dict(orientation="h", y=-0.3, font=dict(size=9)),
                    paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", font=dict(family="Inter, system-ui", size=11, color="#475569"), hovermode="x unified", xaxis=dict(showgrid=False, tickangle=-30, tickfont=dict(size=10,color="#94a3b8")))
                st.plotly_chart(fig_fm, use_container_width=True)

                # Tabela pivot: firmy × miesiące
                pivot_f = (firm_mies.pivot(index="Nazwa", columns="Okres", values=miara_firm)
                           .fillna(0).astype(int))
                pivot_f["SUMA"] = pivot_f.sum(axis=1)
                pivot_f = pivot_f.sort_values("SUMA", ascending=False)
                st.dataframe(pivot_f, use_container_width=True, height=350)

            # ── TAB 3: PKD w czasie ─────────────────────────────
            with tab3:
                st.markdown('<div class="sec-label">PKD – zwolnienia w podziale na miesiące</div>',
                            unsafe_allow_html=True)
                miara_pkd = st.radio("Miara", ["Zwolnieni","Zgłoszeni","Wypow_zmieniające"],
                    horizontal=True, key="zwol_miara_pkd")

                # Top 10 PKD wg sumy
                top_pkd = (dff.groupby("PKD")[miara_pkd].sum()
                           .sort_values(ascending=False).head(10).index.tolist())
                df_pkd = dff[dff["PKD"].isin(top_pkd)].copy()
                df_pkd["PKD_label"] = df_pkd["PKD"] + " – " + df_pkd["PKD_opis"].str[:25]

                pkd_mies = (df_pkd.groupby(["Okres","PKD_label"], observed=True)[miara_pkd]
                            .sum().reset_index())

                col_l, col_r = st.columns([3,2])
                with col_l:
                    fig_pkd = px.bar(pkd_mies,
                        x="Okres", y=miara_pkd, color="PKD_label",
                        barmode="stack", height=440,
                        labels={"PKD_label":"PKD", miara_pkd:miara_pkd.replace("_"," ")},
                        color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_pkd.update_layout(
                        yaxis=dict(gridcolor="#f1f5f9"),
                        legend=dict(orientation="h", y=-0.35, font=dict(size=9)),
                        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", font=dict(family="Inter, system-ui", size=11, color="#475569"), hovermode="x unified", xaxis=dict(showgrid=False, tickangle=-30, tickfont=dict(size=10,color="#94a3b8")))
                    st.plotly_chart(fig_pkd, use_container_width=True)
                with col_r:
                    # Tabela pivot PKD × miesiące
                    pivot_pkd = (pkd_mies.pivot(index="PKD_label", columns="Okres", values=miara_pkd)
                                 .fillna(0).astype(int))
                    pivot_pkd["SUMA"] = pivot_pkd.sum(axis=1)
                    pivot_pkd = pivot_pkd.sort_values("SUMA", ascending=False)
                    st.dataframe(pivot_pkd, use_container_width=True, height=420)

            # ── TAB 4: Powiaty ──────────────────────────────────
            with tab4:
                pow_agg = (dff.groupby("Powiat")
                           .agg(Zwolnieni=("Zwolnieni","sum"), Zgłoszeni=("Zgłoszeni","sum"))
                           .sort_values("Zwolnieni", ascending=False).reset_index())
                col_l, col_r = st.columns([3,2])
                with col_l:
                    fig_pow = px.bar(pow_agg, x="Zwolnieni", y="Powiat", orientation="h",
                        color="Zwolnieni",
                        color_continuous_scale=["#dbeafe", C_NAVY],
                        height=max(400, len(pow_agg)*28), labels={"Powiat":""})
                    fig_pow.update_layout(
                        coloraxis_showscale=False,
                        yaxis=dict(gridcolor="#f1f5f9"),
                        **PLOTLY_LAYOUT)
                    st.plotly_chart(fig_pow, use_container_width=True)
                with col_r:
                    st.dataframe(pow_agg, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════
# DANE SUROWE
# ══════════════════════════════════════════════════════════
elif current_page == "dane":
    st.markdown("## 📋 Dane surowe")
    tab_z,tab_b,tab_s = st.tabs(["Zwolnienia","Bezrobocie","Stopa bezrobocia"])

    with tab_z:
        if not df_zwol.empty:
            st.caption(f"{len(df_zwol):,} rekordów")
            st.dataframe(df_zwol,use_container_width=True,hide_index=True,height=500)
            csv = df_zwol.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Pobierz CSV – zwolnienia",csv,"zwolnienia.csv","text/csv")
        else: st.info("Brak danych")

    with tab_b:
        if not df_bezr.empty:
            st.caption(f"{len(df_bezr):,} rekordów")
            st.dataframe(df_bezr,use_container_width=True,hide_index=True,height=500)
            csv = df_bezr.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Pobierz CSV – bezrobocie",csv,"bezrobocie.csv","text/csv")
        else: st.info("Brak danych")

    with tab_s:
        if not df_stopa.empty:
            st.caption(f"{len(df_stopa):,} rekordów")
            st.dataframe(df_stopa,use_container_width=True,hide_index=True,height=500)
            csv = df_stopa.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Pobierz CSV – stopa",csv,"stopa_bezrobocia.csv","text/csv")
        else: st.info("Brak danych")
