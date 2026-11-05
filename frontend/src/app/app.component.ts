
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';

interface ExtractedFields {
  nom: string | null;
  prenom: string | null;
  date: string | null;
  date_naissance: string | null;
  date_delivrance: string | null;
  date_expiration: string | null;
  montant: string | null;
  email: string | null;
  telephone: string | null;
  nationalite: string | null;
  adresse: string | null;
  numero_document: string | null;
}

interface DocumentResult {
  filename: string;
  status: string;
  document_type: string;
  extraction_method: string;
  extracted_text: string;
  fields: ExtractedFields;
  warnings: string[];
  processed_at: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  fichier: File | null = null;
  resultat: DocumentResult | null = null;
  chargement = false;
  erreur = '';

  private apiUrl = 'http://127.0.0.1:8000/documents';

  constructor(private http: HttpClient) {}

  selectionnerFichier(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.fichier = input.files?.[0] ?? null;
    this.resultat = null;
    this.erreur = '';
  }

  analyserDocument(): void {
    if (!this.fichier || this.chargement) {
      return;
    }

    this.chargement = true;
    this.erreur = '';
    this.resultat = null;

    const formData = new FormData();
    formData.append('file', this.fichier);

    this.http.post<DocumentResult>(this.apiUrl, formData)
      .subscribe({
        next: (reponse) => {
          this.resultat = reponse;
          this.chargement = false;
        },
        error: (error: HttpErrorResponse) => {
          this.erreur =
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'Impossible de contacter le serveur Python.';
          this.chargement = false;
        }
      });
  }

  champsDetectes(): { label: string; valeur: string }[] {
    if (!this.resultat) {
      return [];
    }

    const champs = this.resultat.fields;

    const valeurs: { label: string; valeur: string | null }[] = [
      { label: 'Nom', valeur: champs.nom },
      { label: 'Prénom', valeur: champs.prenom },
      { label: 'Date détectée', valeur: champs.date },
      { label: 'Date de naissance', valeur: champs.date_naissance },
      { label: 'Date de délivrance', valeur: champs.date_delivrance },
      { label: 'Date d’expiration', valeur: champs.date_expiration },
      { label: 'Montant', valeur: champs.montant },
      { label: 'Email', valeur: champs.email },
      { label: 'Téléphone', valeur: champs.telephone },
      { label: 'Nationalité', valeur: champs.nationalite },
      { label: 'Adresse', valeur: champs.adresse },
      { label: 'Numéro du document', valeur: champs.numero_document }
    ];

    return valeurs
      .filter((champ): champ is { label: string; valeur: string } =>
        champ.valeur !== null && champ.valeur.trim() !== ''
      );
  }
}
