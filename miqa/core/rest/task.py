from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from miqa.core.models import Task
from miqa.core.rest.user import UserSerializer
from miqa.core.rest.experiment import ExperimentSerializer

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'name', 'user', 'experiments']

    user = UserSerializer()
    experiments = ExperimentSerializer(many=True)


class TaskViewSet(GenericViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    
    permission_classes = [IsAuthenticated]

    @action(detail=False, pagination_class=None)
    def me(self, request):
        """Return the currently logged in user's tasks."""
        queryset = Task.objects.all()
        queryset = queryset.filter(user=request.user)
        serializer = TaskSerializer(queryset, many=True)
        return Response(data=serializer.data)

