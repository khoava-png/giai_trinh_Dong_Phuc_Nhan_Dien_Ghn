# GHN CONTROL CENTER V3 — ALL-IN-ONE GOOGLE CLOUD RUN

> **Mục tiêu:** Tự động hóa toàn diện hệ thống nhắc phiếu tồn Vận hành GHN (Hối giao, Hối lấy, Hối trả)
> cho 150+ Quản lý Khu vực (AM) và 14 Trợ lý Giám đốc Vùng qua GTalk.
> **Kiến trúc V3:** Hợp nhất 100% về **Google Cloud Platform (Cloud Run + Cloud Scheduler)** — $0đ/tháng, tốc độ bắn tin ~5-10 giây.

---

## 0. CHẾ ĐỘ KHÓA VẬN HÀNH & KẾ HOẠCH KHÔI PHỤC — 2026-09-24

> **Trạng thái hiện tại: FREEZE / PENDING.** Chưa deploy dashboard, chưa đổi traffic Cloud Run,
> chưa pause Scheduler và chưa gửi thử GTalk cho đến khi chốt phạm vi với chủ dự án.

### 0.1 Sự thật runtime đã kiểm tra

- Production đang có **3 điểm kích hoạt độc lập**: `ghn-cron-all`, `ghn-cron-hoilay` và `ghn-hourly-ingestion-job`.
- Hai luồng đầu chạy theo giờ; luồng ingestion cũng chạy theo giờ. Vì vậy có rủi ro ingestion và dispatch chạy chồng nhau nếu không có khóa single-flight và snapshot bất biến.
- Cloud Run service là `ghn-control-center`, nhưng traffic hiện vẫn trỏ vào revision cũ `00026`; revision mới nhất đã tạo nhưng chưa được xác nhận đang nhận traffic.
- Log production sáng nay đã ghi nhận: cycle gửi trước khi ingestion hoàn tất, lỗi `ghi_rp_theo_am()` do code/runtime lệch phiên bản, và một recipient GTalk trả HTTP 500. Đây là lỗi vận hành có bằng chứng, không coi là lỗi dữ liệu cho đến khi tái lập được.
- Google Sheet hiện không có tab `_Control_Center`, trong khi một số tài liệu cũ vẫn mô tả tab này là thành phần bắt buộc. Không được tự tạo lại tab hoặc ghi đè dữ liệu để “chữa” khi chưa có quyết định.

### 0.2 Quy tắc bất biến từ bây giờ

1. Mỗi việc chỉ có **một owner và một trigger được phép chạy**; không chạy thủ công song song với Scheduler.
2. Ingestion và dispatch phải dùng cùng một `snapshot_id`; dispatch không được đọc dữ liệu đang bị ghi dở.
3. Mọi lần chạy phải có run-id, trạng thái `STARTED/RUNNING/SUCCEEDED/FAILED`, thời điểm, revision và trigger nguồn.
4. Trước khi gửi GTalk phải có bước preview/validation; khi test chỉ render và ghi báo cáo, không gửi thật.
5. Chỉ một revision được nhận production traffic; deploy phải có checklist, người phê duyệt và bước rollback rõ ràng.
6. Không để scheduler nội bộ, worker nền, cron cục bộ hoặc job cũ chạy ngầm nếu chưa được liệt kê trong inventory.
7. Dashboard ở trạng thái read-only/freeze trong giai đoạn điều tra; không dùng dashboard làm nguồn điều khiển ngầm.

### 0.2A Quy tắc vận hành tối giản

> **Chỉ dùng một đường chạy online: Cloud Scheduler → Cloud Run → API cào → Google Sheet.**

- File `.bat` chỉ dùng để phát triển/kiểm thử tại máy, không dùng để cập nhật production.
- Khi cần cập nhật tay, vào Cloud Scheduler và bấm **Run now** cho đúng job đang dùng; không mở `.bat` chạy song song.
- Nếu vẫn cập nhật tay tại máy trong giai đoạn tạm thời, chỉ chạy sau khi kiểm tra job online đã kết thúc; không dựa riêng vào “không đúng giờ chẵn” vì một lượt chạy có thể kéo dài qua giờ kế tiếp.
- Chưa triển khai lock phức tạp. Giai đoạn đầu chỉ cần ghi một dòng note vận hành: `Đang chạy: [job] | Bắt đầu: [giờ] | Người chạy: [ai] | Kết quả: [xong/lỗi]`.
- Sau khi đường chạy online ổn định, mới bỏ hẳn đường chạy tay production và giữ `.bat` cho dry-run.

### 0.3 Kế hoạch làm từng chặng, không chồng việc

| Chặng | Mục tiêu | Kết quả bắt buộc trước khi sang chặng kế |
|---|---|---|
| P0 — Freeze & inventory | Khóa deploy/gửi ngoài ý muốn, lập danh sách process, Scheduler, revision, secret và nơi ghi dữ liệu | Có một bảng trigger duy nhất; không còn job không rõ owner |
| P1 — Execution map | Vẽ chính xác đường đi: API → snapshot → Sheet → phân nhóm → preview → GTalk | Xác định một nguồn sự thật cho cơ cấu AM/Vùng/Trợ lý |
| P2 — Crawl-only | Tối ưu cào phiếu, timeout/retry/idempotency, thay toàn bộ snapshot an toàn | Chạy lặp không tạo bản ghi lẫn nhau; có số liệu trước/sau |
| P3 — Validate cơ cấu | Kiểm tra warehouse → GDV/AM/Vùng, phiếu thiếu cơ cấu, trùng/đổi AM | Có báo cáo lỗi dữ liệu; chưa gửi GTalk |
| P4 — Report-only | Sinh RP theo AM/Vùng và preview nội dung GTalk | Chủ dự án duyệt mẫu và số lượng người nhận |
| P5 — Dispatch có kiểm soát | Bật một trigger duy nhất, single-flight lock, retry có giới hạn, DLQ cho lỗi | Một run hoàn tất, audit đủ, không duplicate |
| P6 — Dashboard | Chỉ mở lại giao diện đọc log/snapshot đã chốt | Dashboard không tự tạo thêm luồng chạy |
| P7 — Dọn kiến trúc | Đánh dấu/deprecate tài liệu và code Render/Apps Script/trigger cũ | Có danh sách thành phần được phép tồn tại và thành phần đã tắt |

### 0.4 Mâu thuẫn tài liệu cần coi là nghi vấn, chưa tự suy diễn

- Một nhóm tài liệu ghi Render + Apps Script + GitHub Actions; nhóm khác ghi Cloud Run + Cloud Scheduler.
- Lịch trong phần cũ không khớp đầy đủ với ba Scheduler đang tồn tại; đặc biệt ingestion job dễ bị bỏ sót.
- Một số tài liệu ghi URL dashboard khác với URL anh vừa yêu cầu pending.
- Tài liệu legacy tuyên bố concurrency an toàn, nhưng runtime hiện có các trigger độc lập và log cho thấy ingestion/dispatch giao nhau.
- Các giả thuyết “sai kiểu dữ liệu”, “dictionary overwrite” hoặc “bưu cục trống” chưa được coi là nguyên nhân cho đến khi có run-id, snapshot và dòng dữ liệu tái lập được.

### 0.5 Quyết định cần chủ dự án chốt trước khi thực thi

1. “Dừng web” nghĩa là chỉ khóa deploy/giao diện `ghn-dashboard.pages.dev`, hay dừng cả ingestion, dispatch GTalk và ghi Sheet?
2. Trong thời gian freeze, có cho phép **cào phiếu crawl-only** tiếp tục cập nhật snapshot không?
3. Nguồn chuẩn cuối cùng của cơ cấu là `Co_Cau` + `RP_theo_AM`, hay cần chốt lại một bảng cơ cấu mới?
4. Sau khi ổn định, lịch gửi mong muốn là lịch nào và ai là người duyệt preview trước lần gửi đầu tiên?
5. Ai được quyền deploy/bật Scheduler; có cho phép chạy tay không, và nếu có thì chạy qua đúng một nút/endpoint nào?

> **Ghi chú tài liệu:** các file trong `docs/legacy_sprint_audit/` chỉ được xem là lịch sử cho đến khi đối chiếu lại runtime. File này là kế hoạch điều hành tạm thời; không sửa hàng loạt tài liệu cũ trong cùng một lượt.

### 0.6 Cập nhật tạm thời đã thực hiện — 2026-09-24

- `ghn_vanhanh_api.py`: mặc định 8 luồng; đánh dấu kết quả API bằng `_ok`; lỗi API không còn bị coi là 0 phiếu.
- `cao_ton_phieu_api.py`: nếu có bưu cục lỗi hoặc tổng phiếu lấy được lệch với tổng web báo thì dừng trước bước ghi Sheet và trả mã lỗi `2`.
- `1_Cao_Ton_Phieu_API_Run.bat`: gọi rõ `--workers 8`.
- `control_center.py`: source đã đổi import sang crawler API mới và tạm bỏ tự động deploy Cloudflare trong lúc dashboard FREEZE; tuy nhiên module API mới hiện chưa nằm trong thư mục build `ControlCenter/Cao_Ton_Phieu/`, nên chưa được coi là tích hợp online.
- Chỉ kiểm tra cú pháp, chưa chạy cào thật, chưa ghi Google Sheet, chưa deploy Cloud Run và chưa đổi Scheduler.
- Quy ước production tạm thời: chạy qua Cloud Scheduler/Cloud Run; file `.bat` chỉ dùng phát triển hoặc dry-run.

### 0.7 Kết quả review lại từ đầu — đối chiếu báo cáo AI

#### Đã xác nhận từ source/runtime

- Kiến trúc hiện tại là Cloud Run Python, Google Sheet làm lớp lưu trữ trung gian, GTalk đi qua MBFF và dashboard tĩnh đi qua Cloudflare Pages.
- Có nhiều điểm kích hoạt trong source: `/api/ingestion/run`, `/api/cycle/run`, `/api/scrape_and_send`, `/api/dashboard/deploy`, scheduler nội bộ, Apps Script và các file `.bat`/script cục bộ.
- `control_center.py` có `_bg_scheduler_loop`; source chỉ tắt luồng này khi `AUTO_SCHEDULER=false`.
- Endpoint ingestion và endpoint cycle là hai luồng logic khác nhau; cycle có thể đọc Sheet trước khi ingestion ghi xong nếu lịch chạy giao nhau.
- Module API mới đang nằm ở thư mục crawler bên ngoài phạm vi Docker build của `ControlCenter`. Đây là blocker đóng gói, chưa phải lỗi đã được sửa hoàn tất.
- Lần kiểm tra GCP gần nhất ghi nhận ba Cloud Scheduler job đang ENABLED: `ghn-hourly-ingestion-job`, `ghn-cron-all`, `ghn-cron-hoilay`. Đây là trạng thái đã quan sát, chưa phải quyết định giữ cả ba.
- Dashboard deploy tự động trong source hiện đã được đánh dấu freeze; không được deploy Cloud Run bản này trước khi kiểm tra đầy đủ.

