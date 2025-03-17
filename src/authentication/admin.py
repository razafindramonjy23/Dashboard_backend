from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Department, SystemConfig

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_admin')
    search_fields = ('name',)
    list_filter = ('is_admin',)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + ('department',)
    list_filter = UserAdmin.list_filter + ('department',)
    fieldsets = UserAdmin.fieldsets + (
        ('Département', {'fields': ('department',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Département', {'fields': ('department',)}),
    )

@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'admin_token')
    
    def has_add_permission(self, request):
        # Empêcher l'ajout de multiples configurations
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)