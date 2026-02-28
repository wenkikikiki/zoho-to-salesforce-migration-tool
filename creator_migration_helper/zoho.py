"""Zoho Creator metadata API client."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


class ZohoAPIError(RuntimeError):
    """Raised when Zoho API calls fail."""


def _quote(value: str) -> str:
    return parse.quote(value, safe="")


@dataclass(slots=True)
class ZohoClient:
    """Minimal client for Zoho Creator metadata APIs."""

    base_url: str
    owner: str
    app: str
    token: str
    environment: str | None = None
    timeout_seconds: int = 30

    def get_forms(self) -> list[dict[str, Any]]:
        payload = self._request(
            f"/creator/v2.1/meta/{_quote(self.owner)}/{_quote(self.app)}/form"
        )
        forms = payload.get("forms", [])
        if not isinstance(forms, list):
            raise ZohoAPIError("Zoho response did not include a valid `forms` list")
        return forms

    def get_fields(self, form_link_name: str) -> list[dict[str, Any]]:
        payload = self._request(
            f"/creator/v2.1/meta/{_quote(self.owner)}/{_quote(self.app)}/form/{_quote(form_link_name)}/fields"
        )
        fields = payload.get("fields", [])
        if not isinstance(fields, list):
            raise ZohoAPIError(
                f"Zoho response did not include a valid `fields` list for form `{form_link_name}`"
            )
        return fields

    def _request(self, path: str) -> dict[str, Any]:
        base = self.base_url.strip().rstrip("/")
        if base.startswith("http://") or base.startswith("https://"):
            url = f"{base}{path}"
        else:
            url = f"https://{base}{path}"

        headers = {
            "Authorization": f"Zoho-oauthtoken {self.token}",
            "Accept": "application/json",
        }
        if self.environment:
            headers["environment"] = self.environment

        req = request.Request(url=url, headers=headers, method="GET")
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read()
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ZohoAPIError(
                f"Zoho API request failed ({exc.code}) for {path}: {body}"
            ) from exc
        except error.URLError as exc:
            raise ZohoAPIError(f"Could not reach Zoho API for {path}: {exc}") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ZohoAPIError(f"Invalid JSON returned by Zoho for {path}") from exc

        if isinstance(payload, dict):
            code = payload.get("code")
            # Zoho success code for metadata APIs is 3000.
            if code is not None and str(code) != "3000":
                message = payload.get("message", "unknown error")
                raise ZohoAPIError(f"Zoho API returned code {code}: {message}")
            return payload

        raise ZohoAPIError(f"Unexpected Zoho API response shape for {path}")
