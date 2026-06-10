@echo off
rem ============================================================
rem  CyberNews - Lanceur Windows tout-en-un
rem  Double-cliquez sur ce fichier : il s'occupe de tout
rem  (environnement virtuel, dependances, configuration, menu).
rem ============================================================
setlocal
cd /d "%~dp0"
title CyberNews

rem --- 1. Trouver Python -------------------------------------
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY python --version >nul 2>nul && set "PY=python"
if not defined PY (
    echo [ERREUR] Python 3 est introuvable.
    echo Installez-le depuis https://www.python.org/downloads/
    echo en cochant "Add Python to PATH", puis relancez ce script.
    pause
    exit /b 1
)

rem --- 2. Environnement virtuel ------------------------------
if not exist "venv\Scripts\python.exe" (
    echo Creation de l'environnement virtuel ^(premiere utilisation^)...
    %PY% -m venv venv || (echo [ERREUR] Creation du venv impossible. & pause & exit /b 1)
)
set "VPY=venv\Scripts\python.exe"

rem --- 3. Dependances ----------------------------------------
"%VPY%" -c "import feedparser, requests, dotenv" >nul 2>nul
if errorlevel 1 (
    echo Installation des dependances...
    "%VPY%" -m pip install --quiet --upgrade pip setuptools wheel
    "%VPY%" -m pip install --quiet -r requirements.txt || (
        echo [ERREUR] Installation des dependances impossible. Verifiez votre connexion.
        pause
        exit /b 1
    )
)

rem --- 4. Configuration --------------------------------------
if not exist ".env" (
    copy /y ".env.example" ".env" >nul
    echo.
    echo Premiere utilisation : le fichier de configuration .env va s'ouvrir.
    echo Remplissez au minimum la section Email ^(SENDER_EMAIL, EMAIL_PASSWORD,
    echo RECIPIENT_EMAIL^), enregistrez, puis fermez le Bloc-notes.
    echo.
    pause
    start /wait notepad ".env"
)

rem --- 5. Menu ------------------------------------------------
:menu
echo.
echo  ============= CyberNews =============
echo   [1] Tester la connexion SMTP
echo   [2] Apercu sans envoi (ouvre le digest dans le navigateur)
echo   [3] Generer et ENVOYER le digest
echo   [4] Verifier la sante des sources RSS
echo   [5] Modifier la configuration (.env)
echo   [6] Quitter
echo  =====================================
choice /c 123456 /n /m "Votre choix : "

if errorlevel 6 exit /b 0
if errorlevel 5 (start /wait notepad ".env" & goto menu)
if errorlevel 4 ("%VPY%" cybersec_rss_feed_enhanced.py --check-feeds & goto menu)
if errorlevel 3 ("%VPY%" cybersec_rss_feed_enhanced.py & goto menu)
if errorlevel 2 (
    "%VPY%" cybersec_rss_feed_enhanced.py --dry-run
    if exist "digest.html" start "" "digest.html"
    goto menu
)
"%VPY%" cybersec_rss_feed_enhanced.py --test-smtp
goto menu
