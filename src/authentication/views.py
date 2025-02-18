from rest_framework import status, views
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from .serializers import RegistrationSerializer, CustomTokenObtainPairSerializer, UserSerializer
from .utils.email_service import generate_verification_token, send_verification_email

def is_token_expired(token_created):
    expiration_time = timedelta(hours=24)  
    return timezone.now() - token_created > expiration_time

class RegistrationView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_active = False  # L'utilisateur n'est pas actif avant la vérification
            user.verification_token = generate_verification_token()
            user.verification_token_created = timezone.now()
            user.save()

            verification_url = f"{settings.FRONTEND_URL}/verify-email/{user.verification_token}"
            send_verification_email(user, verification_url)

            return Response({
                'message': 'Inscription réussie. Veuillez vérifier votre email.',
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class VerifyEmailView(views.APIView):
    permission_classes = (AllowAny,)
    
    def post(self, request):
        token = request.data.get('token')
        
        try:
            user = User.objects.get(verification_token=token)
            
            # Vérification de l'expiration du token
            if is_token_expired(user.verification_token_created):
                return Response({
                    'error': 'Le lien de vérification a expiré'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Activation de l'utilisateur
            user.is_verified = True
            user.is_active = True
            user.verification_token = ''
            user.save()
            
            # Génération des tokens JWT
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Email vérifié avec succès',
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
            
        except User.DoesNotExist:
            return Response({
                'error': 'Token de vérification invalide'
            }, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class LogoutView(views.APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({'message': 'Déconnexion réussie'})
            return Response({'error': 'Refresh token requis'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, 
                          status=status.HTTP_400_BAD_REQUEST)
