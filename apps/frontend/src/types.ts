// Types partagés de l'application.

export interface Parking {
  nom: string;
  latitude: number | null;
  longitude: number | null;
  capacite_totale: number | null;
}

// État de la prédiction d'occupation pour un parking donné.
// Un parking peut être inconnu du modèle (404) : on le distingue d'une vraie erreur.
export type EtatPrediction =
  | { statut: 'chargement' }
  | { statut: 'ok'; taux: number }
  | { statut: 'indisponible' }
  | { statut: 'erreur' };
