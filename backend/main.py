import difflib
import os
import re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import fitz
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError
from pydantic import BaseModel

TESSERACT = os.getenv('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
if Path(TESSERACT).is_file():
    pytesseract.pytesseract.tesseract_cmd = TESSERACT

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 10
Image.MAX_IMAGE_PIXELS = 40_000_000

app = FastAPI(title='DocLens API', version='2.2.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:4200', 'http://127.0.0.1:4200'],
    allow_methods=['*'],
    allow_headers=['*'],
)

PAYS = {
    'FRA': 'France', 'MAR': 'Maroc', 'DZA': 'Algérie', 'TUN': 'Tunisie',
    'BEL': 'Belgique', 'CHE': 'Suisse', 'ESP': 'Espagne', 'DEU': 'Allemagne',
    'ITA': 'Italie', 'GBR': 'Royaume-Uni', 'USA': 'États-Unis', 'CAN': 'Canada',
    'PRT': 'Portugal', 'NLD': 'Pays-Bas', 'LUX': 'Luxembourg', 'SEN': 'Sénégal',
    'CIV': "Côte d'Ivoire", 'MLI': 'Mali', 'TUR': 'Turquie', 'CHN': 'Chine',
    'IND': 'Inde', 'BRA': 'Brésil', 'EGY': 'Égypte', 'LBN': 'Liban',
    'ROU': 'Roumanie', 'POL': 'Pologne', 'UKR': 'Ukraine', 'SWE': 'Suède',
    'AUT': 'Autriche', 'GRC': 'Grèce', 'IRL': 'Irlande', 'JPN': 'Japon',
    'ZAF': 'Afrique du Sud', 'CMR': 'Cameroun', 'MRT': 'Mauritanie',
}

# Libellés les plus longs en premier : le préfixe le plus long l'emporte.
LABEL_PATTERNS: list[tuple[str, str]] = [
    (r"date de naissance(?:\s*/\s*date of birth)?", 'Date de naissance'),
    (r"date of birth", 'Date de naissance'),
    (r"n[eé]e?\s+le", 'Date de naissance'),
    (r"lieu de naissance(?:\s*/\s*place of birth)?", 'Lieu de naissance'),
    (r"place of birth", 'Lieu de naissance'),
    (r"date de d[eé]livrance(?:\s*/\s*date of issue)?", 'Date de délivrance'),
    (r"date of issue", 'Date de délivrance'),
    (r"d[eé]livr[eé]\s+le", 'Date de délivrance'),
    (r"date d'expiration(?:\s*/\s*(?:date of expiry|expiry date))?", "Date d'expiration"),
    (r"date of expiry", "Date d'expiration"),
    (r"expiry date", "Date d'expiration"),
    (r"date de validit[eé]", "Date d'expiration"),
    (r"expire\s+le", "Date d'expiration"),
    (r"date(?:\s+de\s+(?:la\s+)?facture)?", 'Date'),
    (r"nationalit[eé](?:\s*/\s*nationality)?", 'Nationalité'),
    (r"nationality", 'Nationalité'),
    (r"pr[eé]noms?(?:\s*/\s*given names?)?", 'Prénom'),
    (r"given names?", 'Prénom'),
    (r"first name", 'Prénom'),
    (r"nom(?:\s+de\s+famille)?(?:\s*/\s*(?:surname|family name|name))?", 'Nom'),
    (r"surname|family name", 'Nom'),
    (r"sexe(?:\s*/\s*sex)?", 'Sexe'),
    (r"sex", 'Sexe'),
    (r"(?:n[°o]|num[eé]ro)(?:\s+du|\s+de)?(?:\s+document|\s+passeport|\s+passport)?(?:\s*/\s*(?:passport\s*)?(?:no|number)\.?)?", 'Numéro de document'),
    (r"passport\s*(?:no|number)\.?", 'Numéro de document'),
    (r"autorit[eé](?:\s*/\s*authority)?", 'Autorité'),
    (r"authority", 'Autorité'),
    (r"adresse e-?mail", 'Email'),
    (r"e-?mail", 'Email'),
    (r"courriel", 'Email'),
    (r"t[eé]l[eé]phone(?:\s*/\s*(?:phone|tel))?", 'Téléphone'),
    (r"phone|t[eé]l\.?", 'Téléphone'),
    (r"adresse(?:\s*/\s*address)?", 'Adresse'),
    (r"address", 'Adresse'),
    (r"net [aà] payer", 'Montant'),
    (r"montant(?:\s+(?:total|ttc|ht))?", 'Montant'),
    (r"total\s+ttc", 'Montant'),
    (r"total\s+ht", 'Total HT'),
    (r"\btva\b", 'TVA'),
    (r"siret", 'SIRET'),
    (r"siren", 'SIREN'),
    (r"iban", 'IBAN'),
    (r"\bbic\b", 'BIC'),
    (r"(?:n[°o]\s*)?facture", 'Numéro de facture'),
    (r"invoice(?:\s+(?:number|no\.?))?", 'Numéro de facture'),
    (r"client", 'Client'),
    (r"soci[eé]t[eé]", 'Société'),
    (r"r[eé]f[eé]rence", 'Référence'),
    (r"objet", 'Objet'),
    (r"pays(?:\s+[eé]metteur)?(?:\s*/\s*issuing state)?", 'Pays émetteur'),
]

