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
        if status == -25300:
            return None
        if status:
            raise ValueError(f"Anahtar Zinciri okuma hatası ({status}).")
        try:
            return c.string_at(secret, length.value).decode()
        finally:
            free(None, secret)
