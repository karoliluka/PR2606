import pandas as pd
import numpy as np
import streamlit as st

OBCINE = [
    "LJUBLJANA", "MARIBOR", "CELJE", "KOPER", "KRANJ",
    "DOMŽALE", "NOVO MESTO", "VELENJE", "KAMNIK", "NOVA GORICA"
]

BARVE = {
    "LJUBLJANA":   "#E53935", "MARIBOR":     "#1E88E5",
    "CELJE":       "#43A047", "KOPER":       "#FB8C00",
    "KRANJ":       "#8E24AA", "DOMŽALE":     "#00ACC1",
    "NOVO MESTO":  "#F4511E", "VELENJE":     "#6D4C41",
    "KAMNIK":      "#546E7A", "NOVA GORICA": "#FFB300",
}

TRZNI_KODI = [1, 2, 5]

# SURS — Povprečna mesečna neto plača (€)
# Vir: https://pxweb.stat.si/ (Povprečne plače po dejavnostih, SI mesečno)
PLACE = {
    2015: 1013, 2016: 1030, 2017: 1062, 2018: 1113, 2019: 1174,
    2020: 1216, 2021: 1292, 2022: 1427, 2023: 1558, 2024: 1680, 2025: 1750,
}

# ECB — Main refinancing operations rate (povprečje leta, %)
# Vir: https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html
ECB_RATE = {
    2015: 0.05, 2016: 0.00, 2017: 0.00, 2018: 0.00, 2019: 0.00,
    2020: 0.00, 2021: 0.00, 2022: 0.96, 2023: 4.00, 2024: 3.65, 2025: 2.65,
}

# Inflacija SLO HICP (%)
# Vir: https://ec.europa.eu/eurostat/web/hicp + SURS
INFLACIJA = {
    2015: 0.0, 2016: -0.2, 2017: 1.6, 2018: 1.9, 2019: 1.6,
    2020: -0.1, 2021: 4.9, 2022: 10.8, 2023: 7.0, 2024: 2.3, 2025: 1.8,
}

# SURS — Število prebivalcev po občinah, 1. januar
# Vir: https://pxweb.stat.si/pxweb/sl/stat/stat__05__prebivalstvo__10__stevilo_preb__05__05C40__/05C4002S.px/
POPULACIJA = {
    "LJUBLJANA":   {2015:288307, 2016:290021, 2017:292988, 2018:295504, 2019:297974,
                    2020:294054, 2021:309401, 2022:313123, 2023:316537, 2024:319283, 2025:321000},
    "MARIBOR":     {2015:93847,  2016:93163,  2017:92459,  2018:91989,  2019:91873,
                    2020:95171,  2021:95720,  2022:95782,  2023:96036,  2024:95854,  2025:96000},
    "CELJE":       {2015:48644,  2016:48275,  2017:48063,  2018:47884,  2019:47685,
                    2020:49402,  2021:49653,  2022:49756,  2023:49902,  2024:49976,  2025:50100},
    "KOPER":       {2015:52540,  2016:52809,  2017:53133,  2018:53451,  2019:54005,
                    2020:52722,  2021:53373,  2022:53892,  2023:54357,  2024:54823,  2025:55100},
    "KRANJ":       {2015:55972,  2016:56263,  2017:56663,  2018:56970,  2019:57424,
                    2020:56612,  2021:57098,  2022:57370,  2023:57601,  2024:57957,  2025:58200},
    "DOMŽALE":     {2015:35438,  2016:35711,  2017:36016,  2018:36358,  2019:36725,
                    2020:36614,  2021:37025,  2022:37379,  2023:37793,  2024:38091,  2025:38300},
    "NOVO MESTO":  {2015:36457,  2016:36760,  2017:37109,  2018:37485,  2019:37740,
                    2020:37138,  2021:37544,  2022:37863,  2023:38123,  2024:38389,  2025:38600},
    "VELENJE":     {2015:25679,  2016:25555,  2017:25468,  2018:25393,  2019:25300,
                    2020:25717,  2021:25699,  2022:25639,  2023:25553,  2024:25436,  2025:25300},
    "KAMNIK":      {2015:29680,  2016:29893,  2017:30080,  2018:30289,  2019:30548,
                    2020:30439,  2021:30816,  2022:31082,  2023:31369,  2024:31661,  2025:31900},
    "NOVA GORICA": {2015:31884,  2016:32066,  2017:32239,  2018:32439,  2019:32625,
                    2020:31891,  2021:32125,  2022:32345,  2023:32568,  2024:32735,  2025:32900},
}


def klasificiraj_tip(raba: str) -> str:
    """Classify property as Hiša/Stanovanje based on GURS DEJANSKA_RABA code."""
    r = str(raba).strip()
    if r.startswith("111") or r.startswith("1 -") or r.startswith("1-"):
        return "Hiša"
    elif r.startswith("112") or r.startswith("2 -") or r.startswith("2-") or r.startswith("47") or r.startswith("3 -"):
        return "Stanovanje"
    return "Drugo"


@st.cache_data
def load_data(path: str = "data/raw/vsi_bivanski.csv") -> pd.DataFrame:
    """Load and clean ETN data with same filters as the team's analysis notebook."""
    df = pd.read_csv(path, low_memory=False)
    df["TIP"]      = df["DEJANSKA_RABA_DELA_STAVBE"].apply(klasificiraj_tip)
    df["LETO"]     = df["LETO_x"]
    df["POVRSINA"] = df["POVRSINA_DELA_STAVBE"]
    df["CENA_M2"]  = df["POGODBENA_CENA_ODSKODNINA"] / df["POVRSINA"]

    df = df[
        df["OBCINA"].isin(OBCINE) &
        df["TRZNOST_POSLA"].isin(TRZNI_KODI) &
        (df["POVRSINA"] > 5) &
        (df["POGODBENA_CENA_ODSKODNINA"] > 0) &
        (df["CENA_M2"] > 300) &
        (df["CENA_M2"] < 15_000) &
        df["TIP"].isin(["Hiša", "Stanovanje"]) &
        df["LETO"].between(2015, 2025)
    ].copy().reset_index(drop=True)

    # IQR-style trim: drop bottom 5% and top 5% within (OBCINA, TIP, LETO) groups.
    # Merge-based approach avoids pandas 2.x groupby+apply key-column dropping.
    q_lo = df.groupby(["OBCINA", "TIP", "LETO"])["CENA_M2"].quantile(0.05).rename("q_lo")
    q_hi = df.groupby(["OBCINA", "TIP", "LETO"])["CENA_M2"].quantile(0.95).rename("q_hi")
    bounds = pd.concat([q_lo, q_hi], axis=1).reset_index()
    df = df.merge(bounds, on=["OBCINA", "TIP", "LETO"])
    df = (
        df[(df["CENA_M2"] >= df["q_lo"]) & (df["CENA_M2"] <= df["q_hi"])]
        .drop(columns=["q_lo", "q_hi"])
        .reset_index(drop=True)
    )
    return df


def load_population() -> dict:
    """Return embedded SURS population data per municipality per year."""
    return POPULACIJA


def load_wages() -> dict:
    """Return embedded SURS net monthly wage data per year."""
    return PLACE


def load_ecb_rates() -> dict:
    """Return embedded ECB main refi rate per year (%)."""
    return ECB_RATE


def load_inflation() -> dict:
    """Return embedded HICP inflation rate per year (%)."""
    return INFLACIJA
