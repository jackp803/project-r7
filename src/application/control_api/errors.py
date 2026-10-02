import secrets
from starlette.responses import JSONResponse
from application.control_api.dto import ErrorResponse


class APIError(ValueError):
    def __init__(self, category, reason, status_code, *, terminal=True):
        self.category, self.reason, self.status_code, self.terminal = category, reason, status_code, terminal
        super().__init__(reason)


def error_response(category, reason, status_code):
    body = ErrorResponse(error=dict(category=category, reason_codes=[reason], correlation_id=secrets.token_hex(16)))
    return JSONResponse(body.model_dump(), status_code=status_code)
