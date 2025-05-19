from swpt_login import captcha


def test_captcha_result():
    cr = captcha.CaptchaResult(is_valid=False, error_message="test_error")
    assert cr.is_valid is False
    assert cr.error_message == "test_error"
    assert not bool(cr)
    assert bool(captcha.CaptchaResult(is_valid=True))
