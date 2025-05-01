from urllib.parse import urljoin
from flask import (
    request,
    redirect,
    url_for,
    flash,
    render_template,
    abort,
    make_response,
    current_app,
    Blueprint,
)
from flask_babel import gettext, get_locale
import user_agents
from sqlalchemy import select
from . import utils, captcha, emails, hydra
from .redis import (
    SignUpRequest,
    LoginVerificationRequest,
    ChangeEmailRequest,
    ChangeRecoveryCodeRequest,
    UserLoginsHistory,
    increment_key_with_limit,
)
from .models import UserRegistration
from .extensions import db

login = Blueprint(
    "login", __name__, template_folder="templates", static_folder="static"
)
consent = Blueprint(
    "consent", __name__, template_folder="templates", static_folder="static"
)


@login.after_app_request
@consent.after_app_request
def set_cache_control_header(response):
    if "Cache-Control" not in response.headers:
        response.headers["Cache-Control"] = "no-cache"
    return response


@login.after_app_request
@consent.after_app_request
def set_frame_options_header(response):
    response.headers["X-Frame-Options"] = "DENY"
    return response


@login.app_context_processor
@consent.app_context_processor
def inject_get_locale():
    return dict(get_locale=get_locale)


def verify_captcha():
    """Verify captcha if required."""

    if current_app.config["SHOW_CAPTCHA_ON_SIGNUP"]:
        captcha_response = request.form.get(
            current_app.config["CAPTCHA_RESPONSE_FIELD_NAME"], ""
        )
        captcha_solution = captcha.verify(captcha_response, request.remote_addr)
        captcha_passed = captcha_solution.is_valid
        captcha_error_message = captcha_solution.error_message
        if not captcha_passed and captcha_error_message is None:
            captcha_error_message = gettext("Incorrect captcha solution.")
    else:
        captcha_passed = True
        captcha_error_message = None
    return captcha_passed, captcha_error_message


def query_user_credentials(email):
    return db.session.execute(
        select(
            UserRegistration.user_id,
            UserRegistration.salt,
            UserRegistration.password_hash,
        )
        .where(UserRegistration.email == email),
        bind_arguments={"bind": db.engines["replica"]},
    ).one_or_none()


def get_user_agent():
    return str(user_agents.parse(request.headers.get("User-Agent", "")))


def get_change_password_link(email):
    return urljoin(request.host_url, url_for(".signup", email=email, recover="true"))


def get_choose_password_link(signup_request):
    return urljoin(
        request.host_url, url_for(".choose_password", secret=signup_request.secret)
    )


def get_change_email_address_link(change_email_request):
    return urljoin(
        request.host_url,
        url_for(".change_email_address", secret=change_email_request.secret),
    )


def get_generate_recovery_code_link(change_recovery_code_request):
    return urljoin(
        request.host_url,
        url_for(".generate_recovery_code", secret=change_recovery_code_request.secret),
    )


def get_computer_code():
    return (
        request.cookies.get(current_app.config["COMPUTER_CODE_COOKIE_NAME"])
        or utils.generate_random_secret()
    )


def set_computer_code_cookie(response, computer_code):
    response.set_cookie(
        current_app.config["COMPUTER_CODE_COOKIE_NAME"],
        computer_code,
        max_age=1000000000,
        httponly=True,
        path=current_app.config["LOGIN_PATH"],
        secure=not current_app.config["DEBUG"],
    )


@login.route("/language/<lang>")
def set_language(lang):
    response = redirect(request.args["to"])
    response.set_cookie(
        current_app.config["LANGUAGE_COOKIE_NAME"],
        lang,
        max_age=1000000000,
        path=current_app.config["LOGIN_PATH"],
    )
    response.set_cookie(
        current_app.config["LANGUAGE_COOKIE_NAME"],
        lang,
        max_age=1000000000,
        path=current_app.config["CONSENT_PATH"],
    )
    return response


