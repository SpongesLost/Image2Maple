from fastapi import FastAPI, File, UploadFile, Request
import os
import datetime
import hashlib
from random import Random
import requests
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

SIMPLETEX_API_URL = 'https://server.simpletex.cn/api/latex_ocr'
SIMPLETEX_APP_ID = os.getenv("SIMPLETEX_APP_ID")
SIMPLETEX_APP_SECRET = os.getenv("SIMPLETEX_APP_SECRET")

@app.get("/")
@limiter.limit("70/minute")
def read_root(request: Request):
    return {"Hello": "World"}

@app.post("/imagetolatex")
@limiter.limit("15/minute")
async def convert_image_to_latex(request: Request, file: UploadFile = File(...)):
    image_bytes = await file.read()
    latex_result = get_latex(image_bytes)
    return {"latex": latex_result}
        
def random_str(length=16):
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    return ''.join(Random().choice(chars) for _ in range(length))
    
def generate_app_auth_headers(req_data):
    header = {
        "timestamp": str(int(datetime.datetime.now().timestamp())),
        "random-str": random_str(16),
        "app-id": SIMPLETEX_APP_ID
    }

    pre_sign_string = ""
    all_keys = list(req_data.keys()) + list(header.keys())
    all_keys.sort()

    for key in all_keys:
        value = header.get(key) if key in header else req_data.get(key)
        if pre_sign_string:
            pre_sign_string += "&"
        pre_sign_string += f"{key}={value}"

    pre_sign_string += f"&secret={SIMPLETEX_APP_SECRET}"
    header["sign"] = hashlib.md5(pre_sign_string.encode()).hexdigest()
    return header

def get_latex(image_bytes: bytes) -> str:
    try:
        files = {'file': ('img.png', image_bytes, 'image/png')}
        data = {}

        headers = generate_app_auth_headers(data)
        r = requests.post(SIMPLETEX_API_URL, files=files, data=data, headers=headers, timeout=40)
        r.raise_for_status()
        return r.json().get('res', {}).get('latex', '')
    except requests.RequestException as e:
        return ""