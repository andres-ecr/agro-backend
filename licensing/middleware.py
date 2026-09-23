import re
from django.http import JsonResponse
from .services import LicenseService

# Routes that are never blocked by license validation
EXEMPT_URL_PATTERNS = [
    re.compile(r'^/admin/'),
    re.compile(r'^/api/v1/license/'),
    re.compile(r'^/api/v1/auth/'),
    re.compile(r'^/swagger/'),
    re.compile(r'^/redoc/'),
    re.compile(r'^/static/'),
    re.compile(r'^/media/'),
    re.compile(r'^/favicon.ico'),
]


class LicenseEnforcementMiddleware:
    """
    Middleware that enforces active license validity on all incoming API calls.
    Returns HTTP 402 (Payment Required) when the license is suspended, expired, or unlicensed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # Check if route is exempt
        for pattern in EXEMPT_URL_PATTERNS:
            if pattern.match(path):
                return self.get_response(request)

        # Allow preflight CORS requests without blocking
        if request.method == 'OPTIONS':
            return self.get_response(request)

        # Perform license check
        is_valid, status, message, meta = LicenseService.check_license()

        if not is_valid:
            # Block request: Software is frozen / suspended
            response = JsonResponse(
                {
                    'error': 'LICENSE_SUSPENDED',
                    'status': status,
                    'message': message,
                    'meta': meta,
                },
                status=402,
            )
            response['X-License-Status'] = status
            return response

        # If valid, process request
        response = self.get_response(request)

        # If operating in offline grace period, attach warning header so frontend can notify operator
        if status == 'grace_period':
            response['X-License-Warning'] = 'grace_period'
            response['X-License-Hours-Remaining'] = str(meta.get('hours_remaining', 0))

        return response
