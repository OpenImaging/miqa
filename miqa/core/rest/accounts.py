from django.contrib.auth import logout
from django.views.generic.base import TemplateView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class AccountInactiveView(TemplateView):
    template_name = "account_inactive.html"


class LogoutView(APIView):
    def post(self, request):
        if request.user.is_authenticated:
            logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
