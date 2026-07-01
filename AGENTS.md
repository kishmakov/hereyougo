# AGENTS.md

## Context

- target VM (in Google cloud) can be accessed as `ssh GC`
- `gcloud` is setup on dev machine

### Euler Access

Use this command to access Euler computational cluster from ETH:

`SSHPASS="$SSH_EULER_PASS" sshpass -e ssh EULER

## Secrets

Secrets should not be committed in the repository. They only can be saved in the
bundled Docker image. On dev machine they are stored in environment as follows:

- `HEREYOUGOBOT_PORT` for open port on VM to listen
- `HEREYOUGOBOT_KEY` for Telegram Bot key
- `GC_VM_IP` for static IP of VM
- `GC_PROJECT_ID` for project ID at Google cloud


## Working Guidelines

- Preserve `README.md`.
- Keep repository changes small and intentional.
- Before committing, verify that only expected files are tracked.

