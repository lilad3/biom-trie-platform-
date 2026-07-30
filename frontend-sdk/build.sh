#!/usr/bin/env bash
# Concatène les fichiers de src/ en un seul fichier dist/biometric-sdk.js,
# pour un usage <script> simple sans étape de bundling côté intégrateur.
set -euo pipefail

cd "$(dirname "$0")"

mkdir -p dist

{
  echo "/*!"
  echo " * biometric-platform frontend-sdk"
  echo " * Fichier généré automatiquement par build.sh — ne pas éditer directement."
  echo " * Éditer les fichiers sous src/ puis relancer ./build.sh"
  echo " */"
  cat src/biometric-scanner.js
  echo ""
  cat src/biometric-client.js
} > dist/biometric-sdk.js

echo "OK : dist/biometric-sdk.js généré ($(wc -l < dist/biometric-sdk.js) lignes)"
