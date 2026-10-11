"""Motivation Corner content (project-vision §20).

Only text quotes exist today. Shared fields live on the abstract
MotivationalContent so that later content types reuse them. The planned
religious content (Dua / Surah / Hadith, with audio) will be its own concrete
model and table, not a `kind` on Quote: it needs fields quotes don't (audio
reference via integrations/storage_client, source reference, translation), and
it may only be served to patients who opted in, a GDPR Art. 9 preference
(docs/decisions.md, 2026-09-26 and 2026-10-08). A separate table means the
quotes endpoints can never return it by accident.
"""

from django.db import models

from core.fields import FreeTextField, PersonNameField
from core.models import ValidatedModelMixin


class MotivationalContent(ValidatedModelMixin, models.Model):
    is_active = models.BooleanField(
        default=True, help_text="Untick to hide it from the app immediately."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class QuoteCategory(models.TextChoices):
    HOPE = "hope", "Hope"
    RESILIENCE = "resilience", "Resilience"
    CALM = "calm", "Calm"
    SELF_CARE = "self_care", "Self-care"


class Quote(MotivationalContent):
    text = FreeTextField(label="Quote", min_length=10, rule_max_length=500)
    author = PersonNameField(max_length=120, label="Author", blank=True)
    category = models.CharField(
        max_length=20, choices=QuoteCategory.choices, blank=True
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["is_active", "category"])]

    def __str__(self):
        return self.text[:60]
