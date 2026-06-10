
![image](cybernews.png)

# 🛡️ CyberNews - Agrégateur RSS intelligent de Cybersécurité

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Sources-55%2B-orange" alt="Sources">
  <img src="https://img.shields.io/badge/IA-Claude-blueviolet" alt="IA">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</div>

## 📝 Description

CyberNews collecte en parallèle les actualités de **plus de 55 sources fiables** (médias spécialisés, chercheurs, éditeurs de sécurité, CERT et agences gouvernementales), les analyse, puis diffuse un **digest intelligent** par email, Discord, Slack, Telegram et GitHub Pages.

Ce qui le rend unique :

- 🧠 **Synthèse IA en français** (optionnel) : un brief exécutif quotidien (« ce qu'un RSSI doit savoir aujourd'hui ») et un résumé d'une phrase en français pour chaque article, générés via l'API Claude
- 💥 **Enrichissement CVE** : score **CVSS** récupéré sur l'API NVD et marquage **⚠️ KEV** (catalogue CISA des vulnérabilités activement exploitées, +10 au score de pertinence)
- 🎯 **Score de pertinence** : zero-day, exploitation active, RCE, ransomware, fuite de données, fraîcheur, fiabilité de la source — les 10 articles les plus critiques en tête de digest
- 🧹 **Déduplication intelligente** : la même histoire couverte par 5 médias n'apparaît qu'une fois, et un article déjà envoyé hier ne revient pas aujourd'hui (historique persistant)
- 🔍 **Filtres personnalisés** : `KEYWORDS_INCLUDE` / `KEYWORDS_EXCLUDE` pour ne suivre que vos technologies
- 📡 **CyberNews devient une source** : flux RSS sortant (`feed.xml`) + page web publique avec archives (GitHub Pages)
- ⚡ **Rapide et poli** : récupération parallèle des 55+ flux avec cache HTTP conditionnel (ETag/Last-Modified)
- 🤖 **Zéro infrastructure** : tout tourne dans GitHub Actions (digest quotidien, CI, surveillance hebdomadaire de la santé des sources)

## 🚦 Trois façons de le lancer

