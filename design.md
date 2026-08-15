

#1 Luồng hệ thống:

- input: file yaml tổng quát của các service trong repo.
- Nếu database trống(repo chưa được đẩy lên) -> băm nội dung file yaml lưu vào database.
- sử dụng sha256, băm nội dung file để xác nhận sự khác nhau giữa nội dung file trước và sau

  - Nếu mã băm file yaml không có gì thay đổi -> continue
  - Nếu mã băm có sự thay đổi trước và sau -> đi xuống luồng thay đổi phía sau:

  Cấu trúc của một file catalog.yaml chuẩn:

```yaml
# docs/idp/idp-core-admin/catalog-info.yaml
# IDP Core Admin API — giao diện portal dành cho Platform/DevOps team
# Các chức năng: catalog, spec review, lifecycle, release, IAM publish, audit
# ─────────────────────────────────────────────────────────────────────────────

# specVersion — phiên bản schema của IDP catalog declaration.
# Giá trị cố định: vsf-idp.io/v2
specVersion: vsf-idp.io/v2

metadata:
  # domain — tên domain nghiệp vụ / P&L chủ quản component này. Free-text, do Biz đặt.
  # Cho phép: spaces, chữ hoa, ký tự đặc biệt printable. Tối đa 128 ký tự. KHÔNG có control characters.
  # Dùng làm label phân loại trên Portal (không tham gia vào service_key hay permission code).
  # Ví dụ: "Platform Engineering" | "Payment & Loyalty" | "Identity"
  domain: platform  # require. -> table: service.domain_code (VARCHAR 128)

  # system — hệ thống (bounded context) mà component thuộc về.
  # Kết hợp với spec.id tạo thành service_key = "{system}.{spec.id}" — định danh bất biến.
  # Format: ^[a-z][a-z0-9-]*$  — bắt đầu bằng chữ thường, chỉ gồm [a-z0-9-]. KHÔNG có spaces/chữ hoa.
  # Ví dụ: idp-core | iam | vsf-payment
  system: idp-core  # require. -> table: service.system_code

  # namespace — K8s / IAM namespace scope của component.
  # Dùng làm segment đầu của permission code: "{namespace}.{service_id}.{resource}.{action}.perm".
  # Format: ^[a-z][a-z0-9-]*$  — bắt đầu bằng chữ thường, chỉ gồm [a-z0-9-]. KHÔNG có spaces/chữ hoa.
  # Ví dụ: idp | iam | commerce
  namespace: idp  # require -> table: service.namespace

spec:
  # type — loại component khai báo.
  #
  # Có API surface → trigger spec ingest + review workflow:
  #   service       → binary HTTP/gRPC API            (cần registry.yaml + openapi.yaml)
  #   gateway       → BFF hoặc API gateway layer      (cần registry.yaml + openapi.yaml)
  #
  # Không có API surface → chỉ track trong catalog:
  #   worker        → background consumer/scheduler   (chỉ catalog-info.yaml)
  #   batch         → one-shot/cron job               (chỉ catalog-info.yaml)
  #   job           → alias của batch (Backstage compat)  (chỉ catalog-info.yaml)
  #   library       → shared library/SDK dùng lại     (chỉ catalog-info.yaml)
  #   website       → frontend web app / SPA           (chỉ catalog-info.yaml)
  #   mobile-app    → ứng dụng di động iOS/Android     (chỉ catalog-info.yaml)
  #   data-pipeline → ETL / CDC / stream pipeline      (chỉ catalog-info.yaml)
  #   function      → serverless function              (chỉ catalog-info.yaml)
  #   plugin        → plugin hoặc module mở rộng       (chỉ catalog-info.yaml)
  #   tool          → công cụ nội bộ / CLI             (chỉ catalog-info.yaml)
  #   documentation → trang tài liệu / docs site       (chỉ catalog-info.yaml)
  #   other         → loại chưa được chuẩn hóa         (chỉ catalog-info.yaml)
  type: service   # require -> table: service.service_type

  # id — định danh duy nhất của component trong system.
  # Kết hợp với metadata.system tạo thành service_key = "{system}.{id}".
  # Format: ^[a-z][a-z0-9-]*$  — bắt đầu bằng chữ thường, chỉ gồm [a-z0-9-]. KHÔNG có spaces/chữ hoa.
  # Phải nhất quán với field service trong registry.yaml.
  id: idp-core-admin  # require -> table: service.service_key ({system}.{id})

  # name — tên hiển thị trên IDP Portal (human-readable, free-text).
  # Cho phép: spaces, chữ hoa, ký tự đặc biệt. KHÔNG được chứa control characters (U+0000–001F, DEL).
  name: IDP Core Admin API  # require -> table: service.name

  # description — mô tả ngắn về component, hiển thị trên trang Service Metadata trong Portal.
  # Tuỳ chọn, không bắt buộc.
  description: IDP Core Admin API - portal for Platform/DevOps team  # optional -> table: service.description

  owners:
    members:  # require at least 1 member techlead -> table: service_member
      # user  — email VinSmart của người sở hữu.
      # role  — vai trò trong team:
      #   techlead   → tech lead / primary owner, người quyết định kiến trúc
      #   maintainer → người maintain code/on-call, nhận alert
      #   member → đóng góp nhưng không chịu trách nhiệm on-call
      - user: v.kiennd17@vinsmartfuture.tech
        role: techlead
      - user: v.hadt191@vinsmartfuture.tech
        role: techlead
      - user: v.daonq2@vinsmartfuture.tech
        role: techlead
      - user: v.tiennq16@vinsmartfuture.tech
        role: member
  # review — cấu hình spec-review merge gate cho API của component này.
  # branch: nhánh đích (destination/target branch) mà merge request phải qua IDP
  #   spec review + approve trước khi merge. Ở MR mode, ingest TỪ CHỐI (422) nếu
  #   target_branch của MR khác giá trị này — BỔ SUNG cho kiểm tra "branch đích là
  #   protected" lấy từ OIDC id token; CẢ HAI phải đúng. Khớp tên nhánh chính xác.
  review:
    branch: "main"  # require để validate merge request

  # topology — danh sách phụ thuộc của component này. IDP Portal dùng để render
  # dependency graph và bảng UPSTREAM / DOWNSTREAM trong tab Dependencies.
  #
  # Mỗi entry là object với các field:
  #   ref      (bắt buộc) — "{kind}:{namespace}/{name}"
  #   protocol (tuỳ chọn) — giao thức giao tiếp: REST | gRPC | Kafka | WebSocket | …
  #   reason   (tuỳ chọn) — mô tả ngắn lý do phụ thuộc, hiển thị cột REASON trên Portal
  #
  # Các kind được hỗ trợ trong ref:
  #   system:        — system mà component NÀY thuộc về → sinh quan hệ partOf / hasPart trên graph (direction: partOf)
  #   resource:      — tài nguyên hạ tầng (database, queue, bucket, secret-store…) (direction: partOf)
  #   component:     — component khác trong IDP (service, worker, gateway…)  (direction: partOf)
  #   providesApis:  — API mà component NÀY expose ra ngoài (khai báo trong registry.yaml) (direction: upstream)
  #   consumesApis:  — API của service khác mà component NÀY gọi vào (direction: downstream)
  #   publishesTo:   — Kafka topic mà component NÀY publish event vào (direction: downstream)
  #   consumesFrom:  — Kafka topic mà component NÀY consume event từ  (direction: upstream)
  #
  # Namespace trong ref phải khớp với namespace của component/resource được tham chiếu,
  # không nhất thiết phải là namespace của service hiện tại.
  topology:   # optional, table -> service_dependency
    # ── Membership ───────────────────────────────────────────────────────────
    # partOf — khai báo component này thuộc system nào.
    # IDP Portal dùng để vẽ cạnh hasPart (system → component) / partOf (component → system)
    # trên Relations graph. Phải khớp với metadata.system ở trên.
    - ref: system:idp/idp-core  #table -> service_dependency.targer_ref
      reason: Component này là một phần của system idp-core    # table -> service_dependency.reason

    # ── Sibling components ────────────────────────────────────────────────────
    - ref: component:idp/idp-core-integration
      reason: Sibling CI/CD API — ghi catalog data, ingest_commit, spec_snapshot mà admin đọc để review
    - ref: component:idp/idp-core-consumer
      reason: Sibling consumer — nhận dispatch event từ outbox mà admin ghi, thực hiện IAM sync call

    # ── Infrastructure ────────────────────────────────────────────────────────
    - ref: resource:idp/idp-core-postgres
      reason: Primary datastore — lưu toàn bộ catalog, review, lifecycle, audit data
    - ref: resource:platform/kafka
      reason: Kafka broker — required for all publishesTo/consumesFrom topics.

    # ── APIs ──────────────────────────────────────────────────────────────────
    - ref: providesApis:idp/idp-core-admin
      protocol: REST   # table -> service_dependency.protocol
      reason: OpenAPI spec của chính service này — expose lên Portal UI.
    - ref: consumesApis:iam/iam-api
      protocol: REST
      reason: Lấy user profile

    # ── Kafka topics ──────────────────────────────────────────────────────────
    # External topics — visible to other services on the platform
    - ref: publishesTo:idp/idp.audit-events
      protocol: kafka
      reason: Publish audit log events (actor, action, entity, before/after) cho downstream consumers
    - ref: consumesFrom:iam/iam.permission-sync
      protocol: kafka
      reason: Nhận thông báo khi IAM sync permission binding thành công để cập nhật trạng thái

    # Internal dispatch topic — transactional outbox pattern.
    # OutboxDispatcher (job chạy trong process này) scan bảng iam_sync_outbox
    # và publish mỗi row thành một event; idp-core-consumer nhận và thực hiện IAM call.
    - ref: publishesTo:idp/idp.iam-sync.dispatch
      protocol: kafka
      reason: Internal outbox dispatch — trigger idp-core-consumer thực hiện IAM sync call
```

