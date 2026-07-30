#!/usr/bin/env bash
# Lanceur Bureau pour etacomp-backup (journalise les erreurs de démarrage).
set -u

INSTALL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_BIN="${INSTALL_DIR}/.venv/bin/etacomp-backup"
LOG="${HOME}/.local/share/etacomp-backup.log"

mkdir -p "$(dirname "$LOG")"
{
  echo "=== $(date -Iseconds) ==="
  echo "cwd=$(pwd)"
  echo "exec=${VENV_BIN}"
  cd "${INSTALL_DIR}" || exit 1
  if [[ ! -x "${VENV_BIN}" ]]; then
    echo "ERREUR: binaire introuvable ${VENV_BIN}"
    exit 1
  fi
  exec "${VENV_BIN}"
} >>"${LOG}" 2>&1
