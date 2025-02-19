from django.urls import path
from . import views

urlpatterns = [
    path('api/login/', views.LoginView.as_view(), name='login'),
    path('api/register/', views.RegisterUserView.as_view(), name='register'),
    path('api/departments/', views.DepartmentListView.as_view(), name='departments'),
    path('api/user-profile/', views.UserProfileView.as_view(), name='user-profile'),
]