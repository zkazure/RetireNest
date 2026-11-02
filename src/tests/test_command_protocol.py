"""命令协议：清单、四个适配器、错误形状与回归。"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.app import app
from commands import PROTOCOL_VERSION, list_commands
from deposit import DemandDeposit
from deposit import calculate as calculate_deposit
from living import calculate as calculate_living
from medical import estimate_medical_cost
from pension import BasicPensionInput
from pension import calculate as calculate_pension

client = TestClient(app)
PROTOCOL = "1.0.0"


def run(command_id: str, inputs: dict, version: str = PROTOCOL):
    return client.post(
        f"/api/commands/{command_id}",
        json={"version": version, "inputs": inputs},
    )


def test_command_list_contains_five_manifests() -> None:
    response = client.get("/api/commands")
    assert response.status_code == 200

    body = response.json()
    assert body["protocol_version"] == PROTOCOL_VERSION
    ids = [command["id"] for command in body["commands"]]
    assert ids == [
        "plan.retirement",
        "medical.estimate",
        "pension.basic",
        "deposit.demand",
        "living.calculate",
    ]
    for command in body["commands"]:
        assert command["question"]
        assert command["version"] == "1.0.0"
        assert command["inputs"]
        assert command["outputs"]
        assert all("question" in item for item in command["inputs"])
        assert all("question" in item for item in command["outputs"])
        assert all("visible" in item for item in command["outputs"])


def test_medical_matches_module() -> None:
    inputs = {"age": 30, "city": "广州", "insurance": "职工医保"}
    response = run("medical.estimate", inputs)
    assert response.status_code == 200

    outputs = response.json()["outputs"]
    expected = estimate_medical_cost(age=30, city="广州", insurance="职工医保")
    assert outputs == expected
    assert outputs["monthly_medical_cost"] == pytest.approx(164.67)


def test_pension_matches_module() -> None:
    inputs = {
        "birth_date": "1965-06-01",
        "gender": "男",
        "contribution_years": "30.0",
        "average_index": "1.0",
        "account_balance": "150000.00",
        "calculation_base": "8000.00",
    }
    response = run("pension.basic", inputs)
    assert response.status_code == 200

    outputs = response.json()["outputs"]
    expected = calculate_pension(
        BasicPensionInput(
            birth_date=date(1965, 6, 1),
            gender="男",
            contribution_years="30.0",
            average_index="1.0",
            account_balance="150000.00",
            calculation_base="8000.00",
        )
    )
    assert outputs["retirement_age_months"] == expected.retirement_age_months
    assert outputs["payout_months"] == expected.payout_months
    assert outputs["total"] == str(expected.total)
    assert outputs["basic_pension"] == str(expected.basic_pension)
    assert outputs["account_pension"] == str(expected.account_pension)
    assert outputs["total"] == "3479.14"


def test_deposit_matches_module() -> None:
    inputs = {
        "principal": "100000.20",
        "annual_rate": "0.0005",
        "start_date": "2026-01-01",
        "end_date": "2027-01-01",
    }
    response = run("deposit.demand", inputs)
    assert response.status_code == 200

    outputs = response.json()["outputs"]
    expected = calculate_deposit(
        DemandDeposit(
            principal="100000.20",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 1, 1),
            annual_rate="0.0005",
        )
    )
    assert outputs["principal"] == str(expected.principal)
    assert outputs["annual_rate"] == str(expected.annual_rate)
    assert outputs["days"] == expected.days
    assert outputs["interest"] == str(expected.interest)
    assert outputs["total"] == str(expected.total)
    assert outputs["total"] == "100050.89"


def test_living_matches_module() -> None:
    inputs = {"age": 30, "city": "珠海", "monthly_expense": 9000}
    response = run("living.calculate", inputs)
    assert response.status_code == 200

    outputs = response.json()["outputs"]
    expected = calculate_living(inputs)
    assert outputs["years"] == expected["years"]
    assert outputs["retire_index"] == expected["retire_index"]
    assert len(outputs["nominal"]["total"]) == expected["years"]
    assert outputs["nominal"]["total"][0] == pytest.approx(expected["nominal"]["total"][0])
    assert outputs["real"]["total"][0] == pytest.approx(expected["real"]["total"][0])


PLAN_INPUTS = {
    "city": "珠海",
    "age": 30,
    "retire_age": 55,
    "life_expectancy": 90,
    "monthly_income": 20000,
    "monthly_expense": 12000,
    "assets": 500000,
    "debt": 0,
    "retirement_expense": 8000,
    "monthly_pension": 3000,
    "nominal_return": 5,
    "inflation": 2,
}


def test_plan_retirement_matches_legacy_endpoint() -> None:
    legacy = client.post(
        "/api/retirement/plan",
        json={
            "template_id": "retirenest-retirement",
            "schema_version": "1.0.0",
            "values": PLAN_INPUTS,
        },
    )
    assert legacy.status_code == 200
    expected = legacy.json()

    response = run("plan.retirement", PLAN_INPUTS)
    assert response.status_code == 200
    outputs = response.json()["outputs"]

    assert outputs["plan_input"] == expected["plan_input"]
    assert outputs["explanation"] == expected["explanation"]
    for key in ("target", "projected", "gap", "coverage"):
        assert outputs[key] == pytest.approx(expected["result"][key])
    assert outputs["required_monthly_saving"] == pytest.approx(
        expected["result"]["requiredMonthlySaving"]
    )
    assert outputs["monthly_surplus"] == pytest.approx(expected["result"]["monthlySurplus"])
    assert outputs["years_to_retirement"] == expected["result"]["yearsToRetirement"]
    assert outputs["retirement_years"] == expected["result"]["retirementYears"]
    assert outputs["depleted_age"] == expected["result"]["depletedAge"]
    assert outputs["points"] == expected["result"]["points"]
    assert outputs["scenarios"] == expected["scenarios"]
    assert len(outputs["warnings"]) == 2


def test_plan_retirement_rejects_cross_field_error() -> None:
    response = run("plan.retirement", {**PLAN_INPUTS, "retire_age": 30})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "INVALID_INPUT"
    assert any(error["field"] == "retire_age" for error in body["field_errors"])


def test_plan_retirement_requires_every_input() -> None:
    inputs = dict(PLAN_INPUTS)
    inputs.pop("assets")
    response = run("plan.retirement", inputs)
    assert response.status_code == 422
    assert any(error["field"] == "assets" for error in response.json()["field_errors"])


def test_internal_outputs_are_marked_invisible() -> None:
    body = client.get("/api/commands").json()
    living = next(command for command in body["commands"] if command["id"] == "living.calculate")
    retire_index = next(item for item in living["outputs"] if item["name"] == "retire_index")
    assert retire_index["visible"] is False

    plan = next(command for command in body["commands"] if command["id"] == "plan.retirement")
    points = next(item for item in plan["outputs"] if item["name"] == "points")
    assert points["visible"] is False


def test_unknown_command() -> None:
    response = run("nope.nope", {})
    assert response.status_code == 404
    assert response.json()["code"] == "UNKNOWN_COMMAND"


def test_unsupported_version() -> None:
    response = run(
        "medical.estimate", {"age": 30, "city": "广州", "insurance": "职工医保"}, "9.9.9"
    )
    assert response.status_code == 409
    assert response.json()["code"] == "UNSUPPORTED_VERSION"


def test_missing_input_returns_field_error() -> None:
    response = run("medical.estimate", {"city": "广州", "insurance": "职工医保"})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "INVALID_INPUT"
    assert any(error["field"] == "age" for error in body["field_errors"])


def test_unknown_input_is_rejected() -> None:
    response = run(
        "medical.estimate",
        {"age": 30, "city": "广州", "insurance": "职工医保", "typo": 1},
    )
    assert response.status_code == 422
    assert any(error["field"] == "typo" for error in response.json()["field_errors"])


def test_bad_enum_and_scientific_decimal() -> None:
    response = run("medical.estimate", {"age": 30, "city": "广州", "insurance": "不存在"})
    assert response.status_code == 422
    assert any(error["field"] == "insurance" for error in response.json()["field_errors"])

    response = run(
        "deposit.demand",
        {
            "principal": "1e5",
            "start_date": "2026-01-01",
            "end_date": "2027-01-01",
        },
    )
    assert response.status_code == 422
    assert any(error["field"] == "principal" for error in response.json()["field_errors"])


def test_female_pension_requires_category() -> None:
    response = run(
        "pension.basic",
        {
            "birth_date": "1990-01-01",
            "gender": "女",
            "contribution_years": "30.0",
            "average_index": "1.0",
            "account_balance": "150000.00",
            "calculation_base": "8000.00",
        },
    )
    assert response.status_code == 422
    assert any(error["field"] == "category" for error in response.json()["field_errors"])


def test_domain_error_becomes_422_without_stack() -> None:
    response = run(
        "living.calculate",
        {"age": 30, "city": "珠海", "monthly_expense": 9000, "retire_age": 30},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "INVALID_INPUT"
    assert "年龄顺序" in body["message"]
    assert "Traceback" not in body["message"]


def test_command_list_inputs_include_conditional_rule() -> None:
    body = client.get("/api/commands").json()
    pension = next(command for command in body["commands"] if command["id"] == "pension.basic")
    category = next(item for item in pension["inputs"] if item["name"] == "category")
    assert category["required"] is False
    assert category["required_when"] == {"field": "gender", "equals": "女"}
    assert len(list_commands()) == 5
