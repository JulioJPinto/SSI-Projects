import os
import sys

from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def decrypt(salt, nonce, signature, content, password):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )

    key = kdf.derive(password.encode())
    cipher = Cipher(algorithms.AES(key[:32]), modes.CTR(nonce))
    dec = cipher.decryptor()

    ori = dec.update(content)

    hmac2 = hmac.HMAC(key[32:], hashes.SHA256())
    hmac2.update(content)
    hmac2.verify(signature)

    return ori


def encrypt(content, password):
    (salt, nonce) = (os.urandom(16), os.urandom(16))

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=64,
        salt=salt,
        iterations=480000,
    )

    key = kdf.derive(password.encode())

    cipher = Cipher(algorithms.AES(key[:32]), modes.CTR(nonce))
    enc = cipher.encryptor()

    cipher_text = enc.update(content)
    hmac2 = hmac.HMAC(key[32:], hashes.SHA256())

    hmac2.update(cipher_text)
    signature = hmac2.finalize()

    return salt, nonce, signature, cipher_text

def main(args):
    if len(args) < 2:
        error()
        return

    file_name = args[1]

    password = input()

    if args[0] == 'enc':
        with open(file_name, 'rb') as file_to_encrypt:
            content = file_to_encrypt.read()
            salt, nonce, signature, cipher_text = encrypt(content, password)
        with open(file_name + '.enc', 'wb') as output_file:
            output_file.write(salt)
            output_file.write(nonce)
            output_file.write(signature)
            output_file.write(cipher_text)
    elif args[0] == 'dec':
        with open(file_name, 'rb') as file_to_decrypt:
            salt, nonce, signature, content = file_to_decrypt.read(16), file_to_decrypt.read(16), file_to_decrypt.read(32), file_to_decrypt.read()
        with open(file_name + '.dec', 'wb') as output_file:
            output_file.write(decrypt(salt, nonce, signature, content, password))
    else:
        error()

def error():
    print("Usage:"
          "\n\tpython3 pbenc_chacha20.py enc <fich>"
          "\n\tpython3 pbenc_chacha20.py dec <fich>")
    sys.exit(1)
    

if __name__ == '__main__':
    main(sys.argv[1:])
