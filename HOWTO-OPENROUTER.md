# SSM + OpenRouter (AI Advisory)

## 1. Key (you already registered)
https://openrouter.ai/keys → Create Key → copy sk-or-v1-...
NEVER paste the key into chat or GitHub.

## 2. Windows cmd (project folder)
```text
set OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY
```
(or: set OPENAI_API_KEY=sk-or-v1-YOUR_KEY)

## 3. Config (already set in this build)
config/parameters.json → AI_ADVISORY:
- enabled: true
- provider: openrouter
- endpoint: https://openrouter.ai/api/v1/chat/completions
- model: openrouter/free

If openrouter/free is unavailable, pick a model ending with :free from
https://openrouter.ai/models and put its id into "model".

## 4. Run
```text
python ssm_core.py
```
Then check ssm_unified_report.json field AI_ADVISORY.
Dashboard: python -m streamlit run interface/app.py --server.port 8501

## 5. Disable AI again
Set "enabled": false — radar still works offline.
