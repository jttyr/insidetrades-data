#!/bin/bash
# Crea el repo publico insidetrades-data en tu GitHub, sube esta carpeta y lanza la primera corrida.
set -e
cd "$(dirname "$0")"
rm -rf __pycache__ alpha_terminal/__pycache__
printf "__pycache__/\n*.pyc\n" > .gitignore
[ -d .git ] || git init -q -b main
git add -A
git -c user.name="insidetrades-bot" -c user.email="bot@users.noreply.github.com" commit -q -m "insidetrades data pipeline" || true
USER_GH=$(gh api user --jq .login)
gh repo create insidetrades-data --public --source=. --push
gh workflow run insidetrades-data.yml || true
echo
echo "LISTO. Pega esta URL en InpDataURL del EA:"
echo "https://raw.githubusercontent.com/$USER_GH/insidetrades-data/main/data/"
