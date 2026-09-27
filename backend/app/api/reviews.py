from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.uploads import get_dataset_or_404
from app.auth import require_any_user, require_auditor
from app.checks import RiskRating, get_checks
from app.db import get_db
from app.models import Dataset, Review, User
from app.schemas import CheckOut, FindingsPage, ReviewOut, RunReviewRequest, SummaryOut
from app.services.reviews import query_findings, review_summary, run_review

router = APIRouter(tags=["reviews"])


def get_review_or_404(db: Session, review_id: int) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
    return review


@router.get("/checks", response_model=list[CheckOut])
def list_checks(_: User = Depends(require_any_user)):
    return [CheckOut(code=c.code, name=c.name, criteria=c.criteria, impact=c.impact,
                     recommendation=c.recommendation) for c in get_checks()]


@router.post("/reviews/run", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def run(payload: RunReviewRequest | None = None, db: Session = Depends(get_db),
        user: User = Depends(require_auditor)):
    payload = payload or RunReviewRequest()
    if payload.dataset_id is not None:
        dataset = get_dataset_or_404(db, payload.dataset_id)
    else:
        dataset = db.scalar(select(Dataset).order_by(Dataset.id.desc()).limit(1))
        if dataset is None:
            raise HTTPException(status_code=404, detail="No data uploaded yet. Upload files via POST /upload first.")
    return run_review(db, dataset, payload.as_of_date or date.today(), run_by=user.username)


@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(db: Session = Depends(get_db), _: User = Depends(require_any_user)):
    return db.scalars(select(Review).order_by(Review.id.desc())).all()


@router.get("/reviews/{review_id}", response_model=ReviewOut)
def get_review(review_id: int, db: Session = Depends(get_db), _: User = Depends(require_any_user)):
    return get_review_or_404(db, review_id)


@router.get("/reviews/{review_id}/findings", response_model=FindingsPage)
def list_findings(
    review_id: int,
    system: str | None = Query(None, description="e.g. core_banking; also matches cross-system SoD findings"),
    check: str | None = Query(None, description="Check code, see GET /checks"),
    risk_rating: RiskRating | None = Query(None),
    search: str | None = Query(None, description="Matches username, employee_id, details or finding_id"),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_user),
):
    get_review_or_404(db, review_id)
    valid_codes = {c.code for c in get_checks()}
    if check is not None and check not in valid_codes:
        raise HTTPException(status_code=422, detail=f"Unknown check '{check}'. Valid: {', '.join(sorted(valid_codes))}")
    total, items = query_findings(
        db, review_id, system=system, check=check,
        risk_rating=risk_rating.value if risk_rating else None,
        search=search, limit=limit, offset=offset,
    )
    return FindingsPage(total=total, items=items)


@router.get("/reviews/{review_id}/summary", response_model=SummaryOut)
def get_summary(review_id: int, db: Session = Depends(get_db), _: User = Depends(require_any_user)):
    review = get_review_or_404(db, review_id)
    return SummaryOut(review_id=review.id, **review_summary(db, review))
