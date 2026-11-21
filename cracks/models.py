from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class Crack(models.Model):
    class Width(models.TextChoices):
        FINGERS = "fingers", "Fingers"
        HANDS = "hands", "Hands"
        FISTS = "fists", "Fists"
        OFFWIDTH = "offwidth", "Offwidth"
        CHIMNEY = "chimney", "Chimney"
        MIXED = "mixed", "Mixed / changing"

    class Access(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        OPEN = "open", "Open"
        RESTRICTED = "restricted", "Restricted (seasonal, permit, ...)"
        CLOSED = "closed", "Closed"

    name = models.CharField(max_length=120, blank=True)
    width = models.CharField(max_length=10, choices=Width.choices)
    length_m = models.PositiveSmallIntegerField(
        "length (m)", null=True, blank=True, validators=[MaxValueValidator(1000)]
    )
    # Free text on purpose: grading systems differ by region.
    grade = models.CharField(max_length=20, blank=True)
    o_grade = models.CharField("O-grade", max_length=20, blank=True)
    rock_type = models.CharField(max_length=50, blank=True)
    access_status = models.CharField(
        max_length=10, choices=Access.choices, default=Access.UNKNOWN
    )
    access_notes = models.TextField(blank=True)
    info_source = models.TextField(
        "where to find info", max_length=500, blank=True,
        help_text="Guidebook and page, website link, local contact, ...",
    )
    photo = models.ImageField(upload_to="cracks/%Y/%m/", blank=True)

    # 6 decimal places is ~10 cm precision, plenty for a crack.
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def get_absolute_url(self):
        return reverse("cracks:detail", args=[self.pk])

    def __str__(self):
        return self.name or f"Unnamed {self.get_width_display().lower()} crack"

class Comment(models.Model):
    crack = models.ForeignKey(Crack, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]  # oldest first, like a conversation

    def __str__(self):
        return f"{self.author} on {self.crack}: {self.text[:40]}"
