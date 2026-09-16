import json
import os
import pytest

from benchmark.real_world.agent_simulators import AgentSimulator
from benchmark.real_world.evaluator import run_hidden_evaluator, TASKS_DIR, RESULTS_DIR


def test_v4_1_tasks_exist():
    assert os.path.exists(TASKS_DIR)
    task_folders = [f for f in os.listdir(TASKS_DIR) if os.path.isdir(os.path.join(TASKS_DIR, f))]
    assert len(task_folders) == 12


def test_v4_1_agent_simulators():
    sim = AgentSimulator(persona="competent")
    assert sim.persona == "competent"
    careless = AgentSimulator(persona="careless")
    assert careless.persona == "careless"


def test_v4_1_results_json_structure():
    results_path = os.path.join(RESULTS_DIR, "v4_1_real_world.json")
    if os.path.exists(results_path):
        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "control_group" in data
        assert "treatment_group" in data
        assert "success_rate" in data["treatment_group"]
