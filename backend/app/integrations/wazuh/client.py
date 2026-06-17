"""
Wazuh REST API v4 client.

Requires WAZUH_URL, WAZUH_USER, WAZUH_PASSWORD in config.
All methods raise WazuhUnavailable when the server can't be reached,
so callers can gracefully degrade rather than crash.
"""
import httpx
import structlog
from app.config import settings

log = structlog.get_logger(__name__)


class WazuhUnavailable(Exception):
    """Raised when the Wazuh manager cannot be reached or is not configured."""


class WazuhClient:
    """
    Thin async wrapper around the Wazuh v4 REST API.

    Each public method obtains a fresh JWT — tokens are short-lived (900 s)
    and caching across async tasks is error-prone, so we keep it simple.
    """

    def _base(self) -> str:
        if not settings.wazuh_url:
            raise WazuhUnavailable("WAZUH_URL is not configured")
        return settings.wazuh_url.rstrip("/")

    async def _token(self) -> str:
        try:
            async with httpx.AsyncClient(verify=settings.wazuh_verify_tls, timeout=10) as http:
                resp = await http.post(
                    f"{self._base()}/security/user/authenticate",
                    auth=(settings.wazuh_user, settings.wazuh_password),
                )
                resp.raise_for_status()
                return resp.json()["data"]["token"]
        except (httpx.HTTPError, KeyError) as exc:
            raise WazuhUnavailable(f"Wazuh authentication failed: {exc}") from exc

    async def _get(self, path: str, *, params: dict | None = None) -> dict:
        token = await self._token()
        try:
            async with httpx.AsyncClient(
                base_url=self._base(),
                headers={"Authorization": f"Bearer {token}"},
                verify=settings.wazuh_verify_tls,
                timeout=30,
            ) as http:
                resp = await http.get(path, params=params or {})
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            raise WazuhUnavailable(f"Wazuh request failed: {exc}") from exc

    async def is_available(self) -> bool:
        """Return True if the Wazuh manager responds to a health probe."""
        if not settings.wazuh_url:
            return False
        try:
            async with httpx.AsyncClient(verify=settings.wazuh_verify_tls, timeout=5) as http:
                resp = await http.get(f"{self._base()}/")
                return resp.status_code < 500
        except Exception:
            return False

    async def get_alerts(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
        q: str | None = None,
    ) -> list[dict]:
        """
        Fetch alerts from Wazuh.  Supports optional query filter `q`
        (Wazuh query syntax, e.g. ``timestamp>2024-01-01T00:00:00``).
        """
        params: dict = {"limit": min(limit, 500), "offset": offset}
        if q:
            params["q"] = q
        body = await self._get("/alerts", params=params)
        return body.get("data", {}).get("affected_items", [])

    async def get_agents(self, *, status: str = "active") -> list[dict]:
        """Fetch Wazuh agents (maps to Endpoints in our model)."""
        body = await self._get("/agents", params={"status": status, "limit": 500})
        return body.get("data", {}).get("affected_items", [])

    async def get_alert_count(self, *, q: str | None = None) -> int:
        """Return total alert count (for pagination)."""
        params: dict = {"limit": 1}
        if q:
            params["q"] = q
        body = await self._get("/alerts", params=params)
        return body.get("data", {}).get("total_affected_items", 0)


wazuh_client = WazuhClient()
