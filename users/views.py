from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import UserSerializer, UserProfileSerializer, CustomTokenObtainPairSerializer
from .permissions import IsAdminUser, IsSupervisorUser
from rest_framework.views import APIView

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token view to include user data"""
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    """Manage users in the system"""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated, IsAdminUser]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsAdminUser]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['GET', 'PUT', 'PATCH'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Manage the authenticated user"""
        user = request.user
        
        if request.method == 'GET':
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
        
        if request.method in ['PUT', 'PATCH']:
            partial = request.method == 'PATCH'
            serializer = UserProfileSerializer(user, data=request.data, partial=partial)
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(generics.UpdateAPIView):
    """Change password for the authenticated user"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        
        if not request.data.get('password'):
            return Response({"password": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(request.data['password'])
        user.save()
        
        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)