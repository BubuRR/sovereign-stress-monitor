# SSM + Groq (AI Advisory)

## 1. Get a free key
1. Open https://console.groq.com
2. Sign up / log in
3. API Keys → Create API Key
4. Copy the key (shown once)

## 2. Windows (cmd in project folder)
```text
set GROQ_API_KEY=gsk_your_key_here
```

## 3. Enable in config/parameters.json
```json
"AI_ADVISORY": {
  "enabled": true,
  "provider": "groq",
  "endpoint": "https://api.groq.com/openai/v1/chat/completions",
  "model": "llama-3.3-70b-versatile",
  "mode": "compare",
  "never_override_scores": true,
  "max_tokens": 800
}
```

## 4. Run
```text
python ssm_core.py
```
Check ssm_unified_report.json → AI_ADVISORY (text or soft error).
Core G/S/Land/Gap never change.

## 5. If model name fails
Open https://console.groq.com/docs/models and put a current chat model id into "model".

## Security
Do not paste the key into chat or GitHub. Revoke if leaked.
