from django.urls import path
from .views import currency_list, country_list, timezone_list

urlpatterns = [
    path("currency-list", currency_list, name="currency-list"),
    path("country-list", country_list, name="country-list"),
    path("timezone-list", timezone_list, name="timezone-list"),
]
