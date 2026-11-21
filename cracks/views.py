from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CommentForm, CrackForm
from .images import clean_photo
from .models import Crack


def pin_data(crack):
    """The small bit of data the map needs per pin."""
    return {
        "lat": float(crack.latitude),
        "lng": float(crack.longitude),
        "title": str(crack),
        "width": crack.get_width_display(),
        "grade": crack.grade,
        "o_grade": crack.o_grade,
        "url": crack.get_absolute_url(),
        "photo": crack.photo.url if crack.photo else "",
    }


def map_view(request):
    """Home page: a full-screen map with one pin per crack."""
    context = {
        "pins": [pin_data(c) for c in Crack.objects.all()],
        "form": CrackForm(),
    }
    return render(request, "cracks/map.html", context)


def crack_detail(request, pk):
    """One crack with its photo and all details."""
    crack = get_object_or_404(Crack, pk=pk)
    context = {
        "crack": crack,
        "crack_location": {"lat": float(crack.latitude), "lng": float(crack.longitude)},
        "comments": crack.comments.select_related("author"),
        "comment_form": CommentForm(),
    }
    return render(request, "cracks/detail.html", context)


@login_required
@require_POST
def add_crack(request):
    """Create a crack from the map popup form. Answers in JSON for the page's JavaScript."""
    form = CrackForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    crack = form.save(commit=False)
    crack.created_by = request.user
    if crack.photo:
        try:
            crack.photo = clean_photo(request.FILES["photo"])
        except Exception:  # Pillow raises various errors for broken or fake images
            return JsonResponse({"errors": {"photo": ["Could not read this image."]}}, status=400)
    crack.save()
    return JsonResponse({"pin": pin_data(crack)}, status=201)


@login_required
@require_POST
def add_comment(request, pk):
    """Save a comment, then go back to the crack page (so a reload doesn't post twice)."""
    crack = get_object_or_404(Crack, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.crack = crack
        comment.author = request.user
        comment.save()
    return redirect(crack.get_absolute_url() + "#comments")
