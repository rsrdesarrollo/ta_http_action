# encoding = utf-8
import base64
import hashlib
import hmac
import json
import logging
import time

import requests


def get_credential(name: str, session_key: str):
    """
    Retrieve a credential from Splunk's password storage and decode it from JSON.

    Args:
        name: Credential name in the 'httpalert' realm
        session_key: Splunk session key from data['session_key']

    Returns:
        dict: Credential data (type, username/password, token, or header info)
    """
    url = f"https://localhost:8089/servicesNS/nobody/webhookmaster/storage/passwords/httpalert:{name}:"

    headers = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }

    params = {
        "output_mode": "json",
    }

    try:
        response = requests.get(
            url, headers=headers, params=params, verify=False, timeout=10
        )
        response.raise_for_status()

        data = response.json()

        # Get the credential data from the first entry
        entry = data.get("entry", [{}])[0]
        content = entry.get("content", {})
        clear_password = content.get("clear_password", "{}")

        return json.loads(clear_password)

    except requests.RequestException as e:
        logging.error(f"Failed to retrieve credential '{name}': {e}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode credential '{name}': {e}")
        raise


def get_hmac_headers(
    body: str,
    hmac_secret: str,
    hmac_hash_function: str,
    hmac_digest_type: str,
    hmac_sig_header: str,
    hmac_time_header: str,
):
    """
    Generate HMAC signature headers for request authentication.

    Args:
        body: Request body to sign
        hmac_secret: Secret key for HMAC generation
        hmac_hash_function: Hash algorithm (sha256, sha1, sha512, md5)
        hmac_digest_type: Output format (hex or base64)
        hmac_sig_header: Header name for the signature
        hmac_time_header: Header name for the timestamp

    Returns:
        dict: Headers with signature and timestamp
    """
    # Get current timestamp
    timestamp = str(int(time.time()))

    # Combine body and timestamp for signing
    message = f"{body}{timestamp}".encode("utf-8")
    secret = hmac_secret.encode("utf-8")

    # Get hash function
    hash_func = getattr(hashlib, hmac_hash_function.lower(), hashlib.sha256)

    # Generate HMAC
    signature = hmac.new(secret, message, hash_func)

    # Format digest
    if hmac_digest_type.lower() == "base64":
        digest = base64.b64encode(signature.digest()).decode("utf-8")
    else:  # hex
        digest = signature.hexdigest()

    headers = {}
    if hmac_sig_header:
        headers[hmac_sig_header] = digest
    if hmac_time_header:
        headers[hmac_time_header] = timestamp

    return headers


def config_to_bool(value):
    """Convert Splunk config string to boolean."""
    if value == "0":
        return False
    else:
        return True
