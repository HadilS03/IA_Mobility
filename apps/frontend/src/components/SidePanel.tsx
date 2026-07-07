import type { EtatPrediction, Parking } from '../types';
import { couleurOccupation, texteOccupation } from '../lib/format';
import TimeControls from './TimeControls';

interface Props {
  parkings: Parking[];
  predictions: Record<string, EtatPrediction>;
  recherche: string;
  heure: number;
  jour: number;
  onRecherche: (valeur: string) => void;
  onChangeHeure: (h: number) => void;
  onChangeJour: (j: number) => void;
  onSelection: (nom: string) => void;
}

// Valeur de tri : un parking dont la prédiction est connue passe avant les
// autres ; on trie ensuite par occupation croissante (« où me garer ? »).
function rangTri(etat: EtatPrediction | undefined): number {
  return etat?.statut === 'ok' ? etat.taux : Number.POSITIVE_INFINITY;
}

function SidePanel(props: Props) {
  const { parkings, predictions, recherche, heure, jour } = props;

  const liste = parkings
    .filter((p) => p.nom.toLowerCase().includes(recherche.toLowerCase()))
    .sort((a, b) => rangTri(predictions[a.nom]) - rangTri(predictions[b.nom]));

  return (
    <aside className="panneau">
      <h1>IA Mobility</h1>
      <p className="sous-titre">Occupation estimée des parkings de Bordeaux</p>

      <input
        className="recherche"
        type="search"
        placeholder="Rechercher un parking…"
        value={recherche}
        onChange={(e) => props.onRecherche(e.target.value)}
        aria-label="Rechercher un parking"
      />

      <TimeControls
        heure={heure}
        jour={jour}
        onChangeHeure={props.onChangeHeure}
        onChangeJour={props.onChangeJour}
      />

      <p className="compteur">{liste.length} parking(s) — triés du plus libre au plus occupé</p>

      <ul className="liste-parkings">
        {liste.map((p) => {
          const etat = predictions[p.nom];
          return (
            <li key={p.nom}>
              <button className="item-parking" onClick={() => props.onSelection(p.nom)}>
                <span className="pastille" style={{ backgroundColor: couleurOccupation(etat) }} />
                <span className="nom">{p.nom}</span>
                <span className="occ">{texteOccupation(etat)}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

export default SidePanel;
