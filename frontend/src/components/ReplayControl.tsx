import { useState } from "react";
import { SAMPLE_TRANSCRIPT } from "../data/sampleTranscript";

interface Props {
  connected: boolean;
  onSend: (speaker: string, text: string, ts: number) => void;
}

export function ReplayControl({ connected, onSend }: Props) {
  const [playing, setPlaying] = useState(false);

  async function play() {
    setPlaying(true);
    for (const turn of SAMPLE_TRANSCRIPT) {
      await sleep(turn.delayMs);
      onSend(turn.speaker, turn.text, Date.now() / 1000);
    }
    setPlaying(false);
  }

  return (
    <button onClick={play} disabled={!connected || playing} data-testid="replay-button">
      {playing ? "Replaying..." : "Replay a sample call"}
    </button>
  );
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
