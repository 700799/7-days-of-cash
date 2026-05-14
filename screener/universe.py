import pandas as pd
import time
from typing import List

_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

_EXTENDED_TICKERS = [
    # Mid-cap growth names commonly screened
    "SMCI", "CRWD", "DDOG", "NET", "SNOW", "MDB", "BILL", "GTLB", "ZS", "OKTA",
    "CFLT", "IOT", "AFRM", "UPST", "SOFI", "HOOD", "COIN", "MARA", "RIOT", "HUT",
    "CLSK", "CIFR", "BTDR", "CORZ", "IREN", "WULF", "BITF", "BTBT", "SRM", "BTCS",
    "NVDA", "AMD", "AVGO", "QCOM", "MRVL", "MCHP", "SWKS", "QRVO", "MPWR", "SITM",
    "AEHR", "ACLS", "ONTO", "FORM", "ICHR", "CAMT", "KLIC", "COHU", "MTSI", "PSIX",
    "AXON", "TMDX", "SILK", "INSP", "NVCR", "RXRX", "NTRA", "EXAS", "PCVX", "VRTX",
    "KRYS", "DNLI", "ARVN", "RCKT", "SGMO", "EDIT", "NTLA", "BEAM", "PRME", "VERV",
    "CELH", "HIMS", "GERN", "URGN", "IDYA", "KYMR", "PRAX", "ACAD", "SAGE", "VNDA",
    "APP", "TTWO", "EA", "RBLX", "U", "CPNG", "SE", "GRAB", "DKNG", "PENN",
    "ASTS", "LUNR", "RDW", "MNTS", "SPIR", "BKSY", "PL", "ISPO", "RKLB", "ASTR",
    "SMMT", "PRCT", "TARS", "IMVT", "LGND", "ITCI", "ADMA", "BPMC", "FOLD", "PTGX",
    "ENPH", "SEDG", "FSLR", "ARRY", "CSIQ", "JKS", "MAXN", "SHLS", "NOVA", "STEM",
    "HALO", "ALKT", "AMBA", "SLAB", "POWI", "DIOD", "VSH", "RMBS", "CEVA", "XPEL",
    "SQ", "AFRM", "PAYC", "PAX", "FOUR", "RPAY", "FLYW", "DLO", "RELY", "CASS",
]


def get_sp500_tickers() -> List[str]:
    try:
        tables = pd.read_html(_SP500_URL, header=0)
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        return sorted(set(tickers))
    except Exception:
        return []


def get_extended_tickers() -> List[str]:
    sp500 = set(get_sp500_tickers())
    extra = [t for t in _EXTENDED_TICKERS if t not in sp500]
    return sorted(set(sp500) | set(extra))


def load_custom_tickers(path: str) -> List[str]:
    with open(path) as f:
        lines = [ln.strip().upper() for ln in f if ln.strip() and not ln.startswith("#")]
    return sorted(set(lines))
