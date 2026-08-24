# Roleplay Dashboard

Streamlit dashboard for monitoring sales Roleplay training performance over
time, built on the "แบบประเมินการทำ Roleplay" Google Form.

Evaluators (Supervisor/Leader, CM, RSD, OM, PBH, RO, GEO Enablement) score a
salesperson on 10 criteria, 1–5 each. The raw total (max 50) is doubled to a
100-point scale; **80% or above is a pass**, per the form's own stated
criterion.

## Pages

- **Overview** — headline KPIs, average score trend over time, and pass rate
  broken down by Channel and Region, plus a queue of rows needing review.
- **All Responses** — the full response table with per-criterion scores,
  mirroring the layout of the original analysis workbook, with a legend
  explaining what each criterion (1.1, 1.2, …) means.

## Data flow

Two live sources in Google Drive, joined on Sale Code:

| Source | Type | Read via | Cache TTL |
| --- | --- | --- | --- |
| Form responses | native Google Sheet | Sheets API | 10 min |
| Org roster (`Mapping_data_*.xlsx`) | uploaded `.xlsx` | Drive download + `openpyxl` | 60 min |

The roster supplies name, Channel, Region, and Province for each Sale Code.
Different TTLs are deliberate: responses arrive continuously, while the roster
changes rarely.

Caching is process-wide, not per-visitor, so all viewers within a TTL window
see the same snapshot and one fetch serves everyone — this keeps the app well
inside Google's free API quotas regardless of viewer count. Refresh is lazy:
the cache only recomputes when a page load happens after the TTL expires. The
header's **Refresh data** button clears the responses and the derived table on
demand (for everyone). It deliberately leaves the roster cached: that download
costs ~1.6s and the roster keeps its own hour-long TTL, so it still refreshes
on the first load after that expires.

## Data quality: Sale Code

Sale Code is a **free-text** field on the form, so a meaningful share of rows
are dirty. `data/transform.py` classifies rather than silently dropping or
mismatching them:

| Class | Example | Handling |
| --- | --- | --- |
| `clean` | `39134159` | Joined directly |
| `extracted_from_text` | `39134585ปิยังกูร สิริโย` | Digits parsed out; the trailing name is cross-checked against the roster as a confidence signal |
| `ambiguous_suffix` | `39129998-2` | **Never auto-matched.** Not a real code — an evaluator's ad hoc way of distinguishing several people assessed under one leader's code in a single session. Unresolvable without asking the evaluator |
| `unparseable` | *(blank)* | Flagged for review |

Anything not `clean`, plus any code absent from the roster, is flagged
`needs_review` and surfaced in the UI instead of being hidden. Charts and KPIs
exclude these rows; the All Responses table still shows them, with the original
raw text preserved so they stay traceable.

The roster also uses placeholder values in its Sale Code column (`0`,
`* รอเบอร์โทร`, `* รอ Thai ID`) to mark staff who are registered but whose
paperwork isn't finalised. These are onboarding status flags, not codes, and
are excluded from the join — `0` alone is shared by several different people,
so joining on it would misattribute scores.

> **Upstream fix worth making:** switching the form's Sale Code field from free
> text to a validated numeric field (or a dropdown sourced from the roster)
> would prevent most of these cases at the source.

## Setup

### 1. Google service account

The app authenticates as a service account — a robot identity, independent of
any individual's Google login, so access doesn't break when staff change roles.

1. In [Google Cloud Console](https://console.cloud.google.com), create a
   project (no billing account needed — Sheets and Drive read access are not
   metered).
2. **APIs & Services → Library**: enable the **Google Sheets API** and
   **Google Drive API**.
3. **IAM & Admin → Service Accounts**: create one. Skip the optional
   project-role and user-access steps — access is granted per file instead.
4. **Keys → Add Key → Create new key → JSON** and download it. This is the only
   copy; treat it like a password.
5. **Share both Drive files** (the responses Sheet and the roster `.xlsx`) with
   the service account's email address as **Viewer**. Enabling the APIs does
   not by itself grant access to any file — this step does.

### 2. Secrets

Create `.streamlit/secrets.toml` (gitignored — never commit it):

```toml
[gcp_service_account]
# paste the downloaded JSON key's fields here
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[ids]
responses_sheet_id = "..."   # from the Sheet's URL: /d/<THIS>/edit
mapping_file_id = "..."      # from the .xlsx file's URL: /d/<THIS>/view

[auth.codes]
# name = "passcode"
# One entry = a single shared password. Many entries = individual codes.
team = "..."
```

Keep the literal `\n` sequences in `private_key` intact — if an editor expands
them into real newlines, the TOML won't parse.

### 3. Run locally

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/streamlit run app.py
```

## Deployment

Deployed on [Streamlit Community Cloud](https://share.streamlit.io) from
`main`, main file `app.py`, Python 3.11.

Paste the same `secrets.toml` contents into the app's **Secrets** box (Advanced
settings on first deploy, or ⋮ → Settings → Secrets afterwards). Secrets can be
edited later without a redeploy. Pushes to `main` redeploy automatically.

## Access control

Viewers are gated by a passcode (`auth.py`) checked against
`[auth.codes]` — deliberately lightweight, not federated identity. Add or
revoke people by editing that table in the deployed app's Secrets; no code
change or redeploy needed.

This is intentionally decoupled from Google: dashboard viewers need **no**
Drive access, because the service account is the only identity that ever reads
the source files.

## Layout

```
app.py              # page shell, view switch, charts, tables
auth.py             # passcode gate
data/
  schema.py         # column layout, labels, criteria text
  ingest.py         # cached Sheets/Drive fetches
  transform.py      # Sale Code classification, roster join, scoring
.streamlit/
  config.toml       # theme
  secrets.toml      # credentials (gitignored)
```

Responses are read **by column position** and renamed immediately to stable
internal names. The form's Thai headers are long and have already drifted
(inconsistent trailing spaces; one is missing its closing parenthesis), so
matching on header text would be brittle. If questions are ever added,
reordered, or removed in the form, `RESPONSE_COLUMNS` in `data/schema.py` is
the one place to update.
