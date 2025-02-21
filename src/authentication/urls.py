from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterUserView.as_view(), name='register'),
    path('departments/', views.DepartmentListView.as_view(), name='departments'),
    path('user-profile/', views.UserProfileView.as_view(), name='user-profile'),
]