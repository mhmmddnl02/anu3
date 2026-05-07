import os
import json
import uuid
import requests

from datetime import datetime, timezone

from app.client.encrypt import (
    encryptsign_xdata,
    java_like_timestamp,
    decrypt_xdata,
    API_KEY,
)

BASE_API_URL = os.getenv("BASE_API_URL")
UA = os.getenv("UA")

if not BASE_API_URL:
    raise ValueError("BASE_API_URL environment variable not set")

if not UA:
    raise ValueError("UA environment variable not set")


# =========================================================
# SEND API REQUEST
# =========================================================

def send_api_request(
    api_key: str,
    path: str,
    payload_dict: dict,
    id_token: str = "",
    method: str = "POST",
):

    print("\n========== DEBUG ==========")
    print("API_KEY:", API_KEY)
    print("UA:", UA)
    print("BASE_API_URL:", BASE_API_URL)
    print("api_key:", api_key)
    print("id_token:", id_token)
    print("===========================\n")

    # =====================================================
    # VALIDASI
    # =====================================================

    if not API_KEY:
        return {
            "status": "ERROR",
            "message": "API_KEY kosong"
        }

    if not api_key:
        return {
            "status": "ERROR",
            "message": "api_key kosong"
        }

    if not BASE_API_URL:
        return {
            "status": "ERROR",
            "message": "BASE_API_URL kosong"
        }

    if not UA:
        return {
            "status": "ERROR",
            "message": "UA kosong"
        }

    # =====================================================
    # ENCRYPT PAYLOAD
    # =====================================================

    try:
        encrypted_payload = encryptsign_xdata(
            api_key=api_key,
            method=method,
            path=path,
            id_token=id_token or "",
            payload=payload_dict
        )

    except Exception as e:
        print("[encrypt error]", e)

        return {
            "status": "ERROR",
            "message": f"Encrypt gagal: {str(e)}"
        }

    # =====================================================
    # SIGNATURE
    # =====================================================

    try:
        xtime = int(
            encrypted_payload["encrypted_body"]["xtime"]
        )

        now = datetime.now(timezone.utc).astimezone()

        sig_time_sec = (xtime // 1000)

        body = encrypted_payload["encrypted_body"]

        x_sig = encrypted_payload["x_signature"]

    except Exception as e:
        print("[signature error]", e)

        return {
            "status": "ERROR",
            "message": f"Signature gagal: {str(e)}"
        }

    # =====================================================
    # HEADERS
    # =====================================================

    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {id_token or ''}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(now),
        "x-version-app": "8.9.0",
    }

    url = f"{BASE_API_URL}/{path}"

    print("REQUEST URL:", url)

    # =====================================================
    # SEND REQUEST
    # =====================================================

    try:
        resp = requests.post(
            url,
            headers=headers,
            data=json.dumps(body),
            timeout=30
        )

    except Exception as e:
        print("[request error]", e)

        return {
            "status": "ERROR",
            "message": f"Request gagal: {str(e)}"
        }

    print("\n========== RAW RESPONSE ==========")
    print(resp.text)
    print("==================================\n")

    # =====================================================
    # DECRYPT RESPONSE
    # =====================================================

    try:
        decrypted_body = decrypt_xdata(
            api_key,
            json.loads(resp.text)
        )

        print("\n======= DECRYPTED RESPONSE =======")
        print(json.dumps(decrypted_body, indent=2))
        print("==================================\n")

    except Exception as e:
        print("[decrypt error]", e)

        return {
            "status": "ERROR",
            "message": f"Decrypt gagal: {str(e)}",
            "raw_response": resp.text
        }

    # =====================================================
    # HANDLE OTP / TOKEN EXPIRED
    # =====================================================

    try:
        response_text = str(decrypted_body).lower()

        expired_keywords = [
            "expired",
            "unauthorized",
            "invalid token",
            "invalid otp",
            "token expired",
            "session expired"
        ]

        if any(keyword in response_text for keyword in expired_keywords):

            print("OTP / Session expired")
            print("Silahkan login ulang untuk request OTP baru")

            return {
                "status": "EXPIRED",
                "message": "OTP atau session expired"
            }

    except Exception as e:
        print("[expired check error]", e)

    return decrypted_body


