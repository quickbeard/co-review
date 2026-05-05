#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck source=/dev/null
  set -a
  source "$ENV_FILE"
  set +a
fi

require_bin() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

for bin in curl python3; do
  require_bin "$bin"
done

GRAFANA_BASE_URL="${GRAFANA_BASE_URL:-${DEVLAKE_GRAFANA_ROOT_URL:-http://localhost:30090/grafana}}"
GRAFANA_BASE_URL="${GRAFANA_BASE_URL%/}"
GRAFANA_API_URL="${GRAFANA_BASE_URL}/api"
GRAFANA_USER="${DEVLAKE_GRAFANA_ADMIN_USER:-admin}"
GRAFANA_PASSWORD="${DEVLAKE_GRAFANA_ADMIN_PASSWORD:-admin}"

if [[ -z "$GRAFANA_USER" || -z "$GRAFANA_PASSWORD" ]]; then
  echo "Grafana admin credentials are required (DEVLAKE_GRAFANA_ADMIN_USER / DEVLAKE_GRAFANA_ADMIN_PASSWORD)." >&2
  exit 1
fi

request() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  local url="${GRAFANA_API_URL}${path}"

  if [[ -n "$data" ]]; then
    curl -fsS -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
      -H "Content-Type: application/json" \
      -X "$method" \
      "$url" \
      --data "$data"
    return
  fi

  curl -fsS -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" -H "Content-Type: application/json" -X "$method" "$url"
}

echo "Waiting for Grafana API at ${GRAFANA_API_URL}/health ..."
for attempt in $(seq 1 30); do
  if request GET "/health" >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    echo "Grafana API is not ready after 30 attempts." >&2
    exit 1
  fi
  sleep 2
done
echo "Grafana API is ready."

FOLDER_TITLE="CoReview Dashboards"
FOLDERS_JSON="$(request GET "/folders?limit=1000")"
FOLDER_UID="$(
  JSON_INPUT="$FOLDERS_JSON" python3 - "$FOLDER_TITLE" <<'PY'
import json
import os
import sys

folders = json.loads(os.environ.get("JSON_INPUT", "[]"))
target = sys.argv[1].strip().lower()
for folder in folders:
    title = str(folder.get("title", "")).strip().lower()
    if title == target:
        print(folder.get("uid", ""))
        break
PY
)"

if [[ -z "$FOLDER_UID" ]]; then
  echo "Creating Grafana folder: ${FOLDER_TITLE}"
  CREATE_FOLDER_PAYLOAD="$(python3 - "$FOLDER_TITLE" <<'PY'
import json
import sys

print(json.dumps({"title": sys.argv[1]}))
PY
)"
  CREATE_FOLDER_RESPONSE="$(request POST "/folders" "$CREATE_FOLDER_PAYLOAD")"
  FOLDER_UID="$(
    JSON_INPUT="$CREATE_FOLDER_RESPONSE" python3 - <<'PY'
import json
import os

print(json.loads(os.environ.get("JSON_INPUT", "{}")).get("uid", ""))
PY
)"
  if [[ -z "$FOLDER_UID" ]]; then
    echo "Failed to create or resolve Grafana folder UID." >&2
    exit 1
  fi
fi

pick_source_dashboard_uid() {
  local provider="$1"
  local search_json="$2"

  JSON_INPUT="$search_json" python3 - "$provider" <<'PY'
import json
import os
import sys

provider = sys.argv[1]
rows = json.loads(os.environ.get("JSON_INPUT", "[]"))

provider_markers = {
    "github": ["github"],
    "gitlab": ["gitlab"],
    "azure_devops": ["azure devops", "azuredevops", "azure_devops", "azure"],
}

def score(row):
    title = str(row.get("title", "")).lower()
    uri = str(row.get("uri", "")).lower()
    text = f"{title} {uri}"
    if "devlake" not in text:
        return -1
    markers = provider_markers[provider]
    if not any(marker in text for marker in markers):
        return -1
    points = 0
    if "coreview" not in text:
        points += 4
    if "default" in text or "builtin" in text or "built-in" in text:
        points += 2
    if "overview" in text or "lead time" in text:
        points += 1
    return points

candidates = []
for row in rows:
    uid = row.get("uid")
    if not uid:
        continue
    points = score(row)
    if points >= 0:
        candidates.append((points, uid))

candidates.sort(key=lambda item: item[0], reverse=True)
if candidates:
    print(candidates[0][1])
PY
}

