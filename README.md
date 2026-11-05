# DocLens

**Intelligent Document Extraction & Analysis**

`Angular 19` · `TypeScript` · `Python 3.11+` · `FastAPI` · `Tesseract OCR` · `PyMuPDF` · `Pillow`

**Statut : Prototype fonctionnel en local — développement et améliorations en cours.**

---

## Présentation

**DocLens** est une application web d'analyse documentaire permettant d'importer des fichiers PDF ou des images, d'en extraire automatiquement le texte et d'identifier certaines informations structurées.

L'application combine trois approches :

- **Extraction PDF** : récupération directe du texte des documents numériques avec PyMuPDF.
- **Reconnaissance OCR** : lecture du texte présent dans les images et documents scannés avec Tesseract.
- **Extraction structurée** : analyse du texte à l'aide de règles Python pour détecter des informations telles que les noms, dates, adresses email et montants.

Le projet repose sur une architecture frontend/backend avec **Angular 19** pour l'interface utilisateur et **Python/FastAPI** pour le traitement documentaire.

L'objectif est de développer progressivement un outil simple à utiliser, capable d'analyser différents documents tout en améliorant la précision et la fiabilité des résultats.

## Fonctionnalités actuelles

### 1. Import et validation des documents

- Import de fichiers PDF, PNG, JPG et JPEG.
- Taille maximale de 10 Mo par fichier.
- Limite de 10 pages par document PDF.
- Vérification du format et gestion des fichiers invalides.
- Affichage de messages d'erreur en cas de problème.

### 2. Extraction du texte

**Documents PDF numériques**

Le texte est extrait directement avec PyMuPDF lorsqu'il est disponible.

**Images et documents scannés**

Tesseract OCR permet de reconnaître les caractères présents dans les images et les pages PDF sans texte exploitable.

La qualité des résultats dépend notamment de la résolution, de la netteté, de l'orientation et de la lisibilité du document.

### 3. Identification des documents

DocLens utilise le contenu textuel pour identifier certaines catégories documentaires.

Les catégories prises en compte peuvent notamment comprendre :

- Factures.
- Passeports et documents d'identité.
- CV.
- Contrats et attestations.
- Documents non classés.

Cette classification repose sur des règles et des indices textuels. Elle peut donc être incomplète ou incorrecte.

### 4. Extraction des informations structurées

DocLens recherche automatiquement plusieurs types d'informations dans le texte extrait.

| Catégorie | Exemples d'informations |
|---|---|
| Identité | Nom, prénom |
| Contact | Adresse email, téléphone |
| Dates | Dates présentes dans le document |
| Finances | Montants de facture |
| Documents administratifs | Informations détectables à partir du texte |

Les champs réellement retournés dépendent du document et des règles d'extraction disponibles.

**Important :** les informations ne sont pas garanties exactes et doivent être vérifiées à partir du document original.

### 5. Traitement des documents d'identité

Les passeports et cartes d'identité représentent des documents plus complexes en raison de leur mise en page, de la présence de plusieurs langues et de la qualité variable des images.

DocLens peut récupérer leur texte par OCR, mais l'extraction fiable de tous les champs d'identité nécessite encore des améliorations.

L'exploitation avancée de la **MRZ (Machine Readable Zone)**, notamment la validation des chiffres de contrôle et la prise en charge complète des différents formats, fait partie des points techniques à consolider et à tester.

### 6. Affichage des résultats

Après l'analyse d'un document, l'interface présente :

- Le nom du fichier traité.
- Le statut du traitement.
- Le type de document identifié.
- La méthode d'extraction utilisée.
- Les informations détectées.
- Le texte complet extrait.
- Les avertissements éventuels.

L'utilisateur peut ainsi consulter les résultats et identifier les informations nécessitant une vérification.

## Exemples de fonctionnement

### Exemple 1 — Facture fictive

Sur une image simple et lisible contenant un nom, une date, un montant et une adresse email, DocLens peut identifier les informations suivantes :

| Champ | Résultat d'exemple |
|---|---|
| Type de document | Facture |
| Nom | Jean Dupont |
| Date | 04/11/2026 |
| Montant | 125,50 EUR |
| Email | jean.dupont@example.com |
| Méthode | Tesseract OCR |

Cet exemple illustre le fonctionnement de l'extraction sur un document de test simple.

