from uuid import UUID

from openai import AsyncOpenAI

from app.core.llm.base import Message
from app.services.audit_log_service import AuditLogService


class OpenAILLMProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        audit_log: AuditLogService | None = None,
        session_id: UUID | None = None,
        user_id: int | None = None,
        turn_id: UUID | None = None,
    ) -> str:
        payload = [
            {"role": message.role, "content": message.content} for message in messages
        ]
        self._audit_info(
            audit_log,
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type="agent_request",
            message="LLM request",
            data={
                "model": self._model,
                "temperature": temperature,
                "message_count": len(messages),
                "messages": payload,
            },
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=payload,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("OpenAI returned an empty response")

        self._audit_info(
            audit_log,
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type="agent_response",
            message="LLM response",
            data={"model": self._model, "content": content},
        )

        if response.usage is not None:
            self._audit_info(
                audit_log,
                session_id=session_id,
                user_id=user_id,
                turn_id=turn_id,
                type="token_usage",
                message="LLM token usage",
                data={
                    "model": self._model,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            )

        return content

    def _audit_info(
        self,
        audit_log: AuditLogService | None,
        *,
        session_id: UUID | None,
        user_id: int | None,
        turn_id: UUID | None,
        type: str,
        message: str,
        data: dict,
    ) -> None:
        if (
            audit_log is None
            or session_id is None
            or user_id is None
            or turn_id is None
        ):
            return

        audit_log.info(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type=type,
            message=message,
            data=data,
        )
