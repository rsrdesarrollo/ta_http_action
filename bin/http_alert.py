# encoding = utf-8
import json
import logging
import sys

import requests
import urllib3
from helpers import config_to_bool, get_credential, get_hmac_headers

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.root
logging.root.setLevel(logging.INFO)
formatter = logging.Formatter("%(levelname)s %(message)s")
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(formatter)
logging.root.addHandler(handler)

DEFAULT_REQUEST_TIMEOUT = 30
DEFAUTL_REQUEST_METHOD = "post"
DEFAULT_PAYLOAD = """"{
  "sid": "$sid$",
  "search_name": "$search_name$",
  "app": "$app$",
  "owner": "$owner$",
  "results_link": "$results_link$",
  "results": $result_obj$
}"""


def render_template_with_context(template: str, context: dict):
    if template is None:
        return template

    for k, v in context.items():
        if type(v) == dict:
            v_obj = json.dumps(v)
            template = template.replace(f"${k}_obj$", v_obj)
            for sub_k, sub_v in v.items():
                sub_v = str(sub_v)
                sub_v = json.dumps(sub_v).strip('"')
                template = template.replace(f"${k}.{sub_k}$", sub_v)
        else:
            v = str(v)
            v = json.dumps(v).strip('"')
            template = template.replace(f"${k}$", v)

    return template


def process(data: dict):
    configuration: dict = data["configuration"]
    session_key = data["session_key"]

    context = {
        "sid": data["sid"],
        "search_name": data["search_name"],
        "app": data["app"],
        "owner": data["owner"],
        "results_link": data["results_link"],
        "result": data["result"],
    }

    endpoint = configuration["endpoint"]

    payload = render_template_with_context(
        configuration.get("payload", DEFAULT_PAYLOAD), context=context
    )
    method = configuration.get("method", DEFAUTL_REQUEST_METHOD)
    qs_params = render_template_with_context(
        configuration.get("qs_params", ""), context=context
    )
    custom_headers = render_template_with_context(
        configuration.get("custom_headers", "{}"), context=context
    )
    credential = configuration.get("credential", "None")

    try:
        custom_headers = json.loads(custom_headers)
    except Exception as ex:
        logging.error(
            f"Invalid custom_headers parameter format. It must be a JSON object. {ex}"
        )
        return

    try:
        payload_dict = json.loads(payload)
    except Exception as ex:
        logging.error(f"Invalid payload JSON format '{payload}'. {ex}")
        return

    if credential != "None":
        credential = get_credential(credential, session_key=session_key)
    else:
        credential = None

    verify_ssl_certificate = config_to_bool(
        configuration.get("verify_ssl_certificate", "1")
    )

    if not endpoint.startswith("https://"):
        logging.error(
            "ERROR httpalert job={} endpoint={} endpoint does not start https:// ".format(
                data["sid"], endpoint
            )
        )
        return

    auth = None
    default_headers = {}

    if not credential:
        pass
    elif credential["type"] == "basic":
        auth = (credential.get("username"), credential.get("password"))
    elif credential["type"] == "header":
        auth = None
        header_name = credential.get("header_name").strip()
        header_value = credential.get("header_value").strip()
        default_headers = {header_name: header_value}
    elif credential["type"] == "hmac":
        auth = None
        hmac_secret = credential.get("hmac_secret")
        hmac_hash_function = credential.get("hmac_hash_function")
        hmac_digest_type = credential.get("hmac_digest_type")
        hmac_sig_header = credential.get("hmac_sig_header", "").strip()
        hmac_time_header = credential.get("hmac_time_header", "").strip()

        default_headers = get_hmac_headers(
            body=payload,
            hmac_secret=hmac_secret,
            hmac_hash_function=hmac_hash_function,
            hmac_digest_type=hmac_digest_type,
            hmac_sig_header=hmac_sig_header,
            hmac_time_header=hmac_time_header,
        )

    headers = {}
    for k, v in {**custom_headers, **default_headers}.items():
        headers[k.lower()] = v

    if method in ("POST", "PUT", "PATCH"):
        headers["content-type"] = "application/json"

    response = requests.request(
        method=method,
        url=endpoint,
        auth=auth,
        params=qs_params,
        data=payload,
        headers=headers,
        timeout=DEFAULT_REQUEST_TIMEOUT,
        verify=verify_ssl_certificate,
    )

    if response.status_code // 100 != 2:
        # Status code != 2XX
        logging.error(
            "httpalert Job={sid} endpoint={endpoint} status_code={status_code} payload={payload}, headers={headers}, response={response}".format(
                sid=data["sid"],
                endpoint=endpoint,
                status_code=response.status_code,
                payload=json.dumps(payload_dict),
                headers=json.dumps(headers),
                response=json.dumps(response.text),
            )
        )
    else:
        logging.info(
            f"httpalert Job={data['sid']} endpoint={endpoint} status_code={response.status_code}"
        )


if len(sys.argv) > 1 and sys.argv[1] == "--execute":
    data = json.load(sys.stdin)
    process(data)


if len(sys.argv) > 1 and sys.argv[1] == "--test":
    data = {
        "configuration": {
            "endpoint": "https://example.com/post",
            "method": "post",
            "verify_ssl_certificate": "True",
            "qs_params": "test=true",
            "payload": "This is the body",
        },
        "result": {
            "count": "2323",
            "name": "Hello",
        },
    }
    process(data)
