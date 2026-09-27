from datetime import date

import pytest

from app.checks import ReviewContext, RiskRating, get_checks
from app.config import BACKEND_DIR, ReviewConfig
from app.data_loading import HR_FILE, load_review_data
from app.review import run_all_checks

DATA_DIR = BACKEND_DIR / "data"
EXTRACT_DATE = date(2026, 9, 27)

pytestmark = pytest.mark.skipif(not (DATA_DIR / HR_FILE).exists(),
                                reason="run scripts/generate_dummy_data.py first")


def test_generated_data_has_15_to_25_exceptions_per_check():
    hr, systems = load_review_data(DATA_DIR)
    findings = run_all_checks(ReviewContext(hr, systems, ReviewConfig(as_of_date=EXTRACT_DATE)))

    for check in get_checks():
        hits = [f for f in findings if f.check_name == check.name]
        if check.code == "privileged_access":
            hits = [f for f in hits if f.risk_rating == RiskRating.HIGH]
        assert 15 <= len(hits) <= 25, f"{check.name}: {len(hits)} exceptions"
