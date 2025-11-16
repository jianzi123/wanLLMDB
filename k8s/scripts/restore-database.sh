#!/bin/bash
# Restore PostgreSQL database in Kubernetes
# Usage: ./restore-database.sh [environment] [backup-file]
#   environment: development|production (default: development)
#   backup-file: Path to backup file (.sql.gz)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENVIRONMENT="${1:-development}"
BACKUP_FILE="$2"
NAMESPACE="wanllmdb"

if [[ "$ENVIRONMENT" == "development" ]]; then
    NAMESPACE="wanllmdb-dev"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}wanLLMDB Database Restore${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Environment:${NC} $ENVIRONMENT"
echo -e "${GREEN}Namespace:${NC} $NAMESPACE"
echo -e "${BLUE}========================================${NC}"
echo ""

# Validate backup file
if [[ -z "$BACKUP_FILE" ]]; then
    echo -e "${RED}Error: Backup file not specified${NC}"
    echo "Usage: $0 [environment] [backup-file]"
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}Backup file:${NC} $BACKUP_FILE"
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo -e "${GREEN}Size:${NC} $BACKUP_SIZE"
echo ""

# Warning
echo -e "${RED}⚠️  WARNING ⚠️${NC}"
echo -e "${YELLOW}This will OVERWRITE the current database!${NC}"
echo -e "${YELLOW}All existing data will be LOST!${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Restore cancelled"
    exit 0
fi

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

# Drop existing connections
echo -e "${BLUE}Dropping existing connections...${NC}"
kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- psql -U "$POSTGRES_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();" || true
echo ""

# Restore database
echo -e "${BLUE}Restoring database...${NC}"
gunzip < "$BACKUP_FILE" | kubectl exec -i -n "$NAMESPACE" "$POSTGRES_POD" -- psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Database restored successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verify
echo -e "${BLUE}Verifying restore...${NC}"
TABLE_COUNT=$(kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')

echo -e "${GREEN}✓ Tables found: $TABLE_COUNT${NC}"
echo ""
echo -e "${BLUE}Restart backend pods to refresh connections:${NC}"
echo "  kubectl rollout restart deployment/backend -n $NAMESPACE"
echo ""
