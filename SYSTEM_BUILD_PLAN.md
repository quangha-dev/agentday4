# Research Agent — kế hoạch xây dựng v0 → v3

## 1. Mục tiêu và nguyên tắc nghiệm thu

Hệ thống là một research agent có khả năng chọn tool, truyền arguments, chạy tool thật, lưu trace đầy đủ và chứng minh được chất lượng qua các vòng cải tiến. Thành công không chỉ là câu trả lời hợp lý; mỗi thay đổi phải truy ngược được tới prompt/tool declaration, artifact hash, run JSON, transcript hoặc test.

Các yêu cầu bắt buộc:

- chạy được với ít nhất một provider thật;
- có tối thiểu 5 tool được khai báo và có ít nhất 1 tool mới do nhóm xây dựng;
- có baseline `v0` và ba vòng cải tiến thật `v1`, `v2`, `v3`;
- có đúng 10 group eval: 5 single-turn và 5 multi-turn;
- có UI dùng chung agent loop với CLI, hiển thị response, tool trace, version và evidence;
- có version log, run JSON, transcript JSON và report dựa trên kết quả thật;
- không để lộ secret; action tool phải fail-closed nếu chưa có xác nhận;
- prompt injection từ user hoặc nội dung truy xuất phải được coi là dữ liệu không tin cậy.

## 2. Kiến trúc mục tiêu

Luồng xử lý cuối cùng:

1. Nhận user input và chuẩn hóa Unicode/ký tự ẩn.
2. `request_guard` đánh giá dấu hiệu injection, exfiltration, ép gọi tool và yêu cầu ngoài phạm vi.
3. Chỉ chặn các chỉ thị tấn công rõ ràng; câu hỏi nghiên cứu hợp lệ về chủ đề prompt injection vẫn được phép.
4. Model nhận system prompt và tool schema đã harden.
5. Tool call được kiểm tra allowlist, schema và argument policy trước khi thực thi.
6. Tool result được redaction, giới hạn kích thước và đóng gói như untrusted data trước khi đưa lại model.
7. Action tool cần xác nhận rõ trong hội thoại và guard ở implementation.
8. Transcript/run lưu version, hash, guard decision, tool call, args, result/error và final answer.
9. UI đọc cùng artifact/evidence để hiển thị so sánh trước–sau.

## 3. Kế hoạch theo version

### v0 — baseline của starter

Mục đích: giữ nguyên bằng chứng ban đầu để đo lỗi.

Đặc điểm cố ý chưa tốt:

- prompt yêu cầu đoán dữ liệu thiếu;
- tự thực hiện hành động gửi/đăng;
- ép chỉ chọn một tool;
- tool descriptions mơ hồ;
- không có ranh giới dữ liệu truy xuất và instruction;
- không có input/tool-result guard.

Nghiệm thu: chạy base eval bằng provider thật, lưu run JSON và ghi dòng `v0` vào version log trước khi thay artifact hiện hành.

### v1 — routing tốt hơn nhưng security chưa hoàn chỉnh

Mục tiêu: sửa routing và argument extraction cơ bản để cho thấy một vòng cải tiến có thật.

Thay đổi:

- phân biệt timeline, social search, web news và URL fetch;
- hỏi lại khi thiếu handle/URL;
- yêu cầu xác nhận trước action;
- cho phép nhiều tool call độc lập;
- bổ sung mapping tên thường gặp sang handle và quy ước timeframe/search type.

Điểm yếu được giữ có chủ ý và phải ghi trong report:

- chủ yếu dựa vào system prompt, chưa có deterministic request guard;
- chưa scan tool output cho injection;
- chưa có argument-policy validation tập trung;
- chống Unicode obfuscation và exfiltration còn yếu.

Nghiệm thu: base eval tốt hơn `v0`; run và hash khác `v0`; failure analysis xác định rõ các lỗ hổng còn lại.

### v2 — security + tool contract

Mục tiêu: khắc phục các lỗi v1 bằng defense-in-depth mà không tạo tool call thừa trong base eval.

