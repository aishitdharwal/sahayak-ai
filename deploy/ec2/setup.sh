#!/bin/bash
# Sahayak AI — EC2 Setup Script
# Run once on a fresh Ubuntu 22.04 t3.medium instance
# sudo bash setup.sh

set -e

echo "=== Sahayak AI EC2 Setup ==="

# System deps
apt-get update -y
apt-get install -y python3.11 python3.11-venv python3-pip nodejs npm nginx git

# App directory
mkdir -p /opt/sahayak
cd /opt/sahayak

# Clone or copy project (adjust to your repo)
# git clone https://github.com/yourorg/sahayak-ai.git .

# Python virtualenv
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# Build React frontend — Nginx will serve it as static files.
# TRADEOFF vs ECS: On EC2 the frontend lives on the same machine.
# Pro: No S3/CloudFront setup. Con: Redeploying frontend = SSH into server.
cd frontend
npm install
npm run build          # outputs to frontend/dist/
cd ..

# Copy env file (student must fill in ANTHROPIC_API_KEY)
cp .env.example .env
echo ">>> Edit /opt/sahayak/.env and add ANTHROPIC_API_KEY before starting"

# Index SOP docs into ChromaDB
# TRADEOFF vs ECS: ChromaDB data lives at /opt/sahayak/chroma_db on disk.
# Safe across reboots. If the instance is replaced you re-run this script.
source venv/bin/activate
cd backend
python -m backend.rag.indexer
cd ..

# Install systemd service and nginx config
cp deploy/ec2/sahayak-backend.service /etc/systemd/system/
cp deploy/ec2/nginx.conf /etc/nginx/sites-available/sahayak
ln -sf /etc/nginx/sites-available/sahayak /etc/nginx/sites-enabled/sahayak
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable sahayak-backend
systemctl start sahayak-backend
systemctl restart nginx

echo "=== Done. Dashboard: http://$(curl -s ifconfig.me) ==="