ALIASES = {
    'date de naissance': 'Date de naissance',
    'date of birth': 'Date de naissance',
    'lieu de naissance': 'Lieu de naissance',
    'place of birth': 'Lieu de naissance',
    'date de delivrance': 'Date de délivrance',
    'date of issue': 'Date de délivrance',
    "date d'expiration": "Date d'expiration",
    'date of expiry': "Date d'expiration",
    'date de validite': "Date d'expiration",
    'prenoms': 'Prénom',
    'prenom': 'Prénom',
    'given names': 'Prénom',
    'nom de famille': 'Nom',
    'surname': 'Nom',
    'family name': 'Nom',
    'nationalite': 'Nationalité',
    'nationality': 'Nationalité',
    'numero de document': 'Numéro de document',
    'numero de passeport': 'Numéro de document',
    'passport number': 'Numéro de document',
    'passport no': 'Numéro de document',
    'telephone': 'Téléphone',
    'total ttc': 'Montant',
    'net a payer': 'Montant',
    'numero de facture': 'Numéro de facture',
}

DATE_LABELS = {
    'Date', 'Date de naissance', 'Date de délivrance', "Date d'expiration", 'Date repérée',
}
REPEATABLE = {'Date repérée', 'Montant', 'Total HT', 'TVA', 'Téléphone', 'Email'}
FIELD_ORDER = [
    'Nom', 'Prénom', 'Sexe', 'Date de naissance', 'Lieu de naissance', 'Nationalité',
    'Pays émetteur', 'Numéro de document', 'Numéro personnel', 'Date de délivrance',
    "Date d'expiration", 'Date', 'Client', 'Société', 'Email', 'Téléphone', 'Adresse',
    'Numéro de facture', 'Référence', 'Objet', 'Total HT', 'TVA', 'Montant', 'IBAN', 'BIC',
    'SIRET', 'SIREN', 'Autorité',
]
MONTHS = {
    'janvier': 1, 'jan': 1, 'fevrier': 2, 'fevr': 2, 'feb': 2, 'mars': 3, 'mar': 3,
    'avril': 4, 'avr': 4, 'apr': 4, 'mai': 5, 'may': 5, 'juin': 6, 'jun': 6,
    'juillet': 7, 'juil': 7, 'jul': 7, 'aout': 8, 'aug': 8, 'septembre': 9,
    'sept': 9, 'sep': 9, 'octobre': 10, 'oct': 10, 'novembre': 11, 'nov': 11,
    'decembre': 12, 'dec': 12,
}
EN_WORDS = {
    'name', 'names', 'given', 'surname', 'family', 'date', 'of', 'birth', 'issue',
    'expiry', 'sex', 'nationality', 'passport', 'number', 'no', 'place', 'authority',
    'address', 'phone', 'state', 'issuing',
}
_LANG: str | None = None


class Fields(BaseModel):
    nom: str | None = None
    prenom: str | None = None
    sexe: str | None = None
    date: str | None = None
    date_naissance: str | None = None
    lieu_naissance: str | None = None
    nationalite: str | None = None
    date_delivrance: str | None = None
    date_expiration: str | None = None
    montant: str | None = None
    email: str | None = None
    telephone: str | None = None
    numero_document: str | None = None
    iban: str | None = None


class Champ(BaseModel):
    libelle: str
    valeur: str


class DocumentResult(BaseModel):
    filename: str
    status: str
    document_type: str
    extraction_method: str
    extracted_text: str
    fields: Fields
    champs: list[Champ] = []
    confiance_ocr: int | None = None
    processed_at: datetime
    warnings: list[str] = []


def fold(value: str) -> str:
    table = str.maketrans('àáâäéèêëìíîïòóôöùúûüç’', 'aaaaeeeeiiiioooouuuuc\'')
    return re.sub(r'\s+', ' ', value.lower().translate(table)).strip()


def tesseract_lang() -> str:
    global _LANG
    if _LANG:
        return _LANG
    preferred = os.getenv('TESSERACT_LANG', 'fra+eng')
    try:
        installed = set(pytesseract.get_languages())
    except Exception:
        _LANG = 'eng'
        return _LANG
    parts = [part for part in preferred.split('+') if part in installed]
    _LANG = '+'.join(parts) if parts else ('eng' if 'eng' in installed else preferred)
    return _LANG


def otsu(gray: Image.Image) -> Image.Image:
    hist = gray.histogram()
    total = sum(hist)
    if total == 0:
        return gray
    sum_total = sum(index * count for index, count in enumerate(hist))
    sum_bg = 0
    weight_bg = 0
    best_var = -1.0
    threshold = 127
    for index, count in enumerate(hist):
        weight_bg += count
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += index * count
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > best_var:
            best_var = variance
            threshold = index
    return gray.point(lambda pixel, limit=threshold: 255 if pixel > limit else 0)


