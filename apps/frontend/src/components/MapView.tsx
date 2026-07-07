import { useEffect, useRef } from 'react';
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

import type { EtatPrediction, Parking } from '../types';
import { texteOccupation } from '../lib/format';

// Correction connue : sans cela, les icônes par défaut de Leaflet ne s'affichent
// pas quand le projet est empaqueté par Vite (les chemins d'images sont perdus).
const IconeDefaut = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = IconeDefaut;

// Centre de Bordeaux (le projet cible cette ville).
const CENTRE_BORDEAUX: [number, number] = [44.8378, -0.5792];

interface Props {
  parkings: Parking[];
  predictions: Record<string, EtatPrediction>;
  selection: string | null;
}

// Composant interne : recentre la carte sur le parking sélectionné dans le panneau.
function AllerVers({ position }: { position: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (position) {
      map.flyTo(position, 15);
    }
  }, [position, map]);
  return null;
}

function MapView({ parkings, predictions, selection }: Props) {
  // On garde une référence vers chaque marqueur pour pouvoir ouvrir sa popup
  // quand l'utilisateur clique sur le parking dans le panneau latéral.
  const marqueurs = useRef<Record<string, L.Marker>>({});

  const parkingSelectionne = parkings.find((p) => p.nom === selection) ?? null;
  const positionSelection: [number, number] | null =
    parkingSelectionne && parkingSelectionne.latitude != null && parkingSelectionne.longitude != null
      ? [parkingSelectionne.latitude, parkingSelectionne.longitude]
      : null;

  useEffect(() => {
    if (selection && marqueurs.current[selection]) {
      marqueurs.current[selection].openPopup();
    }
  }, [selection]);

  return (
    <MapContainer center={CENTRE_BORDEAUX} zoom={13} className="carte">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <AllerVers position={positionSelection} />

      {parkings
        // On n'affiche que les parkings géolocalisés.
        .filter((p) => p.latitude != null && p.longitude != null)
        .map((p) => (
          <Marker
            key={p.nom}
            position={[p.latitude as number, p.longitude as number]}
            ref={(m) => {
              if (m) marqueurs.current[p.nom] = m;
            }}
          >
            <Popup>
              <strong>{p.nom}</strong>
              <br />
              Capacité : {p.capacite_totale ?? '—'} places
              <br />
              {texteOccupation(predictions[p.nom])}
            </Popup>
          </Marker>
        ))}
    </MapContainer>
  );
}

export default MapView;
