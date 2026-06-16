from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RiskAssessment
from app.services.risk_engine import get_risk_engine
from app.services.data_validator import get_validator

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/assessment")
def get_assessment(days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    assessments = (
        db.query(RiskAssessment)
        .order_by(RiskAssessment.assessment_date.desc())
        .limit(days)
        .all()
    )
    return {
        "data": [
            {
                "date": str(a.assessment_date),
                "level": a.risk_level,
                "label": a.risk_level_label,
                "confidence": a.confidence_score,
                "evidence": a.evidence_summary,
            }
            for a in assessments
        ]
    }


@router.post("/assess")
def run_assessment():
    # Validate data before assessment
    validator = get_validator()
    validation = validator.validate()
    validator.close()

    engine = get_risk_engine()
    result = engine.assess(date.today())
    return {
        "level": result.level.value,
        "label": result.label,
        "color": result.color,
        "confidence": result.confidence,
        "weighted_score": round(result.weighted_score, 2),
        "evidence": result.evidence_summary,
        "dimensions": [
            {"name": d.name, "score": round(d.score, 1), "evidence": d.evidence}
            for d in result.dimensions
        ],
        "validation": {
            "is_valid": validation.is_valid,
            "score": round(validation.overall_score, 2),
            "freshness_issues": validation.freshness_issues,
            "value_issues": validation.value_issues,
            "consistency_issues": validation.consistency_issues,
        },
    }


@router.get("/validation")
def get_validation():
    validator = get_validator()
    result = validator.validate()
    validator.close()
    return {
        "is_valid": result.is_valid,
        "score": round(result.overall_score, 2),
        "freshness_ok": result.freshness_ok,
        "values_ok": result.values_ok,
        "consistency_ok": result.consistency_ok,
        "freshness_issues": result.freshness_issues,
        "value_issues": result.value_issues,
        "consistency_issues": result.consistency_issues,
    }
