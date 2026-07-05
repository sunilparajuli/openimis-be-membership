import jwt
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from core.models import User
from django.contrib.auth.models import AnonymousUser

class UnifiedAuthenticationMiddleware(MiddlewareMixin):
    """
    Unified authentication middleware supporting:
    1. Stateful Django users (Officers, Admin, etc.)
    2. Stateless Insuree tokens (linked to tblInsuree UUID)
    """
    def process_request(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return

        token = auth_header.split(" ")[1]
        try:
            # Decode JWT token using Django's SECRET_KEY
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=["HS256"]
            )
            
            # --- USER TYPE 1: Citizens / Insurees (Stateless) ---
            if payload.get("role") == "insuree":
                request.is_insuree = True
                request.insuree_uuid = payload.get("insuree_uuid")
                request.insuree_chfid = payload.get("chfid")
                request.user = AnonymousUser()
                
            # --- USER TYPE 2: Officers / Admin (Stateful) ---
            else:
                user_id = payload.get("user_id")
                if user_id:
                    user = User.objects.filter(i_user_id=user_id).first()
                    if user:
                        request.user = user
                        request.is_insuree = False
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            pass
