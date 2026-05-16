"""Proxy pool management API — CRUD, health checks, stats, and admin controls.

Endpoints:
  POST /api/proxies/              — add proxy
  POST /api/proxies/bulk          — bulk add proxies
  GET  /api/proxies/              — list proxies (filterable)
  GET  /api/proxies/stats         — pool aggregate stats
  GET  /api/proxies/countries     — available countries
  GET  /api/proxies/{id}          — single proxy health
  GET  /api/proxies/country/{cc}  — proxies by country
  PUT  /api/proxies/{id}/reactivate — reactivate proxy
  DELETE /api/proxies/{id}        — soft-delete proxy
  POST /api/proxies/reset-rate-limited — reset all rate-limited proxies
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from configs.settings import settings
from models.proxy import ProxyProtocol, ProxyStatus
from services.proxy_manager import ProxyManager

router = APIRouter(prefix="/api/proxies", tags=["proxies"])

_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
_SyncSession = sessionmaker(bind=_engine)


def _get_sync_db() -> Session:
    db = _SyncSession()
    try:
        yield db
    finally:
        db.close()


# ── request/response schemas ────────────────────────────────

class ProxyCreate(BaseModel):
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    protocol: str = Field(default="http")
    username: str | None = None
    password: str | None = None
    country: str | None = Field(default=None, max_length=10)
    provider: str | None = Field(default=None, max_length=100)
    label: str | None = Field(default=None, max_length=255)


class BulkProxyCreate(BaseModel):
    proxies: list[ProxyCreate]


class ProxyResponse(BaseModel):
    id: int
    host: str
    port: int
    protocol: str
    status: str
    country: str | None = None
    provider: str | None = None
    label: str | None = None
    username: str | None = None
    success_count: int
    fail_count: int
    success_rate_pct: float
    avg_response_ms: int | None = None
    last_used_at: str | None = None
    created_at: str | None = None


class ProxyHealthResponse(BaseModel):
    proxy_id: int
    host: str
    port: int
    protocol: str
    status: str
    country: str | None = None
    provider: str | None = None
    success_count: int
    fail_count: int
    total_requests: int
    success_rate_pct: float
    avg_response_ms: int | None = None
    last_used_at: str | None = None
    last_checked_at: str | None = None


class PoolStatsResponse(BaseModel):
    total_proxies: int
    by_status: dict[str, int]
    by_country: dict[str, int]
    by_protocol: dict[str, int]
    total_requests: int
    total_success: int
    total_fail: int
    overall_success_rate_pct: float


class CountryEntry(BaseModel):
    country: str
    active_count: int


class ReactivateRequest(BaseModel):
    reset_stats: bool = False


class MessageResponse(BaseModel):
    message: str
    count: int | None = None


# ── endpoints ───────────────────────────────────────────────

@router.post("/", response_model=ProxyResponse, status_code=201)
def add_proxy(body: ProxyCreate, db: Session = Depends(_get_sync_db)):
    """Add a new proxy to the pool."""
    mgr = ProxyManager(db)
    try:
        protocol = ProxyProtocol(body.protocol)
    except ValueError:
        raise HTTPException(400, f"Invalid protocol: {body.protocol}")

    proxy = mgr.add_proxy(
        host=body.host,
        port=body.port,
        protocol=protocol,
        username=body.username,
        password=body.password,
        country=body.country,
        provider=body.provider,
        label=body.label,
    )
    db.commit()
    return ProxyResponse(**mgr._proxy_to_dict(proxy))


@router.post("/bulk", response_model=list[ProxyResponse], status_code=201)
def bulk_add_proxies(body: BulkProxyCreate, db: Session = Depends(_get_sync_db)):
    """Add multiple proxies at once."""
    mgr = ProxyManager(db)
    entries = []
    for p in body.proxies:
        try:
            protocol = ProxyProtocol(p.protocol)
        except ValueError:
            raise HTTPException(400, f"Invalid protocol: {p.protocol}")
        entries.append({
            "host": p.host,
            "port": p.port,
            "protocol": protocol,
            "username": p.username,
            "password": p.password,
            "country": p.country,
            "provider": p.provider,
            "label": p.label,
        })

    proxies = mgr.bulk_add_proxies(entries)
    return [ProxyResponse(**mgr._proxy_to_dict(p)) for p in proxies]


@router.get("/", response_model=list[ProxyResponse])
def list_proxies(
    status: str | None = Query(default=None),
    country: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(_get_sync_db),
):
    """List proxies with optional filters."""
    mgr = ProxyManager(db)
    status_enum = None
    if status:
        try:
            status_enum = ProxyStatus(status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    proxies = mgr.list_proxies(
        status=status_enum,
        country=country,
        provider=provider,
        limit=limit,
        offset=offset,
    )
    return [ProxyResponse(**p) for p in proxies]


@router.get("/stats", response_model=PoolStatsResponse)
def pool_stats(db: Session = Depends(_get_sync_db)):
    """Get aggregate stats for the proxy pool."""
    mgr = ProxyManager(db)
    return PoolStatsResponse(**mgr.get_pool_stats())


@router.get("/countries", response_model=list[CountryEntry])
def available_countries(db: Session = Depends(_get_sync_db)):
    """List countries with available active proxies."""
    mgr = ProxyManager(db)
    return [CountryEntry(**c) for c in mgr.get_available_countries()]


@router.get("/country/{country_code}", response_model=list[ProxyResponse])
def proxies_by_country(country_code: str, db: Session = Depends(_get_sync_db)):
    """Get proxies available in a specific country."""
    mgr = ProxyManager(db)
    proxies = mgr.get_proxies_by_country(country_code)
    return [ProxyResponse(**p) for p in proxies]


@router.get("/{proxy_id}", response_model=ProxyHealthResponse)
def proxy_health(proxy_id: int, db: Session = Depends(_get_sync_db)):
    """Get health metrics for a single proxy."""
    mgr = ProxyManager(db)
    try:
        return ProxyHealthResponse(**mgr.check_proxy_health(proxy_id))
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.put("/{proxy_id}/reactivate", response_model=MessageResponse)
def reactivate_proxy(
    proxy_id: int,
    body: ReactivateRequest = ReactivateRequest(),
    db: Session = Depends(_get_sync_db),
):
    """Reactivate a banned/rate-limited/inactive proxy."""
    mgr = ProxyManager(db)
    ok = mgr.reactivate_proxy(proxy_id, reset_stats=body.reset_stats)
    if not ok:
        raise HTTPException(404, f"Proxy {proxy_id} not found")
    db.commit()
    return MessageResponse(message=f"Proxy {proxy_id} reactivated")


@router.delete("/{proxy_id}", response_model=MessageResponse)
def remove_proxy(proxy_id: int, db: Session = Depends(_get_sync_db)):
    """Soft-delete a proxy from the pool."""
    mgr = ProxyManager(db)
    ok = mgr.remove_proxy(proxy_id)
    if not ok:
        raise HTTPException(404, f"Proxy {proxy_id} not found")
    db.commit()
    return MessageResponse(message=f"Proxy {proxy_id} removed")


@router.post("/reset-rate-limited", response_model=MessageResponse)
def reset_rate_limited(db: Session = Depends(_get_sync_db)):
    """Reset all RATE_LIMITED proxies back to ACTIVE."""
    mgr = ProxyManager(db)
    count = mgr.reset_rate_limited_proxies()
    db.commit()
    return MessageResponse(message=f"Reset {count} rate-limited proxies", count=count)
