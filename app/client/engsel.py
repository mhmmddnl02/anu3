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

# =========================================================
# ENV
# =========================================================

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

    safe_id_token = id_token or ""

    print("\n========== DEBUG ==========")
    print("PATH:", path)
    print("API_KEY:", API_KEY)
    print("USER_AGENT:", UA)
    print("ID_TOKEN:", safe_id_token)
    print("===========================\n")

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

    # =====================================================
    # ENCRYPT
    # =====================================================

    try:

        encrypted_payload = encryptsign_xdata(
            api_key=api_key,
            method=method,
            path=path,
            id_token=safe_id_token,
            payload=payload_dict
        )

    except Exception as e:

        print("[encrypt error]", e)

        return {
            "status": "ERROR",
            "message": str(e)
        }

    # =====================================================
    # SIGNATURE
    # =====================================================

    try:

        xtime = int(
            encrypted_payload["encrypted_body"]["xtime"]
        )

        now = datetime.now(
            timezone.utc
        ).astimezone()

        sig_time_sec = (xtime // 1000)

        body = encrypted_payload["encrypted_body"]

        x_sig = encrypted_payload["x_signature"]

    except Exception as e:

        print("[signature error]", e)

        return {
            "status": "ERROR",
            "message": str(e)
        }

    # =====================================================
    # HEADERS
    # =====================================================

    headers = {
        "host": BASE_API_URL.replace(
            "https://",
            ""
        ),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {safe_id_token}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(now),
        "x-version-app": "8.9.0",
    }

    url = f"{BASE_API_URL}/{path}"

    # =====================================================
    # REQUEST
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
            "message": str(e)
        }

    print("\n========== RAW RESPONSE ==========")
    print(resp.text)
    print("==================================\n")

    # =====================================================
    # PARSE JSON
    # =====================================================

    try:
        response_json = json.loads(resp.text)

    except Exception:

        return {
            "status": "ERROR",
            "message": "Response bukan JSON",
            "raw_response": resp.text
        }

    # =====================================================
    # DECRYPT
    # =====================================================

    try:

        decrypted_body = decrypt_xdata(
            api_key,
            response_json
        )

        print("\n======= DECRYPTED RESPONSE =======")
        print(json.dumps(decrypted_body, indent=2))
        print("==================================\n")

    except Exception as e:

        print("[decrypt error]", e)

        return {
            "status": "ERROR",
            "message": str(e),
            "raw_response": resp.text
        }

    return decrypted_body


# =========================================================
# PROFILE
# =========================================================

def get_profile(
    api_key: str,
    access_token: str,
    id_token: str
):

    path = "api/v8/profile"

    payload = {
        "access_token": access_token,
        "app_version": "8.9.0",
        "is_enterprise": False,
        "lang": "en"
    }

    res = send_api_request(
        api_key,
        path,
        payload,
        id_token
    )

    if not isinstance(res, dict):
        return {}

    return res.get("data", {})


# =========================================================
# BALANCE
# =========================================================

def get_balance(
    api_key: str,
    id_token: str
):

    path = "api/v8/packages/balance-and-credit"

    payload = {
        "is_enterprise": False,
        "lang": "en"
    }

    res = send_api_request(
        api_key,
        path,
        payload,
        id_token
    )

    if not isinstance(res, dict):
        return {}

    return (
        res.get("data", {})
        .get("balance", {})
    )


# =========================================================
# GET FAMILY
# =========================================================

def get_family(
    api_key: str,
    tokens: dict,
    family_code: str,
    is_enterprise: bool = False,
    migration_type: str = "NONE"
):

    path = "api/v8/xl-stores/options/list"

    payload = {
        "is_show_tagging_tab": True,
        "is_dedicated_event": True,
        "is_transaction_routine": False,
        "migration_type": migration_type,
        "package_family_code": family_code,
        "is_autobuy": False,
        "is_enterprise": is_enterprise,
        "is_pdlp": True,
        "referral_code": "",
        "is_migration": False,
        "lang": "en"
    }

    res = send_api_request(
        api_key,
        path,
        payload,
        tokens.get("id_token", "")
    )

    if not isinstance(res, dict):
        return {}

    return res.get("data", {})


# =========================================================
# GET FAMILIES
# =========================================================

def get_families(
    api_key: str,
    tokens: dict,
    package_category_code: str
):

    path = "api/v8/xl-stores/families"

    payload = {
        "migration_type": "",
        "is_enterprise": False,
        "is_shareable": False,
        "package_category_code": package_category_code,
        "with_icon_url": True,
        "is_migration": False,
        "lang": "en"
    }

    res = send_api_request(
        api_key,
        path,
        payload,
        tokens.get("id_token", "")
    )

    if not isinstance(res, dict):
        return {}

    return res.get("data", {})


# =========================================================
# GET PACKAGE
# =========================================================

def get_package(
    api_key: str,
    tokens: dict,
    package_option_code: str,
    package_family_code: str = "",
    package_variant_code: str = ""
):

    path = "api/v8/xl-stores/options/detail"

    payload = {
        "is_transaction_routine": False,
        "migration_type": "NONE",
        "package_family_code": package_family_code,
        "family_role_hub": "",
        "is_autobuy": False,
        "is_enterprise": False,
        "is_shareable": False,
        "is_migration": False,
        "lang": "en",
        "package_option_code": package_option_code,
        "is_upsell_pdp": False,
        "package_variant_code": package_variant_code
    }

    res = send_api_request(
        api_key,
        path,
        payload,
        tokens.get("id_token", "")
    )

    if not isinstance(res, dict):
        return {}

    return res.get("data", {})


# =========================================================
# GET ADDONS
# =========================================================

def get_addons(
    api_key: str,
    tokens: dict,
    package_option_code: str
):

    path = "api/v8/xl-stores/options/addons-pinky-box"

    payload = {
        "is_enterprise": False,
        "lang": "en",
        "package_option_code": package_option_code
    }

    res = send_api_request(
        api_key,
        path,
        payload,
        tokens.get("id_token", "")
    )

    if not isinstance(res, dict):
        return {}

    return res.get("data", {})
