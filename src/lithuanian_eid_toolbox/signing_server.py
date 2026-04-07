from flask import Flask, request, jsonify
from flask_cors import CORS
import pkcs11
from pkcs11 import Attribute, Mechanism, ObjectClass
from base64 import b64encode, b64decode
from hashlib import sha256
import os

# Server implements https://elpako.lt/ software protocol for signing.

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "https://api.elpako.lt"}})

pkcs11_mod = pkcs11.lib('/usr/lib64/opensc-pkcs11.so')

@app.route("/Handshake/Browser", methods=["GET"])
def handshake_browser():
    # This supposed to return current user name, but it's only really
    # relevant to the proprietary software which runs as root + as current user.
    # So in our case - just return a dummy name.
    return "jonas"

# GET /Signing/SelectCertificate?childName=jonas&sessionId=null&store=usb2&purpose=authentication&withLog=false
@app.route("/Signing/SelectCertificate", methods=["GET"])
def signing_select_certificate():
    token = next(obj for obj in pkcs11_mod.get_tokens() if obj.label.endswith(' (PACE-PIN)'))

    with token.open() as session:
        certificate = list(session.get_objects({
            Attribute.CLASS: pkcs11.ObjectClass.CERTIFICATE
        }))[0]

        attributes = certificate.get_attributes([
            Attribute.LABEL,
            Attribute.VALUE,
            Attribute.SERIAL_NUMBER
        ])

    return jsonify({
        "certificate": b64encode(attributes[Attribute.VALUE]).decode('utf-8'),
        "name": "TADAS SASNAUSKAS",
        "issuer": "MD CA",
        "validTo": "2029-02-18T02:31:39-08:00"
    })

@app.route("/Signing/Sign", methods=["POST"])
def signing_sign():
    token = next(obj for obj in pkcs11_mod.get_tokens() if obj.label.endswith(' (PACE-PIN)'))

    request_params = request.get_json()
    data_to_sign = sha256(b64decode(request_params['dtbs'])).digest()

    with token.open(user_pin=os.getenv('USER_PIN')) as session:
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
