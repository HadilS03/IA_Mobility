-- Schéma de la base IA Mobility (PostgreSQL)
-- Exécuté automatiquement au premier démarrage du conteneur PostgreSQL
-- (fichier monté dans /docker-entrypoint-initdb.d/ via docker-compose).
--
-- Deux tables seulement, à l'image du rapport E1 :
--   parkings : le référentiel (une ligne par parking, données stables).
--   releves  : l'historique horodaté de l'occupation (plusieurs lignes par parking).
-- On sépare les deux car un parking a une identité fixe (nom, position, capacité)
-- alors que son occupation change en permanence : c'est le principe d'une base
-- relationnelle normalisée, qui évite de répéter le nom/les coordonnées à chaque relevé.

CREATE TABLE IF NOT EXISTS parkings (
    id              SERIAL PRIMARY KEY,
    nom             TEXT             NOT NULL UNIQUE,   -- clé métier : sert à retrouver un parking
    latitude        DOUBLE PRECISION,                  -- pour l'affichage sur la carte Leaflet
    longitude       DOUBLE PRECISION,
    capacite_totale INTEGER          CHECK (capacite_totale >= 0)
);

CREATE TABLE IF NOT EXISTS releves (
    id               SERIAL PRIMARY KEY,
    parking_id       INTEGER      NOT NULL REFERENCES parkings(id) ON DELETE CASCADE,
    horodatage       TIMESTAMP    NOT NULL,
    places_libres    INTEGER      CHECK (places_libres >= 0),
    taux_occupation  NUMERIC(5,2) CHECK (taux_occupation >= 0 AND taux_occupation <= 100),
    -- Un même parking ne peut avoir qu'un seul relevé pour un horodatage donné.
    -- Cette contrainte rend l'import idempotent : réimporter n'ajoute pas de doublon.
    UNIQUE (parking_id, horodatage)
);

-- Index sur la clé étrangère : accélère "tous les relevés d'un parking"
-- (endpoint /parkings/<nom>/historique et requêtes SQL du rapport E1).
CREATE INDEX IF NOT EXISTS idx_releves_parking_id ON releves(parking_id);

-- Index sur l'horodatage : accélère les filtres par plage de dates.
CREATE INDEX IF NOT EXISTS idx_releves_horodatage ON releves(horodatage);
