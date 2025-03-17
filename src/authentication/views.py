# from rest_framework import status, permissions, generics
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from django.contrib.auth import authenticate
# from rest_framework.authtoken.models import Token
# from rest_framework.authentication import TokenAuthentication
# from .serializers import UserSerializer, UserRegistrationSerializer, DepartmentSerializer
# from .models import CustomUser, Department

# class IsAdminUser(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return request.user.is_authenticated and request.user.is_admin_user()

# class LoginView(APIView):
#     def post(self, request):
#         username = request.data.get('username')
#         password = request.data.get('password')
        
#         user = authenticate(username=username, password=password)
#         if user:
#             token, _ = Token.objects.get_or_create(user=user)
#             return Response({
#                 'token': token.key,
#                 'user': user.to_dict()
#             })
#         return Response({'error': 'Identifiants invalides'}, status=status.HTTP_401_UNAUTHORIZED)

# class RegisterUserView(APIView):
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAdminUser]
    
#     def post(self, request):
#         serializer = UserRegistrationSerializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.save()
#             return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class DepartmentListView(generics.ListAPIView):
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [permissions.IsAuthenticated]
#     queryset = Department.objects.filter(is_admin=False)
#     serializer_class = DepartmentSerializer


    
# class UserProfileView(APIView):
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [permissions.IsAuthenticated]
    
#     def get(self, request):
#         return Response(UserSerializer(request.user).data)


from rest_framework import status, permissions, generics, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import UserSerializer, UserRegistrationSerializer, DepartmentSerializer
from .models import CustomUser, Department


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_user()


class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': user.to_dict()
            })
        return Response({'error': 'Identifiants invalides'}, status=status.HTTP_401_UNAUTHORIZED)


class RegisterUserView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DepartmentListView(generics.ListCreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DepartmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    
    def get_queryset(self):
        queryset = Department.objects.filter(is_admin=False)
        
        # Filtrage supplémentaire par params optionnels
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
            
        parent_id = self.request.query_params.get('parent_id', None)
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        # Vérifier si l'utilisateur est admin pour la création
        if not request.user.is_admin_user():
            return Response(
                {"detail": "Vous n'avez pas l'autorisation de créer un département."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        return Response(UserSerializer(request.user).data)