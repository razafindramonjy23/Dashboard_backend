from django.urls import path
from .views import RegistrationView, VerifyEmailView, CustomTokenObtainPairView, LogoutView

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
