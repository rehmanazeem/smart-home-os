"""OTA access control: private/VPN client IPs or a shared API key."""

import ipaddress
import os

from fastapi import Request

ALLOWED_PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
)


def is_private_ip(ip: str) -> bool:
    """Return True if ``ip`` parses and lies in one of the allowed private ranges."""
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in ALLOWED_PRIVATE_NETWORKS)
    except Exception:
        return False


def check_access(request: Request) -> bool:
    """Permit only if request client IP is private (VPN) or the correct API key is provided."""
    api_key = os.environ.get("SMARTHOME_API_KEY")
    # check API key header first
    if api_key:
        header = request.headers.get("x-api-key") or request.headers.get("X-API-KEY")
        if header and header == api_key:
            return True

    # fallback to client IP check
    client_host = request.client.host if request.client else None
    if client_host and is_private_ip(client_host):
        return True

    return False
