from cryptography import x509
import datetime


def cert_load(fname):
    """lê certificado de ficheiro"""
    with open(fname, "rb") as fcert:
        cert = x509.load_pem_x509_certificate(fcert.read())
    return cert


def cert_validtime(cert, now=None):
    """valida que 'now' se encontra no período
    de validade do certificado."""
    if now is None:
        now = datetime.datetime.now()
    if now < cert.not_valid_before or now > cert.not_valid_after:
        raise x509.verification.VerificationError(
            "Certificate is not valid at this time"
        )


def cert_validsubject(cert, attrs=[]):
    """verifica atributos do campo 'subject'. 'attrs'
    é uma lista de pares '(attr,value)' que condiciona
    os valores de 'attr' a 'value'."""
    for attr in attrs:
        if cert.subject.get_attributes_for_oid(attr[0])[0].value != attr[1]:
            raise x509.verification.VerificationError(
                "Certificate subject does not match expected value"
            )


def cert_validexts(cert, policy=[]):
    """valida extensões do certificado.
    'policy' é uma lista de pares '(ext,pred)' onde 'ext' é o OID de uma extensão e 'pred'
    o predicado responsável por verificar o conteúdo dessa extensão."""
    for check in policy:
        ext = cert.extensions.get_extension_for_oid(check[0]).value
        if not check[1](ext):
            raise x509.verification.VerificationError(
                "Certificate extensions does not match expected value"
            )


def valida_cert(cert_name, subject):
    try:
        cert = cert_load(cert_name)
        # obs: pressupõe que a cadeia de certifica só contém 2 níveis
        cert.verify_directly_issued_by(cert_load("MSG_CA.crt"))
        # verificar período de validade...
        cert_validtime(cert)
        # verificar identidade... (e.g.)
        cert_validsubject(cert, [(x509.NameOID.COMMON_NAME, subject)])
        # verificar aplicabilidade... (e.g.)
        # cert_validexts(
        #     cert,
        #     [
        #         (
        #             x509.ExtensionOID.EXTENDED_KEY_USAGE,
        #             lambda e: x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH in e,
        #         )
        #     ],
        # )
    except:
        print("Certificate is invalid!")
        return False

    return True