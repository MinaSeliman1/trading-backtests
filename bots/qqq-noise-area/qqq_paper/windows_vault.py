"""Secrets propres à l'utilisateur Windows, jamais dans les fichiers du bot."""
import ctypes
from ctypes import wintypes
import json
import os

TARGET='TradingBacktests/QQQNoiseArea/PAPER'


class CredentialError(Exception):pass


def validate_credentials(key,secret):
    if not all(isinstance(v,str) and 1<=len(v)<=1024 and v.isascii() and not any(c.isspace() or ord(c)<32 or ord(c)==127 for c in v) for v in (key,secret)):
        raise CredentialError('Invalid PAPER credentials; values omitted')
    return key,secret


class Credential(ctypes.Structure):
    _fields_=[('Flags',wintypes.DWORD),('Type',wintypes.DWORD),('TargetName',wintypes.LPWSTR),('Comment',wintypes.LPWSTR),
        ('LastWritten',wintypes.FILETIME),('CredentialBlobSize',wintypes.DWORD),('CredentialBlob',ctypes.POINTER(wintypes.BYTE)),
        ('Persist',wintypes.DWORD),('AttributeCount',wintypes.DWORD),('Attributes',ctypes.c_void_p),
        ('TargetAlias',wintypes.LPWSTR),('UserName',wintypes.LPWSTR)]


class WindowsVault:
    def __init__(self,target=TARGET):
        if os.name!='nt':raise CredentialError('Windows Credential Manager required')
        if target!=TARGET and not target.startswith('TradingBacktests.Tests/'):raise CredentialError('Unapproved credential target')
        self.target=target;self.api=ctypes.WinDLL('Advapi32.dll',use_last_error=True)
        self.api.CredWriteW.argtypes=[ctypes.POINTER(Credential),wintypes.DWORD];self.api.CredWriteW.restype=wintypes.BOOL
        self.api.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(Credential))];self.api.CredReadW.restype=wintypes.BOOL
        self.api.CredDeleteW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD];self.api.CredDeleteW.restype=wintypes.BOOL
        self.api.CredFree.argtypes=[ctypes.c_void_p];self.api.CredFree.restype=None

    def save(self,key,secret):
        validate_credentials(key,secret)
        raw=json.dumps(dict(key=key,secret=secret),ensure_ascii=True).encode('utf-8')
        if len(raw)>2500:raise CredentialError('Credential payload too large; values omitted')
        buffer=ctypes.create_string_buffer(raw)
        row=Credential();row.Type=1;row.TargetName=self.target;row.Comment='QQQ Noise Area PAPER data, local simulation'
        row.CredentialBlobSize=len(raw);row.CredentialBlob=ctypes.cast(buffer,ctypes.POINTER(wintypes.BYTE))
        row.Persist=2;row.UserName='QQQ PAPER data'
        try:
            if not self.api.CredWriteW(ctypes.byref(row),0):raise CredentialError(f'Windows Credential Manager write failed ({ctypes.get_last_error()})')
        finally:ctypes.memset(ctypes.addressof(buffer),0,len(buffer))

    def load(self):
        pointer=ctypes.POINTER(Credential)()
        if not self.api.CredReadW(self.target,1,0,ctypes.byref(pointer)):
            raise CredentialError(f'Windows PAPER credential unavailable ({ctypes.get_last_error()})')
        try:
            if not 1<=pointer.contents.CredentialBlobSize<=2500:raise CredentialError('Invalid stored PAPER credential')
            raw=ctypes.string_at(pointer.contents.CredentialBlob,pointer.contents.CredentialBlobSize)
            try:
                data=json.loads(raw.decode('utf-8'));return validate_credentials(data['key'],data['secret'])
            except (KeyError,TypeError,ValueError,UnicodeError):raise CredentialError('Invalid stored PAPER credential; values omitted') from None
        finally:self.api.CredFree(pointer)

    def delete(self):
        if not self.api.CredDeleteW(self.target,1,0) and ctypes.get_last_error()!=1168:
            raise CredentialError(f'Windows Credential Manager delete failed ({ctypes.get_last_error()})')
