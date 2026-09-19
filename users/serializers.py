from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the users object"""
    tenant_details = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'password', 'first_name', 'last_name',
            'role', 'avatar', 'tenant', 'tenant_details', 'is_active',
            'is_superuser', 'date_joined'
        )
        read_only_fields = ('id', 'tenant_details', 'date_joined')
        extra_kwargs = {
            'password': {'write_only': True, 'required': False, 'allow_blank': True}
        }
    
    def get_tenant_details(self, obj):
        if obj.tenant:
            return {
                'id': obj.tenant.id,
                'code': obj.tenant.code,
                'name': obj.tenant.name,
            }
        return None
    
    def create(self, validated_data):
        """Create a new user with encrypted password and return it"""
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({'password': 'La contraseña es obligatoria para nuevos usuarios.'})
        user = User.objects.create_user(password=password, **validated_data)
        return user
    
    def update(self, instance, validated_data):
        """Update a user, setting the password correctly and return it"""
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        
        if password:
            user.set_password(password)
            user.save()
        
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    full_name = serializers.SerializerMethodField()
    tenant = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'avatar', 'tenant', 'is_active', 'is_superuser'
        )
        read_only_fields = ('email', 'role', 'tenant', 'is_superuser')
    
    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_tenant(self, obj):
        if obj.tenant:
            return {
                'id': obj.tenant.id,
                'code': obj.tenant.code,
                'name': obj.tenant.name,
            }
        return None


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer to include user data"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user data to response
        user = self.user
        tenant_data = None
        if user.tenant:
            tenant_data = {
                'id': user.tenant.id,
                'code': user.tenant.code,
                'name': user.tenant.name,
            }
            
        data['user'] = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'role': user.role,
            'is_superuser': user.is_superuser,
            'is_active': user.is_active,
            'avatar': user.avatar.url if user.avatar else None,
            'tenant': tenant_data,
        }
        
        return data
