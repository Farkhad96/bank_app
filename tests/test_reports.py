import json
from datetime import date

import pandas as pd

from src import reports, utils


def _make_df():
    return pd.DataFrame(
        {
            "Дата операции": [date(2023, 5, 1), date(2023, 5, 2), date(2023, 5, 3)],
            "Сумма операции": [-100.0, -50.0, 200.0],
            "Категория": ["Супермаркеты", "Наличные", "Зарплата"],
            "Описание": ["Покупка 1", "Снятие", "Поступление"],
            "Статус": ["OK", "OK", "OK"],
        }
    )


def test_report_expenses_by_category_json_and_content(tmp_path, monkeypatch):
    df = _make_df()

    # перенаправляем PROJECT_ROOT, чтобы отчёт сохранился в tmp_path
    monkeypatch.setattr(utils, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(reports, "PROJECT_ROOT", tmp_path)

    result_json = reports.report_expenses_by_category(df)
    data = json.loads(result_json)
    assert isinstance(data, list)
    assert any(row["Категория"] == "Супермаркеты" for row in data)

    # проверяем, что файл отчёта создан
    reports_dir = tmp_path / "reports"
    saved_files = list(reports_dir.glob("report_expenses_by_category_*.json"))
    assert saved_files, "отчётный файл не создан"


def test_report_expenses_by_weekday(tmp_path, monkeypatch):
    df = _make_df()

    monkeypatch.setattr(utils, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(reports, "PROJECT_ROOT", tmp_path)

    result_json = reports.report_expenses_by_weekday(df)
    data = json.loads(result_json)
    assert isinstance(data, list)
    # проверяем наличие нужных ключей
    assert all("День_недели" in row and "Сумма_расходов" in row for row in data)
    # и то, что день недели — строковое имя, а не номер
    valid_names = {
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота",
        "Воскресенье",
    }
    assert {row["День_недели"] for row in data}.issubset(valid_names)


def test_report_expenses_workday_vs_weekend(tmp_path, monkeypatch):
    df = _make_df()

    monkeypatch.setattr(utils, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(reports, "PROJECT_ROOT", tmp_path)

    result_json = reports.report_expenses_workday_vs_weekend(df)
    data = json.loads(result_json)
    assert isinstance(data, list)
    assert {row["Тип_дня"] for row in data}.issubset({"Рабочий", "Выходной"})


def test_report_decorator_custom_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(reports, "PROJECT_ROOT", tmp_path)

    @reports.report_to_file(filename="custom_report.json")
    def dummy_report():
        return json.dumps({"a": 1}, ensure_ascii=False)

    res = dummy_report()
    assert json.loads(res) == {"a": 1}
    assert (tmp_path / "reports" / "custom_report.json").is_file()
