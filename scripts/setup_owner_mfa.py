#!/usr/bin/env python3
"""Generate a local TOTP secret for the creator. NEVER commit the output."""
import base64, secrets, urllib.parse

if __name__=='__main__':
    secret=base64.b32encode(secrets.token_bytes(32)).decode('ascii').rstrip('=')
    label=urllib.parse.quote('SKY IA:Propietario')
    uri=f'otpauth://totp/{label}?secret={secret}&issuer=SKY%20IA&algorithm=SHA1&digits=6&period=30'
    print('SKY_OWNER_MFA_SECRET='+secret)
    print('OTP AUTH URI (pegalo solo en tu aplicación autenticadora):')
    print(uri)
    print('GUARDÁ este secreto localmente en .env, jamás en GitHub ni en capturas públicas.')