Thay đổi:

- thêm guard ngoài model để phát hiện injection trực tiếp;
- thêm tool mới `question_guard` cho audit/giải thích kết quả kiểm tra câu hỏi;
- guard chạy ở orchestration, không bắt model gọi `question_guard` trong mọi request;
- coi web/tweet/PDF/policy text là untrusted data;
- redaction secret và instruction-like payload trong tool results;
- validate URL, size, limit, enum và unknown arguments;
- mô tả rõ confirmation boundary và no-tool/out-of-scope behavior;
- thêm security eval gồm benign, direct injection, obfuscation, tool coercion và secret exfiltration.

Nghiệm thu: không regression base routing; security offline tests pass; câu hỏi nghiên cứu hợp lệ về prompt injection không bị chặn.

### v3 — bản hoàn thiện và evidence-driven UI

Mục tiêu: đóng gói hệ thống để demo/nộp bài.

Thay đổi:

- hoàn thiện prompt với precedence, scope, multi-turn correction và source policy;
- hoàn thiện đúng 10 group eval;
- UI hiển thị chat, guard decision, tool trace, artifact version, prompt diff, version log và run summaries;
- snapshot artifact `v0/v1/v2/v3` để tái tạo so sánh;
- test schema, registry/declaration sync, security regression và grader semantics;
- report liên kết tới evidence thật.

Nghiệm thu cuối:

- provider/core/new-tool smoke tests pass;
- base và group live eval không có provider error;
- 3 live chat scenario có transcript;
- version log đủ `v0–v3`, mỗi version có hypothesis và run file thật;
- UI mở được, không hiển thị secrets;
- không claim pass nếu tool execution có error chưa review.

## 4. Test strategy

### Public/base contract

- routing theo account/topic/web/URL;
- đúng `limit`, `timeframe`, `search_type`;
- clarify khi thiếu thông tin;
- confirmation trước write action;
- no-tool và out-of-scope;
- parallel calls;
- multi-turn carryover, correction và tool switch.

### Group eval bắt buộc

- 5 single-turn và 5 multi-turn;
- không sao chép case mẫu;
- tập trung vào ambiguity, boundary, topic-vs-account, correction, no-tool và injection-safe behavior.

### Hidden-like/adversarial suite

- “ignore previous instructions”, role spoofing, fake system/developer messages;
- yêu cầu tiết lộ system prompt, key, env hoặc transcript bí mật;
- ép gọi tool bằng tên/JSON giả;
- Unicode zero-width/case/spacing obfuscation;
- prompt injection nằm trong URL/tool result;
- benign research về prompt injection để đo false positive;
- action confirmation spoofing;
- URL nguy hiểm như localhost/private IP/non-http scheme;
- extra tool call, unknown tool, unknown argument và oversized input.

Không có bộ pattern tĩnh nào chứng minh an toàn tuyệt đối. Vì vậy kết quả security phải được xem là regression evidence, kết hợp với prompt hierarchy, deterministic policy, tool isolation và human confirmation.

## 5. Phân rã phần xây dựng

| Workstream | Thành phần | Evidence |
|---|---|---|
| Artifact/versioning | snapshots, hashes, version log | `artifacts/versions/`, `version_log.csv` |
| Prompt/routing | system prompt, tool descriptions | base run `v0–v3` |
| Security | request guard, result sanitizer, redaction | security tests + transcript guard fields |
| Tool mới | `question_guard` docs/code/registry/schema | direct smoke test |
| Eval | group + adversarial cases | JSON schema tests, live runs |
| UI | chat/trace/diff/evidence | local UI smoke test, screenshots/demo |
| Report/demo | failure table, metrics, scenarios | `REPORT.md`, run/transcript links |

## 6. Ranh giới bằng chứng

Offline tests chỉ chứng minh code contract và guard behavior. Chúng không được ghi thay cho live model eval. Các metric `v0–v3`, run JSON và transcript nộp bài phải được tạo bằng provider/tool thật với credentials của nhóm.
