"""识别结果三态。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from albassist.domain.models.ocr_models import OcrResult


class RecognitionStatus(Enum):
    """识别结果状态。"""

    ACCEPTED = "accepted"
    STALE = "stale"
    REJECTED = "rejected"


@dataclass(frozen=True)
class RecognitionOutcome:
    """识别结果 - Accepted/Stale/Rejected 三态。"""

    status: RecognitionStatus
    result: OcrResult | None = None
    reason: str = ""

    @property
    def is_accepted(self) -> bool:
        return self.status == RecognitionStatus.ACCEPTED

    @property
    def is_stale(self) -> bool:
        return self.status == RecognitionStatus.STALE

    @property
    def is_rejected(self) -> bool:
        return self.status == RecognitionStatus.REJECTED