@login.route("/signup", methods=["GET", "POST"])
def signup():
    """Handle the initial sign up.

    This screen is also the first step of the "change password" flow.
    When used for changing the password a "?recover=true" query
    parameter must be added to the path.

    This page will send an email to the chosen email address. Because
    of this, it includes a CAPCHA challenge.
    """

    # If an `email` query parameter is added to the path, the given
    # email will be pre-filled int the form. This is useful when we
    # believe that the user's password has been compromised, and we
    # send the user a link to follow, so as to change his/her
    # password.
    email = request.args.get("email", "")

    is_new_user = "recover" not in request.args
    if request.method == "POST":
        captcha_passed, captcha_error_message = verify_captcha()
        email = request.form["email"].strip()

        if utils.is_invalid_email(email):
            flash(gettext("The email address is invalid."))
        elif not captcha_passed:
            flash(captcha_error_message)
        else:
            # Here we generate a unique, secret "computer code", which
            # will be sent as a cookie to the user's browser. This
            # code allows us to tell which computer the user is trying
            # to log in from. We should know this, in order to decide
            # whether to ask for a login verification code or not.
            computer_code = get_computer_code()
            computer_code_hash = utils.calc_sha256(computer_code)

            user = query_user_credentials(email)
            if user:
                if is_new_user:
                    # An user with the same email address already
                    # exists. In this case we fail silently, so as not
                    # to reveal if the email is registered or not.
                    # Though, a message is sent to the given email.
                    emails.send_duplicate_registration_email(email)
                else:
                    # Starts the "change password" flow. The
                    # `SignUpRequest` generates a secret which is
                    # emailed to the user.
                    r = SignUpRequest.create(
                        email=email,
                        cc=computer_code_hash,
                        recover="yes",
                    )
                    emails.send_change_password_email(
                        email,
                        get_choose_password_link(r),
                    )
            else:
                if is_new_user:
                    # Start the "user creation" flow. The
                    # `SignUpRequest` generates a secret which is
                    # emailed to the user.
                    r = SignUpRequest.create(
                        email=email,
                        cc=computer_code_hash,
                    )
                    emails.send_confirm_registration_email(
                        email,
                        get_choose_password_link(r),
                    )
                else:
                    # We are asked to change the password of a
                    # non-existing user. In this case we fail
                    # silently, so as not to reveal if the email is
                    # registered or not.
                    pass

            response = redirect(
                url_for(
                    ".report_sent_email",
                    email=email,
                    login_url=request.args.get("login_url"),
                    login_challenge=request.args.get("login_challenge"),
                )
            )
            set_computer_code_cookie(response, computer_code)
            return response

    title = (
        gettext("Create a New Account")
        if is_new_user
        else gettext("Change Account Password")
    )
    return render_template(
        "signup.html",
        email=email,
        title=title,
        display_captcha=captcha.display_html,
    )


@login.route("/email")
def report_sent_email():
    """Inform the user that a secret link has been sent to his/her email."""
    email = request.args["email"]
    return render_template("report_sent_email.html", email=email)


