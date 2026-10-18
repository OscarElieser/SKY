"""Mercados consultados bajo demanda; SOLO lectura, nada de órdenes ni custodia."""
import csv
from datetime import datetime, timezone
from io import StringIO
import json
import os
import re
from urllib import parse, request

CRYPTOS = {"Bitcoin": "bitcoin", "Ethereum": "ethereum", "Solana": "solana", "Cardano": "cardano", "Dogecoin": "dogecoin"}
ACCIONES = {"Apple": "aapl.us", "Microsoft": "msft.us", "NVIDIA": "nvda.us", "Alphabet": "googl.us", "Amazon": "amzn.us", "Tesla": "tsla.us", "S&P 500 ETF (SPY)": "spy.us"}


def _fetch(url, headers=None, max_bytes=1_500_000):
    req = request.Request(url, headers={"User-Agent": "NeuralTPersonal/4.0 (uso personal)", **(headers or {})})
    with request.urlopen(req, timeout=12) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("La respuesta del servicio supera el máximo de tamaño")
    return raw


def cripto_precios(ids=("bitcoin", "ethereum")):
    ids = tuple(ids)
    if not ids or len(ids) > 5 or not set(ids).issubset(set(CRYPTOS.values())):
        raise ValueError("Selecciona hasta cinco criptomonedas reconocidas")
    q = parse.urlencode({"ids": ",".join(ids), "vs_currencies": "usd", "include_24hr_change": "true", "include_last_updated_at": "true"})
    encabezados = {}
    if os.getenv("COINGECKO_DEMO_API_KEY"):
        encabezados["x-cg-demo-api-key"] = os.environ["COINGECKO_DEMO_API_KEY"]
    data = json.loads(_fetch("https://api.coingecko.com/api/v3/simple/price?" + q, encabezados))
    return [{"activo": nombre, "usd": data[ident].get("usd"), "variacion_24h_pct": data[ident].get("usd_24h_change"),
             "actualizado_utc": datetime.fromtimestamp(data[ident]["last_updated_at"], timezone.utc).isoformat()
              if data[ident].get("last_updated_at") else "Sin fecha", "fuente": "CoinGecko"}
            for nombre, ident in CRYPTOS.items() if ident in ids and ident in data]


def accion_historial(simbolo):
    if simbolo not in ACCIONES.values():
        raise ValueError("Símbolo no autorizado")
    # Stooq proporciona cierres históricos; no equivale a un feed bursátil en tiempo real.
    q = parse.urlencode({"s": simbolo, "i": "d"})
    raw = _fetch("https://stooq.com/q/d/l/?" + q, max_bytes=3_000_000).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(StringIO(raw))
    if not {"Date", "Close"}.issubset(reader.fieldnames or []):
        raise ValueError("Proveedor sin datos históricos disponibles")
    rows=[]
    for r in reader:
        try:
            date = datetime.strptime(r["Date"], "%Y-%m-%d").date().isoformat()
            close = float(r["Close"])
            if close > 0:
                rows.append({"fecha": date, "cierre_usd": close})
        except (ValueError, TypeError):
            continue
    if not rows:
        raise ValueError("El proveedor no devolvió cotizaciones válidas")
    return rows[-252:]


def rentabilidad_historica(inicio, final):
    if inicio <= 0:
        raise ValueError("Precio inicial debe ser mayor que cero")
    return (final / inicio - 1) * 100
