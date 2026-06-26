#!/bin/bash
# Quick redeploy on EC2 after a code push
# TRADEOFF vs ECS: On ECS, a new image push triggers a rolling deploy automatically.
# On EC2, you SSH in and run this script. Simple, but manual.

set -e
cd /opt/sahayak

git pull origin main

source venv/bin/activate
pip install -r backend/requirements.txt --quiet

# Rebuild frontend only if src changed
if git diff HEAD@{1} HEAD --name-only | grep -q "^frontend/"; then
    cd frontend && npm install && npm run build && cd ..
    echo "Frontend rebuilt."
fi

systemctl restart sahayak-backend
echo "Backend restarted. Tail logs: journalctl -u sahayak-backend -f"
