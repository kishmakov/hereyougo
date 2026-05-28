# AGENTS.md

## Context

- Target VM (in Google cloud) can be accessed as `ssh GC`
- Static IP of VM is stored as `VM_IP`, it should not be commited.
- Telegram Bot key is stored as environment variable `HEREYOUGOBOT_KEY`,
  it should not be commited, it can only be used in the bundled Docker image


## Working Guidelines

- Preserve `README.md`.
- Keep repository changes small and intentional.
- Do not restore the old application files unless explicitly requested.
- Before committing, verify that only expected files are tracked.