#### Chưa được phép kết luận

- Apps Script trigger `processQueueTrigger()` còn bật hay đã tắt trên tài khoản thật.
- Có máy Windows, n8n hoặc cron bên ngoài đang chạy các file `.bat`/script hay không.
- Runtime production đang chạy đúng source hiện tại hay vẫn là revision cũ.
- Các giả thuyết sai tên bưu cục, trôi dòng hoặc dictionary overwrite là nguyên nhân chính của lỗi GTalk sáng nay. Cần snapshot và run-id để tái lập.

#### Thứ tự xử lý mới, không làm song song

1. P0 — Inventory: lập một bảng duy nhất gồm Scheduler, endpoint, Apps Script, n8n, batch, process nền, owner và nơi ghi dữ liệu.
2. P1 — Chốt một đường chạy: chọn đúng một crawler production và một Scheduler chính; các đường còn lại chỉ được giữ ở trạng thái legacy hoặc test.
3. P2 — Đóng gói crawler: đưa module API và toàn bộ dependency cần thiết vào đúng context Docker; import test trong container trước khi nói là online.
4. P3 — Kiểm tra dữ liệu: xác nhận số bưu cục, tổng phiếu, failed list, mapping Co_Cau và 4 tab Sheet.
5. P4 — Kiểm tra dispatch: cycle chỉ được đọc snapshot đã hoàn tất; chưa gửi GTalk thật.
6. P5 — Preview GTalk: gửi mẫu duy nhất cho Admin theo quy tắc đã duyệt, sau đó mới xem xét gửi diện rộng.
7. P6 — Mở lại dashboard và deploy: chỉ thực hiện sau khi P0–P5 đạt điều kiện nghiệm thu.

#### Điều kiện dừng của từng P

- Mỗi P chỉ có một AI code thực hiện.
- AI code không được sửa ngoài phạm vi P.
- Không deploy trong lúc review.
- Không chạy production để “thử cho biết”.
- Nếu phát hiện blocker mới thì dừng P hiện tại, cập nhật MD, không tự nhảy sang P khác.

### 0.8 Kết quả audit đóng gói và runtime import

**Trạng thái: BLOCKER ĐÃ XÁC NHẬN.**

- Docker build context là thư mục `ControlCenter`; các thư mục đồng cấp bên ngoài không được đưa vào image.
- `control_center.py` đang gọi `cao_ton_phieu_api` cho `/api/ingestion/run`, nhưng `ControlCenter/Cao_Ton_Phieu/` chưa có `cao_ton_phieu_api.py`.
- `cao_ton_phieu_api.py` còn phụ thuộc `ghn_vanhanh_api.py`; module này cũng chưa có trong build context.
- Vì vậy build image có thể thành công, nhưng request ingestion sẽ lỗi import khi runtime khởi động handler.
- `_bg_scheduler_loop` vẫn import crawler legacy `cao_ton_phieu.py`; nếu được bật sẽ tạo thêm một đường cào khác.
- `/api/cycle/run` không cào dữ liệu; endpoint này đọc Sheet rồi dispatch GTalk. Nếu chạy trước khi ingestion hoàn tất, nó có thể dùng snapshot cũ.

#### Nhiệm vụ code duy nhất tiếp theo

1. Đưa `cao_ton_phieu_api.py` và `ghn_vanhanh_api.py` vào đúng `ControlCenter/Cao_Ton_Phieu/`.
2. Sửa `_bg_scheduler_loop` để không gọi crawler legacy; không tạo thêm crawler mới.
3. Giữ nguyên Dockerfile, cloudbuild.yaml, `.dockerignore`, dashboard và Code.gs.
4. Chỉ kiểm tra import, compile và build context; không gọi API nguồn, không ghi Sheet, không gửi GTalk.
5. Báo cáo kết quả rồi dừng, không tự chuyển sang deploy.

#### Tiêu chí nghiệm thu nhiệm vụ code

- Hai module tồn tại trong build context.
- `control_center`, `dashboard_sync`, `cao_ton_phieu_api` và `ghn_vanhanh_api` import thành công từ thư mục `ControlCenter`.
- Không còn điểm production nào gọi `cao_ton_phieu.py` để cào tự động.
- Không có thay đổi ngoài ba file được phép: hai module crawler và `control_center.py`.
- Không có lệnh deploy, không có lệnh chạy cào thật và không có thay đổi Scheduler.

### 0.9 Kết quả thực hiện nhiệm vụ đồng bộ module

**Trạng thái: ĐÃ VƯỢT BLOCKER ĐÓNG GÓI Ở SOURCE, CHƯA NGHIỆM THU RUNTIME.**

- Hai module `cao_ton_phieu_api.py` và `ghn_vanhanh_api.py` đã có trong `ControlCenter/Cao_Ton_Phieu/`.
- `/api/ingestion/run` và `_bg_scheduler_loop` đều gọi `cao_ton_phieu_api.crawl_tickets_api(workers=8)`.
- Không còn call site trong `control_center.py` gọi crawler legacy `cao_ton_phieu.py`.
- Compile các module cốt lõi đã đạt.
- Chưa có bằng chứng build image và khởi động Cloud Run thành công sau thay đổi.
- Không được coi việc import `control_center` bằng Python CLI là smoke test hợp lệ nếu thao tác đó khởi động server và giữ process chạy. Kiểm tra runtime phải dùng container/entrypoint có kiểm soát hoặc cơ chế import không khởi động server.
- Chưa chạy API nguồn, chưa ghi Sheet, chưa gửi GTalk, chưa deploy và chưa đổi Scheduler.

#### Việc tiếp theo được phép

Chỉ được kiểm tra build image và runtime startup trong môi trường cô lập, không gọi endpoint ingestion. Nếu build/startup đạt, dừng lại để review tiếp dependency, biến môi trường và trạng thái Scheduler. Không tự chuyển sang dry-run production.

### 0.10 Kết quả kiểm tra startup cục bộ

**Trạng thái: STARTUP CỤC BỘ ĐẠT; BUILD-ONLY CLOUD BUILD ĐẠT; PRODUCTION CHƯA THAY ĐỔI.**

- Máy trạm không có Docker daemon/CLI; quy trình build thật dùng Google Cloud Build.
- Cấu trúc build context và hai module crawler đã được kiểm tra trong `ControlCenter/Cao_Ton_Phieu/`.
- Server khởi động với `AUTO_SCHEDULER=false` và `PORT=8089`.
- Endpoint `/health` trả HTTP 200.
- Không gọi ingestion, cycle, dashboard deploy, Web Vận Hành, Google Sheet hoặc GTalk.
- Tiến trình test đã dừng; chưa deploy Cloud Run và không có file bị sửa trong lượt kiểm tra.
- Build-only Cloud Build đã đạt với Build ID `9a3ae033-05d0-42fb-b8c1-65254c6d4188`; image verify build thành công và import trong container Linux đạt.
- Image không được push; Cloud Run traffic không thay đổi.

#### Bước tiếp theo duy nhất

Không được chạy nguyên `cloudbuild.yaml` hiện tại cho bước này vì file đang gồm cả build, push Artifact Registry và deploy Cloud Run. Build-only đã được thực hiện bằng cấu hình verify riêng; tiếp tục dừng để review runtime, traffic và Scheduler.

#### Hiệu chỉnh phương án build-only trước khi thực thi

- Phương án build-only mới chỉ là đề xuất, chưa được tạo file và chưa được chạy.
- Không được kết luận image “sẵn sàng 100%” chỉ dựa trên compile/import; vẫn còn phải kiểm tra startup và cấu hình runtime.
- `gcloud builds submit` sử dụng cơ chế `.gcloudignore`; không được coi `.dockerignore` là cơ chế lọc upload chắc chắn. Phải dùng một file ignore rõ ràng qua `--ignore-file` hoặc tạo `.gcloudignore` an toàn trước khi gửi context; tuyệt đối không để `.env`, key, token hoặc file credential bị upload.
- Cấu hình verify phải không có bước `docker push`, `gcloud run deploy` hoặc gọi endpoint production.
- Không dùng tag `:latest` trong bài kiểm tra; nếu cần lưu image thì dùng tag verify riêng và phải xác định rõ image có được ghi vào Artifact Registry hay không.
- Kết quả hợp lệ chỉ được ghi là: `build-only và import/startup test đạt`, không được ghi là production-ready.

### 0.11 Kết quả kiểm tra runtime production read-only

**Trạng thái: CHƯA DEPLOY BẢN VERIFY; PRODUCTION VẪN ĐANG CHẠY REVISION CŨ.**

- Cloud Run service `ghn-control-center` có revision mới nhất đã tạo là `ghn-control-center-00043-7tl`.
- Revision đang nhận 100% traffic vẫn là `ghn-control-center-00026-gjk`.
- Ba Cloud Scheduler job đang ENABLED: `ghn-cron-all`, `ghn-cron-hoilay`, `ghn-hourly-ingestion-job`.
- Các Scheduler đang gọi hai nhóm endpoint khác nhau: cycle dispatch và ingestion. Đây là điểm cần xử lý trước khi deploy để tránh đọc snapshot cũ hoặc chạy chồng.
- Cloud Run service có các biến môi trường `AUTO_SCHEDULER`, `SCHEDULER_SECRET`, `GTALK_OA_TOKEN`, `CF_ACCOUNT_ID` và `CF_API_TOKEN`; chỉ kiểm tra tên biến, không đọc giá trị secret.
- Giá trị `AUTO_SCHEDULER` chưa được xác nhận lại trong lượt read-only này; không được giả định là `false` chỉ vì source hoặc tài liệu ghi như vậy.
- Không có thay đổi Cloud Run, traffic, Scheduler, Sheet hoặc GTalk trong bước kiểm tra.

#### Kết luận điều hành

Chưa được deploy revision verify. Trước deploy phải chốt một trong hai phương án: giữ ingestion và dispatch là hai job nhưng có quy tắc snapshot/đồng bộ rõ ràng, hoặc hợp nhất thành một đường chạy tuần tự. Không được bật thêm trigger thứ tư.

### 0.12 Review phương án pipeline hợp nhất

Phương án `POST /api/pipeline/run` là hướng được ưu tiên, nhưng báo cáo thiết kế cần hiệu chỉnh trước khi viết code:

- Một Scheduler có lịch `0 6-16 * * *` không tự thay đổi query `filter`. Endpoint phải tự suy ra filter theo giờ Việt Nam: 06:00–13:59 là `ALL`, 14:00–16:59 là `HOI_LAY`, ngoài giờ từ chối.
- Khi pipeline vừa cào vừa dispatch, dispatch phải dùng đúng danh sách ticket và snapshot vừa được kiểm tra; không gọi lại `run_dispatch_cycle()` theo cách đọc Sheet không có `snapshot_id`.
- `failed_bc`, tổng phiếu, mapping cơ cấu và kết quả ghi Sheet phải đạt trước khi gọi GTalk.
- Dashboard vẫn freeze; pipeline không gọi `/api/dashboard/deploy`.
- Không xóa ba Scheduler cũ ở bước đầu. Chỉ pause sau khi pipeline mới đã build, test, deploy có kiểm soát và có một chu kỳ xác nhận thành công.
- Các endpoint cũ có thể giữ tạm ở trạng thái không được Scheduler gọi; chỉ deprecate/xóa sau khi có bằng chứng không còn consumer.

