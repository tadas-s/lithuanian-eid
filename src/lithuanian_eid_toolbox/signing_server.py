from flask import Flask, request, jsonify
from flask_cors import CORS
import pkcs11
from pkcs11 import Attribute, Mechanism, ObjectClass
from base64 import b64encode, b64decode
from hashlib import sha256
import os
from asn1crypto.x509 import Certificate

# Server partially implements https://elpako.lt/ software protocol for authentication.

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "https://api.elpako.lt"}})

pkcs11_mod = pkcs11.lib('/usr/lib64/opensc-pkcs11.so')

def certificate_for_authentication(certificate):
    key_usage_digital_signature = False
    extended_key_usage_client_auth = False

    for ext in certificate['tbs_certificate']['extensions']:
        if ext['extn_id'].native == 'key_usage' and 'digital_signature' in ext['extn_value'].native:
            key_usage_digital_signature = True
        if ext['extn_id'].native == 'extended_key_usage' and 'client_auth' in ext['extn_value'].native:
            extended_key_usage_client_auth = True

    return key_usage_digital_signature and extended_key_usage_client_auth

@app.route("/Handshake/Browser", methods=["GET"])
def handshake_browser():
    # This supposed to return current user name, but it's only really
    # relevant to the proprietary software which runs as root + as current user.
    # So in our case - just return a dummy name.
    return "jonas"

# GET /Signing/SelectCertificate?childName=jonas&sessionId=null&store=usb2&purpose=authentication&withLog=false
@app.route("/Signing/SelectCertificate", methods=["GET"])
def signing_select_certificate():
    for token in pkcs11_mod.get_tokens():
        with token.open() as session:
            try:
                certificate_object = next(session.get_objects({
                    Attribute.CLASS: pkcs11.ObjectClass.CERTIFICATE
                }))
            except StopIteration:
                continue

            der = certificate_object.get_attributes([Attribute.VALUE])[Attribute.VALUE]
            certificate = Certificate.load(der)

            if certificate_for_authentication(certificate):
                return jsonify({
                    "certificate": b64encode(der).decode('utf-8'),
                    "name": certificate['tbs_certificate']['subject'].native['common_name'],
                    "issuer": certificate['tbs_certificate']['issuer'].native['organization_name'],
                    "validTo": certificate['tbs_certificate']['validity']['not_after'].native.date().isoformat()
                })

    return jsonify({
        "certificate": None,
        "name": None,
        "issuer": None,
        "exception": "No certificates found",
        "errorCode": "no_certificates_found"
    })

@app.route("/Signing/Sign", methods=["POST"])
def signing_sign():
    request_params = request.get_json()
    certificate_to_use = b64decode(request_params['certificate'])
    data_to_sign = sha256(b64decode(request_params['dtbs'])).digest()
    token_to_use = None

    for token in pkcs11_mod.get_tokens():
        with token.open() as session:
            certificate_object = next(session.get_objects({
                Attribute.CLASS: pkcs11.ObjectClass.CERTIFICATE
            }))

            der = certificate_object.get_attributes([Attribute.VALUE])[Attribute.VALUE]

            if der == certificate_to_use:
                token_to_use = token
                break

    if not token_to_use:
        return jsonify({
            "result": None,
            "exception": None,
            "errorCode": None,
            "log": None
        })

    with token_to_use.open(user_pin=os.getenv('USER_PIN')) as session:
        private_key = session.get_key(object_class=ObjectClass.PRIVATE_KEY)
        signature = private_key.sign(data_to_sign, mechanism=Mechanism.ECDSA)

        return jsonify({
            "result": b64encode(signature).decode('utf-8'),
            "exception": None,
            "errorCode": None,
            "log": None
        })

def run():
    app.run('127.0.0.1', 38888, debug=True, ssl_context=('cert.pem', 'key.pem'))
