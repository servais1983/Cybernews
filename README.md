
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

## 🚀 Démarrage rapide (en local)

```bash
git clone https://github.com/servais1983/Cybernews.git
cd Cybernews
pip install -r requirements.txt

cp .env.example .env   # puis éditez .env (au minimum la section Email)

python cybersec_rss_feed_enhanced.py --test-smtp   # vérifie la config SMTP
python cybersec_rss_feed_enhanced.py --dry-run     # digest sans envoi → digest.html
python cybersec_rss_feed_enhanced.py               # digest + diffusion
```

> 💡 **Gmail** : utilisez un [mot de passe d'application](https://myaccount.google.com/apppasswords), pas votre mot de passe principal.

## ☁️ Exécution automatique avec GitHub Actions (recommandé)

Trois workflows sont inclus :

| Workflow | Déclencheur | Rôle |
|---|---|---|
| `daily-digest.yml` | tous les jours 6h UTC | génère, enrichit et diffuse le digest, publie GitHub Pages, committe l'historique |
| `ci.yml` | push / PR | lance la suite de tests |
| `feeds-health.yml` | tous les lundis | vérifie que chaque source répond encore (détecte les flux morts) |

**Mise en place :**

1. Forkez ou clonez ce dépôt sur votre compte GitHub
2. Dans **Settings → Secrets and variables → Actions**, ajoutez les *secrets* :
   - obligatoires : `SENDER_EMAIL`, `EMAIL_PASSWORD`, `RECIPIENT_EMAIL`, `SMTP_SERVER`, `SMTP_PORT`
   - optionnels : `ANTHROPIC_API_KEY` (synthèse IA), `NVD_API_KEY` (CVSS plus rapide), `DISCORD_WEBHOOK_URL`, `SLACK_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
   - et en *variables* (optionnel) : `KEYWORDS_INCLUDE`, `KEYWORDS_EXCLUDE`
3. Activez les workflows dans l'onglet **Actions**
4. *(Optionnel)* Activez **GitHub Pages** : **Settings → Pages → Source : Deploy from a branch → `main` / `docs`**. Votre digest sera consultable en permanence sur `https://<compte>.github.io/Cybernews/`, avec archives par date et flux RSS sur `/feed.xml`

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

## 🔧 Dépannage

1. **Erreur SMTP** — `python cybersec_rss_feed_enhanced.py --test-smtp` ; vérifiez le mot de passe d'application et le port (465/587)
2. **Peu d'articles** — augmentez la fenêtre (`--days 7`) ou désactivez l'historique (`--no-history`)
3. **Une source en échec** — les flux indisponibles sont ignorés et listés en fin d'exécution ; le workflow hebdomadaire `feeds-health` vous alerte si une source meurt
4. **L'enrichissement CVSS est lent** — l'API publique NVD est limitée à 5 requêtes/30 s ; ajoutez une `NVD_API_KEY` gratuite
5. **Pas de synthèse IA** — vérifiez `ANTHROPIC_API_KEY` et que le paquet `anthropic` est installé

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
