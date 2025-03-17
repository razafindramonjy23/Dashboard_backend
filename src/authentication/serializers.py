from rest_framework import serializers
from .models import CustomUser, Department, SystemConfig

class UserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    department_id = serializers.IntegerField()
    admin_token = serializers.CharField(write_only=True)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Les mots de passe ne correspondent pas")
        
        # Validation du token admin unique
        admin_token = SystemConfig.get_admin_token()
        if data['admin_token'] != admin_token:
            raise serializers.ValidationError("Token administrateur R&D invalide")
        
        # Validation du département
        try:
            department = Department.objects.get(id=data['department_id'])
            if department.is_admin:
                raise serializers.ValidationError("Impossible d'inscrire un utilisateur comme admin")
            data['department'] = department
        except Department.DoesNotExist:
            raise serializers.ValidationError("Département invalide")
        
        return data
    
    def create(self, validated_data):
        user = CustomUser(
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            department=validated_data['department']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'is_admin']

class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'department', 'department_name', 'is_admin']
    
    def get_department_name(self, obj):
        return obj.department.name if obj.department else None
    
    def get_is_admin(self, obj):
        return obj.is_admin_user()