| Méthode | Pour qui | Effort |
|---|---|---|
| 🖱️ **`start.bat` / `start.sh`** (le plus simple) | un double-clic, le lanceur s'occupe de tout | 0 min |
| ☁️ **GitHub Actions** (recommandé pour l'automatique) | digest quotidien, aucune machine à maintenir | 5 min de config, une seule fois |
| ⏰ **Local, planifié** | cron / Planificateur Windows si vous préférez votre machine | 5 min |

## 🖱️ Lancement en un clic (`start.bat` / `start.sh`)

Le moyen le plus simple : un lanceur tout-en-un qui **s'occupe de tout** — il vérifie Python, crée l'environnement virtuel, installe les dépendances, vous fait remplir la configuration à la première utilisation, puis affiche un menu.

**Windows** — double-cliquez sur **`start.bat`** (ou lancez-le dans un terminal).

**Linux / Mac** :

```bash
./start.sh
```

```
 ============= CyberNews =============
  [1] Tester la connexion SMTP
  [2] Aperçu sans envoi (ouvre le digest dans le navigateur)
  [3] Générer et ENVOYER le digest
  [4] Vérifier la santé des sources RSS
  [5] Modifier la configuration (.env)
  [6] Quitter
 =====================================
```

À la première utilisation, le lanceur copie `.env.example` vers `.env` et l'ouvre dans l'éditeur : remplissez la section Email, enregistrez, fermez — c'est prêt. L'option [2] ouvre automatiquement le digest dans votre navigateur.

> 💡 **Gmail** : utilisez un [mot de passe d'application](https://myaccount.google.com/apppasswords), pas votre mot de passe principal.
>
> Seul prérequis : [Python 3.9+](https://www.python.org/downloads/) (sur Windows, cochez *« Add Python to PATH »* à l'installation).

## 🚀 Démarrage manuel (alternative en ligne de commande)

```bash
git clone https://github.com/servais1983/Cybernews.git
cd Cybernews

python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # Windows : copy .env.example .env
# ... éditez .env (au minimum la section Email) ...

python cybersec_rss_feed_enhanced.py --test-smtp   # ① vérifie la config SMTP
python cybersec_rss_feed_enhanced.py --dry-run     # ② digest sans envoi → ouvrez digest.html
python cybersec_rss_feed_enhanced.py               # ③ digest + envoi réel
```

Sans aucune option, le script récupère les 55+ sources, déduplique, score, enrichit (si les clés optionnelles sont définies) et envoie l'email.

### Exécution planifiée en local (alternative à GitHub Actions)

```bash
# Linux/Mac : crontab -e, puis ajoutez :
0 8 * * * cd /chemin/vers/Cybernews && ./venv/bin/python cybersec_rss_feed_enhanced.py --days 1
```

```powershell
# Windows (PowerShell) :
schtasks /create /tn "CyberNews" /tr "C:\chemin\vers\Cybernews\venv\Scripts\python.exe C:\chemin\vers\Cybernews\cybersec_rss_feed_enhanced.py --days 1" /sc daily /st 08:00
```

## ☁️ Exécution automatique avec GitHub Actions (recommandé)

Trois workflows sont inclus :

| Workflow | Déclencheur | Rôle |
|---|---|---|
| `daily-digest.yml` | tous les jours 6h UTC | génère, enrichit et diffuse le digest, publie GitHub Pages, committe l'historique |
| `ci.yml` | push / PR | lance la suite de tests |
| `feeds-health.yml` | tous les lundis | vérifie que chaque source répond encore (détecte les flux morts) |

**Mise en place (une seule fois, ~5 minutes) :**

1. **Forkez** ce dépôt sur votre compte GitHub (bouton *Fork* en haut à droite)
2. Dans **Settings → Secrets and variables → Actions → New repository secret**, ajoutez :

   | Secret | Obligatoire | Exemple / rôle |
   |---|---|---|
   | `SENDER_EMAIL` | ✅ | `vous@gmail.com` |
   | `EMAIL_PASSWORD` | ✅ | mot de passe d'application Gmail |
   | `RECIPIENT_EMAIL` | ✅ | destinataire du digest |
   | `SMTP_SERVER` | ✅ | `smtp.gmail.com` |
   | `SMTP_PORT` | ✅ | `465` |
   | `ANTHROPIC_API_KEY` | — | active la synthèse IA en français |
   | `NVD_API_KEY` | — | accélère l'enrichissement CVSS |
   | `DISCORD_WEBHOOK_URL`, `SLACK_WEBHOOK_URL` | — | diffusion Discord / Slack |
   | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | — | diffusion Telegram |

   Et dans l'onglet **Variables** (optionnel) : `KEYWORDS_INCLUDE`, `KEYWORDS_EXCLUDE`
3. Onglet **Actions** → cliquez sur **« I understand my workflows, go ahead and enable them »**
4. Testez immédiatement : **Actions → Digest quotidien CyberNews → Run workflow** (vous pouvez cocher *dry run* pour un premier essai sans email)
5. *(Optionnel)* Activez **GitHub Pages** : **Settings → Pages → Source : Deploy from a branch → `main` / `docs`**. Votre digest sera consultable en permanence sur `https://<compte>.github.io/Cybernews/`, avec archives par date et flux RSS sur `/feed.xml`

Ensuite, le digest part tout seul chaque matin à 6h UTC. Le workflow committe automatiquement l'historique (`data/state.json`) et les pages (`docs/`) après chaque envoi réussi.

## 💻 Options de la ligne de commande

| Option | Description |
|---|---|
| `--days N` | Fenêtre de récupération en jours (défaut : 2, accepte les décimales) |
| `--top N` | Nombre d'articles « À la une » (défaut : 10) |
| `--max-per-feed N` | Articles maximum par flux (défaut : 15) |
| `--output FICHIER` | Fichier de sortie du digest HTML (défaut : `digest.html`) |
| `--pages` | Publie aussi sur `docs/` (GitHub Pages + flux RSS sortant) |
| `--no-ai` | Désactive la synthèse IA |
| `--no-enrich` | Désactive l'enrichissement KEV/CVSS |
| `--no-history` | Ignore l'historique des articles déjà envoyés |
| `--dry-run` | Génère le digest sans rien envoyer |
| `--test-smtp` | Teste uniquement la connexion SMTP |
| `--check-feeds` | Vérifie la santé de toutes les sources |
| `--list-feeds` | Liste les sources configurées |

## ⚙️ Configuration (`.env`)

Voir [`.env.example`](.env.example) pour la liste complète commentée. Résumé :

| Variable | Rôle |
|---|---|
| `SENDER_EMAIL`, `EMAIL_PASSWORD`, `RECIPIENT_EMAIL`, `SMTP_SERVER`, `SMTP_PORT` | Envoi de l'email (465 = SSL, 587 = STARTTLS) |
| `DAYS_LOOKBACK` | Fenêtre par défaut en jours |
| `KEYWORDS_INCLUDE` / `KEYWORDS_EXCLUDE` | Filtres par mots-clés (séparés par des virgules) |
| `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` | Synthèse IA via l'API Claude (modèle par défaut : `claude-opus-4-8`) |
| `NVD_API_KEY` | Clé gratuite [NVD](https://nvd.nist.gov/developers/request-an-api-key) — accélère l'enrichissement CVSS |
| `DISCORD_WEBHOOK_URL`, `SLACK_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Canaux de diffusion supplémentaires |
| `SITE_URL` | URL publique du digest (GitHub Pages) |

Les anciens noms `EMAIL_SENDER` / `EMAIL_RECIPIENT` restent acceptés pour compatibilité.

## 📰 Sources (55+)

| Catégorie | Exemples |
|---|---|
| 📰 Actualités | The Hacker News, Bleeping Computer, Krebs on Security, The Record, SecurityWeek, Ars Technica, Wired... |
| 🇫🇷 Sources françaises | ZATAZ, UnderNews, Le Monde Informatique, CNIL |
| 🔬 Recherche & éditeurs | Project Zero, Talos, Unit 42, Mandiant, MSRC, Securelist, Check Point Research, The DFIR Report, PortSwigger... |
| 🏛️ CERT & gouvernemental | CERT-FR (alertes, avis, actualités), CISA, NCSC UK, SANS ISC |
| 💥 Vulnérabilités & exploits | Zero Day Initiative, Exploit-DB, Full Disclosure, r/netsec |
| 🤖 IA & émergent | OpenAI, Google AI, TechCrunch AI, MIT Tech Review |

La liste complète : `python cybersec_rss_feed_enhanced.py --list-feeds`

### Ajouter une source

```python
RSS_FEEDS.append({
    "name": "Nom de la source",
    "url": "https://exemple.com/feed/",
    "category": "Actualités",
    "weight": 1,   # bonus de score pour les sources à haut signal (0 à 4)
})
```

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Les fonctions de scoring, déduplication, filtrage, historique et rendu sont couvertes par des tests sans accès réseau (exécutés en CI à chaque push).

## 📁 Structure du projet

```
Cybernews/
├── cybersec_rss_feed_enhanced.py   # Script principal (tout le pipeline)
├── start.bat / start.sh            # Lanceurs tout-en-un (Windows / Linux-Mac)
├── requirements.txt                # Dépendances d'exécution
├── requirements-dev.txt            # Dépendances de test (pytest)
├── .env.example                    # Modèle de configuration commenté
├── tests/test_digest.py            # Suite de tests (sans réseau)
├── .github/workflows/
│   ├── daily-digest.yml            # Digest quotidien automatique
│   ├── ci.yml                      # Tests à chaque push/PR
│   └── feeds-health.yml            # Santé des sources (hebdomadaire)
├── data/state.json                 # Historique (généré, committé par le workflow)
├── docs/                           # GitHub Pages : digest, archives, feed.xml
├── digest.html                     # Dernier digest généré (local, non versionné)
└── latest_articles.json            # Données brutes du dernier run (non versionné)
```

## 🔧 Dépannage

1. **Erreur SMTP** — `python cybersec_rss_feed_enhanced.py --test-smtp` ; vérifiez le mot de passe d'application et le port (465/587)
2. **Peu d'articles** — augmentez la fenêtre (`--days 7`) ou désactivez l'historique (`--no-history`)
3. **Une source en échec** — les flux indisponibles sont ignorés et listés en fin d'exécution ; le workflow hebdomadaire `feeds-health` vous alerte si une source meurt
4. **L'enrichissement CVSS est lent** — l'API publique NVD est limitée à 5 requêtes/30 s ; ajoutez une `NVD_API_KEY` gratuite
5. **Pas de synthèse IA** — vérifiez `ANTHROPIC_API_KEY` et que le paquet `anthropic` est installé
6. **Le workflow ne committe pas l'historique** — vérifiez **Settings → Actions → General → Workflow permissions → Read and write permissions**

## 🤝 Contribution

1. Fork le projet
2. Créez une branche (`git checkout -b feature/Amelioration`)
3. Committez vos changements (la CI lance les tests automatiquement)
4. Ouvrez une Pull Request

Les ajouts de sources RSS fiables sont particulièrement bienvenus !

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE).

---

<div align="center">
  <sub>Construit avec ❤️ par servais1983</sub>
</div>
