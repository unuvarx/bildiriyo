import tempfile
from pathlib import Path

import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0 Safari/537.36"
)
TIMEOUT = 90

# Bazı .gov.tr siteleri (örn. ilan.gov.tr) ara sertifikayı göndermiyor.
# Eksik ara sertifikalar certs/ klasöründe; certifi listesine eklenir.
_CERTS = Path(__file__).resolve().parent / "certs"


def _ca_bundle() -> str:
    bundle = Path(tempfile.gettempdir()) / "bildiriyo-ca.pem"
    parts = [Path(certifi.where()).read_text()] + [p.read_text() for p in sorted(_CERTS.glob("*.pem"))]
    bundle.write_text("\n".join(parts))
    return str(bundle)


def session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    s.headers["Accept-Language"] = "tr-TR,tr;q=0.9"
    s.verify = _ca_bundle()
    retry = Retry(
        total=2,
        connect=1,  # bağlantı hiç kurulamıyorsa (engel) uzun süre deneme
        backoff_factor=3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=None,  # POST'ları da tekrar dene (hepsi okuma amaçlı)
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s
