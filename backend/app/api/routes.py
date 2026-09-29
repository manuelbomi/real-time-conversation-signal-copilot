"""HTTP + WebSocket routes.

`POST /sessions` creates a session (a fresh bounded conversation-context
window). `WS /ws/sessions/{id}` is the live event stream: the client sends
`UtteranceIn` JSON frames as the conversation happens, and receives
`signal` / `recommendation` / `guardrail_block` / `error` events back as
they're produced. See `app/api/pipeline.py` for what happens in between.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.api.pipeline import now, process_utterance
from app.api.schemas import CreateSessionResponse, ErrorEvent, UtteranceIn
from app.config import settings
from app.context import ConversationContext

router = APIRouter()


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: Request) -> CreateSessionResponse:
    session_id = str(uuid.uuid4())
    request.app.state.copilot.sessions[session_id] = ConversationContext(
        max_turns=settings.context_window_turns
    )
    return CreateSessionResponse(session_id=session_id)


@router.websocket("/ws/sessions/{session_id}")
async def session_stream(websocket: WebSocket, session_id: str) -> None:
    state = websocket.app.state.copilot
    context = state.sessions.get(session_id)
    if context is None:
        # Auto-create rather than reject: convenient for the demo/replay
        # script, and harmless since sessions are just in-memory context
        # windows here. A production deployment would reject unknown
        # session ids once sessions are backed by real auth + persistence.
        context = ConversationContext(max_turns=settings.context_window_turns)
        state.sessions[session_id] = context

    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                utterance = UtteranceIn.model_validate_json(raw)
            except ValidationError as exc:
                await websocket.send_text(ErrorEvent(detail=str(exc)).model_dump_json())
                continue

            if not utterance.is_final:
                continue  # interim ASR partials are not classified, see schemas.py

            async for event in process_utterance(
                speaker=utterance.speaker,
                text=utterance.text,
                ts=utterance.ts or now(),
                context=context,
                detector=state.detector,
                recommender=state.recommender,
                guardrail=state.guardrail,
            ):
                await websocket.send_text(event.model_dump_json())
    except WebSocketDisconnect:
        return
