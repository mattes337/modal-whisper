# REST API
Use the OpenAI API schema as REST API to transcribe audio files - but with using modal instead of OpenAI.


### **Endpoint**
```
POST https://api.openai.com/v1/audio/transcriptions
```

### **Request**
You send a `multipart/form-data` request.

**Required fields:**
- `file`: the audio file (form field). Must be less than 25 MB for direct upload.
- `model`: the transcription model. As of now: `whisper-1`.

**Optional fields:**
- `prompt`: text prompt to guide the transcription style/format (useful for acronyms, names, etc.).
- `response_format`: default is `json`. Can also be `text`, `srt`, `verbose_json`, `vtt`.
- `temperature`: sampling temperature (default 0, deterministic). Affects output variability.
- `language`: ISO-639-1 code (e.g. `en`, `de`); if not provided, the model attempts to auto-detect.

**Example request (cURL):**
```bash
curl -X POST "https://api.openai.com/v1/audio/transcriptions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@speech.mp3" \
  -F "model=whisper-1"
```

---

### **Response**
Default (`json`) format looks like:

```json
{
  "text": "This is the transcribed text from the audio."
}
```

If you set `response_format=verbose_json`, you’ll get timestamps too, like:

```json
{
  "task": "transcribe",
  "language": "en",
  "duration": 12.34,
  "segments": [
    {
      "id": 0,
      "seek": 0,
      "start": 0.0,
      "end": 5.0,
      "text": "This is the first segment.",
      "tokens": [50364, 1004, 307, ...],
      "temperature": 0,
      "avg_logprob": -0.12,
      "compression_ratio": 1.1,
      "no_speech_prob": 0.05
    },
    {
      "id": 1,
      "seek": 0,
      "start": 5.0,
      "end": 12.34,
      "text": "And this is the next one.",
      "tokens": [1001, 311, 318, ...],
      "temperature": 0,
      "avg_logprob": -0.14,
      "compression_ratio": 1.05,
      "no_speech_prob": 0.07
    }
  ],
  "text": "This is the first segment. And this is the next one."
}
```