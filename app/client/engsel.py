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

    # VALIDASI
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
            "message": str(e)
        }

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
            "message": str(e)
        }

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

    try:
        decrypted_body = decrypt_xdata(
            api_key,
            json.loads(resp.text)
        )

        print("\n======= DECRYPTED RESPONSE =======")
        print(json.dumps(decrypted_body, indent=2))
        print("==================================\n")

        return decrypted_body

    except Exception as e:
        print("[decrypt error]", e)

        return {
            "status": "ERROR",
            "message": str(e),
            "raw_response": resp.text
        }


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

    if not isinstance(res, dict):
        return {}

    return res.get("data")


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

    if "data" in res:
        if "balance" in res["data"]:
            return res["data"]["balance"]

    return {}


# =========================================================
# GET FAMILY
# =========================================================

def get_family(
    api_key: str,
    tokens: dict,
    family_code: str,
    is_enterprise: bool | None = None,
    migration_type: str | None = None
) -> dict:

    print("Fetching package family...")

    path = "api/v8/xl-stores/options/list"

    payload_dict = {
        "is_show_tagging_tab": True,
        "is_dedicated_event": True,
        "is_transaction_routine": False,
        "migration_type": migration_type or "NONE",
        "package_family_code": family_code,
        "is_autobuy": False,
        "is_enterprise": is_enterprise or False,
        "is_pdlp": True,
        "referral_code": "",
        "is_migration": False,
        "lang": "en"
    }

    res = send_api_request(
        api_key,
        path,
        payload_dict,
        tokens.get("id_token", ""),
        "POST"
    )

    if not isinstance(res, dict):
        return {}

    return res.get("data")


# =========================================================
# GET FAMILIES
# =========================================================

def get_families(
    api_key: str,
    tokens: dict,
    package_category_code: str
) -> dict:

    print("Fetching families...")

    path = "api/v8/xl-stores/families"

    payload_dict = {
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
        payload_dict,
        tokens.get("id_token", ""),
        "POST"
    )

    if not isinstance(res, dict):
        return {}

    return res.get("data")


# =========================================================
# GET PACKAGE
# =========================================================

def get_package(
    api_key: str,
    tokens: dict,
    package_option_code: str,
    package_family_code: str = "",
    package_variant_code: str = ""
) -> dict:

    path = "api/v8/xl-stores/options/detail"

    raw_payload = {
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

    print("Fetching package...")

    res = send_api_request(
        api_key,
        path,
        raw_payload,
        tokens.get("id_token", ""),
        "POST"
    )

    if not isinstance(res, dict):
        return {}

    return res.get("data")


# =========================================================
# GET ADDONS
# =========================================================

def get_addons(
    api_key: str,
    tokens: dict,
    package_option_code: str
) -> dict:

    path = "api/v8/xl-stores/options/addons-pinky-box"

    raw_payload = {
        "is_enterprise": False,
        "lang": "en",
        "package_option_code": package_option_code
    }

    print("Fetching addons...")

    res = send_api_request(
        api_key,
        path,
        raw_payload,
        tokens.get("id_token", ""),
        "POST"
    )

    if not isinstance(res, dict):
        return {}

    return res.get("data")


# =========================================================
# GET PACKAGE DETAILS
# =========================================================

def get_package_details(
    api_key: str,
    tokens: dict,
    family_code: str,
    variant_code: str,
    option_order: int,
    is_enterprise: bool | None = None,
    migration_type: str | None = None
) -> dict | None:

    family_data = get_family(
        api_key,
        tokens,
        family_code,
        is_enterprise,
        migration_type
    )

    if not family_data:
        return None

    package_variants = family_data.get(
        "package_variants",
        []
    )

    option_code = None

    for variant in package_variants:

        if variant.get("package_variant_code") == variant_code:

            package_options = variant.get(
                "package_options",
                []
            )

            for option in package_options:

                if option.get("order") == option_order:

                    option_code = option.get(
                        "package_option_code"
                    )

                    break

    if not option_code:
        return None

    return get_package(
        api_key,
        tokens,
        option_code
    )


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

    return res


# =========================================================
# NOTIFICATION DETAIL
# =========================================================

def get_notification_detail(
    api_key: str,
    tokens: dict,
    notification_id: str
):

    path = "api/v8/notification/detail"

    raw_payload = {
        "is_enterprise": False,
        "lang": "en",
        "notification_id": notification_id
    }

    res = send_api_request(
        api_key,
        path,
        raw_payload,
        tokens.get("id_token", ""),
        "POST"
    )

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

    return res.get("data")


# =========================================================
# TIERING INFO
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
# UNSUBSCRIBE
# =========================================================

def unsubscribe(
    api_key: str,
    tokens: dict,
    quota_code: str,
    product_domain: str,
    product_subscription_type: str,
) -> bool:

    path = "api/v8/packages/unsubscribe"

    raw_payload = {
        "product_subscription_type": product_subscription_type,
        "quota_code": quota_code,
        "product_domain": product_domain,
        "is_enterprise": False,
        "unsubscribe_reason_code": "",
        "lang": "en",
        "family_member_id": ""
    }

    try:

        res = send_api_request(
            api_key,
            path,
            raw_payload,
            tokens.get("id_token", ""),
            "POST"
        )

        if res and res.get("code") == "000":
            return True

        return False

    except Exception:
        return False


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

    return res
