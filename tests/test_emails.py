from swpt_login import emails
from dataclasses import dataclass
from unittest.mock import Mock


@dataclass
class FakeMail:
    send = Mock()


def test_email_templates(mocker, app):
    mail = FakeMail()
    mocker.patch("swpt_login.emails.mail", mail)
    email = "test@example.com"
    link = "http://example.com"

    with app.test_request_context():
        emails.send_duplicate_registration_email(email)
        emails.send_change_password_email(email, link)
        emails.send_change_password_success_email(email, link)
        emails.send_confirm_registration_email(email, link)
        emails.send_verification_code_email(email, "123456", "Mozilla", link)
        emails.send_change_email_address_request_email(email, link)
        emails.send_change_email_address_email(email, link)
        emails.send_change_recovery_code_email(email, link)
        emails.send_delete_account_email(email, link, link)

    assert mail.send.call_count == 9


def test_email_sending(app):
    email = "test@example.com"
    link = "http://example.com"

    with app.test_request_context():
        emails.send_duplicate_registration_email(email)
        emails.send_change_password_email(email, link)
        emails.send_change_password_success_email(email, link)
        emails.send_confirm_registration_email(email, link)
        emails.send_verification_code_email(email, "123456", "Mozilla", link)
        emails.send_change_email_address_request_email(email, link)
        emails.send_change_email_address_email(email, link)
        emails.send_change_recovery_code_email(email, link)
        emails.send_delete_account_email(email, link, link)


def test_text_to_html_document(app):
    from swpt_login.emails import text_to_html_document

    document = text_to_html_document("Hello!")
    assert "Hello!" in document
    assert document.startswith("<!DOCTYPE")


def test_text_to_html(app):
    from swpt_login.emails import text_to_html

    assert text_to_html("Hello!") == "<p>Hello!</p>"
    assert text_to_html("First\nSecond\n") == "<p>First\nSecond\n</p>"
    assert text_to_html("First\n\nSecond\n") == "<p>First</p><p>Second\n</p>"
    assert text_to_html("First\n\n\nSecond\n") == "<p>First</p><p>Second\n</p>"
    assert text_to_html("\n\nFirst\n\n\nSecond\n\n\n") == "<p>First</p><p>Second</p>"
    assert (
        text_to_html("https://example.com/")
        == '<p><a href="https://example.com/">https://example.com/</a></p>'
    )
    assert (
        text_to_html("https://example.com/\nsomething")
        == "<p>https://example.com/\nsomething</p>"
    )
    assert (
        text_to_html("https://example.com/ something")
        == "<p>https://example.com/ something</p>"
    )
    assert (
        text_to_html("First\n\n-- \nSignature\nLine2\nLine3\n")
        == "<p>First</p><p>-- <br />Signature<br />Line2<br />Line3<br /></p>"
    )
