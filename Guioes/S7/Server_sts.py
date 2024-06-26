# Código baseado em https://docs.python.org/3.6/library/asyncio-stream.html#tcp-echo-client-using-streams
import asyncio
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography import x509
import validate_cert
import os

conn_cnt = 0
conn_port = 8443
max_msg_size = 9999
p = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF
g = 2
ca_cert = x509.load_pem_x509_certificate(open("MSG_CA.crt", "rb").read())

class ServerWorker(object):
    """ Classe que implementa a funcionalidade do SERVIDOR. """
    def __init__(self, cnt, addr=None):
        """ Construtor da classe. """
        self.id = cnt
        self.addr = addr
        self.msg_cnt = 0
        self.dhprivate_key = dh.DHParameterNumbers(p, g).parameters().generate_private_key()
        self.rsaprivate_key = None
        self.cert = "MSG_SERVER.crt"
        self.shared_key = None
        self.aesgcm = None

        with open("MSG_SERVER.key", "rb") as key_file:
            self.rsaprivate_key = serialization.load_pem_private_key(
                key_file.read(),
                password = b'1234'
            )

    def process(self, msg):
        """ Processa uma mensagem (`bytestring`) enviada pelo CLIENTE.
            Retorna a mensagem a transmitir como resposta (`None` para
            finalizar ligação) """
        self.msg_cnt += 1

        if msg.splitlines()[0] == b'-----BEGIN PUBLIC KEY-----':
            print("Received public DH key.")
            client_dh_pub = serialization.load_pem_public_key(msg)
            # Cria o par de chaves públicas
            dh_pair = mkpair(
                self.dhprivate_key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ),
                client_dh_pub.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
            )
            # Gera a assinatura do par de chaves
            signature = self.rsaprivate_key.sign(
                dh_pair, # Chave pública do servidor
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            pair1 = mkpair(signature, self.cert.encode())
            pair2 = mkpair(
                self.dhprivate_key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo),
                pair1
            )
            print("Sending public key, cert and signature.")
            return pair2
        
        if unpair(msg)[0].splitlines()[0] == b'-----BEGIN PUBLIC KEY-----':

            print("Received public key, cert and signature.")
            
            server_dh_pub = serialization.load_pem_public_key(unpair(msg)[0])

            signature, cert_name = unpair(unpair(msg)[1])
            cert_name = cert_name.decode()

            # Verifica o certificado
            cert = x509.load_pem_x509_certificate(load_cert(cert_name))
            
            if not validate_cert.valida_cert(cert_name, "User 1 (SSI MSG Relay Client 1)"):
                print("Certicate is not valid")
                return -1
            print("Certificate is valid")

            server_rsa_public_key = cert.public_key()

            # Verifica a assinatura
            dh_pair = mkpair(
                server_dh_pub.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ),
                self.dhprivate_key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo)
            )
            
            if not valida_rsa_signature(server_rsa_public_key, signature, dh_pair):
                print("Signature is not valid")
                return -1
            print("Signature is valid")

            # Gera a chave partilhada
            shared_key = self.dhprivate_key.exchange(server_dh_pub)
            self.shared_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b'handshake data',
            ).derive(shared_key)

            # Inicializa o AESGCM
            self.aesgcm = AESGCM(self.shared_key)
            print("AESGCM initialized.")
            
            nonce = os.urandom(12)
            ciphertext = nonce + self.aesgcm.encrypt(nonce, "".encode(), None)
        
            return ciphertext

        if self.aesgcm is None:
            return "".encode()

        nonce = msg[:12]
        ciphertext = msg[12:]
        msg = self.aesgcm.decrypt(nonce, ciphertext, None)

        txt = msg.decode()
        print('%d : %r' % (self.id,txt))

        if not txt:
            return -1
        
        new_msg = txt.upper().encode()

        nonce = os.urandom(12)
        ciphertext = nonce + self.aesgcm.encrypt(nonce, new_msg, None)
        
        return ciphertext if len(ciphertext)>0 else None


#
#
# Funcionalidade Cliente/Servidor
#
# obs: não deverá ser necessário alterar o que se segue
#


async def handle_echo(reader, writer):
    global conn_cnt
    conn_cnt +=1
    addr = writer.get_extra_info('peername')
    srvwrk = ServerWorker(conn_cnt, addr)
    data = await reader.read(max_msg_size)
    while True:
        if not data: continue
        if data[:1]==b'\n': break
        data = srvwrk.process(data)
        if data == -1: break
        writer.write(data)
        await writer.drain()
        data = await reader.read(max_msg_size)
    print("[%d]" % srvwrk.id)
    writer.close()


def run_server():
    loop = asyncio.new_event_loop()
    coro = asyncio.start_server(handle_echo, '127.0.0.1', conn_port)
    server = loop.run_until_complete(coro)
    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    print('  (type ^C to finish)\n')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
    print('\nFINISHED!')

def mkpair(x, y):
    """ produz uma byte-string contendo o tuplo '(x,y)' ('x' e 'y' são byte-strings) """
    len_x = len(x)
    len_x_bytes = len_x.to_bytes(2, 'little')
    return len_x_bytes + x + y

def unpair(xy):
    """ extrai componentes de um par codificado com 'mkpair' """
    len_x = int.from_bytes(xy[:2], 'little')
    x = xy[2:len_x+2]
    y = xy[len_x+2:]
    return x, y

def valida_rsa_signature(rsa_public_key, signature, data):
    try:
        rsa_public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except:
        return False

def load_cert(cert_name):
    with open(cert_name, "rb") as cert_file:
        return cert_file.read()

run_server()
