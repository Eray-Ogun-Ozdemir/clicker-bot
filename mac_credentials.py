"""Generic password items in the current user's macOS Keychain."""
import ctypes as c
from ctypes.util import find_library

security = c.CDLL(find_library("Security"))
pointer = c.c_void_p
size = c.c_uint32
find = security.SecKeychainFindGenericPassword
find.argtypes = [pointer, size, c.c_char_p, size, c.c_char_p,
                 c.POINTER(size), c.POINTER(pointer), pointer]
add = security.SecKeychainAddGenericPassword
add.argtypes = [pointer, size, c.c_char_p, size, c.c_char_p, size, c.c_char_p, pointer]
free = security.SecKeychainItemFreeContent
free.argtypes = [pointer, pointer]
delete = security.SecKeychainItemDelete
delete.argtypes = [pointer]
release = c.CDLL(find_library("CoreFoundation")).CFRelease
release.argtypes = [pointer]
NOT_FOUND = -25300


class Keyring:
    def set_password(self, service, account, password):
        service, account, secret = service.encode(), account.encode(), password.encode()
        status = add(None, len(service), service, len(account), account, len(secret), secret, None)
        if status:
            raise ValueError(f"Anahtar Zinciri yazma hatası ({status}).")

    def get_password(self, service, account):
        service, account = service.encode(), account.encode()
        length, secret = size(), pointer()
        status = find(None, len(service), service, len(account), account,
                      c.byref(length), c.byref(secret), None)
        if status == NOT_FOUND:
            return None
        if status:
            raise ValueError(f"Anahtar Zinciri okuma hatası ({status}).")
        try:
            return c.string_at(secret, length.value).decode()
        finally:
            free(None, secret)

    def has_password(self, service, account):
        """Whether the item exists. Does not read the secret, so macOS never asks for access."""
        service, account = service.encode(), account.encode()
        status = find(None, len(service), service, len(account), account, None, None, None)
        if status == NOT_FOUND:
            return False
        if status:
            raise ValueError(f"Anahtar Zinciri okuma hatası ({status}).")
        return True

    def delete_password(self, service, account):
        """Delete the item. Returns False when there was nothing to delete."""
        service, account = service.encode(), account.encode()
        item = pointer()
        status = find(None, len(service), service, len(account), account, None, None, c.byref(item))
        if status == NOT_FOUND:
            return False
        if status:
            raise ValueError(f"Anahtar Zinciri okuma hatası ({status}).")
        try:
            status = delete(item)
        finally:
            release(item)
        if status:
            raise ValueError(f"Anahtar Zinciri silme hatası ({status}).")
        return True
