import os
from functools import lru_cache


FALLBACK_POINTS = [
    {"country": "Brasil", "city": "Sao Paulo", "provider": "Rede local", "latitude": -23.5505, "longitude": -46.6333},
    {"country": "Brasil", "city": "Rio de Janeiro", "provider": "Rede local", "latitude": -22.9068, "longitude": -43.1729},
    {"country": "Estados Unidos", "city": "New York", "provider": "Rede externa", "latitude": 40.7128, "longitude": -74.0060},
    {"country": "Portugal", "city": "Lisboa", "provider": "Rede externa", "latitude": 38.7223, "longitude": -9.1393},
]


@lru_cache(maxsize=1)
def _reader():
    db_path = os.environ.get("GEOIP_DB_PATH")
    if not db_path:
        return None
    try:
        import geoip2.database
        return geoip2.database.Reader(db_path)
    except Exception:
        return None


def lookup_ip(ip):
    reader = _reader()
    if reader:
        try:
            response = reader.city(ip)
            provider = ""
            try:
                provider = reader.asn(ip).autonomous_system_organization or ""
            except Exception:
                pass
            return {
                "country": response.country.name or "Desconhecido",
                "city": response.city.name or "Desconhecida",
                "provider": provider or "Provedor desconhecido",
                "latitude": response.location.latitude,
                "longitude": response.location.longitude,
            }
        except Exception:
            pass

    total = sum(ord(char) for char in ip or "local")
    point = FALLBACK_POINTS[total % len(FALLBACK_POINTS)]
    return dict(point)
