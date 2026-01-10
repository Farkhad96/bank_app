# Bank App

Приложение для анализа личных банковских операций. Читает выгрузку из банка из `data/operations.xlsx`, строит отчёты по расходам и доходам, формирует данные для страниц «Главная» и «События», а также запрашивает курсы валют и цены акций через внешние API. Находится в активной разработке.

## Содержание

- [Использование](#использование)
- [Разработка](#разработка)
- [Тестирование](#тестирование)
- [FAQ](#faq)
- [To do](#to-do)
- [Команда проекта](#команда-проекта)
- [Источники](#источники)

## Использование

### Установка

1\. Клонировать репозиторий

`git clone git@github.com:Farkhad96/bank-app.git`  
`cd bank-app`

2\. Создать виртуальное окружение

Для Windows \(PowerShell\):

`python -m venv .venv`  
`.venv\Scripts\activate`

3\. Установить зависимости через `poetry`

`pip install poetry`  
`poetry install`

4\. Настроить переменные окружения

Скопируйте файл `\.env_template` в `\.env` и укажите свои ключи API:

```bash
cp .env_template .env
```

Отредактируйте `\.env` и заполните `API_KEY` и `API_KEY_STOCK`.

5\. Подготовить входные данные

Положите Excel\-файл с операциями в каталог `data` под именем `operations.xlsx`. Ожидаемые столбцы:

- `Дата операции`
- `Карта` \(опционально\)
- `Сумма операции`
- `Категория`
- `Описание`

### Примеры использования

#### Запуск основного сценария

```python
from src.main import main

if __name__ == "__main__":
    main()
```

При запуске `python -m src.main` в консоль выводятся:

- количество загруженных транзакций;
- данные для главной страницы \(JSON\);
- отчёты по расходам;
- результаты работы сервисов поиска;
- результаты прямых вызовов к API курсов валют и акций.

#### Загрузка транзакций

```python
from src import utils

df = utils.load_transactions()
print(len(df), df.columns)
```

#### Получение данных для главной страницы

```python
from src import views

data_json = views.get_main_page_data("2023-05-02 10:00:00")
print(data_json)
```

#### Страница `События`

```python
from src import views

events_json = views.get_events_page_data("2023-05-03", "M")
print(events_json)
```

#### Анализ кэшбэка

```python
from src import utils, services

df = utils.load_transactions()
cashback_json = services.analyze_cashback_categories(df, 2023, 5, rate=0.05)
print(cashback_json)
```

#### Инвесткопилка

```python
from datetime import date
from src import utils, services

df = utils.load_transactions()
cutoff = date(2023, 5, 31)

tx_list = [
    {
        "Дата операции": str(row["Дата операции"]),
        "Сумма операции": float(row["Сумма операции"]),
    }
    for _, row in df.iterrows()
    if row["Дата операции"] <= cutoff
]

invest_json = services.investment_bank("2023-05", tx_list, limit=100)
print(invest_json)
```

## Разработка

### Требования

- Python \>= 3\.13,\ < 4\.0
- `poetry` для управления зависимостями

Основные зависимости указаны в `pyproject.toml`:

- `pandas`
- `openpyxl`
- `requests`
- `python-dotenv`
- `pytest`, `pytest-cov` для тестов
- линтеры и форматтеры: `flake8`, `black`, `mypy`, `isort`

### Структура проекта

- `src/utils.py` — утилиты: загрузка транзакций, диапазоны дат, приветствия, пользовательские настройки
- `src/views.py` — подготовка JSON для страниц «Главная» и «События»
- `src/reports.py` — отчёты по расходам, декоратор `report_to_file` \(сохранение отчётов в `reports`\)
- `src/services.py` — бизнес\-логика \(кэшбэк, «инвесткопилка», поисковые сервисы\)
- `src/external_api.py` — интеграция с внешними API валют и акций
- `src/main.py` — демонстрационный сценарий запуска
- `data/operations.xlsx` — входные данные \(не входит в репозиторий\)
- `user_settings.json` — пользовательские настройки \(валюты, акции\)
- каталог `logs` — логи модулей `utils`, `views`, `reports`, `services`, `external_api`
- каталог `reports` — сохраняемые отчёты в формате CSV/JSON

## Тестирование

Проект покрыт юнит\-тестами на `pytest`. Для запуска тестов с покрытием:

`pytest --cov`

Тесты находятся в каталоге `tests` и покрывают:

- `tests/test_utils.py` — утилиты, диапазоны дат, загрузка данных и настроек
- `tests/test_reports.py` — отчёты и работа декоратора `report_to_file`
- `tests/test_services.py` — бизнес\-логика, «инвесткопилка», поисковые сервисы
- `tests/test_external_api.py` — работа с внешними API через заглушки `requests.get`
- `tests/test_views.py` — данные для страниц, агрегации расходов и доходов

## FAQ

Раздел будет пополняться по мере появления вопросов.

### Зачем вы разработали этот проект?

Для практики в Python, работе с финансовыми данными и построения небольшого аналитического сервиса для личных финансов.

## To do

- \[x\] Добавить осмысленное `README`
- \[x\] Логирование работы модулей в `logs`


## Команда проекта

- \[Фархад Зайнуллин\]\(https://t.me/madflyzero\) — Back\-End Engineer

## Источники

- Документация `pandas`: https://pandas.pydata.org/  
- Документация `pytest`: https://docs.pytest.org/  
- Документация `requests`: https://requests.readthedocs.io/  
- Документация `python-dotenv`: https://saurabh-kumar.com/python-dotenv/