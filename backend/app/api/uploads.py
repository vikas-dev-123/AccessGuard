from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_any_user, require_auditor
from app.db import get_db
from app.models import Dataset, User
from app.schemas import DatasetOut
from app.services.ingest import UploadedFile, UploadValidationError, parse_upload, save_dataset
from app.settings import settings

router = APIRouter(tags=["uploads"])


def _read(upload: UploadFile) -> UploadedFile:
    # Read one byte past the limit so oversize files are detected without loading them fully.
    return UploadedFile(upload.filename or "", upload.file.read(settings.max_upload_bytes + 1))


def _provided(upload: UploadFile | None) -> bool:
    return upload is not None and bool(upload.filename)


@router.post("/upload", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
def upload_files(
    hr_file: UploadFile = File(..., description="HR master export (hr_employees.csv)"),
    core_banking_file: UploadFile | None = File(None),
    loan_system_file: UploadFile | None = File(None),
    database_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_auditor),
):
    candidates = {"core_banking": core_banking_file, "loan_system": loan_system_file, "database": database_file}
    system_files = {system: _read(f) for system, f in candidates.items() if _provided(f)}
    hr_upload = _read(hr_file)

    try:
        hr, systems = parse_upload(hr_upload, system_files)
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": f"Upload rejected: {len(exc.errors)} problem(s) found.", "errors": exc.errors},
        )

    file_names = {"hr": hr_upload.filename} | {s: f.filename for s, f in system_files.items()}
    return save_dataset(db, hr, systems, file_names, uploaded_by=user.username)


@router.get("/datasets", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db), _: User = Depends(require_any_user)):
    return db.scalars(select(Dataset).order_by(Dataset.id.desc())).all()


def get_dataset_or_404(db: Session, dataset_id: int) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return dataset
