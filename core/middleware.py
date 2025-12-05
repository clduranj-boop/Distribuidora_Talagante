from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.auth import get_user

class AllowInactiveUserMiddleware(AuthenticationMiddleware):
    def process_request(self, request):
        super().process_request(request)
        # Esto permite que usuarios inactivos sigan teniendo request.user
        if not hasattr(request, 'user'):
            request.user = get_user(request)