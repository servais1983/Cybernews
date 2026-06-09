
![image](cybernews.png)

# 🛡️ CyberNews - Agrégateur RSS intelligent de Cybersécurité

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Sources-55%2B-orange" alt="Sources">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</div>

## 📝 Description

CyberNews collecte en parallèle les actualités de **plus de 55 sources fiables** (médias spécialisés, chercheurs, éditeurs de sécurité, CERT et agences gouvernementales), puis génère un **digest HTML intelligent** envoyé par email et sauvegardé localement.

Ce qui le rend différent d'un simple agrégateur :

- 🧠 **Score de pertinence** : chaque article est noté selon des signaux forts (zero-day, exploitation active, RCE, ransomware, fuite de données, CVE, KEV...), la fraîcheur et la fiabilité de la source
- 🔥 **Section "À la une"** : les 10 articles les plus critiques du jour en tête de digest
- 🧹 **Déduplication** : la même histoire couverte par 5 médias n'apparaît qu'une fois (la version la mieux notée est conservée)
- 🔗 **Détection des CVE** : les identifiants CVE sont extraits et reliés automatiquement à la base [NVD](https://nvd.nist.gov/)
- ⚡ **Récupération parallèle** : les 55+ flux sont interrogés en quelques secondes (avec retry et timeout)
- 🤖 **Zéro infrastructure** : un workflow GitHub Actions envoie le digest chaque matin — aucun PC allumé, aucun cron à configurer
- 🔒 **Sécurisé** : secrets dans `.env` ou GitHub Secrets, contenu externe échappé dans le HTML

## 🚀 Démarrage rapide (en local)

```bash
git clone https://github.com/servais1983/Cybernews.git
cd Cybernews
pip install -r requirements.txt

# Configuration
cp .env.example .env   # puis éditez .env avec vos identifiants SMTP

# Vérifiez la connexion SMTP
python cybersec_rss_feed_enhanced.py --test-smtp

# Générez un digest sans envoyer d'email (ouvre ensuite digest.html)
python cybersec_rss_feed_enhanced.py --dry-run

# Digest + envoi par email
python cybersec_rss_feed_enhanced.py
```

> 💡 **Gmail** : utilisez un [mot de passe d'application](https://myaccount.google.com/apppasswords), pas votre mot de passe principal.

## ☁️ Exécution automatique avec GitHub Actions (recommandé)

Le dépôt inclut un workflow ([`.github/workflows/daily-digest.yml`](.github/workflows/daily-digest.yml)) qui envoie le digest **tous les jours à 6h00 UTC**, sans aucune machine à maintenir :

1. Forkez ou clonez ce dépôt sur votre compte GitHub
2. Dans **Settings → Secrets and variables → Actions**, ajoutez les secrets :
   - `SENDER_EMAIL`, `EMAIL_PASSWORD`, `RECIPIENT_EMAIL`, `SMTP_SERVER`, `SMTP_PORT`
3. Activez les workflows dans l'onglet **Actions**

Vous pouvez aussi lancer le workflow manuellement (**Run workflow**) en choisissant la fenêtre de jours, ou en mode `dry-run`. Le digest HTML est publié en artefact à chaque exécution.

## 💻 Options de la ligne de commande

| Option | Description |
|---|---|
| `--days N` | Fenêtre de récupération en jours (défaut : 2, accepte les décimales) |
| `--top N` | Nombre d'articles dans la section "À la une" (défaut : 10) |
| `--max-per-feed N` | Nombre maximum d'articles par flux (défaut : 15) |
| `--output FICHIER` | Fichier de sortie du digest HTML (défaut : `digest.html`) |
| `--dry-run` | Génère le digest sans envoyer d'email |
| `--test-smtp` | Teste uniquement la connexion SMTP |
| `--list-feeds` | Liste les sources configurées |

### Exécution planifiée en local (alternative à GitHub Actions)

```bash
# Linux/Mac : crontab -e
0 8 * * * cd /chemin/vers/Cybernews && /usr/bin/python3 cybersec_rss_feed_enhanced.py --days 1
```

```powershell
# Windows
schtasks /create /tn "CyberNews" /tr "python C:\chemin\vers\cybersec_rss_feed_enhanced.py --days 1" /sc daily /st 08:00
```

## ⚙️ Configuration (`.env`)

```env
SENDER_EMAIL=votre_email@gmail.com
EMAIL_PASSWORD=votre_mot_de_passe_application
RECIPIENT_EMAIL=destinataire@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465          # 465 = SSL, 587 = STARTTLS (les deux sont supportés)
DAYS_LOOKBACK=2        # optionnel
```

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

## 🔧 Dépannage

1. **Erreur de connexion SMTP** — lancez `python cybersec_rss_feed_enhanced.py --test-smtp` ; vérifiez le mot de passe d'application et le port (465 ou 587)
2. **Peu d'articles** — augmentez la fenêtre avec `--days 7`
3. **Un flux est en échec** — les flux indisponibles sont ignorés et listés en fin d'exécution ; le digest est généré quand même

## 🤝 Contribution

1. Fork le projet
2. Créez une branche (`git checkout -b feature/Amelioration`)
3. Committez vos changements
4. Ouvrez une Pull Request

Les ajouts de sources RSS fiables sont particulièrement bienvenus !

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE).

---

<div align="center">
  <sub>Construit avec ❤️ par servais1983</sub>
</div>
