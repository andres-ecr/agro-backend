from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="ERP Agroindustrial API",
      default_version='v1',
      description="API para el sistema ERP Agroindustrial",
      terms_of_service="https://www.example.com/terms/",
      contact=openapi.Contact(email="contact@example.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API endpoints - sin el prefijo api/v1/
    path('auth/', include('users.urls')),
    path('users/', include('users.urls')),  # Añadir esta línea
    path('tenants/', include('tenants.urls')),
    path('transporte/', include('transporte.urls')),
    path('reports/', include('reports.urls')),
    path('trazabilidad/', include('trazabilidad.urls')),
    path('inventory/', include('inventory.urls')),
    path('producers/', include('producers.urls')),
    path('license/', include('licensing.urls')),
    
    # Mantener también las rutas con prefijo para compatibilidad
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/users/', include('users.urls')),
    path('api/v1/tenants/', include('tenants.urls')),
    path('api/v1/transporte/', include('transporte.urls')),
    path('api/v1/reports/', include('reports.urls')),
    path('api/v1/trazabilidad/', include('trazabilidad.urls')),
    path('api/v1/inventory/', include('inventory.urls')),
    path('api/v1/producers/', include('producers.urls')),
    path('api/v1/license/', include('licensing.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)