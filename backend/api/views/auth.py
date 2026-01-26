from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator


def get_user_session_info(request):
    """
    Helper function to get user and session info from request.
    Returns a dict with user (or None) and session_key.
    """
    if request.user.is_authenticated:
        return {
            'user': request.user,
            'session_key': None
        }
    else:
        # Ensure session exists for anonymous users
        if not request.session.session_key:
            request.session.create()
        return {
            'user': None,
            'session_key': request.session.session_key
        }


def filter_by_owner(queryset, request):
    """
    Filter a queryset to only include items owned by the current user/session.
    """
    if request.user.is_authenticated:
        return queryset.filter(user=request.user)
    else:
        session_key = request.session.session_key
        if session_key:
            return queryset.filter(session_key=session_key)
        return queryset.none()


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(APIView):
    """
    Returns a CSRF token for the frontend to use in subsequent requests.
    GET /api/auth/csrf/
    """
    def get(self, request):
        return Response({
            'csrfToken': get_token(request)
        })


class RegisterView(APIView):
    """
    Handles user registration.
    POST /api/auth/register/
    """
    def post(self, request):
        username = request.data.get('username', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')
        password_confirm = request.data.get('password_confirm', '')
        
        # Validation
        if not username:
            return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not password:
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if password != password_confirm:
            return Response({'error': 'Passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(password) < 8:
            return Response({'error': 'Password must be at least 8 characters'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already taken'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email already registered'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the current session key before creating user (for migrating anonymous data)
        old_session_key = request.session.session_key
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
        except Exception as e:
            return Response({'error': f'Failed to create user: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Log the user in
        login(request, user)
        
        # Migrate anonymous data to the new user account
        if old_session_key:
            self._migrate_anonymous_data(old_session_key, user)
        
        return Response({
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }, status=status.HTTP_201_CREATED)
    
    def _migrate_anonymous_data(self, session_key, user):
        """Migrate anonymous user's data to their new account."""
        from ..models import Analysis, Chat, GymSesh, AnalysisTranscript, GymTranscript
        
        # Migrate analyses
        Analysis.objects.filter(session_key=session_key).update(user=user, session_key=None)
        
        # Migrate chats
        Chat.objects.filter(session_key=session_key).update(user=user, session_key=None)
        
        # Migrate gym sessions
        GymSesh.objects.filter(session_key=session_key).update(user=user, session_key=None)
        
        # Migrate transcripts
        AnalysisTranscript.objects.filter(session_key=session_key).update(user=user, session_key=None)
        GymTranscript.objects.filter(session_key=session_key).update(user=user, session_key=None)


class LoginView(APIView):
    """
    Handles user login.
    POST /api/auth/login/
    """
    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        
        if not username or not password:
            return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Authenticate user (username can be email or username)
        user = authenticate(request, username=username, password=password)
        
        # If auth failed, try with email
        if user is None:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is None:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({'error': 'Account is disabled'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get the current session key before logging in (for migrating anonymous data)
        old_session_key = request.session.session_key
        
        # Log the user in
        login(request, user)
        
        # Optionally migrate anonymous data if user had a session
        if old_session_key:
            self._migrate_anonymous_data(old_session_key, user)
        
        return Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })
    
    def _migrate_anonymous_data(self, session_key, user):
        """Migrate anonymous user's data to their account on login."""
        from ..models import Analysis, Chat, GymSesh, AnalysisTranscript, GymTranscript
        
        # Migrate analyses
        Analysis.objects.filter(session_key=session_key).update(user=user, session_key=None)
        
        # Migrate chats
        Chat.objects.filter(session_key=session_key).update(user=user, session_key=None)
        
        # Migrate gym sessions
        GymSesh.objects.filter(session_key=session_key).update(user=user, session_key=None)
        
        # Migrate transcripts
        AnalysisTranscript.objects.filter(session_key=session_key).update(user=user, session_key=None)
        GymTranscript.objects.filter(session_key=session_key).update(user=user, session_key=None)


class LogoutView(APIView):
    """
    Handles user logout.
    POST /api/auth/logout/
    """
    def post(self, request):
        logout(request)
        return Response({'message': 'Logout successful'})


class MeView(APIView):
    """
    Returns current user info or anonymous session status.
    GET /api/auth/me/
    """
    def get(self, request):
        if request.user.is_authenticated:
            return Response({
                'authenticated': True,
                'user': {
                    'id': request.user.id,
                    'username': request.user.username,
                    'email': request.user.email
                }
            })
        else:
            # Ensure session exists for anonymous users
            if not request.session.session_key:
                request.session.create()
            
            return Response({
                'authenticated': False,
                'session_key': request.session.session_key
            })
