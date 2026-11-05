
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
from typing import Optional
import re
import os
import shutil
import unicodedata
import logging
import uuid
import time

import fitz
import pytesseract
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from pytesseract import Output

# Configuration Tesseract sous Windows
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.isfile(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

Image.MAX_IMAGE_PIXELS = 30_000_000
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("doclens")

app = FastAPI(
    title="DocLens API",
    description="Extraction d'informations dans les documents",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


class ExtractedFields(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    date: Optional[str] = None
    date_naissance: Optional[str] = None
    date_delivrance: Optional[str] = None
    date_expiration: Optional[str] = None
    montant: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    nationalite: Optional[str] = None
    adresse: Optional[str] = None
    numero_document: Optional[str] = None


class DocumentResult(BaseModel):
    filename: str
    status: str
    document_type: str
    extraction_method: str
    extracted_text: str
    fields: ExtractedFields
    warnings: list[str] = Field(default_factory=list)
    processed_at: datetime


def nettoyer(texte: str) -> str:
    return re.sub(r"\s+", " ", texte).strip(" :;,-")


def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte)
    return "".join(
        c for c in texte if not unicodedata.combining(c)
    ).lower()


def date_valide(valeur: str) -> bool:
    match = re.fullmatch(
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
        valeur
    )
    if not match:
        return False

    try:
        datetime(
            int(match.group(3)),
            int(match.group(2)),
            int(match.group(1))
        )
        return True
    except ValueError:
        return False


def chercher_date(texte: str) -> Optional[str]:
    dates = re.findall(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
        texte
    )
    for valeur in dates:
        if date_valide(valeur):
            return valeur
    return None


def champ_libelle(texte: str, libelles: list[str]) -> Optional[str]:
    lignes = texte.splitlines()

    for index, ligne in enumerate(lignes):
        for libelle in libelles:
            motif = r"^\s*" + libelle + r"\s*[:\-]\s*(.+?)\s*$"
            match = re.search(motif, ligne, re.IGNORECASE)
            if match:
                valeur = nettoyer(match.group(1))
                if 2 <= len(valeur) <= 100:
                    return valeur

            motif_seul = r"^\s*" + libelle + r"\s*[:\-]?\s*$"
            if re.search(motif_seul, ligne, re.IGNORECASE):
                if index + 1 < len(lignes):
                    valeur = nettoyer(lignes[index + 1])
                    if 2 <= len(valeur) <= 100:
                        return valeur

    return None


def type_document(texte: str) -> str:
    t = normaliser(texte)

    if "passeport" in t or "passport" in t:
        return "Passeport"
    if "facture" in t or "invoice" in t:
        return "Facture"
    if "curriculum vitae" in t or re.search(r"\bcv\b", t):
        return "CV"
    if "carte nationale" in t or "identity card" in t:
        return "Carte d'identité"
    if "attestation" in t:
        return "Attestation"
    if "contrat" in t:
        return "Contrat"
    if "releve" in t:
        return "Relevé"
    if "diplome" in t:
        return "Diplôme"

    return "Document général"


def preparer_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")

    if max(image.size) < 1800:
        facteur = min(2.5, 1800 / max(image.size))
        image = image.resize(
            (
                int(image.width * facteur),
                int(image.height * facteur)
            ),
            Image.Resampling.LANCZOS
        )

    gris = ImageOps.grayscale(image)
    gris = ImageOps.autocontrast(gris)
    gris = ImageEnhance.Contrast(gris).enhance(1.4)
    gris = gris.filter(ImageFilter.SHARPEN)

    return gris


def ocr_image(image: Image.Image) -> str:
    image = preparer_image(image)

    langues = pytesseract.get_languages(config="")
    disponibles = [l for l in ["fra", "eng"] if l in langues]

    if not disponibles:
        raise RuntimeError("Aucune langue OCR disponible.")

    langue = "+".join(disponibles)

    resultats = []

    for psm in [6, 11]:
        texte = pytesseract.image_to_string(
            image,
            lang=langue,
            config=f"--oem 3 --psm {psm}"
        ).strip()

        if texte:
            resultats.append(texte)

    if not resultats:
        return ""

    def score(texte: str) -> int:
        return len(re.findall(r"[A-Za-zÀ-ÿ0-9]", texte))

    return max(resultats, key=score)


def lire_document(contenu: bytes, extension: str):
    textes = []
    methodes = set()

    if extension == ".pdf":
        try:
            document = fitz.open(
                stream=contenu,
                filetype="pdf"
            )
        except Exception:
            raise HTTPException(400, "PDF invalide.")

        try:
            if document.page_count > 10:
                raise HTTPException(
                    400,
                    "Maximum 10 pages par document."
                )

            for page in document:
                texte_pdf = page.get_text("text").strip()

                # A digital PDF already has selectable text: avoid slow, duplicate OCR.
                texte_ocr = ""
                if len(texte_pdf) < 30:
                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(2, 2), alpha=False
                    )
                    with Image.open(BytesIO(pix.tobytes("png"))) as image:
                        texte_ocr = ocr_image(image)

                if texte_pdf:
                    methodes.add("PDF texte")
                if texte_ocr:
                    methodes.add("OCR Tesseract")

                # Conserver les informations des deux sources.
                # Éviter une répétition lorsque le texte est identique.
                if texte_pdf and texte_ocr:
                    if normaliser(texte_pdf) == normaliser(texte_ocr):
                        textes.append(texte_pdf)
                    else:
                        textes.append(
                            texte_pdf + "\n" + texte_ocr
                        )
                else:
                    textes.append(texte_pdf or texte_ocr)

        finally:
            document.close()

    else:
        try:
            image = Image.open(BytesIO(contenu))
            image.load()
            texte = ocr_image(image)
            textes.append(texte)
            methodes.add("OCR Tesseract")
        except Exception as exc:
            raise HTTPException(
                422,
                f"Impossible de lire l'image : {exc}"
            )

    texte_final = "\n\n".join(t for t in textes if t.strip())
    methode = " + ".join(sorted(methodes)) or "Aucune"

    return texte_final, methode


def extraire_champs(texte: str, categorie: str) -> ExtractedFields:
    champs = ExtractedFields()

    email = re.search(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        texte
    )
    if email:
        champs.email = email.group(0)

    telephone = re.search(
        r"(?<!\d)(?:\+33|0)[1-9](?:[\s.\-]?\d{2}){4}(?!\d)",
        texte
    )
    if telephone:
        champs.telephone = telephone.group(0)

    champs.date = chercher_date(texte)

    if categorie == "Passeport":
        # Sur un passeport, ne pas interpréter automatiquement
        # les lignes OCR abîmées comme une identité fiable.
        champs.nom = None
        champs.prenom = None
        champs.nationalite = None
        champs.date_naissance = None
        champs.date_delivrance = None
        champs.date_expiration = None
        champs.numero_document = None

    else:
        champs.nom = champ_libelle(
            texte,
            [r"Nom", r"Client", r"Name"]
        )

        champs.prenom = champ_libelle(
            texte,
            [r"Prénom", r"Prenom", r"First name"]
        )

        champs.adresse = champ_libelle(
            texte,
            [r"Adresse", r"Address"]
        )

        champs.date_naissance = champ_libelle(
            texte,
            [r"Date de naissance", r"Date of birth"]
        )

        champs.date_delivrance = champ_libelle(
            texte,
            [r"Date de délivrance", r"Date of issue"]
        )

        champs.date_expiration = champ_libelle(
            texte,
            [r"Date d'expiration", r"Date of expiry"]
        )

        champs.nationalite = champ_libelle(
            texte,
            [r"Nationalité", r"Nationality"]
        )

        champs.numero_document = champ_libelle(
            texte,
            [r"Numéro de document", r"Document number"]
        )

    if categorie == "Facture":
        montant = re.search(
            r"\b\d+(?:[\s.,]\d{3})*(?:[.,]\d{2})?\s*(?:EUR\b|€)",
            texte,
            re.IGNORECASE
        )
        if montant:
            champs.montant = montant.group(0)

    return champs


@app.get("/")
def accueil():
    return {
        "application": "DocLens",
        "status": "online",
        "version": "2.0.0"
    }


@app.get("/health")
def health():
    chemin = pytesseract.pytesseract.tesseract_cmd
    disponible = bool(
        os.path.isfile(chemin) or shutil.which(chemin)
    )
    return {
        "status": "healthy" if disponible else "degraded",
        "tesseract": disponible
    }


@app.post("/documents", response_model=DocumentResult)
async def upload_document(file: UploadFile = File(...)):
    extension = Path(file.filename or "").suffix.lower()

    if extension not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(
            400,
            "Formats acceptés : PDF, PNG, JPG, JPEG."
        )

    contenu = await file.read(10 * 1024 * 1024 + 1)

    if not contenu:
        raise HTTPException(400, "Le fichier est vide.")

    if len(contenu) > 10 * 1024 * 1024:
        raise HTTPException(
            413,
            "Le fichier dépasse 10 Mo."
        )

    request_id = uuid.uuid4().hex[:12]
    started = time.monotonic()
    logger.info("document_started id=%s extension=%s size=%d", request_id, extension, len(contenu))
    try:
        texte, methode = lire_document(contenu, extension)

        categorie = type_document(texte)
        champs = extraire_champs(texte, categorie)

        avertissements = []

        if not texte.strip():
            avertissements.append(
                "Aucun texte lisible détecté."
            )

        if categorie == "Passeport":
            avertissements.append(
                "Les champs d'identité du passeport nécessitent "
                "une validation spécifique. Les résultats OCR "
                "bruts peuvent contenir des erreurs."
            )

        logger.info("document_completed id=%s method=%s duration_ms=%d", request_id, methode, int((time.monotonic() - started) * 1000))
        return DocumentResult(
            filename=file.filename or "document",
            status="completed" if texte.strip() else "no_text",
            document_type=categorie,
            extraction_method=methode,
            extracted_text=texte,
            fields=champs,
            warnings=avertissements,
            processed_at=datetime.now(timezone.utc)
        )

    except HTTPException:
        raise
    except pytesseract.TesseractNotFoundError:
        logger.exception("ocr_unavailable id=%s", request_id)
        raise HTTPException(
            500,
            "Tesseract introuvable. Vérifiez son installation."
        )
    except Exception:
        logger.exception("document_failed id=%s", request_id)
        raise HTTPException(
            422,
            f"L'analyse du document a échoué (référence : {request_id})."
        )
