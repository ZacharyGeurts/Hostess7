# NEXUS Panel i18n

| Path | Purpose |
|------|---------|
| `languages.json` | 99 imported locales — American English first in UI, then alphabetical |
| `country-locales.json` | Egress IP country → default locale |
| `messages/en-US.json` | Base string catalog |
| `messages/{code}.json` | Per-locale overrides (fallback to en-US) |

Runtime preference: `/var/lib/nexus-shield/panel-language.json`

API: `GET/POST /api/panel-language`

Detection runs only when the operator has not set or changed language yet (`user_set` / `source: user`).