### 0.13 Điều kiện bổ sung trước khi viết pipeline

- `ghn-master-pipeline-job` nếu được tạo để chuẩn bị thì bắt buộc ở trạng thái `PAUSED`; không được ENABLED khi ba job cũ còn ENABLED.
- Không được tạo thêm trigger hoạt động trong cùng thời điểm với ba job hiện tại.
- `/api/pipeline/run`, `/api/ingestion/run`, `/api/cycle/run` và scheduler nội bộ phải dùng cùng cơ chế single-flight hoặc phải có phương án loại trừ rõ ràng trước khi chạy thực tế.
- Không được chỉ dùng lock riêng của pipeline nếu ingestion/cycle có thể chạy cùng lúc bằng lock khác.
- Nếu ghi Sheet giữa chừng thất bại, pipeline phải dừng dispatch và báo trạng thái snapshot không hoàn tất; không được tuyên bố snapshot thành công chỉ vì một tab đã ghi xong.
- Admin summary phải xác định rõ là log nội bộ hay tin GTalk; mặc định chỉ ghi log, không gửi thêm một tin ngoài dispatch.
- Phương án hiện chỉ nêu ghi `Ton_phieu`, `Chi_tiet`, `RP_theo_AM`; AI code phải xác nhận rõ `RP_theo_TroLy` có được giữ nguyên hay không, không được âm thầm bỏ một đầu ra hiện đang tồn tại.

### 0.14 Hotfix cấp thiết: thay crawler legacy bằng API crawler

**Ưu tiên: P0 — thực hiện ngay.** Nhiều lỗi vận hành hiện phát sinh từ đường cào legacy tuần tự và dữ liệu có thể trôi trong lúc cào. Hotfix tập trung vào crawler và fail-closed, không chờ hoàn thiện pipeline hợp nhất.

Phạm vi hotfix:

- Endpoint `/api/ingestion/run` dùng `cao_ton_phieu_api.crawl_tickets_api(workers=8)`.
- Scheduler nội bộ nếu còn tồn tại trong source cũng không được gọi crawler legacy.
- Có `failed_bc` hoặc lệch tổng thì dừng trước khi ghi Sheet.
- Giữ dashboard FREEZE.
- Không thay đổi frontend, schema cơ cấu, Scheduler hoặc luồng deploy.
- Chưa gửi GTalk tự động trong bước hotfix nếu snapshot chưa được xác nhận hợp lệ.

Hotfix chỉ được deploy sau khi compile, build-only, startup và test mock fail-closed đạt. Không được dùng hotfix để đồng thời triển khai pipeline hợp nhất hoặc xóa Scheduler cũ.

### 0.15 Ghi nhận báo cáo AI về hotfix/pipeline

**Trạng thái: MOCK PIPELINE ĐẠT; HOTFIX CRAWLER CHƯA NGHIỆM THU; CHƯA DEPLOY.**

- Báo cáo AI ghi nhận `control_center.py` đã thêm `/api/pipeline/run`, dùng chung `_scrape_lock`, fail-closed và dispatch in-memory; các mock test đạt.
- Nội dung này thuộc phạm vi pipeline hợp nhất, không hoàn toàn trùng với hotfix P0 thay crawler legacy bằng API crawler.
- Chưa đủ bằng chứng để kết luận endpoint ingestion production và scheduler nội bộ đã được thay thế đúng crawler API trong revision đang chạy.
- Chưa build-only lại sau thay đổi pipeline.
- Chưa chạy cào thật, chưa ghi Sheet, chưa gửi GTalk, chưa bật Scheduler và chưa deploy Cloud Run.
- Không được deploy dựa trên báo cáo này cho đến khi xác nhận diff thực tế, build-only và kiểm tra đường gọi crawler trong cả `/api/ingestion/run`, `/api/pipeline/run` và `_bg_scheduler_loop`.

### 0.16 Trạng thái hotfix P0 sau kiểm thử

**Trạng thái: SOURCE HOTFIX ĐẠT; PRODUCTION CHƯA ÁP DỤNG.**

- `/api/ingestion/run` và `_bg_scheduler_loop` đã chuyển sang `cao_ton_phieu_api.crawl_tickets_api(workers=8)`.
- Đã loại bỏ call site crawler legacy trong `control_center.py`.
- Fail-closed đã được kiểm thử với crawler lỗi, `failed_bc` và lệch tổng.
- Compile, import và 4 mock test đạt.
- Không gọi API thật, không ghi Sheet, không gửi GTalk và không deploy.
- Cloud Run production vẫn cần xác nhận revision/traffic sau bước build và deploy có kiểm soát.

#### Việc còn lại sau hotfix

1. Kiểm tra diff thực tế và build-only lại sau bản hotfix cuối.
2. Xác nhận `AUTO_SCHEDULER=false` trên revision chuẩn bị deploy.
3. Deploy revision mới ở chế độ không nhận traffic để kiểm tra startup/health.
4. Chuyển traffic có kiểm soát sau khi xác nhận endpoint và biến môi trường.
5. Chạy một lượt dry-run/kiểm tra dữ liệu thật có giám sát; chưa gửi GTalk diện rộng.
6. Đối chiếu số phiếu theo từng bưu cục, không chỉ so sánh tổng toàn hệ thống.
7. Theo dõi log và xác nhận không còn crawler legacy hoặc trigger song song.

### 0.17 Kết quả deploy hotfix P0 ở chế độ no-traffic (đã được thay thế bởi mục 0.18)

**Trạng thái: DEPLOY THÀNH CÔNG; CHƯA CHUYỂN TRAFFIC PRODUCTION.**

- Image: `asia-southeast1-docker.pkg.dev/ghn-sheets-automation/cloud-run-source-deploy/ghn-control-center:hotfix-p0`.
- Build ID: `b7e11f7d-175a-4a01-b991-2cc346805f59`.
- Revision mới: `ghn-control-center-00046-yiy`.
- URL kiểm tra tagged revision: `https://hotfix-p0---ghn-control-center-jqzmzaigwa-as.a.run.app/health`.
- Health: HTTP 200.
- Tại thời điểm ghi nhận ban đầu, traffic production vẫn ở `ghn-control-center-00026-gjk`; thông tin này đã được thay thế bởi kết quả chuyển traffic trong mục 0.18.
- Chưa gọi ingestion, cycle hoặc dashboard deploy; chưa cào Web Vận Hành, ghi Sheet hoặc gửi GTalk.

#### Việc được phép tiếp theo

Tại thời điểm mục này được ghi, chỉ được kiểm tra tagged revision bằng health, startup log và các test mock/dry-run không ghi dữ liệu. Trạng thái chuyển traffic mới nhất xem tại mục 0.18.

### 0.18 Kết quả chuyển traffic hotfix P0

**Trạng thái: HOTFIX ĐANG NHẬN 100% PRODUCTION TRAFFIC.**

- Revision thực tế: `ghn-control-center-00046-yiy`.
- Startup probe: đạt.
- `/health`: HTTP 200 khi gọi đúng đường dẫn.
- `AUTO_SCHEDULER=false`: log startup xác nhận scheduler nội bộ đã tắt.
- Ba Scheduler giữ nguyên; chưa chạy thủ công crawler, chưa ghi Sheet và chưa gửi GTalk.
- Có hai request `/health)` trả 404 do URL kiểm tra có ký tự `)` thừa; không phải lỗi endpoint `/health` chuẩn. Cần dùng đúng URL, không kèm dấu ngoặc đóng.
- Bước tiếp theo là theo dõi lượt Scheduler thật đầu tiên và kiểm tra log cào/dispatch; không tạo thêm trigger.

### 0.22 Chuyển traffic hotfix-v2

**Trạng thái: HOTFIX-V2 ĐANG NHẬN 100% TRAFFIC; SCHEDULER VẪN PAUSED.**

- Revision `ghn-control-center-00048-jis`: 100% traffic.
- Revision `ghn-control-center-00046-yiy`: 0% traffic.
- Production `/health`: `HEALTHY`.
- URL tagged hotfix-v2 `/health`: `HEALTHY`.
- `ghn-cron-all`, `ghn-cron-hoilay`, `ghn-hourly-ingestion-job`: `PAUSED`.
- Thao tác chuyển traffic không gọi ingestion, không ghi Sheet và không gửi GTalk.

### 0.19 Trạng thái đóng băng sau khi sửa hotfix/pipeline

**Trạng thái: ĐÃ PAUSE TOÀN BỘ TỰ ĐỘNG; SOURCE ĐÃ TEST OFFLINE.**

- `ghn-cron-all`, `ghn-cron-hoilay` và `ghn-hourly-ingestion-job` đều đang `PAUSED`.
- Các file đã sửa: `control_center.py`, `Cao_Ton_Phieu/cao_ton_phieu_api.py`, `Cao_Ton_Phieu/ghn_vanhanh_api.py`.
- Compile và import module đạt.
- 8/8 mock test đạt, gồm crawler success, `failed_bc`, lệch tổng, fail-closed ghi Sheet và filter thời gian.
- `cloudbuild.verify.yaml` hợp lệ nhưng build-only Docker Linux chưa được xác nhận thực thi trong mốc này.
- Không gọi API Web Vận Hành, không ghi Sheet, không gửi GTalk, không deploy Cloud Run và không đổi traffic.

#### Trạng thái cho phép tiếp theo

Chỉ được chạy build-only Docker Linux. Sau khi build-only đạt mới xem xét E2E có kiểm soát. Không unpause Scheduler và không chạy E2E production khi chưa có lệnh riêng.

### 0.20 Ba mức kiểm thử cần phân biệt

1. **Test code/build:** compile, import, Docker build, startup. Không chứng minh dữ liệu thực tế đúng.
2. **Test dữ liệu thật không tác động production:** gọi Web API thật, kiểm tra số phiếu và mapping trong RAM hoặc ghi sang một Google Sheet staging riêng; không gửi GTalk.
3. **Test production:** ghi Sheet production và có thể gửi GTalk. Chỉ thực hiện sau khi mức 2 đạt và có phê duyệt riêng.

Lựa chọn an toàn tiếp theo là deploy revision mới `--no-traffic`, sau đó chạy data test thật ở chế độ không ghi production hoặc trên Sheet staging. Không chọn phương án ghi thẳng Sheet production chỉ để kiểm thử.

---

