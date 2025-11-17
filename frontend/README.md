# wanLLMDB Frontend

This is the frontend application for wanLLMDB, built with React 18, TypeScript, and Vite.

## Tech Stack

- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **State Management**: Redux Toolkit
- **UI Library**: Ant Design
- **Routing**: React Router v6
- **Charts**: Recharts, Plotly.js
- **HTTP Client**: Axios

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The application will be available at `http://localhost:3000`

### Build

```bash
npm run build
```

### Testing

```bash
npm run test
```

### Linting

```bash
npm run lint
npm run lint:fix
```

### Format

```bash
npm run format
```

## Project Structure

```
src/
├── assets/          # Static assets
├── components/      # Reusable components
│   ├── common/     # Common UI components
│   ├── layout/     # Layout components
│   ├── charts/     # Chart components
│   └── forms/      # Form components
├── features/        # Feature modules
│   ├── auth/       # Authentication
│   ├── projects/   # Projects
│   └── runs/       # Runs
├── pages/           # Page components
├── hooks/           # Custom hooks
├── services/        # API services
├── store/           # Redux store
├── utils/           # Utility functions
├── types/           # TypeScript types
└── test/            # Test utilities
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint errors
- `npm run format` - Format code with Prettier
- `npm run type-check` - TypeScript type checking
- `npm run test` - Run tests
- `npm run test:coverage` - Run tests with coverage

## Environment Variables

Create a `.env.local` file in the root directory:

```env
VITE_API_URL=http://localhost:8000
```

## Proxy Configuration

The Vite dev server automatically proxies API requests to the backend. The proxy target is automatically detected based on the runtime environment:

### Automatic Detection Priority

1. **Explicit Override** (Highest Priority)
   - Set `VITE_PROXY_TARGET` environment variable to explicitly specify the backend URL
   - Example: `VITE_PROXY_TARGET=http://custom-backend:9000`

2. **Kubernetes Environment**
   - Detected when `KUBERNETES_SERVICE_HOST` or `K8S_SERVICE_NAME` is set
   - Uses service name from `K8S_SERVICE_NAME` (default: `wanllmdb-backend`)
   - Port from `K8S_SERVICE_PORT` (default: `8000`)
   - Example: `http://wanllmdb-backend:8000`

3. **Docker Compose Environment**
   - Detected when `DOCKER` env var is set or `/.dockerenv` file exists
   - Uses service name from `DOCKER_SERVICE_NAME` (default: `backend`)
   - Port from `DOCKER_SERVICE_PORT` (default: `8000`)
   - Example: `http://backend:8000`

4. **Local Development** (Default)
   - When running locally (not in Docker/K8s)
   - Uses `localhost` with port from `BACKEND_PORT` (default: `8000`)
   - Example: `http://localhost:8000`

### Configuration Examples

#### Docker Compose
```yaml
environment:
  DOCKER: "true"
  DOCKER_SERVICE_NAME: backend
  DOCKER_SERVICE_PORT: "8000"
```

#### Kubernetes
```yaml
env:
  - name: K8S_SERVICE_NAME
    value: "wanllmdb-backend"
  - name: K8S_SERVICE_PORT
    value: "8000"
```

#### Local Development
```bash
# No special configuration needed
# Defaults to http://localhost:8000
```

#### Custom Override
```bash
# Override with explicit target
VITE_PROXY_TARGET=http://my-backend:9000 npm run dev
```