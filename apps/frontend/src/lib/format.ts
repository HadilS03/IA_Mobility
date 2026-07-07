import type { EtatPrediction } from '../types';

// Texte lisible décrivant l'état d'occupation d'un parking.
export function texteOccupation(etat: EtatPrediction | undefined): string {
  if (!etat || etat.statut === 'chargement') return 'Chargement…';
  if (etat.statut === 'ok') return `${etat.taux.toFixed(0)} % occupé`;
  if (etat.statut === 'indisponible') return 'Prédiction indisponible';
  return 'Erreur de prédiction';
}

// Couleur associée au taux : vert = places probables, rouge = quasi plein.
// Aide l'utilisateur à repérer d'un coup d'œil où se garer.
export function couleurOccupation(etat: EtatPrediction | undefined): string {
  if (etat?.statut === 'ok') {
    if (etat.taux < 50) return '#2e7d32';
    if (etat.taux < 80) return '#f9a825';
    return '#c62828';
  }
  return '#9e9e9e';
}
