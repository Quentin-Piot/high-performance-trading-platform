#!/usr/bin/env bash
set -euo pipefail

# Demo WebSocket Monte Carlo: soumet un job via HTTP et suit la progression via websocat.
# Paramétrable via variables d'environnement. Exemples:
#   BASE_URL=http://localhost:8000/api/v1 RUNS=2000 ./scripts/monte_carlo_ws_demo.sh

BASE_URL="${BASE_URL:-http://localhost:8000/api/v1}"
SYMBOL="${SYMBOL:-aapl}"
RUNS="${RUNS:-2000}"
STRATEGY="${STRATEGY:-sma_crossover}"
SMA_SHORT="${SMA_SHORT:-10}"
SMA_LONG="${SMA_LONG:-20}"
INITIAL_CAPITAL="${INITIAL_CAPITAL:-10000}"
NORMALIZE="${NORMALIZE:-true}"

check_cmd() { command -v "$1" >/dev/null 2>&1; }

if ! check_cmd curl; then
  echo "Erreur: curl est requis" >&2
  exit 1
fi
if ! check_cmd websocat; then
  echo "Erreur: websocat est requis (ex: brew install websocat)" >&2
  exit 1
fi

# Déterminer automatiquement la plage disponible si non fournie
DATE_RANGES_URL="${BASE_URL}/monte-carlo/symbols/date-ranges"
echo "Récupération des plages de dates disponibles pour ${SYMBOL}..."
RANGES_JSON=$(curl -s "$DATE_RANGES_URL")
if check_cmd jq; then
  START_DEFAULT=$(echo "$RANGES_JSON" | jq -r --arg sym "$SYMBOL" '.symbols[] | select((.symbol|ascii_downcase)==($sym|ascii_downcase)) | .min_date' | cut -c1-10)
  END_DEFAULT=$(echo "$RANGES_JSON" | jq -r --arg sym "$SYMBOL" '.symbols[] | select((.symbol|ascii_downcase)==($sym|ascii_downcase)) | .max_date' | cut -c1-10)
else
  START_DEFAULT=$(python3 - "$SYMBOL" <<'PY'
import sys,json
sym=sys.argv[1].lower()
data=json.loads(sys.stdin.read())
for s in data.get('symbols',[]):
    if str(s.get('symbol','')).lower()==sym:
        d=s.get('min_date')
        print(str(d)[:10])
        break
PY
  <<<"$RANGES_JSON")
  END_DEFAULT=$(python3 - "$SYMBOL" <<'PY'
import sys,json
sym=sys.argv[1].lower()
data=json.loads(sys.stdin.read())
for s in data.get('symbols',[]):
    if str(s.get('symbol','')).lower()==sym:
        d=s.get('max_date')
        print(str(d)[:10])
        break
PY
  <<<"$RANGES_JSON")
fi
if [[ -z "${START_DEFAULT}" || -z "${END_DEFAULT}" || "${START_DEFAULT}" == "null" || "${END_DEFAULT}" == "null" ]]; then
  echo "Impossible de déterminer la plage de dates disponible pour ${SYMBOL}. Réponse: ${RANGES_JSON}" >&2
  exit 1
fi
START_DATE="${START_DATE:-$START_DEFAULT}"
END_DATE="${END_DATE:-$END_DEFAULT}"

echo "Soumission du job Monte Carlo (${RUNS} runs) pour ${SYMBOL} (${START_DATE} → ${END_DATE})..."
SUBMIT_URL="${BASE_URL}/monte-carlo/async?symbol=${SYMBOL}&start_date=${START_DATE}&end_date=${END_DATE}&num_runs=${RUNS}&initial_capital=${INITIAL_CAPITAL}&strategy=${STRATEGY}&sma_short=${SMA_SHORT}&sma_long=${SMA_LONG}&normalize=${NORMALIZE}"

SUBMIT_RESP=$(curl -s -X POST "$SUBMIT_URL")
echo "Réponse soumission: $SUBMIT_RESP"

if check_cmd jq; then
  JOB_ID=$(printf "%s" "$SUBMIT_RESP" | jq -r '.job_id')
else
  JOB_ID=$(python3 - <<'PY'
import sys,json
data=json.loads(sys.stdin.read())
print(data.get("job_id",""))
PY
  <<<"$SUBMIT_RESP")
fi

if [[ -z "$JOB_ID" || "$JOB_ID" == "null" ]]; then
  if check_cmd jq; then
    ERR=$(echo "$SUBMIT_RESP" | jq -r '.detail // .message // .error // .status')
  else
    ERR=$(python3 - <<'PY'
import sys,json
data=json.loads(sys.stdin.read())
print(data.get('detail') or data.get('message') or data.get('error') or data.get('status') or '')
PY
    <<<"$SUBMIT_RESP")
  fi
  echo "Soumission échouée: ${ERR}" >&2
  exit 1
fi
echo "Job ID: $JOB_ID"

# Construction de l'URL WebSocket à partir de BASE_URL
WS_BASE="$(echo "$BASE_URL" | sed 's#^http://##; s#^https://##')"
SCHEME="$(echo "$BASE_URL" | sed 's#://.*##')"
WS_SCHEME="ws"
if [[ "$SCHEME" == "https" ]]; then WS_SCHEME="wss"; fi
WS_URL="${WS_SCHEME}://${WS_BASE}/monte-carlo/ws/${JOB_ID}"
echo "Connexion WebSocket: $WS_URL"

if check_cmd jq; then
  # Affichage condensé: statut, progression, timestamps
  websocat -t "$WS_URL" | jq -c '{status, progress, started_at, completed_at, runs}'
else
  websocat -t "$WS_URL"
fi

echo "WebSocket fermé. Récupération du statut final..."
FINAL_STATUS_URL="${BASE_URL}/monte-carlo/async/${JOB_ID}"
if check_cmd jq; then
  curl -s "$FINAL_STATUS_URL" | jq -C
else
  curl -s "$FINAL_STATUS_URL"
fi

echo "Terminé."