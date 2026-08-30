"""Live-ingest readiness checks. No EDGAR download unless explicitly requested."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fintruth.config import Settings, get_settings

logger = logging.getLogger(__name__)

PLACEHOLDER_MARKERS = (
    "contact@example.com",
    "your@email",
    "changeme",
    "todo@",
)


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    """One named readiness check."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class PreflightResult:
    """Aggregate ingest readiness."""

    checks: tuple[PreflightCheck, ...]
    ready: bool

    def lines(self) -> list[str]:
        """Human-readable summary lines."""
        rows = [f"[{'ok' if c.ok else 'FAIL'}] {c.name}: {c.detail}" for c in self.checks]
        rows.append("ready" if self.ready else "not ready — fix FAIL rows before live ingest")
        return rows


def user_agent_is_placeholder(user_agent: str) -> bool:
    """True if the SEC identity still looks like the committed example."""
    ua = (user_agent or "").strip().lower()
    if len(ua) < 12:
        return True
    return any(marker in ua for marker in PLACEHOLDER_MARKERS)


def check_user_agent(settings: Settings) -> PreflightCheck:
    """SEC fair-access policy requires a descriptive User-Agent with contact."""
    ua = settings.sec_user_agent
    if not ua.strip():
        return PreflightCheck("sec_user_agent", False, "SEC_USER_AGENT is empty")
    if user_agent_is_placeholder(ua):
        return PreflightCheck(
            "sec_user_agent",
            False,
            "SEC_USER_AGENT still looks like .env.example; set a real name + email",
        )
    return PreflightCheck("sec_user_agent", True, ua)


def check_edgartools() -> PreflightCheck:
    """Confirm the ingest dependency is importable."""
    try:
        import edgar  # noqa: F401
    except ImportError as exc:
        return PreflightCheck("edgartools", False, f"not importable ({exc})")
    return PreflightCheck("edgartools", True, "importable")


def check_data_dirs(settings: Settings) -> PreflightCheck:
    """Ensure raw/processed parents exist or can be created."""
    raw = settings.data_raw_dir
    processed = settings.data_processed_dir
    try:
        raw.mkdir(parents=True, exist_ok=True)
        processed.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return PreflightCheck("data_dirs", False, str(exc))
    return PreflightCheck("data_dirs", True, f"raw={raw} processed={processed}")


def check_sec_reachable(settings: Settings, timeout_s: float = 8.0) -> PreflightCheck:
    """Optional GET against data.sec.gov (fair-access User-Agent required)."""
    url = "https://data.sec.gov/submissions/CIK0000320193.json"
    try:
        import httpx
    except ImportError:
        return PreflightCheck("sec_network", False, "httpx not installed")
    headers = {"User-Agent": settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"}
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
        if resp.status_code == 200:
            return PreflightCheck("sec_network", True, f"HTTP {resp.status_code} {url}")
        return PreflightCheck(
            "sec_network",
            False,
            f"HTTP {resp.status_code} from data.sec.gov — check User-Agent / rate limit",
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        return PreflightCheck("sec_network", False, f"{type(exc).__name__}: {exc}")


def run_preflight(
    settings: Settings | None = None,
    *,
    check_network: bool = False,
) -> PreflightResult:
    """Run local readiness checks. Network is opt-in so unit tests stay offline."""
    cfg = settings or get_settings()
    checks: list[PreflightCheck] = [
        check_user_agent(cfg),
        check_edgartools(),
        check_data_dirs(cfg),
    ]
    if check_network:
        checks.append(check_sec_reachable(cfg))
    required = [c for c in checks if c.name != "sec_network"]
    ready = all(c.ok for c in required)
    if check_network:
        ready = ready and all(c.ok for c in checks)
    return PreflightResult(checks=tuple(checks), ready=ready)
