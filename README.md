
![image](cybernews.png)

# 🛡️ CyberNews - Agrégateur RSS de Cybersécurité

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</div>

## 📝 Description

CyberNews est un agrégateur RSS intelligent qui collecte et analyse les dernières actualités en cybersécurité et en intelligence artificielle depuis plus de 100 sources fiables. Le script envoie quotidiennement un résumé par email des articles les plus pertinents.

## ✨ Fonctionnalités

- 🔄 Agrégation de plus de 100 sources RSS fiables
- 🎯 Filtrage intelligent des articles
- 📧 Envoi quotidien par email
- 🌍 Support multilingue (FR/EN)
- 🔒 Gestion sécurisée des données sensibles
- ⚡ Configuration flexible

## 🚀 Prérequis

- Python 3.8 ou supérieur
- Compte email avec accès SMTP
- Accès à un serveur SMTP

## 📦 Installation

1. Clonez le dépôt :
```bash
git clone https://github.com/servais1983/Cybernews.git
cd Cybernews
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

3. Créez un fichier `.env` avec vos paramètres :
```env
EMAIL_SENDER=votre_email@exemple.com
EMAIL_PASSWORD=votre_mot_de_passe
EMAIL_RECIPIENT=destinataire@exemple.com
SMTP_SERVER=smtp.exemple.com
SMTP_PORT=587
```

## 💻 Utilisation

### Exécution manuelle
```bash
python cybersec_rss_feed_enhanced.py
```

### Exécution automatique

#### Windows
```bash
schtasks /create /tn "CyberNews" /tr "python C:\chemin\vers\cybersec_rss_feed_enhanced.py" /sc daily /st 08:00
```

#### Linux/Mac
```bash
crontab -e
# Ajoutez la ligne suivante :
0 8 * * * /usr/bin/python3 /chemin/vers/cybersec_rss_feed_enhanced.py
```

## 📁 Structure du Projet

```
CyberNews/
├── cybersec_rss_feed_enhanced.py  # Script principal
├── requirements.txt               # Dépendances
├── .env                          # Configuration (à créer)
├── .gitignore                    # Fichiers ignorés par Git
├── LICENSE                       # Licence MIT
└── README.md                     # Documentation
```

## 📰 Sources RSS

Le script agrège les actualités depuis plusieurs catégories de sources :

### 🔒 Cybersécurité
- Sources gouvernementales (ANSSI, CERT-FR, etc.)
- Blogs de sécurité (SANS, Krebs on Security, etc.)
- Médias spécialisés (Dark Reading, Security Week, etc.)

### 🤖 Intelligence Artificielle
- Blogs d'entreprises (Google AI, OpenAI, etc.)
- Médias technologiques (MIT Technology Review, etc.)
- Sources académiques (Nature, Science, etc.)

### 🇫🇷 Sources Françaises
- Médias IT (LeMagIT, ITespresso, etc.)
- Institutions (CNIL, ANSSI, etc.)
- Blogs spécialisés (Journal du Hack, etc.)

## ⚙️ Personnalisation

### Ajouter une nouvelle source RSS
```python
RSS_FEEDS.append({
    "name": "Nom de la source",
    "url": "URL du flux RSS",
    "logo": "URL du logo",
    "max_articles": 5
})
```

### Modifier le format de l'email
Le format HTML est personnalisable dans la fonction `format_email_content()`.

## 🔧 Dépannage

### Problèmes courants

1. **Erreur de connexion SMTP**
   - Vérifiez vos identifiants dans `.env`
   - Assurez-vous que le serveur SMTP est accessible

2. **Aucun article récupéré**
   - Vérifiez la connectivité internet
   - Validez les URLs des flux RSS

3. **Erreur d'encodage**
   - Assurez-vous d'utiliser UTF-8
   - Vérifiez les caractères spéciaux

## 🤝 Contribution

Les contributions sont les bienvenues ! Voici comment participer :

1. Fork le projet
2. Créez une branche (`git checkout -b feature/Amelioration`)
3. Committez vos changements (`git commit -m 'Ajout d'une fonctionnalité'`)
4. Poussez vers la branche (`git push origin feature/Amelioration`)
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 📞 Contact

Pour toute question ou suggestion :
- Ouvrez une issue sur GitHub
- Contactez-moi via [GitHub](https://github.com/servais1983)

## 🙏 Remerciements

- Tous les contributeurs
- Les sources RSS qui partagent leurs actualités
- La communauté open source

---

<div align="center">
  <sub>Construit avec ❤️ par servais1983</sub>
</div> 
