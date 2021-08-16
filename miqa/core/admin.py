# -*- coding: utf-8 -*-
from miqa.core.models.task import Task
from django.contrib import admin

from .models import Annotation, Experiment, Image, Scan, ScanNote, Session, Site, Task


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


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created',
        'modified',
        'name',
        'user',
    )
    filter_horizontal = ('experiments',)
    list_filter = ('created', 'modified', 'user')
    search_fields = ('name',)