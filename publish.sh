#!/usr/bin/env bash
# Build + push multi-arch SprachBoot images to GHCR so friends run without cloning.
#
# One-time setup:
#   1. GitHub Personal Access Token (classic), scope: write:packages
#      https://github.com/settings/tokens
#   2. Log in:
#        echo "$GH_TOKEN" | docker login ghcr.io -u lohith-pras --password-stdin
#   3. Create a buildx builder once (enables multi-arch via QEMU in Docker Desktop):
#        docker buildx create --use --name sprachboot
#   4. After the first push: github.com -> profile -> Packages -> set BOTH
#      packages (sprachboot-backend, sprachboot-frontend) to PUBLIC so friends
#      pull without logging in.
#
# Then each update:  ./publish.sh
set -euo pipefail

OWNER=lohith-pras
PLATFORMS=linux/amd64,linux/arm64   # covers Intel/Windows + Apple-silicon friends

echo "==> backend (multi-arch)"
docker buildx build --platform "$PLATFORMS" \
  -t "ghcr.io/$OWNER/sprachboot-backend:latest" \
  --push ./backend

echo "==> frontend (multi-arch)"
docker buildx build --platform "$PLATFORMS" \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 \
  -t "ghcr.io/$OWNER/sprachboot-frontend:latest" \
  --push ./frontend

echo
echo "Pushed. Send friends compose.friend.yml. They run:"
echo "  docker compose pull && docker compose up"
