"""Read-path query logic for reference data. All public (no PHI)."""

from apps.reference.models import City, Country, Language, Specialization
from core.validators import normalize_display_text


def list_countries():
    return Country.objects.all()


def search_cities(*, country_code, search=None, limit=20):
    qs = City.objects.filter(
        country__code=country_code.upper(), is_verified=True
    ).select_related("country")
    if search:
        qs = qs.filter(name__istartswith=normalize_display_text(search))
    return list(qs.order_by("name")[:limit])


def list_languages():
    return Language.objects.filter(is_active=True)


def list_specializations():
    return list(Specialization.objects.filter(is_active=True))
