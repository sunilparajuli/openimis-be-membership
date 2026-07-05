
import graphene
import random
import time
from .services import PDFGenerationService  
from core.models import User, Role, UserRole
from insuree.models import Insuree
from membership.utils.db_helper import SQLiteHelper
from membership.utils.auth_helper import authenticate_and_get_token
from membership.views import create_insuree_user

import jwt
import datetime
from django.conf import settings

def generate_insuree_token(insuree):
    expiration = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    payload = {
        "insuree_uuid": str(insuree.uuid),
        "chfid": insuree.chf_id,
        "role": "insuree",
        "exp": expiration,
        "iat": datetime.datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token

class GeneratePdfSlip(graphene.Mutation):
    class Arguments:
        insuree_uuid = graphene.String(required=True)
        slip_type = graphene.String(required=False)

    base64_pdf = graphene.String()

    def mutate(self, info, insuree_uuid, slip_type=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("You do not have permission to access this resource.")
        
        pdf_base64 = PDFGenerationService.generate_pdf(user, insuree_uuid, slip_type)
        return GeneratePdfSlip(base64_pdf=pdf_base64)


class LoginInsuree(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)

    token = graphene.String()
    refresh_token = graphene.String()
    is_insuree = graphene.Boolean()
    insuree_uuid = graphene.String()
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, username, password):
        request = info.context
        db_helper = SQLiteHelper()
        try:
            user = User.objects.filter(username=username).first()
            if not user:
                return LoginInsuree(success=False, message="User not found")

            is_insuree = db_helper.is_insuree(user.i_user_id)
            insuree_id = db_helper.get_insuree_id_by_user_id(user.i_user_id)
            insuree = Insuree.objects.filter(id=insuree_id).first() if is_insuree else None

            token_data = authenticate_and_get_token(username, password, request)
            if token_data:
                if is_insuree and insuree:
                    stateless_token = generate_insuree_token(insuree)
                    return LoginInsuree(
                        success=True,
                        token=stateless_token,
                        refresh_token=stateless_token,
                        is_insuree=True,
                        insuree_uuid=insuree.uuid,
                        message="Login successful (stateless)"
                    )
                else:
                    return LoginInsuree(
                        success=True,
                        token=token_data["token"],
                        refresh_token=token_data["token"],
                        is_insuree=False,
                        message="Login successful (stateful)"
                    )
            else:
                return LoginInsuree(success=False, message="Invalid username or password")
        except Exception as e:
            return LoginInsuree(success=False, message=str(e))
        finally:
            db_helper.close()


class RegisterInsuree(graphene.Mutation):
    class Arguments:
        chfid = graphene.String(required=True)
        head_chfid = graphene.String(required=True)
        dob = graphene.String(required=True)
        phone = graphene.String(required=True)
        email = graphene.String(required=False)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, chfid, head_chfid, dob, phone, email=None):
        try:
            head_insuree = Insuree.objects.get(chf_id=head_chfid, head=True)
            insuree = Insuree.objects.get(chf_id=chfid, family=head_insuree.family)
        except Insuree.DoesNotExist:
            return RegisterInsuree(success=False, message="Insuree with the provided details does not exist.")

        if phone:
            insuree.phone = phone
        if email:
            insuree.email = email
        insuree.save()

        # Generate OTP
        otp_code = str(random.randint(100000, 999999))
        db = SQLiteHelper()
        db.insert_user(insuree.id, phone, otp_code)
        db.close()

        print(f"OTP for {phone}: {otp_code}")
        return RegisterInsuree(success=True, message="OTP sent successfully.")


class VerifyOtp(graphene.Mutation):
    class Arguments:
        phone = graphene.String(required=True)
        otp = graphene.String(required=True)
        username = graphene.String(required=True)
        password = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, phone, otp, username, password):
        db = SQLiteHelper()
        user_data = db.get_user_by_phone(phone)
        db.close()

        if not user_data:
            return VerifyOtp(success=False, message="User not found.")

        _, insuree_id, _, saved_otp, user_id, otp_expiry, otp_validated = user_data

        if saved_otp != otp:
            return VerifyOtp(success=False, message="Invalid OTP.")

        if int(time.time()) > otp_expiry:
            return VerifyOtp(success=False, message="OTP expired.")

        data = {
            "insuree_id": insuree_id,
            "username": username,
            "password": password,
            "phone": phone,
        }
        create_user_response, status_code = create_insuree_user(data)
        if status_code == 201:
            return VerifyOtp(success=True, message="OTP validated, registration complete.")
        else:
            return VerifyOtp(success=False, message=str(create_user_response))