- dựa vào cấu trúc chuẩn của file yaml trên, triển khai thành 3 bảng database theo cấu trúc như sau:

# **Bảng 1 Services (Lưu trữ Metadata)**

| Cột          | ghi chú                                   |
| ------------- | ------------------------------------------ |
| service_key   | **[PK]** Format: `{system}.{id}`   |
| domain        | Từ`metadata.domain`                     |
| commit_hash   |                                            |
| system        | Từ`metadata.domain`                     |
| name space    | Từ`metadata.domain`                     |
| service_id    | Từ`spec.id`                             |
| service_type  | Từ`spec.type` (service, worker, job...) |
| name          | Từ`spec.name`                           |
| description   | Từ`spec.description`                    |
| review_branch | Từ`spec.review.branch`                  |
| raw_yaml      | Lưu toàn bộ cục YAML gốc              |
| created_at    | Thời gian tạo                            |
| updated_at    | Thời gian của lần cập nhật cuối      |
|               |                                            |


# **Bảng 2 Service_members** 

| Cột        | Ghi chú                                                              |
| ----------- | --------------------------------------------------------------------- |
| id          | **[PK]** Khóa chính tự tăng hoặc UUID                      |
| service_key | **[FK]** Trỏ tới `services.service_key` (ON DELETE CASCADE) |
| user_email  | Email của owner (vd:`v.kiennd17@...`)                              |
| role        | `techlead`, `maintainer`, `member`                              |
|             |                                                                       |


