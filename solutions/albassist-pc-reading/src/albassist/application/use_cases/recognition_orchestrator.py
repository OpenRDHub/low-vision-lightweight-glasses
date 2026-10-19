"""识别用例与过期校验。

前置校验 → 调用引擎 → 四元组校验 → Accepted/Stale/Rejected。
"""

from __future__ import annotations

from typing import Callable

from albassist.application.ports.ocr_engine import IOcrEngine
from albassist.application.use_cases.recognition_outcome import (
    RecognitionOutcome,
    RecognitionStatus,
)
from albassist.domain.exceptions import ImageFrameValidationError
from albassist.domain.models.ocr_models import RecognitionRequest, SessionIdentity


class RecognitionOrchestrator:
    """识别编排器。

    结果提交前验证 SessionId + RequestId + FrameId + FrameRevision
    与当前会话一致；新材料替换、重新冻结或 ROI 变更都会使旧任务失效。
    """

    def __init__(self, ocr_engine: IOcrEngine) -> None:
        self._engine = ocr_engine

    async def recognize_async(
        self,
        request: RecognitionRequest,
        get_current_identity: Callable[[], SessionIdentity],
        cancel_token: object | None = None,
    ) -> RecognitionOutcome:
        """执行识别流程。

        Args:
            request: 识别请求。
            get_current_identity: 获取当前会话标识的回调（不缓存，并发安全）。
            cancel_token: 取消令牌。

        Returns:
            RecognitionOutcome: Accepted（结果有效）、Stale（过期丢弃）、Rejected（前置失败）。
        """
        try:
            request.image.validate()
        except ImageFrameValidationError as e:
            return RecognitionOutcome(
                status=RecognitionStatus.REJECTED, reason=f"图像校验失败: {e}"
            )

        if request.frame_id != request.image.frame_id:
            return RecognitionOutcome(
                status=RecognitionStatus.REJECTED,
                reason=f"frame_id 不匹配: request={request.frame_id} image={request.image.frame_id}",
            )

        result = await self._engine.recognize_async(request, cancel_token)

        current = get_current_identity()
        if (
            result.session_id == current.session_id
            and result.request_id == current.request_id
            and result.frame_id == current.frame_id
            and result.frame_revision == current.frame_revision
        ):
            return RecognitionOutcome(status=RecognitionStatus.ACCEPTED, result=result)

        return RecognitionOutcome(
            status=RecognitionStatus.STALE,
            reason=(
                f"过期结果丢弃: result=({result.session_id[:8]}..., "
                f"{result.frame_id[:8]}..., rev={result.frame_revision}) "
                f"current=({current.session_id[:8]}..., "
                f"{current.frame_id[:8]}..., rev={current.frame_revision})"
            ),
        )