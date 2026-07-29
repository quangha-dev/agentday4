from __future__ import annotations

import ipaddress
import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse


MAX_USER_CHARS = 12_000
MAX_TOOL_TEXT_CHARS = 24_000
ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\u2066-\u2069\ufeff]")


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    action: str
    risk_level: str
    categories: list[str]
    reasons: list[str]
    normalized_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_ATTACK_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "instruction_override",
        re.compile(
            r"\b(ignore|disregard|forget|override|bypass)\b.{0,50}\b(previous|prior|above|system|developer|instruction|policy|rule)s?\b"
            r"|\b(bo qua|bỏ qua|phớt lờ|quen di|quên đi|ghi de|ghi đè)\b.{0,50}\b(chi thi|chỉ thị|huong dan|hướng dẫn|system|developer|quy tac|quy tắc)\b",
            re.IGNORECASE,
        ),
        "Attempts to override higher-priority instructions.",
    ),
    (
        "role_spoofing",
        re.compile(
            r"(^|\n)\s*(system|developer|assistant)\s*:\s*|<\/?\s*(system|developer|assistant)\b|\[\s*(system|developer)\s*\]",
            re.IGNORECASE,
        ),
        "Contains role-spoofing markers.",
    ),
    (
        "secret_exfiltration",
        re.compile(
            r"\b(reveal|show|print|dump|exfiltrate|leak|return|read)\b.{0,70}\b(system prompt|developer message|api key|token|credential|secret|environment variable|\.env)\b"
            r"|\b(tiet lo|tiết lộ|in ra|doc|đọc|lay|lấy)\b.{0,70}\b(system prompt|api key|token|credential|bi mat|bí mật|\.env)\b",
            re.IGNORECASE,
        ),
        "Requests protected instructions or secrets.",
    ),
    (
        "tool_coercion",
        re.compile(
            r"\b(force|must|directly|immediately)\b.{0,40}\b(call|invoke|execute|run)\b.{0,30}\b(tool|function)\b"
            r"|TOOL_CALLS_JSON|function_call\s*[:=]|\{\s*[\"']?name[\"']?\s*:\s*[\"']?(send|fetch|lookup)",
            re.IGNORECASE,
        ),
        "Attempts to forge or force a tool call.",
    ),
    (
        "jailbreak",
        re.compile(
            r"\b(jailbreak|developer mode|dan mode|no restrictions|unfiltered mode)\b"
            r"|\b(do anything now|you are now free)\b",
            re.IGNORECASE,
        ),
        "Matches a known jailbreak framing.",
    ),
)

_SECURITY_RESEARCH_RE = re.compile(
    r"\b(prompt injection|jailbreak|security|an toan|an toàn|bao mat|bảo mật)\b",
    re.IGNORECASE,
)
_ANALYSIS_INTENT_RE = re.compile(
    r"\b(explain|analy[sz]e|detect|classify|audit|research|study|what is|phan tich|phân tích|đánh giá|kiem tra|kiểm tra|nghien cuu|nghiên cứu|la gi|là gì)\b",
    re.IGNORECASE,
)
_EXPLICIT_PROMPT_AUDIT_RE = re.compile(
    r"^\s*(?:hãy\s+|vui lòng\s+|please\s+)?(?:audit|classify|detect|analy[sz]e|kiểm tra|kiem tra|phân tích|phan tich|đánh giá)\b.{0,80}\b(?:prompt|chuỗi|chuoi|đoạn|doan|text|nội dung|noi dung)\b",
    re.IGNORECASE,
)

