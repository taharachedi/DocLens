# DocLens

**Intelligent Document Extraction & Analysis**

`Angular 19` · `Python 3.11+` · `FastAPI` · `Tesseract OCR` · `PyMuPDF` · `Pillow`

DocLens est une application web permettant d'analyser des documents PDF et des images afin d'en extraire automatiquement le texte et les informations structurées.

L'application combine l'extraction de texte des PDF numériques, la reconnaissance optique de caractères (OCR) et des règles intelligentes de détection pour identifier différents types de documents et leurs informations principales.

Le projet est développé avec Angular pour l'interface utilisateur et Python/FastAPI pour le traitement documentaire.

## Fonctionnalités

### 1. Import et validation des documents
- Import de fichiers PDF, PNG, JPG et JPEG.
- Taille maximale : 10 Mo.
- Limite de 10 pages par document PDF.
- Vérification du format et de la validité des fichiers.

### 2. Extraction intelligente du texte
- Extraction directe du texte des PDF numériques avec PyMuPDF.
- Reconnaissance OCR des images et des documents scannés avec Tesseract.
- Prétraitement des images : redimensionnement, amélioration du contraste, netteté et binarisation.
- Redressement des images pour améliorer la reconnaissance.
- Estimation de la confiance de reconnaissance OCR.

### 3. Détection automatique du type de document

DocLens identifie plusieurs catégories de documents :

- Passeport.
- Carte d'identité.
- Facture.
- CV.
- Contrat.
- Attestation.
- Autres documents.

### 4. Extraction des informations

L'application peut identifier différentes informations selon le contenu du document :

| Catégorie | Informations détectées |
|---|---|
| Identité | Nom, prénom, sexe, nationalité |
| Dates | Date, naissance, délivrance, expiration |
| Contact | Adresse email, téléphone |
| Documents | Numéro de document |
| Finances | Montant, IBAN |
| Passeports | Informations structurées de la zone MRZ |

### 5. Reconnaissance MRZ des passeports

DocLens intègre un traitement spécifique des zones MRZ (Machine Readable Zone) des passeports.

- Détection des lignes MRZ.
- Prise en charge des formats TD1 et TD3.
- Extraction des informations d'identité.
- Vérification des chiffres de contrôle.
- Correction de certaines confusions de caractères OCR.

### 6. Résultats et gestion des erreurs

- Affichage du texte extrait.
- Présentation des informations détectées.
- Identification de la méthode d'extraction utilisée.
- Affichage du niveau de confiance OCR lorsqu'il est disponible.
- Messages d'avertissement lorsque la reconnaissance est insuffisante.

## Architecture technique

DocLens repose sur une architecture frontend/backend.

**Frontend — Angular 19**

Interface utilisateur permettant d'importer les documents et de consulter les résultats de l'analyse.

**Backend — Python / FastAPI**

API REST responsable de la validation des fichiers, du traitement OCR, de l'extraction des informations et de la génération des résultats JSON.

### Flux de traitement

```text
                 UTILISATEUR
                      |
                      v
               ANGULAR 19
                localhost:4200
                      |
                      | HTTP POST
                      | /documents
                      v
                FASTAPI
                localhost:8000
                      |
                      v
              VALIDATION FICHIER
                      |
                      v
             ANALYSE DU DOCUMENT
                      |
              +-------+-------+
              |               |
              v               v
           PyMuPDF         Tesseract
         PDF numérique      OCR
                              |
                     Prétraitement image
                              |
                     Reconnaissance MRZ
              |               |
              +-------+-------+
                      |
                      v
                TEXTE EXTRAIT
                      |
                      v
             EXTRACTION DES CHAMPS
                      |
                      v
              DÉTECTION DU DOCUMENT
                      |
                      v
                 RÉSULTAT JSON
                      |
                      v
                ANGULAR 19
```

## Technologies utilisées

| Technologie | Utilisation |
|---|---|
| Angular 19 | Interface utilisateur |
| TypeScript | Développement frontend |
| Python | Traitement documentaire |
| FastAPI | API REST |
| Pydantic | Validation et structuration des données |
| PyMuPDF | Extraction du texte PDF |
| Tesseract OCR | Reconnaissance de texte |
| pytesseract | Intégration Python de Tesseract |
| Pillow | Prétraitement des images |
| pytest | Tests automatisés |

## Structure du projet

