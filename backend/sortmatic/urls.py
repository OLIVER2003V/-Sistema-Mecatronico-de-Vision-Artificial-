from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("cuentas.urls")),
    path("api/", include("linea.urls")),
]

if settings.ALMACENAMIENTO != "s3":
    # Con DJANGO_ALMACENAMIENTO=s3 las fotos las sirve el bucket con URLs
    # firmadas. Sin S3 las sirve Django: el nombre de archivo es aleatorio
    # (ver linea.models.ruta_foto_descarte) para que no se puedan adivinar.
    urlpatterns += [
        path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
