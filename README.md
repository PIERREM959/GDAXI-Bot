# GDAXI Bot

Bot de trading simulé pour GDAXI basé sur Yahoo Finance.

## Fonctionnalités
- Trading entre 09:00 et 17:30 (heure de Paris)
- Achat 1 DAX si moyenne de la dernière bougie > précédente
- Email toutes les heures avec solde USD et DAX
- Vente à 17:30 au dernier prix
- Déploiement sur Render

## Installation
```bash
pip install -r requirements.txt
