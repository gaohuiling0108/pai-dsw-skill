"""
PAI-DSW Skill Unified Exceptions

Custom exception hierarchy for structured error handling across
CLI commands, MCP tools, and programmatic API access.
"""


class DSWError(Exception):
    """Base exception for all DSW operations.

    Attributes:
        message: Human-readable error description.
        code: Machine-readable error code for programmatic handling.
        details: Optional dict with structured context (instance_id, matches, etc.).
    """

    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code or "DSW_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON responses (MCP, API)."""
        result = {
            "error": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


# --- Instance errors ---

class InstanceNotFoundError(DSWError):
    """No instance matched the given identifier."""

    def __init__(self, identifier: str):
        super().__init__(
            message=f"未找到名称包含 '{identifier}' 的实例",
            code="INSTANCE_NOT_FOUND",
            details={"identifier": identifier},
        )


class InstanceAmbiguousError(DSWError):
    """Multiple instances matched the given identifier."""

    def __init__(self, identifier: str, matches: list):
        super().__init__(
            message=f"找到多个匹配的实例: '{identifier}'",
            code="INSTANCE_AMBIGUOUS",
            details={"identifier": identifier, "matches": matches},
        )


class InstanceStateError(DSWError):
    """Instance is in a state that does not allow the requested operation."""

    def __init__(self, instance_id: str, current_status: str, required_status: str):
        super().__init__(
            message=f"实例 {instance_id} 当前状态为 {current_status}，需要 {required_status}",
            code="INSTANCE_STATE_ERROR",
            details={
                "instance_id": instance_id,
                "current_status": current_status,
                "required_status": required_status,
            },
        )


# --- Credential / config errors ---

class CredentialError(DSWError):
    """Failed to obtain valid credentials."""

    def __init__(self, message: str = "未找到有效的阿里云凭证"):
        super().__init__(message=message, code="CREDENTIAL_ERROR")


class WorkspaceNotSetError(DSWError):
    """Workspace ID is required but not configured."""

    def __init__(self):
        super().__init__(
            message="需要设置工作空间 ID (PAI_WORKSPACE_ID)",
            code="WORKSPACE_NOT_SET",
        )


class ConfigError(DSWError):
    """Configuration read/write error."""

    def __init__(self, message: str):
        super().__init__(message=message, code="CONFIG_ERROR")


# --- API errors ---

class APIError(DSWError):
    """Remote API call failed."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(
            message=message,
            code="API_ERROR",
            details={"status_code": status_code} if status_code else {},
        )


class RateLimitError(APIError):
    """API request was throttled."""

    def __init__(self, retry_after: int = None):
        super().__init__(
            message="API 请求被限流",
            status_code=429,
        )
        self.code = "RATE_LIMITED"
        if retry_after:
            self.details["retry_after"] = retry_after


# --- Validation errors ---

class ValidationError(DSWError):
    """Input parameter validation failed."""

    def __init__(self, message: str, field: str = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field} if field else {},
        )
