/// <reference types="vite/client" />

// Typage de la variable d'environnement utilisée par l'application.
interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
