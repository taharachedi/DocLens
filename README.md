# DocLens

**Extraction d'informations à partir de documents PDF et d'images**

`Angular 19` · `Python` · `FastAPI` · `Tesseract OCR` · `PyMuPDF`

DocLens est une application web personnelle qui permet d'importer un document, d'en extraire le texte et d'identifier automatiquement certaines informations utiles.

Le projet est actuellement fonctionnel en local et continue d'évoluer. L'objectif est de construire progressivement un outil d'analyse documentaire plus flexible, fiable et simple à utiliser.

## Fonctionnalités actuelles

- **Import de documents :** fichiers PDF, PNG, JPG et JPEG.
- **Extraction de texte :** lecture directe des PDF numériques avec PyMuPDF et reconnaissance OCR des images ou des pages scannées avec Tesseract.
- **Détection de champs :** extraction de certaines informations comme les noms, dates, adresses email, numéros de téléphone et montants.
- **Affichage des résultats :** interface Angular présentant les informations détectées et le texte complet extrait.
- **Validation des fichiers :** contrôle du format, de la taille maximale de 10 Mo et de la limite de 10 pages PDF.
- **Gestion des erreurs :** messages d'avertissement et journalisation technique.
- **Tests automatisés :** vérification des routes principales de l'API et de certaines règles d'extraction.

L'extraction des champs repose actuellement sur des règles Python. Aucun modèle LLM n'est encore intégré.

## Architecture technique

L'application est organisée en deux parties :

**Frontend — Angular 19**

L'interface permet de sélectionner un document, de lancer son analyse et de consulter les résultats.

**Backend — Python / FastAPI**

Le backend reçoit le fichier, vérifie sa validité, extrait son contenu et retourne les informations détectées au format JSON.

```text
                  UTILISATEUR
                       |
                       v
              INTERFACE ANGULAR
                localhost:4200
                       |
                       | HTTP POST /documents
                       v
                  API FASTAPI
                localhost:8000
                       |
             Validation du fichier
                       |
              Extraction du texte
                  /         \
                 v           v
              PyMuPDF     Tesseract
              PDF texte   OCR images
                  \         /
                   v       v
               TEXTE EXTRAIT
                       |
                       v
              RÈGLES D'EXTRACTION
                       |
                       v
                 RÉSULTAT JSON
                       |
                       v
              AFFICHAGE ANGULAR
```

Les documents sont traités en mémoire. Cette version ne conserve pas les fichiers importés et n'envoie pas leur contenu à un service LLM externe.

## Exemples de tests

### 1. Facture fictive — Extraction réussie

Un premier test a été réalisé avec une image claire contenant des informations fictives.

| Champ | Valeur extraite |
|---|---|
| Type de document | Facture |
| Nom | Jean Dupont |
| Date | 04/11/2026 |
| Montant | 125,50 EUR |
| Email | jean.dupont@example.com |
| Statut | completed |

Les quatre champs attendus ont été correctement extraits sur cet exemple.

Ce résultat valide le fonctionnement de la chaîne d'analyse sur un document simple et lisible. Il ne constitue pas une mesure générale de précision du système.

### 2. Passeport scanné — Extraction partielle

Un second test a été réalisé sur un passeport scanné.

**Résultats observés :**

- Le document a été reconnu comme un passeport.
- L'OCR a récupéré une partie du texte.
- Une date a été détectée automatiquement.
- Les autres informations d'identité n'ont pas été correctement structurées.

Ce test met en évidence les limites actuelles de la reconnaissance OCR et des règles d'extraction sur les documents complexes.

Les données personnelles du document testé ne sont pas publiées.

## Installation et exécution

### Prérequis

Pour exécuter DocLens en local, il faut disposer de :

- Python 3.11 ou supérieur.
- Node.js compatible avec Angular 19 et npm.
- Tesseract OCR installé sur l'ordinateur.
- Git pour récupérer le dépôt.

