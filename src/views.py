from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
import json
import logging

import pandas as pd

from .utils import (
    load_transactions,
    load_user_settings,
    parse_datetime,
    get_date_range,
    filter_by_date_range,
    get_greeting,
    RangeKind,
    PROJECT_ROOT,
)
from .external_api import get_currency_rates, get_stock_prices

logger = logging.getLogger("views")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(PROJECT_ROOT / "logs" / "views.log", mode="w", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s : %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def _get_card_summary(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Для каждой карты считает:
    - общую сумму расходов
    - кешбэк = 1 рубль за каждые 100 рублей расходов
    """
    logger.info("_get_card_summary called, rows=%d", len(df))
    # расходы считаем только по отрицательным суммам
    df_expenses = df[df["Сумма операции"] < 0].copy()
    if df_expenses.empty:
        logger.info("_get_card_summary: no expenses in period")
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
    logger.info("_get_card_summary finished, cards=%d", len(result))
    return result


def _get_top_transactions(df: pd.DataFrame, n: int = 5) -> List[Dict[str, Any]]:
    """
    Топ-n транзакций по модулю суммы.
    """
    logger.info("_get_top_transactions called, rows=%d, n=%d", len(df), n)
    if df.empty:
        logger.info("_get_top_transactions: empty dataframe")
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
    logger.info("_get_top_transactions finished, returned=%d", len(result))
    return result


def get_main_page_data(dt_str: str) -> str:
    """
    Главная страница:
    - dt_str: 'YYYY-MM-DD HH:MM:SS'
    Возвращает JSON-строку с данными для главной страницы.
    """
    logger.info("get_main_page_data called with dt_str=%r", dt_str)
    dt: datetime = parse_datetime(dt_str)
    greeting = get_greeting(dt)

    df = load_transactions()
    logger.info("Transactions loaded: %d rows", len(df))
    start_date, end_date = get_date_range(dt.date(), "M")
    df_period = filter_by_date_range(df, start_date, end_date)
    logger.info("Filtered period %s-%s, rows=%d", start_date, end_date, len(df_period))

    cards = _get_card_summary(df_period)
    top_transactions = _get_top_transactions(df_period)

    settings = load_user_settings()
    currency_rates = get_currency_rates(settings.user_currencies)
    stock_prices = get_stock_prices(settings.user_stocks)

    payload: Dict[str, Any] = {
        "greeting": greeting,
        "cards": cards,
        "top_transactions": top_transactions,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }
    logger.info(
        "get_main_page_data finished: cards=%d, top_tx=%d, currencies=%d, stocks=%d",
        len(cards),
        len(top_transactions),
        len(currency_rates),
        len(stock_prices),
    )
    return json.dumps(payload, ensure_ascii=False)


def _aggregate_expenses(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Расходы:
    - total_amount
    - main
    - transfers_and_cash
    """
    logger.info("_aggregate_expenses called, rows=%d", len(df))
    # расходы — отрицательные суммы
    df_exp = df[df["Сумма операции"] < 0].copy()
    if df_exp.empty:
        logger.info("_aggregate_expenses: no expenses")
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

    result = {
        "total_amount": total_amount,
        "main": main_list,
        "transfers_and_cash": transfers_and_cash,
    }
    logger.info(
        "_aggregate_expenses finished: total=%d, main_len=%d, transfers_len=%d",
        total_amount,
        len(main_list),
        len(transfers_and_cash),
    )
    return result


def _aggregate_income(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Поступления:
    - total_amount
    - main
    """
    logger.info("_aggregate_income called, rows=%d", len(df))
    df_inc = df[df["Сумма операции"] > 0].copy()
    if df_inc.empty:
        logger.info("_aggregate_income: no income")
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

    result = {
        "total_amount": total_amount,
        "main": main_list,
    }
    logger.info("_aggregate_income finished: total=%d, main_len=%d", total_amount, len(main_list))
    return result


def get_events_page_data(
    date_str: str,
    range_kind: RangeKind = "M",
) -> str:
    """
    Страница 'События'.
    """
    logger.info("get_events_page_data called with date_str=%r, range_kind=%s", date_str, range_kind)
    try:
        if " " in date_str:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        logger.error("Invalid date_str in get_events_page_data: %r (%s)", date_str, exc)
        return json.dumps({"error": "invalid date"}, ensure_ascii=False)

    df = load_transactions()
    logger.info("Transactions loaded: %d rows", len(df))
    start_date, end_date = get_date_range(dt.date(), range_kind)
    df_period = filter_by_date_range(df, start_date, end_date)
    logger.info("Filtered period %s-%s, rows=%d", start_date, end_date, len(df_period))

    expenses = _aggregate_expenses(df_period)
    income = _aggregate_income(df_period)

    settings = load_user_settings()
    currency_rates = get_currency_rates(settings.user_currencies)
    stock_prices = get_stock_prices(settings.user_stocks)

    payload: Dict[str, Any] = {
        "expenses": expenses,
        "income": income,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }
    logger.info(
        "get_events_page_data finished: expenses_total=%s, income_total=%s, currencies=%d, stocks=%d",
        expenses.get("total_amount"),
        income.get("total_amount"),
        len(currency_rates),
        len(stock_prices),
    )
    return json.dumps(payload, ensure_ascii=False)
