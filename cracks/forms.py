from django import forms

from .models import Comment, Crack

MAX_UPLOAD_MB = 10


class CrackForm(forms.ModelForm):
    class Meta:
        model = Crack
        fields = [
            "width", "name", "grade", "o_grade", "length_m", "rock_type",
            "access_status", "access_notes", "info_source", "photo", "latitude", "longitude",
        ]
        widgets = {
            "latitude": forms.HiddenInput,
            "longitude": forms.HiddenInput,
            "access_notes": forms.Textarea(attrs={"rows": 2}),
            "info_source": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and photo.size > MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(f"Photo must be smaller than {MAX_UPLOAD_MB} MB.")
        return photo


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        labels = {"text": ""}
        widgets = {
            "text": forms.Textarea(attrs={
                "rows": 3, "maxlength": 2000,
                "placeholder": "Beta, conditions, access info, rack advice…",
            }),
        }
