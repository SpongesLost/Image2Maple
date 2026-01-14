import datetime
import hashlib
from random import Random
import requests
import logging
        
def random_str(length=16):
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    return ''.join(Random().choice(chars) for _ in range(length))
    
def generate_app_auth_headers(app_id, app_secret, req_data):
    header = {
        "timestamp": str(int(datetime.datetime.now().timestamp())),
        "random-str": random_str(16),
        "app-id": app_id
    }

    pre_sign_string = ""
    all_keys = list(req_data.keys()) + list(header.keys())
    all_keys.sort()

    for key in all_keys:
        value = header.get(key) if key in header else req_data.get(key)
        if pre_sign_string:
            pre_sign_string += "&"
        pre_sign_string += f"{key}={value}"

    pre_sign_string += f"&secret={app_secret}"
    header["sign"] = hashlib.md5(pre_sign_string.encode()).hexdigest()
    return header

def get_latex(ocr_url, app_data, app_secret, image_bytes: bytes) -> str:
    try:
        files = {'file': ('img.png', image_bytes, 'image/png')}
        data = {}

        headers = generate_app_auth_headers(app_data, app_secret, data)
        r = requests.post(ocr_url, files=files, data=data, headers=headers, timeout=40)
        r.raise_for_status()
        return r.json().get('res', {}).get('latex', '')
    except requests.RequestException as e:
        logging.error("OCR request failed: %s", e)
        return ""