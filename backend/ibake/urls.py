from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('inventory/', include('inventory.urls')),
    path('sales/', include('sales_management.urls')),
    path('customer/', include('customer_management.urls')),
    path('employee/', include('employee.urls')),
    path('accounting/', include('accounting.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('select2/', include('django_select2.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 