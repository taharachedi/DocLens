# DocLens

Application locale d'extraction d'informations depuis des documents PDF et des images. Projet personnel en cours de d├®veloppement.

## ├ëtat r├®el du projet

**Impl├®ment├® dans cette version :**
- Interface Angular 19 pour s├®lectionner un fichier et afficher les r├®sultats.
- API REST Python / FastAPI (`POST /documents`, `GET /health`, `GET /`).
- Lecture du texte natif des PDF avec PyMuPDF ; OCR Tesseract pour les pages sans texte exploitable et pour les images.
- Extraction **par r├¿gles Python** de champs courants (nom, pr├®nom, email, t├®l├®phone, dates, montant de facture, etc.). Les r├®sultats doivent ├¬tre v├®rifi├®s : il ne s'agit pas d'une extraction fiable sur tous les documents.
- Validation du format (PDF, PNG, JPG, JPEG), de la taille (10 Mo) et de la limite de pages PDF (10 pages).
- Gestion des erreurs, messages d'avertissement, journaux techniques sans contenu des documents.
- Tests automatis├®s pour les routes de base et certaines r├¿gles d'extraction.

**Non impl├®ment├® :** aucun appel ├á un LLM, aucune comparaison de prompts ou de mod├¿les, aucune base PostgreSQL, aucun traitement Celery/Redis, aucun SSO, aucun d├®ploiement cloud. Ce d├®p├┤t ne doit pas ├¬tre pr├®sent├® comme une solution de production.

## Pr├®requis

- Python 3.11+ et Node.js compatible avec Angular 19.
- Tesseract OCR install├® sur le syst├¿me. Pour le fran├ºais, installer ├®galement les donn├®es de langue `fra` ; l'anglais `eng` est pris en charge.
- Sur Windows, le code recherche Tesseract dans `C:\Program Files\Tesseract-OCR\tesseract.exe`. Sinon, l'ex├®cutable `tesseract` doit ├¬tre accessible via le `PATH`.

## D├®marrer le backend

Dans un terminal ├á la racine du d├®p├┤t :

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Sur Linux/macOS, remplacer la cr├®ation et l'activation par `python3 -m venv .venv` puis `source .venv/bin/activate`.

Documentation de l'API : http://127.0.0.1:8000/docs

## D├®marrer le frontend

Dans un **second terminal** :

```powershell
cd frontend
npm ci
npm start
```

Ouvrir http://localhost:4200, s├®lectionner un document puis lancer l'analyse. Le backend doit ├¬tre d├®marr├® en parall├¿le.

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
        |-- Tesseract : OCR des images / pages scann├®es
        |-- R├¿gles Python : champs d├®tect├®s
        v
R├®ponse JSON -> interface Angular
```

Les fichiers sont trait├®s en m├®moire. Cette version ne conserve pas les documents et n'envoie pas leur contenu vers un service LLM. ├ëviter d'utiliser de vrais documents sensibles lors des d├®monstrations.

## Limites connues

- Les champs sont d├®tect├®s par expressions r├®guli├¿res et libell├®s : ils peuvent ├¬tre incomplets ou inexacts.
- La qualit├® de l'OCR d├®pend du scan et des langues install├®es.
- Le traitement est synchrone ; les lots et le suivi des t├óches ne sont pas disponibles.
- Les PDF num├®riques sont lus directement ; les PDF scann├®s passent par l'OCR.
- Pas d'authentification, de persistance ou de garanties de s├®curit├® de production.

## Am├®liorations envisag├®es (non r├®alis├®es)

1. Ajouter une int├®gration LLM **optionnelle** et configurable, avec validation Pydantic des sorties et gestion des secrets.
2. Ajouter l'import de lots, une file de t├óches asynchrones et des statuts consultables.
3. Enregistrer les exp├®rimentations dans PostgreSQL et comparer les r├®sultats ├á une v├®rit├® terrain.
4. Ajouter des tests d'int├®gration OCR sur des documents de d├®monstration anonymis├®s.
5. Ajouter monitoring, m├®triques, authentification et pipeline CI/CD avant tout d├®ploiement.

## Confidentialit├®

Ne jamais publier de documents personnels, de cl├®s API, de fichiers `.env` ou de bases de donn├®es dans le d├®p├┤t Git. Le `.gitignore` exclut les environnements virtuels et les d├®pendances install├®es.
