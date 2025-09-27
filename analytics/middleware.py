from django.utils.deprecation import MiddlewareMixin
from .models import AnalyticsEvent

EXCLUDE_PATHS = ['/static/', '/media/', '/admin/']

class AnalyticsPageViewMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Exclude static, media, and admin paths
        if any(request.path.startswith(p) for p in EXCLUDE_PATHS):
            return None
        if request.user.is_authenticated:
            AnalyticsEvent.objects.create(
                user=request.user,
                event_type='page_view',
                page_url=request.path,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={}
            )
        return None 