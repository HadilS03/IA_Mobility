# IA Mobility

Bienvenue sur le dépôt du projet IA Mobility. Le projet utilise une architecture Monorepo pour centraliser le Frontend, le Backend et les services d'IA.

## Etat Actuel du Projet

Le squelette du monorepo est initialisé sur la branche main.

### Tâches déjà accomplies (Teddy):

* Infrastructure : Initialisation du Monorepo avec npm workspaces.
* Frontend : Initialisation du projet React + Vite + TypeScript.
* Cartographie : Installation de Leaflet et intégration dans le projet.
* Composant Map : Modification de App.tsx pour afficher une carte interactive fonctionnelle avec correction du rendu des icônes.

---

## Installation et Utilisation

Si vous récupérez ce projet via GitHub, vous n'avez pas besoin de réinstaller Node.js ou de recréer les dossiers si vous avez déjà l'environnement prêt.

### 1. Installation des dépendances

À la racine du projet, lancez la commande suivante pour installer tous les paquets :

```bash
npm install

```

### 2. Lancer le Frontend

Pour tester l'interface et la carte :

```bash
npm run dev -w @ia-mobility/frontend

```

---

## Rappel bref des tâches (regarder le trello)

### Frontend (Lead: Teddy)

* Déjà fait : Init React/Vite, Intégration Leaflet, Config App.tsx.
* À faire : Créer les formulaires d'adresses et gérer l'affichage des 5 trajets optimisés.

### Authentification et RGPD (Lead: Laurent)

* Implémenter la création de compte et connexion.
* Configurer BetterAuth avec hachage Argon2.
* Mettre en place l'OAuth Google et la protection CSRF.
* Gérer le schéma "Users" en base de données.

### IA et Moteur de recherche (Lead: Mamor)

* Collecter les données de parking (Open Data).
* Feature engineering et entraînement du modèle Random Forest.
* Créer l'endpoint /predict via FastAPI.

### Infrastructure et Smart Search (Lead: Boubacar)

* Configuration de PostgreSQL avec Docker.
* Mise en place de Drizzle ORM.
* Intégration des APIs (Google Directions, Météo, Trafic) et agrégation des données.

---

## Structure du dossier apps/

* frontend/ : Interface React + Leaflet (déjà configurée).
* backend/ : API Node.js (à développer par Laurent).
* ai-service/ : Service Python FastAPI (à développer par Mamor).

---

## Notes importantes

* Leaflet : J'ai dû modifier App.tsx pour afficher la carte.
* Git : Travaillez sur vos branches respectives et faites des Pull Requests vers main.



