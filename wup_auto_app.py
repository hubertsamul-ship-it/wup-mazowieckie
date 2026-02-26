"""
WUP Mazowieckie – Aplikacja Analityczna (wersja AUTO v2)
=========================================================
Struktura folderów:
    dane/
    ├── zwolnienia/          ← miesięczne pliki zwolnień grupowych
    │   ├── 2025-01.xlsx
    │   ├── 2025-02.xlsx
    │   └── ...
    └── bezrobocie/          ← miesięczne pliki MRPiPS-01
        ├── 2025-03.xlsx
        ├── 2026-01.xlsx
        └── ...

Obsługiwane formaty nazw plików:
    2025-01.xlsx  |  2025_01.xlsx  |  01_2025.xlsx  |  I_2025.xlsx

Uruchomienie:
    py -m streamlit run wup_auto_app.py
"""

import os, re, glob
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Konfiguracja ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WUP Mazowieckie – Rynek Pracy",
    page_icon="📊", layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS – SaaS Dashboard ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* ─── Background ─── */
.main .block-container {
    background: #f4f7f6 !important;
    padding: 0 !important;
    max-width: 100% !important;
}
.main { background: #f4f7f6 !important; }

/* ─── Sidebar ─── */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b !important;
    min-width: 240px !important;
}
[data-testid="stSidebar"] > div { padding: 0 !important; }
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #f1f5f9 !important;
    font-weight: 700 !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}
