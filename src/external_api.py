import json
import logging
import os
from typing import Dict, List

import requests
from dotenv import load_dotenv

from src.utils import PROJECT_ROOT

load_dotenv()
api_key = os.getenv("API_KEY")
headers = {"apikey": f"{api_key}"}
api_key_stock = os.getenv("API_KEY_STOCK")
headers_stock = {"access_key": f"{api_key_stock}"}

logger = logging.getLogger("external_api")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(PROJECT_ROOT / "logs" / "external_api.log", mode="w", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s : %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def get_currency_rates(currencies: List[str]) -> List[Dict[str, float]]:
    """
    Запрашивает курсы валют к рублю.
    Возвращает список словарей: {"currency": "USD", "rate": 73.21}
    """
    logger.info("Requesting currency rates for %s", currencies)

    results: List[Dict[str, float]] = []
    for cur in currencies:
        url = f"https://api.apilayer.com/currency_data/live?source={cur}&currencies=RUB"
        try:
            response = requests.get(url, headers=headers, timeout=1000)
        except requests.RequestException as exc:
            logger.error("Currency API request failed for %s: %s", cur, exc)
            results.append({"currency": cur, "rate": 0.0})
            continue

        status_code = response.status_code
        if status_code == 200:
            try:
                content_dict = json.loads(response.text)
                rate = content_dict.get("quotes", {}).get(f"{cur}RUB")
                if rate is None:
                    logger.warning("No rate in response for %s: %s", cur, content_dict)
                    rate = 0.0
            except (ValueError, TypeError) as exc:
                logger.error("Failed to parse currency response for %s: %s", cur, exc)
                rate = 0.0
        else:
            logger.error("Currency API error for %s: %s %s", cur, status_code, response.reason)
            rate = 0.0
        results.append({"currency": cur, "rate": rate})

    logger.info("Currency rates fetched: %s", results)
    return results


def get_stock_prices(stocks: List[str]) -> List[Dict[str, float]]:
    """
    Запрашивает цены акций.
    Возвращает список словарей: {"stock": "AAPL", "price": 150.12}
    """
    logger.info("Requesting stock prices for %s", stocks)

    results: List[Dict[str, float]] = []
    for s in stocks:
        url = "https://api.marketstack.com/v2/eod"
        try:
            response = requests.get(url, params={"access_key": f"{api_key_stock}", "symbols": f"{s}"})
        except requests.RequestException as exc:
            logger.error("Stock API request failed for %s: %s", s, exc)
            results.append({"stock": s, "price": 0.0})
            continue

        status_code = response.status_code
        if status_code == 200:
            try:
                content_dict = json.loads(response.text)
                data = content_dict.get("data") or []
                if not data:
                    logger.warning("Empty data in stock response for %s: %s", s, content_dict)
                    price = 0.0
                else:
                    price = data[0].get("close", 0.0)
            except (ValueError, TypeError) as exc:
                logger.error("Failed to parse stock response for %s: %s", s, exc)
                price = 0.0
        else:
            logger.error("Stock API error for %s: %s %s", s, status_code, response.reason)
            price = 0.0

        results.append({"stock": s, "price": price})

    logger.info("Stock prices fetched: %s", results)
    return results