"""
conftest.py - Shared pytest fixtures for CIVIX AI test suite.
Seeds a clean SQLite database once per test session so every test
module reads from the same consistent 40-complaint dataset.
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import database
from data.sample_data import populate_database


@pytest.fixture(scope="session", autouse=True)
def seeded_database():
    """Reset and seed the database exactly once for the whole test session."""
    populate_database(reset=True)
    yield
    # Leave data intact after tests (useful for manual inspection)


@pytest.fixture(scope="session")
def all_complaints(seeded_database):
    """Returns all 40 seeded complaints as a list of dicts."""
    return database.get_all_complaints()


# ---------------------------------------------------------------------------
# Small pools of complaints used as inputs across multiple test modules
# ---------------------------------------------------------------------------

POOL_ROADS = [
    {
        "id": "CIVIX-1004",
        "title": "Massive pothole outside Sony World Signal causing scooter accidents",
        "description": "Deep 1-meter wide pothole right at the turning near Sony World signal. Two two-wheelers fallen today.",
        "category": "Roads & Infrastructure",
        "latitude": 12.9351,
        "longitude": 77.6244,
    },
    {
        "id": "CIVIX-1010",
        "title": "Severe sewage pipeline burst and overflowing onto 100ft road",
        "description": "Main underground sewage pipe has ruptured. Black wastewater flooding two lanes.",
        "category": "Water Supply & Drainage",
        "latitude": 12.9718,
        "longitude": 77.6410,
    },
    {
        "id": "CIVIX-1016",
        "title": "Electrical transformer sparking dangerously near ITPL main gate 2",
        "description": "Heavy orange sparks and loud popping sound from roadside transformer. Thick black smoke.",
        "category": "Electricity & Power",
        "latitude": 12.9865,
        "longitude": 77.7377,
    },
    {
        "id": "CIVIX-0001",
        "title": "Noise complaint from construction site",
        "description": "Loud machinery working past midnight near residential area.",
        "category": "Public Safety",
        "latitude": 13.0800,
        "longitude": 77.5000,
    },
]


@pytest.fixture(scope="session")
def small_pool():
    return POOL_ROADS

