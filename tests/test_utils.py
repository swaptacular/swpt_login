import pytest
import base64
from swpt_login import utils


def test_is_invalid_email():
    assert utils.is_invalid_email('invalid_email')
    assert utils.is_invalid_email('too-l' + 500 * 'o' + 'ng@email.com')
    assert not utils.is_invalid_email('valid@email.com')


def test_generate_password_salt():
    salt = utils.generate_password_salt()
    assert isinstance(salt, str)
    assert len(base64.b64decode(salt)) == 16
    assert utils.generate_password_salt() != salt


def test_generate_random_secret():
    secret = utils.generate_random_secret()
    assert isinstance(secret, str)
    assert len(base64.urlsafe_b64decode(secret)) == 15
    assert utils.generate_random_secret() != secret


def test_generate_recovery_code():
    rc = utils.generate_recovery_code()
    assert isinstance(rc, str)
    assert len(base64.b32decode(rc)) == 10
    assert utils.generate_recovery_code() != rc


def test_split_recovery_code_in_blocks():
    assert utils.split_recovery_code_in_blocks('IZ5IFBSATO2CKMZJ') \
        == 'IZ5I FBSA TO2C KMZJ'
    assert utils.split_recovery_code_in_blocks(None) == ''


def test_normalize_recovery_code():
    rc = utils.generate_recovery_code()
    assert utils.normalize_recovery_code(rc) == rc
    assert utils.normalize_recovery_code(rc.lower()) == rc
    assert utils.normalize_recovery_code(rc.upper()) == rc
    assert utils.normalize_recovery_code('*' + rc[1:]) != rc
    assert utils.normalize_recovery_code(
        utils.split_recovery_code_in_blocks(rc)
    ) == rc

    rc = 'IZ5IFBSATO2CKMZJ'
    assert utils.normalize_recovery_code(rc.replace('I', '1')) == rc
    assert utils.normalize_recovery_code(rc.replace('O', '0')) == rc
    assert utils.normalize_recovery_code('   IZ5I  FB SATO2C KMZJ  \n') == rc


def test_generate_verification_code():
    for n in range(1, 10):
        vc = utils.generate_verification_code(num_digits=n)
        assert isinstance(vc, str)
        assert len(vc) == n
        assert vc.isdigit()

    vcs = [utils.generate_verification_code() for _ in range(10)]
    assert all([len(vc) == 6 for vc in vcs])

    first_vc = vcs[0]
    assert not all([vc == first_vc for vc in vcs])


def test_calc_crypt_hash():
    h = utils.calc_crypt_hash('salt', 'password')
    assert isinstance(h, str)
    assert len(base64.b64decode(h)) == 32
    assert h == 'QgiDbOU4LtyTKpfVGGRkaInIx2UxtoKai1g3W4d6U7I='

    with pytest.raises(ValueError):
        utils.calc_crypt_hash('$unkonwn_method$salt', 'password')

    with pytest.raises(ValueError):
        utils.calc_crypt_hash('salt', 'too_long' * 1000)


def test_calc_sha256():
    sha256 = utils.calc_sha256('123')
    assert isinstance(sha256, str)
    assert len(base64.urlsafe_b64decode(sha256)) == 32
    assert sha256 == 'pmWkWSBCL51Bfkhn79xPuKBKHz__H6B-mY6G9_eieuM='
