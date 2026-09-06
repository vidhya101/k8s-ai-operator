# Voice input for the team

Munder ships a working voice-to-text pipeline: you press the mic button in any
agent's terminal (or in the Command Center composer), speak, and the transcript
lands in the agent's prompt. This doc is the exact setup — three inputs
Munder needs, and one macOS permission.

## What Munder actually uses under the hood

- **Transcription**: [Groq API](https://console.groq.com) running Whisper.
  Chosen because Groq's Whisper endpoint is one of the fastest (~200ms
  latency for short utterances) and has a generous free tier.
- **Recording**: browser MediaRecorder in the Electron renderer — no local
  Whisper install needed.
- **Trigger**: the mic button in `MessageQueueComposer` and the Voice toggle
  in `FullscreenTerminal`. Both hit the same code path.

## Setup — one-time, 5 minutes

### 1. Get a Groq API key (free tier is fine for daily use)

1. Go to <https://console.groq.com>
2. Sign in / sign up (Google SSO works)
3. **API Keys** → **Create API Key** → copy the value (starts with `gsk_…`)

Free tier: ~30 requests/minute on Whisper, no cost for reasonable daily use.
Way more than you'll hit with normal dictation.

### 2. Paste it into Munder's Voice settings

In Munder:
- ⚙️ (bottom-left) → **Settings** → **Voice**
- Paste the key
- Save

Munder stores it in `integration-secrets.json` (encrypted at rest, per
Munder's design). You never enter it again.

### 3. Grant microphone permission (one time, macOS)

The FIRST time you press the mic button, macOS will pop the standard permission
dialog: *"'Electron' would like to access the microphone."* Click **Allow**.

If you accidentally clicked Deny once and it stopped asking:
- System Settings → **Privacy & Security** → **Microphone** → toggle Electron
  (or Munder Difflin if it appears under its own name) to ON
- Restart Munder for the change to take effect

## Using voice

### Michael's terminal (the god / orchestrator)

- Fullscreen his terminal (⛶ in the corner of his card, or click his character
  → **open** → the terminal expands)
- Press the **voice** button (bottom control bar)
- Speak — release / press stop when done
- Munder transcribes → the text lands in Michael's prompt
- Review + hit Enter or edit before submitting

### Any worker's terminal

Same flow — every worker's card has a voice button in its composer.

### Free Flow mode (long-form dictation)

Look for the "Free Flow" toggle in the composer. It lets you speak for a long
stretch without releasing — Munder segments and transcribes as you go. Useful
for dictating a paragraph-length task description to Michael instead of typing.

## Cost + rate limits reality check

- **Free tier**: 30 req/min on Whisper-large-v3. Each mic press = one request
  (regardless of utterance length). You'd have to press 30 times a minute to
  hit it — implausible for normal use.
- **Paid tier**: essentially free at daily-use volumes (~$0.001/minute of
  audio). If Groq raises this later, Munder settings let you swap providers.

## What voice does NOT do

- **Doesn't drive Michael autonomously** — it's dictation. You still hit
  Enter (or say "send" if you've configured a custom shortcut) to submit.
- **Doesn't work when the Munder window is minimized** — Munder needs the
  focus to receive mic input reliably.
- **Doesn't record when the mic light is off** — Munder shows a red dot on
  the mic button while recording. If it's not there, nothing is being
  captured.

## Troubleshooting

- **Mic button greyed out / says "voice: no key"** — you didn't finish step 2.
  Settings → Voice → paste the key.
- **Mic button says "voice: rate-limited"** — free tier's 30 req/min hit.
  Wait a minute or upgrade.
- **Transcription is nonsense** — the mic is likely picking up laptop-fan or
  keyboard noise. Use a headset mic for reliable results.
- **Mic access still asks every launch** — macOS TCC bug; sometimes the
  Electron identity changes between Vite dev launches. `npm run build && npm
  run preview` uses a stable identity — but for dev use, just click Allow.

## Common Pitfalls

- **Leaving the Groq key in the terminal** — after pasting into Munder's
  Settings, clear your shell history or make sure the paste didn't hit any
  scrollback. Groq keys are long-lived; treat them like any other secret.
- **Assuming the transcript is submitted automatically** — it lands in the
  prompt textarea. You still review + press Enter.
- **Using voice for anything security-critical** — dictation is imperfect;
  never dictate a destructive command like a `terraform apply` invocation
  without checking the transcript.