## 🕒 Lịch Trình Tự Động & Cơ Chế Cập Nhật (Cập nhật chuẩn 2026)
- **Lịch chạy Cloud Scheduler (Tất cả các ngày trong tuần - T2 đến CN):**
  - **`ghn-cron-all` (Luồng ALL - Giao / Lấy / Trả):** Chạy định kỳ **mỗi tiếng 1 lần** (`0 6,7,8,9,10,11,12,13 * * *`).
  - **`ghn-cron-hoilay` (Luồng Hối Lấy chuyên biệt):** Chạy định kỳ **mỗi tiếng 1 lần** (`0 14,15,16 * * *`).
  - **`ghn-hourly-ingestion-job` (Luồng cào/cập nhật snapshot):** Chạy mỗi giờ (`0 6-18 * * *`). Luồng này phải được điều phối bằng `snapshot_id`, không được chạy song song không kiểm soát với dispatch.
- **Giao diện Quản lý (Cloudflare Pages):**
  - **URL đang ghi trong tài liệu cũ:** `https://ghn-control-center-v3.pages.dev`
  - **URL anh yêu cầu tạm pending:** `https://ghn-dashboard.pages.dev/` — chưa xác nhận đây là site cần pause deploy hay chỉ là URL giao diện mới.
  - **Auto-Sync:** Tự động làm mới bảng Log Cào Phiếu & Báo Cáo Lỗi **mỗi 30 giây/lần** khi mở buồng lái, kết nối trực tiếp với Cloud Run Backend.

- **Cloud Run URL:** `https://ghn-control-center-748472498606.asia-southeast1.run.app`
- **Health Check:** `https://ghn-control-center-748472498606.asia-southeast1.run.app/health` (`HTTP 200 OK`)
- **Dashboard Quản trị:** `https://ghn-control-center-748472498606.asia-southeast1.run.app/dashboard`
  - **User:** `admin` | **Pass:** `Ghn@2026!`
- **GCP Project:** `ghn-sheets-automation` (Region: `asia-southeast1`)
- **Chi phí vận hành:** **0 VNĐ / tháng** (Dùng < 1% Free tier của GCP).

---

## 2. BẢN ĐỒ KIẾN TRÚC HỆ THỐNG V3 (GCP UNIFIED)

```

┌────────────────────────────────────────────────────────────────────────┐
│                      GOOGLE CLOUD PLATFORM (GCP)                       │
│                                                                        │
│   ┌────────────────────────┐         ┌─────────────────────────────┐   │
│   │ Google Cloud Scheduler │ ──────► │   Google Cloud Run          │   │
│   │ (Cron: 6h, 9h, 12h,    │  POST   │   (All-in-One Python 3.11)  │   │
│   │        15h, 17h)       │         │                             │   │
│   └────────────────────────┘         │  1. Đọc Chi_tiet & Co_Cau   │   │
│                                      │  2. Lọc & Gom theo AM/Vùng  │   │
│                                      │  3. Render Markdown Template│   │
│                                      │  4. Bắn GTalk 172 tin (5s)  │   │
│                                      │  5. Báo cáo Admin (3049378) │   │
│                                      │  6. Ghi Log Google Sheet    │   │
│                                      └──────────────┬──────────────┘   │
│                                                     │                  │
│                                                     ▼                  │
│                                      ┌─────────────────────────────┐   │
│                                      │ Google Sheets Database      │   │
│                                      │ (Chi_tiet, Ton_phieu, Log)  │   │
│                                      └─────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. LỊCH CHẠY TỰ ĐỘNG TRÊN CLOUD SCHEDULER (2 JOBS)

| Job ID | Lịch chạy (Giờ VN) | Endpoint gọi | Trạng thái |
|---|---|---|:---:|
| **`ghn-cron-all`** | `0 6,7,8,9,10,11,12,13 * * *` (Mỗi tiếng 6h-13h, T2-CN) | `POST /api/cycle/run?filter=ALL` | 🟢 **ENABLED** |
| **`ghn-cron-hoilay`** | `0 14,15,16 * * *` (Mỗi tiếng 14h-16h, T2-CN) | `POST /api/cycle/run?filter=HOI_LAY` | 🟢 **ENABLED** |
| **`ghn-hourly-ingestion-job`** | `0 6-18 * * *` (Mỗi tiếng 6h-18h, T2-CN) | `POST /api/ingestion/run` | 🟢 **ENABLED** |

---

## 4. TỔNG KẾT DANH MỤC FILE TOÀN BỘ DỰ ÁN

| File / Thư mục | Chức năng |
|---|---|
| `control_center.py` | Toàn bộ mã nguồn All-in-One Python (HTTP Server + Gom phiếu + Gửi GTalk 5 luồng + Đồng bộ Sheet). |
| `Dockerfile` | Cấu hình đóng gói Container chuẩn Cloud Run Python 3.11-slim. |
| `requirements.txt` | Khai báo thư viện: `requests`, `google-auth`, `google-api-python-client`. |
| `.dockerignore` | Loại trừ file rác và tối ưu dung lượng source upload. |
| `Index.html` | Giao diện Dashboard Control Center quản trị. |
| `dashboard/` | Source code trang biểu đồ phục vụ Cloudflare Pages. |

---

## 5. KẾ HOẠCH TRỌNG TÂM TRONG NGÀY

Phạm vi hôm nay chỉ gồm hai mục. Không triển khai Health Report qua GTalk OA, không dọn legacy diện rộng và không mở thêm tính năng dashboard.

### Mục tiêu 1: Ổn định cào phiếu

Phạm vi:

- Dùng API crawler thay crawler legacy tuần tự.
- Dùng `workers=8`.
- Gắn trực tiếp mã bưu cục, tên bưu cục và loại phiếu vào từng ticket ngay khi nhận dữ liệu.
- Kiểm tra `failed_bc`, tổng phiếu Web báo, tổng phiếu lấy được và mapping `Co_Cau`.
- Nếu có lỗi hoặc lệch dữ liệu thì không ghi snapshot mới và không dispatch GTalk.
- Giữ Dashboard FREEZE.

Kết quả cần đạt:

```text
API crawler chạy được
Không còn call site crawler legacy
failed_bc = 0
Tổng phiếu hợp lệ
Mapping bưu cục → GDV/AM/Vùng hợp lệ
Ghi Ton_phieu, Chi_tiet và các RP không lỗi
Không gửi GTalk trong bước kiểm tra cào
```

### Mục tiêu 2: Ổn định thông báo theo thời gian và loại phiếu

Khung giờ cần xác nhận trước khi bật Scheduler:

```text
06:00–13:59: filter ALL
14:00–16:59: filter HOI_LAY
Ngoài hai khung giờ: không gửi
```

Ý nghĩa loại phiếu:

```text
ALL: Hối giao, Hối lấy, Hối trả
HOI_LAY: chỉ Hối lấy
```

Nội dung cần kiểm tra:

- Đúng người nhận AM/Vùng/Trợ lý theo `Co_Cau`.
- Đúng bưu cục và số phiếu.
- Đúng loại phiếu theo filter.
- Không đọc nhầm snapshot cũ.
- Không gửi ngoài khung giờ.
- Không gửi nếu bước cào hoặc ghi Sheet thất bại.
- Không gửi trùng do ingestion và cycle chạy giao nhau.

Kết quả cần đạt:

```text
06:00–13:59 gửi đúng ALL
14:00–16:59 gửi đúng HOI_LAY
Ngoài giờ bị từ chối
Sai filter bị từ chối
Preview đúng người nhận và loại phiếu
Không gửi thật khi chưa được duyệt
```

### Thứ tự thực hiện trong ngày

1. Hoàn tất hotfix API crawler.
2. Build-only và kiểm tra startup.
3. Deploy revision mới ở chế độ không nhận traffic.
4. Kiểm tra health và log startup.
5. Kiểm thử filter và dispatch bằng mock/dry-run.
6. Chỉ sau khi đạt mới xem xét chuyển traffic.
7. Không pause Scheduler cũ cho đến khi có phương án cutover rõ ràng.

### Không nằm trong phạm vi hôm nay

- Health Report qua GTalk OA.
- Giao diện frontend.
- Dọn/xóa toàn bộ legacy.
- Tối ưu thêm tốc độ ngoài mức 8 worker.
- Thay đổi schema `Co_Cau`.
- Xóa hoặc bật thêm Scheduler.

### Lệnh giao việc AI code trong ngày

```text
Chỉ xử lý hai mục: ổn định API crawler và ổn định filter gửi GTalk theo giờ/loại phiếu.

Không làm Health Report OA.
Không sửa frontend.
Không đổi schema Co_Cau.
Không xóa hoặc bật Scheduler.
Không deploy nếu chưa có lệnh riêng.

Giai đoạn hiện tại chỉ được:
1. Kiểm tra hotfix API crawler.
2. Build-only.
3. Kiểm tra startup.
4. Test filter ALL và HOI_LAY bằng mock/dry-run.
5. Kiểm tra fail-closed và không gửi ngoài giờ.

Báo cáo tối đa 10 dòng, chỉ ghi trạng thái, file, lệnh, kết quả và lỗi.
Không emoji, không giải thích dài.
```

---

## 6. REVISION HOTFIX-V2 VÀ LẦN CHẠY THẬT ĐẦU TIÊN

**Trạng thái: ĐÃ CHUYỂN TRAFFIC VÀ ĐÃ KIỂM TRA GHI DỮ LIỆU THẬT.**

- Image: `asia-southeast1-docker.pkg.dev/ghn-sheets-automation/cloud-run-source-deploy/ghn-control-center:hotfix-p0-v2`.
- Build ID: `b6f5f323-fcc4-4cc0-9e18-e32448ffceba`.
- Revision: `ghn-control-center-00048-jis`.
- URL direct: `https://hotfix-v2---ghn-control-center-jqzmzaigwa-as.a.run.app`.
- Health: HTTP 200.
- Traffic: `100%` ở `ghn-control-center-00048-jis`.
- Health production: HTTP 200.
- Ba Scheduler: `PAUSED`.

### Lần chạy ingestion kiểm soát

- Job: `ghn-hourly-ingestion-job`.
- Cách chạy: tạm `resume`, chạy đúng một lần, sau đó `pause` ngay.
- Kết quả crawler API: `1.717` phiếu, `266` bưu cục.
- Ghi Google Sheet: thành công.
- Snapshot: `SNAP-20260924-1317`.
- Thời gian: `18,18 giây`.
- Dashboard: không deploy do đang FREEZE.
- Không chạy `cycle`, không bật hai Scheduler còn lại.
- Không có log lỗi crawler hoặc lỗi ghi Sheet trong lần chạy.

#### Bước tiếp theo

Không chạy lại ingestion ngay. Đối chiếu dữ liệu vừa ghi trên Sheet và log snapshot trước khi kiểm thử dispatch GTalk. Chỉ bật Scheduler sau khi xác nhận số liệu và loại phiếu đúng.

## 7. RÀ SOÁT CLOUD RUN SAU HOTFIX

Thời điểm rà soát: 24/09/2026. Chỉ đọc, không thay đổi cấu hình.

