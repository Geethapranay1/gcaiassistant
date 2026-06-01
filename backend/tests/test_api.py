import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_process_without_llm():
    os.environ.pop("GROQ_API_KEY", None)
    resp = client.post("/process", json={"query": "Send an email to Rahul"})
    assert resp.status_code == 200
    data = resp.json()
    assert "tool" in data
    assert "missing_fields" in data

def test_find_slot_endpoint():
    resp = client.post("/find-slot", json={
        "participants": ["Rahul", "Priya"],
        "duration_minutes": 30,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "2026-06-02 15:00" in data["available_slots"]
    assert data["selected_slot"] == "2026-06-02 15:00"

def test_find_slot_empty_participants():
    resp = client.post("/find-slot", json={
        "participants": [],
        "duration_minutes": 30,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["available_slots"] == []
    assert data["selected_slot"] is None
