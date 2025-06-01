# CyberNews - Agrégateur RSS de Cybersécurité et IA

## Description
CyberNews est un script Python qui agrège automatiquement les dernières actualités en cybersécurité et en intelligence artificielle depuis plus de 100 sources RSS fiables. Le script envoie quotidiennement un résumé par email des articles les plus pertinents.

## Fonctionnalités
- Agrégation de plus de 100 sources RSS en cybersécurité et IA
- Filtrage des articles des 7 derniers jours
- Nettoyage et formatage du contenu HTML
- Envoi d'un email quotidien avec mise en page professionnelle
- Support multilingue (français et anglais)
- Gestion des erreurs et des flux RSS inaccessibles
- Configuration flexible via variables d'environnement

## Prérequis
- Python 3.7 ou supérieur
- Compte email (Gmail, Outlook, etc.)
- Accès à un serveur SMTP

## Installation

1. Clonez le dépôt :
```bash
git clone https://github.com/servais1983/CyberNews.git
cd CyberNews
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

3. Créez un fichier `.env` à la racine du projet avec les variables suivantes :
```env
EMAIL_RECIPIENT=votre@email.com
EMAIL_SENDER=votre@email.com
EMAIL_PASSWORD=votre_mot_de_passe
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
EMAIL_SUBJECT_PREFIX="Actualités en Cybersécurité - "
```

## Utilisation

### Exécution manuelle
```bash
python cybersec_rss_feed_enhanced.py
```

### Exécution automatique (Linux/Unix)
Pour exécuter le script quotidiennement à 8h00 :
```bash
crontab -e
```
Ajoutez la ligne :
```
0 8 * * * /chemin/vers/python /chemin/vers/CyberNews/cybersec_rss_feed_enhanced.py
```

### Exécution automatique (Windows)
Utilisez le Planificateur de tâches Windows pour créer une tâche quotidienne.

## Structure du Projet
```
CyberNews/
├── cybersec_rss_feed_enhanced.py  # Script principal
├── requirements.txt               # Dépendances Python
├── .env                          # Configuration (à créer)
└── README.md                     # Documentation
```

## Sources RSS
Le script inclut des sources de :
- CERTs et organisations gouvernementales
- Éditeurs de sécurité majeurs
- Équipes de recherche en sécurité
- Fournisseurs de services de sécurité
- Sources académiques et scientifiques
- Sources d'actualités technologiques
- Sources spécialisées en IA

## Personnalisation

### Ajouter une nouvelle source RSS
Ajoutez une nouvelle entrée dans la liste `RSS_FEEDS` :
```python
{
    "name": "Nom de la Source",
    "url": "URL du flux RSS",
    "logo": "URL du logo",
    "max_articles": 5
}
```

### Modifier le format de l'email
Le format de l'email peut être personnalisé en modifiant la fonction `format_email_content()`.

## Dépannage

### Problèmes courants
1. **Erreur de connexion SMTP**
   - Vérifiez les paramètres SMTP dans le fichier `.env`
   - Assurez-vous que le mot de passe est correct
   - Vérifiez que le port n'est pas bloqué par votre pare-feu

2. **Aucun article récupéré**
   - Vérifiez votre connexion Internet
   - Assurez-vous que les URLs des flux RSS sont valides
   - Vérifiez les logs pour plus de détails

### Logs
Le script génère des logs détaillés dans la console. Pour les sauvegarder :
```bash
python cybersec_rss_feed_enhanced.py > logs.txt 2>&1
```

## Contribution
Les contributions sont les bienvenues ! N'hésitez pas à :
1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commiter vos changements
4. Pousser vers la branche
5. Ouvrir une Pull Request

## Licence
Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## Contact
Pour toute question ou suggestion, n'hésitez pas à ouvrir une issue sur GitHub.

## Remerciements
Merci à tous les contributeurs et aux sources RSS qui rendent ce projet possible. 