duplicate_dashboard() {
  local provider="$1"
  local source_uid="$2"
  local target_title="$3"
  local target_uid="$4"

  local dashboard_json
  dashboard_json="$(request GET "/dashboards/uid/${source_uid}")"

  local payload
  payload="$(
    JSON_INPUT="$dashboard_json" python3 - "$target_title" "$target_uid" "$provider" "$FOLDER_UID" <<'PY'
import json
import os
import sys

data = json.loads(os.environ.get("JSON_INPUT", "{}"))
target_title = sys.argv[1]
target_uid = sys.argv[2]
provider = sys.argv[3]
folder_uid = sys.argv[4]

dashboard = data.get("dashboard") or {}
dashboard["id"] = None
dashboard["uid"] = target_uid
dashboard["title"] = target_title
dashboard["version"] = 0

tags = list(dashboard.get("tags") or [])
for tag in ["coreview", "devlake", provider]:
    if tag not in tags:
        tags.append(tag)
dashboard["tags"] = tags

payload = {
    "dashboard": dashboard,
    "folderUid": folder_uid,
    "overwrite": True,
    "message": "CoReview bootstrap: duplicate built-in DevLake dashboard for embedding",
}
print(json.dumps(payload))
PY
  )"

  request POST "/dashboards/db" "$payload"
}

SEARCH_JSON="$(request GET "/search?type=dash-db&limit=500")"

declare -A PROVIDER_LABELS=(
  [github]="GitHub"
  [gitlab]="GitLab"
  [azure_devops]="Azure DevOps"
)

declare -A SOURCE_UIDS
declare -A TARGET_UIDS=(
  [github]="coreview-github"
  [gitlab]="coreview-gitlab"
  [azure_devops]="coreview-azuredevops"
)

for provider in github gitlab azure_devops; do
  uid="$(pick_source_dashboard_uid "$provider" "$SEARCH_JSON")"
  if [[ -z "$uid" ]]; then
    echo "Could not find built-in DevLake dashboard for provider: $provider" >&2
    exit 1
  fi
  SOURCE_UIDS["$provider"]="$uid"
done

echo "Duplicating dashboards into folder '${FOLDER_TITLE}' ..."
for provider in github gitlab azure_devops; do
  title="CoReview DevLake ${PROVIDER_LABELS[$provider]}"
  target_uid="${TARGET_UIDS[$provider]}"
  source_uid="${SOURCE_UIDS[$provider]}"

  response="$(duplicate_dashboard "$provider" "$source_uid" "$title" "$target_uid")"
  saved_uid="$(
    JSON_INPUT="$response" python3 - <<'PY'
import json
import os

print(json.loads(os.environ.get("JSON_INPUT", "{}")).get("uid", ""))
PY
  )"
  if [[ -z "$saved_uid" ]]; then
    echo "Failed to duplicate dashboard for ${provider}." >&2
    exit 1
  fi
  TARGET_UIDS["$provider"]="$saved_uid"
  echo "  - ${provider}: source=${source_uid} target=${saved_uid}"
done

echo ""
echo "Copy these values into your .env file:"
echo "NEXT_PUBLIC_DEVLAKE_GRAFANA_BASE_URL=${GRAFANA_BASE_URL}"
echo "NEXT_PUBLIC_DEVLAKE_GRAFANA_DASHBOARD_UID_MAP=github:${TARGET_UIDS[github]},gitlab:${TARGET_UIDS[gitlab]},azure_devops:${TARGET_UIDS[azure_devops]}"
echo ""
echo "Optional direct links:"
echo "GitHub:      ${GRAFANA_BASE_URL}/d/${TARGET_UIDS[github]}?orgId=1&kiosk&theme=light"
echo "GitLab:      ${GRAFANA_BASE_URL}/d/${TARGET_UIDS[gitlab]}?orgId=1&kiosk&theme=light"
echo "AzureDevOps: ${GRAFANA_BASE_URL}/d/${TARGET_UIDS[azure_devops]}?orgId=1&kiosk&theme=light"
