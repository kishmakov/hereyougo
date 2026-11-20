#!/usr/bin/env bash
set -euo pipefail

: "${SSH_EULER_PASS:?SSH_EULER_PASS is not set}"
: "${HEREYOUGO_VM_IP:?HEREYOUGO_VM_IP is not set}"
: "${HEREYOUGO_BOT_PORT:?HEREYOUGO_BOT_PORT is not set}"
: "${HEREYOUGO_USER_ID:?HEREYOUGO_USER_ID is not set}"

EULER_SSH_TARGET="${EULER_SSH_TARGET:-EULER}"
BOT_SERVICE_URL="http://${HEREYOUGO_VM_IP}:${HEREYOUGO_BOT_PORT}/notify"
MESSAGE="HereYouGo Euler SLURM test completed"
SLURM_TEST_SLEEP_SECONDS="3"

printf -v bot_url_q "%q" "${BOT_SERVICE_URL}"
printf -v message_q "%q" "${MESSAGE}"
printf -v notify_token_q "%q" "${NOTIFY_TOKEN:-}"
printf -v user_id_q "%q" "${HEREYOUGO_USER_ID}"
printf -v sleep_seconds_q "%q" "${SLURM_TEST_SLEEP_SECONDS}"


job_id="$(
  {
    cat <<SLURM
#!/usr/bin/env bash
#SBATCH --job-name=hereyougo-bot-test
#SBATCH --time=00:02:00
#SBATCH --mem-per-cpu=128M
#SBATCH --cpus-per-task=1
#SBATCH --output=hereyougo-bot-test-%j.out

set -euo pipefail

BOT_SERVICE_URL=${bot_url_q}
MESSAGE=${message_q}
NOTIFY_TOKEN=${notify_token_q}
HEREYOUGO_USER_ID=${user_id_q}
SLURM_TEST_SLEEP_SECONDS=${sleep_seconds_q}

job_started_at="\$(date +%s)"
sleep "\${SLURM_TEST_SLEEP_SECONDS}"

completed_at="\$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
job_finished_at="\$(date +%s)"
job_elapsed_seconds="\$((job_finished_at - job_started_at))"
host="\$(hostname)"
text="\${MESSAGE} in \${job_elapsed_seconds}s on Euler host \${host} as SLURM job \${SLURM_JOB_ID:-unknown} at \${completed_at}"

curl_args=(
  --fail-with-body
  --connect-timeout 10
  --max-time 30
  -sS
  -X POST
  "\${BOT_SERVICE_URL}"
  -H "Content-Type: text/plain"
  -H "X-HereYouGo-User-ID: \${HEREYOUGO_USER_ID}"
  --data-binary @-
)

if [[ -n "\${NOTIFY_TOKEN}" ]]; then
  curl_args+=(-H "Authorization: Bearer \${NOTIFY_TOKEN}")
fi

printf -v curl_command "%q " curl "\${curl_args[@]}"
printf "%s" "\${text}" | ssh -o BatchMode=yes -o ConnectTimeout=10 "\${SLURM_SUBMIT_HOST}" "\${curl_command}"
printf "\\n"
SLURM
  } | SSHPASS="${SSH_EULER_PASS}" sshpass -e ssh "${EULER_SSH_TARGET}" "sbatch --parsable"
)"

echo "Submitted Euler SLURM job ${job_id}"
echo "Output file on Euler: hereyougo-bot-test-${job_id}.out"
