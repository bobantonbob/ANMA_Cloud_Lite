"""Restrict iframe parents to explicitly approved Home Assistant origins."""
from urllib.parse import urlsplit
from django.conf import settings


def _valid_origin(value):
    # A full origin only; no CSP directives, paths, credentials, or fragments.
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("https", "http") or not parsed.hostname:
            return False
        if parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            return False
        if parsed.port is not None and not (0 < parsed.port < 65536):
            return False
        return True
    except ValueError:
        return False


class TrustedFrameAncestorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        origins = [origin for origin in settings.ANMA_FRAME_ANCESTORS if _valid_origin(origin)]
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self'" + (" " + " ".join(origins) if origins else "")
        )
        response.headers.pop("X-Frame-Options", None)
        return response
