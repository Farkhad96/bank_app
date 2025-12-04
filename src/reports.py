import logging
from typing import Any

import pandas as pd

from .utils import PROJECT_ROOT

logger = logging.getLogger("reports")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(PROJECT_ROOT / "logs" / "reports.log", mode="w", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s : %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def report_expenses_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    Возвращает DataFrame:
        Категория | Сумма_расходов
    где Сумма_расходов - положительная величина (по модулю расходов).
    """
    logger.info("Building report_expenses_by_category, rows=%d", len(df))
    df_exp = df[df["Сумма операции"] < 0].copy()
    if df_exp.empty:
        logger.info("No expense data for report_expenses_by_category")
        return pd.DataFrame(columns=["Категория", "Сумма_расходов"])

    df_exp["Расход"] = -df_exp["Сумма операции"]
    grouped = df_exp.groupby("Категория")["Расход"].sum().reset_index()
    grouped = grouped.rename(columns={"Расход": "Сумма_расходов"})
    result = grouped.sort_values("Сумма_расходов", ascending=False)
    logger.info("report_expenses_by_category built, categories=%d", len(result))
    return result


def report_expenses_by_weekday(df: pd.DataFrame) -> pd.DataFrame:
    """
    Возвращает DataFrame:
        День_недели | Сумма_расходов
    День_недели: 0 - Понедельник, ..., 6 - Воскресенье
    """
    logger.info("Building report_expenses_by_weekday, rows=%d", len(df))
    df_exp = df[df["Сумма операции"] < 0].copy()
    if df_exp.empty:
        logger.info("No expense data for report_expenses_by_weekday")
        return pd.DataFrame(columns=["День_недели", "Сумма_расходов"])

    df_exp["Расход"] = -df_exp["Сумма операции"]
    df_exp["День_недели"] = pd.to_datetime(df_exp["Дата операции"]).dt.weekday

    grouped = df_exp.groupby("День_недели")["Расход"].sum().reset_index()
    grouped = grouped.rename(columns={"Расход": "Сумма_расходов"})
    result = grouped.sort_values("День_недели")
    logger.info("report_expenses_by_weekday built, days=%d", len(result))
    return result


def report_expenses_workday_vs_weekend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Возвращает DataFrame:
        Тип_дня | Сумма_расходов
    где Тип_дня: 'Рабочий', 'Выходной'
    """
    logger.info("Building report_expenses_workday_vs_weekend, rows=%d", len(df))
    df_exp = df[df["Сумма операции"] < 0].copy()
    if df_exp.empty:
        logger.info("No expense data for report_expenses_workday_vs_weekend")
        return pd.DataFrame(columns=["Тип_дня", "Сумма_расходов"])

    df_exp["Расход"] = -df_exp["Сумма операции"]
    weekdays = pd.to_datetime(df_exp["Дата операции"]).dt.weekday
    df_exp["Тип_дня"] = weekdays.apply(lambda d: "Выходной" if d >= 5 else "Рабочий")

    grouped = df_exp.groupby("Тип_дня")["Расход"].sum().reset_index()
    grouped = grouped.rename(columns={"Расход": "Сумма_расходов"})
    logger.info("report_expenses_workday_vs_weekend built")
    return grouped
