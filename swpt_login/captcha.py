import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from flask_babel import lazy_gettext
from flask import current_app


ERROR_MESSAGE = lazy_gettext('You did not solve the "CAPTCHA" challenge.')


class CaptchaResult:
    def __init__(self, is_valid, error_message=None):
        self.is_valid = is_valid
        self.error_message = error_message

    def __bool__(self):
        return self.is_valid


def display_html(lang="en"):
    """Gets the HTML to display the CAPTCHA."""

    script_type = current_app.config["CAPTCHA_SCRIPT_TYPE"]
    challenge_url = current_app.config["CAPTCHA_SCRIPT_SRC"]
    lang_qp = current_app.config["CAPTCHA_SCRIPT_SRC_LANG_QUERY_PARAM"]

    if lang_qp:
        challenge_url += f"?{lang_qp}={lang}"

    return """
    <div class="{div_class}" data-sitekey="{public_key}"></div>
    <script {type_attr} src="{challenge_url}" async defer></script>
    """.format(
        div_class=current_app.config["CAPTCHA_DIV_CLASS"],
        public_key=current_app.config["CAPTCHA_SITEKEY"],
        type_attr=f'type="{script_type}"' if script_type else "",
        challenge_url=challenge_url,
    )


def verify(captcha_response, remote_ip):
    """
    Submits CAPTCHA request for verification, returns `CaptchaResult`.

    captcha_response -- The value of the CAPTCHA response field from the form
    remoteip -- The user's IP address
    """

    if not captcha_response:
        return CaptchaResult(is_valid=False, error_message=ERROR_MESSAGE)

    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "User-agent": "CAPTCHA Python",
    }
    data = {
        "response": captcha_response,
    }
    secret = current_app.config["CAPTCHA_SITEKEY_SECRET"]
    auth_header = current_app.config["CAPTCHA_VERIFY_AUTH_HEADER"]

    if auth_header:
        headers[auth_header] = secret
    else:
        data["secret"] = secret

    if current_app.config["CAPTCHA_VERIFY_SEND_REMOTE_IP"]:
        data["remoteip"] = remote_ip

    http_request = Request(
        url=current_app.config["CAPTCHA_VERIFY_URL"],
        data=urlencode(data).encode("ascii"),
        headers=headers,
    )
    with urlopen(
            http_request,
            timeout=current_app.config["CAPTCHA_VERIFY_TIMEOUT_SECONDS"],
    ) as http_response:
        response_object = json.loads(http_response.read().decode())

    if response_object["success"]:
        return CaptchaResult(is_valid=True)
    else:
        return CaptchaResult(is_valid=False, error_message=ERROR_MESSAGE)
