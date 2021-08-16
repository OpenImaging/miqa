from django.contrib.auth.models import User
from django.db import transaction
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Annotation, Experiment, Image, Scan, ScanNote, Session
from miqa.core.rest.permissions import LockContention, UserHoldsSessionLock
from miqa.core.tasks import export_data, import_data


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = ['id', 'decision']

    decision = serializers.ChoiceField(choices=Annotation.decision.field.choices)


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['id', 'name']
        ref_name = 'scan_image'


class ScanNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanNote
        fields = ['id', 'note', 'created', 'modified']
        ref_name = 'scan_note'

    # Override the default DateTimeFields to disable read_only=True
    created = serializers.DateTimeField()
    modified = serializers.DateTimeField()


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = ['id', 'scan_id', 'scan_type', 'notes', 'decisions', 'images']
        ref_name = 'experiment_scan'

    notes = ScanNoteSerializer(many=True)
    images = ImageSerializer(many=True)
    decisions = DecisionSerializer(many=True)


class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = ['id', 'name', 'scans']
        ref_name = 'session_experiment'

    scans = ScanSerializer(many=True)


class LockOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']
        ref_name = 'lock_owner'


class SessionRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['id', 'name', 'experiments', 'lock_owner']
        ref_name = 'session'

    experiments = ExperimentSerializer(many=True)
    lock_owner = LockOwnerSerializer()


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['id', 'name', 'lock_owner']
        ref_name = 'sessions'

    lock_owner = LockOwnerSerializer()


class SessionSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['importpath', 'exportpath']

    importpath = serializers.CharField(source='import_path')
    exportpath = serializers.CharField(source='export_path')


class SessionViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, UserHoldsSessionLock]

    def get_queryset(self):
        if self.action == 'retrieve':
            return Session.objects.prefetch_related(
                'experiments__scans__images', 'experiments__scans__notes'
            )
        else:
            return Session.objects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SessionRetrieveSerializer
        else:
            return SessionSerializer

    @swagger_auto_schema(
        method='GET',
        responses={200: SessionSettingsSerializer()},
    )
    @swagger_auto_schema(
        method='PUT',
        request_body=SessionSettingsSerializer(),
        responses={200: SessionSettingsSerializer()},
    )
    @action(
        detail=True,
        url_path='settings',
        url_name='settings',
        methods=['GET', 'PUT'],
        permission_classes=[IsAdminUser],
    )
    def settings_(self, request, **kwargs):
        session: Session = self.get_object()
        if request.method == 'GET':
            serializer = SessionSettingsSerializer(instance=session)
        elif request.method == 'PUT':
            serializer = SessionSettingsSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            session.import_path = serializer.data['importpath']
            session.export_path = serializer.data['exportpath']
            session.save()
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=no_body,
        responses={204: 'Import succeeded.'},
    )
    @action(detail=True, url_path='import', url_name='import', methods=['POST'])
    def import_(self, request, **kwargs):
        session: Session = self.get_object()
        import_data(request.user, session)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        request_body=no_body,
        responses={204: 'Export succeeded.'},
    )
    @action(detail=True, methods=['POST'])
    def export(self, request, **kwargs):
        session: Session = self.get_object()
        try:
            export_data(request.user, session)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except IsADirectoryError:
            return Response({'detail': 'Invalid export path'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        request_body=no_body,
        responses={
            204: 'Lock acquired.',
            409: 'The lock is held by a different user.',
        },
    )
    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def lock(self, request, pk=None):
        """Acquire the exclusive write lock on this session."""
        with transaction.atomic():
            session: Session = Session.objects.select_for_update().get(pk=pk)

            if session.lock_owner is not None and session.lock_owner != request.user:
                raise LockContention()

            if session.lock_owner is None:
                session.lock_owner = request.user
                session.save(update_fields=['lock_owner'])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        request_body=no_body,
        responses={
            204: 'Lock released.',
            409: 'The lock is held by a different user.',
        },
    )
    @lock.mapping.delete
    def release_lock(self, request, pk=None):
        """Release the exclusive write lock on this session."""
        with transaction.atomic():
            session: Session = Session.objects.select_for_update().get(pk=pk)

            if session.lock_owner is not None and session.lock_owner != request.user:
                raise LockContention()

            if session.lock_owner is not None:
                session.lock_owner = None
                session.save(update_fields=['lock_owner'])

        return Response(status=status.HTTP_204_NO_CONTENT)
