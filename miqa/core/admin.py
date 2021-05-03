# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Experiment, Image, Scan, ScanNote, Session, Site


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
    list_display = (
        'id',
        'created',
        'modified',
        'experiment',
        'site',
        'scan_id',
        'scan_type',
        'decision',
        'note',
    )
    list_filter = ('created', 'modified')


@admin.register(ScanNote)
class ScanNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'note', 'scan')
    list_filter = ('created', 'scan')


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
        'session',
    )
    list_filter = ('created', 'modified', 'creator', 'session')
    search_fields = ('name',)
