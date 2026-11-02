"""协议 1.1 的工具元数据与新命令执行用例。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from commands import PROTOCOL_VERSION, list_commands

client = TestClient(app)

NEW_COMMANDS = {
    "savings.project",
    "savings.goal",
    "inflation.convert",
    "simulation.retirement",
    "withdrawal.safe_rate",
    "longevity.estimate",
}


def manifests() -> dict[str, dict]:
    body = client.get("/api/commands").json()
    return {command["id"]: command for command in body["commands"]}


def test_protocol_version_is_1_1() -> None:
    body = client.get("/api/commands").json()
    assert body["protocol_version"] == "1.1.0"
    assert PROTOCOL_VERSION == "1.1.0"


def test_new_commands_expose_tool_metadata() -> None:
    catalog = manifests()
    for command_id in NEW_COMMANDS:
        command = catalog[command_id]
        assert command["version"] == "1.0.0"
        assert command["description"]
        assert command["when_to_use"]
        assert command["when_not_to_use"]
        assert command["deterministic"] is True
        for spec in command["inputs"]:
            assert spec["description"], f"{command_id}.{spec['name']} 缺少参数说明"
        for spec in command["outputs"]:
            assert "description" in spec


def test_new_commands_have_examples() -> None:
    catalog = manifests()
    for command_id in NEW_COMMANDS:
        examples = catalog[command_id]["examples"]
        assert examples
        assert examples[0]["inputs"]


def test_no_duplicate_command_ids() -> None:
    ids = [command.manifest.id for command in list_commands()]
    assert len(ids) == len(set(ids)) == 11


@pytest.mark.parametrize("command_id", sorted(NEW_COMMANDS))
def test_examples_execute_and_return_declared_outputs(command_id: str) -> None:
    command = manifests()[command_id]
    response = client.post(
        f"/api/commands/{command_id}",
        json={
            "version": command["version"],
            "inputs": command["examples"][0]["inputs"],
        },
    )
    assert response.status_code == 200, response.text
    outputs = response.json()["outputs"]
    assert set(outputs) == {spec["name"] for spec in command["outputs"]}
    assert response.json()["meta"]["deterministic"] is True


def test_monte_carlo_is_reproducible_over_http() -> None:
    command = manifests()["simulation.retirement"]
    payload = {
        "version": command["version"],
        "inputs": command["examples"][0]["inputs"],
    }
    first = client.post("/api/commands/simulation.retirement", json=payload)
    second = client.post("/api/commands/simulation.retirement", json=payload)
    assert first.status_code == 200
    assert first.json()["outputs"] == second.json()["outputs"]


def test_withdrawal_is_reproducible_over_http() -> None:
    command = manifests()["withdrawal.safe_rate"]
    payload = {
        "version": command["version"],
        "inputs": command["examples"][0]["inputs"],
    }
    first = client.post("/api/commands/withdrawal.safe_rate", json=payload)
    second = client.post("/api/commands/withdrawal.safe_rate", json=payload)
    assert first.status_code == 200
    assert first.json()["outputs"] == second.json()["outputs"]


def test_longevity_probabilities_are_percent() -> None:
    command = manifests()["longevity.estimate"]
    response = client.post(
        "/api/commands/longevity.estimate",
        json={
            "version": command["version"],
            "inputs": command["examples"][0]["inputs"],
        },
    )
    outputs = response.json()["outputs"]
    assert 0 <= outputs["probability_to_95"] <= outputs["probability_to_90"] <= 100
    assert outputs["probability_to_90"] <= outputs["probability_to_85"] <= 100


def test_longevity_has_as_of() -> None:
    command = manifests()["longevity.estimate"]
    assert command["as_of"] == "2020"


@pytest.mark.parametrize(
    ("command_id", "inputs", "field"),
    [
        (
            "savings.project",
            {
                "current_savings": 100_000,
                "monthly_contribution": 1_000,
                "annual_return_pct": 5,
                "inflation_pct": 2,
                "years": 10,
                "compounding": "按日",
            },
            "compounding",
        ),
        (
            "inflation.convert",
            {
                "amount": 100_000,
                "annual_inflation_pct": 2,
                "years": 10,
                "direction": "横着转",
            },
            "direction",
        ),
        (
            "longevity.estimate",
            {"current_age": 30, "sex": "其他", "health": "一般"},
            "sex",
        ),
        (
            "simulation.retirement",
            {
                "current_savings": 500_000,
                "monthly_contribution": 3_000,
                "years_to_retirement": 50,
                "retirement_years": 60,
                "annual_retirement_expense": 60_000,
                "annual_return_pct": 5,
                "volatility_pct": 10,
                "inflation_pct": 2,
            },
            "inputs",
        ),
    ],
)
def test_new_command_input_errors_are_field_level(
    command_id: str,
    inputs: dict,
    field: str,
) -> None:
    command = manifests()[command_id]
    response = client.post(
        f"/api/commands/{command_id}",
        json={"version": command["version"], "inputs": inputs},
    )
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "INVALID_INPUT"
    assert any(error["field"] == field for error in body["field_errors"])
