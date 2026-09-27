# Captions and Delivery

Captions are off unless requested. Keep authoritative dialogue, translation decisions, observed speech, and caption rendering separate.

A caption track pins the finished master, declares the final edit clock, exact text, source-line reference, speaker, timing, and delivery mode. Sentence timing does not become word timing by interpolation. ASR output is evidence, not authoritative dialogue.

Use:

```sh
python scripts/caption_track.py check --root PROJECT --plan captions/track.json
python scripts/caption_track.py compile --root PROJECT --plan captions/track.json --format srt --out captions/track.srt
```

Use `delivery_conform.py check` on every final profile. One successful aspect ratio, language, sidecar set, or container does not certify another. Check actual streams, frame rate, frame count, dimensions, audio, and required sidecars.
