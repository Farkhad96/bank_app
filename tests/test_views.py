import json
from datetime import date

import pandas as pd

from src import utils, views


class DummySettings(utils.UserSettings):
    pass


def _make_tx_df():
    return pd.DataFrame(
        {
            "Дата операции": [date(2023, 5, 1), date(2023, 5, 2), date(2023, 5, 3)],
            "Карта": ["1111222233334444", "5555666677778888", "5555666677778888"],
            "Сумма операции": [-100.0, -200.0, 300.0],
            "Категория": ["Супермаркеты", "Наличные", "Зарплата"],
            "Описание": ["Покупка", "Снятие", "Зарплата"],
        }
    )


def test_get_main_page_data(monkeypatch):
    # подмена загрузки транзакций
    monkeypatch.setattr(views, "load_transactions", lambda: _make_tx_df())

    # подмена настроек пользователя
    dummy_settings = DummySettings(user_currencies=["USD"], user_stocks=["AAPL"])

    monkeypatch.setattr(views, "load_user_settings", lambda: dummy_settings)

    # подмена внешних API
    monkeypatch.setattr(views, "get_currency_rates", lambda cur: [{"currency": cur[0], "rate": 73.21}])
    monkeypatch.setattr(views, "get_stock_prices", lambda st: [{"stock": st[0], "price": 150.0}])

    res_json = views.get_main_page_data("2023-05-02 10:00:00")
    data = json.loads(res_json)

    assert "greeting" in data
    assert data["cards"]
    assert data["top_transactions"]
    assert data["currency_rates"][0]["currency"] == "USD"
    assert data["stock_prices"][0]["stock"] == "AAPL"


def test_get_events_page_data_month(monkeypatch):
    monkeypatch.setattr(views, "load_transactions", lambda: _make_tx_df())

    dummy_settings = DummySettings(user_currencies=["USD"], user_stocks=["AAPL"])
    monkeypatch.setattr(views, "load_user_settings", lambda: dummy_settings)

    monkeypatch.setattr(views, "get_currency_rates", lambda cur: [{"currency": cur[0], "rate": 73.21}])
    monkeypatch.setattr(views, "get_stock_prices", lambda st: [{"stock": st[0], "price": 150.0}])

    res_json = views.get_events_page_data("2023-05-03", "M")
    data = json.loads(res_json)

    assert "expenses" in data
    assert "income" in data
    assert isinstance(data["expenses"]["total_amount"], int)
    assert isinstance(data["income"]["total_amount"], int)


def test_get_events_page_data_invalid_date():
    res_json = views.get_events_page_data("2023-13-01", "M")
    data = json.loads(res_json)
    assert data.get("error") == "invalid date"
