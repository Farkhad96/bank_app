import json
from datetime import date

import pandas as pd

from src import services


def test_analyze_cashback_categories_basic():
    df = pd.DataFrame(
        {
            "Дата операции": [date(2023, 5, 1), date(2023, 5, 2)],
            "Сумма операции": [-1000.0, -500.0],
            "Категория": ["Супермаркеты", "Фастфуд"],
            "Описание": ["Покупка", "Покупка"],
        }
    )
    res_json = services.analyze_cashback_categories(df, 2023, 5, rate=0.1)
    data = json.loads(res_json)
    assert data["Супермаркеты"] == 100.0
    assert data["Фастфуд"] == 50.0


def test_analyze_cashback_categories_no_expenses():
    df = pd.DataFrame(
        {
            "Дата операции": [date(2023, 5, 1)],
            "Сумма операции": [1000.0],
            "Категория": ["Зарплата"],
            "Описание": ["Поступление"],
        }
    )
    res_json = services.analyze_cashback_categories(df, 2023, 5)
    data = json.loads(res_json)
    assert data == {}


def test_investment_bank_ok():
    tx = [
        {"Дата операции": "2023-05-01", "Сумма операции": -1712.0},
        {"Дата операции": "2023-05-03", "Сумма операции": -50.0},
        {"Дата операции": "2023-06-01", "Сумма операции": -10.0},  # другой месяц
    ]
    res_json = services.investment_bank("2023-05", tx, limit=50)
    data = json.loads(res_json)
    assert "total_invested" in data
    assert data["total_invested"] > 0


def test_investment_bank_invalid_month():
    tx = [{"Дата операции": "bad-date", "Сумма операции": -100.0}]
    res_json = services.investment_bank("2023/05", tx, limit=10)
    data = json.loads(res_json)
    assert data["total_invested"] == 0.0


def _make_df_for_search():
    return pd.DataFrame(
        {
            "Дата операции": [date(2023, 5, 1), date(2023, 5, 2), date(2023, 5, 3)],
            "Сумма операции": [-100.0, -200.0, -300.0],
            "Категория": ["Супермаркеты", "Переводы", "Связь"],
            "Описание": [
                "Покупка продуктов",
                "Перевод Валерий А.",
                "Я МТС +7 921 111-22-33",
            ],
        }
    )


def test_simple_search():
    df = _make_df_for_search()
    res_json = services.simple_search(df, "продукт")
    data = json.loads(res_json)
    assert len(data) == 1
    assert data[0]["category"] == "Супермаркеты"


def test_search_by_phone_numbers():
    df = _make_df_for_search()
    res_json = services.search_by_phone_numbers(df)
    data = json.loads(res_json)
    assert len(data) == 1
    assert "+7 921 111-22-33" in data[0]["description"]


def test_search_transfers_to_persons():
    df = _make_df_for_search()
    res_json = services.search_transfers_to_persons(df)
    data = json.loads(res_json)
    assert len(data) == 1
    assert data[0]["category"] == "Переводы"
    assert "Валерий А." in data[0]["description"]
