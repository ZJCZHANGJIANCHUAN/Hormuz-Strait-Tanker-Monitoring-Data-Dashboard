import pytest
from datetime import date, timedelta, datetime, timezone

from fastapi.testclient import TestClient
from app.main import app
from app.database import engine, Base, SessionLocal
from app.models import (
    StraitPassage, OilPrice, FireHotspot, UKMTOEvent,
    ShippingIndex, PortLoading, RiskAssessment,
)


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def populated_db():
    db = SessionLocal()
    today = date.today()
    for i in range(10):
        d = today - timedelta(days=i)
        db.add(StraitPassage(
            record_date=d,
            total_vessels=55,
            tanker_vessels=22,
            lng_vessels=4,
            source="test",
        ))
        db.add(OilPrice(
            record_date=d,
            brent_close=82.0,
            brent_open=81.8,
            brent_high=83.0,
            brent_low=81.0,
            wti_close=78.0,
            spread=4.0,
            source="test",
        ))
    db.add(FireHotspot(
        detection_time=datetime.now(timezone.utc) - timedelta(hours=12),
        latitude=29.25, longitude=50.30,
        brightness=350.0, frp=8.5,
        confidence="high",
        facility_name="Kharg Island",
        facility_type="oil_terminal",
        source="test",
    ))
    db.add(UKMTOEvent(
        event_date=datetime.now(timezone.utc) - timedelta(days=2),
        event_type="suspicious_activity",
        severity="high",
        area_name="Strait of Hormuz",
        description="Suspicious approach",
        source="test",
    ))
    db.add(ShippingIndex(
        record_date=today - timedelta(days=1),
        bdti=1100, td3c=950, td8=700, bcti=600,
        source="test",
    ))
    db.add(PortLoading(
        record_date=today - timedelta(days=1),
        port_name="Kharg Island", port_code="IRKHK",
        loaded_tankers=10, ballast_tankers=3,
        loading_ratio=0.77,
        source="test",
    ))
    db.add(RiskAssessment(
        assessment_date=today - timedelta(days=1),
        risk_level=2,
        risk_level_label="中度实质影响",
        confidence_score=0.85,
        evidence_summary="Test assessment",
    ))
    db.commit()
    yield db
    db.rollback()
    db.close()


class TestHealthCheck:

    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"


class TestDashboard:

    def test_summary_endpoint(self, client, populated_db):
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "risk" in data
        assert "strait" in data
        assert "oil" in data
        assert "fires" in data
        assert "ukmto" in data
        assert "source_status" in data

    def test_summary_has_risk_level(self, client, populated_db):
        resp = client.get("/api/dashboard/summary")
        data = resp.json()
        assert data["risk"]["level"] == 2
        assert data["risk"]["label"] == "中度实质影响"

    def test_sources_endpoint(self, client):
        resp = client.get("/api/dashboard/sources")
        assert resp.status_code == 200


class TestData:

    def test_strait_data(self, client, populated_db):
        resp = client.get("/api/data/strait?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert len(data["data"]) > 0

    def test_strait_data_validation(self, client):
        resp = client.get("/api/data/strait?days=0")
        assert resp.status_code == 422  # validation error

    def test_ports_data(self, client, populated_db):
        resp = client.get("/api/data/ports?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    def test_prices_data(self, client, populated_db):
        resp = client.get("/api/data/prices?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert len(data["data"]) > 0

    def test_shipping_data(self, client, populated_db):
        resp = client.get("/api/data/shipping?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    def test_fires_data(self, client, populated_db):
        resp = client.get("/api/data/fires?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert len(data["data"]) > 0

    def test_fires_data_filter_by_facility(self, client, populated_db):
        resp = client.get("/api/data/fires?days=7&facility=Kharg+Island")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["data"]:
            assert item["facility_name"] == "Kharg Island"

    def test_ukmto_data(self, client, populated_db):
        resp = client.get("/api/data/ukmto?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert len(data["data"]) > 0


class TestRisk:

    def test_assessment_list(self, client, populated_db):
        resp = client.get("/api/risk/assessment?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert len(data["data"]) > 0

    def test_run_assessment(self, client, populated_db):
        resp = client.post("/api/risk/assess")
        assert resp.status_code == 200
        data = resp.json()
        assert "level" in data
        assert "label" in data
        assert "confidence" in data
        assert "dimensions" in data


class TestAdmin:

    def test_get_logs(self, client):
        resp = client.get("/api/admin/logs?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    def test_add_ukmto_event(self, client):
        resp = client.post("/api/admin/ukmto/events", json={
            "event_date": "2025-01-15T12:00:00",
            "event_type": "suspicious_activity",
            "description": "Test event",
            "severity": "medium",
            "area_name": "Strait of Hormuz",
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "Event added successfully"

    def test_add_shipping_index(self, client):
        resp = client.post("/api/admin/shipping", json={
            "record_date": "2025-01-15",
            "bdti": 1200.0,
            "td3c": 1000.0,
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "Shipping index added"
