import json
from datetime import date

import pandas as pd
import pytest

from src import services


@pytest.fixture
def df_cashback_cat() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Дата операции": [date(2023, 5, 1), date(2023, 5, 2)],
            "Сумма операции": [-1000.0, -500.0],
            "Категория": ["Супермаркеты", "Фастфуд"],
            "Описание": ["Покупка", "Покупка"],
            "Статус": ["OK", "OK"],
        }
    )


@pytest.fixture
def df_cashback_cat_no_exp() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Дата операции": [date(2023, 5, 1)],
            "Сумма операции": [1000.0],
            "Категория": ["Зарплата"],
            "Описание": ["Поступление"],
            "Статус": ["OK"],
        }
    )


@pytest.fixture
def tx_investment() -> list[dict]:
    return [
        {"Дата операции": "2023-05-01", "Сумма операции": -1712.0, "Статус": "OK"},
        {"Дата операции": "2023-05-03", "Сумма операции": -50.0, "Статус": "OK"},
        {"Дата операции": "2023-06-01", "Сумма операции": -10.0, "Статус": "OK"},  # другой месяц
    ]


@pytest.fixture
def tx_investment_bad() -> list[dict]:
    return [{"Дата операции": "bad-date", "Сумма операции": -100.0, "Статус": "OK"}]


def test_analyze_cashback_categories_basic(df_cashback_cat):
    res_json = services.analyze_cashback_categories(df_cashback_cat, 2023, 5, rate=0.1)
    data = json.loads(res_json)
    assert data["Супермаркеты"] == 100.0
    assert data["Фастфуд"] == 50.0


def test_analyze_cashback_categories_no_expenses(df_cashback_cat_no_exp):
    res_json = services.analyze_cashback_categories(df_cashback_cat_no_exp, 2023, 5)
    data = json.loads(res_json)
    assert data == {}


def test_investment_bank_ok(tx_investment):
    res_json = services.investment_bank("2023-05", tx_investment, limit=50)
    data = json.loads(res_json)
    assert "total_invested" in data
    assert data["total_invested"] > 0


def test_investment_bank_invalid_month(tx_investment_bad):
    res_json = services.investment_bank("2023/05", tx_investment_bad, limit=10)
    data = json.loads(res_json)
    assert data["total_invested"] == 0.0


@pytest.fixture
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
            "Статус": ["OK", "OK", "OK"],
        }
    )


def test_simple_search(_make_df_for_search):
    df = _make_df_for_search
    res_json = services.simple_search(df, "продукт")
    data = json.loads(res_json)
    assert len(data) == 1
    assert data[0]["category"] == "Супермаркеты"


def test_search_by_phone_numbers(_make_df_for_search):
    df = _make_df_for_search
    res_json = services.search_by_phone_numbers(df)
    data = json.loads(res_json)
    assert len(data) == 1
    assert "+7 921 111-22-33" in data[0]["description"]


def test_search_transfers_to_persons(_make_df_for_search):
    df = _make_df_for_search
    res_json = services.search_transfers_to_persons(df)
    data = json.loads(res_json)
    assert len(data) == 1
    assert data[0]["category"] == "Переводы"
    assert "Валерий А." in data[0]["description"]
