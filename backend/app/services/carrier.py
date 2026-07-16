"""Carrier detection by tracking-number format, and public tracking-page
URL construction. Pure pattern matching -- no network calls, no API keys.

Real-time status polling (poll_status below) is a deliberate stub: this
environment has no UPS/FedEx/USPS/DHL developer credentials, and status
must never be fabricated. When a tenant configures real carrier API
credentials (out of scope here), swap poll_status's body for actual
HTTP calls and flip status_source to "carrier_api" on success -- the
Shipment model and API layer already support that distinction.
"""
import re

# Ordered most-distinctive-first: UPS's "1Z" prefix and USPS's long
# numeric prefixes are unambiguous; bare digit-count patterns for
# FedEx/DHL are checked last since they can overlap with each other.
_PATTERNS = [
    ("ups", re.compile(r"^1Z[0-9A-Z]{16}$", re.IGNORECASE)),
    ("usps", re.compile(r"^(94|93|92|82|70|03|23)\d{18,20}$")),
    ("usps", re.compile(r"^[A-Z]{2}\d{9}US$", re.IGNORECASE)),
    ("fedex", re.compile(r"^\d{12}$")),
    ("fedex", re.compile(r"^\d{15}$")),
    ("fedex", re.compile(r"^\d{20}$")),
    ("dhl", re.compile(r"^\d{10,11}$")),
]

_TRACKING_URL_TEMPLATES = {
    "ups": "https://www.ups.com/track?tracknum={tn}",
    "fedex": "https://www.fedex.com/fedextrack/?trknbr={tn}",
    "usps": "https://tools.usps.com/go/TrackConfirmAction?tLabels={tn}",
    "dhl": "https://www.dhl.com/en/express/tracking.html?AWB={tn}",
}


def detect_carrier(tracking_number: str) -> str:
    """Best-effort guess from the tracking number's shape alone. These
    are common-format heuristics, not authoritative -- callers/users can
    always override the result manually."""
    cleaned = (tracking_number or "").strip().replace(" ", "").upper()
    for carrier, pattern in _PATTERNS:
        if pattern.match(cleaned):
            return carrier
    return "unknown"


def tracking_url(carrier: str, tracking_number: str) -> str | None:
    template = _TRACKING_URL_TEMPLATES.get(carrier)
    if not template or not tracking_number:
        return None
    return template.format(tn=tracking_number.strip())


def poll_status(shipment):
    """Attempts a live carrier status poll. Returns (ok, status, note).

    No carrier API credentials are configured in this environment, so
    this always reports that plainly rather than inventing a status --
    the UI surfaces `note` and leaves the existing manual status alone.
    """
    return False, None, (
        f"No {shipment.carrier.upper()} API credentials configured for this tenant. "
        "Update status manually, or use the tracking link to check the carrier's site."
    )
