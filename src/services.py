from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List
import logging
import math
import json

import pandas as pd

from .utils import PROJECT_ROOT

logger = logging.getLogger("services")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(PROJECT_ROOT / "logs" / "services.log", mode="w", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s : %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def analyze_cashback_categories(
    data: pd.DataFrame, year: int, month: int, rate: float = 0.05
) -> str:
    """
    Анализ выгодности категорий повышенного кэшбэка.

    data: DataFrame с транзакциями (как в utils.load_transactions)
    year, month: год и месяц, которые анализируем
    rate: ставка кэшбэка, по умолчанию 5%

    Возвращает JSON-строку вида:
        {"Супермаркеты": 123.45, "Фастфуд": 67.89, ...}
    """
    logger.info("analyze_cashback_categories started for %04d-%02d, rows=%d", year, month, len(data))

    # условно считаем, что кешбэк начисляется только на расходы (отрицательные суммы)
    df = data.copy()
    df["year"] = pd.to_datetime(df["Дата операции"]).dt.year
    df["month"] = pd.to_datetime(df["Дата операции"]).dt.month

    df_month = df[(df["year"] == year) & (df["month"] == month) & (df["Сумма операции"] < 0)].copy()
    if df_month.empty:
        logger.warning("No expenses for analyze_cashback_categories in %04d-%02d", year, month)
        return json.dumps({}, ensure_ascii=False)

    df_month["Расход"] = -df_month["Сумма операции"]

    grouped = df_month.groupby("Категория")["Расход"].sum().reset_index()
    grouped["cashback"] = grouped["Расход"] * rate

    result: Dict[str, float] = {}
    for _, row in grouped.iterrows():
        result[row["Категория"]] = float(round(row["cashback"], 2))

    logger.info("analyze_cashback_categories finished, categories=%d", len(result))
    return json.dumps(result, ensure_ascii=False)


def investment_bank(
    month: str,  # 'YYYY-MM'
    transactions: List[Dict[str, Any]],
    limit: int,  # 10, 50, 100
) -> str:
    """
    Рассчитывает сумму, которая попала бы в "Инвесткопилку".

    month: 'YYYY-MM'
    transactions: список словарей вида:
        {
            "Дата операции": "2023-01-15",
            "Сумма операции": -1712.0
        }
    limit: шаг округления (10, 50, 100)

    Возвращает JSON-строку с одним числом:
        {"total_invested": 123.45}
    """
    logger.info("investment_bank started for %s, tx_count=%d, limit=%d", month, len(transactions), limit)

    try:
        year, m = map(int, month.split("-"))
    except ValueError:
        logger.error("Invalid month format in investment_bank: %s", month)
        return json.dumps({"total_invested": 0.0}, ensure_ascii=False)

    def is_in_month(tx: Dict[str, Any]) -> bool:
        try:
            d = date.fromisoformat(tx["Дата операции"])
        except (KeyError, ValueError) as exc:
            logger.error("Bad transaction date in investment_bank: %s (%s)", tx, exc)
            return False
        return d.year == year and d.month == m

    def is_expense(tx: Dict[str, Any]) -> bool:
        return tx.get("Сумма операции", 0) < 0

    def rounding_diff(tx: Dict[str, Any]) -> float:
        amount = -tx.get("Сумма операции")
        rounded = math.ceil(amount / limit) * limit
        return rounded - amount

    tx_in_month = list(filter(is_in_month, transactions))
    tx_expenses = list(filter(is_expense, tx_in_month))
    diffs = list(map(rounding_diff, tx_expenses))

    total = float(round(sum(diffs), 2))
    payload = {"total_invested": total}
    logger.info(
        "investment_bank finished for %s: matched_tx=%d, expenses=%d, total=%.2f",
        month,
        len(tx_in_month),
        len(tx_expenses),
        total,
    )
    return json.dumps(payload, ensure_ascii=False)


def simple_search(transactions: pd.DataFrame, query: str) -> str:
    """
    Ищет query в 'Описание' или 'Категория' (регистр игнорируем).
    Возвращает JSON-строку со списком транзакций.
    """
    logger.info("simple_search started with query=%r, rows=%d", query, len(transactions))
    q = query.lower()

    def match(row_: pd.Series) -> bool:  # type: ignore[name-defined]
        return q in row_["Описание"].lower() or q in row_["Категория"].lower()

    mask = transactions.apply(match, axis=1)
    df_found = transactions[mask].copy()
    logger.info("simple_search found %d rows", len(df_found))

    result: List[Dict[str, Any]] = []
    for _, row in df_found.iterrows():
        result.append(
            {
                "date": row["Дата операции"].isoformat(),
                "amount": float(row["Сумма операции"]),
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )
    return json.dumps(result, ensure_ascii=False)


PHONE_PATTERN = re.compile(
    r"\+7\s?\d{3}\s?\d{3}-?\d{2}-?\d{2}"
)


def search_by_phone_numbers(transactions: pd.DataFrame) -> str:
    """
    Возвращает JSON-строку со всеми транзакциями, в описании которых есть мобильные номера вида:
    +7 921 11-22-33, +7 995 555-55-55 и т.п.
    """
    logger.info("search_by_phone_numbers started, rows=%d", len(transactions))

    def has_phone(desc: str) -> bool:
        return bool(PHONE_PATTERN.search(desc))

    mask = transactions["Описание"].astype(str).apply(has_phone)
    df_found = transactions[mask]
    logger.info("search_by_phone_numbers found %d rows", len(df_found))

    result: List[Dict[str, Any]] = []
    for _, row in df_found.iterrows():
        result.append(
            {
                "date": row["Дата операции"].isoformat(),
                "amount": float(row["Сумма операции"]),
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )
    return json.dumps(result, ensure_ascii=False)


NAME_PATTERN = re.compile(r"[А-ЯЁ][а-яё]+ [А-ЯЁ]\.")


def search_transfers_to_persons(transactions: pd.DataFrame) -> str:
    """
    Возвращает JSON-строку со всеми транзакциями:
    - Категория == 'Переводы'
    - в описании есть 'Имя И.' (русская буква + точка)
    """
    logger.info("search_transfers_to_persons started, rows=%d", len(transactions))

    df = transactions[transactions["Категория"] == "Переводы"].copy()
    logger.info("Filtered transfers, rows=%d", len(df))

    def has_name(desc: str) -> bool:
        return bool(NAME_PATTERN.search(desc))

    mask = df["Описание"].astype(str).apply(has_name)
    df_found = df[mask]
    logger.info("search_transfers_to_persons found %d rows", len(df_found))

    result: List[Dict[str, Any]] = []
    for _, row in df_found.iterrows():
        result.append(
            {
                "date": row["Дата операции"].isoformat(),
                "amount": float(row["Сумма операции"]),
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )
    return json.dumps(result, ensure_ascii=False)
