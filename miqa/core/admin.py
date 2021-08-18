# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm

from .models import Annotation, Experiment, Image, Scan, ScanNote, Session, Site

# This custom admin site only exists to ensure that admin logins are not immediately logged out,
# as normal user logins are.
# See the SESSION_COOKIE_AGE setting
class CustomAdminLoginForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        # Admins will remain logged in for 30 minutes
        self.request.session.set_expiry(1800)


class CustomAdminSite(admin.AdminSite):
    login_form = CustomAdminLoginForm


admin.site = CustomAdminSite()


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'modified', 'name', 'note', 'session')
    list_filter = ('created', 'modified', 'session')
    search_fields = ('name',)


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'modified', 'scan', 'raw_path', 'name')
    list_filter = ('created', 'modified')
    raw_id_fields = ('scan',)
    search_fields = ('name',)


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'modified', 'experiment', 'site', 'scan_id', 'scan_type')
    list_filter = ('created', 'modified')


@admin.register(ScanNote)
class ScanNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'modified', 'initials', 'creator', 'note', 'scan')
    list_filter = ('created', 'initials', 'creator', 'scan')


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'creator', 'decision', 'scan')
    list_filter = ('created', 'creator', 'scan')


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created',
        'modified',
        'name',
        'creator',
        'import_path',
        'export_path',
    )
    list_filter = ('created', 'modified', 'creator')
    search_fields = ('name',)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created',
        'modified',
        'name',
        'creator',
    )
    list_filter = ('created', 'modified', 'creator')
    search_fields = ('name',)
