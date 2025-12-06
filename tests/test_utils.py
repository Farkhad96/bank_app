import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from src import utils

@pytest.fixture
def df_src() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Дата операции": ["2023-05-01", "2023-05-02"],
            "Карта": ["1111222233334444", "5555666677778888"],
            "Сумма операции": [-10.5, 20],
            "Категория": ["Супермаркеты", "Переводы"],
            "Описание": ["Покупка", "Перевод"],
            "Статус": ["OK", "OK"]
        }
    )

@pytest.fixture
def sample_df() -> pd.DataFrame:
    return  pd.DataFrame(
        {
            "Дата операции": [date(2023, 5, 1),
                              date(2023, 5, 10),
                              date(2023, 6, 1)],
            "value": [1, 2, 3],
        }
    )

@pytest.fixture
def settings_sample() -> dict:
    return {"user_currencies": ["USD"], "user_stocks": ["AAPL", "TSLA"]}

def test_parse_datetime_ok():
    dt = utils.parse_datetime("2023-05-01 12:34:56")
    assert isinstance(dt, datetime)
    assert dt.year == 2023
    assert dt.month == 5
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.minute == 34
    assert dt.second == 56


@pytest.mark.parametrize(
    "hour,expected",
    [
        (6, "Доброе утро"),
        (13, "Добрый день"),
        (18, "Добрый вечер"),
        (2, "Доброй ночи"),
    ],
)
def test_get_greeting(hour, expected):
    dt = datetime(2023, 1, 1, hour, 0, 0)
    assert utils.get_greeting(dt) == expected


@pytest.mark.parametrize(
    "kind,expected_start,expected_end",
    [
        ("M", date(2023, 5, 1), date(2023, 5, 20)),
        ("Y", date(2023, 1, 1), date(2023, 5, 20)),
        ("ALL", date(1970, 1, 1), date(2023, 5, 20)),
        ("W", None, None),  # отдельно проверим диапазон недели
    ],
)
def test_get_date_range(kind, expected_start, expected_end):
    target = date(2023, 5, 20)
    start, end = utils.get_date_range(target, kind)
    if kind == "W":
        # понедельник той же недели и сама дата
        assert start.weekday() == 0
        assert end == target
    else:
        assert start == expected_start
        assert end == expected_end


def test_get_date_range_invalid_kind():
    with pytest.raises(ValueError):
        utils.get_date_range(date(2023, 1, 1), "X")  # type: ignore[arg-type]

def test_filter_by_date_range(sample_df):
    start, end = date(2023, 5, 1), date(2023, 5, 31)
    filtered = utils.filter_by_date_range(sample_df, start, end)
    assert len(filtered) == 2
    assert filtered["value"].tolist() == [1, 2]

def test_load_user_settings_tmp(tmp_path, monkeypatch,settings_sample):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps(settings_sample, ensure_ascii=False), encoding="utf-8")

    # подменяем SETTINGS_PATH
    monkeypatch.setattr(utils, "SETTINGS_PATH", settings_file)

    settings = utils.load_user_settings()
    assert settings.user_currencies == ["USD"]
    assert settings.user_stocks == ["AAPL", "TSLA"]


def test_load_transactions_minimal(tmp_path, monkeypatch,df_src):
    xlsx_path = tmp_path / "operations.xlsx"
    df_src.to_excel(xlsx_path, index=False)

    # подменяем DATA_DIR, чтобы load_transactions читал наш файл
    monkeypatch.setattr(utils, "DATA_DIR", Path(tmp_path))

    df = utils.load_transactions()
    assert len(df) == 2
    assert df["Сумма операции"].dtype.kind in ("f",)  # float
    assert str(df.loc[0, "Категория"]) == "Супермаркеты"
