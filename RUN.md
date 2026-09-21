```bash
cd SSM-v30.5
pip install -r requirements.txt && pytest -q && python ssm_core.py
```
Optional keys: edit `config/parameters.json` → `API_KEYS_VAULT`.

## GitHub Release (auto)

```bash
git tag v30.5.2
git push origin v30.5.2
```

Workflow `.github/workflows/release.yml` runs tests and creates a Release with source zip.
