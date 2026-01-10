from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Literal, Tuple

import pandas as pd

from .find_project_root import find_project_root

# Константы путей
PROJECT_ROOT = find_project_root()
DATA_DIR = PROJECT_ROOT / "data"
SETTINGS_PATH = PROJECT_ROOT / "user_settings.json"


@dataclass
class UserSettings:
    user_currencies: List[str]
    user_stocks: List[str]


# Логгер
logger = logging.getLogger("utils")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(PROJECT_ROOT / "logs" / "utils.log", mode="w", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s : %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def load_transactions(path: Path | None = None) -> pd.DataFrame:
    """
    Чтение Excel с транзакциями.
    Ожидаемые колонки: 'Дата операции', 'Карта', 'Сумма операции', 'Категория', 'Описание'
    """
    path = path or (DATA_DIR / "operations.xlsx")
    logger.info("Loading transactions from %s", path)
    df = pd.read_excel(path)

    # Приводим к нужным типам
    # Сначала пробуем ожидаемый формат, если не получилось — падаем обратно на автоопределение
    try:
        df["Дата операции"] = pd.to_datetime(
            df["Дата операции"],
            format="%d.%m.%Y %H:%M:%S",
            errors="raise",
        ).dt.date
    except ValueError:
        df["Дата операции"] = pd.to_datetime(
            df["Дата операции"],
            dayfirst=True,
            errors="raise",
        ).dt.date

    df["Сумма операции"] = df["Сумма операции"].astype(float)
    df["Категория"] = df["Категория"].astype(str)
    df["Описание"] = df["Описание"].astype(str)
    if "Карта" in df.columns:
        df["Карта"] = df["Карта"].astype(str)

    logger.info("Loaded %d transactions", len(df))
    return df


def load_user_settings(path: Path | None = None) -> UserSettings:
    path = path or SETTINGS_PATH
    logger.info("Loading user settings from %s", path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    settings = UserSettings(
        user_currencies=data.get("user_currencies", []),
        user_stocks=data.get("user_stocks", []),
    )
    logger.info(
        "User settings loaded: currencies=%s, stocks=%s",
        settings.user_currencies,
        settings.user_stocks,
    )
    return settings


def parse_datetime(dt_str: str) -> datetime:
    """
    Строка формата 'YYYY-MM-DD HH:MM:SS' -> datetime
    """
    logger.info("Parsing datetime string %r", dt_str)
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")


RangeKind = Literal["W", "M", "Y", "ALL"]


def get_date_range(target_date: date, range_kind: RangeKind = "M") -> Tuple[date, date]:
    """
    Вернуть (start_date, end_date) в зависимости от диапазона:
    - W: неделя, в которую входит target_date (с понедельника по воскресенье)
    - M: месяц (с 1-го числа)
    - Y: год (с 1 января)
    - ALL: с минимально возможной даты до target_date
    """
    logger.info("Calculating date range for %s with kind=%s", target_date, range_kind)
    if range_kind == "W":
        # понедельник текущей недели
        start = target_date - timedelta(days=target_date.weekday())
        end = target_date
    elif range_kind == "M":
        start = target_date.replace(day=1)
        end = target_date
    elif range_kind == "Y":
        start = target_date.replace(month=1, day=1)
        end = target_date
    elif range_kind == "ALL":
        start = date(1970, 1, 1)
        end = target_date
    else:
        logger.error("Unknown range_kind: %s", range_kind)
        raise ValueError(f"Unknown range_kind: {range_kind}")

    logger.info("Date range calculated: %s - %s", start, end)
    return start, end


def filter_by_date_range(
    df: pd.DataFrame,
    start_date: date,
    end_date: date,
    date_col: str = "Дата операции",
) -> pd.DataFrame:
    logger.info(
        "Filtering dataframe by date range %s - %s, rows_before=%d",
        start_date,
        end_date,
        len(df),
    )
    mask = (df[date_col] >= start_date) & (df[date_col] <= end_date)
    result = df.loc[mask].copy()
    logger.info("Filtering finished, rows_after=%d", len(result))
    return result


def get_greeting(dt: datetime) -> str:
    """
    Возвращает приветствие на русском:
    - 05:00–11:59 — Доброе утро
    - 12:00–16:59 — Добрый день
    - 17:00–22:59 — Добрый вечер
    - 23:00–04:59 — Доброй ночи
    """
    hour = dt.hour
    if 5 <= hour < 12:
        greeting = "Доброе утро"
    elif 12 <= hour < 17:
        greeting = "Добрый день"
    elif 17 <= hour < 23:
        greeting = "Добрый вечер"
    else:
        greeting = "Доброй ночи"
    logger.info("Greeting for %s is %r", dt, greeting)
    return greeting
