from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class SystemConfig(models.Model):
    admin_token = models.CharField(max_length=64, unique=True)

    @classmethod
    def get_admin_token(cls):
        config, created = cls.objects.get_or_create(id=1, defaults={'admin_token': 'default_token'})
        return config.admin_token

class CustomUser(AbstractUser):
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='users'
    )
    groups = models.ManyToManyField(
        Group,
        related_name="customuser_groups",  
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_permissions", 
        blank=True
    )

    def is_admin_user(self):
        return self.department and self.department.is_admin

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'department': self.department.name if self.department else None,
            'is_admin': self.is_admin_user(),
        }

class AdminToken(models.Model):
    token = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.token