"""Unit tests for Supervisor Agent routing."""

import pytest
from cdss.agents.supervisor import INTENT_TO_AGENT, SupervisorAgent


def test_route_intent_patient():
    agent = SupervisorAgent()
    out = agent.route_intent("get patient history", {})
    assert out["agent"] == "PatientAgent"


def test_route_intent_surgery():
    agent = SupervisorAgent()
    out = agent.route_intent("surgery checklist", {})
    assert out["agent"] == "SurgeryPlanningAgent"


def test_route_intent_scheduling():
    agent = SupervisorAgent()
    out = agent.route_intent("book appointment", {})
    assert out["agent"] == "SchedulingAgent"


def test_route_intent_engagement():
    agent = SupervisorAgent()
    out = agent.route_intent("send reminder", {})
    assert out["agent"] == "EngagementAgent"


def test_aggregate_response():
    agent = SupervisorAgent()
    out = agent.aggregate_response([{"a": 1}, {"b": 2}])
    assert out["aggregated"] is True
    assert len(out["responses"]) == 2
