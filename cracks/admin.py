from django.contrib import admin

from .models import Comment, Crack


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("author", "created_at")


@admin.register(Crack)
class CrackAdmin(admin.ModelAdmin):
    list_display = ("__str__", "width", "grade", "access_status", "created_at")
    list_filter = ("width", "access_status")
    search_fields = ("name", "rock_type", "access_notes")
    inlines = [CommentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("__str__", "author", "crack", "created_at")
    search_fields = ("text", "author__username")