def prepare(image: Image.Image, binarize: bool) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    image = ImageOps.grayscale(image)
    long_side = max(image.size)
    if long_side < 2000:
        scale = 2000 / long_side
    elif long_side > 4200:
        scale = 4200 / long_side
    else:
        scale = 1
    if scale != 1:
        image = image.resize(
            (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
            Image.Resampling.LANCZOS,
        )
    image = ImageOps.autocontrast(image, cutoff=1)
    image = ImageEnhance.Sharpness(image).enhance(1.8)
    image = ImageEnhance.Contrast(image).enhance(1.35)
    if binarize:
        image = image.filter(ImageFilter.MedianFilter(size=3))
        image = otsu(image)
    return image


def straighten(image: Image.Image) -> Image.Image:
    """Redresse une page nettement tournée. Une page déjà droite n'est pas touchée."""
    try:
        probe = image.copy()
        probe.thumbnail((1000, 1000))
        osd = pytesseract.image_to_osd(probe, lang='osd')
    except Exception:
        return image
    angle_match = re.search(r'Rotate:\s+(\d+)', osd)
    conf_match = re.search(r'Orientation confidence:\s+([\d.]+)', osd)
    if not angle_match or not conf_match:
        return image
    angle = int(angle_match.group(1))
    if angle in (90, 180, 270) and float(conf_match.group(1)) >= 10:
        # « Rotate » indique la rotation horaire du texte : on la corrige dans l'autre sens.
        return image.rotate(360 - angle, expand=True, fillcolor='white')
    return image


def _read_ocr(image: Image.Image, psm: int, lang: str | None = None) -> str:
    config = f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'
    language = lang or tesseract_lang()
    try:
        return pytesseract.image_to_string(image, lang=language, config=config)
    except pytesseract.TesseractError:
        if language != 'eng':
            return pytesseract.image_to_string(image, lang='eng', config=config)
        raise


def _confidence(image: Image.Image, psm: int) -> float:
    try:
        data = pytesseract.image_to_data(
            image,
            lang=tesseract_lang(),
            config=f'--oem 3 --psm {psm}',
            output_type=pytesseract.Output.DICT,
        )
    except pytesseract.TesseractError:
        return 0.0
    values = []
    for raw in data.get('conf', []):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            values.append(value)
    return sum(values) / len(values) if values else 0.0


def score_text(text: str) -> int:
    words = re.findall(r'[A-Za-zÀ-ÿ0-9]{2,}', text)
    return sum(len(word) for word in words) + 3 * len(words)


def ocr_mrz_band(image: Image.Image) -> str:
    width, height = image.size
    if height < 80:
        return ''
    band = image.crop((0, int(height * 0.72), width, height))
    binary = prepare(band, binarize=True)
    config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<'
    try:
        text = pytesseract.image_to_string(binary, lang='eng', config=config)
    except pytesseract.TesseractError:
        return ''
    kept = []
    for line in text.splitlines():
        compact = re.sub(r'[^A-Z0-9<]', '', line.upper())
        if compact.count('<') >= 2 and len(compact) >= 20:
            kept.append(compact)
    return '\n'.join(kept)


def ocr_image(image: Image.Image) -> tuple[str, float]:
    image = straighten(ImageOps.exif_transpose(image).convert('RGB'))
    gray = prepare(image, binarize=False)
    binary = prepare(image, binarize=True)
    best_text = ''
    best_key = (-1, -1.0)
    best_image: tuple[Image.Image, int] | None = None
    for variant, psm in ((gray, 6), (gray, 4), (binary, 6)):
        text = _read_ocr(variant, psm)
        rank = (score_text(text), len(text.strip()))
        if rank > best_key:
            best_key = rank
            best_text = text
            best_image = (variant, psm)
        if psm == 6 and rank[0] >= 180:
            break
    band = ocr_mrz_band(image)
    if band and band.replace('\n', '') not in re.sub(r'[^A-Z0-9<]', '', best_text.upper()):
        best_text = f'{best_text.rstrip()}\n{band}'
    confidence = _confidence(*best_image) if best_image else 0.0
    return best_text.strip(), confidence


def _native_text(page) -> str:
    try:
        return page.get_text('text', sort=True).strip()
    except TypeError:
        return page.get_text('text').strip()


def _render_page(page) -> Image.Image:
    rect = page.rect
    zoom = 300 / 72
    pixels = rect.width * rect.height * zoom * zoom
    if pixels > 9_000_000:
        zoom = (9_000_000 / max(rect.width * rect.height, 1)) ** 0.5
    try:
        dpi = max(72, min(300, int(72 * zoom)))
        pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    except TypeError:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return Image.open(BytesIO(pixmap.tobytes('png')))


def read_document(content: bytes, suffix: str) -> tuple[str, str, int | None]:
    if suffix == '.pdf':
        try:
            document = fitz.open(stream=content, filetype='pdf')
        except Exception:
            raise HTTPException(400, 'PDF invalide ou illisible.')
        try:
            if document.needs_pass:
                raise HTTPException(400, 'PDF protégé par mot de passe.')
            if not 1 <= document.page_count <= MAX_PAGES:
                raise HTTPException(400, f'Le PDF doit contenir de 1 à {MAX_PAGES} pages.')
            sections = []
            confidences = []
            used_ocr = False
            kept_native = False
            for index, page in enumerate(document, start=1):
                native = _native_text(page)
                native_score = score_text(native)
                looks_like_passport = re.search(r'passeport|passport', native, re.I)
                mrz_already = parse_mrz(native) is not None
                needs_ocr = native_score < 220 or (looks_like_passport and not mrz_already)
                text = native
                if native_score >= 40:
                    kept_native = True
                if needs_ocr:
                    try:
                        scanned, confidence = ocr_image(_render_page(page))
                    except pytesseract.TesseractNotFoundError:
                        if native_score < 20:
                            raise
                        scanned, confidence = '', 0
                    scanned_mrz = parse_mrz(scanned) if scanned else None
                    if score_text(scanned) > native_score or (scanned_mrz and not mrz_already):
                        text = scanned
                        used_ocr = True
                        confidences.append(confidence)
                if document.page_count > 1:
                    sections.append(f'--- Page {index} ---\n{text}')
                else:
                    sections.append(text)
            if not used_ocr:
                method = 'PDF texte'
            elif kept_native:
                method = 'OCR Tesseract + PDF'
            else:
                method = 'OCR Tesseract'
            joined = '\n\n'.join(sections).strip()
            average = round(sum(confidences) / len(confidences)) if confidences else None
            return joined[:200_000], method, average
        finally:
            document.close()
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format not in ('PNG', 'JPEG'):
                raise HTTPException(400, 'Image PNG ou JPEG requise.')
            text, confidence = ocr_image(image)
            return text[:200_000], 'OCR Tesseract', round(confidence)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(400, 'Image invalide ou trop grande.')


def _date_from_numbers(day: int, month: int, year: int) -> str | None:
    try:
        parsed = datetime(year, month, day)
    except ValueError:
        return None
    if 1900 <= parsed.year <= 2100:
        return parsed.strftime('%d/%m/%Y')
    return None


def repair_date_token(token: str) -> str:
    return token.translate(str.maketrans('OILZSBGQoilzsbgq', '0112586901125869'))


def normalize_date(raw: str) -> str | None:
    token = raw.strip()
    candidates = [token, repair_date_token(token)]
    for candidate in candidates:
        iso = re.fullmatch(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', candidate)
        if iso:
            found = _date_from_numbers(int(iso.group(3)), int(iso.group(2)), int(iso.group(1)))
            if found:
                return found
        numeric = re.fullmatch(r'(\d{1,2})[./\-\s](\d{1,2})[./\-\s](\d{4})', candidate)
        if numeric:
            found = _date_from_numbers(int(numeric.group(1)), int(numeric.group(2)), int(numeric.group(3)))
            if found:
                return found
        written = re.fullmatch(
            r'(\d{1,2})\s+([A-Za-zÀ-ÿ]{3,10})\.?\s+(\d{4})',
            candidate,
        )
        if written:
            month = MONTHS.get(fold(written.group(2)))
            if month:
                found = _date_from_numbers(int(written.group(1)), month, int(written.group(3)))
                if found:
                    return found
    return None


def find_dates(text: str) -> list[str]:
    found = []
    patterns = [
        r'(?<![A-Za-z0-9])[0-9OIlZSGB]{1,2}[./-][0-9OIlZSGB]{1,2}[./-][0-9OIlZSGB]{4}(?![A-Za-z0-9])',
        r'(?<![A-Za-z0-9])[0-9]{4}[./-][0-9]{2}[./-][0-9]{2}(?![A-Za-z0-9])',
        r'(?<![A-Za-z0-9])\d{1,2}\s+\d{1,2}\s+\d{4}(?![A-Za-z0-9])',
        r'(?<![A-Za-z0-9])\d{1,2}\s+[A-Za-zÀ-ÿ]{3,10}\.?\s+\d{4}(?![A-Za-z0-9])',
    ]
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            parsed = normalize_date(match.group())
            if parsed and parsed not in seen:
                seen.add(parsed)
                found.append(parsed)
    return found


def strip_translation(rest: str) -> str:
    rest = rest.strip()
    if rest.startswith('/'):
        parts = rest[1:].strip().split(' ')
        index = 0
        while index < len(parts) and index < 4 and fold(parts[index]) in EN_WORDS:
            index += 1
        rest = ' '.join(parts[index:])
    return rest.strip(' :.-–—')


def match_label_prefix(line: str) -> tuple[str, str] | None:
    cleaned = re.sub(r'\s+', ' ', line).replace('’', "'").strip()
    lowered = cleaned.lower()
    best_end = -1
    best_name = None
    for pattern, name in LABEL_PATTERNS:
        match = re.match(pattern, lowered)
        if not match:
            continue
        if match.end() < len(lowered) and lowered[match.end()].isalpha():
            continue
        if match.end() > best_end:
            best_end = match.end()
            best_name = name
    if best_name is None:
        return None
    return best_name, strip_translation(cleaned[best_end:])


def fuzzy_label(line: str) -> str | None:
    head = re.split(r'\d|[:：]', line, maxsplit=1)[0]
    head = fold(head.split('/')[0])
    head = head.strip(' :.-')
    if not 6 <= len(head) <= 42 or len(head.split()) > 6:
        return None
    match = difflib.get_close_matches(head, list(ALIASES), n=1, cutoff=0.82)
    if not match:
        return None
    return ALIASES[match[0]]


def is_pure_label(line: str) -> bool:
    folded = fold(line.strip(' :.-/'))
    if folded in EN_WORDS or folded in {
        'given names', 'family name', 'date of birth', 'date of issue',
        'date of expiry', 'place of birth', 'passport number', 'passport no',
    }:
        return True
    prefix = match_label_prefix(line)
    if prefix and not prefix[1]:
        return True
    if re.search(r'\d', line):
        return False
    return fuzzy_label(line) is not None


def tidy_unknown_label(raw: str) -> str | None:
    label = re.sub(r'\s+', ' ', raw).strip(' .-:')
    words = label.split()
    if not 2 <= len(label) <= 40 or not 1 <= len(words) <= 5:
        return None
    if not re.search(r'[A-Za-zÀ-ÿ]', label):
        return None
    if label.endswith('.') or label.count(',') > 0:
        return None
    return label[0].upper() + label[1:]


def normalize_value(label: str, value: str) -> str | None:
    value = re.sub(r'\s+', ' ', value).strip(' ,;')
    if not value or len(value) > 160:
        return None
    if is_pure_label(value):
        return None
    if label in DATE_LABELS:
        dates = find_dates(value)
        return dates[0] if dates else None
    if label == 'Email':
        match = re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', value)
        return match.group().lower() if match else None
    if label in {'Montant', 'Total HT', 'TVA'}:
        amounts = find_amounts(value)
        return amounts[0] if amounts else (value if re.search(r'\d', value) else None)
    if label == 'Téléphone':
        phones = find_phones(value)
        return phones[0] if phones else None
    if label == 'IBAN':
        compact = re.sub(r'\s+', '', value).upper()
        return compact if iban_ok(compact) else (compact if re.search(r'[A-Z]{2}\d{2}', compact) else None)
    if label in {'SIRET', 'SIREN', 'Numéro de document', 'Numéro de facture', 'Référence'}:
        compact = re.sub(r'\s+', '', value)
        return compact[:40] if re.search(r'[A-Za-z0-9]', compact) else None
    if label == 'Sexe':
        token = fold(value)
        if token in {'f', 'femme', 'female'}:
            return 'F'
        if token in {'m', 'homme', 'male', 'masculin'}:
            return 'M'
        return None
    if not re.search(r'[A-Za-zÀ-ÿ0-9]', value):
        return None
    return value


def find_amounts(text: str) -> list[str]:
    pattern = re.compile(
        r'(?<!\w)(?:\d{1,3}(?:[ \u00a0.]\d{3})+|\d+)(?:[,.]\d{2})\s*(?:€|EUR|euros?)\b'
        r'|\b(?:€|EUR)\s*(?:\d{1,3}(?:[ \u00a0.]\d{3})+|\d+)(?:[,.]\d{2})',
        re.I,
    )
    return [re.sub(r'\s+', ' ', match.group()).strip() for match in pattern.finditer(text)]


def find_phones(text: str) -> list[str]:
    pattern = re.compile(
        r'(?<!\d)(?:\+33[\s.-]?[1-9](?:[\s.-]?\d{2}){4}|0[1-9](?:[\s.-]?\d{2}){4}|\+\d{1,3}[\s.-]\d(?:[\s.-]?\d){7,12})(?!\d)'
    )
    found = []
    for match in pattern.finditer(text):
        phone = re.sub(r'\s+', ' ', match.group()).strip()
        if phone not in found:
            found.append(phone)
    return found


def find_emails(text: str) -> list[str]:
    return list(dict.fromkeys(
        match.group().lower()
        for match in re.finditer(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', text)
    ))


def iban_ok(iban: str) -> bool:
    compact = re.sub(r'\s+', '', iban).upper()
    if not 15 <= len(compact) <= 34 or not re.fullmatch(r'[A-Z]{2}\d{2}[A-Z0-9]+', compact):
        return False
    rearranged = compact[4:] + compact[:4]
    digits = ''.join(str(ord(char) - 55) if char.isalpha() else char for char in rearranged)
    remainder = 0
    for char in digits:
        remainder = (remainder * 10 + int(char)) % 97
    return remainder == 1


def find_ibans(text: str) -> list[str]:
    found = []
    for match in re.finditer(r'\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,8}\b', text.upper()):
        compact = re.sub(r'\s+', '', match.group())
        if iban_ok(compact) and compact not in found:
            found.append(compact)
    return found


def extract_labeled(text: str) -> list[tuple[str, str]]:
    lines = []
    for raw in text.splitlines():
        line = re.sub(r'[ \t]+', ' ', raw).strip()
        if line and not re.fullmatch(r'-{2,}\s*Page\s+\d+\s*-{2,}', line):
            lines.append(line)
    found = []
    index = 0
    while index < len(lines):
        prefix = match_label_prefix(lines[index])
        label = None
        rest = ''
        if prefix:
            label, rest = prefix
        else:
            guessed = fuzzy_label(lines[index])
            if guessed:
                split_at = re.search(r'\d|[:：]', lines[index])
                if split_at and not re.search(r'\d', lines[index][:split_at.start()]):
                    label, rest = guessed, lines[index][split_at.start():].strip()
                elif not re.search(r'\d', lines[index]):
                    label, rest = guessed, ''
            if not label and (':' in lines[index] or '：' in lines[index]):
                left, right = re.split(r'[:：]', lines[index], maxsplit=1)
                unknown = tidy_unknown_label(left)
                if unknown:
                    label, rest = unknown, right.strip()
        if not label:
            index += 1
            continue
        consumed = 0
        if not rest:
            cursor = index + 1
            while cursor < len(lines) and cursor <= index + 2 and is_pure_label(lines[cursor]):
                cursor += 1
            if cursor < len(lines) and not is_pure_label(lines[cursor]):
                rest = lines[cursor]
                consumed = cursor - index
                if label == 'Adresse' and cursor + 1 < len(lines) and not is_pure_label(lines[cursor + 1]):
                    if len(lines[cursor + 1]) <= 70:
                        rest = f'{rest}, {lines[cursor + 1]}'
                        consumed += 1
        value = normalize_value(label, rest)
        if value:
            found.append((label, value))
            index += 1 + consumed
        else:
            index += 1
    return found


def mrz_checksum(data: str) -> str:
    weights = (7, 3, 1)
    total = 0
    for index, char in enumerate(data):
        if char == '<':
            value = 0
        elif char.isdigit():
            value = int(char)
        elif 'A' <= char <= 'Z':
            value = ord(char) - 55
        else:
            return ''
        total += value * weights[index % 3]
    return str(total % 10)


def _alts(char: str, numeric: bool) -> list[str]:
    pairs = {'O': '0', '0': 'O', 'I': '1', '1': 'I', 'L': '1', 'B': '8', '8': 'B',
             'S': '5', '5': 'S', 'Z': '2', '2': 'Z', 'G': '6', '6': 'G', 'Q': '0'}
    if numeric:
        coerced = char.translate(str.maketrans('OILZSBGQ', '01125860'))
        return [coerced if coerced.isdigit() or coerced == '<' else char]
    choices = [char]
    if char in pairs and pairs[char] not in choices:
        choices.append(pairs[char])
    return choices


def solve_checked_field(data: str, check: str, numeric: bool) -> str | None:
    groups = [_alts(char, numeric) for char in data]
    checks = _alts(check, True)
    combinations = 1
    for group in groups:
        combinations *= len(group)
    if combinations > 4096:
        return None
    best = None
    best_distance = 99
    from itertools import product
    for candidate in product(*groups):
        field = ''.join(candidate)
        distance = sum(left != right for left, right in zip(field, data))
        if distance > 3 or distance >= best_distance:
            continue
        for digit in checks:
            if mrz_checksum(field) == digit:
                best = field
                best_distance = distance
                break
    return best


def _mrz_date(value: str, birth: bool) -> str | None:
    if not re.fullmatch(r'\d{6}', value):
        return None
    year_short = int(value[:2])
    month = int(value[2:4])
    day = int(value[4:6])
    current = datetime.now().year
    year = 2000 + year_short
    if birth and year > current:
        year -= 100
    if not birth and year < 1990:
        year += 100
    return _date_from_numbers(day, month, year)


def _mrz_names(field: str) -> tuple[str | None, str | None]:
    cleaned = field.rstrip('<')
    surname, _, given = cleaned.partition('<<')
    surname = re.sub(r'\s+', ' ', surname.replace('<', ' ')).strip()
    given = re.sub(r'\s+', ' ', given.replace('<', ' ')).strip()
    if not re.fullmatch(r"[A-Z ]{2,}", surname):
        return None, None
    if given and not re.fullmatch(r"[A-Z ]{1,}", given):
        given = ''
    return surname, given or None


def _format_country(code: str) -> str:
    name = PAYS.get(code)
    return f'{code} — {name}' if name else code


def mrz_like_lines(text: str) -> list[str]:
    lines = []
    for raw in text.upper().splitlines():
        compact = raw.replace(' ', '').replace('«', '<').replace('‹', '<').replace('＜', '<')
        compact = re.sub(r'[^A-Z0-9<]', '', compact)
        if len(compact) >= 25 and compact.count('<') >= 2:
            lines.append(compact)
    return lines


def parse_td3(line1: str, line2: str) -> dict | None:
    line1 = (line1 + '<' * 44)[:44]
    line2 = (line2 + '<' * 44)[:44]
    if not line1.startswith('P') or '<' not in line1:
        return None
    number = solve_checked_field(line2[0:9], line2[9], numeric=False)
    birth = solve_checked_field(line2[13:19], line2[19], numeric=True)
    expiry = solve_checked_field(line2[21:27], line2[27], numeric=True)
    if not number or not birth or not expiry:
        return None
    birth_date = _mrz_date(birth, birth=True)
    expiry_date = _mrz_date(expiry, birth=False)
    if not birth_date or not expiry_date:
        return None
    country = line1[2:5].translate(str.maketrans('012568', 'OIZSGB'))
    nationality = line2[10:13].translate(str.maketrans('012568', 'OIZSGB'))
    if not re.fullmatch(r'[A-Z]{3}', nationality):
        return None
    sex = line2[20]
    if sex not in {'M', 'F', '<'}:
        sex = {'H': 'M'}.get(sex, '')
    if sex not in {'M', 'F', '<'}:
        return None
    surname, given = _mrz_names(line1[5:44])
    if not surname:
        return None
    personal = None
    optional = solve_checked_field(line2[28:42], line2[42], numeric=False)
    if optional:
        personal = optional.replace('<', '').strip() or None
    result = {
        'type': 'Passeport',
        'nom': surname,
        'prenom': given,
        'sexe': None if sex == '<' else sex,
        'naissance': birth_date,
        'expiration': expiry_date,
        'numero': number.replace('<', ''),
        'nationalite': _format_country(nationality),
    }
    if re.fullmatch(r'[A-Z]{3}', country):
        result['pays'] = _format_country(country)
    if personal:
        result['personnel'] = personal
    return result


def parse_td1(line1: str, line2: str, line3: str) -> dict | None:
    line1, line2, line3 = [(line + '<' * 30)[:30] for line in (line1, line2, line3)]
    if not re.match(r'[IAC][A-Z<]', line1):
        return None
    number = solve_checked_field(line1[5:14], line1[14], numeric=False)
    birth = solve_checked_field(line2[0:6], line2[6], numeric=True)
    expiry = solve_checked_field(line2[8:14], line2[14], numeric=True)
    if not number or not birth or not expiry:
        return None
    birth_date = _mrz_date(birth, True)
    expiry_date = _mrz_date(expiry, False)
    nationality = line2[15:18].translate(str.maketrans('012568', 'OIZSGB'))
    surname, given = _mrz_names(line3)
    sex = line2[7]
    if not birth_date or not expiry_date or not surname or not re.fullmatch(r'[A-Z]{3}', nationality):
        return None
    if sex not in {'M', 'F', '<'}:
        return None
    return {
        'type': "Carte d'identité",
        'nom': surname,
        'prenom': given,
        'sexe': None if sex == '<' else sex,
        'naissance': birth_date,
        'expiration': expiry_date,
        'numero': number.replace('<', ''),
        'nationalite': _format_country(nationality),
        'pays': _format_country(line1[2:5]) if re.fullmatch(r'[A-Z]{3}', line1[2:5]) else None,
    }


def parse_mrz(text: str) -> dict | None:
    lines = mrz_like_lines(text)
    for index, line in enumerate(lines):
        if line.startswith('P') and index + 1 < len(lines):
            parsed = parse_td3(line, lines[index + 1])
            if parsed:
                return parsed
        if re.match(r'[IAC][A-Z<]', line) and index + 2 < len(lines):
            parsed = parse_td1(line, lines[index + 1], lines[index + 2])
            if parsed:
                return parsed
    flat = ''.join(lines)
    for match in re.finditer(r'P[A-Z<]', flat):
        window = flat[match.start():match.start() + 88]
        if len(window) >= 72:
            parsed = parse_td3(window[:44], window[44:88])
            if parsed:
                return parsed
    for match in re.finditer(r'[IAC][A-Z<][A-Z]{3}', flat):
        window = flat[match.start():match.start() + 90]
        if len(window) >= 80:
            parsed = parse_td1(window[:30], window[30:60], window[60:90])
            if parsed:
                return parsed
    return None


class _Bag:
    def __init__(self):
        self.items: list[Champ] = []
        self.keys: set[str] = set()

    def _reindex(self):
        self.keys = {
            (f'{fold(item.libelle)}|{fold(item.valeur)}' if item.libelle in REPEATABLE else fold(item.libelle))
            for item in self.items
        }

    def put(self, label: str, value: str | None, overwrite: bool = False):
        if value is None:
            return
        value = re.sub(r'\s+', ' ', value).strip(' ,;')
        if not value:
            return
        if overwrite and label not in REPEATABLE:
            self.items = [item for item in self.items if fold(item.libelle) != fold(label)]
            self._reindex()
        key = f'{fold(label)}|{fold(value)}' if label in REPEATABLE else fold(label)
        if key in self.keys:
            return
        if label not in REPEATABLE and any(fold(item.libelle) == fold(label) for item in self.items):
            return
        self.items.append(Champ(libelle=label, valeur=value))
        self.keys.add(key)


def _sort_champs(items: list[Champ]) -> list[Champ]:
    order = {name: index for index, name in enumerate(FIELD_ORDER)}
    ranked = list(enumerate(items))
    ranked.sort(key=lambda pair: (0, order[pair[1].libelle], pair[0]) if pair[1].libelle in order else (1, pair[0]))
    return [item for _, item in ranked]


def extract_information(text: str) -> tuple[Fields, list[Champ], str | None, list[str]]:
    notes = []
    bag = _Bag()
    for label, value in extract_labeled(text):
        bag.put(label, value)
    for email in find_emails(text):
        bag.put('Email', email)
    for phone in find_phones(text):
        bag.put('Téléphone', phone)
    for amount in find_amounts(text):
        bag.put('Montant', amount)
    for iban in find_ibans(text):
        bag.put('IBAN', iban)
    known_dates = {item.valeur for item in bag.items if 'date' in fold(item.libelle)}
    for value in find_dates(text):
        if value not in known_dates:
            bag.put('Date repérée', value)

    identity = parse_mrz(text)
    if identity:
        notes.append('Numéro et dates contrôlés avec la zone MRZ. Vérifiez le nom sur le document.')
        bag.put('Nom', identity.get('nom'), overwrite=True)
        bag.put('Prénom', identity.get('prenom'), overwrite=True)
        bag.put('Sexe', identity.get('sexe'), overwrite=True)
        bag.put('Date de naissance', identity.get('naissance'), overwrite=True)
        bag.put("Date d'expiration", identity.get('expiration'), overwrite=True)
        bag.put('Numéro de document', identity.get('numero'), overwrite=True)
        bag.put('Nationalité', identity.get('nationalite'), overwrite=True)
        bag.put('Pays émetteur', identity.get('pays'), overwrite=True)
        bag.put('Numéro personnel', identity.get('personnel'), overwrite=True)
    elif mrz_like_lines(text):
        notes.append("Une zone MRZ est visible, mais ses chiffres de contrôle ne correspondent pas.")

    champs = _sort_champs(bag.items)

    def first(*labels: str) -> str | None:
        for label in labels:
            for item in champs:
                if item.libelle == label:
                    return item.valeur
        return None

    fields = Fields(
        nom=first('Nom'),
        prenom=first('Prénom'),
        sexe=first('Sexe'),
        date=first('Date'),
        date_naissance=first('Date de naissance'),
        lieu_naissance=first('Lieu de naissance'),
        nationalite=first('Nationalité'),
        date_delivrance=first('Date de délivrance'),
        date_expiration=first("Date d'expiration"),
        montant=first('Montant'),
        email=first('Email'),
        telephone=first('Téléphone'),
        numero_document=first('Numéro de document'),
        iban=first('IBAN'),
    )
    return fields, champs, identity.get('type') if identity else None, notes


def detect_type(text: str, mrz_type: str | None) -> str:
    if mrz_type:
        return mrz_type
    folded = fold(text)
    if 'passeport' in folded or 'passport' in folded:
        return 'Passeport'
    if 'carte nationale' in folded or "carte d'identite" in folded or 'identity card' in folded:
        return "Carte d'identité"
    if any(token in folded for token in ('facture', 'invoice', 'total ttc', 'net a payer')):
        return 'Facture'
    if 'curriculum vitae' in folded or re.search(r'\bcompetences\b|\bexperiences professionnelles\b', folded):
        return 'CV'
    if re.search(r'\bcontrat\b', folded) or 'entre les soussignes' in folded:
        return 'Contrat'
    if 'attestation' in folded or 'certificat' in folded:
        return 'Attestation'
    return 'Autre document'


@app.get('/')
def home():
    return {'application': 'DocLens', 'status': 'online', 'version': '2.2.0'}


@app.get('/health')
def health():
    return {'status': 'healthy'}


@app.post('/documents', response_model=DocumentResult)
async def upload_document(file: UploadFile = File(...)):
    filename = Path(file.filename or 'document').name
    suffix = Path(filename).suffix.lower()
    if suffix not in ('.pdf', '.png', '.jpg', '.jpeg'):
        raise HTTPException(400, 'Formats acceptés : PDF, PNG, JPG, JPEG.')
    content = await file.read(MAX_BYTES + 1)
    if not content:
        raise HTTPException(400, 'Fichier vide.')
    if len(content) > MAX_BYTES:
        raise HTTPException(413, 'Taille maximale : 10 Mo.')
    try:
        text, method, confidence = read_document(content, suffix)
    except HTTPException:
        raise
    except pytesseract.TesseractNotFoundError:
        raise HTTPException(500, 'Tesseract introuvable : vérifiez son installation.')
    except Exception:
        raise HTTPException(422, 'Impossible de lire ce document.')

    fields, champs, mrz_type, notes = extract_information(text)
    warnings = ['Vérifiez ces informations sur le document original.']
    if not text.strip():
        warnings = ['Aucun texte lisible. Reprenez le document à plat, sans reflet, en remplissant la page.']
    elif score_text(text) < 25:
        warnings.append('Très peu de texte a été lu. Le scan est probablement trop flou ou trop sombre.')
    elif confidence is not None and confidence < 55:
        warnings.append('Lecture incertaine. Rapprochez le document et évitez les reflets.')
    if not champs and text.strip():
        warnings.append("Le texte a été lu, mais aucun champ avec un libellé reconnaissable n'a été isolé.")
    warnings.extend(notes)
    return DocumentResult(
        filename=filename,
        status='completed',
        document_type=detect_type(text, mrz_type),
        extraction_method=method,
        extracted_text=text,
        fields=fields,
        champs=champs,
        confiance_ocr=confidence,
        processed_at=datetime.now(timezone.utc),
        warnings=warnings,
    )
