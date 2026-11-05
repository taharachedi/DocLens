# DocLens

Application locale d'extraction d'informations depuis des documents PDF et des images. Projet personnel en cours de développement.

## État réel du projet

**Implémenté dans cette version :**
- Interface Angular 19 pour sélectionner un fichier et afficher les résultats.
- API REST Python / FastAPI (`POST /documents`, `GET /health`, `GET /`).
- Lecture du texte natif des PDF avec PyMuPDF ; OCR Tesseract pour les pages sans texte exploitable et pour les images.
- Extraction **par règles Python** de champs courants (nom, prénom, email, téléphone, dates, montant de facture, etc.). Les résultats doivent être vérifiés : il ne s'agit pas d'une extraction fiable sur tous les documents.
- Validation du format (PDF, PNG, JPG, JPEG), de la taille (10 Mo) et de la limite de pages PDF (10 pages).
- Gestion des erreurs, messages d'avertissement, journaux techniques sans contenu des documents.
- Tests automatisés pour les routes de base et certaines règles d'extraction.

**Non implémenté :** aucun appel à un LLM, aucune comparaison de prompts ou de modèles, aucune base PostgreSQL, aucun traitement Celery/Redis, aucun SSO, aucun déploiement cloud. Ce dépôt ne doit pas être présenté comme une solution de production.

## Prérequis

- Python 3.11+ et Node.js compatible avec Angular 19.
- Tesseract OCR installé sur le système. Pour le français, installer également les données de langue `fra` ; l'anglais `eng` est pris en charge.
- Sur Windows, le code recherche Tesseract dans `C:\Program Files\Tesseract-OCR\tesseract.exe`. Sinon, l'exécutable `tesseract` doit être accessible via le `PATH`.

## Démarrer le backend

Dans un terminal à la racine du dépôt :

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Sur Linux/macOS, remplacer la création et l'activation par `python3 -m venv .venv` puis `source .venv/bin/activate`.

Documentation de l'API : http://127.0.0.1:8000/docs

## Démarrer le frontend

Dans un **second terminal** :

```powershell
cd frontend
npm ci
npm start
```

Ouvrir http://localhost:4200, sélectionner un document puis lancer l'analyse. Le backend doit être démarré en parallèle.

## Tests

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Pour le frontend : `cd frontend`, puis `npm ci` et `npm run build`.

## Architecture

```text
Navigateur Angular :4200
        |
        | POST /documents (multipart/form-data)
        v
FastAPI :8000
        |-- PyMuPDF : texte PDF natif
        |-- Tesseract : OCR des images / pages scannées
        |-- Règles Python : champs détectés
        v
Réponse JSON -> interface Angular
```

Les fichiers sont traités en mémoire. Cette version ne conserve pas les documents et n'envoie pas leur contenu vers un service LLM. Éviter d'utiliser de vrais documents sensibles lors des démonstrations.

## Limites connues

- Les champs sont détectés par expressions régulières et libellés : ils peuvent être incomplets ou inexacts.
- La qualité de l'OCR dépend du scan et des langues installées.
- Le traitement est synchrone ; les lots et le suivi des tâches ne sont pas disponibles.
- Les PDF numériques sont lus directement ; les PDF scannés passent par l'OCR.
- Pas d'authentification, de persistance ou de garanties de sécurité de production.

## Améliorations envisagées (non réalisées)

1. Ajouter une intégration LLM **optionnelle** et configurable, avec validation Pydantic des sorties et gestion des secrets.
2. Ajouter l'import de lots, une file de tâches asynchrones et des statuts consultables.
3. Enregistrer les expérimentations dans PostgreSQL et comparer les résultats à une vérité terrain.
4. Ajouter des tests d'intégration OCR sur des documents de démonstration anonymisés.
5. Ajouter monitoring, métriques, authentification et pipeline CI/CD avant tout déploiement.

## Confidentialité

Ne jamais publier de documents personnels, de clés API, de fichiers `.env` ou de bases de données dans le dépôt Git. Le `.gitignore` exclut les environnements virtuels et les dépendances installées.
