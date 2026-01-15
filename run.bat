@echo off
set OLLAMA_BASE_URL=http://localhost:11434
set OLLAMA_MODEL=qwen2.5:latest
set OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest
set OLLAMA_API_TIMEOUT=300

:: Set default provider to zhipu
set PROVIDER=zhipu

:: Check if provider parameter is provided
if "%1" neq "" set PROVIDER=%1

:: Run main.py with provider parameter
uv run main.py --provider %PROVIDER%