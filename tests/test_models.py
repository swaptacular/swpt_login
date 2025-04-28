from swpt_login import models as m


def test_user_registration(db_session):
    db_session.add(
        m.UserRegistration(
            user_id="1",
            email="email@example.com",
            salt="abcd",
            password_hash="1234",
            recovery_code_hash="7890",
        )
    )
    db_session.commit()
    ur = m.UserRegistration.query.one()
    assert ur.user_id == "1"
    assert ur.email == "email@example.com"
    assert ur.salt == "abcd"
    assert ur.password_hash == "1234"
    assert ur.recovery_code_hash == "7890"
