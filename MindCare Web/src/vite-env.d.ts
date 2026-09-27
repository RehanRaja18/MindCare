/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend API root, ending in "/api/v1" (e.g. https://<backend-host>/api/v1). */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
