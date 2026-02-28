"""Pytest configuration and fixtures."""

import os

import pytest


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    """Set minimal env for unit tests."""
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    monkeypatch.setenv("STAGE", "test")
