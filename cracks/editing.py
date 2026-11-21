"""Edit and delete for cracks and comments. Allowed for the author and for admins (staff)."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CommentForm, CrackForm
from .images import clean_photo
from .models import Comment, Crack


def check_can_edit(user, author):
    """Raise 403 Forbidden unless the user wrote it or is an admin."""
    if not (user.is_staff or (author is not None and user == author)):
        raise PermissionDenied


@login_required
def edit_crack(request, pk):
    crack = get_object_or_404(Crack, pk=pk)
    check_can_edit(request.user, crack.created_by)
    old_photo = crack.photo.name

    form = CrackForm(request.POST or None, request.FILES or None, instance=crack)
    if request.method == "POST" and form.is_valid():
        crack = form.save(commit=False)
        new_upload = request.FILES.get("photo")
        if new_upload:
            try:
                crack.photo = clean_photo(new_upload)
            except Exception:  # Pillow raises various errors for broken or fake images
                form.add_error("photo", "Could not read this image.")
                return render(request, "cracks/crack_edit.html", {"form": form, "crack": crack})
        crack.save()
        # Remove the old file if the photo was replaced or cleared, so storage doesn't fill up.
        if old_photo and crack.photo.name != old_photo:
            crack.photo.storage.delete(old_photo)
        return redirect(crack)
    return render(request, "cracks/crack_edit.html", {"form": form, "crack": crack})


@login_required
@require_POST
def delete_crack(request, pk):
    crack = get_object_or_404(Crack, pk=pk)
    check_can_edit(request.user, crack.created_by)
    if crack.photo:
        crack.photo.delete(save=False)
    crack.delete()  # its comments are deleted too (on_delete=CASCADE)
    return redirect("cracks:map")


@login_required
def edit_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    check_can_edit(request.user, comment.author)
    form = CommentForm(request.POST or None, instance=comment)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(comment.crack.get_absolute_url() + "#comments")
    return render(request, "cracks/comment_edit.html", {"form": form, "comment": comment})


@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    check_can_edit(request.user, comment.author)
    crack_url = comment.crack.get_absolute_url()
    comment.delete()
    return redirect(crack_url + "#comments")