Sur Windows, Tesseract est recherché dans :

`C:\Program Files\Tesseract-OCR\tesseract.exe`

Sinon, l'exécutable doit être accessible depuis le `PATH`.

Pour la reconnaissance du français, les données linguistiques `fra` doivent également être installées.

### 1. Récupérer le projet

```bash
git clone https://github.com/taharachedi/DocLens.git
cd DocLens
```

### 2. Démarrer le backend

Dans un premier terminal PowerShell :

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Le backend est accessible sur :

**http://127.0.0.1:8000**

La documentation interactive de l'API est disponible sur :

**http://127.0.0.1:8000/docs**

### 3. Démarrer le frontend

Dans un deuxième terminal, depuis la racine du projet :

```powershell
cd frontend
npm ci
npm start
```

Ouvrir ensuite :

**http://localhost:4200**

L'application est prête à recevoir un document si les deux services sont démarrés.

## API REST

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/` | Accueil de l'API |
| GET | `/health` | Vérification de l'état du service |
| POST | `/documents` | Import et analyse d'un document |

L'endpoint `/documents` reçoit un fichier au format `multipart/form-data` et retourne une réponse JSON contenant les résultats de l'analyse.

## Tests et qualité du code

Le backend contient des tests automatisés pour les routes principales et certaines règles d'extraction.

Pour lancer les tests :

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Pour vérifier la compilation du frontend :

```powershell
cd frontend
npm ci
npm run build
```

Ces commandes permettent de vérifier certains aspects du fonctionnement, mais ne garantissent pas encore la fiabilité de l'extraction sur tous les documents.

## Limites actuelles

DocLens est un prototype fonctionnel, pas une application de production.

Les principales limites sont les suivantes :

- L'extraction structurée repose sur des règles Python, sans LLM.
- La qualité des résultats dépend fortement de la lisibilité des documents.
- Certains champs peuvent être absents ou incorrectement détectés.
- Le traitement des documents est synchrone.
- Le traitement de lots et le suivi des tâches asynchrones ne sont pas disponibles.
- Aucune base de données ni authentification n'est intégrée.
- L'application n'est pas encore déployée sur une infrastructure distante.

Les résultats importants doivent être vérifiés à partir du document original.

## Améliorations prévues

Le développement de DocLens se poursuit de manière progressive.

**1. Amélioration de l'OCR**

Améliorer le prétraitement des images, la reconnaissance des documents scannés et la détection des champs complexes.

**2. Extraction assistée par LLM**

Étudier l'intégration d'une API LLM pour obtenir des résultats structurés, avec validation des réponses à l'aide de Pydantic.

**3. Traitement asynchrone**

Ajouter la gestion de plusieurs documents, le suivi des tâches et une stratégie de traitement des erreurs.

**4. Évaluation des performances**

Constituer des jeux de données fictifs avec des valeurs attendues pour mesurer la qualité de l'extraction et comparer différentes approches.

**5. Persistance et suivi**

Étudier l'ajout de PostgreSQL pour conserver les résultats d'expérimentations, ainsi que des journaux et indicateurs de monitoring.

**6. Industrialisation**

Renforcer les tests, la sécurité, l'authentification et la chaîne CI/CD avant d'envisager un déploiement.

Ces fonctionnalités constituent des pistes d'évolution et ne sont pas encore implémentées.

## Confidentialité

DocLens est destiné à des démonstrations et à des expérimentations locales.

Il est recommandé d'utiliser uniquement des documents fictifs ou anonymisés. Aucun document personnel, mot de passe, fichier `.env` ou clé API ne doit être publié dans le dépôt.

## Auteur

**Taha Rachedi**

Projet personnel de développement web et d'extraction d'informations documentaires.

GitHub : [taharachedi](https://github.com/taharachedi)

---

*DocLens — Projet personnel en cours de développement et d'amélioration.
