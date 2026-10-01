"""URL routes for the reference API, included under /api/v1/reference/."""

from django.urls import path

from apps.reference.api.views import (
    CityListView,
    CountryListView,
    LanguageListView,
    SpecializationListView,
)

app_name = "reference"

urlpatterns = [
    path("countries/", CountryListView.as_view(), name="countries"),
    path("cities/", CityListView.as_view(), name="cities"),
    path("languages/", LanguageListView.as_view(), name="languages"),
    path("specializations/", SpecializationListView.as_view(), name="specializations"),
]
