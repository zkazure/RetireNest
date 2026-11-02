"""HTTP 接口的契约、错误形状与字段映射测试。"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.service import SCHEMA_VERSION, TEMPLATE_ID

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "frontend" / "contracts"
REQUEST = json.loads((CONTRACTS / "plan-request.example.json").read_text(encoding="utf-8"))
ALL_MODULES_REQUEST = json.loads(
    (CONTRACTS / "plan-request-all-modules.example.json").read_text(encoding="utf-8")
)
RESPONSE = json.loads((CONTRACTS / "plan-response.example.json").read_text(encoding="utf-8"))

client = TestClient(app)


def post_plan(payload: object):
    return client.post("/api/retirement/plan", json=payload)


def test_default_request_returns_contract_response() -> None:
    response = post_plan(REQUEST)
    assert response.status_code == 200

    body = response.json()
    assert body["template_id"] == TEMPLATE_ID
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["mode"] == "backend"
    assert body["plan_input"] == RESPONSE["plan_input"]
    assert set(body["result"]) == set(RESPONSE["result"])
    assert len(body["result"]["points"]) == len(RESPONSE["result"]["points"])
    assert [point["age"] for point in body["result"]["points"]] == [
        point["age"] for point in RESPONSE["result"]["points"]
    ]
    assert body["result"]["depletedAge"] == RESPONSE["result"]["depletedAge"]
    assert [scenario["id"] for scenario in body["scenarios"]] == [
        "conservative",
        "baseline",
        "optimistic",
    ]
    assert isinstance(body["explanation"], str) and body["explanation"]
    assert isinstance(body["warnings"], list) and body["warnings"]


@pytest.mark.parametrize(
    "field",
    [
        "yearsToRetirement",
        "retirementYears",
        "realReturn",
        "monthlySurplus",
        "target",
        "projected",
        "gap",
        "coverage",
        "requiredMonthlySaving",
    ],
)
def test_numeric_result_matches_contract_example(field: str) -> None:
    body = post_plan(REQUEST).json()
    assert body["result"][field] == pytest.approx(RESPONSE["result"][field], rel=1e-12)


def test_all_modules_request_is_accepted_and_extensions_ignored() -> None:
    response = post_plan(ALL_MODULES_REQUEST)
    assert response.status_code == 200

    body = response.json()
    assert body["result"]["target"] == pytest.approx(RESPONSE["result"]["target"], rel=1e-12)
    assert body["plan_input"]["city"] == ALL_MODULES_REQUEST["values"]["city"]
    assert "medical_enabled" not in body["plan_input"]
    assert "pension" not in body["plan_input"]


def test_wrong_schema_version_returns_409() -> None:
    payload = copy.deepcopy(REQUEST)
    payload["schema_version"] = "9.9.9"
    response = post_plan(payload)
    assert response.status_code == 409
    assert response.json()["code"] == "SCHEMA_VERSION_MISMATCH"


def test_wrong_template_id_returns_409() -> None:
    payload = copy.deepcopy(REQUEST)
    payload["template_id"] = "another-template"
    response = post_plan(payload)
    assert response.status_code == 409
    assert response.json()["code"] == "SCHEMA_VERSION_MISMATCH"


def test_age_order_returns_422_with_field_error() -> None:
    payload = copy.deepcopy(REQUEST)
    payload["values"]["retire_age"] = payload["values"]["age"]
    response = post_plan(payload)

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert any(error["field"] == "retire_age" for error in body["field_errors"])


def test_missing_or_wrong_type_returns_422() -> None:
    payload = copy.deepcopy(REQUEST)
    del payload["values"]["age"]
    response = post_plan(payload)
    assert response.status_code == 422
    assert any(error["field"] == "age" for error in response.json()["field_errors"])

    payload = copy.deepcopy(REQUEST)
    payload["values"]["age"] = "28"
    response = post_plan(payload)
    assert response.status_code == 422
    assert any(error["field"] == "age" for error in response.json()["field_errors"])


def test_out_of_range_expense_returns_422() -> None:
    payload = copy.deepcopy(REQUEST)
    payload["values"]["monthly_expense"] = 0
    response = post_plan(payload)
    assert response.status_code == 422
    assert any(error["field"] == "monthly_expense" for error in response.json()["field_errors"])


def test_malformed_json_returns_422() -> None:
    response = client.post(
        "/api/retirement/plan",
        content="{",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_unknown_top_level_field_returns_422() -> None:
    payload = copy.deepcopy(REQUEST)
    payload["unexpected"] = True
    response = post_plan(payload)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_custom_city_is_accepted() -> None:
    payload = copy.deepcopy(REQUEST)
    payload["values"]["city"] = "某某市"
    response = post_plan(payload)
    assert response.status_code == 200
    assert response.json()["plan_input"]["city"] == "某某市"


DIST_INDEX = ROOT / "frontend" / "dist" / "index.html"


@pytest.mark.skipif(not DIST_INDEX.is_file(), reason="前端尚未构建")
def test_built_frontend_is_served_at_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
