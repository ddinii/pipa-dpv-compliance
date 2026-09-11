@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 goto use_py

where python >nul 2>nul
if not errorlevel 1 goto use_python

echo ERROR: Python was not found.
echo Install Python, enable "Add Python to PATH", and try again.
goto failed

:use_py
echo [1/2] Installing required Python packages...
py -m pip install rdflib pyshacl
if errorlevel 1 goto install_failed
echo [2/2] Validating all PIPA PoC scenarios...
py "%~dp0validate_final_scenarios.py"
set "VALIDATION_EXIT=%ERRORLEVEL%"
goto finished

:use_python
echo [1/2] Installing required Python packages...
python -m pip install rdflib pyshacl
if errorlevel 1 goto install_failed
echo [2/2] Validating all PIPA PoC scenarios...
python "%~dp0validate_final_scenarios.py"
set "VALIDATION_EXIT=%ERRORLEVEL%"
goto finished

:install_failed
echo ERROR: Package installation failed.
goto failed

:failed
set "VALIDATION_EXIT=2"

:finished
echo.
if "%VALIDATION_EXIT%"=="0" echo SUCCESS: All available tests passed.
if not "%VALIDATION_EXIT%"=="0" echo FAILED: Review the messages above.
pause
exit /b %VALIDATION_EXIT%
