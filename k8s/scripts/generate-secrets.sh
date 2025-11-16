#!/bin/bash
# Generate secrets.yaml from template with strong random values
# Usage: ./generate-secrets.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
K8S_DIR="$(dirname "$SCRIPT_DIR")"
BASE_DIR="$K8S_DIR/base"
TEMPLATE_FILE="$BASE_DIR/secrets.yaml.example"
OUTPUT_FILE="$BASE_DIR/secrets.yaml"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}wanLLMDB Secret Generator${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed${NC}"
    exit 1
fi

# Check if secrets.yaml already exists
if [[ -f "$OUTPUT_FILE" ]]; then
    echo -e "${YELLOW}Warning: $OUTPUT_FILE already exists${NC}"
    read -p "Do you want to overwrite it? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Cancelled"
        exit 0
    fi
fi

echo -e "${GREEN}Generating strong secrets...${NC}"
echo ""

# Generate secrets
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
REDIS_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
MINIO_ACCESS_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
MINIO_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

# Base64 encode
SECRET_KEY_B64=$(echo -n "$SECRET_KEY" | base64)
POSTGRES_PASSWORD_B64=$(echo -n "$POSTGRES_PASSWORD" | base64)
REDIS_PASSWORD_B64=$(echo -n "$REDIS_PASSWORD" | base64)
MINIO_ACCESS_KEY_B64=$(echo -n "$MINIO_ACCESS_KEY" | base64)
MINIO_SECRET_KEY_B64=$(echo -n "$MINIO_SECRET_KEY" | base64)
ADMIN_USERS_B64=$(echo -n "admin" | base64)

# Create secrets.yaml
cat > "$OUTPUT_FILE" <<EOF
---
# Auto-generated secrets for wanLLMDB
# Generated: $(date)
# ⚠️ DO NOT commit this file to version control
# ⚠️ Keep this file secure with proper permissions: chmod 600 secrets.yaml

apiVersion: v1
kind: Secret
metadata:
  name: wanllmdb-secrets
  namespace: wanllmdb
type: Opaque
data:
  # JWT Secret Key (32+ characters)
  SECRET_KEY: $SECRET_KEY_B64

  # PostgreSQL Password
  POSTGRES_PASSWORD: $POSTGRES_PASSWORD_B64

  # Redis Password
  REDIS_PASSWORD: $REDIS_PASSWORD_B64

  # MinIO Access Key (12+ characters)
  MINIO_ACCESS_KEY: $MINIO_ACCESS_KEY_B64

  # MinIO Secret Key (12+ characters)
  MINIO_SECRET_KEY: $MINIO_SECRET_KEY_B64

  # Admin Users (comma-separated)
  ADMIN_USERS: $ADMIN_USERS_B64

---
# Database connection URLs
apiVersion: v1
kind: Secret
metadata:
  name: wanllmdb-db-url
  namespace: wanllmdb
type: Opaque
stringData:
  DATABASE_URL: "postgresql://wanllm:$POSTGRES_PASSWORD@postgres:5432/wanllmdb"
  REDIS_URL: "redis://:$REDIS_PASSWORD@redis:6379/0"
  TIMESCALE_URL: "postgresql://wanllm:$POSTGRES_PASSWORD@postgres:5432/wanllmdb_metrics"
EOF

# Set restrictive permissions
chmod 600 "$OUTPUT_FILE"

echo -e "${GREEN}✓ Secrets generated successfully!${NC}"
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Generated Credentials (SAVE THESE!)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}JWT Secret Key:${NC}"
echo "  $SECRET_KEY"
echo ""
echo -e "${GREEN}PostgreSQL:${NC}"
echo "  User: wanllm"
echo "  Password: $POSTGRES_PASSWORD"
echo "  Database: wanllmdb"
echo ""
echo -e "${GREEN}Redis:${NC}"
echo "  Password: $REDIS_PASSWORD"
echo ""
echo -e "${GREEN}MinIO:${NC}"
echo "  Access Key: $MINIO_ACCESS_KEY"
echo "  Secret Key: $MINIO_SECRET_KEY"
echo ""
echo -e "${GREEN}Admin Users:${NC}"
echo "  admin (default)"
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}IMPORTANT:${NC}"
echo "  1. Save these credentials in a secure password manager"
echo "  2. File created at: $OUTPUT_FILE"
echo "  3. Permissions set to 600 (owner read/write only)"
echo "  4. DO NOT commit secrets.yaml to version control"
echo "  5. Add to .gitignore if not already there"
echo ""
echo -e "${BLUE}Connection Strings:${NC}"
echo -e "${GREEN}PostgreSQL:${NC}"
echo "  postgresql://wanllm:$POSTGRES_PASSWORD@postgres:5432/wanllmdb"
echo ""
echo -e "${GREEN}Redis:${NC}"
echo "  redis://:$REDIS_PASSWORD@redis:6379/0"
echo ""
echo -e "${GREEN}Done!${NC}"
