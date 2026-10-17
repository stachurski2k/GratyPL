from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import FeedPage, feed_item
from app.services import feed

router = APIRouter(prefix="/api/feed", tags=["feed"])


@router.get("")
def list_feed(
    session: Annotated[Session, Depends(get_session)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=feed.MAX_LIMIT)] = feed.DEFAULT_LIMIT,
) -> FeedPage:
    result = feed.list_feed(session, limit=limit, cursor=cursor)
    return FeedPage(items=[feed_item(i) for i in result.items], next_cursor=result.next_cursor)
