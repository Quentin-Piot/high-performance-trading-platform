#!/usr/bin/env bash
set -euo pipefail

SSH_KEY_PATH="${HOME}/.ssh/terraform-dev.pem"
SSH_USER="ec2-user"
PROJECT_NAME="trading-platform"
REMOTE_DIR="/home/ec2-user/${PROJECT_NAME}"
FRONTEND_IMAGE="trading-platform_frontend"
BACKEND_IMAGE="trading-platform_backend"

# récupère ip depuis terraform
pushd terraform > /dev/null
INSTANCE_IP=$(terraform output -raw instance_public_ip 2>/dev/null || true)
popd > /dev/null

if [[ -z "$INSTANCE_IP" ]]; then
  echo "ERROR: cannot find instance_public_ip from terraform. Run 'terraform apply' first."
  exit 1
fi

echo "Deploy -> ${INSTANCE_IP}"

# build local images
echo "Building images locally..."
docker-compose build --parallel

# export images
echo "Exporting images..."
docker save "$FRONTEND_IMAGE" | gzip > /tmp/frontend.tar.gz
docker save "$BACKEND_IMAGE"  | gzip > /tmp/backend.tar.gz

# build package (only docker-compose + envs)
PACKAGE_LOCAL="/tmp/${PROJECT_NAME}_package.tar.gz"
tar -czf "$PACKAGE_LOCAL" \
  docker-compose.yml \
  web/.env \
  backend/api/.env || true

# transfer to remote (fixed filenames to avoid wildcard issues)
echo "Transferring package and images to remote..."
scp -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no "$PACKAGE_LOCAL" \
    /tmp/frontend.tar.gz /tmp/backend.tar.gz "${SSH_USER}@${INSTANCE_IP}:/tmp/"

# remote deploy
ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no "${SSH_USER}@${INSTANCE_IP}" bash -s <<'REMOTE_EOF'
set -euo pipefail
PROJECT_DIR="/home/ec2-user/trading-platform"
sudo rm -rf "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# extract package
tar -xzf /tmp/trading-platform_package.tar.gz || tar -xzf /tmp/*trading-platform*_package.tar.gz || true

# load images
sudo gunzip -c /tmp/frontend.tar.gz | sudo docker load
sudo gunzip -c /tmp/backend.tar.gz  | sudo docker load

# stop previous containers
sudo docker-compose down || true

# start using loaded images (force no build)
sudo docker-compose up -d --no-build

sleep 5
sudo docker-compose ps

# basic checks
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost || echo "000")
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health || echo "000")

echo "HTTP: $HTTP_CODE"
echo "API:  $API_CODE"

# cleanup tmp files
sudo rm -f /tmp/frontend.tar.gz /tmp/backend.tar.gz /tmp/trading-platform_package.tar.gz || true
REMOTE_EOF

# cleanup local temp
rm -f /tmp/frontend.tar.gz /tmp/backend.tar.gz "$PACKAGE_LOCAL"

echo "Deploy finished. Visit http://${INSTANCE_IP}"