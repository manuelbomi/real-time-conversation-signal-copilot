#!/usr/bin/env python
"""Replay a JSONL transcript over the WebSocket API at a realistic pace.

There's no live telephony/ASR wired into this repo (see the companion
streaming-asr-diarization-pipeline repo, which emits the same
`{speaker, text, ts, is_final}` event shape this endpoint expects) -- this
script is the stand-in that lets you see the full pipeline run end-to-end
against the demo knowledge base without any audio hardware.

Usage:
    python scripts/replay_transcript.py [path/to/transcript.jsonl] [--url ws://localhost:8000]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx
import websockets


async def replay(transcript_path: Path, base_http_url: str, base_ws_url: str) -> None:
    lines = [json.loads(line) for line in transcript_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    async with httpx.AsyncClient(base_url=base_http_url) as client:
        response = await client.post("/sessions")
        response.raise_for_status()
        session_id = response.json()["session_id"]
    print(f"session_id={session_id}")

    uri = f"{base_ws_url}/ws/sessions/{session_id}"
    async with websockets.connect(uri) as ws:
        async def send_turns() -> None:
            for entry in lines:
                await asyncio.sleep(entry.get("delay_s", 1.0))
                payload = {
                    "speaker": entry["speaker"],
                    "text": entry["text"],
                    "ts": time.time(),
                    "is_final": True,
                }
                print(f">> {entry['speaker']}: {entry['text']}")
                await ws.send(json.dumps(payload))
            await asyncio.sleep(2.0)  # give the last utterance time to finish processing

        async def receive_events() -> None:
            try:
                async for raw in ws:
                    event = json.loads(raw)
                    print(f"<< [{event['type']}] {json.dumps(event, indent=None)}")
            except websockets.ConnectionClosed:
                return

        sender = asyncio.create_task(send_turns())
        receiver = asyncio.create_task(receive_events())
        await sender
        receiver.cancel()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "transcript",
        nargs="?",
        default=str(Path(__file__).parent / "sample_transcript.jsonl"),
        type=Path,
    )
    parser.add_argument("--http-url", default="http://localhost:8000")
    parser.add_argument("--ws-url", default="ws://localhost:8000")
    args = parser.parse_args()
    asyncio.run(replay(Path(args.transcript), args.http_url, args.ws_url))


if __name__ == "__main__":
    main()
