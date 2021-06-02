from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
        ]


class UserViewSet(GenericViewSet):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    @action(detail=False, pagination_class=None)
    def me(self, request):
        """Return the currently logged in user's information."""
        if request.user.is_anonymous:
            return Response(status=204)
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
