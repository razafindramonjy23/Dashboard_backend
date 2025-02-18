from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=255, blank=True)
    verification_token_created = models.DateTimeField(null=True)

    
    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set", 
        blank=True
    )
    
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions_set",  
        blank=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['username']

    class Meta: 
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email
