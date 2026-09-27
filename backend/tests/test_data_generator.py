import csv

from app.data_loading import ACCOUNT_REQUIRED_COLUMNS, HR_FILE, HR_REQUIRED_COLUMNS, SYSTEM_FILES
from app.config import BACKEND_DIR
from scripts import generate_dummy_data

FILES = [HR_FILE, *SYSTEM_FILES.values()]


def _lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def test_generator_is_deterministic_and_matches_committed_sample(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    generate_dummy_data.main(first)
    generate_dummy_data.main(second)

    for name in FILES:
        assert _lines(first / name) == _lines(second / name), f"{name} differs between runs"
        assert _lines(first / name) == _lines(BACKEND_DIR / "data" / name), f"{name} differs from committed sample"


def test_generated_files_have_expected_columns(tmp_path):
    generate_dummy_data.main(tmp_path)
    with open(tmp_path / HR_FILE, encoding="utf-8") as f:
        hr = list(csv.DictReader(f))
    assert list(hr[0]) == HR_REQUIRED_COLUMNS
    assert len(hr) == 200

    for name in SYSTEM_FILES.values():
        with open(tmp_path / name, encoding="utf-8") as f:
            assert next(csv.reader(f)) == ACCOUNT_REQUIRED_COLUMNS