[data-testid="stSidebar"] .stButton button {
    background: transparent !important;
    border: 1px solid #1e3a5f !important;
    color: #93c5fd !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    width: 100% !important;
    transition: all 0.15s ease !important;
    margin: 2px 0 !important;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: #1e3a5f !important;
    color: #bfdbfe !important;
    border-color: #2563eb !important;
}
[data-testid="stSidebar"] .stTextInput input {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
    color: #e2e8f0 !important;
    font-size: 0.78rem !important;
}
[data-testid="stSidebar"] label {
    color: #64748b !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #1e293b !important;
    margin: 8px 0 !important;
}
[data-testid="stSidebar"] .stSuccess {
    background: rgba(16,185,129,0.1) !important;
    border: 1px solid rgba(16,185,129,0.2) !important;
    border-radius: 6px !important;
    font-size: 0.78rem !important;
}
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] .stCaption { color: #475569 !important; font-size: 0.72rem !important; }

/* ─── Main padding ─── */
.wup-main { padding: 24px 28px; }

/* ─── Page header ─── */
.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
.page-title {
    font-size: 1.35rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.02em;
}
.page-subtitle {
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 2px;
}
.date-badge {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.78rem;
    color: #475569;
    font-weight: 500;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

/* ─── KPI Cards ─── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 20px;
}
.kpi-card {
    background: white;
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04);
    border: 1px solid #f1f5f9;
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.2s ease;
}
.kpi-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 14px 14px 0 0;
}
.kpi-card.blue::before  { background: linear-gradient(90deg, #2563eb, #60a5fa); }
.kpi-card.green::before { background: linear-gradient(90deg, #059669, #34d399); }
.kpi-card.orange::before{ background: linear-gradient(90deg, #d97706, #fbbf24); }
.kpi-card.purple::before{ background: linear-gradient(90deg, #7c3aed, #a78bfa); }
.kpi-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #94a3b8;
    margin-bottom: 8px;
}
.kpi-location {
    font-size: 0.72rem;
    color: #64748b;
    margin-bottom: 4px;
    font-weight: 500;
}
.kpi-value {
    font-size: 1.9rem;
    font-weight: 800;
    color: #0f172a;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: -0.03em;
    line-height: 1;
}
.kpi-unit {
    font-size: 0.85rem;
    color: #64748b;
    font-weight: 500;
    margin-left: 2px;
    font-family: 'Inter', sans-serif;
}
.kpi-delta {
    font-size: 0.72rem;
    margin-top: 6px;
    color: #94a3b8;
}

/* ─── Section cards ─── */
.section-card {
    background: white;
    border-radius: 14px;
    padding: 20px 22px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04);
    border: 1px solid #f1f5f9;
    margin-bottom: 16px;
}
.section-title {
    font-size: 0.88rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* ─── Tabs ─── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: white;
    border-radius: 10px;
    padding: 3px;
    gap: 1px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    border: 1px solid #e2e8f0;
    margin-bottom: 16px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 7px !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    color: #64748b !important;
    padding: 7px 14px !important;
    transition: all 0.15s !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: #0f172a !important;
    color: white !important;
    font-weight: 600 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }

/* ─── Metrics (native) ─── */
[data-testid="stMetric"] {
    background: white;
    border-radius: 10px;
    padding: 14px 16px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    border: 1px solid #f1f5f9;
}
[data-testid="stMetric"] label {
    color: #94a3b8 !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-size: 1.6rem !important;
    font-weight: 800 !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ─── DataFrame ─── */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    border: 1px solid #e2e8f0 !important;
}

/* ─── Download button ─── */
.stDownloadButton button {
    background: white !important;
    border: 1.5px solid #2563eb !important;
    color: #2563eb !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
}
.stDownloadButton button:hover {
    background: #2563eb !important;
    color: white !important;
}

/* ─── Misc ─── */
h2, h3 { color: #0f172a !important; font-weight: 700 !important; }
hr { border-color: #e2e8f0 !important; margin: 16px 0 !important; }
.stCaption, small { color: #94a3b8 !important; font-size: 0.75rem !important; }
.stInfo { background: #eff6ff !important; border: 1px solid #bfdbfe !important; border-radius: 8px !important; }
.stSuccess { background: #f0fdf4 !important; border: 1px solid #bbf7d0 !important; border-radius: 8px !important; }
[data-baseweb="tag"] { background: #dbeafe !important; color: #1e40af !important; border-radius: 5px !important; font-size: 0.75rem !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

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
PKD_OPISY = {
    # Usługi finansowe i ubezpieczenia
    "6419Z":"Pozostałe usługi kredytowe","6499Z":"Pozostałe usługi finansowe",
    "6619Z":"Pozostałe usługi wspomagające finanse","6622Z":"Agenci ubezpieczeniowi",
    "6492Z":"Udzielanie pożyczek poza systemem bankowym",
    # IT i telekomunikacja
    "6110Z":"Telekomunikacja przewodowa","6120Z":"Telekomunikacja bezprzewodowa",
    "6130Z":"Telekomunikacja satelitarna","6190Z":"Pozostała telekomunikacja",
    "6201Z":"Działalność związana z oprogramowaniem",
    "6202Z":"Doradztwo w zakresie informatyki",
    "6203Z":"Zarządzanie urządzeniami informatycznymi",
    "6209Z":"Pozostała działalność usługowa w zakresie IT",
    "6311Z":"Przetwarzanie danych","6312Z":"Portale internetowe",
    "6391Z":"Działalność agencji informacyjnych",
    # Handel
    "4651Z":"Sprzedaż hurtowa komputerów i elektroniki",
    "4711Z":"Handel detaliczny w niewyspecjalizowanych sklepach",
    "4719Z":"Pozostały handel detaliczny niewyspecjalizowany",
    "4730Z":"Sprzedaż detaliczna paliw","4776Z":"Sprzedaż detaliczna kwiatów i roślin",
    # Transport i logistyka
    "4920Z":"Transport kolejowy towarów",
    "5310Z":"Działalność pocztowa objęta obowiązkiem świadczenia usług powszechnych",
    "5320Z":"Pozostała działalność pocztowa i kurierska",
    # Produkcja
    "2042Z":"Produkcja pozostałych wyrobów chemicznych",
    "2222Z":"Produkcja opakowań z tworzyw sztucznych",
    "2222.Z":"Produkcja opakowań z tworzyw sztucznych",
    "2351Z":"Produkcja cementu","2732Z":"Produkcja pozostałych przewodów elektrycznych",
    "2910B":"Produkcja pozostałych pojazdów samochodowych",
    # Działalność profesjonalna
    "7211Z":"Badania naukowe i prace rozwojowe w dziedzinie biotechnologii",
    "7311Z":"Działalność agencji reklamowych",
    "7021Z":"Public relations i komunikacja",
    "7490Z":"Pozostała działalność profesjonalna, naukowa i techniczna",
    # Pozostałe usługi
    "8220Z":"Działalność centrów telefonicznych (call center)",
    "9200Z":"Działalność związana z grami losowymi i zakładami wzajemnymi",
}

def normalizuj_pkd(pkd: str) -> str:
    """Ujednolica format PKD – usuwa kropki, spacje, zamienia na wielkie litery."""
    return re.sub(r'[.\s]', '', str(pkd).strip()).upper()

# ── Wykrywanie plików ─────────────────────────────────────────────────────────
def parsuj_nazwe(nazwa: str):
    m = re.match(r'^(\d{4})[-_.](\d{1,2})$', nazwa)
    if m: return int(m.group(1)), int(m.group(2))
    m = re.match(r'^(\d{1,2})[-_.](\d{4})$', nazwa)
    if m: return int(m.group(2)), int(m.group(1))
    m = re.match(r'^(X{0,3}(?:IX|IV|V?I{0,3}))[-_.](\d{4})$', nazwa, re.IGNORECASE)
    if m and m.group(1).upper() in ROMAN:
        return int(m.group(2)), ROMAN[m.group(1).upper()]
    m = re.match(r'^([a-ząćęłńóśźż]+)[-_.](\d{4})$', nazwa, re.IGNORECASE)
    if m and m.group(1).lower() in PL_NAMES:
        return int(m.group(2)), PL_NAMES[m.group(1).lower()]
    return None


# Słownik mapowania nazw GUS (powiaty mazowieckie) → dokładne nazwy w GeoJSON
GUS_DO_GEO = {
    "białobrzeski":      "powiat białobrzeski",
    "ciechanowski":      "powiat ciechanowski",
    "garwoliński":       "powiat garwoliński",
    "gostyniński":       "powiat gostyniński",
    "grodziski":         "powiat grodziski",
    "grójecki":          "powiat grójecki",
    "kozienicki":        "powiat kozienicki",
    "legionowski":       "powiat legionowski",
    "lipski":            "powiat lipski",
    "łosicki":           "powiat łosicki",
    "makowski":          "powiat makowski",
    "miński":            "powiat miński",
    "mławski":           "powiat mławski",
    "nowodworski":       "powiat nowodworski",
    "ostrołęcki":        "powiat ostrołęcki",
    "ostrowski":         "powiat ostrowski",
    "otwocki":           "powiat otwocki",
    "piaseczyński":      "powiat piaseczyński",
    "płocki":            "powiat płocki",
    "płoński":           "powiat płoński",
    "pruszkowski":       "powiat pruszkowski",
    "przasnyski":        "powiat przasnyski",
    "przysuski":         "powiat przysuski",
    "pułtuski":          "powiat pułtuski",
    "radomski":          "powiat radomski",
    "siedlecki":         "powiat siedlecki",
    "sierpecki":         "powiat sierpecki",
    "sochaczewski":      "powiat sochaczewski",
    "sokołowski":        "powiat sokołowski",
    "szydłowiecki":      "powiat szydłowiecki",
    "warszawski zachodni": "powiat warszawski zachodni",
    "węgrowski":         "powiat węgrowski",
    "wołomiński":        "powiat wołomiński",
    "wyszkowski":        "powiat wyszkowski",
    "zwoleński":         "powiat zwoleński",
    "żuromiński":        "powiat żuromiński",
    "żyrardowski":       "powiat żyrardowski",
    "m. ostrołęka":      "powiat Ostrołęka",
    "m. płock":          "powiat Płock",
    "m. radom":          "powiat Radom",
    "m. siedlce":        "powiat Siedlce",
    "m. warszawa":       "powiat Warszawa",
    "warszawa":          "powiat Warszawa",
}

# Mapowanie kodów NUTS2 → nazwy województw w GeoJSON
NUTS2_DO_GEO = {
    "PL21": "małopolskie",
    "PL22": "śląskie",
    "PL41": "wielkopolskie",
    "PL42": "zachodniopomorskie",
    "PL43": "lubuskie",
    "PL51": "dolnośląskie",
    "PL52": "opolskie",
    "PL61": "kujawsko-pomorskie",
    "PL62": "warmińsko-mazurskie",
    "PL63": "pomorskie",
    "PL71": "łódzkie",
    "PL72": "świętokrzyskie",
    "PL81": "lubelskie",
    "PL82": "podkarpackie",
    "PL84": "podlaskie",
    "PL9":  "mazowieckie",   # cały makroregion mazowiecki
    "PL91": "mazowieckie",   # region warszawski stołeczny → mazowieckie
    "PL92": "mazowieckie",   # region mazowiecki regionalny → mazowieckie
}


@st.cache_data
def wczytaj_geojson(sciezka: str) -> dict:
    """Wczytuje plik GeoJSON z granicami powiatów."""
    try:
        import json
        with open(sciezka, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@st.cache_data
def wczytaj_stopa_bezrobocia(folder: str) -> pd.DataFrame:
    """
    Wczytuje pliki stopy bezrobocia z GUS (format Pow_MM_YYYY.xlsx).
    Arkusz Tabl.1  – województwa/regiony/podregiony (col[4]=nazwa, col[5]=bezrobotni tys, col[6]=stopa%)
    Arkusz Tabl.1a – powiaty (col[0]=woj, col[1]=pow, col[2]=nazwa, col[3]=bezrob tys, col[4]=stopa%)
    Wyciąga tylko dane mazowieckie (woj=14).
    """
    pliki = znajdz_pliki(folder)
    records = []

    for p in pliki:
        try:
            xl = pd.ExcelFile(p["sciezka"])

            # Tabl.1 – wszystkie województwa (NUTS2, kod 4-znakowy) + mazowieckie regiony/podregiony
            if "Tabl.1" in xl.sheet_names:
                df = xl.parse("Tabl.1", header=None)
                for i in range(len(df)):
                    kod  = str(df.iloc[i, 0]).strip()
                    if not kod.startswith("PL"):
                        continue
                    nazwa  = str(df.iloc[i, 4]).strip()
                    bezrob = pd.to_numeric(df.iloc[i, 5], errors="coerce")
                    stopa  = pd.to_numeric(df.iloc[i, 6], errors="coerce")
                    if np.isnan(stopa):
                        continue
                    # Określ typ
                    if len(kod) == 4:
                        typ = "województwo"
                        geo = NUTS2_DO_GEO.get(kod)
                    elif len(kod) == 2:
                        continue  # makroregiony – pomijamy
                    elif kod == "PL9":
                        typ = "województwo_mazow"
                        geo = "mazowieckie"
                    elif kod.startswith("PL9") and len(kod) == 4:
                        typ = "region_mazow"
                        geo = None
                    elif kod.startswith("PL9"):
                        typ = "podregion_mazow"
                        geo = None
                    else:
                        continue
                    nazwa_clean = (nazwa.replace("REGION: ","")
                                       .replace("PODREGION: ","")
                                       .replace("MAKROREGION ","")
                                       .strip())
                    records.append({
                        "Okres": p["nazwa_pl"], "Rok": p["rok"],
                        "Miesiąc_num": p["miesiac"], "Sort_key": p["sort_key"],
                        "Kod": kod, "Nazwa": nazwa_clean.title(),
                        "Typ": typ,
                        "Bezrobotni_tys": bezrob,
                        "Stopa": stopa,
                        "Geo_nazwa": geo,
                    })

            # Tabl.1a – powiaty mazowieckie (woj=14)
            if "Tabl.1a" in xl.sheet_names:
                df = xl.parse("Tabl.1a", header=None)
                for i in range(len(df)):
                    woj = str(df.iloc[i, 0]).strip()
                    if woj != "14":
                        continue
                    pow_kod = str(df.iloc[i, 1]).strip()
                    nazwa   = str(df.iloc[i, 2]).strip().lower().strip()
                    bezrob  = pd.to_numeric(df.iloc[i, 3], errors="coerce")
                    stopa   = pd.to_numeric(df.iloc[i, 4], errors="coerce")
                    if np.isnan(stopa):
                        continue
                    typ = "województwo" if pow_kod == "00" else "powiat"
                    geo = GUS_DO_GEO.get(nazwa)
                    records.append({
                        "Okres": p["nazwa_pl"], "Rok": p["rok"],
                        "Miesiąc_num": p["miesiac"], "Sort_key": p["sort_key"],
                        "Kod": f"14{pow_kod}", "Nazwa": nazwa.title(),
                        "Typ": typ,
                        "Bezrobotni_tys": bezrob,
                        "Stopa": stopa,
                        "Geo_nazwa": geo,
                    })
        except Exception:
            continue

    df_out = pd.DataFrame(records)
    if not df_out.empty:
        kolejnosc = list(dict.fromkeys([p["nazwa_pl"] for p in pliki]))
        df_out["Okres"] = pd.Categorical(df_out["Okres"], categories=kolejnosc, ordered=True)
        df_out = df_out.sort_values("Sort_key")
    return df_out


def znajdz_pliki(folder: str) -> list:
    wyniki = []
    # Deduplikacja – Windows ignoruje wielkość liter więc *.xlsx i *.XLSX
    # mogą zwracać te same pliki podwójnie
    wszystkie = (glob.glob(os.path.join(folder, "*.xlsx")) +
                 glob.glob(os.path.join(folder, "*.XLSX")) +
                 glob.glob(os.path.join(folder, "*.xls")))
    seen = set()
    unikalne = []
    for s in wszystkie:
        if s.lower() not in seen:
            seen.add(s.lower())
            unikalne.append(s)
    for sciezka in unikalne:
        nazwa = os.path.splitext(os.path.basename(sciezka))[0]
        parsed = parsuj_nazwe(nazwa)
        if parsed:
            rok, mies = parsed
            if 1 <= mies <= 12 and 2000 <= rok <= 2100:
                wyniki.append({
                    "sciezka": sciezka, "rok": rok, "miesiac": mies,
                    "nazwa_pl": f"{MIESIAC_PL[mies]} {rok}",
                    "sort_key": rok * 100 + mies,
                })
    return sorted(wyniki, key=lambda x: x["sort_key"])


# ── Wczytywanie zwolnień ──────────────────────────────────────────────────────
@st.cache_data
def wczytaj_zwolnienia(folder: str):
    pliki = znajdz_pliki(folder)
    records = []
    for p in pliki:
        try:
            try:
                xl = pd.read_excel(p["sciezka"], sheet_name="dane", header=None)
            except Exception:
                xl = pd.read_excel(p["sciezka"], header=None)
            for i in range(7, len(xl)):
                vals = list(xl.iloc[i])
                powiat = vals[1] if len(vals) > 1 else None
                if not isinstance(powiat, str) or len(powiat.strip()) < 2:
                    continue
                if any(x in powiat.lower() for x in ["powiat","suma","ogółem","razem"]):
                    continue
                def g(idx):
                    v = vals[idx] if idx < len(vals) else None
                    return None if (v is None or (isinstance(v, float) and np.isnan(v))) else v
                nazwa = re.sub(r"\s{2,}", " ", str(g(3) or "").strip())[:70]
                pkd_raw = str(g(5) or "").strip()
                pkd     = normalizuj_pkd(pkd_raw)
                records.append({
                    "Okres": p["nazwa_pl"], "Rok": p["rok"],
                    "Miesiąc_num": p["miesiac"], "Sort_key": p["sort_key"],
                    "Powiat": powiat.strip(), "Nazwa": nazwa,
                    "PKD": pkd, "PKD_opis": PKD_OPISY.get(pkd, pkd),
                    "Zgłoszeni":         pd.to_numeric(g(6),  errors="coerce") or 0,
                    "Wypow_zmieniające": pd.to_numeric(g(8),  errors="coerce") or 0,
                    "Zwolnieni":         pd.to_numeric(g(10), errors="coerce") or 0,
                    "Monitorowani":      pd.to_numeric(g(11), errors="coerce") or 0,
                    "Likwidacja":        str(g(9) or "").strip().lower() == "tak",
                })
        except Exception:
            continue
    df = pd.DataFrame(records)
    if not df.empty:
        # Deduplikacja – usuń duplikaty okresów (gdy dwa pliki mają ten sam miesiąc)
        kolejnosc = list(dict.fromkeys([p["nazwa_pl"] for p in pliki]))
        df["Okres"] = pd.Categorical(df["Okres"], categories=kolejnosc, ordered=True)
    return df, pliki


# ── Wczytywanie bezrobocia MRPiPS-01 ─────────────────────────────────────────
def klasyfikuj_jednostke(sheet: str, region: str) -> str:
    """Klasyfikuje arkusz jako województwo / region / podregion / powiat."""
    if sheet == "WOJEWÓDZTWO OGÓŁEM":
        return "województwo"
    r = region.upper()
    if "REGION" in r and "PODREGION" not in r:
        return "region"
    if "PODREGION" in r or sheet.startswith("R.") or sheet.lower().startswith("podregion") or sheet.lower().startswith("warszawski"):
        return "podregion"
    return "powiat"


@st.cache_data
def wczytaj_bezrobocie(folder: str) -> pd.DataFrame:
    """
    Wczytuje wszystkie pliki MRPiPS-01.
    Wyciąga dane dla województwa, regionów, podregionów i powiatów.
    """
    pliki = znajdz_pliki(folder)
    records = []

    for p in pliki:
        try:
            xl = pd.ExcelFile(p["sciezka"])
            for sheet in xl.sheet_names:
                if sheet in ["dbf", "Arkusz2"]:
                    continue
                try:
                    df = xl.parse(sheet, header=None)
                    if len(df) < 20:
                        continue

                    region = str(df.iloc[0, 0]).strip()
                    if region in ["nan", ""] or region.startswith("za miesiąc"):
                        region = sheet

                    # Znajdź wiersz Ogółem
                    ogol_row = None
                    for ri in range(10, min(25, len(df))):
                        if "Ogółem" in str(df.iloc[ri, 0]):
                            ogol_row = ri
                            break
                    if ogol_row is None:
                        ogol_row = 15

                    def v(ri, ci):
                        try:
                            return pd.to_numeric(df.iloc[ri, ci], errors="coerce")
                        except Exception:
                            return np.nan

                    def znajdz(tekst, start=15, stop=50):
                        for ri in range(start, min(stop, len(df))):
                            for ci in range(min(5, df.shape[1])):
                                if tekst.lower() in str(df.iloc[ri, ci]).lower():
                                    return ri
                        return None

                    stan = v(ogol_row, 12)
                    if np.isnan(stan):
                        continue

                    ri_wsi    = znajdz("Zamieszkali na wsi")
                    ri_zwol   = znajdz("zwolnione z przyczyn dotyczących")
                    ri_bez_kw = znajdz("bez kwalifikacji")
                    ri_do30   = znajdz("do 30 roku")
                    ri_do25   = znajdz("do 25 roku")
                    ri_pow50  = znajdz("powyżej 50")
                    ri_dlugt  = znajdz("długotrwale")
                    ri_niepeł = znajdz("niepełnosprawni")
                    ri_cudz   = znajdz("Cudzoziemcy")

                    def vr(ri):
                        return v(ri, 12) if ri is not None else np.nan

                    typ = klasyfikuj_jednostke(sheet, region)

                    records.append({
                        "Okres":          p["nazwa_pl"],
                        "Rok":            p["rok"],
                        "Miesiąc_num":    p["miesiac"],
                        "Sort_key":       p["sort_key"],
                        "Region":         region.strip().title(),
                        "Arkusz":         sheet,
                        "Typ":            typ,
                        "Stan_koniec":    stan,
                        "Stan_koniec_K":  v(ogol_row, 13),
                        "Zarejestrowani": v(ogol_row, 8),
                        "Z_zasilkiem":    v(ogol_row, 14),
                        "Na_wsi":         vr(ri_wsi),
                        "Zwolnieni_zakl": vr(ri_zwol),
                        "Bez_kwalif":     vr(ri_bez_kw),
                        "Do_30_lat":      vr(ri_do30),
                        "Do_25_lat":      vr(ri_do25),
                        "Pow_50_lat":     vr(ri_pow50),
                        "Dlugoterwale":   vr(ri_dlugt),
                        "Niepelnosprawni":vr(ri_niepeł),
                        "Cudzoziemcy":    vr(ri_cudz),
                    })
                except Exception:
                    continue
        except Exception:
            continue

    df_out = pd.DataFrame(records)
    if not df_out.empty:
        kolejnosc = list(dict.fromkeys([p["nazwa_pl"] for p in pliki]))
        df_out["Okres"] = pd.Categorical(df_out["Okres"], categories=kolejnosc, ordered=True)
        df_out = df_out.sort_values("Sort_key")
    return df_out


# ════════════════════════════════════════════════════════════════════════════
# UI
# ════════════════════════════════════════════════════════════════════════════

# ── Sidebar – nawigacja + wczytywanie danych ──────────────────────────────────
with st.sidebar:
    # Logo / Tytuł
    st.markdown("""
    <div style="padding: 20px 16px 12px 16px; border-bottom: 1px solid #1e293b;">
        <div style="font-size:0.65rem;font-weight:700;letter-spacing:0.12em;color:#3b82f6;text-transform:uppercase;margin-bottom:4px;">WUP Warszawa</div>
        <div style="font-size:1rem;font-weight:800;color:#f1f5f9;letter-spacing:-0.01em;line-height:1.2;">Rynek Pracy</div>
        <div style="font-size:0.68rem;color:#475569;margin-top:3px;">Województwo Mazowieckie</div>
    </div>
    """, unsafe_allow_html=True)

    # Nawigacja
    st.markdown("""
    <div style="padding: 12px 16px 4px 16px;">
        <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;color:#334155;text-transform:uppercase;margin-bottom:8px;">Menu</div>
    </div>
    """, unsafe_allow_html=True)

    nav_opcje = {
        "🏠  Pulpit":             "pulpit",
        "👥  Bezrobotni":         "bezrobotni",
        "📉  Stopa bezrobocia":   "stopa",
        "🏭  Zwolnienia grupowe": "zwolnienia",
        "📋  Dane surowe":        "dane_surowe",
    }
    if "nav" not in st.session_state:
        st.session_state["nav"] = "pulpit"

    for label, key in nav_opcje.items():
        is_active = st.session_state["nav"] == key
        btn_style = "background:#1e3a5f !important; color:#bfdbfe !important; border-color:#2563eb !important;" if is_active else ""
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state["nav"] = key
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.divider()

    # Dane techniczne – zwinięte
    with st.expander("⚙️ Ustawienia danych", expanded=False):
        folder_zwol = st.text_input("Zwolnienia", value=os.path.join(BASE_DIR, "dane", "zwolnienia"))
        folder_bezr = st.text_input("Bezrobocie MRPiPS", value=os.path.join(BASE_DIR, "dane", "bezrobocie"))
        folder_stopa = st.text_input("Stopa bezrobocia", value=os.path.join(BASE_DIR, "dane", "stopa_bezrobocia"))

    if st.button("🔄  Odśwież dane", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Wczytaj dane (cicho)
    folder_zwol  = os.path.join(BASE_DIR, "dane", "zwolnienia")
    folder_bezr  = os.path.join(BASE_DIR, "dane", "bezrobocie")
    folder_stopa = os.path.join(BASE_DIR, "dane", "stopa_bezrobocia")
    geojson_sciezka     = os.path.join(BASE_DIR, "powiaty.geojson")
    geojson_woj_sciezka = os.path.join(BASE_DIR, "wojewodztwa.geojson")

    df_zwol = pd.DataFrame(); pliki_zwol = []
    df_bezr = pd.DataFrame(); df_stopa = pd.DataFrame()
    geojson = {}; geojson_woj = {}

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

    # Status danych
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    status_items = []
    if pliki_zwol: status_items.append(f"✅ Zwolnienia: {len(pliki_zwol)} mies.")
    if not df_bezr.empty: status_items.append(f"✅ Bezrobocie: {df_bezr[['Rok','Miesiąc_num']].drop_duplicates().shape[0]} mies.")
    if not df_stopa.empty: status_items.append(f"✅ Stopa bezr.: {df_stopa[['Rok','Miesiąc_num']].drop_duplicates().shape[0]} mies.")
    for s in status_items:
        st.caption(s)

current_page = st.session_state.get("nav", "pulpit")


# Filtracja danych zwolnień
wybrane_okresy = list(df_zwol["Okres"].cat.categories) if not df_zwol.empty and hasattr(df_zwol["Okres"], "cat") else []
wybrane_powiaty = sorted(df_zwol["Powiat"].unique()) if not df_zwol.empty else []
szukaj = ""

# Filtracja
dff = df_zwol.copy() if not df_zwol.empty else pd.DataFrame()
if not dff.empty:
    if wybrane_okresy:
        dff = dff[dff["Okres"].isin(wybrane_okresy)]
    if wybrane_powiaty:
        dff = dff[dff["Powiat"].isin(wybrane_powiaty)]

# ── Filtrowanie zwolnień ──────────────────────────────────────────────────────
dff = df_zwol.copy() if not df_zwol.empty else pd.DataFrame()

# ── Nawigacja stron ────────────────────────────────────────────────────────────
def render_page_header(title, subtitle, last_date=None):
    date_html = f'<div class="date-badge">📅 Ostatnie dane: <b>{last_date}</b></div>' if last_date else ""
    st.markdown(f"""
    <div style="padding: 20px 28px 0 28px;">
        <div class="page-header">
            <div>
                <div class="page-title">{title}</div>
                <div class="page-subtitle">{subtitle}</div>
            </div>
            {date_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_kpi(label, location, value, unit, color_class):
    return f"""
    <div class="kpi-card {color_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-location">{location}</div>
        <div class="kpi-value">{value}<span class="kpi-unit">{unit}</span></div>
    </div>"""

# ═══════════════════════════════════════════════════════════════════
# PULPIT
# ═══════════════════════════════════════════════════════════════════
if current_page == "pulpit":
    # Dane do KPI
    ostatni_bezr = None
    ostatnia_stopa_mazow = None
    ostatnia_stopa_wawa = None
    ostatni_bezr_wawa = None
    last_date = None

    if not df_stopa.empty:
        powiaty_s = df_stopa[df_stopa["Typ"] == "powiat"]
        woj_s = df_stopa[df_stopa["Typ"] == "województwo"]
        if not woj_s.empty:
            ost_woj = woj_s.sort_values("Sort_key").iloc[-1]
            ostatnia_stopa_mazow = ost_woj["Stopa"]
            ostatni_bezr = ost_woj["Bezrobotni_tys"]
            last_date = str(ost_woj["Okres"])
        if not powiaty_s.empty:
            wawa = powiaty_s[powiaty_s["Nazwa"].str.lower().str.contains("warszawa")]
            if not wawa.empty:
                ost_wawa = wawa.sort_values("Sort_key").iloc[-1]
                ostatnia_stopa_wawa = ost_wawa["Stopa"]
                ostatni_bezr_wawa = ost_wawa["Bezrobotni_tys"]

    render_page_header("Pulpit", "Przegląd kluczowych wskaźników rynku pracy", last_date)

    # KPI Cards
    kpi_html = '<div style="padding: 16px 28px;"><div class="kpi-grid">'
    kpi_html += render_kpi("Bezrobotni", "Mazowieckie",
                            f"{ostatni_bezr:.1f}" if ostatni_bezr else "—", " tys.", "blue")
    kpi_html += render_kpi("Stopa bezrobocia", "Mazowieckie",
                            f"{ostatnia_stopa_mazow:.1f}" if ostatnia_stopa_mazow else "—", "%", "green")
    kpi_html += render_kpi("Bezrobotni", "m. Warszawa",
                            f"{ostatni_bezr_wawa:.1f}" if ostatni_bezr_wawa else "—", " tys.", "orange")
    kpi_html += render_kpi("Stopa bezrobocia", "m. Warszawa",
                            f"{ostatnia_stopa_wawa:.1f}" if ostatnia_stopa_wawa else "—", "%", "purple")
    kpi_html += '</div></div>'
    st.markdown(kpi_html, unsafe_allow_html=True)

    # Mapy
    st.markdown('<div style="padding: 0 28px;">', unsafe_allow_html=True)
    col_map1, col_map2 = st.columns(2)

    def rysuj_mape_pulpit(df_mapa, geojson_data, tytul, zoom, center, height=380):
        if not geojson_data or df_mapa.empty:
            st.info("Brak danych do mapy")
            return
        geo_map = {f["properties"]["nazwa"]: f["properties"]["id"] for f in geojson_data["features"]}
        df_mapa = df_mapa.copy()
        df_mapa["geo_id"] = df_mapa["Geo_nazwa"].map(geo_map)
        df_plot = df_mapa.dropna(subset=["geo_id"])
        if df_plot.empty:
            st.info("Brak dopasowanych danych")
            return
        fig = px.choropleth_mapbox(
            df_plot, geojson=geojson_data, locations="geo_id",
            featureidkey="properties.id", color="Stopa",
            hover_name="Nazwa",
            hover_data={"Stopa":":.1f","Bezrobotni_tys":":.1f","geo_id":False},
            color_continuous_scale="Blues",
            range_color=[0, df_plot["Stopa"].max()],
            mapbox_style="carto-positron",
            zoom=zoom, center=center, opacity=0.85,
            labels={"Stopa":"Stopa %","Bezrobotni_tys":"Bezrobotni (tys.)"},
            height=height,
        )
        fig.update_layout(
            margin={"r":0,"t":30,"l":0,"b":0},
            title=dict(text=tytul, font=dict(size=13, color="#0f172a"), x=0),
            coloraxis_colorbar=dict(title="Stopa %", thickness=10, len=0.7),
            paper_bgcolor="white", plot_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)

    if not df_stopa.empty:
        ostatni_key = df_stopa["Sort_key"].max()
        okres_str = str(df_stopa[df_stopa["Sort_key"]==ostatni_key]["Okres"].iloc[0])

        with col_map1:
            st.markdown('<div class="section-card"><div class="section-title">🇵🇱 Stopa bezrobocia – Polska</div>', unsafe_allow_html=True)
            woj_map = df_stopa[(df_stopa["Typ"]=="województwo") & (df_stopa["Sort_key"]==ostatni_key)].copy()
            # Poprawka: Mazowieckie jako jedno województwo
            woj_map = woj_map[woj_map["Geo_nazwa"].notna()]
            rysuj_mape_pulpit(woj_map, geojson_woj, f"Polska · {okres_str}", 5.0, {"lat":52.1,"lon":19.5})
            st.markdown('</div>', unsafe_allow_html=True)

        with col_map2:
            st.markdown('<div class="section-card"><div class="section-title">📍 Stopa bezrobocia – powiaty mazowieckie</div>', unsafe_allow_html=True)
            pow_map = df_stopa[(df_stopa["Typ"]=="powiat") & (df_stopa["Sort_key"]==ostatni_key)].copy()
            rysuj_mape_pulpit(pow_map, geojson, f"Mazowieckie · {okres_str}", 6.5, {"lat":52.1,"lon":20.8})
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        with col_map1:
            st.info("Brak danych stopy bezrobocia")
        with col_map2:
            st.info("Dodaj pliki do folderu stopa_bezrobocia/")

    st.markdown('</div>', unsafe_allow_html=True)

    # Wykres trendu z przełącznikiem
    st.markdown('<div style="padding: 0 28px 28px 28px;">', unsafe_allow_html=True)
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📈 Trend w czasie</div>', unsafe_allow_html=True)

    if not df_stopa.empty:
        col_toggle, _ = st.columns([2,5])
        with col_toggle:
            miara = st.radio("Wskaźnik", ["Stopa bezrobocia (%)", "Liczba bezrobotnych (tys.)"],
                              horizontal=False, key="pulpit_miara")
        col_field = "Stopa" if "Stopa" in miara else "Bezrobotni_tys"
        col_label = "Stopa %" if "Stopa" in miara else "Bezrobotni (tys.)"

        woj_trend = df_stopa[df_stopa["Typ"]=="województwo"].sort_values("Sort_key")
        if not woj_trend.empty:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=woj_trend["Okres"], y=woj_trend[col_field],
                mode="lines+markers",
                line=dict(color="#2563eb", width=3),
                marker=dict(size=8, color="#2563eb",
                            line=dict(color="white", width=2)),
                name="Mazowieckie",
                fill="tozeroy",
                fillcolor="rgba(37,99,235,0.06)",
            ))
            fig_trend.update_layout(
                height=280, hovermode="x unified",
                xaxis_tickangle=-30,
                yaxis_title=col_label,
                paper_bgcolor="white", plot_bgcolor="white",
                margin=dict(l=0,r=0,t=10,b=40),
                xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#94a3b8")),
                yaxis=dict(gridcolor="#f1f5f9", tickfont=dict(size=11, color="#94a3b8")),
                showlegend=False,
            )
            st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Brak danych do wykresu trendu")

    st.markdown('</div></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# POZOSTAŁE STRONY – stare zakładki
# ═══════════════════════════════════════════════════════════════════
elif current_page in ["bezrobotni","stopa","zwolnienia","dane_surowe"]:
    st.markdown('<div style="padding: 20px 28px;">', unsafe_allow_html=True)

    if current_page == "zwolnienia":
        render_page_header("Zwolnienia grupowe", "Analiza zgłoszeń zwolnień grupowych")
    elif current_page == "bezrobotni":
        render_page_header("Bezrobotni", "Dane MRPiPS – bezrobocie rejestrowane")
    elif current_page == "stopa":
        render_page_header("Stopa bezrobocia", "Dane GUS – stopa bezrobocia wg jednostek terytorialnych")
    elif current_page == "dane_surowe":
        render_page_header("Dane surowe", "Eksport i podgląd danych")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Przegląd zwolnień", "🏭 Firmy i PKD", "🗺️ Powiaty zwolnień", "👥 Bezrobocie",
        "📊 Stopa bezrobocia", "📋 Dane surowe",
    ])
    st.markdown('</div>', unsafe_allow_html=True)
    # Wyświetl odpowiednią zakładkę automatycznie
    if current_page == "zwolnienia":
        pass  # tab1/tab2/tab3 obsługują zwolnienia
    elif current_page == "bezrobotni":
        pass  # tab4
    elif current_page == "stopa":
        pass  # tab5



# ════════════ TAB 1 – PRZEGLĄD ════════════
with tab1:
    if dff.empty:
        st.info("Brak danych zwolnień")
    else:
        c1,c2,c3,c4 = st.columns(4)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Okresy",                  len(dff["Okres"].unique()))
        c2.metric("Zgłoszeni",               f"{int(dff['Zgłoszeni'].sum()):,}")
        c3.metric("Wypow. zmieniające",      f"{int(dff['Wypow_zmieniające'].sum()):,}")
        c4.metric("Zwolnieni",               f"{int(dff['Zwolnieni'].sum()):,}")
        c5.metric("Monitorowani",            f"{int(dff['Monitorowani'].sum()):,}")
        st.divider()

        monthly = (dff.groupby("Okres", observed=True)
                   .agg(Zwolnieni=("Zwolnieni","sum"),
                        Zgłoszeni=("Zgłoszeni","sum"),
                        Firmy=("Nazwa","count"))
                   .reset_index())
        fig = make_subplots(specs=[[{"secondary_y":True}]])
        fig.add_trace(go.Bar(x=monthly["Okres"], y=monthly["Zgłoszeni"],
                             name="Zgłoszeni", marker_color="#93c5fd", opacity=0.7),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=monthly["Okres"], y=monthly["Zwolnieni"],
                                 name="Zwolnieni", mode="lines+markers",
                                 line=dict(color="#dc2626", width=3), marker=dict(size=8)),
                      secondary_y=True)
        fig.add_trace(go.Scatter(x=monthly["Okres"], y=monthly["Firmy"],
                                 name="Liczba firm", mode="lines+markers",
                                 line=dict(color="#16a34a", width=2, dash="dot"),
                                 marker=dict(size=6)),
                      secondary_y=True)
        fig.update_layout(title="Zwolnienia grupowe miesięcznie – Mazowieckie",
                          height=430, hovermode="x unified", xaxis_tickangle=-30,
                          legend=dict(orientation="h", y=-0.25))
        fig.update_yaxes(title_text="Zgłoszeni", secondary_y=False)
        fig.update_yaxes(title_text="Zwolnieni / Firmy", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tabela miesięczna")
        st.dataframe(monthly.rename(columns={"Firmy":"Liczba firm"}),
                     use_container_width=True, hide_index=True)


# ════════════ TAB 2 – FIRMY i PKD ════════════
with tab2:
    if dff.empty:
        st.info("Brak danych")
    else:
        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("Top firm wg zwolnionych")
            n = st.slider("Ile firm?", 5, 30, 15)
            top_f = (dff.groupby("Nazwa")
                     .agg(Zgłoszeni=("Zgłoszeni","sum"), Zwolnieni=("Zwolnieni","sum"))
                     .sort_values("Zwolnieni", ascending=False).head(n).reset_index())
            fig_f = px.bar(top_f, x="Zwolnieni", y="Nazwa", orientation="h",
                           color="Zwolnieni", color_continuous_scale="Reds",
                           height=max(350, n*26))
            fig_f.update_layout(yaxis=dict(autorange="reversed"),
                                coloraxis_showscale=False, yaxis_title="")
            st.plotly_chart(fig_f, use_container_width=True)
        with col_r:
            st.subheader("Top sekcji PKD")
            pkd_metric = st.radio("Miara", ["Zwolnieni","Wypow_zmieniające","Zgłoszeni"],
                                   horizontal=True, key="pkd_metric")
            top_p = (dff.groupby(["PKD","PKD_opis"])
                     .agg(Zwolnieni=("Zwolnieni","sum"),
                          Wypow_zmieniające=("Wypow_zmieniające","sum"),
                          Zgłoszeni=("Zgłoszeni","sum"))
                     .sort_values(pkd_metric, ascending=False).head(15).reset_index())
            top_p["Label"] = top_p["PKD"] + " – " + top_p["PKD_opis"].str[:28]
            fig_p = px.bar(top_p, x=pkd_metric, y="Label", orientation="h",
                           color=pkd_metric, color_continuous_scale="Oranges", height=430)
            fig_p.update_layout(yaxis=dict(autorange="reversed"),
                                coloraxis_showscale=False, yaxis_title="")
            st.plotly_chart(fig_p, use_container_width=True)

        # Wypowiedzenia zmieniające – osobna sekcja
        st.divider()
        st.subheader("📋 Wypowiedzenia zmieniające warunki pracy i płacy")
        wypow_df = (dff[dff["Wypow_zmieniające"] > 0]
                    .groupby(["Nazwa","PKD","PKD_opis","Powiat"])
                    .agg(Wypow_zmieniające=("Wypow_zmieniające","sum"),
                         Zgłoszeni=("Zgłoszeni","sum"))
                    .sort_values("Wypow_zmieniające", ascending=False)
                    .reset_index())
        if wypow_df.empty:
            st.info("Brak wypowiedzeń zmieniających w wybranym okresie")
        else:
            c1, c2 = st.columns([2,1])
            with c1:
                fig_wz = px.bar(wypow_df.head(15), x="Wypow_zmieniające", y="Nazwa",
                                orientation="h", color="Wypow_zmieniające",
                                color_continuous_scale="Purples",
                                title="Top firm – wypowiedzenia zmieniające",
                                height=max(300, len(wypow_df.head(15))*28))
                fig_wz.update_layout(yaxis=dict(autorange="reversed"),
                                     coloraxis_showscale=False, yaxis_title="")
                st.plotly_chart(fig_wz, use_container_width=True)
            with c2:
                st.dataframe(wypow_df[["Nazwa","PKD","Wypow_zmieniające","Powiat"]],
                             use_container_width=True, hide_index=True,
                             column_config={"Wypow_zmieniające": st.column_config.NumberColumn(format="%d")})


# ════════════ TAB 3 – POWIATY ════════════
with tab3:
    if dff.empty:
        st.info("Brak danych")
    else:
        pow_df = (dff.groupby("Powiat")
                  .agg(Zwolnieni=("Zwolnieni","sum"),
                       Zgłoszeni=("Zgłoszeni","sum"),
                       Firmy=("Nazwa","count"))
                  .sort_values("Zwolnieni", ascending=False).reset_index())
        col_a, col_b = st.columns([2,1])
        with col_a:
            fig_pow = px.bar(pow_df.head(15), x="Powiat", y="Zwolnieni",
                             color="Zwolnieni", color_continuous_scale="Blues",
                             title="Top 15 powiatów", height=400)
            fig_pow.update_xaxes(tickangle=-35)
            fig_pow.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_pow, use_container_width=True)
        with col_b:
            st.dataframe(pow_df, use_container_width=True, hide_index=True,
                         column_config={"Zwolnieni": st.column_config.NumberColumn(format="%d")})

        top10 = pow_df.head(10)["Powiat"].tolist()
        heat  = (dff[dff["Powiat"].isin(top10)]
                 .groupby(["Powiat","Okres"], observed=True)["Zwolnieni"].sum()
                 .reset_index()
                 .pivot(index="Powiat", columns="Okres", values="Zwolnieni")
                 .fillna(0))
        fig_h = px.imshow(heat, color_continuous_scale="YlOrRd",
                          title="Heatmapa – top 10 powiatów × miesiąc",
                          height=350, aspect="auto")
        fig_h.update_xaxes(tickangle=-30)
        st.plotly_chart(fig_h, use_container_width=True)


# ════════════ TAB 4 – BEZROBOCIE ════════════
with tab4:
    if df_bezr.empty:
        st.info("ℹ️ Brak danych bezrobocia – dodaj pliki MRPiPS do folderu `bezrobocie/`")
    else:
        def safe_int(val):
            return f"{int(val):,}" if (val is not None and not np.isnan(val)) else "—"

        woj     = df_bezr[df_bezr["Typ"] == "województwo"].sort_values("Sort_key")
        powiaty = df_bezr[df_bezr["Typ"] == "powiat"].sort_values("Sort_key")
        podreg  = df_bezr[df_bezr["Typ"] == "podregion"].sort_values("Sort_key")

        # Metryki ostatniego miesiąca
        if not woj.empty:
            ostatni = woj.iloc[-1]
            st.caption(f"Ostatnie dane: **{ostatni['Okres']}**")
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Bezrobotni (stan)",  f"{int(ostatni['Stan_koniec']):,}")
            c2.metric("Zarejestrowani",     safe_int(ostatni["Zarejestrowani"]))
            c3.metric("Do 30 lat",          safe_int(ostatni["Do_30_lat"]))
            c4.metric("Bez kwalifikacji",   safe_int(ostatni["Bez_kwalif"]))
            st.divider()

        # Podzakładki
        bz1, bz2, bz3, bz4 = st.tabs([
            "📈 Trend województwa",
            "🗺️ Powiaty – wybrany miesiąc",
            "📊 Trend powiatu",
            "📋 Tabela",
        ])

        # ── BZ1: Trend województwa ──
        with bz1:
            if len(woj) > 1:
                fig_t = make_subplots(specs=[[{"secondary_y":True}]])
                fig_t.add_trace(go.Scatter(x=woj["Okres"], y=woj["Stan_koniec"],
                                           name="Stan końcowy", mode="lines+markers",
                                           line=dict(color="#dc2626", width=3),
                                           marker=dict(size=9)), secondary_y=False)
                fig_t.add_trace(go.Scatter(x=woj["Okres"], y=woj["Stan_koniec_K"],
                                           name="w tym kobiety", mode="lines+markers",
                                           line=dict(color="#f97316", width=2, dash="dot"),
                                           marker=dict(size=7)), secondary_y=False)
                fig_t.add_trace(go.Bar(x=woj["Okres"], y=woj["Zarejestrowani"],
                                       name="Zarejestrowani w miesiącu",
                                       marker_color="#93c5fd", opacity=0.6),
                                secondary_y=True)
                fig_t.update_layout(height=430, hovermode="x unified", xaxis_tickangle=-30,
                                    legend=dict(orientation="h", y=-0.25))
                fig_t.update_yaxes(title_text="Stan bezrobocia", secondary_y=False)
                fig_t.update_yaxes(title_text="Zarejestrowani", secondary_y=True)
                st.plotly_chart(fig_t, use_container_width=True)
            else:
                st.info("Potrzeba co najmniej 2 miesięcy do wykresu trendu")

            # Trend kategorii
            if len(woj) > 1:
                st.subheader("Trend wybranych kategorii")
                kategorie = {
                    "Bez kwalifikacji":"Bez_kwalif",
                    "Do 30 lat":"Do_30_lat",
                    "Do 25 lat":"Do_25_lat",
                    "Powyżej 50 lat":"Pow_50_lat",
                    "Długotrwale bezrobotni":"Dlugoterwale",
                    "Zamieszkali na wsi":"Na_wsi",
                    "Cudzoziemcy":"Cudzoziemcy",
                    "Niepełnosprawni":"Niepelnosprawni",
                }
                wybrane_kat = st.multiselect(
                    "Wybierz kategorie",
                    list(kategorie.keys()),
                    default=["Bez kwalifikacji","Do 30 lat","Długotrwale bezrobotni"]
                )
                if wybrane_kat:
                    fig_kat = go.Figure()
                    for kat in wybrane_kat:
                        dane = woj[woj[kategorie[kat]].notna()]
                        fig_kat.add_trace(go.Scatter(
                            x=dane["Okres"], y=dane[kategorie[kat]],
                            name=kat, mode="lines+markers", marker=dict(size=7)
                        ))
                    fig_kat.update_layout(height=380, hovermode="x unified",
                                          xaxis_tickangle=-30,
                                          legend=dict(orientation="h", y=-0.35))
                    st.plotly_chart(fig_kat, use_container_width=True)

        # ── BZ2: Powiaty – wybrany miesiąc ──
        with bz2:
            if powiaty.empty:
                st.info("Brak danych powiatowych")
            else:
                dostepne_okresy = list(dict.fromkeys(
                    powiaty.sort_values("Sort_key")["Okres"].astype(str).tolist()
                ))
                wybrany_okres = st.selectbox(
                    "Wybierz miesiąc", dostepne_okresy,
                    index=len(dostepne_okresy)-1
                )
                pow_m = powiaty[powiaty["Okres"].astype(str) == wybrany_okres].copy()

                col_l, col_r = st.columns([3,2])
                with col_l:
                    fig_pow = px.bar(
                        pow_m.sort_values("Stan_koniec"),
                        x="Stan_koniec", y="Region", orientation="h",
                        color="Stan_koniec", color_continuous_scale="RdYlGn_r",
                        title=f"Bezrobotni wg powiatów – {wybrany_okres}",
                        height=700,
                        labels={"Stan_koniec":"Bezrobotni","Region":""}
                    )
                    fig_pow.update_layout(coloraxis_showscale=False)
                    st.plotly_chart(fig_pow, use_container_width=True)

                with col_r:
                    st.dataframe(
                        pow_m[["Region","Stan_koniec","Zarejestrowani","Z_zasilkiem",
                               "Bez_kwalif","Do_30_lat"]]
                        .sort_values("Stan_koniec", ascending=False)
                        .rename(columns={
                            "Region":"Powiat","Stan_koniec":"Bezrobotni",
                            "Zarejestrowani":"Zarej.","Z_zasilkiem":"Z zasiłkiem",
                            "Bez_kwalif":"Bez kwalif.","Do_30_lat":"Do 30 lat"
                        }),
                        use_container_width=True, hide_index=True, height=680
                    )

                # Heatmapa powiatów w czasie (jeśli więcej miesięcy)
                if powiaty["Okres"].nunique() > 1:
                    st.subheader("Heatmapa – bezrobocie powiatów w czasie")
                    heat = (powiaty
                            .groupby(["Region","Okres"], observed=True)["Stan_koniec"]
                            .sum().reset_index()
                            .pivot(index="Region", columns="Okres", values="Stan_koniec")
                            .fillna(0))
                    fig_heat = px.imshow(heat, color_continuous_scale="RdYlGn_r",
                                         height=600, aspect="auto",
                                         labels={"color":"Bezrobotni"})
                    fig_heat.update_xaxes(tickangle=-30)
                    st.plotly_chart(fig_heat, use_container_width=True)

        # ── BZ3: Trend wybranego powiatu ──
        with bz3:
            if powiaty.empty or powiaty["Okres"].nunique() < 2:
                st.info("Potrzeba co najmniej 2 miesięcy danych powiatowych")
            else:
                lista_powiatow = sorted(powiaty["Region"].unique())
                wybrany_powiat = st.selectbox("Wybierz powiat", lista_powiatow)
                pow_trend = powiaty[powiaty["Region"] == wybrany_powiat].sort_values("Sort_key")

                fig_pt = make_subplots(specs=[[{"secondary_y":True}]])
                fig_pt.add_trace(go.Scatter(
                    x=pow_trend["Okres"], y=pow_trend["Stan_koniec"],
                    name="Stan końcowy", mode="lines+markers",
                    line=dict(color="#dc2626", width=3), marker=dict(size=9)
                ), secondary_y=False)
                fig_pt.add_trace(go.Bar(
                    x=pow_trend["Okres"], y=pow_trend["Zarejestrowani"],
                    name="Zarejestrowani", marker_color="#93c5fd", opacity=0.7
                ), secondary_y=True)
                fig_pt.update_layout(
                    title=f"Bezrobocie – {wybrany_powiat}",
                    height=400, hovermode="x unified", xaxis_tickangle=-30,
                    legend=dict(orientation="h", y=-0.25)
                )
                fig_pt.update_yaxes(title_text="Stan bezrobocia", secondary_y=False)
                fig_pt.update_yaxes(title_text="Zarejestrowani", secondary_y=True)
                st.plotly_chart(fig_pt, use_container_width=True)

                st.dataframe(
                    pow_trend[["Okres","Stan_koniec","Zarejestrowani","Bez_kwalif",
                               "Do_30_lat","Na_wsi","Dlugoterwale"]]
                    .rename(columns={
                        "Stan_koniec":"Stan końcowy","Bez_kwalif":"Bez kwalif.",
                        "Do_30_lat":"Do 30 lat","Na_wsi":"Na wsi",
                        "Dlugoterwale":"Długotrwale"
                    }),
                    use_container_width=True, hide_index=True
                )

        # ── BZ4: Tabela ──
        with bz4:
            typ_filtr = st.radio("Pokaż", ["województwo","podregion","powiat"],
                                  horizontal=True, index=0)
            df_tab = df_bezr[df_bezr["Typ"] == typ_filtr].copy()
            cols_w = ["Okres","Region","Stan_koniec","Stan_koniec_K","Zarejestrowani",
                      "Z_zasilkiem","Bez_kwalif","Do_30_lat","Na_wsi","Cudzoziemcy"]
            st.dataframe(
                df_tab.sort_values(["Sort_key","Stan_koniec"], ascending=[True,False])[cols_w]
                .rename(columns={
                    "Stan_koniec":"Stan końcowy","Stan_koniec_K":"w tym kobiety",
                    "Z_zasilkiem":"Z zasiłkiem","Bez_kwalif":"Bez kwalif.",
                    "Do_30_lat":"Do 30 lat","Na_wsi":"Na wsi",
                }),
                use_container_width=True, hide_index=True, height=500
            )


# ════════════ TAB 5 – STOPA BEZROBOCIA ════════════
with tab5:
    if df_stopa.empty:
        st.info("ℹ️ Brak danych – dodaj pliki GUS do folderu `stopa_bezrobocia/` i plik `powiaty.geojson` do folderu `WUP_Aplikacja`")
        st.markdown("""
        **Oczekiwane nazwy plików:** `Pow01_2026.xlsx`, `Pow02_2026.xlsx` itd.
        (aplikacja automatycznie wykryje daty)
        """)
    else:
        powiaty_s = df_stopa[df_stopa["Typ"] == "powiat"]
        woj_s     = df_stopa[df_stopa["Typ"] == "województwo"]
        regiony_s = df_stopa[df_stopa["Typ"].isin(["region","podregion"])]

        # Metryki
        if not woj_s.empty:
            ost = woj_s.sort_values("Sort_key").iloc[-1]
            st.caption(f"Ostatnie dane: **{ost['Okres']}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Stopa bezrobocia – woj.", f"{ost['Stopa']} %")
            c2.metric("Bezrobotni", f"{ost['Bezrobotni_tys']} tys.")
            c3.metric("Miesięcy danych", df_stopa["Okres"].nunique())
            st.divider()

        st_tab1, st_tab2, st_tab3 = st.tabs([
            "🗺️ Mapa powiatów",
            "📈 Trend",
            "📋 Tabela",
        ])

        def rysuj_mape(df_mapa, geojson_data, tytul, zoom, center, height=580):
            """Rysuje choropleth mapbox."""
            if not geojson_data:
                st.warning("⚠️ Brak pliku GeoJSON – mapa niedostępna")
                return
            geo_map = {f["properties"]["nazwa"]: f["properties"]["id"]
                       for f in geojson_data["features"]}
            df_mapa = df_mapa.copy()
            df_mapa["geo_id"] = df_mapa["Geo_nazwa"].map(geo_map)
            df_plot = df_mapa.dropna(subset=["geo_id"])
            if df_plot.empty:
                st.warning("Brak dopasowanych danych do mapy")
                return
            fig = px.choropleth_mapbox(
                df_plot,
                geojson=geojson_data,
                locations="geo_id",
                featureidkey="properties.id",
                color="Stopa",
                hover_name="Nazwa",
                hover_data={"Stopa": ":.1f", "Bezrobotni_tys": ":.1f", "geo_id": False},
                color_continuous_scale="RdYlGn_r",
                range_color=[0, df_plot["Stopa"].max()],
                mapbox_style="carto-positron",
                zoom=zoom, center=center, opacity=0.8,
                title=tytul,
                labels={"Stopa": "Stopa %", "Bezrobotni_tys": "Bezrobotni (tys.)"},
                height=height,
            )
            fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0},
                              coloraxis_colorbar=dict(title="Stopa %"))
            st.plotly_chart(fig, use_container_width=True)

        # ── Mapa ──
        with st_tab1:
            woj_s_mapa = df_stopa[df_stopa["Typ"] == "województwo"].copy()
            dostepne = list(dict.fromkeys(
                df_stopa.sort_values("Sort_key")["Okres"].astype(str).unique().tolist()
            ))
            wybrany = st.selectbox("Miesiąc", dostepne,
                                    index=len(dostepne)-1, key="stopa_okres")

            st.subheader(f"🇵🇱 Polska – stopa bezrobocia wg województw – {wybrany}")
            woj_m = woj_s_mapa[woj_s_mapa["Okres"].astype(str) == wybrany]
            rysuj_mape(woj_m, geojson_woj, f"Polska – {wybrany}",
                       zoom=5.0, center={"lat": 52.1, "lon": 19.5}, height=560)

            # Tabela województw
            if not woj_m.empty:
                st.dataframe(
                    woj_m[["Nazwa","Stopa","Bezrobotni_tys"]]
                    .sort_values("Stopa", ascending=False)
                    .rename(columns={"Stopa":"Stopa %","Bezrobotni_tys":"Bezrobotni (tys.)"}),
                    use_container_width=True, hide_index=True
                )

            st.divider()
            st.subheader(f"📍 Mazowieckie – stopa bezrobocia wg powiatów – {wybrany}")
            if not powiaty_s.empty:
                pow_m = powiaty_s[powiaty_s["Okres"].astype(str) == wybrany].copy()
                rysuj_mape(pow_m, geojson, f"Mazowieckie – {wybrany}",
                           zoom=6.5, center={"lat": 52.1, "lon": 20.8}, height=580)

                # Tabela powiatów
                col_l, col_r = st.columns([3,2])
                with col_l:
                    fig_bar = px.bar(
                        pow_m.sort_values("Stopa", ascending=False),
                        x="Stopa", y="Nazwa", orientation="h",
                        color="Stopa", color_continuous_scale="RdYlGn_r",
                        title=f"Ranking powiatów mazowieckich – {wybrany}",
                        height=700, labels={"Stopa":"Stopa %","Nazwa":""}
                    )
                    fig_bar.update_layout(coloraxis_showscale=False)
                    st.plotly_chart(fig_bar, use_container_width=True)
                with col_r:
                    st.dataframe(
                        pow_m[["Nazwa","Stopa","Bezrobotni_tys"]]
                        .sort_values("Stopa", ascending=False)
                        .rename(columns={"Stopa":"Stopa %","Bezrobotni_tys":"Bezrobotni (tys.)"}),
                        use_container_width=True, hide_index=True, height=680
                    )

        # ── Trend ──
        with st_tab2:
            if df_stopa["Okres"].nunique() < 2:
                st.info("Potrzeba co najmniej 2 miesięcy do wykresu trendu")
            else:
                # Polska ogółem + wszystkie województwa
                polska_s = df_stopa[df_stopa["Kod"] == "0"].sort_values("Sort_key")
                woj_all  = df_stopa[df_stopa["Typ"] == "województwo"].sort_values("Sort_key")

                st.subheader("🇵🇱 Trend – Polska i województwa")
                lista_woj = sorted(woj_all["Nazwa"].unique())
                wybrane_woj = st.multiselect(
                    "Wybierz województwa do wykresu",
                    lista_woj,
                    default=["Mazowieckie"] if "Mazowieckie" in lista_woj else lista_woj[:5],
                    key="trend_woj"
                )

                fig_woj = go.Figure()
                # Polska ogółem
                if not polska_s.empty:
                    fig_woj.add_trace(go.Scatter(
                        x=polska_s["Okres"], y=polska_s["Stopa"],
                        mode="lines+markers", name="POLSKA",
                        line=dict(color="#111827", width=3, dash="dash"),
                        marker=dict(size=8)
                    ))
                # Wybrane województwa
                for woj_n in wybrane_woj:
                    d = woj_all[woj_all["Nazwa"] == woj_n].sort_values("Sort_key")
                    fig_woj.add_trace(go.Scatter(
                        x=d["Okres"], y=d["Stopa"],
                        mode="lines+markers", name=woj_n,
                        marker=dict(size=7)
                    ))
                fig_woj.update_layout(
                    height=420, hovermode="x unified", xaxis_tickangle=-30,
                    yaxis_title="Stopa bezrobocia %",
                    legend=dict(orientation="h", y=-0.3)
                )
                st.plotly_chart(fig_woj, use_container_width=True)

                st.divider()
                st.subheader("📍 Trend – powiaty mazowieckie")
                if not powiaty_s.empty and powiaty_s["Okres"].nunique() > 1:
                    col_l, col_r = st.columns([1,2])
                    with col_l:
                        wybrany_p = st.selectbox("Jeden powiat", sorted(powiaty_s["Nazwa"].unique()), key="trend_powiat")
                    with col_r:
                        wybrane_p = st.multiselect(
                            "Porównaj kilka powiatów",
                            sorted(powiaty_s["Nazwa"].unique()),
                            default=sorted(powiaty_s["Nazwa"].unique())[:4],
                            key="trend_powiaty"
                        )

                    col_a, col_b = st.columns(2)
                    with col_a:
                        p_trend = powiaty_s[powiaty_s["Nazwa"] == wybrany_p].sort_values("Sort_key")
                        fig_pt = go.Figure()
                        fig_pt.add_trace(go.Scatter(
                            x=p_trend["Okres"], y=p_trend["Stopa"],
                            mode="lines+markers",
                            line=dict(color="#2563eb", width=3), marker=dict(size=9),
                            name=wybrany_p
                        ))
                        fig_pt.update_layout(title=f"{wybrany_p}", height=350,
                                             hovermode="x unified", xaxis_tickangle=-30,
                                             yaxis_title="Stopa %")
                        st.plotly_chart(fig_pt, use_container_width=True)

                    with col_b:
                        fig_comp = go.Figure()
                        for pow_n in wybrane_p:
                            d = powiaty_s[powiaty_s["Nazwa"] == pow_n].sort_values("Sort_key")
                            fig_comp.add_trace(go.Scatter(
                                x=d["Okres"], y=d["Stopa"],
                                mode="lines+markers", name=pow_n, marker=dict(size=7)
                            ))
                        fig_comp.update_layout(
                            title="Porównanie powiatów", height=350,
                            hovermode="x unified", xaxis_tickangle=-30,
                            yaxis_title="Stopa %",
                            legend=dict(orientation="h", y=-0.4)
                        )
                        st.plotly_chart(fig_comp, use_container_width=True)

        # ── Tabela ──
        with st_tab3:
            typ_s = st.radio("Pokaż", ["powiat","województwo","region","podregion"],
                              horizontal=True)
            df_t = df_stopa[df_stopa["Typ"] == typ_s].copy()
            df_t2 = df_t.sort_values(["Sort_key","Stopa"], ascending=[True,False])[["Okres","Nazwa","Stopa","Bezrobotni_tys"]].rename(columns={"Stopa":"Stopa %","Bezrobotni_tys":"Bezrobotni (tys.)"})
            st.dataframe(df_t2, use_container_width=True, hide_index=True, height=500)






# ════════════ TAB 5 – SUROWE DANE ════════════
with tab6:
    if not dff.empty:
        st.subheader(f"Zwolnienia ({len(dff):,} rekordów)")
        cols = ["Okres","Powiat","Nazwa","PKD","PKD_opis",
                "Zgłoszeni","Wypow_zmieniające","Zwolnieni","Monitorowani","Likwidacja"]
        st.dataframe(
            dff[cols].sort_values(["Okres","Zwolnieni"], ascending=[True,False]),
            use_container_width=True, hide_index=True, height=400,
            column_config={
                "Zwolnieni": st.column_config.NumberColumn(format="%d"),
                "Likwidacja": st.column_config.CheckboxColumn(),
            }
        )
        csv = dff[cols].to_csv(index=False, encoding="utf-8-sig")
        st.download_button("⬇️ Pobierz CSV – zwolnienia", csv,
                           file_name="zwolnienia_export.csv", mime="text/csv")

    if not df_bezr.empty:
        st.subheader(f"Bezrobocie ({len(df_bezr):,} rekordów)")
        cols_b = ["Okres","Region","Stan_koniec","Zarejestrowani",
                  "Bez_kwalif","Do_30_lat","Na_wsi","Cudzoziemcy"]
        st.dataframe(df_bezr[cols_b], use_container_width=True,
                     hide_index=True, height=400)
        csv_b = df_bezr[cols_b].to_csv(index=False, encoding="utf-8-sig")
        st.download_button("⬇️ Pobierz CSV – bezrobocie", csv_b,
                           file_name="bezrobocie_export.csv", mime="text/csv")


# ── Stopka ────────────────────────────────────────────────────────────────────
st.divider()
n_zw = len(pliki_zwol) if pliki_zwol else 0
n_bz = (df_bezr[["Rok","Miesiąc_num"]].drop_duplicates().shape[0]
        if not df_bezr.empty else 0)
st.caption(f"📁 Zwolnienia: {n_zw} plików · Bezrobocie: {n_bz} plików | WUP Mazowieckie")
