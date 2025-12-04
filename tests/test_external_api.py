import json

from src import external_api


class DummyResponse:
    def __init__(self, status_code=200, text="", reason="OK"):
        self.status_code = status_code
        self.text = text
        self.reason = reason


def test_get_currency_rates_success(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        payload = {"quotes": {"USDRUB": 73.21}}
        return DummyResponse(200, json.dumps(payload))

    monkeypatch.setattr(external_api.requests, "get", fake_get)

    res = external_api.get_currency_rates(["USD"])
    assert res == [{"currency": "USD", "rate": 73.21}]


def test_get_currency_rates_error_status(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return DummyResponse(500, "err", reason="Server Error")

    monkeypatch.setattr(external_api.requests, "get", fake_get)

    res = external_api.get_currency_rates(["USD"])
    assert res[0]["currency"] == "USD"
    assert res[0]["rate"] == 0.0


def test_get_currency_rates_bad_json(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return DummyResponse(200, "not-a-json")

    monkeypatch.setattr(external_api.requests, "get", fake_get)

    res = external_api.get_currency_rates(["USD"])
    assert res[0]["rate"] == 0.0


def test_get_stock_prices_success(monkeypatch):
    payload = {"data": [{"close": 150.12}]}

    def fake_get(url, params=None, timeout=None):
        assert "symbols" in params
        return DummyResponse(200, json.dumps(payload))

    monkeypatch.setattr(external_api.requests, "get", fake_get)

    res = external_api.get_stock_prices(["AAPL"])
    assert res == [{"stock": "AAPL", "price": 150.12}]


def test_get_stock_prices_empty_data(monkeypatch):
    payload = {"data": []}

    def fake_get(url, params=None, timeout=None):
        return DummyResponse(200, json.dumps(payload))

    monkeypatch.setattr(external_api.requests, "get", fake_get)

    res = external_api.get_stock_prices(["AAPL"])
    assert res[0]["price"] == 0.0


def test_get_stock_prices_error(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return DummyResponse(404, "not found", reason="Not Found")

    monkeypatch.setattr(external_api.requests, "get", fake_get)

    res = external_api.get_stock_prices(["AAPL"])
    assert res[0]["price"] == 0.0