# **Bảng 3 Service_dependencies(Lưu trữ Topology / Topology Graph)**

| Cột        | Ghi chú                                                               |
| ----------- | ---------------------------------------------------------------------- |
| id          | [PK]                                                                   |
| service_key | **[FK]** Trỏ tới `services.service_key` (ON DELETE CASCADE)  |
| target_ref  | Giá trị`ref` (vd: `component:idp/idp-core-consumer`)             |
| ref_kind    | Parse từ`target_ref` (system, resource, component, providesApis...) |
| protocol    | `REST`, `gRPC`, `kafka` (nullable)                               |
| reason      | Lý do phụ thuộc                                                     |

- Một số lưu ý:

  - khi người dùng xóa file rồi push code lên, -> thêm nhãn removed -> xóa khỏi database
  - Khi người file bị chỉnh sửa phần nào ở các bảng thì sẽ xuất hiện phần ấy
  - Thông báo sẽ được gửi về qua webhook
  - cấu trúc thư mục được cấu tạo như sau:
    - idp-webhook-test/
      ├── app/                            # Toàn bộ mã nguồn Backend FastAPI
      │   ├── __init__.py
      │   ├── main.py                     # Khởi tạo FastAPI, định nghĩa router (/v1/test_api)
      │   ├── database.py                 # Cấu hình SQLAlchemy (kết nối DB, Session)
      │   ├── models.py                   # Định nghĩa 3 bảng (services, members, dependencies)
      │   ├── parser.py                   # Chứa logic parse file .yaml thành Dictionary
      │   └── webhook_handler.py          # Chứa logic Transaction, SELECT FOR UPDATE, check version
      │
      ├── dummy_repos/                    # Thư mục giả lập kho chứa code của developer
      └── idp-core-admin/
      └── catalog-info.yaml
  - Sau khi lấy được các thông tin ở payload, các thay đổi nội dung vào các bảng hãy sử dụng orm để tự tạo bảng cho tôi và lưu dữ liệu vào database, lưu vào postre SQL thông qua URL:DATABASE_URL=postgresql://neondb_owner:npg_Gaf8o0LzQxJC@ep-round-pine-azdxj0uf.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&options=-csearch_path%3Dai20k_db
  - trong database sẽ chỉ chứa một phiên bản của dữ liệu, nếu dữ liệu được cập nhật thì dữ liệu mới sẽ ghi đè lên dữ liệu cũ trong database
  - ứng dụng arq để tối ưu hệ thống luôn,

  ### Xử lý Bất đồng bộ (Asynchronous Processing)

  Đừng xử lý logic tải file và lưu DB ngay trong route của FastAPI. Hãy áp dụng **Background Tasks** (có sẵn của FastAPI) hoặc Message Queue (như Celery, Redis Queue, RabbitMQ).


  * **API nhận Webhook:** Chỉ kiểm tra tính hợp lệ của Webhook, ném payload vào Queue/Background Task, và trả về HTTP `202 Accepted` ngay lập tức (dưới 100ms).
  * **Worker:** Lấy payload ra, lọc các file `.yaml` đã thay đổi, tải về, parse và cập nhật DB.

  ### Xử Lý Xóa File (File Deletion)

  Payload Webhook của GitHub/GitLab thường có 3 mảng: `added`, `modified`, `removed`.

  * Với `added` và `modified`: Tải file về và Sử dụng hàm băm sha256 (Thêm mới hoặc Cập nhật) vào DB.
  * Với `removed`: Lấy đường dẫn file, tra xem nó thuộc `service_key` nào trong DB và tiến hành xóa (`DELETE` hoặc soft-delete `is_deleted = true`). Không tải file vì file đã bị xóa.


### Cơ Chế Idempotency & Phiên Bản

Sử dụng `commit_hash` để so sánh. Khi lưu vào DB, hãy check: "Commit hash của file đang xử lý có phải là mới nhất so với commit hash đang nằm trong DB không?". Nếu cũ hơn, bỏ qua sự kiện đó để tránh việc mạng bị lag làm thay đổi thứ tự update.
