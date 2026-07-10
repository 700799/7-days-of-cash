// Shared Worker types.

export interface Env {
  DB: D1Database;
  ASSETS: Fetcher;
  APP_ORIGIN: string;
  GOOGLE_CLIENT_ID?: string;
  GOOGLE_CLIENT_SECRET?: string;
  RESEND_API_KEY?: string;
  EMAIL_FROM?: string;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  picture: string | null;
}

export type AppContext = {
  Bindings: Env;
  Variables: {
    user: User | null;
  };
};
