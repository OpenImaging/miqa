# -*- coding: utf-8 -*-
from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from .models import Artifact, Evaluation, Experiment, Frame, Group, Project, Scan, ScanDecision


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'modified', 'name', 'note', 'project', 'lock_owner')
    list_filter = ('created', 'modified', 'project', 'lock_owner')
    search_fields = ('name', 'lock_owner')


@admin.register(Frame)
class FrameAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'modified', 'scan', 'raw_path', 'frame_number')
    list_filter = ('created', 'modified')
    raw_id_fields = ('scan',)
    search_fields = ('name',)


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'modified', 'experiment', 'name', 'scan_type')
    list_filter = ('created', 'modified')


@admin.register(ScanDecision)
class ScanDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'creator', 'decision', 'scan', 'note')
    list_filter = ('created', 'creator', 'scan')


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('id', 'frame', 'evaluation_model')
    list_filter = ('frame', 'evaluation_model')


@admin.register(Project)
class ProjectAdmin(GuardedModelAdmin):
    list_display = (
        'id',
        'created',
        'modified',
        'name',
        'creator',
        'import_path',
        'export_path',
        'evaluation_models',
    )
    list_filter = ('created', 'modified', 'creator')
    search_fields = ('name',)


@admin.register(Artifact)
class ArtifactAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'group')
    list_filter = ('name', 'group')


@admin.register(Group)
class ArtifactGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    list_filter = ('name',)
