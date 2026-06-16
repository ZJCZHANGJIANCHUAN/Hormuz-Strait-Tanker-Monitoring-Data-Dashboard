"""
Data validation service — ensures data freshness, detects anomalies,
and validates cross-source consistency before risk assessment.
"""
import logging
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field

from sqlalchemy import func
from app.database import SessionLocal
from app.models import (
    StraitPassage, PortLoading, OilPrice, ShippingIndex,
    FireHotspot, UKMTOEvent, RiskAssessment, CollectionLog,
)

logger = logging.getLogger(__name__)

# Expected ranges for key indicators
EXPECTED_RANGES = {
    "strait_tanker": (10, 40),       # tankers/day through Hormuz (~21 avg, EIA)
    "strait_total": (30, 90),        # total vessels/day (~58 avg, EIA)
    "brent_price": (40, 120),        # $/barrel
    "brent_wti_spread": (-3, 15),    # $ spread
    "bdti": (500, 2500),             # Baltic Dirty Tanker Index
    "loading_ratio": (0.2, 0.90),    # port loading ratio
    "fire_frp": (0.1, 500),          # Fire Radiative Power
}

# Freshness thresholds: maximum hours since last successful collection
FRESHNESS_HOURS = {
    "portwatch": 24,       # strait + port data: daily is fine
    "yahoo_finance": 12,   # oil prices: should be within trading day
    "nasa_firms": 24,      # fire data: daily
    "ukmto": 12,           # security events: should be frequent
    "shipping_index": 24,  # estimated daily
}


@dataclass
class ValidationResult:
    is_valid: bool
    freshness_ok: bool
    values_ok: bool
    consistency_ok: bool
    freshness_issues: list[str] = field(default_factory=list)
    value_issues: list[str] = field(default_factory=list)
    consistency_issues: list[str] = field(default_factory=list)
    overall_score: float = 1.0  # 0.0-1.0


