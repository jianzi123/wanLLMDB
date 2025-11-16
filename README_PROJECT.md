# wanLLMDB - ML Experiment Management Platform

A comprehensive machine learning experiment management platform inspired by Weights & Biases, featuring experiment tracking, artifact management, hyperparameter optimization, and collaborative reporting.

## Features

- **Experiment Tracking**: Track runs, metrics, configurations, and system resources
- **Real-time Visualization**: Interactive charts and dashboards
- **Artifact Management**: Version control for datasets and models
- **Hyperparameter Sweeps**: Automated hyperparameter optimization
- **Model Registry**: Manage model lifecycle from development to production
- **Collaborative Reports**: Share and collaborate on experiment results
- **Team Collaboration**: Organizations, teams, and fine-grained permissions

## Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for blazing-fast development
- **Redux Toolkit** for state management
- **Ant Design** for UI components
- **Recharts** and **Plotly.js** for data visualization

### Backend
- **FastAPI** (Python 3.11) for main API services
- **Go** for high-performance metric service
- **PostgreSQL 15** for relational data
- **TimescaleDB** for time-series metrics
- **Redis 7** for caching
- **MinIO** for object storage

### DevOps
- **Docker** & **Docker Compose** for containerization
- **Kubernetes** for production deployment
- **GitHub Actions** for CI/CD
- **Prometheus** & **Grafana** for monitoring

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Node.js 18+ and Python 3.11+ for local development

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/wanLLMDB.git
cd wanLLMDB

# Start all services
make setup

# Or manually:
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

Access the application:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

### Local Development

#### Backend

```bash
cd backend

# Install dependencies
poetry install

# Copy environment variables
cp .env.example .env

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run python -m app.main
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Project Structure

```
wanLLMDB/
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── features/     # Feature modules
│   │   ├── pages/        # Page components
│   │   ├── store/        # Redux store
│   │   └── types/        # TypeScript types
│   └── package.json
│
├── backend/              # FastAPI backend application
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── models/      # Database models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── services/    # Business logic
│   │   └── core/        # Core utilities
│   ├── alembic/         # Database migrations
│   └── pyproject.toml
│
├── services/            # Microservices
│   ├── metric-service/  # Go metric service
│   └── api-gateway/     # Go API gateway
│
├── docs/                # Documentation
├── scripts/             # Utility scripts
└── docker-compose.yml   # Docker Compose configuration
```

## Development

### Available Commands

```bash
# Start development environment
make dev

# View logs
make logs

# Run tests
make test

# Database migrations
make migrate-up
make migrate-down
make migrate-create MESSAGE="your message"

# Code quality
make lint-backend
make lint-frontend
make format-backend
make format-frontend

# Access shells
make backend-shell
make frontend-shell
make db-shell
```

See `make help` for all available commands.

## Testing

```bash
# Backend tests
cd backend
poetry run pytest

# Frontend tests
cd frontend
npm test

# With Docker
make test
```

## Documentation

- [Project Planning](./PROJECT_PLAN.md)
- [Technical Architecture](./TECHNICAL_ARCHITECTURE.md)
- [Technology Stack Decisions](./TECH_STACK_DECISION.md)
- [Development Roadmap](./DEVELOPMENT_ROADMAP.md)
- [Frontend README](./frontend/README.md)
- [Backend README](./backend/README.md)

## Roadmap

- [x] **Phase 1: MVP** - Basic experiment tracking and visualization
- [ ] **Phase 2: Advanced Features** - Artifacts, Sweeps, Model Registry
- [ ] **Phase 3: Enterprise** - Advanced collaboration and deployment

See [DEVELOPMENT_ROADMAP.md](./DEVELOPMENT_ROADMAP.md) for detailed milestones.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](./LICENSE) file for details.

## Acknowledgments

- Inspired by [Weights & Biases](https://wandb.ai/)
- Built with amazing open-source technologies

## Support

- Documentation: [https://docs.wanllmdb.io](https://docs.wanllmdb.io)
- Issues: [GitHub Issues](https://github.com/your-org/wanLLMDB/issues)
- Discussions: [GitHub Discussions](https://github.com/your-org/wanLLMDB/discussions)

---

Made with ❤️ by the wanLLMDB team
