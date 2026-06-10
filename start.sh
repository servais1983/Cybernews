#!/usr/bin/env bash
# ============================================================
#  CyberNews - Lanceur Linux/Mac tout-en-un
#  ./start.sh : il s'occupe de tout (environnement virtuel,
#  dépendances, configuration, menu interactif).
# ============================================================
set -u
cd "$(dirname "$0")"

# --- 1. Trouver Python -------------------------------------
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
    echo "[ERREUR] Python 3 est introuvable. Installez-le (ex. : sudo apt install python3 python3-venv)."
    exit 1
fi

# --- 2. Environnement virtuel ------------------------------
if [ ! -x "venv/bin/python" ]; then
    echo "Création de l'environnement virtuel (première utilisation)..."
    "$PY" -m venv venv || { echo "[ERREUR] Création du venv impossible."; exit 1; }
fi
VPY="venv/bin/python"

# --- 3. Dépendances ----------------------------------------
if ! "$VPY" -c "import feedparser, requests, dotenv" >/dev/null 2>&1; then
    echo "Installation des dépendances..."
    "$VPY" -m pip install --quiet --upgrade pip setuptools wheel
    "$VPY" -m pip install --quiet -r requirements.txt || {
        echo "[ERREUR] Installation des dépendances impossible. Vérifiez votre connexion."
        exit 1
    }
fi

# --- 4. Configuration --------------------------------------
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo
    echo "Première utilisation : le fichier de configuration .env va s'ouvrir."
    echo "Remplissez au minimum la section Email (SENDER_EMAIL, EMAIL_PASSWORD,"
    echo "RECIPIENT_EMAIL), enregistrez, puis fermez l'éditeur."
    echo
    read -r -p "Appuyez sur Entrée pour continuer..."
    "${EDITOR:-nano}" .env
fi

open_in_browser() {
    if command -v xdg-open >/dev/null 2>&1; then xdg-open "$1" >/dev/null 2>&1 &
    elif command -v open >/dev/null 2>&1; then open "$1"
    else echo "Aperçu disponible : $1"; fi
}

# --- 5. Menu ------------------------------------------------
while true; do
    echo
    echo " ============= CyberNews ============="
    echo "  [1] Tester la connexion SMTP"
    echo "  [2] Aperçu sans envoi (ouvre le digest dans le navigateur)"
    echo "  [3] Générer et ENVOYER le digest"
    echo "  [4] Vérifier la santé des sources RSS"
    echo "  [5] Modifier la configuration (.env)"
    echo "  [6] Quitter"
    echo " ====================================="
    read -r -p "Votre choix : " choice
    case "$choice" in
        1) "$VPY" cybersec_rss_feed_enhanced.py --test-smtp ;;
        2) "$VPY" cybersec_rss_feed_enhanced.py --dry-run && [ -f digest.html ] && open_in_browser digest.html ;;
        3) "$VPY" cybersec_rss_feed_enhanced.py ;;
        4) "$VPY" cybersec_rss_feed_enhanced.py --check-feeds ;;
        5) "${EDITOR:-nano}" .env ;;
        6) exit 0 ;;
        *) echo "Choix invalide." ;;
    esac
done