class DataValidator:
    """Validates data quality before risk assessment."""

    def __init__(self):
        self.db = SessionLocal()

    def validate(self) -> ValidationResult:
        freshness_issues = self._check_freshness()
        value_issues = self._check_value_ranges()
        consistency_issues = self._check_consistency()

        freshness_ok = len(freshness_issues) <= 1  # allow 1 stale source
        values_ok = len(value_issues) == 0
        consistency_ok = len(consistency_issues) <= 1

        is_valid = freshness_ok and values_ok and consistency_ok

        total_checks = 3
        passed = sum([freshness_ok, values_ok, consistency_ok])
        overall_score = passed / total_checks

        result = ValidationResult(
            is_valid=is_valid,
            freshness_ok=freshness_ok,
            values_ok=values_ok,
            consistency_ok=consistency_ok,
            freshness_issues=freshness_issues,
            value_issues=value_issues,
            consistency_issues=consistency_issues,
            overall_score=overall_score,
        )

        if not is_valid:
            logger.warning(f"Data validation failed (score={overall_score:.0%}): "
                           f"freshness={freshness_issues}, values={value_issues}, "
                           f"consistency={consistency_issues}")

        return result

    def _check_freshness(self) -> list[str]:
        """Check each data source has recent data."""
        issues = []
        today = date.today()

        for source, max_hours in FRESHNESS_HOURS.items():
            last_log = (
                self.db.query(CollectionLog)
                .filter(
                    CollectionLog.collector_name == source,
                    CollectionLog.status.in_(["success", "partial"]),
                )
                .order_by(CollectionLog.completed_at.desc())
                .first()
            )

            if not last_log or not last_log.completed_at:
                # Check if data exists in the actual tables
                has_data = self._source_has_data(source)
                if not has_data:
                    issues.append(f"{source}: 从未采集到数据")
                continue

            hours_since = (datetime.utcnow() - last_log.completed_at).total_seconds() / 3600
            if hours_since > max_hours:
                issues.append(
                    f"{source}: {hours_since:.0f}小时未更新 (阈值{max_hours}h)"
                )

        # Check that risk assessment itself is fresh
        last_risk = (
            self.db.query(RiskAssessment)
            .order_by(RiskAssessment.assessment_date.desc())
            .first()
        )
        if not last_risk or last_risk.assessment_date < today - timedelta(days=1):
            issues.append("风险评估: 超过1天未评估")

        return issues

    def _source_has_data(self, source: str) -> bool:
        """Check if a source has any data in its primary table."""
        table_map = {
            "portwatch": StraitPassage,
            "yahoo_finance": OilPrice,
            "nasa_firms": FireHotspot,
            "ukmto": UKMTOEvent,
            "shipping_index": ShippingIndex,
        }
        table = table_map.get(source)
        if not table:
            return False

        count = self.db.query(func.count(table.id)).scalar()
        return count > 0

    def _check_value_ranges(self) -> list[str]:
        """Check if current values are within expected ranges."""
        issues = []
        today = date.today()

        # Strait passage check
        latest_strait = (
            self.db.query(StraitPassage)
            .order_by(StraitPassage.record_date.desc())
            .first()
        )
        if latest_strait:
            if latest_strait.tanker_vessels:
                lo, hi = EXPECTED_RANGES["strait_tanker"]
                if not (lo <= latest_strait.tanker_vessels <= hi):
                    issues.append(
                        f"油轮通行量异常: {latest_strait.tanker_vessels}艘/日 "
                        f"(正常范围 {lo}-{hi})"
                    )
            if latest_strait.total_vessels:
                lo, hi = EXPECTED_RANGES["strait_total"]
                if not (lo <= latest_strait.total_vessels <= hi):
                    issues.append(
                        f"总通行量异常: {latest_strait.total_vessels}艘/日 "
                        f"(正常范围 {lo}-{hi})"
                    )

        # Oil price check
        latest_oil = (
            self.db.query(OilPrice)
            .order_by(OilPrice.record_date.desc())
            .first()
        )
        if latest_oil:
            if latest_oil.brent_close:
                lo, hi = EXPECTED_RANGES["brent_price"]
                if not (lo <= latest_oil.brent_close <= hi):
                    issues.append(
                        f"布伦特油价异常: ${latest_oil.brent_close:.2f} "
                        f"(正常范围 ${lo}-${hi})"
                    )
            if latest_oil.spread is not None:
                lo, hi = EXPECTED_RANGES["brent_wti_spread"]
                if not (lo <= latest_oil.spread <= hi):
                    issues.append(
                        f"布伦特-WTI价差异常: ${latest_oil.spread:.2f}"
                    )

        # Shipping index check
        latest_shipping = (
            self.db.query(ShippingIndex)
            .order_by(ShippingIndex.record_date.desc())
            .first()
        )
        if latest_shipping and latest_shipping.bdti:
            lo, hi = EXPECTED_RANGES["bdti"]
            if not (lo <= latest_shipping.bdti <= hi):
                issues.append(
                    f"BDTI异常: {latest_shipping.bdti} (正常范围 {lo}-{hi})"
                )

        # Port loading ratio check
        recent_ports = (
            self.db.query(PortLoading)
            .filter(PortLoading.record_date >= today - timedelta(days=7))
            .all()
        )
        for p in recent_ports:
            if p.loading_ratio is not None:
                lo, hi = EXPECTED_RANGES["loading_ratio"]
                if not (lo <= p.loading_ratio <= hi):
                    issues.append(
                        f"港口{p.port_name}装载比异常: {p.loading_ratio:.0%}"
                    )

        return issues

    def _check_consistency(self) -> list[str]:
        """Check cross-source consistency."""
        issues = []
        today = date.today()

        # Check 1: Oil price vs BDTI — should move together
        oil_7d_ago = (
            self.db.query(OilPrice)
            .filter(OilPrice.record_date >= today - timedelta(days=7))
            .order_by(OilPrice.record_date.asc())
            .first()
        )
        oil_latest = (
            self.db.query(OilPrice)
            .order_by(OilPrice.record_date.desc())
            .first()
        )

        shipping_7d_ago = (
            self.db.query(ShippingIndex)
            .filter(ShippingIndex.record_date >= today - timedelta(days=7))
            .order_by(ShippingIndex.record_date.asc())
            .first()
        )
        shipping_latest = (
            self.db.query(ShippingIndex)
            .order_by(ShippingIndex.record_date.desc())
            .first()
        )

        if oil_7d_ago and oil_latest and shipping_7d_ago and shipping_latest:
            if oil_7d_ago.brent_close and oil_latest.brent_close:
                oil_change = (oil_latest.brent_close - oil_7d_ago.brent_close) / oil_7d_ago.brent_close
                if shipping_7d_ago.bdti and shipping_latest.bdti:
                    bdti_change = (shipping_latest.bdti - shipping_7d_ago.bdti) / shipping_7d_ago.bdti
                    # Oil and BDTI typically move in same direction
                    if abs(oil_change) > 0.05 and oil_change * bdti_change < 0:
                        issues.append(
                            f"油价与BDTI背离: 油价{oil_change:+.1%}, BDTI{bdti_change:+.1%}"
                        )

        # Check 2: Strait passage vs port loading — should correlate
        strait_7d = (
            self.db.query(func.avg(StraitPassage.tanker_vessels))
            .filter(
                StraitPassage.record_date >= today - timedelta(days=7),
                StraitPassage.tanker_vessels > 0,
            )
            .scalar()
        )
        strait_prior = (
            self.db.query(func.avg(StraitPassage.tanker_vessels))
            .filter(
                StraitPassage.record_date >= today - timedelta(days=14),
                StraitPassage.record_date < today - timedelta(days=7),
                StraitPassage.tanker_vessels > 0,
            )
            .scalar()
        )

        if strait_7d and strait_prior and strait_prior > 0:
            strait_change = (strait_7d - strait_prior) / strait_prior
            if abs(strait_change) > 0.3:
                issues.append(f"海峡通行量周变化显著: {strait_change:+.1%}")

        return issues

    def close(self):
        if self.db:
            self.db.close()


def get_validator() -> DataValidator:
    return DataValidator()
