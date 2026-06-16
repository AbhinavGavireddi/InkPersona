from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["app"] == "InkPersona"


def test_traits_endpoint_returns_groups_and_disclaimer():
    response = client.get("/traits")
    assert response.status_code == 200
    body = response.json()
    assert "groups" in body
    assert "slant_and_baseline" in body["groups"]
    assert "not a validated way" in body["disclaimer"]


def test_mock_analysis_endpoint():
    response = client.get("/mock-analysis")
    assert response.status_code == 200
    body = response.json()
    assert body["product_name"] == "InkPersona"
    assert body["objective_traits"]["stroke"]["pressure_estimate"]["confidence"] == "low"


def test_rejects_non_image_upload():
    response = client.post(
        "/analyze",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415
