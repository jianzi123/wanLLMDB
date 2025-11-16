#!/bin/bash
# wanLLMDB Kubernetes Deployment Script
# Usage: ./deploy.sh [environment] [action]
#   environment: development|production (default: development)
#   action: apply|delete|status (default: apply)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
K8S_DIR="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-development}"
ACTION="${2:-apply}"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|production)$ ]]; then
    echo -e "${RED}Error: Environment must be 'development' or 'production'${NC}"
    echo "Usage: $0 [development|production] [apply|delete|status]"
    exit 1
fi

# Validate action
if [[ ! "$ACTION" =~ ^(apply|delete|status)$ ]]; then
    echo -e "${RED}Error: Action must be 'apply', 'delete', or 'status'${NC}"
    echo "Usage: $0 [development|production] [apply|delete|status]"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}wanLLMDB Kubernetes Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Environment:${NC} $ENVIRONMENT"
echo -e "${GREEN}Action:${NC} $ACTION"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}Error: kubectl is not installed${NC}"
        echo "Install from: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    echo -e "${GREEN}✓ kubectl found:$(NC} $(kubectl version --client --short 2>/dev/null || kubectl version --client)"

    # Check kustomize
    if ! command -v kustomize &> /dev/null; then
        echo -e "${RED}Error: kustomize is not installed${NC}"
        echo "Install from: https://kubectl.docs.kubernetes.io/installation/kustomize/"
        exit 1
    fi
    echo -e "${GREEN}✓ kustomize found:${NC} $(kustomize version --short)"

    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}Error: Cannot connect to Kubernetes cluster${NC}"
        echo "Check your kubeconfig and cluster status"
        exit 1
    fi
    echo -e "${GREEN}✓ Kubernetes cluster connected${NC}"

    # Check secrets for apply action
    if [[ "$ACTION" == "apply" ]]; then
        SECRETS_FILE="$K8S_DIR/base/secrets.yaml"
        if [[ ! -f "$SECRETS_FILE" ]]; then
            echo -e "${RED}Error: secrets.yaml not found${NC}"
            echo -e "${YELLOW}Please create secrets from template:${NC}"
            echo "  1. cd $K8S_DIR/base"
            echo "  2. cp secrets.yaml.example secrets.yaml"
            echo "  3. Edit secrets.yaml with actual values"
            echo "  4. Generate strong secrets:"
            echo "     python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
            exit 1
        fi
        echo -e "${GREEN}✓ secrets.yaml found${NC}"
    fi

    echo ""
}

# Deploy function
deploy() {
    echo -e "${BLUE}Deploying wanLLMDB to $ENVIRONMENT...${NC}"
    echo ""

    OVERLAY_DIR="$K8S_DIR/overlays/$ENVIRONMENT"

    if [[ ! -d "$OVERLAY_DIR" ]]; then
        echo -e "${RED}Error: Overlay directory not found: $OVERLAY_DIR${NC}"
        exit 1
    fi

    # Apply secrets first
    echo -e "${YELLOW}[1/3] Applying secrets...${NC}"
    kubectl apply -f "$K8S_DIR/base/secrets.yaml"
    echo ""

    # Build and apply kustomization
    echo -e "${YELLOW}[2/3] Building and applying manifests...${NC}"
    kustomize build "$OVERLAY_DIR" | kubectl apply -f -
    echo ""

    # Wait for deployments
    echo -e "${YELLOW}[3/3] Waiting for deployments to be ready...${NC}"

    NAMESPACE="wanllmdb"
    if [[ "$ENVIRONMENT" == "development" ]]; then
        NAMESPACE="wanllmdb-dev"
    fi

    echo "Waiting for PostgreSQL..."
    kubectl rollout status statefulset/postgres -n "$NAMESPACE" --timeout=5m || true

    echo "Waiting for Redis..."
    kubectl rollout status statefulset/redis -n "$NAMESPACE" --timeout=5m || true

    echo "Waiting for MinIO..."
    kubectl rollout status statefulset/minio -n "$NAMESPACE" --timeout=5m || true

    echo "Waiting for Backend..."
    kubectl rollout status deployment/backend -n "$NAMESPACE" --timeout=5m || true

    echo "Waiting for Frontend..."
    kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout=5m || true

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment completed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    # Show status
    show_status
}

# Delete function
delete() {
    echo -e "${RED}Deleting wanLLMDB from $ENVIRONMENT...${NC}"
    echo -e "${YELLOW}Warning: This will delete all resources including data!${NC}"
    echo ""

    read -p "Are you sure you want to continue? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Deletion cancelled"
        exit 0
    fi

    OVERLAY_DIR="$K8S_DIR/overlays/$ENVIRONMENT"

    if [[ ! -d "$OVERLAY_DIR" ]]; then
        echo -e "${RED}Error: Overlay directory not found: $OVERLAY_DIR${NC}"
        exit 1
    fi

    kustomize build "$OVERLAY_DIR" | kubectl delete -f -

    echo -e "${GREEN}Deletion completed${NC}"
}

# Show status
show_status() {
    NAMESPACE="wanllmdb"
    if [[ "$ENVIRONMENT" == "development" ]]; then
        NAMESPACE="wanllmdb-dev"
    fi

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}wanLLMDB Status - $ENVIRONMENT${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    echo -e "${GREEN}Namespace:${NC}"
    kubectl get namespace "$NAMESPACE" 2>/dev/null || echo "Namespace not found"
    echo ""

    echo -e "${GREEN}Pods:${NC}"
    kubectl get pods -n "$NAMESPACE" -o wide 2>/dev/null || echo "No pods found"
    echo ""

    echo -e "${GREEN}Services:${NC}"
    kubectl get services -n "$NAMESPACE" 2>/dev/null || echo "No services found"
    echo ""

    echo -e "${GREEN}Ingress:${NC}"
    kubectl get ingress -n "$NAMESPACE" 2>/dev/null || echo "No ingress found"
    echo ""

    echo -e "${GREEN}PersistentVolumeClaims:${NC}"
    kubectl get pvc -n "$NAMESPACE" 2>/dev/null || echo "No PVCs found"
    echo ""

    echo -e "${GREEN}Recent Events:${NC}"
    kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -10 2>/dev/null || echo "No events found"
    echo ""

    # Show endpoints
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Access Information${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    INGRESS_INFO=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[0].spec.rules[*].host}' 2>/dev/null || echo "")

    if [[ -n "$INGRESS_INFO" ]]; then
        echo -e "${GREEN}Configured Hosts:${NC}"
        for host in $INGRESS_INFO; do
            echo "  - http://$host"
        done
    else
        echo -e "${YELLOW}No ingress configured. Use port-forward to access services:${NC}"
        echo "  Frontend:  kubectl port-forward -n $NAMESPACE svc/frontend 3000:3000"
        echo "  Backend:   kubectl port-forward -n $NAMESPACE svc/backend 8000:8000"
        echo "  MinIO:     kubectl port-forward -n $NAMESPACE svc/minio-console 9001:9001"
    fi
    echo ""
}

# Main execution
check_prerequisites

case "$ACTION" in
    apply)
        deploy
        ;;
    delete)
        delete
        ;;
    status)
        show_status
        ;;
esac

echo -e "${GREEN}Done!${NC}"