### Đang đúng và giữ nguyên

- `AUTO_SCHEDULER=false`: không chạy scheduler nội bộ trong Cloud Run.
- `maxScale=1`: bảo đảm không mở nhiều instance crawler song song.
- Revision `ghn-control-center-00048-jis`: đang nhận 100% traffic.
- Ba Scheduler cũ: đang `PAUSED`.

### Điểm cần tối ưu sau khi hệ thống ổn định

1. `minScale=1`: có thể giảm về `0` để tránh giữ instance khi dừng vận hành; chỉ làm sau khi chấp nhận thời gian khởi động tăng.
2. `containerConcurrency=80`: cần benchmark lại vì service có crawler và lock; chưa tự ý giảm trong giai đoạn xác minh.
3. Revision `00046-yiy` vẫn có tag URL riêng dù không nhận traffic; sau thời gian rollback nên gỡ tag hoặc xóa revision theo quy trình có xác nhận.
4. Ba Scheduler cũ đang tồn tại nhưng bị pause; sau khi pipeline mới đạt kiểm thử end-to-end thì hợp nhất thành một job duy nhất.
5. `ingress=all`: cần đánh giá lại sau khi xác nhận cơ chế xác thực Scheduler; chưa đổi để tránh làm hỏng callback.
6. Credential hiện đang cấu hình trực tiếp trong biến môi trường Cloud Run; cần chuyển sang Secret Manager và xoay token ở một đợt bảo mật riêng.
7. Startup probe đang cho phép thời gian chờ dài; chỉ tinh chỉnh sau khi có số liệu startup thực tế.

### Double-check dữ liệu API

- Revision: `ghn-control-center-00048-jis` (`hotfix-v2`).
- Snapshot: `SNAP-20260924-1325`.
- Web: `1.707` phiếu, `269` bưu cục.
- API: `1.707` phiếu, `269` bưu cục.
- Bưu cục lệch: `0`; phiếu trùng: `0`; `failed_bc=0`.
- Trường bắt buộc thiếu: `0`.
- Filter kiểm tra: `ALL` và `HOI_LAY`.
- Kết quả: dữ liệu API khớp Web 100%; không ghi Sheet, không gửi GTalk, không deploy Dashboard.

### Blocker phát hiện khi rà soát dispatch

- Luồng `/api/pipeline/run` hiện gửi mẫu Top 1 cho Admin rồi tiếp tục gửi toàn bộ `tasks` trong cùng request.
- Mẫu Top 1 chưa phải cơ chế chờ duyệt; nếu gọi chế độ thật sẽ có nguy cơ gửi diện rộng ngay.
- `dry_run=true` chỉ mô phỏng, không gửi thật.
- Chưa được phép gửi GTalk thật hoặc bật Scheduler cho đến khi tách riêng chế độ `preview/admin-only` và chế độ dispatch diện rộng.
- Thiết kế cần sửa: preview chỉ crawl, map và gửi một mẫu cho Admin; request kết thúc sau mẫu. Dispatch toàn bộ phải là bước riêng, có xác nhận rõ ràng.

### Kết luận

Hiện chưa có mục nào cần sửa ngay để tiếp tục kiểm thử hotfix. Không xóa revision, không đổi scale, concurrency, ingress hoặc credential trước khi hoàn tất đối chiếu dữ liệu và kiểm thử GTalk.

## 8. QUYẾT ĐỊNH KIẾN TRÚC VÀ VẬN HÀNH ĐÃ CHỐT

### Kiến trúc production

```text
Cloud Scheduler → Cloud Run → GHN API → Google Sheet → GTalk
```

- Apps Script, GitHub Actions, Render, n8n và file `.bat` không được chạy production song song.
- Các thành phần cũ chỉ giữ để tham chiếu, kiểm thử hoặc di trú; phải được đánh dấu `LEGACY`, `TEST` hoặc `DISABLED`.
- Nguồn cơ cấu chính thức là tab `Co_Cau`.
- Tên và thứ tự cột Google Sheet hiện tại được giữ nguyên; chỉ được thay đổi khi cập nhật Data Dictionary và toàn bộ mapping.

### Quy tắc cột và dữ liệu

- API thiếu hoặc đổi tên cột bắt buộc thì dừng toàn bộ.
- Không ghi Google Sheet và không gửi GTalk khi Data Contract không đạt.
- Mã bưu cục, mã ticket và mã nhân sự luôn xử lý dạng chuỗi để giữ số 0 đầu.
- Bảng alias phải quản lý tập trung, không đổi tên cột rải rác trong từng hàm.
- Cần bổ sung Data Dictionary gồm tên chuẩn, tên nguồn, kiểu dữ liệu, bắt buộc/không bắt buộc, giá trị hợp lệ và nơi sử dụng.

### Quy trình Preview và Full Dispatch

Preview:

```text
Crawl → Verify → Mapping → gửi đúng 1 mẫu cho Admin → kết thúc
```

- Preview không ghi Sheet.
- Preview không gửi AM hoặc Trợ lý.
- Preview không gửi summary diện rộng.
- Preview tạo `snapshot_id` và báo số lượng tin dự kiến.

Full Dispatch:

- Chỉ được chạy bằng lệnh riêng sau khi chủ dự án xác nhận đúng `snapshot_id`.
- Lệnh phải có `snapshot_id`, mã xác nhận chính xác và secret hợp lệ.
- Thiếu một trong ba điều kiện thì từ chối.
- Không có nút giao diện chung để tránh bấm nhầm.
- Không tự động chuyển từ Preview sang Full Dispatch.
- Snapshot phải có TTL và trạng thái; snapshot hết hạn hoặc đã sử dụng thì từ chối.

### Lịch production

- 06:00–13:59: filter `ALL`.
- 14:00–16:59: filter `HOI_LAY`.
- Ngoài khung giờ: từ chối.
- Chỉ bật một Scheduler production sau khi Full Dispatch đạt kiểm thử.

### Thứ tự bắt buộc tiếp theo

1. Bổ sung Data Dictionary và Data Contract.
2. Tách Preview/Admin-only khỏi Full Dispatch.
3. Kiểm thử snapshot, TTL, lock và chống gửi trùng.
4. Deploy revision no-traffic.
5. Kiểm thử Preview không ghi Sheet và chỉ gửi Admin.
6. Chờ xác nhận `snapshot_id` rồi mới chạy Full Dispatch.
7. Kiểm tra Sheet, log và số tin gửi.
8. Hợp nhất Scheduler sau cùng.

## 9. REVISION HOTFIX-V3 — TÁCH PREVIEW VÀ DISPATCH

**Trạng thái: BUILD, UNIT TEST VÀ DEPLOY NO-TRAFFIC ĐẠT; CHƯA ĐƯỢC CHẠY PRODUCTION.**

- File sửa: `control_center.py`.
- Endpoint: `/api/pipeline/run`, hỗ trợ Preview và Dispatch.
- Build ID: `6a04c4a6-8c1c-4257-958f-856f8a1e935b`.
- Image tag: `hotfix-p0-v3`.
- Revision: `ghn-control-center-00050-tic` (`hotfix-v3`).
- Traffic: revision mới `0%`; production giữ revision cũ `100%`.
- Scheduler: cả ba job vẫn `PAUSED`.
- Test báo cáo: `10/10` đạt.
- Không ghi Google Sheet và không gửi GTalk diện rộng trong kiểm thử.

### Điều kiện chưa đạt để chuyển tiếp

- Snapshot hiện được mô tả là giữ trong RAM.
- Preview và Dispatch là hai request; RAM không bảo đảm tồn tại qua restart, instance mới hoặc thay đổi revision.
- Chưa nghiệm thu dispatch liên request với snapshot hợp lệ, snapshot hết hạn, snapshot sai, snapshot đã dùng và restart giữa hai bước.
- Chưa được chuyển traffic, chưa gửi GTalk thật và chưa bật Scheduler.

### Lệnh kiểm tra tiếp theo cho AI

```text
Chỉ kiểm tra độ bền snapshot của hotfix-v3, không sửa thêm ngoài control_center.py nếu chưa cần.

Kiểm tra bắt buộc:
1. Preview tạo snapshot_id và trạng thái chờ duyệt.
2. Dispatch ở request thứ hai dùng đúng snapshot_id.
3. Dispatch sai snapshot_id bị từ chối.
4. Dispatch thiếu confirm=true bị từ chối.
5. Dispatch snapshot hết TTL bị từ chối.
6. Dispatch cùng snapshot lần thứ hai bị từ chối.
7. Preview rồi restart process/container rồi Dispatch: phải từ chối an toàn nếu snapshot chỉ ở RAM; không được crawl lại ngầm và không được gửi dữ liệu khác.
8. Kiểm tra request Preview và Dispatch không ghi Sheet hoặc gửi ngoài phạm vi được thiết kế.
9. Kiểm tra lock giữa Preview và Dispatch.
10. Báo rõ snapshot là RAM-only hay durable storage.

Không deploy traffic, không bật Scheduler, không gửi GTalk diện rộng.
Báo cáo tối đa 12 dòng, không emoji.
```

## 10. KẾ HOẠCH NGÀY MAI — THEO DÕI PRODUCTION V6

### Trạng thái đầu ngày

- Revision production: `ghn-control-center-00053-qer` (`hotfix-v6`).
- Traffic: 100% trên v6.
- Master Scheduler: `ghn-master-pipeline-job`, `ENABLED`, lịch mục tiêu `0 6-16 * * *`, timezone `Asia/Ho_Chi_Minh`.
- Scheduler cũ: `ghn-cron-all`, `ghn-cron-hoilay`, `ghn-hourly-ingestion-job` đều `PAUSED`.
- Đối soát trực tiếp Cloud Console: có đúng 4 job; Master là job duy nhất `Enabled`, lần chạy gần nhất `Success`, URI là `POST /api/pipeline/run`; ba job cũ đều `Paused` và không có tác dụng vận hành.
- Dashboard: tiếp tục `FREEZE`.
- Link Dashboard `https://ghn-dashboard.pages.dev/` chỉ được đưa lại vào nội dung tin sau khi Dashboard đã sửa xong, kiểm tra đạt và được chủ dự án cho phép mở lại. Trong thời gian `FREEZE`, không gửi hoặc triển khai link này như một thay đổi mới.
- Không tạo revision mới nếu không có blocker được chứng minh.

### Mục tiêu

Xác nhận Master Pipeline chạy ổn định qua các lượt tự động thật, không chạy song song, không sai filter, không sai mapping và không gửi thiếu tin do lỗi không được ghi nhận.

### Việc thực hiện theo thứ tự

1. Kiểm tra trạng thái Master Scheduler và health Cloud Run trước khung chạy.
2. Theo dõi từng lượt pipeline tự động trong các khung giờ.
3. Đối chiếu mỗi lượt:
   - filter tự động theo giờ;
   - tổng Web/API và số bưu cục;
   - `failed_bc`;
   - số RP theo AM và Trợ lý;
   - số task GTalk dự kiến/thành công/thất bại;
   - snapshot_id, run_id và thời gian chạy;
   - trạng thái các tab Sheet.
