import os
import re
import base64
import struct
import hashlib

EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def is_invalid_email(email) -> bool:
    if len(email) >= 255:
        return True
    return not EMAIL_REGEX.match(email)


def generate_password_salt(num_bytes: int = 16) -> str:
    """Generate a random Base64 encoded password salt."""
    return base64.b64encode(os.urandom(num_bytes)).decode("ascii")


def generate_random_secret(num_bytes: int = 15) -> str:
    return base64.urlsafe_b64encode(os.urandom(num_bytes)).decode("ascii")


def generate_recovery_code(num_bytes: int = 10) -> str:
    return base64.b32encode(os.urandom(num_bytes)).decode("ascii")


def normalize_recovery_code(recovery_code: str) -> str:
    return (
        recovery_code.strip()
        .replace(" ", "")
        .replace("0", "O")
        .replace("1", "I")
        .upper()
    )


def split_recovery_code_in_blocks(recovery_code: str, block_size: int = 4) -> str:
    if recovery_code is None:
        return ""
    N = block_size
    block_count = (len(recovery_code) + N - 1) // N
    blocks = [recovery_code[N * i:N * i + 4] for i in range(block_count)]
    return " ".join(blocks)


def generate_verification_code(num_digits: int = 6):
    assert 1 <= num_digits < 10
    random_number = struct.unpack("<L", os.urandom(4))[0] % (10**num_digits)
    return str(random_number).zfill(num_digits)


def calc_crypt_hash(salt: str, password: str) -> str:
    """Return a Base64 encoded cryptographic hash."""
    if salt.startswith("$"):
        # NOTE: Currently, only the default hashing method is
        # supported.
        method = salt[0:salt.rfind("$")]
        raise ValueError(f'unsupported hashing method "{method}"')

    salt_bytes = base64.b64decode(salt, validate=True)
    password_bytes = password.encode("utf8")
    if len(password_bytes) > 1024:
        raise ValueError("The password is too long.")

    return base64.b64encode(
        # The generation of the Scrypt hash requires 128*n*r bytes of
        # memory. In our case, that is 128KiB. This should be enough
        # to render GPUs ineffective to a large extent. The number of
        # rounds is given by "n". In our case we should be able to
        # crunch about 2000-3000 hashes per second per CPU core, which
        # should be enough to not be a bottleneck in case of a DoS
        # attack. Given that a single CPU core can make no more than
        # few hundreds of SSL handshakes per second, this means that
        # the SSL handshakes will almost certainly be the real CPU
        # bottleneck in case of a DoS attack.
        hashlib.scrypt(
            password=password_bytes,
            salt=salt_bytes,
            n=128,
            r=8,
            p=1,
            dklen=32,
        )
    ).decode("ascii")


def calc_sha256(computer_code: str) -> str:
    m = hashlib.sha256()
    m.update(computer_code.encode())
    return base64.urlsafe_b64encode(m.digest()).decode("ascii")
