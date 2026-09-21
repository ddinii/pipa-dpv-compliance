@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python

echo ERROR: Python was not found.
goto failed

:use_py
py -m pip install -r requirements.txt
if errorlevel 1 goto failed
py run_tests.py
set "RESULT=%ERRORLEVEL%"
goto finished

:use_python
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
python run_tests.py
set "RESULT=%ERRORLEVEL%"
goto finished

:failed
set "RESULT=1"

:finished
echo.
if "%RESULT%"=="0" echo SUCCESS: Fact-to-Ontology mapping is valid.
if not "%RESULT%"=="0" echo FAILED: Review the errors above.
pause
exit /b %RESULT%

