# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the DocExtract project.

## Project Overview

DocExtract (also known as Tagdstiller) is a full-stack web application designed for document keyword extraction and management. It allows users to upload documents in various formats (PDF, DOCX, HTML, Markdown, TXT) and then uses AI-powered extractors to identify and analyze keywords. The application features a real-time management UI for viewing and interacting with the extracted keywords.

The project is architected as a monorepo with a React/TypeScript frontend and a Python/FastAPI backend.

### Key Technologies

*   **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Neo4j, PyMuPDF, KeyBERT, spaCy, LangChain, KoNLPy
*   **Frontend**: React 18+, TypeScript, Tailwind CSS, Axios, PDF.js
*   **Database**: SQLite (default), Memgraph (for knowledge graph features)
*   **Package Managers**: pip (backend), npm (frontend)

### Directory Structure

*   `backend/`: Contains the Python FastAPI backend application.
    *   `main.py`: The main entry point for the backend server.
    *   `routers/`: API endpoint definitions.
    *   `extractors/`: Keyword extraction logic.
    *   `services/`: Business logic and services.
    *   `db/`: Database models and configuration.
    *   `requirements.txt`: Python dependencies.
*   `frontend/`: Contains the React/TypeScript frontend application.
    *   `src/App.tsx`: The main React application component.
    *   `src/components/`: Reusable React components.
    *   `src/services/`: API communication services.
    *   `package.json`: Frontend dependencies and scripts.
*   `scripts/`: Shell scripts for managing the application (start, stop, etc.).
*   `docs/`: Project documentation.

## Building and Running

The project uses a set of shell scripts to manage the application lifecycle.

### Prerequisites

*   Python 3.11+ (Conda recommended)
*   Node.js 16+
*   Git

### Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd DocExtract
    ```

2.  **Set up the backend:**
    ```bash
    conda create -n DocExtract python=3.11
    conda activate DocExtract
    cd backend
    pip install -r requirements.txt
    ```

3.  **Set up the frontend:**
    ```bash
    cd frontend
    npm install
    ```

### Running the Application

*   **Start both backend and frontend:**
    ```bash
    ./scripts/start_all.sh
    ```
    *   Frontend will be available at `http://localhost:3001`
    *   Backend will be available at `http://localhost:58000`

*   **Start only the backend:**
    ```bash
    ./scripts/start_backend.sh
    ```

*   **Start only the frontend:**
    ```bash
    ./scripts/start_frontend.sh
    ```

### Testing

*   **Run backend tests:**
    ```bash
    cd backend
    pytest tests/ -v
    ```

## Development Conventions

*   **Backend Coding Style**: The project uses Black, isort, and flake8 for code formatting and linting.
*   **Frontend Coding Style**: The project uses Prettier and ESLint for code formatting and linting.
*   **Commit Messages**: The project follows the Conventional Commits specification.
*   **Branching**: Feature development should be done in branches named `feature/new-feature`.
