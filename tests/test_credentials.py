"""The credential file: the site address, the user, and the Application Password."""
import os

import pytest

from wp_publish.credentials import CredentialError, load_credentials

SECRET = "abcd efgh ijkl mnop qrst uvwx"


def write(tmp_path, mode=0o600):
    path = tmp_path / "wordpress.env"
    path.write_text(
        "WP_URL=https://joyweshare.org\nWP_USER=don\n" f"WP_APP_PASSWORD={SECRET}\n",
        encoding="utf-8",
    )
    os.chmod(path, mode)
    return path


def test_reads_the_site_user_and_password(tmp_path):
    creds = load_credentials(write(tmp_path))
    assert creds.url == "https://joyweshare.org"
    assert creds.user == "don"
    assert creds.password == SECRET


def test_the_password_never_shows_when_printed(tmp_path):
    creds = load_credentials(write(tmp_path))
    assert SECRET not in repr(creds)
    assert SECRET not in str(creds)


def test_a_missing_file_stops_the_run(tmp_path):
    with pytest.raises(CredentialError):
        load_credentials(tmp_path / "nowhere.env")


@pytest.mark.parametrize("mode", [0o640, 0o644, 0o604])
def test_a_file_others_can_read_stops_the_run_without_showing_the_password(tmp_path, mode):
    with pytest.raises(CredentialError) as error:
        load_credentials(write(tmp_path, mode))
    assert SECRET not in str(error.value)