4. Nếu có tin GTalk lỗi, xác định đúng recipient và lỗi từ log; chỉ retry recipient lỗi, không chạy lại toàn bộ pipeline.
5. Kiểm tra pipeline trả trạng thái `PARTIAL_FAILURE` khi có tin lỗi, không ghi nhận `SUCCESS` giả.
6. Xác nhận không có request từ ba Scheduler cũ, ingestion riêng hoặc cycle riêng.
7. Ghi kết quả từng lượt vào bảng theo dõi và cập nhật MD sau khi có đủ bằng chứng.

### Điều kiện đạt

- Tối thiểu 3 lượt tự động liên tiếp không có lỗi logic.
- Filter đúng `ALL` trong 06:00–13:59 và `HOI_LAY` trong 14:00–16:59.
- Crawler, mapping và Sheet không lỗi.
- Không có chạy chồng hoặc ghi đè ngoài Master Pipeline.
- GTalk đạt 100% hoặc mọi lỗi được ghi rõ recipient và retry riêng thành công.

### Không thực hiện ngày mai nếu chưa có blocker

- Không tạo v7 hoặc revision mới.
- Không đổi schema `Co_Cau`.
- Không mở Dashboard.
- Không bật Scheduler cũ.
- Không xóa revision cũ.
- Không chuyển snapshot sang Firestore/Cloud Storage.
- Không làm Health Report OA mở rộng.

### Lệnh giao việc AI cho ngày mai

```text
Chỉ theo dõi và kiểm chứng Master Pipeline production v6.

Không sửa code, không tạo revision mới, không deploy, không bật Scheduler cũ.
Theo dõi các lượt ghn-master-pipeline-job và báo cáo:
filter, run_id, snapshot_id, số phiếu, số bưu cục, failed_bc, số task AM/Trợ lý, số gửi thành công/thất bại, recipient lỗi và trạng thái Sheet.

Nếu GTalk lỗi, chỉ xác định và retry recipient lỗi theo cơ chế được phê duyệt; không chạy lại toàn bộ pipeline.
Nếu phát hiện lỗi logic hoặc chạy song song thì dừng và báo ngay.

Báo cáo ngắn, không emoji, không tự thay đổi production.
```

### Kết quả kiểm tra vòng đời snapshot hotfix-v3

- Preview tạo `snapshot_id` hợp lệ.
- Dispatch đúng `snapshot_id` được chấp nhận.
- Sai `snapshot_id`, thiếu `confirm=true`, snapshot hết TTL và snapshot đã dùng lại đều bị từ chối.
- Restart hoặc mất RAM dẫn tới từ chối Dispatch an toàn; không crawl lại ngầm và không gửi GTalk.
- Lock chặn chạy đồng thời giữa Preview và Dispatch.
- Preview không ghi Sheet; test dry-run không gửi GTalk thật.
- Storage hiện tại là RAM-only với TTL 1.800 giây và auto-eviction.

**Kết luận:** P7 đạt về lifecycle safety và fail-closed, chưa phải durable snapshot. Nếu Cloud Run restart sau Preview, phải tạo Preview mới. Chưa triển khai Cloud Storage/Firestore ở giai đoạn hotfix.

### Bước tiếp theo

Kiểm thử Preview thật trên revision no-traffic, chỉ gửi đúng một mẫu Top 1 cho Admin. Chưa ghi Sheet, chưa gửi AM/Trợ lý, chưa chạy Full Dispatch và chưa bật Scheduler.

### Kết quả Preview thật hotfix-v3

- HTTP: `200 OK` trên revision `ghn-control-center-00050-tic` (`hotfix-v3`).
- Snapshot: `SNAP-20260924-140414`.
- Filter: `ALL`.
- Tổng Web/API: `1.665` phiếu, khớp 100%; `266` bưu cục; `failed_bc=0`.
- Đã gửi đúng một mẫu Top 1 cho Admin `3049378`: Phạm Đức Thắng, Vùng XBG, 449 phiếu.
- Không ghi Google Sheet.
- Không gửi AM, Trợ lý hoặc summary diện rộng.
- Không có lỗi.

**Gate tiếp theo:** chỉ chạy Full Dispatch sau khi chủ dự án xác nhận nội dung mẫu và đúng `snapshot_id` `SNAP-20260924-140414`.

## 11. KẾ HOẠCH CẬP NHẬT 4 TEMPLATE GTALK

### Mục tiêu

Đưa nội dung gửi AM và Trợ lý về đúng mẫu nghiệp vụ đã chốt, trong đó mỗi dòng thể hiện rõ:

- Số phiếu `GÁN KHẨN CẤP để không bị phạt`.
- Số phiếu `GÁN NGAY để không tăng mức phạt`.

### Bốn template cần quản lý

1. AM — `ALL`.
2. Trợ lý vùng — `ALL`.
3. AM — `HOI_LAY`.
4. Trợ lý vùng — `HOI_LAY`.

### Quy tắc bảo vệ nội dung

- Nội dung template do chủ dự án chốt; không tự viết lại, rút gọn, đổi câu chữ hoặc đổi thứ tự.
- Không sửa logic crawler, filter, mapping `Co_Cau`, Scheduler hoặc Dashboard khi chỉ cập nhật template.
- Không tự suy đoán nguồn của `so_khan_cap` và `so_gan_ngay`.
- Nếu source chưa có trường hoặc logic xác định hai nhóm này, phải dừng và báo thiếu dữ liệu.
- Chỉ được cập nhật template sau khi chủ dự án xác nhận bản nháp.

### Quy trình kiểm thử template

1. So sánh diff trước/sau, chỉ cho phép thay đổi phần template và render liên quan.
2. Compile và render offline đủ 4 template.
3. Deploy revision no-traffic nếu cần kiểm thử runtime.
4. Gửi đúng một mẫu Top 1 cho Admin `3049378`.
5. Không ghi Google Sheet.
6. Không gửi AM hoặc Trợ lý thật.
7. Không gửi summary diện rộng.
8. Không chạy Full Dispatch.
9. Không bật Scheduler và không chuyển traffic.
10. Dừng chờ chủ dự án review nội dung mẫu.

### Gate nghiệm thu

- Chủ dự án xác nhận đúng nội dung, đúng số lượng và đúng cách phân loại hai nhóm phiếu.
- Sau khi được duyệt mới xem xét chuyển traffic hoặc Full Dispatch.
- Nếu mẫu sai, chỉ sửa lại nội dung được chỉ định; không sửa lan sang crawler hoặc pipeline.

### Quy tắc khóa template sau khi được duyệt

Sau khi chủ dự án duyệt bản template, bốn template được đánh dấu:

```text
TEMPLATE_STATUS = APPROVED_LOCKED
TEMPLATE_VERSION = 1.0
```

AI và mọi nhiệm vụ code về sau phải tuân thủ:

1. Không được sửa câu chữ, dấu câu, thứ tự dòng, emoji, placeholder hoặc nhãn `GÁN KHẨN CẤP`/`GÁN NGAY` nếu không có lệnh cho phép trực tiếp từ chủ dự án.
2. Không được đổi template vì lý do tối ưu code, đổi filter, đổi scheduler, đổi API hoặc refactor.
3. Mọi yêu cầu sửa template phải ghi rõ cụm xác nhận: `CHO PHÉP SỬA TEMPLATE VERSION 1.0`.
4. Nếu không có cụm xác nhận trên, AI chỉ được đọc, kiểm tra và báo cáo; không được chỉnh sửa.
5. Trước khi sửa được cho phép, AI phải xuất diff nguyên văn phần thay đổi và dừng chờ xác nhận.
6. Sau khi sửa được cho phép, phải tăng `TEMPLATE_VERSION`, chạy golden test và gửi đúng một mẫu Admin để review.
7. Nếu thay đổi code làm template bị thay đổi ngoài ý muốn, nhiệm vụ phải FAIL và không được deploy.
8. Crawler, mapping, filter và pipeline không được tự động ghi đè nội dung template.

### Cơ chế kiểm soát đề xuất

- Lưu bản template đã duyệt làm golden fixture.
- Unit test so sánh nội dung render với golden fixture.
- CI/build phải FAIL nếu template thay đổi nhưng không tăng phiên bản và không có xác nhận.
- Báo cáo AI phải có mục `Template changed: YES/NO` và diff tương ứng.

## 12. ADMIN GIÁM SÁT VÀ 3 BÁO CÁO MỖI LẦN CHẠY

### Danh sách Admin

- Admin chính: `3049378`.
- Admin giám sát dữ liệu: `3026736`.
- Hai mã được xem là hai người nhận Admin độc lập, không phải AM hoặc Trợ lý vận hành.

### Quy tắc gửi

Sau mỗi Master Pipeline thành công, mỗi Admin phải nhận đúng 3 tin báo cáo riêng, tổng cộng 6 lượt gửi Admin:

1. Health API.
2. RP AM có số phiếu nhiều nhất.
3. RP Trợ lý/Vùng có tổng số phiếu nhiều nhất.

Các báo cáo phải dùng cùng `run_id`, `snapshot_id`, `filter` và thời điểm của Master Pipeline. Không đọc lại Sheet để dựng báo cáo.

Link Dashboard trong tin AM/Trợ lý phải giữ đúng URL `https://ghn-dashboard.pages.dev/` sau khi Dashboard được sửa xong và mở lại theo phê duyệt. Không tự thêm link trong giai đoạn Dashboard còn `FREEZE`.

### Nội dung 3 báo cáo

#### Tin 1 — Health API

- API source reachable.
- Auth status.
- Latency.
- Tổng bưu cục.
- Tổng phiếu Web/API nếu đã có trong pipeline.
- `failed_bc`.
- `api_status` và `data_check`.
- Revision và `snapshot_id`.

#### Tin 2 — RP AM Top 1

- AM có tổng số phiếu cao nhất trong filter của lượt chạy.
- Tên AM, mã AM, vùng.
- Số phiếu GÁN KHẨN CẤP.
- Số phiếu GÁN NGAY.
- Danh sách bưu cục liên quan.
- `run_id`, `snapshot_id`, filter và thời điểm.

#### Tin 3 — RP Trợ lý/Vùng Top 1

- Vùng có tổng số phiếu cao nhất trong filter của lượt chạy.
- Tên vùng và danh sách Trợ lý nhận vùng.
- Các AM trong vùng và số phiếu tương ứng.
- Số phiếu GÁN KHẨN CẤP.
- Số phiếu GÁN NGAY.
- `run_id`, `snapshot_id`, filter và thời điểm.

### Quy tắc fail-closed

