# Google Auth & RBAC for Control Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay thế GHN SSO v2 bằng Google OAuth2, tích hợp Google Cloud Firestore để lưu trữ danh sách phân quyền (Role-based access control: Owner, Admin, Viewer), audit log, và thêm trang quản trị `/dashboard/admin`.

**Architecture:** 
- `google_auth.py`: Module xử lý Google OAuth2 authorization code flow, verify ID token / userinfo.
- `auth_store.py`: Module kết nối Google Cloud Firestore để CRUD user whitelist, roles (`admin`, `viewer`), và ghi audit log. Cấu hình cứng `khoava2022@gmail.com` là Owner cố định không thể xóa/hạ quyền.
- `control_center.py`: Cập nhật route auth (`/auth/login`, `/auth/callback`, `/auth/me`, `/auth/logout`) và bổ sung route admin (`/dashboard/admin`, `/api/admin/users`).
- Giao diện `/dashboard/admin`: Giao diện HTML quản lý user cho Admin.

**Tech Stack:** Python 3.11, Google Cloud Firestore (`google-cloud-firestore`), requests, standard library `http.server`.

**Spec:** Thiết kế đã chốt qua hội thoại với user (Google login, @ghn.vn auto-viewer, ngoài ghn.vn cần whitelist Firestore, khoava2022@gmail.com là Owner gốc).

## Global Constraints
- `khoava2022@gmail.com` luôn là Owner và không thể bị sửa/hạ/xóa.
- Email `@ghn.vn` mặc định là Viewer nếu chưa có trong DB.
- Email ngoài `@ghn.vn` bị từ chối truy cập (hiển thị thông báo HTML inline) nếu chưa được Admin thêm vào Firestore.
- Mọi thao tác thêm/xóa/đổi quyền phải ghi audit log vào Firestore (`audit_log` collection).
- Không làm ảnh hưởng đến các luồng ingestion, cào phiếu và dispatch GTalk hiện có.

---

### Task 1: Tạo module `google_auth.py`

**Files:**
- Create: `E:/GHN/AntiGravity/Khua_Ho_Tro/03_GHN_Ops/GTalk/01_Module_GuTin_n8n/ControlCenter/google_auth.py`
- Test: `E:/GHN/AntiGravity/Khua_Ho_Tro/03_GHN_Ops/GTalk/01_Module_GuTin_n8n/ControlCenter/tests/test_google_auth.py`

**Interfaces:**
- Consumes: Env vars `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, `SESSION_SECRET`.
- Produces: `build_authorization_url(state, nonce)`, `exchange_code_for_tokens(code)`, `fetch_userinfo(access_token)`, `create_session_token(user_info)`, `verify_session_token(token)`.

- [ ] **Step 1: Viết test cho `google_auth.py`**
- [ ] **Step 2: Viết code `google_auth.py`**
- [ ] **Step 3: Chạy test xác thực thành công**

---

### Task 2: Tạo module `auth_store.py` (Firestore RBAC & Audit)

**Files:**
- Create: `E:/GHN/AntiGravity/Khua_Ho_Tro/03_GHN_Ops/GTalk/01_Module_GuTin_n8n/ControlCenter/auth_store.py`

**Interfaces:**
- Consumes: Google Cloud Firestore credentials / default credentials.
- Produces: `get_user_role(email)`, `list_users()`, `add_or_update_user(email, role, added_by)`, `remove_user(email, removed_by)`.

- [ ] **Step 1: Viết code `auth_store.py` tích hợp Firestore với fallback an toàn khi chưa cấu hình DB**
- [ ] **Step 2: Kiểm tra logic Owner bảo vệ khoava2022@gmail.com**

---

### Task 3: Cập nhật `control_center.py` tích hợp Google Auth & RBAC

**Files:**
- Modify: `E:/GHN/AntiGravity/Khua_Ho_Tro/03_GHN_Ops/GTalk/01_Module_GuTin_n8n/ControlCenter/control_center.py`

- [ ] **Step 1: Thay thế import `sso_oidc` bằng `google_auth` và `auth_store`**
- [ ] **Step 2: Cập nhật luồng `/auth/login`, `/auth/callback`, kiểm tra domain `@ghn.vn` và phân quyền Firestore**
- [ ] **Step 3: Thêm các endpoint API quản trị `/api/admin/users` và route trang admin `/dashboard/admin`**

---

### Task 4: Tạo giao diện trang quản trị `admin.html`

**Files:**
- Create: `E:/GHN/AntiGravity/Khua_Ho_Tro/03_GHN_Ops/GTalk/01_Module_GuTin_n8n/ControlCenter/admin.html`

- [ ] **Step 1: Viết HTML/JS quản lý danh sách user (thêm, sửa role, xóa, xem audit log)**

---

### Task 5: Viết Unit Test và chạy kiểm thử toàn tuyến

**Files:**
- Modify/Create: `E:/GHN/AntiGravity/Khua_Ho_Tro/03_GHN_Ops/GTalk/01_Module_GuTin_n8n/ControlCenter/tests/test_auth_routes.py`

- [ ] **Step 1: Cập nhật test case cho Google Auth & RBAC**
- [ ] **Step 2: Chạy pytest xác nhận toàn bộ test pass**