_LEGAL_SCOPE_RE = re.compile(
    r"\b(pháp luật|pháp lý|luật|bộ luật|điều luật|điều\s+\d+|khoản\s+\d+|điểm\s+[a-zđ]|"
    r"nghị định|nghị quyết|thông tư|quyết định|văn bản|hiệu lực|hợp đồng|lao động|doanh nghiệp|"
    r"quyền|nghĩa vụ|trách nhiệm|xử phạt|mức phạt|thủ tục|khiếu nại|tố cáo|thuế|đất đai|"
    r"quy chế|quy định|dữ liệu|lưu trữ|sao lưu|phục hồi|sự cố|kiểm toán|truy cập|MOCK-\d+|"
    r"legal|law|article|clause|regulation|statute|contract)\b",
    re.IGNORECASE,
)
_CAPABILITY_OR_GREETING_RE = re.compile(
    r"^\s*(xin chào|chào|hello|hi|bạn làm được gì|khả năng của bạn|hướng dẫn sử dụng|trợ lý này|hệ thống này|lexflow)",
    re.IGNORECASE,
)
_ADULT_CONTENT_RE = re.compile(
    r"\b(18\+|nội dung người lớn|khiêu dâm|porn|pornography|sex video|ảnh nóng|nude)\b",
    re.IGNORECASE,
)
_SOVEREIGNTY_RE = re.compile(
    r"\b(chủ quyền quốc gia|tranh chấp chủ quyền|hoàng sa|trường sa|biển đông|"
    r"national sovereignty|territorial sovereignty|territorial dispute|south china sea)\b",
    re.IGNORECASE,
)


def normalize_untrusted_text(value: str) -> str:
    """Normalize obfuscation without rewriting the user's semantic content."""
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = ZERO_WIDTH_RE.sub("", normalized)
    normalized = normalized.replace("\x00", "")
    return normalized.strip()


def inspect_request(text: str, *, enforce_scope: bool = True) -> GuardDecision:
    normalized = normalize_untrusted_text(text)
    reasons: list[str] = []
    categories: list[str] = []

    if not normalized:
        return GuardDecision(
            allowed=True,
            action="allow",
            risk_level="low",
            categories=[],
            reasons=[],
            normalized_text=normalized,
        )

    if len(normalized) > MAX_USER_CHARS:
        categories.append("oversized_input")
        reasons.append(f"Input exceeds the {MAX_USER_CHARS}-character safety limit.")

    for category, pattern, reason in _ATTACK_PATTERNS:
        if pattern.search(normalized):
            categories.append(category)
            reasons.append(reason)

    categories = list(dict.fromkeys(categories))
    reasons = list(dict.fromkeys(reasons))

    explicit_prompt_audit = bool(_EXPLICIT_PROMPT_AUDIT_RE.search(normalized))
    is_security_analysis = bool(
        explicit_prompt_audit
        or (
            _SECURITY_RESEARCH_RE.search(normalized)
            and _ANALYSIS_INTENT_RE.search(normalized)
            and "secret_exfiltration" not in categories
            and "tool_coercion" not in categories
        )
    )

    if categories and (enforce_scope or not is_security_analysis):
        return GuardDecision(
            allowed=False,
            action="block_and_explain",
            risk_level="high",
            categories=categories,
            reasons=reasons,
            normalized_text=normalized,
        )
    if categories:
        return GuardDecision(
            allowed=True,
            action="allow_security_analysis",
            risk_level="medium",
            categories=categories,
            reasons=reasons,
            normalized_text=normalized,
        )
    if enforce_scope and _ADULT_CONTENT_RE.search(normalized):
        return GuardDecision(
            allowed=False,
            action="block_adult_content",
            risk_level="high",
            categories=["adult_content"],
            reasons=["Nội dung người lớn nằm ngoài phạm vi của trợ lý pháp luật này."],
            normalized_text=normalized,
        )
    if enforce_scope and _SOVEREIGNTY_RE.search(normalized):
        return GuardDecision(
            allowed=False,
            action="block_sensitive_sovereignty",
            risk_level="high",
            categories=["sensitive_sovereignty"],
            reasons=["Chủ đề chủ quyền quốc gia bị chặn theo chính sách ứng dụng."],
            normalized_text=normalized,
        )
    if enforce_scope and not (
        _LEGAL_SCOPE_RE.search(normalized) or _CAPABILITY_OR_GREETING_RE.search(normalized)
    ):
        return GuardDecision(
            allowed=False,
            action="block_out_of_scope",
            risk_level="low",
            categories=["out_of_scope"],
            reasons=["Câu hỏi không thuộc phạm vi tra cứu văn bản pháp luật."],
            normalized_text=normalized,
        )
    return GuardDecision(
        allowed=True,
        action="allow",
        risk_level="low",
        categories=[],
        reasons=[],
        normalized_text=normalized,
    )