# =========================================================
# PROFILE
# =========================================================

def get_profile(api_key: str, access_token: str, id_token: str) -> dict:
    path = "api/v8/profile"

    raw_payload = {
        "access_token": access_token,
        "app_version": "8.9.0",
        "is_enterprise": False,
        "lang": "en"
    }

    print("Fetching profile...")

    res = send_api_request(
        api_key,
        path,
        raw_payload,
        id_token,
        "POST"
    )

    print("RAW RESPONSE:", res)

    if not isinstance(res, dict):
        return {}

    return res.get("data", {})


# =========================================================
# BALANCE
# =========================================================

def get_balance(api_key: str, id_token: str) -> dict:
    path = "api/v8/packages/balance-and-credit"

    raw_payload = {
        "is_enterprise": False,
        "lang": "en"
    }

    print("Fetching balance...")

    res = send_api_request(
        api_key,
        path,
        raw_payload,
        id_token,
        "POST"
    )

    if not isinstance(res, dict):
        return {}

    if "data" in res:
        if "balance" in res["data"]:
            return res["data"]["balance"]

    print("Error getting balance")

    return {}


# =========================================================
# LOGIN INFO
# =========================================================

def login_info(
    api_key: str,
    tokens: dict,
    is_enterprise: bool = False
):

    path = "api/v8/auth/login"

    raw_payload = {
        "access_token": tokens.get("access_token", ""),
        "is_enterprise": is_enterprise,
        "lang": "en"
    }

    res = send_api_request(
        api_key,
        path,
        raw_payload,
        tokens.get("id_token", ""),
        "POST"
    )

    if not isinstance(res, dict):
        return {}

    if "data" not in res:
        print(json.dumps(res, indent=2))
        print("Error login")

        return {}

    return res["data"]


# =========================================================
# TIERING
# =========================================================

def get_tiering_info(
    api_key: str,
    tokens: dict
) -> dict:

    path = "gamification/api/v8/loyalties/tiering/info"

    raw_payload = {
        "is_enterprise": False,
        "lang": "en"
    }

    print("Fetching tiering info...")

    res = send_api_request(
        api_key,
        path,
        raw_payload,
        tokens.get("id_token", ""),
        "POST"
    )

    if not isinstance(res, dict):
        return {}

    return res.get("data", {})


# =========================================================
# NOTIFICATIONS
# =========================================================

def get_notifications(
    api_key: str,
    tokens: dict,
):

    path = "api/v8/notification-non-grouping"

    raw_payload = {
        "is_enterprise": False,
        "lang": "en"
    }

    res = send_api_request(
        api_key,
        path,
        raw_payload,
        tokens.get("id_token", ""),
        "POST"
    )

    if not isinstance(res, dict):
        return {}

    return res


# =========================================================
# TRANSACTION HISTORY
# =========================================================

def get_transaction_history(
    api_key: str,
    tokens: dict
) -> dict:

    path = "payments/api/v8/transaction-history"

    raw_payload = {
        "is_enterprise": False,
        "lang": "en"
    }

    print("Fetching transaction history...")

    res = send_api_request(
        api_key,
        path,
        raw_payload,
        tokens.get("id_token", ""),
        "POST"
    )

    if not isinstance(res, dict):
        return {}

    return res.get("data", {})


# =========================================================
# DASHBOARD SEGMENTS
# =========================================================

def dashboard_segments(
    api_key: str,
    tokens: dict,
) -> dict:

    path = "dashboard/api/v8/segments"

    raw_payload = {
        "access_token": tokens.get("access_token", "")
    }

    res = send_api_request(
        api_key,
        path,
        raw_payload,
        tokens.get("id_token", ""),
        "POST"
    )

    if not isinstance(res, dict):
        return {}

    return res
