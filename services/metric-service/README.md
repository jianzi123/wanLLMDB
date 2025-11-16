# Metric Service

High-performance metric ingestion service built with Go and Gin framework.

## Features

- **Batch Metric Writing**: Efficiently write up to 1000 metrics in a single request
- **Real-time Streaming**: WebSocket support for live metric updates
- **TimescaleDB Integration**: Optimized time-series data storage
- **Redis Caching**: Fast metric retrieval with intelligent caching
- **System Metrics**: CPU, GPU, memory, disk, and network monitoring
- **Query API**: Flexible metric querying with time range and step filtering
- **Statistics**: Built-in metric statistics (min, max, avg, stddev)

## Architecture

```
┌─────────────┐
│   Client    │
│  (Python    │
│   SDK)      │
└──────┬──────┘
       │ HTTP/WS
       ▼
┌─────────────────────────────────┐
│     Metric Service (Go)         │
│  ┌────────────────────────┐     │
│  │  Gin HTTP Server       │     │
│  │  - Batch Write API     │     │
│  │  - Query API           │     │
│  │  - WebSocket Handler   │     │
│  └────────┬───────────────┘     │
│           │                     │
│  ┌────────▼────────┐            │
│  │  Service Layer  │            │
│  │  - Validation   │            │
│  │  - Caching      │            │
│  │  - PubSub       │            │
│  └────────┬────────┘            │
│           │                     │
│  ┌────────▼──────────┐          │
│  │  Repository Layer │          │
│  │  - Batch Insert   │          │
│  │  - Queries        │          │
│  └────────┬──────────┘          │
└───────────┼─────────────────────┘
            │
    ┌───────┴────────┐
    ▼                ▼
┌──────────┐    ┌─────────┐
│TimescaleDB│    │  Redis  │
│  (Metrics)│    │ (Cache) │
└───────────┘    └─────────┘
```

## API Endpoints

### Batch Write Metrics
```
POST /api/v1/metrics/batch
Content-Type: application/json

{
  "metrics": [
    {
      "run_id": "uuid",
      "metric_name": "loss",
      "step": 100,
      "value": 0.45,
      "time": "2024-01-01T12:00:00Z",
      "metadata": {}
    }
  ]
}
```

### Get Run Metrics
```
GET /api/v1/runs/{run_id}/metrics?limit=1000&start_time=2024-01-01T00:00:00Z
```

### Get Metric History
```
GET /api/v1/runs/{run_id}/metrics/{metric_name}?limit=1000
```

### Get Latest Metric Value
```
GET /api/v1/runs/{run_id}/metrics/{metric_name}/latest
```

### Get Metric Statistics
```
GET /api/v1/runs/{run_id}/metrics/{metric_name}/stats

Response:
{
  "metric_name": "loss",
  "count": 1000,
  "min_value": 0.1,
  "max_value": 2.5,
  "avg_value": 0.8,
  "std_dev": 0.3,
  "first_time": "2024-01-01T00:00:00Z",
  "last_time": "2024-01-01T12:00:00Z"
}
```

### WebSocket Real-time Metrics
```
WS /ws/metrics/{run_id}

Subscribe:
{
  "type": "subscribe",
  "payload": {
    "run_id": "uuid",
    "metric_names": ["loss", "accuracy"]
  }
}

Receive:
{
  "type": "metric",
  "payload": {
    "metrics": [...]
  }
}
```

## Configuration

Environment variables:

- `PORT`: Service port (default: 8001)
- `ENVIRONMENT`: Environment (development/production)
- `TIMESCALE_URL`: TimescaleDB connection string
- `REDIS_URL`: Redis connection string
- `BATCH_SIZE`: Maximum batch size (default: 1000)
- `CACHE_TIMEOUT`: Cache timeout in seconds (default: 300)

## Development

### Prerequisites

- Go 1.21+
- TimescaleDB
- Redis

### Run locally

```bash
# Install dependencies
go mod download

# Run with hot reload
air

# Or run directly
go run cmd/server/main.go
```

### Run with Docker

```bash
# Build image
docker build -t metric-service .

# Run container
docker run -p 8001:8001 \
  -e TIMESCALE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  metric-service
```

## Performance

- **Batch writes**: Up to 10,000 metrics/second
- **Query latency**: <50ms (cached), <200ms (database)
- **WebSocket**: Supports 1000+ concurrent connections
- **Connection pooling**: 5-20 database connections

## Testing

```bash
# Run tests
go test ./...

# Run with coverage
go test -cover ./...

# Run benchmarks
go test -bench=. ./...
```

## Production Deployment

1. Build optimized binary:
```bash
CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o metric-service ./cmd/server
```

2. Configure environment variables

3. Set up monitoring (Prometheus metrics coming soon)

4. Configure load balancer for horizontal scaling

## Future Enhancements

- [ ] Prometheus metrics export
- [ ] gRPC API support
- [ ] Metric downsampling
- [ ] Query optimization with continuous aggregates
- [ ] Rate limiting
- [ ] Authentication/Authorization
- [ ] Distributed tracing