### Exemple 2 — Document d'identité

Sur un passeport scanné, DocLens peut reconnaître une partie du texte et détecter certaines dates.

Cependant, les informations d'identité peuvent être incomplètes ou incorrectes lorsque l'OCR rencontre des difficultés.

L'application signale alors les limites de reconnaissance afin d'encourager la vérification manuelle.

**Ces deux exemples montrent à la fois les possibilités actuelles de l'application et les améliorations encore nécessaires.**

## Architecture technique

DocLens utilise une architecture web séparant l'interface utilisateur du traitement documentaire.

### Frontend — Angular 19

Le frontend permet de sélectionner un fichier, de lancer son analyse et de consulter les informations extraites.

### Backend — Python / FastAPI

Le backend assure la validation des documents, la lecture des PDF, la reconnaissance OCR et l'extraction des champs.

Il expose une API REST utilisée par Angular.

### Flux de traitement

```text
                UTILISATEUR
                     |
                     v
              INTERFACE ANGULAR
               localhost:4200
                     |
                     | POST /documents
                     v
                 FASTAPI
               localhost:8000
                     |
                     v
             VALIDATION DU FICHIER
                     |
                     v
             ANALYSE DU DOCUMENT
                     |
            +--------+--------+
            |                 |
            v                 v
       PDF numérique     Image / PDF scanné
            |                 |
            v                 v
         PyMuPDF       Préparation de l'image
            |                 |
            |                 v
            |            Tesseract OCR
            |                 |
            +--------+--------+
                     |
                     v
                TEXTE EXTRAIT
                     |
                     v
          DÉTECTION DU TYPE DE DOCUMENT
                     |
                     v
           EXTRACTION DES INFORMATIONS
                     |
                     v
              RÉPONSE JSON
                     |
                     v
               INTERFACE ANGULAR
```

## Technologies utilisées

| Technologie | Rôle |
|---|---|
| Angular 19 | Interface web |
| TypeScript | Développement frontend |
| Python | Traitement documentaire |
| FastAPI | API REST |
| Pydantic | Validation et structuration des réponses |
| PyMuPDF | Lecture et extraction des PDF |
| Tesseract OCR | Reconnaissance optique des caractères |
| pytesseract | Utilisation de Tesseract depuis Python |
| Pillow | Manipulation et préparation des images |
| pytest | Tests automatisés backend |

## Structure du projet

```text
DocLens/
|
|-- backend/
|   |-- main.py
|   |-- requirements.txt
|   |-- requirements-dev.txt
|   |
|   `-- tests/
|       `-- test_main.py
|
|-- frontend/
|   |-- public/
|   |-- src/
|   |   |-- app/
|   |   |-- main.ts
|   |   `-- styles.css
|   |
|   |-- angular.json
|   |-- package.json
|   `-- package-lock.json
|
|-- .gitignore
`-- README.md
```

Le dossier `backend` contient l'API Python et les tests associés.

Le dossier `frontend` contient l'application Angular, ses composants et sa configuration.

## Installation et exécution

### Prérequis

Avant de commencer, installer :

- Python 3.11 ou une version compatible supérieure.
- Node.js et npm compatibles avec Angular 19.
- Tesseract OCR.
- Git.

Sous Windows, Tesseract est généralement installé dans :

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Vérifier que Tesseract est accessible au programme et installer les données linguistiques nécessaires, notamment `fra` et `eng` pour le français et l'anglais.

### Étape 1 — Cloner le dépôt

Ouvrir PowerShell :

```powershell
git clone https://github.com/taharachedi/DocLens.git
cd DocLens
```

### Étape 2 — Démarrer le backend

Depuis la racine du projet :

```powershell
cd backend

py -m venv .venv

.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Une fois le serveur démarré :

**API :** http://127.0.0.1:8000

**Documentation Swagger :** http://127.0.0.1:8000/docs

### Étape 3 — Démarrer le frontend

Ouvrir un deuxième terminal PowerShell et se placer dans le dossier `frontend` du projet :

```powershell
cd frontend

npm ci

npm start
```

Ouvrir ensuite :

**Application web :** http://localhost:4200

Les serveurs Angular et FastAPI doivent fonctionner simultanément.

### Étape 4 — Utiliser l'application

