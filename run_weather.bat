@echo off
set OLLAMA_BASE_URL=http://localhost:11434
set OLLAMA_MODEL=qwen2.5:latest
set OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest
set OLLAMA_API_TIMEOUT=300

uv run weather_agent.py
