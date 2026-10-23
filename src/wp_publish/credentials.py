"""The credential file: the site address, the user, and the Application Password.

The file holds three lines:

    WP_URL=https://example.org
    WP_USER=name
    WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

and must be readable by its owner only (chmod 600).
"""
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

KEYS = ("WP_URL", "WP_USER", "WP_APP_PASSWORD")


class CredentialError(Exception):
    """The credential file cannot be used. The message never holds the password."""


@dataclass(frozen=True)
class Credentials:
    url: str
    user: str
    password: str = field(repr=False)


def load_credentials(path: Path) -> Credentials:
    path = Path(path).expanduser()
    if not path.is_file():
        raise CredentialError(f"{path}: no credential file there")
    mode = stat.S_IMODE(os.stat(path).st_mode)
    if mode & 0o077:
        raise CredentialError(
            f"{path}: readable by others (mode {oct(mode)}); it must be 600 (chmod 600 {path})"
        )
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip()
    missing = [name for name in KEYS if not values.get(name)]
    if missing:
        raise CredentialError(f"{path}: missing {', '.join(missing)}")
    return Credentials(
        url=values["WP_URL"].rstrip("/"),
        user=values["WP_USER"],
        password=values["WP_APP_PASSWORD"],
    )
