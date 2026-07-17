from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import RecruiterTokenObtainPairSerializer, UserSerializer


class RecruiterTokenObtainPairView(TokenObtainPairView):
    """POST username/password -> {access, refresh, user}."""

    serializer_class = RecruiterTokenObtainPairSerializer


class MeView(APIView):
    """Returns the currently authenticated recruiter."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
