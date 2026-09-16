# STACK TRACE — /api/sched/get INCIDENT

> **Incident ID:** INC-P0-001  
> **Date:** 15/09/2026  

## 1. Mô phỏng Stack Trace (Simulated Stack Trace tại điểm nghẽn Upstash Redis / JSON Decode)
```text
Traceback (most recent call last):
  File "control_center.py", line 1002, in do_GET
    elif p == "/api/sched/get":
  File "control_center.py", line 1053, in do_GET
    _reply(self, 200, action_sched_get())
  File "control_center.py", line 1190, in action_sched_get
    s = _load_sched()
  File "control_center.py", line 1116, in _load_sched
    d = _redis_get("control_center:sched")
  File "control_center.py", line 66, in _redis_get
    r = requests.get(f"{UPSTASH_URL}/get/{key}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=3)
  File "requests/adapters.py", line 516, in send
    raise ReadTimeout(e, request=request)
requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='us1-********.upstash.io', port=443): Read timed out. (read timeout=3)
```
*(Lưu ý: Do `_redis_get` bọc `try...except Exception`, ngoại lệ ReadTimeout được bắt và trả về `None`, nhưng nếu luồng HTTP bị treo đồng thời do nghẽn socket hoặc Reverse Proxy (Render load balancer) timeout 30s, Render sẽ trả về HTTP 502 Bad Gateway).*