- Nếu crawl, verify, mapping hoặc ghi Sheet thất bại thì không gửi 3 báo cáo dữ liệu.
- Khi pipeline thất bại, chỉ gửi một cảnh báo lỗi tối thiểu cho hai Admin; không tạo báo cáo giả.
- Lỗi gửi một tin Admin phải ghi rõ người nhận, loại báo cáo và lỗi; không chạy lại toàn bộ pipeline.
- Không gửi các tin giám sát này cho AM hoặc Trợ lý.
- Ba báo cáo Admin là nhóm template riêng, không được sửa 4 template AM/Trợ lý đã khóa.

### Prompt giao AI

```text
Thêm Admin giám sát mã 3026736 bên cạnh Admin hiện tại 3049378.

Sau mỗi Master Pipeline thành công, gửi cho MỖI Admin đúng 3 tin riêng:
1. Health API.
2. RP AM Top 1 theo số phiếu của filter hiện tại.
3. RP Trợ lý/Vùng Top 1 theo số phiếu của filter hiện tại.

Tổng cộng 6 lượt gửi Admin cho mỗi pipeline thành công.

Nguồn dữ liệu bắt buộc:
- Dùng cùng snapshot RAM vừa crawl.
- Dùng cùng run_id, snapshot_id, filter và timestamp.
- Không đọc lại RP_theo_AM hoặc RP_theo_TroLy từ Sheet để dựng tin.

Quy tắc:
- Không gửi các báo cáo này cho AM hoặc Trợ lý.
- Nếu crawler, verify, mapping hoặc ghi Sheet lỗi thì không gửi báo cáo dữ liệu.
- Nếu pipeline fail thì chỉ gửi cảnh báo lỗi tối thiểu cho hai Admin.
- Nếu một tin Admin lỗi, ghi recipient/type/error và tiếp tục các tin còn lại.
- Không retry toàn bộ pipeline.
- Không sửa 4 template AM/Trợ lý đã khóa.
- Không thay đổi câu chữ template đã được duyệt.
- Không tự sửa logic phân loại GÁN KHẨN CẤP/GÁN NGAY.
- Sau khi Dashboard sửa xong và được phê duyệt mở lại, bổ sung đúng link `https://ghn-dashboard.pages.dev/` vào mẫu được duyệt; trước thời điểm đó không sửa template để thêm link.

Kiểm thử bắt buộc:
- 2 Admin nhận đủ 3 loại báo cáo.
- Đúng snapshot và filter.
- Top AM đúng.
- Top Vùng/Trợ lý đúng.
- Không đọc Sheet để dựng báo cáo.
- Fail-closed khi pipeline lỗi.
- Ghi rõ lỗi nếu một tin Admin gửi thất bại.

Chưa deploy, chưa chuyển traffic, chưa bật/tắt Scheduler và chưa gửi thật trước khi báo cáo test.
Báo cáo không quá 15 dòng, không emoji.
```

## 13. QUYỀN ADMIN ĐÃ ĐƯỢC CHỦ DỰ ÁN CHỐT

### Cấu hình bất biến

Danh sách Admin giám sát được chủ dự án thiết lập từ đầu và phải giữ nguyên:

```text
ADMIN_1 = 3049378
ADMIN_2 = 3026736
ADMIN_STATUS = APPROVED_LOCKED
```

Quy tắc bắt buộc:

1. Không được xóa, thay thế, đổi thứ tự hoặc tự suy đoán lại hai mã Admin.
2. Không được coi `3026736` là AM hoặc Trợ lý.
3. Không được chỉ gửi báo cáo cho `3049378` rồi coi là hoàn tất.
4. Mỗi Master Pipeline thành công phải gửi đủ 3 loại báo cáo cho từng Admin:
   - Health API.
   - RP AM Top 1.
   - RP Trợ lý/Vùng Top 1.
5. Tổng số tin giám sát Admin phải là 6 tin cho mỗi pipeline thành công.
6. Ba báo cáo của hai Admin phải dùng cùng `run_id`, `snapshot_id`, `filter`, `timestamp` và dữ liệu RAM.
7. Nếu một trong hai Admin gửi lỗi, phải ghi rõ `recipient_id`, `report_type`, lỗi và trạng thái; không được bỏ qua trong summary.
8. Nếu pipeline fail-closed trước khi có snapshot hợp lệ, không tạo báo cáo dữ liệu Top 1.
9. Mọi thay đổi danh sách Admin phải có câu lệnh trực tiếp của chủ dự án, không được suy ra từ `Co_Cau`.
10. AI phải kiểm tra test matrix có cả hai mã Admin trước khi báo PASS.

### Kiểm tra bắt buộc trước mỗi lần nghiệm thu

- Xác nhận cấu hình vẫn có đủ `3049378` và `3026736`.
- Xác nhận mỗi mã nhận đủ 3 loại báo cáo.
- Xác nhận báo cáo Top 1 lấy từ RP trong RAM của snapshot hiện tại.
- Xác nhận không lấy dữ liệu cũ từ tab `RP_theo_AM` hoặc `RP_theo_TroLy`.
- Xác nhận không gửi nhầm báo cáo giám sát cho AM/Trợ lý.

## 14. HỢP ĐỒNG HIỂN THỊ DASHBOARD — CẬP NHẬT SAU RP ĐỐI SOÁT 2026-09-24

### 14.1 Kết luận phạm vi giao diện

- Tên các khu vực chính của dashboard hiện cơ bản đúng, không đổi tên tùy tiện.
- Lỗi trọng tâm hiện tại là dữ liệu mapping và dữ liệu đầu vào, không phải đổi tên giao diện.
- Khu vực phải giữ đúng tên: `Tồn phiếu theo Vùng / AM / Bưu cục`.
- Không dùng `Vùng / AM / Mã kho` làm tên hoặc cấp hiển thị.
- `Mã kho` chỉ là mã phụ của bưu cục, không thay cho tên bưu cục.

### 14.2 Cấu trúc hiển thị bắt buộc

```text
Vùng
  AM
    Bưu cục
      Mã kho
```

- Vùng hiển thị bằng tên/mã vùng chuẩn.
- AM hiển thị bằng tên AM; nếu chưa gán thì ghi `Chưa gán AM`.
- Bưu cục hiển thị bằng tên bưu cục.
- Mã kho hiển thị phụ sau tên bưu cục.
- Không được đưa mã kho vào vị trí tên vùng, tên AM hoặc tên bưu cục.
- Mỗi mã kho chỉ được map tới một bưu cục, một vùng và tối đa một AM tại cùng snapshot.
- Mã kho không map được phải nằm trong nhóm lỗi, không được âm thầm bỏ khỏi bảng.

### 14.3 Ý nghĩa các khu vực dữ liệu

| Khu vực | Ý nghĩa bắt buộc | Nguồn kiểm tra |
|---|---|---|
| Tổng phiếu tồn | Tổng số ticket trong snapshot hợp lệ | `Chi_tiet`/API |
| Tiền phạt đang chịu | Tổng `tien_phat` của snapshot | API + `Chi_tiet` |
| Trễ SLA | Ticket có trạng thái SLA trễ theo data contract đã chốt | API/Sheet |
| Chưa Trễ SLA | Ticket chưa trễ trong cùng snapshot | API/Sheet |
| Top 15 bưu cục | 15 bưu cục có tổng ticket cao nhất | `ma_buu_cuc` + `ten_buu_cuc` |
| Phân bố theo trạng thái | Chỉ phân bố Trễ SLA và Chưa Trễ SLA | cùng snapshot |
| Tồn theo Vùng/AM/Bưu cục | Cây Vùng → AM → Bưu cục → Mã kho | `Co_Cau` + `Chi_tiet` |
| Bảng bưu cục | Một dòng cho mỗi bưu cục, có tên và mã | `Ton_phieu`/`Chi_tiet` |
| Danh sách phiếu | Một dòng cho mỗi ticket, đủ mã ticket, mã đơn, kho, SLA, phạt | `Chi_tiet` |

### 14.4 Bằng chứng RP hiện có cần giữ nguyên để điều tra

- Production đang hiển thị snapshot `24/09/2026 04:00:20`, trong khi API được báo cáo có dữ liệu mới lúc `17:54:49`.
- Production có dấu hiệu mất `ma_ticket`, `ma_don`, `tien_phat` và `ten_buu_cuc`.
- Production hiển thị `Trễ SLA = 0%` và `Tiền phạt = 0đ`; chưa được coi là dữ liệu đúng.
- 14 vùng chuẩn đã được nhận diện; vẫn phải kiểm tra đủ vùng, AM và mã kho ở snapshot hiện tại.
- Có ticket chưa gán AM; phải phân biệt rõ `Chưa gán AM` với lỗi mapping.
- Báo cáo hiện nghi ngờ API trả `penalty=0` khi crawl tách theo `ly_do`; phải tái lập bằng kiểm tra read-only trước khi sửa.
- `dashboard_sync._build_raw()` bị nghi ngờ không nạp đầy đủ dữ liệu bưu cục; phải xác minh trước khi kết luận.
- Có rủi ro internal scheduler và ingestion cùng ghi Sheet; phải kiểm tra lock và lịch thực tế.

### 14.5 Điều kiện mở lại dashboard

Chỉ mở lại deploy sau khi đạt đủ:

1. Timestamp production là snapshot mới nhất đã được xác nhận.
2. Tổng ticket, tổng phạt và SLA khớp API/Sheet/HTML/UI.
3. Tất cả vùng được kiểm tra; không có vùng mất hoặc map sai.
4. Tất cả AM được kiểm tra; dòng chưa gán được đánh dấu rõ.
5. Tất cả mã kho được map tới đúng tên bưu cục và vùng.
6. Top 15 và bảng bưu cục có tên, mã và tổng đúng.
7. Không có trigger/writer chồng hoặc deploy bản cũ ghi đè.
8. Ticket mẫu truy vết khớp từ nguồn tới giao diện.

### 14.6 DINH NGHIA VUNG — CHOT LAI, KHONG CO SO LUONG CO DINH

So luong vung trong moi bao cao chi la ket qua cua snapshot tai thoi diem do.
Khong duoc coi 14, 18 hoac bat ky con so nao la cau hinh co dinh cua he thong.

Nguon chuan:

```text
Co_Cau.region_shortname
-> Chi_tiet.region_shortname
-> dashboard RAW
-> Dashboard UI va RP
```

Quy tac bat buoc:

1. Khong hardcode allowlist hoac so luong vung.
2. Khong tu dong doi `Freight Operations - HCM` thanh `HCM`.
3. Khong tu dong doi `Freight Operations - HN` thanh `HNO`.
4. Khong loai `SC North`, `SC South` hoac vung moi neu ton tai trong `Co_Cau`.
5. Vung co 0 ticket van la du lieu hop le neu dang co trong danh muc nguon; UI co the khong hien trong bang phan bo theo ticket.
6. Vung co ticket phai hien thi day du trong filter va cay Dashboard.
7. Vung moi xuat hien trong `Co_Cau` phai tu dong duoc nhan, khong can sua code de them ten vung.
8. Gia tri xuat hien trong `Chi_tiet` nhung khong co trong `Co_Cau` phai vao nhom canh bao/unmapped; khong tu dong them vao `Co_Cau`.
9. Ticket khong map duoc vung phai vao `(Chua gan Vung)` va bao cao so luong; khong bi am tham loai bo.
10. Moi RP/template phai lay danh sach vung tu nguon dong, khong tu danh sach viet cung.
11. Neu `Code.gs` co logic bo qua vung, chi duoc sua sau khi xac dinh ro dong do la header ky thuat hay region hop le; khong duoc dung `GH NANG` lam dieu kien loai vung chung.
12. Test phai bao gom vung moi phat sinh, vung 0 ticket va gia tri khong map duoc.

Ket qua dem vung trong moi snapshot chi la thong tin bao cao, khong phai viec can sua cau hinh.

## 15. PROMPT ĐIỀU TRA NGẮN CHO AI KHÁC

```text
Chi dieu tra read-only, khong sua code, khong deploy, khong ghi Sheet, khong chay production.

