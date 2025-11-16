#!/bin/bash
# Health check script for wanLLMDB Kubernetes deployment
# Usage: ./health-check.sh [environment]
#   environment: development|production (default: development)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ENVIRONMENT="${1:-development}"
NAMESPACE="wanllmdb"

if [[ "$ENVIRONMENT" == "development" ]]; then
    NAMESPACE="wanllmdb-dev"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}wanLLMDB Health Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Environment:${NC} $ENVIRONMENT"
echo -e "${GREEN}Namespace:${NC} $NAMESPACE"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check namespace
echo -e "${BLUE}[1/7] Checking namespace...${NC}"
if kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${GREEN}✓ Namespace exists${NC}"
else
    echo -e "${RED}✗ Namespace not found${NC}"
    exit 1
fi
echo ""

# Check PostgreSQL
echo -e "${BLUE}[2/7] Checking PostgreSQL...${NC}"
POSTGRES_POD=$(kubectl get pods -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [[ -n "$POSTGRES_POD" ]]; then
    if kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- pg_isready -U wanllm &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
    else
        echo -e "${YELLOW}⚠ PostgreSQL pod exists but not ready${NC}"
    fi
else
    echo -e "${RED}✗ PostgreSQL pod not found${NC}"
fi
echo ""

# Check Redis
echo -e "${BLUE}[3/7] Checking Redis...${NC}"
REDIS_POD=$(kubectl get pods -n "$NAMESPACE" -l app=redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [[ -n "$REDIS_POD" ]]; then
    REDIS_PASSWORD=$(kubectl get secret wanllmdb-secrets -n "$NAMESPACE" -o jsonpath='{.data.REDIS_PASSWORD}' 2>/dev/null | base64 -d)
    if kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ping &> /dev/null; then
        echo -e "${GREEN}✓ Redis is ready${NC}"
    else
        echo -e "${YELLOW}⚠ Redis pod exists but not ready${NC}"
    fi
else
    echo -e "${RED}✗ Redis pod not found${NC}"
fi
echo ""

# Check MinIO
echo -e "${BLUE}[4/7] Checking MinIO...${NC}"
MINIO_POD=$(kubectl get pods -n "$NAMESPACE" -l app=minio -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [[ -n "$MINIO_POD" ]]; then
    if kubectl exec -n "$NAMESPACE" "$MINIO_POD" -- sh -c "curl -f http://localhost:9000/minio/health/live" &> /dev/null; then
        echo -e "${GREEN}✓ MinIO is ready${NC}"
    else
        echo -e "${YELLOW}⚠ MinIO pod exists but not ready${NC}"
    fi
else
    echo -e "${RED}✗ MinIO pod not found${NC}"
fi
echo ""

# Check Backend
echo -e "${BLUE}[5/7] Checking Backend API...${NC}"
BACKEND_PODS=$(kubectl get pods -n "$NAMESPACE" -l app=backend -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")
if [[ -n "$BACKEND_PODS" ]]; then
    READY_COUNT=0
    TOTAL_COUNT=0
    for pod in $BACKEND_PODS; do
        ((TOTAL_COUNT++))
        if kubectl exec -n "$NAMESPACE" "$pod" -- curl -f http://localhost:8000/health &> /dev/null; then
            ((READY_COUNT++))
        fi
    done
    if [[ $READY_COUNT -eq $TOTAL_COUNT ]]; then
        echo -e "${GREEN}✓ Backend API is ready ($READY_COUNT/$TOTAL_COUNT pods)${NC}"
    else
        echo -e "${YELLOW}⚠ Backend API partially ready ($READY_COUNT/$TOTAL_COUNT pods)${NC}"
    fi
else
    echo -e "${RED}✗ Backend pods not found${NC}"
fi
echo ""

# Check Frontend
echo -e "${BLUE}[6/7] Checking Frontend...${NC}"
FRONTEND_PODS=$(kubectl get pods -n "$NAMESPACE" -l app=frontend -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")
if [[ -n "$FRONTEND_PODS" ]]; then
    READY_COUNT=0
    TOTAL_COUNT=0
    for pod in $FRONTEND_PODS; do
        ((TOTAL_COUNT++))
        if kubectl exec -n "$NAMESPACE" "$pod" -- curl -f http://localhost:3000 &> /dev/null; then
            ((READY_COUNT++))
        fi
    done
    if [[ $READY_COUNT -eq $TOTAL_COUNT ]]; then
        echo -e "${GREEN}✓ Frontend is ready ($READY_COUNT/$TOTAL_COUNT pods)${NC}"
    else
        echo -e "${YELLOW}⚠ Frontend partially ready ($READY_COUNT/$TOTAL_COUNT pods)${NC}"
    fi
else
    echo -e "${RED}✗ Frontend pods not found${NC}"
fi
echo ""

# Check Ingress
echo -e "${BLUE}[7/7] Checking Ingress...${NC}"
if kubectl get ingress -n "$NAMESPACE" &> /dev/null; then
    INGRESS_HOSTS=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[*].spec.rules[*].host}' 2>/dev/null || echo "")
    if [[ -n "$INGRESS_HOSTS" ]]; then
        echo -e "${GREEN}✓ Ingress configured${NC}"
        echo -e "${GREEN}  Hosts:${NC}"
        for host in $INGRESS_HOSTS; do
            echo "    - $host"
        done
    else
        echo -e "${YELLOW}⚠ Ingress exists but no hosts configured${NC}"
    fi
else
    echo -e "${YELLOW}⚠ No ingress found (use port-forward for access)${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"

# Get overall pod status
TOTAL_PODS=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
RUNNING_PODS=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
READY_PODS=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}' 2>/dev/null | grep -c "True" || echo 0)

echo -e "${GREEN}Total Pods:${NC} $TOTAL_PODS"
echo -e "${GREEN}Running:${NC} $RUNNING_PODS"
echo -e "${GREEN}Ready:${NC} $READY_PODS"
echo ""

if [[ $READY_PODS -eq $TOTAL_PODS ]] && [[ $TOTAL_PODS -gt 0 ]]; then
    echo -e "${GREEN}✓ All systems operational${NC}"
    echo ""
    echo -e "${BLUE}Access Information:${NC}"
    echo "  Port-forward commands:"
    echo "    Frontend:  kubectl port-forward -n $NAMESPACE svc/frontend 3000:3000"
    echo "    Backend:   kubectl port-forward -n $NAMESPACE svc/backend 8000:8000"
    echo "    MinIO:     kubectl port-forward -n $NAMESPACE svc/minio-console 9001:9001"
else
    echo -e "${YELLOW}⚠ Some components are not ready${NC}"
    echo ""
    echo "Check pod status with:"
    echo "  kubectl get pods -n $NAMESPACE"
    echo ""
    echo "Check logs with:"
    echo "  kubectl logs -n $NAMESPACE -l app=backend --tail=100"
fi
echo ""
