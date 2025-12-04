import requests
from typing import Dict, List

def get_currency_rates(currencies: List[str]) -> List[Dict[str, float]]:
    """
    Заглушка для запроса курса валют.
    Здесь можно использовать любой реальный API.
    Возвращает список словарей: {"currency": "USD", "rate": 73.21}
    """
    # Пример "фейковых" данных — в реальном коде заменить на реальные запросы.

    results: List[Dict[str, float]] = []
    for cur in currencies:
        # В реальном сервисе вы бы делали запрос к API:
        # response = requests.get(...)
        # rate = response.json()...
        rate = 70.0  # заглушка
        results.append({"currency": cur, "rate": rate})
    return results


def get_stock_prices(stocks: List[str]) -> List[Dict[str, float]]:
    """
    Заглушка для запроса цен акций.
    Возвращает список словарей: {"stock": "AAPL", "price": 150.12}
    """
    results: List[Dict[str, float]] = []
    for s in stocks:
        price = 100.0  # заглушка
        results.append({"stock": s, "price": price})
    return results