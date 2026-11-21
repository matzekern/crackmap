"""Sign-up. Login and logout use Django's built-in views (see config/urls.py)."""
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme


def safe_next(request, default="/"):
    """Only follow ?next= if it points to our own site (prevents open redirects)."""
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return target
    return default


def signup(request):
    if request.user.is_authenticated:
        return redirect("/")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect(safe_next(request))
    return render(request, "registration/signup.html", {"form": form, "next": safe_next(request, "")})
