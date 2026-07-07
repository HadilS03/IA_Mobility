/// <reference types="vite/client" />

// Typage de la variable d'environnement utilisée par l'application.
interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_DATA_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
