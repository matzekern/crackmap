from django.urls import path

from . import editing, views

app_name = "cracks"

urlpatterns = [
    path("", views.map_view, name="map"),
    path("cracks/add/", views.add_crack, name="add"),
    path("cracks/<int:pk>/", views.crack_detail, name="detail"),
    path("cracks/<int:pk>/edit/", editing.edit_crack, name="edit"),
    path("cracks/<int:pk>/delete/", editing.delete_crack, name="delete"),
    path("cracks/<int:pk>/comments/", views.add_comment, name="add_comment"),
    path("comments/<int:pk>/edit/", editing.edit_comment, name="edit_comment"),
    path("comments/<int:pk>/delete/", editing.delete_comment, name="delete_comment"),
]
