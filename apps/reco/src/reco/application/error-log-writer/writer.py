"""MOD-RECO-029 Error Log Writer implementation."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.application.reco_error_handler.models import ErrorLogWriteRequest
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID
from .mapper import map_write_request_to_record
from .ports import ErrorLogRepository
from .repository import InMemoryErrorLogRepository
from .validation import validate_write_request


@dataclass
class ErrorLogWriter:
    """ErrorLogWriterPort implementation for MOD-RECO-029."""

    repository: ErrorLogRepository = field(default_factory=InMemoryErrorLogRepository)
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID

    def write(self, request: ErrorLogWriteRequest) -> None:
        validate_write_request(request)
        record = map_write_request_to_record(request)
        error_log_id = self.repository.insert(record)

        self.logger.bind(trace_id=request.trace_id).info(
            "error_log_inserted",
            module_id=self.module_id,
            error_log_id=error_log_id,
            error_code=request.error_code,
            owner_type=request.owner_type,
            owner_id=request.owner_id,
        )


def build_default_error_log_writer() -> ErrorLogWriter:
    return ErrorLogWriter()
