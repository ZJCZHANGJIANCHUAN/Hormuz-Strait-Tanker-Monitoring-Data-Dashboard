import pytest
from datetime import date, timedelta

from app.services.risk_engine import RiskEngine, RiskLevel


class TestRiskEngine:

    def test_weights_sum_to_one(self):
        assert abs(sum(RiskEngine.WEIGHTS.values()) - 1.0) < 0.001

    def test_dim_column_map_covers_all_dimensions(self):
        engine = RiskEngine()
        engine.db.close()
        expected = {"海峡通行量", "港口装船量", "油价", "运价指数", "卫星火点", "安全事件"}
        assert set(RiskEngine.DIM_COLUMN_MAP.keys()) == expected

    def test_risk_level_labels(self):
        assert RiskLevel(1).label == "情绪冲击"
        assert RiskLevel(2).label == "中度实质影响"
        assert RiskLevel(3).label == "严重供应冲击"
        assert RiskLevel(4).label == "极端冲击"

    def test_risk_level_colors(self):
        assert RiskLevel(1).color == "#52c41a"
        assert RiskLevel(2).color == "#faad14"
        assert RiskLevel(3).color == "#ff7a45"
        assert RiskLevel(4).color == "#ff4d4f"

    def test_assess_with_strait_data(self, db, sample_strait_data):
        engine = RiskEngine()
        engine.db = db
        result = engine.assess(date.today())
        assert result.level in RiskLevel
        assert 0 <= result.confidence <= 1
        assert len(result.dimensions) == 6
        dim_names = [d.name for d in result.dimensions]
        assert "海峡通行量" in dim_names
        assert result.evidence_summary

    def test_assess_empty_database(self, db):
        engine = RiskEngine()
        engine.db = db
        result = engine.assess(date.today())
        assert result.level == RiskLevel.SENTIMENT_ONLY
        assert result.confidence < 0.5

    def test_eval_strait_passage_baseline(self, db, sample_strait_data):
        engine = RiskEngine()
        engine.db = db
        dim = engine._eval_strait_passage(date.today())
        assert dim.name == "海峡通行量"
        assert dim.score >= 0
        assert len(dim.evidence) > 0

    def test_eval_oil_price_with_data(self, db, sample_oil_data):
        engine = RiskEngine()
        engine.db = db
        dim = engine._eval_oil_price(date.today())
        assert dim.name == "油价"
        assert dim.score >= 0

    def test_eval_oil_price_empty(self, db):
        engine = RiskEngine()
        engine.db = db
        dim = engine._eval_oil_price(date.today())
        assert dim.score == -1
        assert "无近期数据" in dim.evidence[0]

    def test_eval_fire_anomaly(self, db, sample_fire_data):
        engine = RiskEngine()
        engine.db = db
        dim = engine._eval_fire_anomaly(date.today())
        assert dim.name == "卫星火点"
        assert dim.score >= 0

    def test_eval_fire_anomaly_empty(self, db):
        engine = RiskEngine()
        engine.db = db
        dim = engine._eval_fire_anomaly(date.today())
        assert dim.score == 0
        assert "无火点" in dim.evidence[0]

    def test_eval_ukmto_events(self, db, sample_ukmto_data):
        engine = RiskEngine()
        engine.db = db
        dim = engine._eval_ukmto_events(date.today())
        assert dim.name == "安全事件"
        assert dim.score > 0

    def test_eval_ukmto_events_empty(self, db):
        engine = RiskEngine()
        engine.db = db
        dim = engine._eval_ukmto_events(date.today())
        assert dim.score == 0

    def test_eval_port_loading(self, db, sample_port_data):
        engine = RiskEngine()
        engine.db = db
        dim = engine._eval_port_loading(date.today())
        assert dim.name == "港口装船量"
        assert dim.score >= 0

    def test_eval_port_loading_empty(self, db):
        engine = RiskEngine()
        engine.db = db
        dim = engine._eval_port_loading(date.today())
        assert dim.score == -1

    def test_apply_rules_sentiment_only(self, db):
        engine = RiskEngine()
        engine.db = db
        level = engine._apply_rules(date.today(), 2.0)
        assert level == RiskLevel.SENTIMENT_ONLY

    def test_apply_rules_moderate(self, db):
        engine = RiskEngine()
        engine.db = db
        level = engine._apply_rules(date.today(), 4.0)
        assert level == RiskLevel.MODERATE

    def test_apply_rules_severe(self, db):
        engine = RiskEngine()
        engine.db = db
        level = engine._apply_rules(date.today(), 6.0)
        assert level == RiskLevel.SEVERE

    def test_apply_rules_extreme(self, db):
        engine = RiskEngine()
        engine.db = db
        level = engine._apply_rules(date.today(), 8.0)
        assert level == RiskLevel.EXTREME

    def test_calc_confidence_all_available(self):
        from app.services.risk_engine import DimensionScore
        engine = RiskEngine()
        dims = [
            DimensionScore("a", 1.0, 0.2),
            DimensionScore("b", 2.0, 0.2),
            DimensionScore("c", 3.0, 0.2),
        ]
        conf = engine._calc_confidence(dims)
        assert conf == 1.0

    def test_calc_confidence_partial(self):
        from app.services.risk_engine import DimensionScore
        engine = RiskEngine()
        dims = [
            DimensionScore("a", 1.0, 0.2),
            DimensionScore("b", -1, 0.2),  # no data
            DimensionScore("c", 3.0, 0.2),
        ]
        conf = engine._calc_confidence(dims)
        assert conf == 2 / 3

    def test_dimension_score_defaults(self):
        from app.services.risk_engine import DimensionScore
        dim = DimensionScore(name="test", score=5.0, weight=0.2)
        assert dim.name == "test"
        assert dim.score == 5.0
        assert dim.weight == 0.2
        assert dim.evidence == []
