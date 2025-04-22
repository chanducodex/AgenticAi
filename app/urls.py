from django.urls import path
from .views import invoiceParserAPIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.views.decorators.csrf import csrf_exempt
from django.contrib import admin

# Monkey‑patch the admin login view to skip CSRF/origin checks
admin.site.login = csrf_exempt(admin.site.login)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/parse-invoice/', invoiceParserAPIView, name='parse-invoice'),
    path('api/token/',    TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
