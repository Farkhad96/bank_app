from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from .utils import (
    load_transactions,
    load_user_settings,
    parse_datetime,
    get_date_range,
    filter_by_date_range,
    get_greeting,
    RangeKind
)
from .external_api import get_currency_rates, get_stock_prices


def _get_card_summary(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Для каждой карты считает:
    - общую сумму расходов (отрицательные суммы превращаем в положительные расходы)
    - кешбэк = 1 рубль за каждые 100 рублей расходов (floor)
    """
    # расходы считаем только по отрицательным суммам
    df_expenses = df[df["Сумма операции"] < 0].copy()
    if df_expenses.empty:
        return []

    df_expenses["Расход"] = -df_expenses["Сумма операции"]

    grouped = df_expenses.groupby("Карта")["Расход"].sum().reset_index()

    result: List[Dict[str, Any]] = []
    for _, row in grouped.iterrows():
        card = str(row["Карта"])
        last_digits = card[-4:] if len(card) >= 4 else card
        total_spent = float(round(row["Расход"], 2))
        cashback = round(total_spent / 100, 2)
        result.append(
            {
                "last_digits": last_digits,
                "total_spent": total_spent,
                "cashback": cashback,
            }
        )
    return result


def _get_top_transactions(df: pd.DataFrame, n: int = 5) -> List[Dict[str, Any]]:
    """
    Топ-n транзакций по модулю суммы.
    """
    if df.empty:
        return []

    df_tmp = df.copy()
    df_tmp["abs_amount"] = df_tmp["Сумма операции"].abs()
    df_top = df_tmp.sort_values("abs_amount", ascending=False).head(n)

    result: List[Dict[str, Any]] = []
    for _, row in df_top.iterrows():
        result.append(
            {
                "date": row["Дата операции"].strftime("%d.%m.%Y"),
                "amount": float(round(row["Сумма операции"], 2)),
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )
    return result


def get_main_page_data(dt_str: str) -> Dict[str, Any]:
    """
    Главная страница:
    - dt_str: 'YYYY-MM-DD HH:MM:SS'
    Возвращает словарь (который потом можно превратить в JSON).
    """
    dt: datetime = parse_datetime(dt_str)
    greeting = get_greeting(dt)

    df = load_transactions()
    start_date, end_date = get_date_range(dt.date(), "M")
    df_period = filter_by_date_range(df, start_date, end_date)

    cards = _get_card_summary(df_period)
    top_transactions = _get_top_transactions(df_period)

    settings = load_user_settings()
    currency_rates = get_currency_rates(settings.user_currencies)
    stock_prices = get_stock_prices(settings.user_stocks)

    return {
        "greeting": greeting,
        "cards": cards,
        "top_transactions": top_transactions,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }

def _aggregate_expenses(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Расходы:
    - total_amount: сумма расходов (целое, округление)
    - main: топ-7 категорий + 'Остальное'
    - transfers_and_cash: 'Наличные', 'Переводы'
    """
    # расходы — отрицательные суммы
    df_exp = df[df["Сумма операции"] < 0].copy()
    if df_exp.empty:
        return {
            "total_amount": 0,
            "main": [],
            "transfers_and_cash": [],
        }

    df_exp["amount_pos"] = -df_exp["Сумма операции"]

    # total
    total_amount = int(round(df_exp["amount_pos"].sum()))

    # main: группируем по категории
    grouped = (
        df_exp.groupby("Категория")["amount_pos"].sum().reset_index()
    )
    grouped = grouped.sort_values("amount_pos", ascending=False)

    top7 = grouped.head(7)
    others = grouped.iloc[7:]

    main_list: List[Dict[str, Any]] = []
    for _, row in top7.iterrows():
        main_list.append(
            {
                "category": row["Категория"],
                "amount": int(round(row["amount_pos"])),
            }
        )

    if not others.empty:
        others_sum = int(round(others["amount_pos"].sum()))
        main_list.append({"category": "Остальное", "amount": others_sum})

    # transfers_and_cash
    categories_tc = ["Наличные", "Переводы"]
    df_tc = df_exp[df_exp["Категория"].isin(categories_tc)]

    transfers_and_cash: List[Dict[str, Any]] = []
    if not df_tc.empty:
        grouped_tc = (
            df_tc.groupby("Категория")["amount_pos"].sum().reset_index()
        )
        grouped_tc = grouped_tc.sort_values("amount_pos", ascending=False)
        for _, row in grouped_tc.iterrows():
            transfers_and_cash.append(
                {
                    "category": row["Категория"],
                    "amount": int(round(row["amount_pos"])),
                }
            )

    return {
        "total_amount": total_amount,
        "main": main_list,
        "transfers_and_cash": transfers_and_cash,
    }


def _aggregate_income(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Поступления:
    - total_amount: сумма положительных операций
    - main: по категориям, по убыванию
    """
    df_inc = df[df["Сумма операции"] > 0].copy()
    if df_inc.empty:
        return {
            "total_amount": 0,
            "main": [],
        }

    df_inc["amount_pos"] = df_inc["Сумма операции"]

    total_amount = int(round(df_inc["amount_pos"].sum()))

    grouped = (
        df_inc.groupby("Категория")["amount_pos"].sum().reset_index()
    )
    grouped = grouped.sort_values("amount_pos", ascending=False)

    main_list: List[Dict[str, Any]] = []
    for _, row in grouped.iterrows():
        main_list.append(
            {
                "category": row["Категория"],
                "amount": int(round(row["amount_pos"])),
            }
        )

    return {
        "total_amount": total_amount,
        "main": main_list,
    }


def get_events_page_data(
    date_str: str,
    range_kind: RangeKind = "M",
) -> Dict[str, Any]:
    """
    Страница 'События':
    - date_str: 'YYYY-MM-DD' или 'YYYY-MM-DD HH:MM:SS'
    - range_kind: 'W' | 'M' | 'Y' | 'ALL'
    """
    # допускаем оба формата
    if " " in date_str:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    else:
        dt = datetime.strptime(date_str, "%Y-%m-%d")

    df = load_transactions()
    start_date, end_date = get_date_range(dt.date(), range_kind)
    df_period = filter_by_date_range(df, start_date, end_date)

    expenses = _aggregate_expenses(df_period)
    income = _aggregate_income(df_period)

    settings = load_user_settings()
    currency_rates = get_currency_rates(settings.user_currencies)
    stock_prices = get_stock_prices(settings.user_stocks)

    return {
        "expenses": expenses,
        "income": income,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }