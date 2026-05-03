# smartsketch_backend/urls.py
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


def root(request):
    return JsonResponse({"message": "SmartSketch API", "docs": "Use /api/ for endpoints."})


urlpatterns = [
    path("", root),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]

# User uploads (forensic images). Must work when DEBUG=False (e.g. Render);
# WhiteNoise does not serve MEDIA_ROOT.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

