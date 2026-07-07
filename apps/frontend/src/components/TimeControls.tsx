// Sélecteur d'heure et de jour : permet de simuler une prédiction à un autre
// moment que « maintenant » (très utile pour la démonstration devant le jury).

const JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];

interface Props {
  heure: number;
  jour: number;
  onChangeHeure: (h: number) => void;
  onChangeJour: (j: number) => void;
}

function TimeControls({ heure, jour, onChangeHeure, onChangeJour }: Props) {
  return (
    <div className="controls">
      <label>
        Jour
        <select value={jour} onChange={(e) => onChangeJour(Number(e.target.value))}>
          {JOURS.map((nom, index) => (
            <option key={index} value={index}>{nom}</option>
          ))}
        </select>
      </label>
      <label>
        Heure
        <select value={heure} onChange={(e) => onChangeHeure(Number(e.target.value))}>
          {Array.from({ length: 24 }, (_, h) => (
            <option key={h} value={h}>{h}h</option>
          ))}
        </select>
      </label>
    </div>
  );
}

export default TimeControls;
