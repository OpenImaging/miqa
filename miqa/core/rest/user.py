from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_out
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet


from miqa.core.models import Experiment


def remove_locks(sender, user, request, **kwargs):
    previously_locked_experiments = Experiment.objects.filter(lock_owner=request.user)
    for previously_locked_experiment in previously_locked_experiments:
        previously_locked_experiment.lock_owner = None
        previously_locked_experiment.save()


user_logged_out.connect(remove_locks)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_superuser', 'first_name', 'last_name']
        ref_name = 'user'


class UserViewSet(ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, pagination_class=None)
    def me(self, request):
        """Return the currently logged in user's information."""
        if request.user.is_anonymous:
            return Response(status=204)
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