_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:tvly|fc)-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+[^\s,;]+"),
    re.compile(r"(?i)\b(?:api[_ -]?key|token|secret|password)\s*[=:]\s*[^\s,;]+"),
    re.compile(r"https://api\.telegram\.org/bot[^/\s]+", re.IGNORECASE),
)


def redact_secrets(text: str) -> str:
    redacted = str(text)
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted


def redact_for_logging(value: Any, *, _key: str = "") -> Any:
    """Recursively redact secrets while preserving attack text as audit evidence."""
    sensitive_key = _key.lower() in {
        "api_key", "apikey", "authorization", "credential", "credentials",
        "password", "secret", "token", "bot_token",
    }
    if sensitive_key:
        return "[REDACTED_SECRET]"
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, list):
        return [redact_for_logging(item, _key=_key) for item in value]
    if isinstance(value, dict):
        return {str(key): redact_for_logging(item, _key=str(key)) for key, item in value.items()}
    return value


def _neutralize_instruction_lines(text: str) -> str:
    safe_lines: list[str] = []
    for line in redact_secrets(text).splitlines():
        decision = inspect_request(line, enforce_scope=False)
        if not decision.allowed and decision.categories:
            safe_lines.append(
                "[REDACTED_UNTRUSTED_INSTRUCTION: " + ", ".join(decision.categories) + "]"
            )
        else:
            safe_lines.append(line)
    safe = "\n".join(safe_lines)
    if len(safe) > MAX_TOOL_TEXT_CHARS:
        safe = safe[:MAX_TOOL_TEXT_CHARS] + "\n...<truncated_by_security_policy>"
    return safe


def sanitize_tool_result(value: Any, *, _key: str = "") -> Any:
    """Redact secrets and neutralize instruction-like text from untrusted tool data."""
    sensitive_key = _key.lower() in {
        "api_key", "apikey", "authorization", "credential", "credentials",
        "password", "secret", "token", "bot_token",
    }
    if sensitive_key:
        return "[REDACTED_SECRET]"
    if isinstance(value, str):
        return _neutralize_instruction_lines(value)
    if isinstance(value, list):
        return [sanitize_tool_result(item, _key=_key) for item in value[:100]]
    if isinstance(value, dict):
        return {
            str(key): sanitize_tool_result(item, _key=str(key))
            for key, item in list(value.items())[:100]
        }
    return value


def validate_public_http_url(url: str) -> tuple[bool, str | None]:
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return False, "invalid_url"
    if parsed.scheme not in {"http", "https"}:
        return False, "only_http_https_allowed"
    if not parsed.hostname or parsed.username or parsed.password:
        return False, "invalid_or_credentialed_url"

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        return False, "local_hostname_blocked"
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True, None
    if not address.is_global:
        return False, "non_public_ip_blocked"
    return True, None


