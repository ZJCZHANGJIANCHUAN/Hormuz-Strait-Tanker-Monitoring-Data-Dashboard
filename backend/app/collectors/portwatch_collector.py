import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from app.collectors.base import BaseCollector, CollectResult, CollectorStatus
from app.database import SessionLocal
from app.models import StraitPassage, PortLoading

logger = logging.getLogger(__name__)

PORTWATCH_CHOKEPOINT_URL = (
    "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
    "Daily_Chokepoints_Data/FeatureServer/0/query"
)
PORTWATCH_PORT_URL = (
    "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
    "Daily_Ports_Data/FeatureServer/0/query"
)
STRAIT_OF_HORMUZ_ID = "chokepoint6"
KEY_PORTS = [
    "Kharg Island", "Ras Tanura", "Fujairah", "Das Island",
    "Ras Laffan", "Mina al-Ahmadi", "Basrah", "Jubail",
    "Ruwais", "Yanbu",
]


class PortWatchCollector(BaseCollector):
    source_name = "portwatch"
    update_frequency = timedelta(hours=12)

    async def collect(self, target_date: datetime | None = None) -> CollectResult:
        errors = []
        records_count = 0

        try:
            result = await self._fetch_strait_data()
            if result.errors:
                errors.extend(result.errors)
            records_count += result.records_count
        except Exception as e:
            errors.append(f"Strait data failed: {e}")

        try:
            result = await self._fetch_port_data()
            if result.errors:
                errors.extend(result.errors)
            records_count += result.records_count
        except Exception as e:
            errors.append(f"Port data failed: {e}")

        return CollectResult(
            status=CollectorStatus.SUCCESS if not errors else CollectorStatus.PARTIAL,
            records_count=records_count,
            errors=errors,
        )

    async def _fetch_strait_data(self) -> CollectResult:
        errors = []
        all_records = []
        offset = 0

        try:
            while True:
                params = {
                    "where": f"portid='{STRAIT_OF_HORMUZ_ID}'",
                    "outFields": "*",
                    "outSR": "4326",
                    "f": "json",
                    "resultOffset": offset,
                    "resultRecordCount": 1000,
                    "orderByFields": "date DESC",
                }
                resp = await self.http_client.get(PORTWATCH_CHOKEPOINT_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

                features = data.get("features", [])
                if not features:
                    break

                for f in features:
                    attrs = f["attributes"]
                    date_val = attrs.get("date")
                    if isinstance(date_val, str):
                        record_date = datetime.strptime(date_val, "%Y-%m-%d").date()
                    elif date_val:
                        record_date = datetime.fromtimestamp(date_val / 1000, tz=timezone.utc).date()
                    else:
                        record_date = None

                    all_records.append({
                        "record_date": record_date,
                        "total_vessels": attrs.get("n_total"),
                        "tanker_vessels": attrs.get("n_tanker"),
                        "lng_vessels": 0,
                        "container_vessels": attrs.get("n_container"),
                        "dry_bulk_vessels": attrs.get("n_dry_bulk"),
                        "tanker_capacity_tons": attrs.get("capacity_tanker"),
                        "total_capacity_tons": attrs.get("capacity"),
                    })

                offset += len(features)
                if len(features) < 1000:
                    break

            db = SessionLocal()
            try:
                inserted = 0
                for rec in all_records:
                    if not rec["record_date"]:
                        continue
                    existing = (
                        db.query(StraitPassage)
                        .filter(
                            StraitPassage.record_date == rec["record_date"],
                            StraitPassage.source == "portwatch",
                        )
                        .first()
                    )
                    if not existing:
                        db.add(StraitPassage(**rec))
                        inserted += 1
                db.commit()
            finally:
                db.close()

            logger.info(f"PortWatch: fetched {len(all_records)} records, inserted {inserted}")
            return CollectResult(
                status=CollectorStatus.SUCCESS,
                records_count=inserted,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"PortWatch strait data error: {e}")
            return CollectResult(
                status=CollectorStatus.FAILED,
                errors=[str(e)],
            )

    async def _fetch_port_data(self) -> CollectResult:
        errors = []
        all_records = []

        try:
            # Build OR filter for key ports
            name_conditions = " OR ".join(
                f"portname='{p}'" for p in KEY_PORTS
            )
            where_clause = f"({name_conditions})"

            offset = 0
            while True:
                params = {
                    "where": where_clause,
                    "outFields": "*",
                    "outSR": "4326",
                    "f": "json",
                    "resultOffset": offset,
                    "resultRecordCount": 500,
                    "orderByFields": "date DESC",
                }
                resp = await self.http_client.get(PORTWATCH_PORT_URL, params=params, timeout=20.0)
                resp.raise_for_status()
                data = resp.json()

                features = data.get("features", [])
                if not features:
                    break

                for f in features:
                    attrs = f["attributes"]
                    date_val = attrs.get("date")
                    if isinstance(date_val, str):
                        record_date = datetime.strptime(date_val, "%Y-%m-%d").date()
                    elif date_val:
                        record_date = datetime.fromtimestamp(date_val / 1000, tz=timezone.utc).date()
                    else:
                        continue

                    port_name = attrs.get("portname", "")
                    portcalls_tanker = attrs.get("portcalls_tanker") or 0
                    export_tanker = attrs.get("export_tanker") or 0
                    import_tanker = attrs.get("import_tanker") or 0

                    # Loading ratio: if both import and export are 0, ratio is 0
                    total_flow = export_tanker + import_tanker
                    if total_flow > 0:
                        loading_ratio = export_tanker / total_flow
                    else:
                        loading_ratio = 0.0

                    all_records.append({
                        "record_date": record_date,
                        "port_name": port_name,
                        "port_code": attrs.get("portid", ""),
                        "departing_tankers": portcalls_tanker,
                        "arriving_tankers": portcalls_tanker,
                        "loaded_tankers": round(portcalls_tanker * loading_ratio) if loading_ratio else 0,
                        "ballast_tankers": round(portcalls_tanker * (1 - loading_ratio)) if loading_ratio else portcalls_tanker,
                        "loading_ratio": loading_ratio,
                        "estimated_exports_7d": export_tanker * 7 if export_tanker else 0,
                        "estimated_exports_30d": export_tanker * 30 if export_tanker else 0,
                    })

                offset += len(features)
                if len(features) < 1000:
                    break

            db = SessionLocal()
            try:
                inserted = 0
                for rec in all_records:
                    existing = (
                        db.query(PortLoading)
                        .filter(
                            PortLoading.record_date == rec["record_date"],
                            PortLoading.port_code == rec["port_code"],
                            PortLoading.source == "portwatch",
                        )
                        .first()
                    )
                    if not existing:
                        db.add(PortLoading(**rec))
                        inserted += 1
                db.commit()
            finally:
                db.close()

            logger.info(f"PortWatch ports: fetched {len(all_records)} records, inserted {inserted}")
            return CollectResult(
                status=CollectorStatus.SUCCESS if inserted > 0 else CollectorStatus.PARTIAL,
                records_count=inserted,
                errors=errors if not inserted else [],
            )

        except Exception as e:
            logger.error(f"PortWatch port data error: {e}")
            return CollectResult(
                status=CollectorStatus.FAILED,
                errors=[str(e)],
            )
