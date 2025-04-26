from swpt_login import emails
from dataclasses import dataclass
from unittest.mock import Mock


@dataclass
class FakeMail:
    send = Mock()


def test_email_templates(mocker, app):
    mail = FakeMail()
    mocker.patch("swpt_login.emails.mail", mail)
    email = 'test@example.com'
    link = 'http://example.com'

    with app.test_request_context():
        emails.send_duplicate_registration_email(email)
        emails.send_change_password_email(email, link)
        emails.send_change_password_success_email(email, link)
        emails.send_confirm_registration_email(email, link)
        emails.send_verification_code_email(email, '123456', 'Mozilla', link)
        emails.send_change_email_address_request_email(email, link)
        emails.send_change_email_address_email(email, link)
        emails.send_change_recovery_code_email(email, link)

    assert mail.send.call_count == 8
