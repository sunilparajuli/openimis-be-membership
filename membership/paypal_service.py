import base64
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


# PayPal API Configuration
PAYPAL_API_BASE = "https://api.sandbox.paypal.com"  # Use "https://api.paypal.com" for production
CLIENT_ID = "Aeu0RUl2ZCmG7yy6yREg37xvhdZ3LJc4l8SFrTjj8XwfaPrY5UoKBMDA4YAeYsBXW5I3eLZrlmPIEC-l"
SECRET = "ED-nXXRw1s-_aSMxSMlOCU4PyMryL3vrdLWmrxhTqjZBgGjUK5Loy4JJXYjTw-2D2UDTmFhqRjeezKDM"


class PayPalService:
    @staticmethod
    def get_access_token():
        """Fetch the PayPal access token."""
        url = f"{PAYPAL_API_BASE}/v1/oauth2/token"
        auth = base64.b64encode(f"{CLIENT_ID}:{SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}

        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            raise Exception(f"Failed to get access token: {response.text}")

    @staticmethod
    def create_payment(access_token, transactions):
        """Create a PayPal payment."""
        url = f"{PAYPAL_API_BASE}/v1/payments/payment"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, headers=headers, json=transactions)
        if response.status_code == 201:
            data = response.json()
            approval_url = next(
                (link["href"] for link in data.get("links", []) if link["rel"] == "approval_url"), None
            )
            execute_url = next(
                (link["href"] for link in data.get("links", []) if link["rel"] == "execute"), None
            )
            return {"approval_url": approval_url, "execute_url": execute_url}
        else:
            raise Exception(f"Failed to create payment: {response.text}")

    @staticmethod
    def execute_payment(access_token, execute_url, payer_id):
        """Execute the PayPal payment."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        data = {"payer_id": payer_id}

        response = requests.post(execute_url, headers=headers, json=data)
        print("paypal response",response)
        if response.status_code == 200:
            return response.json().get("id")
        else:
            raise Exception(f"Failed to execute payment: {response.text}")


class GetAccessToken(APIView):
    authentication_classes = ()
    permission_classes = ()
    def post(self, request):
        """Endpoint to fetch the PayPal access token."""
        try:
            access_token = PayPalService.get_access_token()
            return Response({"access_token": access_token}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from decimal import Decimal, InvalidOperation

def convert_numbers_to_float(data):
    """
    Recursively converts numeric strings in a dictionary or list
    to floats with 2-digit precision.
    """
    if isinstance(data, dict):
        return {key: convert_numbers_to_float(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_numbers_to_float(item) for item in data]
    elif isinstance(data, str):
        # Try to convert numeric strings to float
        try:
            num = Decimal(data)
            return round(float(num), 2)
        except (ValueError, TypeError, InvalidOperation):
            return data  # Return the original value if conversion fails
    else:
        return data  # Return the original value if not a dict, list, or string

class CreatePayment(APIView):
    authentication_classes = ()
    permission_classes = ()
    def post(self, request):
        """Endpoint to create a PayPal payment."""
        print('data', request.data)
        
        try:
            # import pdb;pdb.set_trace()
            access_token = PayPalService.get_access_token()
            transactions = request.data
            converted_data = convert_numbers_to_float(transactions)
            payment = PayPalService.create_payment(access_token, converted_data)
            return Response(payment, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ExecutePayment(APIView):
    authentication_classes = ()
    permission_classes = ()    
    def post(self, request):
        """Endpoint to execute a PayPal payment."""
        try:
            access_token = PayPalService.get_access_token()
            execute_url = request.data.get("execute_url")
            payer_id = request.data.get("payer_id")
            payment_id = PayPalService.execute_payment(access_token, execute_url, payer_id)
            return Response({"payment_id": payment_id}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)