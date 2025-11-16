#!/bin/bash
# Backup PostgreSQL database from Kubernetes
# Usage: ./backup-database.sh [environment] [backup-dir]
#   environment: development|production (default: development)
#   backup-dir: Directory to store backups (default: ./backups)

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENVIRONMENT="${1:-development}"
BACKUP_DIR="${2:-./backups}"
NAMESPACE="wanllmdb"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if [[ "$ENVIRONMENT" == "development" ]]; then
    NAMESPACE="wanllmdb-dev"
fi

BACKUP_FILE="$BACKUP_DIR/wanllmdb_${ENVIRONMENT}_${TIMESTAMP}.sql.gz"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}wanLLMDB Database Backup${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Environment:${NC} $ENVIRONMENT"
echo -e "${GREEN}Namespace:${NC} $NAMESPACE"
echo -e "${GREEN}Backup file:${NC} $BACKUP_FILE"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Get PostgreSQL pod
echo -e "${BLUE}Finding PostgreSQL pod...${NC}"
POSTGRES_POD=$(kubectl get pods -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [[ -z "$POSTGRES_POD" ]]; then
    echo -e "${RED}Error: PostgreSQL pod not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found pod: $POSTGRES_POD${NC}"
echo ""

# Get database credentials
echo -e "${BLUE}Retrieving credentials...${NC}"
POSTGRES_USER=$(kubectl get configmap wanllmdb-config -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_USER}' 2>/dev/null || echo "wanllm")
POSTGRES_DB=$(kubectl get configmap wanllmdb-config -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_DB}' 2>/dev/null || echo "wanllmdb")

echo -e "${GREEN}✓ User: $POSTGRES_USER${NC}"
echo -e "${GREEN}✓ Database: $POSTGRES_DB${NC}"
echo ""

# Create backup
echo -e "${BLUE}Creating backup...${NC}"
kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$BACKUP_FILE"

# Check if backup was created
if [[ -f "$BACKUP_FILE" ]]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    echo -e "${GREEN}  File: $BACKUP_FILE${NC}"
    echo -e "${GREEN}  Size: $BACKUP_SIZE${NC}"
    echo ""

    # List recent backups
    echo -e "${BLUE}Recent backups:${NC}"
    ls -lh "$BACKUP_DIR" | tail -5
    echo ""

    echo -e "${GREEN}Backup completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}To restore this backup:${NC}"
    echo "  ./restore-database.sh $ENVIRONMENT $BACKUP_FILE"
else
    echo -e "${RED}Error: Backup failed${NC}"
    exit 1
fi
