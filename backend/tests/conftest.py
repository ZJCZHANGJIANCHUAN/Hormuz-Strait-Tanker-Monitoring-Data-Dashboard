import pytest
from datetime import date, timedelta, datetime, timezone

from app.database import engine, Base, SessionLocal
from app.models import (
    StraitPassage, PortLoading, OilPrice, ShippingIndex,
    FireHotspot, UKMTOEvent, RiskAssessment, CollectionLog,
)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_strait_data(db):
    today = date.today()
    for i in range(30):
        d = today - timedelta(days=i)
        db.add(StraitPassage(
            record_date=d,
            total_vessels=55 + i % 3,
            tanker_vessels=22 + i % 3,
            lng_vessels=4,
            container_vessels=12,
            dry_bulk_vessels=8,
            tanker_capacity_tons=2500000.0,
            total_capacity_tons=5500000.0,
            source="test",
        ))
    db.commit()


@pytest.fixture
def sample_oil_data(db):
    today = date.today()
    for i in range(10):
        d = today - timedelta(days=i)
        db.add(OilPrice(
            record_date=d,
            brent_close=82.0 + i * 0.1,
            brent_open=81.8 + i * 0.1,
            brent_high=83.0 + i * 0.1,
            brent_low=81.0 + i * 0.1,
            wti_close=78.0 + i * 0.1,
            spread=4.0,
            source="test",
        ))
    db.commit()


@pytest.fixture
def sample_fire_data(db):
    db.add(FireHotspot(
        detection_time=datetime.now(timezone.utc) - timedelta(hours=12),
        latitude=29.25,
        longitude=50.30,
        brightness=350.0,
        frp=8.5,
        confidence="high",
        facility_name="Kharg Island",
        facility_type="oil_terminal",
        country="Iran",
        source="test",
    ))
    db.commit()


@pytest.fixture
def sample_ukmto_data(db):
    db.add(UKMTOEvent(
        event_date=datetime.now(timezone.utc) - timedelta(days=2),
        event_type="suspicious_activity",
        severity="high",
        area_name="Strait of Hormuz",
        description="Suspicious approach",
        source="test",
    ))
    db.commit()


@pytest.fixture
def sample_port_data(db):
    db.add(PortLoading(
        record_date=date.today() - timedelta(days=1),
        port_name="Kharg Island",
        port_code="IRKHK",
        loaded_tankers=10,
        ballast_tankers=3,
        loading_ratio=0.77,
        source="test",
    ))
    db.add(PortLoading(
        record_date=date.today() - timedelta(days=2),
        port_name="Kharg Island",
        port_code="IRKHK",
        loaded_tankers=8,
        ballast_tankers=4,
        loading_ratio=0.67,
        source="test",
    ))
    db.commit()
