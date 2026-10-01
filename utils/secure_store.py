import base64
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path
from typing import Optional


CRYPTPROTECT_UI_FORBIDDEN = 0x1


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _blob_from_bytes(data: bytes):
    if not data:
        return DATA_BLOB(), None
    buffer = ctypes.create_string_buffer(data, len(data))
    blob = DATA_BLOB(
        len(data),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    return blob, buffer


def _dpapi_protect(data: bytes, description: str = "SimpleRPA secret") -> bytes:
    if os.name != "nt":
        raise RuntimeError("Windows DPAPI is only available on Windows")

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    in_blob, in_buffer = _blob_from_bytes(data)
    out_blob = DATA_BLOB()

    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        description,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    _ = in_buffer  # keep input memory alive for the API call

    if not ok:
        raise ctypes.WinError()

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _dpapi_unprotect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Windows DPAPI is only available on Windows")

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    in_blob, in_buffer = _blob_from_bytes(data)
    out_blob = DATA_BLOB()
    description = ctypes.c_wchar_p()

    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        ctypes.byref(description),
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    _ = in_buffer

    if not ok:
        raise ctypes.WinError()

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)
        if description:
            kernel32.LocalFree(description)


class WindowsSecretStore:
    """Store small secrets encrypted with Windows DPAPI for the current user."""

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            appdata = os.getenv("APPDATA")
            base = Path(appdata) if appdata else (Path.home() / "AppData" / "Roaming")
            path = base / "SimpleRPA" / "secrets.json"
        self.path = Path(path)

    def save(self, name: str, value: str):
        value = str(value or "")
        if not value:
            self.delete(name)
            return

        data = self._read_all()
        encrypted = _dpapi_protect(
            value.encode("utf-8"),
            description=f"SimpleRPA:{name}",
        )
        data[name] = base64.b64encode(encrypted).decode("ascii")
        self._write_all(data)

    def load(self, name: str) -> Optional[str]:
        data = self._read_all()
        encoded = data.get(name)
        if not encoded:
            return None

        try:
            encrypted = base64.b64decode(encoded)
            plain = _dpapi_unprotect(encrypted)
            return plain.decode("utf-8")
        except Exception:
            return None

    def delete(self, name: str):
        data = self._read_all()
        if name not in data:
            return

        del data[name]
        if data:
            self._write_all(data)
        else:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass

    def has(self, name: str) -> bool:
        return bool(self.load(name))

    def _read_all(self):
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return {}

    def _write_all(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)

        payload = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        os.replace(tmp_path, self.path)


AGNES_KEY_NAME = "agnes_api_key"


def load_saved_agnes_key() -> Optional[str]:
    return WindowsSecretStore().load(AGNES_KEY_NAME)


def save_agnes_key(value: str):
    WindowsSecretStore().save(AGNES_KEY_NAME, value)


def delete_saved_agnes_key():
    WindowsSecretStore().delete(AGNES_KEY_NAME)
