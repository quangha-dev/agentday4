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


def normalize_untrusted_text(value: str) -> str:
    """Normalize obfuscation without rewriting the user's semantic content."""
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = ZERO_WIDTH_RE.sub("", normalized)
    normalized = normalized.replace("\x00", "")
    return normalized.strip()


def inspect_request(text: str) -> GuardDecision:
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

    if categories and not is_security_analysis:
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
        decision = inspect_request(line)
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
    properties = schema.get("properties") or {}
    required = schema.get("required") or []
    errors: list[str] = []

    unknown = sorted(set(args) - set(properties))
    if unknown:
        errors.append("unknown_arguments:" + ",".join(unknown))
    for key in required:
        if key not in args:
            errors.append(f"missing_required:{key}")
    for key, value in args.items():
        prop = properties.get(key)
        if not prop:
            continue
        expected_type = prop.get("type")
        if expected_type and not _matches_json_type(value, expected_type):
            errors.append(f"wrong_type:{key}:{expected_type}")
            continue
        if "enum" in prop and value not in prop["enum"]:
            errors.append(f"invalid_enum:{key}")
        if isinstance(value, int) and not isinstance(value, bool):
            if "minimum" in prop and value < prop["minimum"]:
                errors.append(f"below_minimum:{key}")
            if "maximum" in prop and value > prop["maximum"]:
                errors.append(f"above_maximum:{key}")
        if isinstance(value, str) and len(value) > 8_000:
            errors.append(f"argument_too_long:{key}")

    if name == "fetch" and isinstance(args.get("url"), str):
        ok, reason = validate_public_http_url(args["url"])
        if not ok:
            errors.append(f"unsafe_url:{reason}")
    if name == "send" and args.get("confirmed") is not True:
        errors.append("send_requires_explicit_confirmation")

    return not errors, errors
