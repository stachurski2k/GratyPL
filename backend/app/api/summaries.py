from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import SummaryOut
from app.services import summaries

router = APIRouter(prefix="/api/summaries", tags=["summaries"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/generate", status_code=201)
def generate_summary(
    session: SessionDep,
    week_start: Annotated[date, Query(description="Poniedziałek tygodnia (czas warszawski)")],
    force: bool = False,
) -> SummaryOut:
    return SummaryOut.from_model(summaries.generate_summary(session, week_start, force=force))


@router.get("/{week_start}")
def get_summary(session: SessionDep, week_start: date) -> SummaryOut:
    return SummaryOut.from_model(summaries.get_summary(session, week_start))
