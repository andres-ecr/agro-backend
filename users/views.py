from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status, generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import UserSerializer, UserProfileSerializer, CustomTokenObtainPairSerializer
from .permissions import IsAdminUser, IsSupervisorUser
from rest_framework.views import APIView

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token view to include user data"""
    permission_classes = (permissions.AllowAny,)
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    """Manage users in the system"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return User.objects.none()
            
        if user.role == 'superadmin' or user.is_superuser:
            queryset = User.objects.all().order_by('-date_joined')
            tenant_id = self.request.query_params.get('tenant')
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            return queryset
        elif user.role == 'admin':
            if not user.tenant:
                return User.objects.none()
            return User.objects.filter(tenant=user.tenant).exclude(role='superadmin').order_by('-date_joined')
        else:
            return User.objects.filter(id=user.id)
    
    def perform_create(self, serializer):
        user = self.request.user
        if user.role != 'superadmin' and not user.is_superuser:
            role = serializer.validated_data.get('role', 'operator')
            if role == 'superadmin':
                raise ValidationError({'role': 'No tiene permisos para crear usuarios superadmin.'})
            tenant = user.tenant
            if not tenant:
                raise ValidationError({'tenant': 'El usuario administrador no tiene una sede asignada.'})
            allowed_roles = tenant.allowed_roles if tenant.allowed_roles else ['admin', 'operator']
            if role not in allowed_roles:
                raise ValidationError({'role': f"El rol '{role}' no está permitido para esta sede. Roles permitidos: {', '.join(allowed_roles)}"})
            serializer.save(tenant=tenant, role=role)
        else:
            serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if user.role != 'superadmin' and not user.is_superuser:
            role = serializer.validated_data.get('role')
            if role:
                if role == 'superadmin':
                    raise ValidationError({'role': 'No tiene permisos para asignar el rol superadmin.'})
                tenant = user.tenant
                if not tenant:
                    raise ValidationError({'tenant': 'El usuario administrador no tiene una sede asignada.'})
                allowed_roles = tenant.allowed_roles if tenant.allowed_roles else ['admin', 'operator']
                if role not in allowed_roles:
                    raise ValidationError({'role': f"El rol '{role}' no está permitido para esta sede. Roles permitidos: {', '.join(allowed_roles)}"})
            serializer.save(tenant=user.tenant)
        else:
            serializer.save()
    
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
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)