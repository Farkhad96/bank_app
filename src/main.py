from __future__ import annotations

import json
from datetime import datetime, date

import pandas as pd

import src.utils as utils
import src.views as views
import src.reports as reports
import src.services as services
import src.external_api as external_api


def main() -> None:
    # 1. Загрузка транзакций из `data/operations.xlsx`
    df: pd.DataFrame = utils.load_transactions()
    print("Loaded transactions:", len(df))

    # 2. Загрузка пользовательских настроек
    settings = utils.load_user_settings()
    print("User currencies:", settings.user_currencies)
    print("User stocks:", settings.user_stocks)

    # 3. Главная страница — жёстко задаём дату в диапазоне данных (31.12.2021)
    now_str = "2021-12-31 12:00:00"
    main_page_json = views.get_main_page_data(now_str)
    main_page = json.loads(main_page_json)
    print("\n=== Main page data ===")
    print(json.dumps(main_page, ensure_ascii=False, indent=2))

    # 4. Страница `События` — тоже используем последнюю дату из файла
    today_str = "2021-12-31"
    for kind in ["W", "M", "Y", "ALL"]:
        events_json = views.get_events_page_data(today_str, range_kind=kind)  # type: ignore[arg-type]
        events = json.loads(events_json)
        print(f"\n=== Events page ({kind}) ===")
        print(json.dumps(events, ensure_ascii=False, indent=2))

    # 5. Отчёты — ограничим датафрейм периодом до 31.12.2021 (на случай будущих данных)
    cutoff_date = date(2021, 12, 31)
    df_cut = df[df["Дата операции"] <= cutoff_date]

    expenses_by_cat_json = reports.report_expenses_by_category(df_cut)
    print("\n=== report_expenses_by_category ===")
    print(json.dumps(json.loads(expenses_by_cat_json), ensure_ascii=False, indent=2))

    expenses_by_weekday_json = reports.report_expenses_by_weekday(df_cut)
    print("\n=== report_expenses_by_weekday ===")
    print(json.dumps(json.loads(expenses_by_weekday_json), ensure_ascii=False, indent=2))

    expenses_work_vs_weekend_json = reports.report_expenses_workday_vs_weekend(df_cut)
    print("\n=== report_expenses_workday_vs_weekend ===")
    print(json.dumps(json.loads(expenses_work_vs_weekend_json), ensure_ascii=False, indent=2))

    # 8. Анализ категорий повышенного кешбэка — месяц и год последней транзакции
    cashback_json = services.analyze_cashback_categories(df, 2021, 12, rate=0.05)
    print("\n=== analyze_cashback_categories ===")
    print(json.dumps(json.loads(cashback_json), ensure_ascii=False, indent=2))

    # 9. Инвесткопилка — месяц 2021-12
    tx_list = [
        {
            "Дата операции": str(row["Дата операции"]),
            "Сумма операции": float(row["Сумма операции"]),
        }
        for _, row in df.iterrows()
        if row["Дата операции"] <= cutoff_date
    ]
    month_str = "2021-12"
    invest_json = services.investment_bank(month_str, tx_list, limit=100)
    print("\n=== investment_bank ===")
    print(json.dumps(json.loads(invest_json), ensure_ascii=False, indent=2))

    # 10–12. Сервисы поиска — тоже используем df_cut
    simple_search_json = services.simple_search(df_cut, "магазин")
    print("\n=== simple_search(\"магазин\") ===")
    print(json.dumps(json.loads(simple_search_json), ensure_ascii=False, indent=2))

    phone_search_json = services.search_by_phone_numbers(df_cut)
    print("\n=== search_by_phone_numbers ===")
    print(json.dumps(json.loads(phone_search_json), ensure_ascii=False, indent=2))

    transfers_json = services.search_transfers_to_persons(df_cut)
    print("\n=== search_transfers_to_persons ===")
    print(json.dumps(json.loads(transfers_json), ensure_ascii=False, indent=2))

    # 13. Прямой вызов внешних API — оставляем без изменений
    if settings.user_currencies:
        direct_rates = external_api.get_currency_rates(settings.user_currencies)
        print("\n=== direct get_currency_rates ===")
        print(json.dumps(direct_rates, ensure_ascii=False, indent=2))

    if settings.user_stocks:
        direct_stocks = external_api.get_stock_prices(settings.user_stocks)
        print("\n=== direct get_stock_prices ===")
        print(json.dumps(direct_stocks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
