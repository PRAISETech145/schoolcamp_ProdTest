"""
MTN Mobile Money & Orange Money API integration for Cameroon.
All credentials are read from Django settings (loaded from .env).
"""
import uuid
import base64
import requests
import urllib3
from django.conf import settings

# Suppress SSL warnings on Windows
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ── MTN MoMo ────────────────────────────────────────────────────────────────

def mtn_get_access_token():
    """Get a Bearer token from MTN MoMo API."""
    base_url = getattr(settings, 'MTN_MOMO_BASE_URL', 'https://sandbox.momodeveloper.mtn.com')
    api_user = settings.MTN_MOMO_API_USER
    api_key  = settings.MTN_MOMO_API_KEY
    sub_key  = settings.MTN_MOMO_SUBSCRIPTION_KEY

    credentials = base64.b64encode(f"{api_user}:{api_key}".encode()).decode()

    response = requests.post(
        f"{base_url}/collection/token/",
        headers={
            "Authorization": f"Basic {credentials}",
            "Ocp-Apim-Subscription-Key": sub_key,
            "Content-Type": "application/json",
        },
        verify=False,   # ✅ Fix for Windows SSL revocation error
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("access_token")


def mtn_request_to_pay(amount, phone, reference, callback_url=None):
    """
    Send a payment request to a MTN MoMo subscriber.
    Returns True on success (202), raises Exception on failure.
    phone: 9-digit Cameroonian number e.g. '670000000'
    """
    base_url     = getattr(settings, 'MTN_MOMO_BASE_URL', 'https://sandbox.momodeveloper.mtn.com')
    sub_key      = settings.MTN_MOMO_SUBSCRIPTION_KEY
    environment  = getattr(settings, 'MTN_MOMO_ENVIRONMENT', 'sandbox')
    callback_url = callback_url or getattr(settings, 'MTN_MOMO_CALLBACK_URL', '')

    token          = mtn_get_access_token()
    x_reference_id = str(uuid.uuid4())   # MTN's own UUID, separate from our reference

    headers = {
        "Authorization":             f"Bearer {token}",
        "X-Reference-Id":            x_reference_id,
        "X-Target-Environment":      environment,
        "Ocp-Apim-Subscription-Key": sub_key,
        "Content-Type":              "application/json",
    }
    if callback_url:
        headers["X-Callback-Url"] = callback_url

    payload = {
        "amount":     str(int(amount)),
        "currency":   "XAF",
        "externalId": reference,           # our reference — comes back in webhook
        "payer": {
            "partyIdType": "MSISDN",
            "partyId":     f"237{phone}",  # full international format
        },
        "payerMessage": "SchoolCamp subscription 200 XAF",
        "payeeNote":    f"SchoolCamp ref {reference}",
    }

    resp = requests.post(
        f"{base_url}/collection/v1_0/requesttopay",
        json=payload,
        headers=headers,
        verify=False,   # ✅ Fix for Windows SSL revocation error
        timeout=30,
    )

    if resp.status_code == 202:
        return True

    raise Exception(f"MTN MoMo error {resp.status_code}: {resp.text}")


def mtn_check_payment_status(reference_id):
    """
    Check the status of a payment by its MTN X-Reference-Id.
    Returns dict with 'status' key: SUCCESSFUL / PENDING / FAILED
    """
    base_url    = getattr(settings, 'MTN_MOMO_BASE_URL', 'https://sandbox.momodeveloper.mtn.com')
    sub_key     = settings.MTN_MOMO_SUBSCRIPTION_KEY
    environment = getattr(settings, 'MTN_MOMO_ENVIRONMENT', 'sandbox')

    token = mtn_get_access_token()

    resp = requests.get(
        f"{base_url}/collection/v1_0/requesttopay/{reference_id}",
        headers={
            "Authorization":             f"Bearer {token}",
            "Ocp-Apim-Subscription-Key": sub_key,
            "X-Target-Environment":      environment,
        },
        verify=False,   # ✅ Fix for Windows SSL revocation error
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ── Orange Money ─────────────────────────────────────────────────────────────

def orange_get_access_token():
    """Get an OAuth2 Bearer token from Orange Money API."""
    base_url      = getattr(settings, 'ORANGE_MONEY_BASE_URL', 'https://api.orange.com')
    client_id     = settings.ORANGE_MONEY_CLIENT_ID
    client_secret = settings.ORANGE_MONEY_CLIENT_SECRET

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    resp = requests.post(
        f"{base_url}/oauth/v3/token",
        headers={
            "Authorization":  f"Basic {credentials}",
            "Content-Type":   "application/x-www-form-urlencoded",
            "Accept":         "application/json",
        },
        data={"grant_type": "client_credentials"},
        verify=False,   # ✅ Fix for Windows SSL revocation error
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def orange_request_to_pay(amount, phone, reference, callback_url=None):
    """
    Send a payment request to an Orange Money subscriber.
    Returns payment_url (str) or True on success, raises Exception on failure.
    phone: 9-digit Cameroonian number e.g. '699000000'
    """
    base_url     = getattr(settings, 'ORANGE_MONEY_BASE_URL', 'https://api.orange.com')
    merchant_key = settings.ORANGE_MONEY_MERCHANT_KEY
    callback_url = callback_url or getattr(settings, 'ORANGE_MONEY_CALLBACK_URL', '')

    token = orange_get_access_token()

    payload = {
        "merchant_key": merchant_key,
        "currency":     "XAF",
        "order_id":     reference,
        "amount":       int(amount),
        "return_url":   callback_url,
        "cancel_url":   callback_url,
        "notif_url":    callback_url,
        "lang":         "fr",
        "reference":    reference,
    }

    resp = requests.post(
        f"{base_url}/orange-money-webpay/cm/v1/webpayment",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
        verify=False,   # ✅ Fix for Windows SSL revocation error
        timeout=30,
    )

    if resp.status_code in (200, 201):
        data = resp.json()
        return data.get("payment_url") or True

    raise Exception(f"Orange Money error {resp.status_code}: {resp.text}")