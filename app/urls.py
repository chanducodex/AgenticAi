from django.urls import path
from .views import invoiceParserAPIView

urlpatterns = [
    path('parse-invoice/', invoiceParserAPIView, name='parse-invoice')
]