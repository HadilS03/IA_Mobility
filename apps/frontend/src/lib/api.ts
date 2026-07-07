import type { Parking } from '../types';

// URL de l'API configurable via variable d'environnement Vite (VITE_API_URL).
// Par défaut, l'API locale du service Python.
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000';

// Clé d'API exigée par les endpoints de données (/parkings, /historique, /dataset).
const DATA_API_KEY = import.meta.env.VITE_DATA_API_KEY ?? '';

export async function recupererParkings(): Promise<Parking[]> {
  // Endpoint protégé : on transmet la clé d'API. Un 401 (clé absente/invalide)
  // fait échouer la requête et est traité comme une indisponibilité côté UI.
  const reponse = await fetch(`${API_URL}/parkings`, {
    headers: { 'X-API-Key': DATA_API_KEY },
  });
  if (!reponse.ok) {
    throw new Error(`Appel /parkings en echec (${reponse.status})`);
  }
  return reponse.json();
}

export interface OptionsPrediction {
  heure: number;
  jour: number;
  minute?: number;
}

// Renvoie le taux d'occupation prédit (0–100), ou null si le parking est
// inconnu du modèle (réponse 404 : mode dégradé). Lève une erreur sinon.
export async function recupererPrediction(
  nom: string,
  opts: OptionsPrediction,
): Promise<number | null> {
  const params = new URLSearchParams({
    nom,
    heure: String(opts.heure),
    jour: String(opts.jour),
    minute: String(opts.minute ?? 0),
  });
  const reponse = await fetch(`${API_URL}/predict?${params.toString()}`);
  if (reponse.status === 404) {
    return null;
  }
  if (!reponse.ok) {
    throw new Error(`Appel /predict en echec (${reponse.status})`);
  }
  const data = await reponse.json();
  // L'API renvoie "44.33%" : on récupère le nombre.
  return parseFloat(String(data.prediction_occupation).replace('%', ''));
}
