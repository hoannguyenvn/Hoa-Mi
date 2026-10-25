@echo off
REM Chay app Hoa Mi - dung Miniforge Conda co san
cd /d "%~dp0"
set CONDA_PY=C:\Users\ADMIN\miniforge3\python.exe
set HF_HUB_DISABLE_SYMLINKS_WARNING=1

if not exist "%CONDA_PY%" goto nopython

"%CONDA_PY%" -c "import faster_whisper, sounddevice, yt_dlp, imageio_ffmpeg" >nul 2>&1
if %errorlevel% neq 0 goto install
goto run

:install
echo Dang cai thu vien (faster-whisper, yt-dlp, ffmpeg...), chi lam 1 lan...
"%CONDA_PY%" -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 goto piperr
goto run

:run
echo Dang mo app Hoa Mi...
"%CONDA_PY%" "%~dp0app.py"
echo.
echo App da thoat. Ma loi: %errorlevel%
pause
exit /b 0

:nopython
echo Khong tim thay Conda Python.
echo Hay sua duong dan CONDA_PY trong file nay cho dung.
pause
exit /b 1

:piperr
echo LOI: khong cai duoc thu vien. Hay chup man hinh nay gui lai.
pause
exit /b 1
