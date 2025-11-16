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
