import logging
from datetime import date, timedelta
from enum import IntEnum
from dataclasses import dataclass, field

from sqlalchemy import func
from app.database import SessionLocal
from app.models import (
    StraitPassage, PortLoading, OilPrice, ShippingIndex,
    FireHotspot, UKMTOEvent, RiskAssessment,
)

logger = logging.getLogger(__name__)


class RiskLevel(IntEnum):
    SENTIMENT_ONLY = 1
    MODERATE = 2
    SEVERE = 3
    EXTREME = 4

    @property
    def label(self) -> str:
        return {
            1: "情绪冲击",
            2: "中度实质影响",
            3: "严重供应冲击",
            4: "极端冲击",
        }[self.value]

    @property
    def color(self) -> str:
        return {1: "#52c41a", 2: "#faad14", 3: "#ff7a45", 4: "#ff4d4f"}[self.value]


@dataclass
class DimensionScore:
    name: str
    score: float
    weight: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class AssessmentResult:
    level: RiskLevel
    label: str
    color: str
    confidence: float
    weighted_score: float
    dimensions: list[DimensionScore]
    evidence_summary: str


class RiskEngine:
    WEIGHTS = {
        "strait_passage": 0.25,
        "port_loading": 0.20,
        "oil_price": 0.15,
        "shipping_index": 0.15,
        "fire_anomaly": 0.10,
        "ukmto_events": 0.15,
    }

    # Map Chinese dimension names to DB column names
    DIM_COLUMN_MAP = {
        "海峡通行量": "strait_passage_score",
        "港口装船量": "port_loading_score",
        "油价": "oil_price_score",
        "运价指数": "shipping_index_score",
        "卫星火点": "fire_anomaly_score",
        "安全事件": "ukmto_event_score",
    }

    def __init__(self):
        self.db = SessionLocal()

    def assess(self, assessment_date: date | None = None) -> AssessmentResult:
        if assessment_date is None:
            assessment_date = date.today()

        try:
            dims = [
                self._eval_strait_passage(assessment_date),
                self._eval_port_loading(assessment_date),
                self._eval_oil_price(assessment_date),
                self._eval_shipping_index(assessment_date),
                self._eval_fire_anomaly(assessment_date),
                self._eval_ukmto_events(assessment_date),
            ]

            weighted_score = sum(d.score * d.weight for d in dims)
            available_weight = sum(d.weight for d in dims if d.score >= 0)
            if available_weight > 0:
                adjusted_score = sum(d.score * d.weight for d in dims if d.score >= 0) / available_weight
            else:
                adjusted_score = weighted_score

            level = self._apply_rules(assessment_date, adjusted_score)

            evidence_parts = []
            for d in dims:
                if d.evidence:
                    evidence_parts.append(f"【{d.name}】" + "；".join(d.evidence))
            evidence_summary = "\n".join(evidence_parts) if evidence_parts else "数据不足，无法判定"

            confidence = self._calc_confidence(dims)

            result = AssessmentResult(
                level=level,
                label=level.label,
                color=level.color,
                confidence=confidence,
                weighted_score=adjusted_score,
                dimensions=dims,
                evidence_summary=evidence_summary,
            )

            self._save_assessment(assessment_date, result)
            return result

        finally:
            self.db.close()

    def _eval_strait_passage(self, assessment_date: date) -> DimensionScore:
        baseline_30d = self._get_baseline_strait(assessment_date, 30)
        yesterday = assessment_date - timedelta(days=1)

        current = (
            self.db.query(StraitPassage)
            .filter(StraitPassage.record_date == yesterday)
            .order_by(StraitPassage.created_at.desc())
            .first()
        )

        if not current or not current.tanker_vessels or not baseline_30d:
            return DimensionScore("海峡通行量", -1, self.WEIGHTS["strait_passage"], ["无近期数据"])

        tanker_count = current.tanker_vessels
        decline = (baseline_30d - tanker_count) / baseline_30d if baseline_30d > 0 else 0
        score = min(10, max(0, decline * 20))

        evidence = [
            f"昨日油轮通行 {tanker_count} 艘 (IMF PortWatch AIS数据)",
            f"30日均值 {baseline_30d:.0f} 艘",
            f"偏离 {decline:.1%}",
        ]
        if current.total_vessels:
            evidence.append(f"总通行 {current.total_vessels} 艘")

        return DimensionScore("海峡通行量", score, self.WEIGHTS["strait_passage"], evidence)

    # IEA baseline: Persian Gulf oil ports average loading ratio ~79%
    IEA_PORT_RATIO = 0.79

    def _eval_port_loading(self, assessment_date: date) -> DimensionScore:
        yesterday = assessment_date - timedelta(days=1)
        lookback = assessment_date - timedelta(days=7)

        recent = (
            self.db.query(PortLoading)
            .filter(PortLoading.record_date >= lookback, PortLoading.record_date <= yesterday)
            .all()
        )

        if not recent:
            return DimensionScore("港口装船量", -1, self.WEIGHTS["port_loading"], ["无近期数据"])

        avg_ratio = sum(r.loading_ratio for r in recent if r.loading_ratio) / max(len([r for r in recent if r.loading_ratio]), 1)

        # Compare against IEA baseline (79%)
        deviation = self.IEA_PORT_RATIO - avg_ratio

        if avg_ratio > 0.70:
            score = 1
            evidence = [f"装载比 {avg_ratio:.0%} (IEA基准: {self.IEA_PORT_RATIO:.0%})，港口活跃正常"]
        elif avg_ratio > 0.50:
            score = 4
            evidence = [f"装载比 {avg_ratio:.0%} (IEA基准: {self.IEA_PORT_RATIO:.0%})，装船活动有所下降"]
        elif avg_ratio > 0.30:
            score = 7
            evidence = [f"装载比 {avg_ratio:.0%} (IEA基准: {self.IEA_PORT_RATIO:.0%})，装船活动明显减少"]
        else:
            score = 9
            evidence = [f"装载比 {avg_ratio:.0%} (IEA基准: {self.IEA_PORT_RATIO:.0%})，港口装船严重受限"]

        evidence.append(f"近7日 {len(recent)} 条港口记录 ({len(set(r.port_name for r in recent))} 个港口)")
        return DimensionScore("港口装船量", score, self.WEIGHTS["port_loading"], evidence)

    def _eval_oil_price(self, assessment_date: date) -> DimensionScore:
        lookback = assessment_date - timedelta(days=5)

        prices = (
            self.db.query(OilPrice)
            .filter(OilPrice.record_date >= lookback, OilPrice.record_date <= assessment_date)
            .order_by(OilPrice.record_date.asc())
            .all()
        )

        if len(prices) < 2:
            return DimensionScore("油价", -1, self.WEIGHTS["oil_price"], ["无近期数据"])

        first = prices[0].brent_close or 0
        last = prices[-1].brent_close or 0
        if first == 0:
            score = 3
            evidence = ["油价数据不完整"]
        else:
            change_pct = (last - first) / first
            if change_pct > 0.05:
                score = 8
                evidence = [f"布伦特 {last:.2f}，5日涨幅 {change_pct:.1%}", "油价显著上涨"]
            elif change_pct > 0.02:
                score = 5
                evidence = [f"布伦特 {last:.2f}，5日涨幅 {change_pct:.1%}", "油价温和上涨"]
            elif change_pct > 0:
                score = 3
                evidence = [f"布伦特 {last:.2f}，5日涨幅 {change_pct:.1%}"]
            else:
                score = 1
                evidence = [f"布伦特 {last:.2f}，5日变化 {change_pct:.1%}"]

        if prices[-1].spread:
            spread = prices[-1].spread
            evidence.append(f"布伦特-WTI价差 ${spread:.2f}")

        return DimensionScore("油价", score, self.WEIGHTS["oil_price"], evidence)

    def _eval_shipping_index(self, assessment_date: date) -> DimensionScore:
        yesterday = assessment_date - timedelta(days=1)
        shipping = (
            self.db.query(ShippingIndex)
            .filter(ShippingIndex.record_date >= assessment_date - timedelta(days=5))
            .order_by(ShippingIndex.record_date.desc())
            .first()
        )

        if not shipping or not shipping.bdti:
            return DimensionScore("运价指数", -1, self.WEIGHTS["shipping_index"], ["无运价数据，请手动录入"])

        evidence = [f"BDTI: {shipping.bdti}"]
        if shipping.td3c:
            evidence.append(f"TD3C: {shipping.td3c}")

        if shipping.bdti > 1500:
            score = 8
            evidence.append("BDTI处于高位")
        elif shipping.bdti > 1200:
            score = 5
            evidence.append("BDTI偏高")
        else:
            score = 2

        return DimensionScore("运价指数", score, self.WEIGHTS["shipping_index"], evidence)

    def _eval_fire_anomaly(self, assessment_date: date) -> DimensionScore:
        yesterday = assessment_date - timedelta(days=1)
        lookback = assessment_date - timedelta(days=3)

        fires = (
            self.db.query(FireHotspot)
            .filter(FireHotspot.detection_time >= lookback)
            .all()
        )

        if not fires:
            return DimensionScore("卫星火点", 0, self.WEIGHTS["fire_anomaly"], ["近3日无火点检测"])

        high_conf = [f for f in fires if f.confidence == "high"]
        facility_counts = {}
        for f in fires:
            if f.facility_name and f.facility_name != "Unmapped":
                facility_counts[f.facility_name] = facility_counts.get(f.facility_name, 0) + 1

        evidence = [f"近3日检测到 {len(fires)} 个火点"]
        if high_conf:
            evidence.append(f"高置信度 {len(high_conf)} 个")
        if facility_counts:
            evidence.append(f"涉及设施: {', '.join(facility_counts.keys())}")

        score = min(10, len(fires) * 2 + len(high_conf) * 3)
        return DimensionScore("卫星火点", score, self.WEIGHTS["fire_anomaly"], evidence)

    def _eval_ukmto_events(self, assessment_date: date) -> DimensionScore:
        lookback = assessment_date - timedelta(days=7)

        events = (
            self.db.query(UKMTOEvent)
            .filter(UKMTOEvent.event_date >= lookback)
            .all()
        )

        if not events:
            return DimensionScore("安全事件", 0, self.WEIGHTS["ukmto_events"], ["近7日无安全事件记录"])

        severity_weight = {"critical": 5, "high": 3, "medium": 2, "low": 1}
        weighted = sum(severity_weight.get(e.severity, 1) for e in events)

        score = min(10, weighted)
        types = set(e.event_type for e in events)
        evidence = [
            f"近7日 {len(events)} 起事件",
            f"类型: {', '.join(types)}",
        ]
        return DimensionScore("安全事件", score, self.WEIGHTS["ukmto_events"], evidence)

    def _apply_rules(self, assessment_date: date, weighted_score: float) -> RiskLevel:
        yesterday = assessment_date - timedelta(days=1)

        # Check for extreme: strait passage collapse
        passage = (
            self.db.query(StraitPassage)
            .filter(StraitPassage.record_date == yesterday)
            .first()
        )
        baseline = self._get_baseline_strait(assessment_date, 30)

        massive_passage_drop = False
        if passage and passage.tanker_vessels and baseline and baseline > 0:
            decline = (baseline - passage.tanker_vessels) / baseline
            if decline > 0.8:
                massive_passage_drop = True

        # Check consecutive export drops
        consecutive_drops = self._count_consecutive_passage_drops(assessment_date)

        # Check sustained oil price
        oil_sustained = self._is_oil_sustained_high(assessment_date)

        if massive_passage_drop and consecutive_drops >= 7:
            return RiskLevel.EXTREME

        if consecutive_drops >= 7 and oil_sustained:
            return RiskLevel.SEVERE

        if consecutive_drops >= 3:
            return RiskLevel.MODERATE

        if weighted_score < 3:
            return RiskLevel.SENTIMENT_ONLY
        elif weighted_score < 5.5:
            return RiskLevel.MODERATE
        elif weighted_score < 7.5:
            return RiskLevel.SEVERE
        else:
            return RiskLevel.EXTREME

    def _get_baseline_strait(self, assessment_date: date, days: int) -> float | None:
        start_date = assessment_date - timedelta(days=days)
        avg = (
            self.db.query(func.avg(StraitPassage.tanker_vessels))
            .filter(
                StraitPassage.record_date >= start_date,
                StraitPassage.record_date < assessment_date,
                StraitPassage.tanker_vessels > 0,
            )
            .scalar()
        )
        return float(avg) if avg else None

    def _count_consecutive_passage_drops(self, assessment_date: date) -> int:
        baseline = self._get_baseline_strait(assessment_date, 30)
        if not baseline:
            return 0

        count = 0
        for i in range(1, 15):
            d = assessment_date - timedelta(days=i)
            row = (
                self.db.query(StraitPassage)
                .filter(StraitPassage.record_date == d)
                .first()
            )
            if not row or not row.tanker_vessels:
                continue
            if (baseline - row.tanker_vessels) / baseline > 0.3:
                count += 1
            else:
                break
        return count

    def _is_oil_sustained_high(self, assessment_date: date) -> bool:
        prices = (
            self.db.query(OilPrice)
            .filter(OilPrice.record_date >= assessment_date - timedelta(days=7))
            .order_by(OilPrice.record_date.asc())
            .all()
        )
        if len(prices) < 3:
            return False
        first = prices[0].brent_close or 0
        last = prices[-1].brent_close or 0
        if first == 0:
            return False
        return (last - first) / first > 0.05

    def _calc_confidence(self, dims: list[DimensionScore]) -> float:
        available = sum(1 for d in dims if d.score >= 0)
        total = len(dims)
        if total == 0:
            return 0.0
        return min(1.0, available / total)

    def _save_assessment(self, assessment_date: date, result: AssessmentResult):
        try:
            existing = (
                self.db.query(RiskAssessment)
                .filter(RiskAssessment.assessment_date == assessment_date)
                .first()
            )
            if existing:
                existing.risk_level = result.level.value
                existing.risk_level_label = result.label
                existing.confidence_score = result.confidence
                existing.evidence_summary = result.evidence_summary
                for d in result.dimensions:
                    col = self.DIM_COLUMN_MAP.get(d.name)
                    if col:
                        setattr(existing, col, d.score if d.score >= 0 else None)
            else:
                attrs = {
                    "assessment_date": assessment_date,
                    "risk_level": result.level.value,
                    "risk_level_label": result.label,
                    "confidence_score": result.confidence,
                    "evidence_summary": result.evidence_summary,
                }
                for d in result.dimensions:
                    col = self.DIM_COLUMN_MAP.get(d.name)
                    if col:
                        attrs[col] = d.score if d.score >= 0 else None
                assessment = RiskAssessment(**attrs)
                self.db.add(assessment)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to save risk assessment: {e}")
            self.db.rollback()


def get_risk_engine() -> RiskEngine:
    return RiskEngine()
