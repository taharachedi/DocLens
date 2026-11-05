from fastapi.testclient import TestClient
from main import app, date_valide, extraire_champs, type_document

client = TestClient(app)


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["application"] == "DocLens"


def test_reject_unsupported_extension():
    response = client.post("/documents", files={"file": ("test.txt", b"hello", "text/plain")})
    assert response.status_code == 400


def test_reject_empty_file():
    response = client.post("/documents", files={"file": ("test.pdf", b"", "application/pdf")})
    assert response.status_code == 400


def test_reject_oversized_file():
    response = client.post("/documents", files={"file": ("test.pdf", b"x" * (10 * 1024 * 1024 + 1), "application/pdf")})
    assert response.status_code == 413


def test_dates():
    assert date_valide("12/05/2025")
    assert not date_valide("31/02/2025")


def test_invoice_fields():
    text = "Facture\nNom : Dupont\nPrénom : Marie\nEmail : marie@example.com\nTotal : 120,00 €"
    assert type_document(text) == "Facture"
    fields = extraire_champs(text, "Facture")
    assert fields.nom == "Dupont"
    assert fields.email == "marie@example.com"
    assert fields.montant == "120,00 €"
