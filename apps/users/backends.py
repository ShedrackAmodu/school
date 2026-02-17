"""
Custom authentication backends for email and username-based login.
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Custom authentication backend that allows users to authenticate
    using either their email address or username along with password.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user with either email or username and password.
        
        Args:
            request: The request object
            username: Can be either email or username
            password: User password
            **kwargs: Additional arguments
            
        Returns:
            User object if authentication succeeds, None otherwise
        """
        try:
            # Try to find user by email or username
            # Support both 'username' and 'email' parameter names for flexibility
            login_credential = username or kwargs.get('email')
            
            if not login_credential:
                return None

            # First, try to find user by email (most common case)
            try:
                user = User.objects.get(email=login_credential)
                if user.check_password(password) and self.user_can_authenticate(user):
                    return user
            except User.DoesNotExist:
                pass

            # If not found by email, try by username
            try:
                user = User.objects.get(username=login_credential)
                if user.check_password(password) and self.user_can_authenticate(user):
                    return user
            except User.DoesNotExist:
                pass

            # If still not found, run the default password hasher once to reduce timing
            # differences between an existing and non-existing user
            User().set_password(password)
            return None
                
        except Exception as e:
            # Log any unexpected errors for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Authentication error: {e}")
            
            # Run the default password hasher once to reduce timing
            # differences between an existing and non-existing user
            User().set_password(password)
            return None

    def get_user(self, user_id):
        """
        Get user by ID.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
