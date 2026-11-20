# Environment

Probed on 2026-11-20 from the build VM with `curl -sS -o /dev/null -w '%{http_code}' -m 10 <url>`.

| Host | Result | Use |
| --- | --- | --- |
| https://pypi.org/pypi/permitcheck/json | 404 | name check: free |
| https://registry.npmjs.org/permitcheck | 404 | name check: free |
| https://pypi.org/pypi/plancheck/json | 404 | backup name check |
| https://registry.npmjs.org/plancheck | 200 | backup name is taken on npm |
| https://huggingface.co | 000 (no connection) | not needed |
| https://api.groq.com/openai/v1/models | 000 (no connection) | record mode: blocked |
| https://openrouter.ai/api/v1/models | 000 (no connection) | record mode: blocked |
| https://api.osv.dev | 000 (no connection) | used pip-audit instead |
| https://semgrep.dev | 000 (no connection) | used `ruff check --select S` instead |

Provider keys in the environment: none (`GROQ_API_KEY` and `OPENROUTER_API_KEY` are unset).

Machine: Intel(R) Xeon(R) Processor @ 2.10GHz, 4 cores, Python 3.13.18 on the VM. CI uses Python 3.11.
