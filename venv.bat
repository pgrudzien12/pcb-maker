@echo off
REM Convenience script to activate local virtual environment
IF NOT EXIST .venv (
  echo Virtual environment folder .venv not found.
  echo Create one with: uv venv
  goto :eof
)
CALL .venv\Scripts\activate.bat
