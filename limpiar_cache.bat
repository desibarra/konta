@echo off
echo Limpiando cache de Django...
echo.

REM Eliminar archivos .pyc
echo Eliminando archivos .pyc...
for /r %%i in (*.pyc) do del "%%i"

REM Eliminar carpetas __pycache__
echo Eliminando carpetas __pycache__...
for /d /r %%i in (__pycache__) do rd /s /q "%%i"

echo.
echo ✅ Cache limpiado
echo.
echo Ahora reinicia el servidor Django:
echo   python manage.py runserver
echo.
pause
