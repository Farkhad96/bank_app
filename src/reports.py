import functools
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .utils import PROJECT_ROOT

logger = logging.getLogger("reports")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(PROJECT_ROOT / "logs" / "reports.log", mode="w", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s : %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def report_to_file(_func: Any = None, *, filename: str = None) -> Any:
    """
    Декоратор для функций-отчетов.

    `@report_to_file` — пишет результат в файл с именем по умолчанию.
    `@report_to_file(filename="my_report.csv")` — пишет в указанный файл.
    """

    def decorator_report(func) -> Any:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)

            if not isinstance(result, str):
                logger.warning(
                    "report_to_file: function %s did not return JSON string, got %s",
                    func.__name__,
                    type(result),
                )
                return result

            reports_dir: Path = PROJECT_ROOT / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                default_name = f"{func.__name__}_{timestamp}.json"
                file_path = reports_dir / default_name
            else:
                file_path = reports_dir / filename

            try:
                with file_path.open("w", encoding="utf-8") as f:
                    f.write(result)
                logger.info(
                    "Report from %s saved to %s (len=%d)",
                    func.__name__,
                    file_path,
                    len(result),
                )
            except OSError as exc:
                logger.error(
                    "Failed to save report %s to %s: %s",
                    func.__name__,
                    file_path,
                    exc,
                )

            return result

        return wrapper

    if _func is not None and callable(_func):
        return decorator_report(_func)

    return decorator_report


@report_to_file
def report_expenses_by_category(df: pd.DataFrame) -> str:
    """
    Возвращает JSON-строку:
    [
      {"Категория": "...", "Сумма_расходов": 1234.56},
      ...
    ]
    где Сумма_расходов - положительная величина (по модулю расходов).
    """
    logger.info("Building report_expenses_by_category, rows=%d", len(df))
    df_exp = df[df["Сумма операции"] < 0].copy()
    if df_exp.empty:
        logger.info("No expense data for report_expenses_by_category")
        return json.dumps([], ensure_ascii=False)

    df_exp["Расход"] = -df_exp["Сумма операции"]
    grouped = df_exp.groupby("Категория")["Расход"].sum().reset_index()
    grouped = grouped.rename(columns={"Расход": "Сумма_расходов"})
    result_df = grouped.sort_values("Сумма_расходов", ascending=False)
    logger.info("report_expenses_by_category built, categories=%d", len(result_df))

    result_list = result_df.to_dict(orient="records")
    return json.dumps(result_list, ensure_ascii=False)


@report_to_file
def report_expenses_by_weekday(df: pd.DataFrame) -> str:
    """
    Возвращает JSON-строку:
    [
      {"День_недели": "Понедельник", "Сумма_расходов": 1000.0},
      ...
    ]
    День_недели: Понедельник, ..., Воскресенье
    """
    logger.info("Building report_expenses_by_weekday, rows=%d", len(df))
    df_exp = df[df["Сумма операции"] < 0].copy()
    if df_exp.empty:
        logger.info("No expense data for report_expenses_by_weekday")
        return json.dumps([], ensure_ascii=False)

    df_exp["Расход"] = -df_exp["Сумма операции"]

    # вычисляем номер дня недели и маппим в русские названия
    weekday_series = pd.to_datetime(df_exp["Дата операции"]).dt.weekday
    weekday_map = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }
    df_exp["День_недели"] = weekday_series.map(weekday_map)

    grouped = df_exp.groupby("День_недели")["Расход"].sum().reset_index()
    grouped = grouped.rename(columns={"Расход": "Сумма_расходов"})

    # сортируем по порядку дней недели, а не по алфавиту
    sort_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    grouped["__order"] = grouped["День_недели"].apply(sort_order.index)
    result_df = grouped.sort_values("__order").drop(columns="__order")

    logger.info("report_expenses_by_weekday built, days=%d", len(result_df))

    result_list = result_df.to_dict(orient="records")
    return json.dumps(result_list, ensure_ascii=False)


@report_to_file
def report_expenses_workday_vs_weekend(df: pd.DataFrame) -> str:
    """
    Возвращает JSON-строку:
    [
      {"Тип_дня": "Рабочий", "Сумма_расходов": 1234.5},
      {"Тип_дня": "Выходной", "Сумма_расходов": 567.8}
    ]
    """
    logger.info("Building report_expenses_workday_vs_weekend, rows=%d", len(df))
    df_exp = df[df["Сумма операции"] < 0].copy()
    if df_exp.empty:
        logger.info("No expense data for report_expenses_workday_vs_weekend")
        return json.dumps([], ensure_ascii=False)

    df_exp["Расход"] = -df_exp["Сумма операции"]
    weekdays = pd.to_datetime(df_exp["Дата операции"]).dt.weekday
    df_exp["Тип_дня"] = weekdays.apply(lambda d: "Выходной" if d >= 5 else "Рабочий")

    grouped = df_exp.groupby("Тип_дня")["Расход"].sum().reset_index()
    grouped = grouped.rename(columns={"Расход": "Сумма_расходов"})
    result_df = grouped.sort_values("Тип_дня")
    logger.info("report_expenses_workday_vs_weekend built, types=%d", len(result_df))

    result_list = result_df.to_dict(orient="records")
    return json.dumps(result_list, ensure_ascii=False)