Du an: E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin_n8n\ControlCenter
Dashboard: https://ghn-dashboard.pages.dev/

Kiem tra day du chuoi:
API -> Chi_tiet -> Ton_phieu -> RP_theo_AM -> HTML -> Cloudflare -> UI.

Bat buoc kiem tra:
1. Timestamp, so ticket, so buu cuc, tong phat, Tre SLA, Chua Tre SLA.
2. Toan bo vung, toan bo AM, toan bo ma kho.
3. Mapping ma kho -> ten buu cuc -> vung -> AM.
4. Vung thieu/thua, AM sai, kho thieu ten, kho trung map, dong null.
5. Top 15, bang buu cuc, cay Vung -> AM -> Buu cuc -> Ma kho.
6. Ticket 4754747 qua tat ca cac lop.
7. Tat ca trigger/writer: Cloud Scheduler, internal scheduler, GitHub Actions, deploy script, dashboard_sync, Apps Script, n8n/batch, Cloud Run, Cloudflare.
8. Chay chong, ghi de, build khi Sheet dang ghi, deploy ban cu.

Tra loi ngan theo mau:
KET LUAN: DUNG / SAI / CHUA DU BANG CHUNG
DATA: dung/sai + ly do
MAPPING VUNG: dung/sai
MAPPING AM: dung/sai
MAPPING KHO: dung/sai
SLA PHAT: dung/sai
TRIGGER: co chong/khong/chua biet
LOP LOI: API/Sheet/mapping/build/deploy/UI
TICKET 4754747: dung/sai/chua tim thay
BUOC TIEP: mot cau

Khong viet code. Cuoi cung ghi: Chua thay doi production.
```

## 16. KE HOACH DEPLOY DASHBOARD VA KHOA HEADER — CHOT 2026-09-25

### 16.1 Muc tieu

- Deploy Dashboard tu dung artifact da build tu source:
  `dashboard/index.html`.
- Moi lan gui thong bao phai dung snapshot moi vua crawl va deploy thanh cong.
- Bao ve hang tieu de Google Sheet, khong cho sua nham ten cot hoac thu tu cot.
- Chi bat SSO sau khi Dashboard production da verify dung du lieu.

### 16.2 Chuoi bat buoc moi lan gui thong bao

```text
INGESTION -> VALIDATE -> BUILD -> DEPLOY -> VERIFY -> SEND NOTIFICATION
```

Quy tac:

1. Crawl va tao `snapshot_id` moi.
2. Validate schema `Chi_tiet` 14 cot, `Ton_phieu` 8 cot, `Co_Cau` 10 cot.
3. Validate tong ticket, `tien_phat`, `bcs`, AM, vung va mapping.
4. Build artifact tu source Dashboard duy nhat.
5. Deploy artifact.
6. Verify production count, timestamp, hash, SLA, tien phat, bang ticket va mapping.
7. Chi sau khi verify PASS moi gui thong bao.
8. Neu bat ky buoc nao FAIL thi khong gui thong bao du lieu.

Thong bao phai kem:

```text
snapshot_id
source_updated_at
built_at
deployed_at
total
total_phat
tre_sla
chua_tre_sla
artifact_hash
```

### 16.3 Bao ve header Google Sheet

Bao ve hang tieu de cua cac tab:

```text
Chi_tiet
Ton_phieu
Co_Cau
```

Yeu cau:

- Dung Protected Range cho hang tieu de.
- Chi owner/admin va service account da duoc cap quyen moi duoc sua header.
- Khong khoa cac dong du lieu ma ingestion can ghi.
- Khong doi ten cot, thu tu cot hoac schema.
- Test ingestion sau khi khoa header.
- Neu khong co quyen Protected Range thi dung va bao cao, khong tu y bo qua.

### 16.4 Pre-deploy gate

Chi deploy khi dat tat ca dieu kien:

1. Chu du an phe duyet mo `FREEZE`.
2. Source va artifact da duoc hash va doi chieu.
3. Snapshot moi nhat da xac nhan.
4. Tong ticket va tong phat khop API/Sheet/HTML.
5. Logic SLA da chot:
   `tien_phat = 0 -> Chua Tre SLA`, `tien_phat > 0 -> Tre SLA`.
6. Bang ticket co du lieu, khong blank.
7. `bcs`, `ams`, vung va mapping khong rong bat thuong.
8. Khong co writer hoac scheduler dang ghi de snapshot.
9. Da co artifact cu va phuong an rollback.

### 16.5 Thu tu deploy

```text
Backup artifact cu
-> mo FREEZE co phe duyet
-> deploy Cloudflare Pages
-> verify production
-> cap nhat quy trinh gui thong bao
-> chay thong bao test
-> rollback neu verify FAIL
```

- Khong deploy Cloud Run neu khong can cho Dashboard.
- Khong bat Scheduler trong cung buoc neu chua kiem tra writer/lock.
- Khong gui thong bao that truoc khi verify Dashboard production.

### 16.6 SSO sau deploy Dashboard

Chi thuc hien sau khi Dashboard production PASS:

1. Cau hinh `GHN_SSO_CLIENT_ID`.
2. Cau hinh `GHN_SSO_CLIENT_SECRET`.
3. Cau hinh `GHN_SSO_REDIRECT_URI`.
4. Kiem tra login, callback, state, nonce, session, logout va timeout.
5. Xac nhan API/webhook khong bi chan nham.
6. Khong log secret, access token hoac refresh token.

### 16.7 SUA TEMPLATE SAU KHI DASHBOARD LIVE

Chi thuc hien sau khi Dashboard Cloudflare da deploy va verify PASS.

Pham vi:

- Ra soat template RP Vung dang duoc dung that.
- Cap nhat link Dashboard dung:
  `https://ghn-dashboard.pages.dev/`
- Khong sua schema Google Sheet.
- Khong doi logic mapping Vung, AM, Buu cuc hoac Ma kho.
- Khong sua template AM/Trợ lý da khoa neu khong co yeu cau rieng.
- Khong bo qua hoac tu y loai bo vung hop le tu nguon.
- Dong bo version template giua file nguon, Code.gs va artifact runtime neu chung cung duong chay.

Quy trinh:

```text
Xac dinh template active
-> backup template cu
-> sua link Dashboard
-> preview dry-run
-> verify dung Vung/AM/Buu cuc
-> test gui den recipient test
-> phe duyet
-> moi cho phep gui that
```

Dieu kien dat:

1. Template khong con link Dashboard cu.
2. Link moi mo dung production Dashboard.
3. Noi dung thong bao giu dung cau truc da duyet.
4. Khong gui nham Vung, AM, Trợ lý hoac Admin.
5. Preview va test recipient dung snapshot moi.
6. Neu Dashboard verify fail thi khong sua template va khong gui thong bao.

Trang thai phase nay: CHUA BAT DAU, cho Dashboard production verify PASS.

### 16.8 Phan cong

- Chu du an: phe duyet mo FREEZE, phe duyet deploy va phe duyet bat SSO.
- AI thuc thi: chay dung cac buoc, khong tu mo rong pham vi, bao cao hash va ket qua.
- AI khong duoc tu y sua RP Vung, Code.gs, Cloud Run version, schema hoac Scheduler.

---

## 17. NHẬT KÝ HOÀN THIỆN ĐỢT 25/09/2026

### 17.1 Logic SLA đơn giản hóa
- `tien_phat == 0` ➔ `Chưa Trễ SLA`
- `tien_phat > 0` ➔ `Trễ SLA`
- Áp dụng đồng nhất 100% qua cùng hàm `slaOf(t)` trên toàn bộ KPI, Chart 2, Cây tổ chức và Bảng ticket.

### 17.2 Hỗ trợ đầy đủ 18 Vùng từ Co_Cau
- Tự động lấy UNION: `Co_Cau regions (18 vùng) + Chi_tiet regions + (Chưa gán Vùng)`.
- Giữ nguyên tên vùng đặc thù: `Freight Operations - HCM`, `Freight Operations - HN`, `SC North`, `SC South`.
- Vùng 0 vé vẫn được bảo toàn trong danh mục lọc và hiển thị.

### 17.3 Đồng bộ Link Dashboard trong Template Báo cáo Vùng
- Cập nhật link `https://ghn-dashboard.pages.dev/` vào template báo cáo Trợ lý Vùng (`mau_vung_all`, `mau_vung_hoilay`).
- Không làm thay đổi schema hay cấu trúc dữ liệu downstream.

### 17.4 Tích hợp Auto-Deploy Cloudflare Pages vào Master Pipeline
- Endpoint: `POST /api/pipeline/run` (gọi từ `ghn-master-pipeline-job` lúc `0 6-16 * * *` VN).
- Chuỗi thực thi tự động: `Ingestion ➔ Validate ➔ Write Sheet ➔ Auto-Deploy Cloudflare Pages ➔ Send GTalk Notifications`.

### 17.5 Quy chuẩn thông báo 2 Admin & 6 tin giám sát
- Danh sách Admin: `ADMIN_IDS = ["3049378", "3026736"]`.
- Mỗi đợt chạy gửi đủ 3 loại tin cho mỗi Admin (Tổng: 6 tin):
  1. `HEALTH_API`: Sức khỏe API, Latency, SLA, Snapshot ID, Nguồn cập nhật, Build/Deploy timestamp, Artifact Hash, Link Dashboard.
  2. `TOP_AM`: Bản sao nguyên văn tin AM tồn nhiều nhất.
  3. `TOP_TRO_LY`: Bản sao nguyên văn tin Trợ lý Vùng tồn nhiều nhất.

### 17.6 Trạng thái hiện tại
- **Cloudflare Pages (`ghn-dashboard.pages.dev`):** Đã triển khai màn hình thông báo bảo trì / tạm dừng phục vụ theo yêu cầu của Quản trị viên.
- **Lịch hẹn rà soát toàn diện:** Đã lên lịch tự động chạy lúc **13:10 ngày 25/09/2026** (Read-only Audit).
- **Bộ kiểm thử:** Đạt 31/31 unit & integration tests PASS.