def blocked_response(decision: GuardDecision) -> str:
    if "out_of_scope" in decision.categories:
        return "Tôi chỉ hỗ trợ tra cứu và đối chiếu văn bản pháp luật trong thư viện LexFlow."
    if "adult_content" in decision.categories:
        return "Tôi không hỗ trợ nội dung 18+ hoặc nội dung người lớn."
    if "sensitive_sovereignty" in decision.categories:
        return "Tôi không trả lời các chủ đề về chủ quyền quốc gia theo chính sách của hệ thống."
    labels = ", ".join(decision.categories) or "unsafe_instruction"
    return (
        "Mình không thể thực hiện chỉ thị này vì nó có dấu hiệu can thiệp vào quy tắc hệ thống "
        f"hoặc truy xuất dữ liệu được bảo vệ ({labels}). Nếu mục tiêu của bạn là nghiên cứu bảo mật, "
        "hãy yêu cầu phân tích nội dung ở dạng dữ liệu, không yêu cầu thực thi chỉ thị đó."
    )


def _matches_json_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    return True


def _validate_schema_value(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    if value is None and schema.get("default", object()) is None:
        return errors
    expected_type = schema.get("type")
    if expected_type and not _matches_json_type(value, expected_type):
        return [f"wrong_type:{path}:{expected_type}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"invalid_enum:{path}")
    if isinstance(value, str):
        minimum = int(schema.get("minLength", 0))
        maximum = min(int(schema.get("maxLength", MAX_USER_CHARS)), MAX_TOOL_TEXT_CHARS)
        if len(value) < minimum:
            errors.append(f"below_min_length:{path}")
        if len(value) > maximum:
            errors.append(f"above_max_length:{path}")
        if schema.get("format") == "date" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            errors.append(f"invalid_date:{path}")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"below_minimum:{path}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"above_maximum:{path}")
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            errors.append(f"below_min_items:{path}")
        if len(value) > int(schema.get("maxItems", 100)):
            errors.append(f"above_max_items:{path}")
        if schema.get("uniqueItems"):
            serialized = [repr(item) for item in value]
            if len(serialized) != len(set(serialized)):
                errors.append(f"duplicate_items:{path}")
        item_schema = schema.get("items") or {}
        for index, item in enumerate(value):
            errors.extend(_validate_schema_value(item, item_schema, f"{path}[{index}]"))
    if isinstance(value, dict):
        properties = schema.get("properties") or {}
        required = schema.get("required") or []
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                errors.append(f"unknown_arguments:{path}:" + ",".join(unknown))
        for key in required:
            if key not in value:
                errors.append(f"missing_required:{path}.{key}")
        for key, child in value.items():
            if key in properties:
                errors.extend(_validate_schema_value(child, properties[key], f"{path}.{key}"))
    return errors


def validate_tool_call(
    name: str,
    args: dict[str, Any],
    declarations: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    """Validate a model-produced call before local implementation execution."""
    declaration: dict[str, Any] | None = None
    for item in declarations:
        function = item.get("function", item)
        if function.get("name") == name:
            declaration = function
            break
    if declaration is None:
        return False, ["tool_not_declared"]
    if not isinstance(args, dict):
        return False, ["arguments_must_be_object"]

    schema = declaration.get("parameters") or {}
    schema = {**schema, "additionalProperties": False}
    errors = _validate_schema_value(args, schema, "args")

    if name == "fetch" and isinstance(args.get("url"), str):
        ok, reason = validate_public_http_url(args["url"])
        if not ok:
            errors.append(f"unsafe_url:{reason}")
    if name == "send" and args.get("confirmed") is not True:
        errors.append("send_requires_explicit_confirmation")

    return not errors, errors


def validate_tool_result(name: str, result: Any) -> tuple[bool, list[str]]:
    """Validate the common ver2 output envelope before returning data to the model."""
    if not isinstance(result, dict):
        return False, ["tool_result_must_be_object"]
    errors: list[str] = []
    if result.get("tool") != name:
        errors.append("tool_result_name_mismatch")
    if not isinstance(result.get("ok"), bool):
        errors.append("tool_result_missing_ok")
    if result.get("contract_version") != "ver2":
        errors.append("tool_result_contract_not_ver2")
    if result.get("ok") is False and not isinstance(result.get("error"), (dict, list)):
        errors.append("tool_error_envelope_missing")
    return not errors, errors
