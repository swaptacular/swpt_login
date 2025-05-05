import re
from flask import render_template
from flask_babel import gettext
from flask_mail import Message
from .extensions import mail

PARAGRAPHS_SEPARATOR_REGEX = re.compile(r"(?:\r?\n){2,}", re.MULTILINE)
SIGNATURE_START_REGEX = re.compile(r"\A-- \r?\n", re.MULTILINE)
ANCHOR_LINE_REGEX = re.compile(r"\Ahttps?://\S+\Z", re.MULTILINE)


def text_to_html_document(text: str) -> str:
    return render_template("html_mail_layout.html", body=text_to_html(text))


def text_to_html(text: str) -> str:
    html_paragraphs = []

    for p in PARAGRAPHS_SEPARATOR_REGEX.split(text):
        if p != "":
            if SIGNATURE_START_REGEX.match(p):
                p = "<br />".join(p.split("\n"))
            elif ANCHOR_LINE_REGEX.match(p):
                p = f'<a href="{p}">{p}</a>'
            html_paragraphs.append(f"<p>{p}</p>")

    return "".join(html_paragraphs)


def send_duplicate_registration_email(email):
    text = render_template(
        "duplicate_registration.txt",
        email=email,
    )
    msg = Message(
        subject=gettext("Duplicate Registration"),
        recipients=[email],
        body=text,
        html=text_to_html_document(text),
    )
    mail.send(msg)


def send_change_password_email(email, choose_password_link):
    text = render_template(
        "change_password.txt",
        email=email,
        choose_password_link=choose_password_link,
    )
    msg = Message(
        subject=gettext("Change Account Password"),
        recipients=[email],
        body=text,
        html=text_to_html_document(text),
    )
    mail.send(msg)


def send_change_password_success_email(email, change_password_page):
    text = render_template(
        "change_password_success.txt",
        email=email,
        change_password_page=change_password_page,
    )
    msg = Message(
        subject=gettext("Changed Account Password"),
        recipients=[email],
        body=text,
        html=text_to_html_document(text),
    )
    mail.send(msg)


def send_confirm_registration_email(email, register_link):
    text = render_template(
        "confirm_registration.txt",
        email=email,
        register_link=register_link,
    )
    msg = Message(
        subject=gettext("Create a New Account"),
        recipients=[email],
        body=text,
        html=text_to_html_document(text),
    )
    mail.send(msg)


def send_verification_code_email(
    email, verification_code, user_agent, change_password_page
):
    text = render_template(
        "verification_code.txt",
        verification_code=verification_code,
        user_agent=user_agent,
        change_password_page=change_password_page,
    )
    msg = Message(
        subject=gettext("New login from %(user_agent)s", user_agent=user_agent),
        recipients=[email],
        body=text,
        html=text_to_html_document(text),
    )
    mail.send(msg)


def send_change_email_address_request_email(email, change_password_page):
    text = render_template(
        "request_email_change.txt",
        change_password_page=change_password_page,
    )
    msg = Message(
        subject=gettext("Change Email Address"),
        recipients=[email],
        body=text,
        html=text_to_html_document(text),
    )
    mail.send(msg)


def send_change_email_address_email(email, change_email_address_link):
    text = render_template(
        "change_email_address.txt",
        email=email,
        change_email_address_link=change_email_address_link,
    )
    msg = Message(
        subject=gettext("Change Email Address"),
        recipients=[email],
        body=text,
        html=text_to_html_document(text),
    )
    mail.send(msg)


def send_change_recovery_code_email(email, change_recovery_code_link):
    text = render_template(
        "change_recovery_code.txt",
        email=email,
        change_recovery_code_link=change_recovery_code_link,
    )
    msg = Message(
        subject=gettext("Change Recovery Code"),
        recipients=[email],
        body=text,
        html=text_to_html_document(text),
    )
    mail.send(msg)


def send_delete_account_email(
        email,
        delete_account_link,
        change_password_page,
):
    text = render_template(
        "delete_account.txt",
        email=email,
        delete_account_link=delete_account_link,
        change_password_page=change_password_page,
    )
    msg = Message(
        subject=gettext("Delete Account"),
        recipients=[email],
        body=text,
        html=text_to_html_document(text),
    )
    mail.send(msg)
