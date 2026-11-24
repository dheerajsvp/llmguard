"""The HTTP layer. A thin wrapper: all real logic lives in Guard and AuditLog."""

import hmac
import logging
from collections.abc import Collection
from datetime import UTC, datetime, time, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field, StringConstraints

from llmguard import __version__
from llmguard.audit.chain import StoredRecord
from llmguard.audit.reader import AuditReader
from llmguard.guard import AuditError, Guard, ProviderError

logger = logging.getLogger("llmguard.api")

Doc = Annotated[str, StringConstraints(max_length=50_000)]


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20_000)
    system: str | None = Field(default=None, max_length=10_000)
    documents: list[Doc] = Field(default_factory=list, max_length=20)


class ViolationOut(BaseModel):
    rule_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    blocked: bool
    request_id: str
    violations: list[ViolationOut]
    redactions: dict[str, int]


class EventOut(BaseModel):
    seq: int
    created_at: datetime
    request_id: str
    blocked: bool
    rule_ids: list[str]
    redactions: dict[str, int]
    prompt_sha256: str
    prev_hash: str
    hash: str


class EventsPage(BaseModel):
    events: list[EventOut]
    total: int
    limit: int
    offset: int


class DayOut(BaseModel):
    day: str
    total: int
    blocked: int


class RuleOut(BaseModel):
    rule_id: str
    count: int


class StatsOut(BaseModel):
    since: datetime
    total: int
    blocked: int
    by_day: list[DayOut]
    top_rules: list[RuleOut]


class HeadOut(BaseModel):
    seq: int
    hash: str


class ChainOut(BaseModel):
    ok: bool
    checked: int
    first_bad_seq: int | None
    reason: str
    head: HeadOut | None


def _event_out(r: StoredRecord) -> EventOut:
    return EventOut(
        seq=r.seq,
        created_at=r.created_at,
        request_id=r.event.request_id,
        blocked=r.event.blocked,
        rule_ids=list(r.event.rule_ids),
        redactions=r.event.redactions,
        prompt_sha256=r.event.prompt_sha256,
        prev_hash=r.prev_hash,
        hash=r.hash,
    )


def create_app(
    guard: Guard,
    reader: AuditReader | None,
    chat_keys: Collection[str],
    admin_keys: Collection[str],
) -> FastAPI:
    app = FastAPI(title="llmguard", version=__version__)
    chat_set, admin_set = frozenset(chat_keys), frozenset(admin_keys)

    def matches(key: str | None, keys: frozenset[str]) -> bool:
        if not key:
            return False
        found = False
        for k in keys:  # compare against every key, each comparison in constant time
            found |= hmac.compare_digest(key.encode(), k.encode())
        return found

    def authorize(key: str | None, mine: frozenset[str], other: frozenset[str]) -> None:
        if matches(key, mine):
            return
        if matches(key, other):  # a real key, but for a different role
            raise HTTPException(403, "This key is not allowed to use this endpoint")
        raise HTTPException(
            401, "Missing or invalid API key", headers={"WWW-Authenticate": "ApiKey"}
        )

    def require_chat(x_api_key: Annotated[str | None, Header()] = None) -> None:
        authorize(x_api_key, chat_set, admin_set)

    def require_admin(x_api_key: Annotated[str | None, Header()] = None) -> None:
        authorize(x_api_key, admin_set, chat_set)

    def get_reader() -> AuditReader:
        if reader is None:
            raise HTTPException(503, "Audit log is not configured")
        return reader

    Reader = Annotated[AuditReader, Depends(get_reader)]

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # Plain `def` (not async): Guard makes a blocking network call to the model, and
    # FastAPI runs plain functions in a thread pool so one slow call does not freeze the server.
    @app.post("/v1/chat", response_model=ChatResponse, dependencies=[Depends(require_chat)])
    def chat(req: ChatRequest) -> ChatResponse:
        try:
            result = guard.run(req.prompt, req.system, req.documents)
        except ProviderError as exc:
            # Log only the error *type*: provider messages can echo the prompt.
            logger.error("model provider call failed (%s)", type(exc.__cause__).__name__)
            raise HTTPException(502, "The model provider failed") from None
        except AuditError as exc:
            logger.error("audit write failed (%s)", type(exc.__cause__).__name__)
            raise HTTPException(503, "Audit log unavailable; reply withheld") from None
        return ChatResponse(
            reply=result.reply,
            blocked=result.blocked,
            request_id=result.request_id,
            violations=[
                ViolationOut(rule_id=v.rule_id, message=v.message) for v in result.violations
            ],
            redactions=result.redactions,
        )

    @app.get("/api/events", response_model=EventsPage, dependencies=[Depends(require_admin)])
    def list_events(
        audit: Reader,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        blocked: bool | None = None,
        rule_id: Annotated[str | None, Query(max_length=64)] = None,
    ) -> EventsPage:
        records, total = audit.list_events(limit, offset, blocked, rule_id)
        return EventsPage(
            events=[_event_out(r) for r in records], total=total, limit=limit, offset=offset
        )

    @app.get(
        "/api/events/{request_id}", response_model=EventOut, dependencies=[Depends(require_admin)]
    )
    def get_event(request_id: str, audit: Reader) -> EventOut:
        record = audit.get_event(request_id)
        if record is None:
            raise HTTPException(404, "No such event")
        return _event_out(record)

    @app.get("/api/stats", response_model=StatsOut, dependencies=[Depends(require_admin)])
    def stats(audit: Reader, days: Annotated[int, Query(ge=1, le=90)] = 7) -> StatsOut:
        first_day = datetime.now(UTC).date() - timedelta(days=days - 1)
        since = datetime.combine(first_day, time.min, tzinfo=UTC)
        window = audit.stats(since)
        counts = {d.day: d for d in window.by_day}
        by_day: list[DayOut] = []
        for i in range(days):  # zero-fill so charts have no gaps
            d = first_day + timedelta(days=i)
            c = counts.get(d)
            by_day.append(
                DayOut(day=d.isoformat(), total=c.total if c else 0, blocked=c.blocked if c else 0)
            )
        return StatsOut(
            since=since,
            total=window.total,
            blocked=window.blocked,
            by_day=by_day,
            top_rules=[RuleOut(rule_id=r.rule_id, count=r.count) for r in window.top_rules],
        )

    @app.get("/api/chain", response_model=ChainOut, dependencies=[Depends(require_admin)])
    def chain(audit: Reader) -> ChainOut:
        result = audit.verify_chain()
        head = audit.head()
        return ChainOut(
            ok=result.ok,
            checked=result.checked,
            first_bad_seq=result.first_bad_seq,
            reason=result.reason,
            head=HeadOut(seq=head[0], hash=head[1]) if head else None,
        )

    return app
