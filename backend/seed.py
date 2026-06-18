"""
Seed script — only fills missing baseline data. Never overwrites real data.
Oil prices, fire hotspots, and UKMTO events are NEVER seeded (real sources only).
"""
import random
from datetime import date, datetime, timedelta, timezone

from app.database import engine, Base, SessionLocal
from app.models import StraitPassage, PortLoading, ShippingIndex


def seed_strait_passages(db):
    """IEA strait baseline — skip if data already exists."""
    existing = db.query(StraitPassage).filter(StraitPassage.source == "iea_baseline").count()
    if existing > 0:
        print(f"  StraitPassage: {existing} records exist, skip")
        return 0

    for i in range(90, -1, -1):
        d = date.today() - timedelta(days=i)
        noise = random.gauss(0, 1.5)
        db.add(StraitPassage(
            record_date=d,
            total_vessels=round(58 + noise * 2.5),
            tanker_vessels=round(max(15, min(25, 21 + noise))),
            lng_vessels=3, container_vessels=13, dry_bulk_vessels=11,
            tanker_capacity_tons=round(2800000 + random.uniform(-200000, 200000)),
            total_capacity_tons=round(6200000 + random.uniform(-400000, 400000)),
            source="iea_baseline",
        ))
    db.commit()
    print(f"  StraitPassage: 91 records seeded")
    return 91


def seed_port_loadings(db):
    """IEA port baseline — skip if data already exists."""
    existing = db.query(PortLoading).filter(PortLoading.source == "iea_baseline").count()
    if existing > 0:
        print(f"  PortLoading: {existing} records exist, skip")
        return 0

    ports = {
        "Kharg Island": ("IRKHK", 12, 0.83), "Ras Tanura": ("SARTA", 18, 0.78),
        "Fujairah": ("AEFJR", 8, 0.63), "Das Island": ("AEDAS", 6, 0.83),
        "Ras Laffan": ("QARLF", 8, 0.88), "Mina al-Ahmadi": ("KWMEA", 10, 0.80),
        "Basrah": ("IQBSR", 14, 0.79), "Jubail": ("SAJUB", 8, 0.75),
        "Ruwais": ("AERUW", 6, 0.83), "Yanbu": ("SAYNB", 8, 0.75),
    }
    for i in range(90, -1, -1):
        d = date.today() - timedelta(days=i)
        for name, (code, tankers, ratio) in ports.items():
            loaded = round(tankers * ratio)
            ballast = tankers - loaded
            db.add(PortLoading(
                record_date=d, port_name=name, port_code=code,
                departing_tankers=loaded, arriving_tankers=ballast,
                loaded_tankers=loaded, ballast_tankers=ballast,
                loading_ratio=ratio, source="iea_baseline",
            ))
    db.commit()
    print(f"  PortLoading: 910 records seeded")
    return 910


def seed_shipping_indices(db):
    """BDTI estimates — skip if data already exists."""
    existing = db.query(ShippingIndex).filter(ShippingIndex.source == "estimated").count()
    if existing > 5:
        print(f"  ShippingIndex: {existing} records exist, skip")
        return 0

    for i in range(30, -1, -1):
        d = date.today() - timedelta(days=i)
        exist = db.query(ShippingIndex).filter(
            ShippingIndex.record_date == d, ShippingIndex.source == "estimated"
        ).first()
        if not exist:
            db.add(ShippingIndex(
                record_date=d,
                bdti=round(random.uniform(1100, 1300)),
                td3c=round(random.uniform(900, 1100)),
                source="estimated",
            ))
    db.commit()
    print(f"  ShippingIndex: ~31 records seeded")
    return 31


def main():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Seeding baseline data (skips if real data exists)...")
        seed_strait_passages(db)
        seed_port_loadings(db)
        seed_shipping_indices(db)
        print("\nDone. Oil prices / fire / UKMTO use REAL data only — never seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
