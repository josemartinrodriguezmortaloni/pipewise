import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl) {
  throw new Error("NEXT_PUBLIC_SUPABASE_URL environment variable is required");
}

if (!supabaseAnonKey) {
  throw new Error(
    "NEXT_PUBLIC_SUPABASE_ANON_KEY environment variable is required"
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Types para TypeScript
export interface User {
  id: string;
  email: string;
  full_name: string;
  company?: string;
  phone?: string;
  has_2fa: boolean;
  created_at: string;
  last_login?: string;
}

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: User;
}