@login.route("/password/<secret>", methods=["GET", "POST"])
def choose_password(secret):
    """Handle the selection of a new password.

    This page is shown during the initial sign up, and also as a
    second step in the "change password" flow. Normally, the user will
    go to this page after clicking on a secret link, sent to his/her
    email.
    """

    signup_request = SignUpRequest.from_secret(secret)
    if not signup_request:
        return render_template("report_expired_link.html")

    is_recovery = signup_request.recover == "yes"

    if request.method == "POST":
        recovery_code = request.form.get("recovery_code", "")
        password = request.form["password"]
        min_length = current_app.config["PASSWORD_MIN_LENGTH"]
        max_length = current_app.config["PASSWORD_MAX_LENGTH"]

        if len(password) < min_length:
            flash(
                gettext(
                    "The password should have at least %(num)s characters.",
                    num=min_length,
                )
            )
        elif len(password) > max_length:
            flash(
                gettext(
                    "The password should have at most %(num)s characters.",
                    num=max_length,
                )
            )
        elif password != request.form["confirm"]:
            flash(gettext("Passwords do not match."))
        elif is_recovery and not signup_request.is_correct_recovery_code(recovery_code):
            try:
                signup_request.register_code_failure()
            except signup_request.ExceededMaxAttempts:
                abort(403)
            flash(gettext("Incorrect recovery code"))
        else:
            # NOTE: Here we use `UserLoginsHistory` to save the
            # cryptographic hash of the user's "computer code", so
            # that when the user logs in from this computer for the
            # first time, he/she will not be asked for a login
            # verification code. At this point, the ownership of the
            # user's email address has been proven.
            #
            if is_recovery:
                signup_request.accept(password)
                UserLoginsHistory(signup_request.user_id).add(signup_request.cc)

                # When changing the user's password, it is a very good
                # idea to invalidate all issued tokens for the user's
                # account.
                hydra.invalidate_credentials(signup_request.user_id)

                # Inform the user that the password on his/her account
                # has been changed. This may come as a surprise if the
                # user has been hacked.
                emails.send_change_password_success_email(
                    signup_request.email,
                    get_change_password_link(signup_request.email),
                )
                return render_template(
                    "report_recovery_success.html",
                    email=signup_request.email,
                )
            else:
                # Limit the number of allowed sign-ups for a given
                # period of time, per IP address. This seems to be
                # necessary, because CAPTCHAs are becoming less and
                # less effective. Note that this method works well
                # only for IPv4, but not for IPv6.
                increment_key_with_limit(
                    key="ip:" + request.remote_addr,
                    limit=current_app.config["SIGNUP_IP_MAX_REGISTRATIONS"],
                    period_seconds=current_app.config["SIGNUP_IP_BLOCK_SECONDS"],
                )

                # For newly registered users, a secret recovery code
                # will be generated, which they must write down and
                # hide somewhere. The recovery code is required when
                # users forget their passwords, or lose access to
                # their emails.
                recovery_code = signup_request.accept(password)
                UserLoginsHistory(signup_request.user_id).add(signup_request.cc)

                # Do not cache this page! It contains a plain-text secret.
                response = make_response(
                    render_template(
                        "report_signup_success.html",
                        email=signup_request.email,
                        recovery_code=utils.split_recovery_code_in_blocks(
                            recovery_code
                        ),
                    )
                )
                response.headers["Cache-Control"] = "no-store"
                return response

    response = make_response(
        render_template(
            "choose_password.html",
            require_recovery_code=is_recovery,
        )
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@login.route("/change-email", methods=["GET", "POST"])
def change_email_login():
    """Initiates the "change email" flow.

    Users must be able to change the email addresses associated with
    their accounts (in case they have lost access to them). To allow
    this we require:

      1. The user's current (old) email address;
      2. The user's password;
      3. The user's recovery code;
      4. The ownership of the new email address must be verified.

    This page starts this long process by asking for the user's
    current (old) email address, and the user's password. In fact,
    this page is a kind of login screen.
    """

    if request.method == "POST":
        old_email = request.form["email"].strip()
        password = request.form["password"]
        user = query_user_credentials(old_email)

        if user and user.password_hash == utils.calc_crypt_hash(user.salt, password):
            # NOTE: We create a special kind of login verification
            # request -- a login verification request without a
            # verification code. This request can only be used to set
            # a new email address for the account.
            try:
                login_verification_request = LoginVerificationRequest.create(
                    user_id=user.user_id,
                    email=old_email,
                    challenge_id=request.args.get("login_challenge", ""),
                )
            except LoginVerificationRequest.ExceededMaxAttempts:
                abort(403)

            # Inform the owner of the old email address that a request
            # has been made to change his/her account's email address.
            # This may come as a surprise if the user has been hacked.
            emails.send_change_email_address_request_email(
                old_email,
                get_change_password_link(old_email),
            )

            return redirect(
                url_for(
                    ".choose_new_email",
                    secret=login_verification_request.secret,
                )
            )

        flash(gettext("Incorrect email or password"))

    return render_template("change_email_login.html")


@login.route("/choose-email/<secret>", methods=["GET", "POST"])
def choose_new_email(secret):
    """The second step in the "change email" flow.

    This page asks the user to choose a new email address for his/her
    account, but also requires the user's recovery code. And because
    this page will send an email to the chosen email address, it also
    includes a CAPCHA challenge.
    """

    verification_request = LoginVerificationRequest.from_secret(secret)
    if not verification_request:
        return render_template("report_expired_link.html")

    if request.method == "POST":
        captcha_passed, captcha_error_message = verify_captcha()
        new_email = request.form["email"].strip()
        recovery_code = request.form.get("recovery_code", "")

        if utils.is_invalid_email(new_email):
            flash(gettext("The email address is invalid."))
        elif not captcha_passed:
            flash(captcha_error_message)
        elif not verification_request.is_correct_recovery_code(recovery_code):
            flash(gettext("Incorrect recovery code"))
        else:
            verification_request.accept()

            # The third and final step of "change email" flow is to
            # verify that the chosen new email address really is owned
            # by the user. The `ChangeEmailRequest` generates a secret
            # which is sent to the chosen new email address.
            r = ChangeEmailRequest.create(
                user_id=verification_request.user_id,
                email=new_email,
                old_email=verification_request.email,
            )
            emails.send_change_email_address_email(
                new_email,
                get_change_email_address_link(r),
            )
            return redirect(
                url_for(
                    ".report_sent_email",
                    email=new_email,
                    login_challenge=verification_request.challenge_id,
                )
            )

    response = make_response(
        render_template(
            "choose_new_email.html",
            require_recovery_code=True,
            display_captcha=captcha.display_html,
        )
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@login.route("/change-email/<secret>", methods=["GET", "POST"])
def change_email_address(secret):
    """The third and final step of "change email" flow.

    At this point the user have satisfied the following requirements:

      1. Knows the old email address;
      2. Knows the password;
      3. Knows the recovery code;
      4. Have chosen a new email address;
      5. The ownership of the new email address has been confirmed.

    Nevertheless, on this page we require the user to enter the
    password again. This prevents an attacker who can read user's
    email, to follow the secret link to this page, and finalize the
    "change email" flow, without the user's consent.
    """

    change_email_request = ChangeEmailRequest.from_secret(secret)
    if not change_email_request:
        return render_template("report_expired_link.html")

    if request.method == "POST":
        old_email = change_email_request.old_email
        password = request.form["password"]
        user = query_user_credentials(old_email)

        if user and user.password_hash == utils.calc_crypt_hash(user.salt, password):
            try:
                change_email_request.accept()
            except change_email_request.EmailAlredyRegistered:
                # Oops! A different account is already registered with
                # the new email address. Tell the user and give up.
                return redirect(
                    url_for(
                        ".report_email_change_failure",
                        new_email=change_email_request.email,
                    )
                )

            # When changing the user's email address (which is
            # required for login), it is probably a good idea to
            # invalidate all issued tokens for the user's account.
            hydra.invalidate_credentials(change_email_request.user_id)

            return redirect(
                url_for(
                    ".report_email_change_success",
                    new_email=change_email_request.email,
                    old_email=change_email_request.old_email,
                )
            )

        flash(gettext("Incorrect password"))

    return render_template(
        "enter_password.html",
        title=gettext("Change Email Address"),
    )


@login.route("/change-email-failure")
def report_email_change_failure():
    """Report "change email" flow failure.

    This page tell the user that a different account is already
    registered with that email.
    """

    return render_template(
        "report_email_change_failure.html",
        new_email=request.args["new_email"],
    )


@login.route("/change-email-success")
def report_email_change_success():
    """Report "change email" flow success.

    This page tell the user that the email address on his/her account
    has been successfully changed.
    """

    return render_template(
        "report_email_change_success.html",
        old_email=request.args["old_email"],
        new_email=request.args["new_email"],
    )


@login.route("/change-recovery-code", methods=["GET", "POST"])
def change_recovery_code():
    """Initiates the "change recovery code" flow.

    Users must be able to change their recovery codes in case they
    have lost them. To allow this we require:

      1. The user's password;
      2. The user's email address;
      3. The ownership of the user's email address must be confirmed.

    This page starts this process by sending an email to the given
    email address. Because of this, it includes a CAPCHA challenge.
    """

    email = request.args.get("email", "")

    if request.method == "POST":
        captcha_passed, captcha_error_message = verify_captcha()
        email = request.form["email"].strip()

        if utils.is_invalid_email(email):
            flash(gettext("The email address is invalid."))
        elif not captcha_passed:
            flash(captcha_error_message)
        else:
            # The `ChangeRecoveryCodeRequest` generates a secret which
            # is sent to the user's email.
            r = ChangeRecoveryCodeRequest.create(email=email)
            emails.send_change_recovery_code_email(
                email,
                get_generate_recovery_code_link(r),
            )
            return redirect(
                url_for(
                    ".report_sent_email",
                    email=email,
                    login_challenge=request.args.get("login_challenge"),
                )
            )

    return render_template(
        "signup.html",
        email=email,
        title=gettext("Change Recovery Code"),
        display_captcha=captcha.display_html,
    )


@login.route("/recovery-code/<secret>", methods=["GET", "POST"])
def generate_recovery_code(secret):
    """The second and final step in the "change recovery code" flow.

    At this point the ownership of the givens email address has been
    confirmed. On this page we require the user to enter his/her
    password.
    """

    crc_request = ChangeRecoveryCodeRequest.from_secret(secret)
    if not crc_request:
        return render_template("report_expired_link.html")

    if request.method == "POST":
        email = crc_request.email
        password = request.form["password"]
        user = query_user_credentials(email)

        if user and user.password_hash == utils.calc_crypt_hash(user.salt, password):
            new_recovery_code = crc_request.accept()

            # Do not cache this page! It contains a plain-text secret.
            response = make_response(
                render_template(
                    "report_recovery_code_change.html",
                    email=email,
                    recovery_code=utils.split_recovery_code_in_blocks(
                        new_recovery_code
                    ),
                )
            )
            response.headers["Cache-Control"] = "no-store"
            return response

        flash(gettext("Incorrect password"))

    return render_template(
        "enter_password.html",
        title=gettext("Change Recovery Code"),
    )


@login.route("/", methods=["GET", "POST"])
def login_form():
    """Handle users' login.

    Normally, Hydra (the OAuth2 server) will redirect the person who
    wants to log in to this page, passing a
    `?login_challenge=<challenge_id>` query parameter. This page must
    decide on the identity of the user, and then inform Hydra about
    the decision.
    """

    login_request = hydra.LoginRequest(request.args.get("login_challenge", ""))

    # Sometimes, after the user has already been authenticated, he/she
    # will reload this page again. In such cases we should immediately
    # redirect the user to wherever Hydra wants him/her to be.
    oauth2_subject = login_request.fetch()
    if oauth2_subject:
        return redirect(login_request.accept(oauth2_subject))

    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]
        user = query_user_credentials(email)

        if user and user.password_hash == utils.calc_crypt_hash(user.salt, password):
            oauth2_subject = hydra.get_subject(user.user_id)

            # NOTE: The `UserLoginsHistory` instance contains the
            # cryptographic hashes of the "computer code"s for the
            # computers from which the user have logged in recently.
            computer_code = get_computer_code()
            computer_code_hash = utils.calc_sha256(computer_code)
            user_logins_history = UserLoginsHistory(user.user_id)

            if user_logins_history.contains(computer_code_hash):
                # The `UserLoginsHistory` can contain a limited number
                # of unique entries. When this limit is reached, and a
                # new entry is added, the oldest entry will be
                # removed. Re-adding the `computer_code_hash` here,
                # will promote it to be the newest entry.
                user_logins_history.add(computer_code_hash)

                # At this point now we know that: 1) The person who
                # wants to log in knows the user's password; 2) There
                # was a previous successful login from the same
                # computer.
                #
                # We have our "2 factors", so we let the user in.
                return redirect(login_request.accept(oauth2_subject))

            # NOTE: At this point now we know that the person who
            # wants to log in knows the password, but we are missing
            # the second "authentication factor". To obtain it, we
            # will redirect the person who wants to log in to the
            # `enter_verification_code` page, which requires knowing
            # two secrets:
            #
            #   1. The verification cookie. We send this cookie to the
            #      user's browser. Knowing this secret ensures that
            #      the person who wants to log in knows the user's
            #      password.
            #
            #   2. The verification code. We send this code to the
            #      user's email address. Knowing this secret ensures
            #      that the person who wants to log in can read the
            #      user's email.
            #
            verification_code = utils.generate_verification_code()
            verification_cookie = utils.generate_random_secret()
            verification_cookie_hash = utils.calc_sha256(verification_cookie)

            try:
                LoginVerificationRequest.create(
                    _secret=verification_cookie_hash,
                    user_id=user.user_id,
                    email=email,
                    code=verification_code,
                    challenge_id=login_request.challenge_id,
                )
            except LoginVerificationRequest.ExceededMaxAttempts:
                abort(403)

            emails.send_verification_code_email(
                email,
                verification_code,
                get_user_agent(),
                get_change_password_link(email),
            )

            response = redirect(url_for(".enter_verification_code"))
            response.set_cookie(
                current_app.config["LOGIN_VERIFICATION_COOKIE_NAME"],
                verification_cookie,
                httponly=True,
                path=current_app.config["LOGIN_PATH"],
                secure=not current_app.config["DEBUG"],
            )
            set_computer_code_cookie(response, computer_code)
            return response

        flash(gettext("Incorrect email or password"))

    return render_template("login.html")


@login.route("/verify", methods=["GET", "POST"])
def enter_verification_code():
    """Handle entering a login verification code.

    Login verification code is required after a successful login on a
    new device. That is: a device that do not present a proper "login
    verification cookie". Once a correct login verification code has
    been entered, a proper "login verification cookie" will set on the
    device, and a login verification code will not be required again
    on this device.
    """

    cookie_name = current_app.config["LOGIN_VERIFICATION_COOKIE_NAME"]
    verification_cookie = request.cookies.get(cookie_name, "*")
    verification_cookie_hash = utils.calc_sha256(verification_cookie)

    lvr = LoginVerificationRequest.from_secret(verification_cookie_hash)
    if not lvr:
        return render_template("report_expired_link.html")

    if request.method == "POST":
        if request.form["verification_code"].strip() == lvr.code:
            lvr.accept()

            # Here we use `UserLoginsHistory` to save the
            # cryptographic hash of the user's "computer code", so
            # that the next time the user logs in from this computer,
            # he/she will not be asked for a login verification code
            # again. At this point, the ownership of the user's email
            # address has been proven.
            computer_code_hash = utils.calc_sha256(get_computer_code())
            UserLoginsHistory(lvr.user_id).add(computer_code_hash)

            # Tell Hydra this user must be let in.
            login_request = hydra.LoginRequest(lvr.challenge_id)
            oauth2_subject = hydra.get_subject(lvr.user_id)
            return redirect(login_request.accept(oauth2_subject))

        try:
            lvr.register_code_failure()
        except lvr.ExceededMaxAttempts:
            abort(403)

        flash(gettext("Invalid verification code"))

    return render_template(
        "enter_verification_code.html",
        verification_cookie_hash=verification_cookie_hash,
    )


@consent.route("/", methods=["GET", "POST"])
def grant_consent():
    """Handle the OAuth2 consent dialog.

    After a successful login, the user will be asked to authorize the
    application to perform different classes of operations ("scopes").
    """
    consent_request = hydra.ConsentRequest(request.args["consent_challenge"])

    if request.method == "POST":
        granted_scopes = request.form.getlist("granted_scope")
        return redirect(consent_request.accept(granted_scopes))

    consent_request_info = consent_request.fetch()
    requested_scopes = (
        consent_request_info["requested_scope"] if consent_request_info else []
    )
    if len(requested_scopes) == 0:
        return redirect(consent_request.accept([]))

    return render_template(
        "grant_scopes.html",
        requested_scopes=requested_scopes,
        user_id_field_name=current_app.config["API_USER_ID_FIELD_NAME"],
        client=consent_request_info["client"],
    )


@consent.route("/revoke-access", methods=["GET", "POST"])
def revoke_granted_access():
    if request.method == "POST":
        consent_request = hydra.ConsentRequest(request.args["consent_challenge"])
        consent_data = consent_request.fetch()
        if consent_data:
            hydra.revoke_consent_sessions(consent_data["subject"])

        return render_template("report_revoke_granted_access_success.html")

    return render_template("revoke_granted_access.html")