```text
DocLens/
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   │
│   └── tests/
│       └── test_main.py
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   │   ├── app.component.ts
│   │   │   ├── app.component.html
│   │   │   ├── app.component.css
│   │   │   └── app.component.spec.ts
│   │   ├── main.ts
│   │   └── styles.css
│   │
│   ├── angular.json
│   ├── package.json
│   └── package-lock.json
│
├── .gitignore
└── README.md
```

## Installation et exécution

### Prérequis

- Python 3.11 ou supérieur.
- Node.js et npm.
- Tesseract OCR.
- Git.

Tesseract doit être installé et accessible depuis le PATH.

Sous Windows, l'installation standard se trouve généralement ici :

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Pour la reconnaissance du français et de l'anglais, installer les données linguistiques `fra` et `eng`.

### 1. Cloner le dépôt

```bash
git clone https://github.com/taharachedi/DocLens.git
cd DocLens
```

### 2. Installer et démarrer le backend

Sous Windows PowerShell :

```powershell
cd backend

py -m venv .venv

.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Le backend sera accessible à :

http://127.0.0.1:8000

Documentation interactive de l'API :

http://127.0.0.1:8000/docs

### 3. Installer et démarrer le frontend

Dans un deuxième terminal, depuis la racine du projet :

```powershell
cd frontend

npm ci

npm start
```

L'interface sera accessible à :

http://localhost:4200

Les deux services doivent être démarrés pour utiliser l'application.

## API REST

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/` | Informations sur l'application |
| GET | `/health` | Vérification de l'état de l'API |
| POST | `/documents` | Import et analyse d'un document |

L'endpoint `/documents` reçoit un fichier via `multipart/form-data`.

La réponse JSON contient notamment :

- `filename` : nom du fichier.
- `status` : statut du traitement.
- `document_type` : type de document identifié.
- `extraction_method` : méthode d'extraction utilisée.
- `extracted_text` : texte reconnu.
- `fields` : informations structurées.
- `champs` : liste des champs détectés.
- `confiance_ocr` : estimation de la confiance OCR.
- `processed_at` : date du traitement.
- `warnings` : avertissements éventuels.

## Tests et qualité

Le dépôt contient des tests backend dans `backend/tests/`.

Installation des dépendances de développement :

```powershell
cd backend
python -m pip install -r requirements-dev.txt
```

Exécution des tests :

```powershell
python -m pytest -q
```

Compilation du frontend :

```powershell
cd frontend
npm ci
npm run build
```

Ces vérifications ne constituent pas une garantie de précision de l'extraction sur tous les documents.

## Limites actuelles

DocLens est un projet personnel fonctionnel en environnement local, encore en développement.

Ses principales limites sont :

- L'extraction structurée repose principalement sur des règles Python.
- Aucun modèle LLM n'est actuellement intégré.
- Les résultats dépendent de la qualité des documents et de l'OCR.
- Certains champs peuvent être absents ou incorrectement détectés.
- Le traitement est synchrone.
- Le traitement de lots n'est pas encore disponible.
- Aucune base de données ni authentification n'est intégrée.
- L'application n'est pas encore déployée sur une infrastructure distante.

Les informations extraites doivent toujours être vérifiées à partir du document original.

## Améliorations envisagées

- Amélioration continue de la reconnaissance OCR.
- Intégration éventuelle d'un modèle LLM pour l'extraction structurée.
- Traitement asynchrone et analyse de plusieurs documents.
- Évaluation de la précision sur des jeux de données fictifs.
- Ajout éventuel d'une base de données PostgreSQL.
- Renforcement de la sécurité et de la couverture des tests.
- Déploiement et intégration continue (CI/CD).

Ces évolutions sont des pistes de développement et ne sont pas toutes implémentées.

## Confidentialité et sécurité

DocLens est destiné à des démonstrations et à des expérimentations locales.

Les documents sont traités en mémoire et ne sont pas conservés par une base de données.

Aucun service LLM externe n'est utilisé actuellement.

Il est recommandé d'utiliser uniquement des documents fictifs ou anonymisés. Ne publiez jamais de documents personnels, de clés API, de mots de passe ou de fichiers contenant des informations sensibles.

## Auteur

**Taha Rachedi**

Projet personnel de développement web et d'analyse documentaire.

GitHub : https://github.com/taharachedi

---

*DocLens — Intelligent Document Extraction & Analysis.*
