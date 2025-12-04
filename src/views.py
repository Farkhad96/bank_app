from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from .external_api import get_currency_rates, get_stock_prices
from .utils import (PROJECT_ROOT, RangeKind, filter_by_date_range, get_date_range, get_greeting, load_transactions,
                    load_user_settings, parse_datetime)

logger = logging.getLogger("views")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(PROJECT_ROOT / "logs" / "views.log", mode="w", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s : %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def _get_card_summary(df_period: pd.DataFrame) -> list[dict[str, object]]:
    """
    Агрегация расходов по картам для выбранного периода.
    Возвращает список словарей с полями:
    * `card`
    * `total_expense`
    """
    # фильтруем только расходы (отрицательные суммы)
    df_expenses = df_period[df_period["Сумма операции"] < 0].copy()

    # если нет колонки `Карта` или нет расходов, возвращаем пустой список
    if "Карта" not in df_expenses.columns or df_expenses.empty:
        return []

    # нормализуем название карты в строку, чтобы избежать проблем с типами
    df_expenses["Карта"] = df_expenses["Карта"].astype(str)

    # группируем по карте и считаем сумму расходов (по модулю)
    df_expenses["Расход"] = df_expenses["Сумма операции"].abs()
    grouped = df_expenses.groupby("Карта")["Расход"].sum().reset_index()

    # сортировка по сумме расходов по убыванию
    grouped = grouped.sort_values("Расход", ascending=False)

    # приведение к формату для JSON
    result: list[dict[str, object]] = [
        {
            "card": row["Карта"],
            "total_expense": float(row["Расход"]),
        }
        for _, row in grouped.iterrows()
    ]
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
    grouped = df_exp.groupby("Категория")["amount_pos"].sum().reset_index()
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
        grouped_tc = df_tc.groupby("Категория")["amount_pos"].sum().reset_index()
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

    grouped = df_inc.groupby("Категория")["amount_pos"].sum().reset_index()
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
