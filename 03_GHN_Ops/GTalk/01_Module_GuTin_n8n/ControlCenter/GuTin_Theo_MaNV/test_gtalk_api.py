import urllib.request
import json

url = "http://localhost:8000/api/send"
payload = {
    "groups": ["Tin nhắn của tôi"],
    "message_plain": "Day la tin nhan test bot gui tu dong (text roi sau hinh).",
    "image_path": r"E:\GHN\AntiGravity\Khứa Hỗ Trợ\clipboard_temp.png",
    "delay": 2.0
}
headers = {'Content-Type': 'application/json'}
req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)

try:
    response = urllib.request.urlopen(req)
    for line in response:
        print(line.decode('utf-8').strip())
except Exception as e:
    print(f"Error: {e}")
