import { useCallback, useEffect, useState } from 'react';

import './App.css';
import type { EtatPrediction, Parking } from './types';
import { recupererParkings, recupererPrediction } from './lib/api';
import MapView from './components/MapView';
import SidePanel from './components/SidePanel';

function App() {
  const [parkings, setParkings] = useState<Parking[]>([]);
  const [predictions, setPredictions] = useState<Record<string, EtatPrediction>>({});
  const [erreur, setErreur] = useState<string | null>(null);

  const maintenant = new Date();
  const [heure, setHeure] = useState<number>(maintenant.getHours());
  // getDay() : 0 = dimanche. Le modèle utilise 0 = lundi (weekday Python) : on convertit.
  const [jour, setJour] = useState<number>((maintenant.getDay() + 6) % 7);

  const [recherche, setRecherche] = useState<string>('');
  const [selection, setSelection] = useState<string | null>(null);

  // 1) Au chargement : on récupère la liste des parkings à afficher.
  useEffect(() => {
    recupererParkings()
      .then(setParkings)
      .catch(() => setErreur("Impossible de charger les parkings. L'API est-elle démarrée ?"));
  }, []);

  // 2) Récupère la prédiction de chaque parking pour l'heure/jour choisis.
  //    Recalculé à chaque changement de moment (mode « simulation »).
  const chargerPredictions = useCallback(
    (liste: Parking[]) => {
      // Tout passe en « chargement » le temps des appels.
      setPredictions(Object.fromEntries(liste.map((p) => [p.nom, { statut: 'chargement' }])));

      // Appels en parallèle : chaque parking se met à jour dès sa réponse.
      // Un échec sur un parking ne bloque pas les autres (mode dégradé).
      liste.forEach(async (p) => {
        try {
          const taux = await recupererPrediction(p.nom, { heure, jour });
          setPredictions((prev) => ({
            ...prev,
            [p.nom]: taux === null ? { statut: 'indisponible' } : { statut: 'ok', taux },
          }));
        } catch {
          setPredictions((prev) => ({ ...prev, [p.nom]: { statut: 'erreur' } }));
        }
      });
    },
    [heure, jour],
  );

  useEffect(() => {
    if (parkings.length > 0) {
      chargerPredictions(parkings);
    }
  }, [parkings, chargerPredictions]);

  return (
    <div className="app">
      <SidePanel
        parkings={parkings}
        predictions={predictions}
        recherche={recherche}
        heure={heure}
        jour={jour}
        onRecherche={setRecherche}
        onChangeHeure={setHeure}
        onChangeJour={setJour}
        onSelection={setSelection}
      />
      <div className="zone-carte">
        {erreur && <div className="bandeau-erreur">{erreur}</div>}
        <MapView parkings={parkings} predictions={predictions} selection={selection} />
      </div>
    </div>
  );
}

export default App;