1. Ouvrir l'interface Angular.
2. Sélectionner un fichier PDF ou une image.
3. Lancer l'analyse.
4. Consulter le type de document, les champs détectés et le texte extrait.
5. Vérifier les résultats à partir du document original.

## API REST

L'API FastAPI expose les endpoints suivants :

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/` | Informations sur l'application |
| GET | `/health` | Vérification de l'API |
| POST | `/documents` | Import et analyse d'un document |

L'endpoint `POST /documents` accepte un fichier envoyé avec le format `multipart/form-data`.

Selon la version de l'API, la réponse JSON peut contenir notamment :

- `filename` : nom du fichier.
- `status` : statut du traitement.
- `document_type` : catégorie identifiée.
- `extraction_method` : méthode de lecture utilisée.
- `extracted_text` : texte extrait.
- `fields` : informations structurées.
- `warnings` : avertissements.

La documentation interactive disponible sur `/docs` permet de consulter le schéma exact des requêtes et des réponses.

## Tests et vérifications

Le projet comprend des tests backend dans le dossier `backend/tests`.

### Tests Python

Depuis le dossier `backend`, avec l'environnement virtuel activé ou en utilisant son interpréteur :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

.\.venv\Scripts\python.exe -m pytest -q
```

### Vérification Angular

Depuis le dossier `frontend` :

```powershell
npm ci

npm run build
```

Ces vérifications permettent de contrôler certains comportements techniques et la compilation, mais ne garantissent pas la précision de l'extraction documentaire.

## Limites actuelles

DocLens est un **projet personnel expérimental**, fonctionnel en local et en cours d'amélioration.

Les principales limites sont les suivantes :

- L'extraction structurée repose principalement sur des règles Python et non sur un modèle LLM.
- La précision dépend fortement de la qualité des documents.
- Certains champs peuvent être absents ou mal reconnus.
- Les documents administratifs complexes nécessitent des traitements spécifiques.
- Le traitement est actuellement synchrone.
- L'analyse de lots n'est pas encore disponible.
- Aucune base de données n'est intégrée.
- L'application ne dispose pas encore d'un système d'authentification.
- Aucun déploiement cloud n'est actuellement proposé.

DocLens n'est pas destiné à être utilisé comme une solution de production pour des documents sensibles.

## Perspectives d'amélioration

Le développement du projet se poursuit autour de plusieurs axes.

### Amélioration de la reconnaissance documentaire

- Renforcement de la qualité OCR.
- Meilleure gestion des images difficiles.
- Amélioration de la détection des types de documents.
- Consolidation de l'extraction des champs d'identité.
- Tests plus approfondis sur les zones MRZ.

### Extraction assistée par intelligence artificielle

- Étude d'une intégration optionnelle de modèles LLM.
- Extraction structurée à partir de consignes configurables.
- Validation des réponses générées.
- Comparaison de plusieurs méthodes d'extraction.

### Évaluation et fiabilité

- Constitution de jeux de tests fictifs et anonymisés.
- Mesure de la précision des champs extraits.
- Comparaison des résultats avec des données de référence.
- Amélioration de la couverture des tests automatisés.

### Évolution de l'architecture

- Traitement asynchrone.
- Analyse de plusieurs documents.
- Persistance éventuelle avec PostgreSQL.
- Renforcement de la sécurité.
- Mise en place d'une intégration continue et d'un déploiement.

**Ces fonctionnalités représentent des perspectives de développement et ne doivent pas être considérées comme déjà implémentées.**

## Confidentialité et sécurité

DocLens est actuellement destiné aux expérimentations et démonstrations locales.

Les documents sont traités sans base de données de stockage et aucun service LLM externe n'est intégré.

Pour les démonstrations, il est recommandé d'utiliser uniquement des documents fictifs ou anonymisés.

Ne jamais publier dans le dépôt :

- Des passeports, cartes d'identité ou documents personnels réels.
- Des mots de passe ou clés API.
- Des fichiers de configuration contenant des secrets.
- Des données confidentielles.

## Auteur

**Taha Rachedi**

Projet personnel de développement web, traitement documentaire et extraction d'informations.

**GitHub :** https://github.com/taharachedi

**Dépôt du projet :** https://github.com/taharachedi/DocLens

---

*DocLens — Intelligent Document Extraction & Analysis*

*Projet en développement continu.*
