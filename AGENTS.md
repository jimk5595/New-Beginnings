---
description: Repository Information Overview
alwaysApply: true
---

# Repository Information Overview

## Repository Summary

The **NewBeginnings AI System** is a modular, autonomous AI platform designed for technical building and task orchestration. It features a **FastAPI** backend that dynamically loads modules, manages AI personas (using **Gemini 3.0**), and integrates with a **React**-based dashboard. The system follows a strict management protocol defined in a `system_manifest.json` file.

## Repository Structure

- **backend/**: The primary directory containing the core application logic, API services, and shared utilities.
- **backend/frontend/**: A React-based dashboard for system monitoring and interaction.
- **backend/eliza/**: A specialized sub-component (Flask-based) for task orchestration and scene management.
- **backend/personas/**: Library of AI persona definitions and configurations.
- **backend/database/**: Persistent storage using SQLite (`system_growth.db`).
- **backend/memory_system/**: Core logic for AI memory management.

### Main Repository Components

- **Core Backend**: FastAPI server handling LLM routing, task execution, and module loading.
- **Frontend Dashboard**: React/Vite application providing a UI for the AI system.
- **Eliza Orchestrator**: A Flask-based component focused on complex task planning and execution.
- **Persona System**: A collection of AI profiles for diverse operational roles.

## Projects

### Backend (Core)

**Configuration Files**: `backend/main.py`, `backend/system_manifest.json`

#### Language & Runtime

**Language**: Python  
**Runtime**: Python 3.x  
**Framework**: FastAPI  
**Build System**: Python Native

#### Dependencies

**Main Dependencies**:

- `fastapi`
- `pydantic`
- `importlib` (Dynamic loading)
- `sqlite3`
- `gemini-api` (via `GeminiClient`)

#### Build & Installation

```bash
# Set up virtual environment
python -m venv backend/venv
source backend/venv/bin/activate  # On Windows: backend\venv\Scripts\activate

# Install dependencies (Standard Python practice)
pip install fastapi uvicorn pydantic google-generativeai
```

#### Usage & Operations

```bash
# Start the main FastAPI server
python backend/main.py
```

#### Testing

**Framework**: Pytest
**Test Location**: `backend/tests/`
**Naming Convention**: `test_*.py`
**Run Command**:

```bash
pytest backend/tests
```

### Frontend (Dashboard)

**Configuration File**: `backend/frontend/package.json`

#### Language & Runtime

**Language**: TypeScript / JavaScript  
**Runtime**: Node.js  
**Build System**: Vite  
**Package Manager**: npm

#### Dependencies

**Main Dependencies**:

- `react`: 18.2.0
- `react-dom`: 18.2.0

**Development Dependencies**:

- `typescript`: 5.3.3
- `vite`: 5.0.12
- `@vitejs/plugin-react`: 4.2.1

#### Build & Installation

```bash
cd backend/frontend
npm install
npm run build
```

#### Usage & Operations

```bash
# Run in development mode
npm run dev
```

### Eliza Orchestrator

**Configuration File**: `backend/eliza/app.py`

#### Language & Runtime

**Language**: Python  
**Framework**: Flask  
**Runtime**: Python 3.x

#### Dependencies

**Main Dependencies**:

- `flask`
- `flask-cors`

#### Usage & Operations

```bash
# The Eliza app is typically initialized via the factory function in app.py
# and integrated into the broader system.
```
