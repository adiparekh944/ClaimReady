import { createClient } from '@supabase/supabase-js';

// Initialize Supabase client
const supabaseUrl = "https://hjomhelzgvdmjyhijyxr.supabase.co";
const supabaseAnonKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhqb21oZWx6Z3ZkbWp5aGlqeXhyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcwODU1MTMsImV4cCI6MjA2MjY2MTUxM30.D1pwL5D6uAv_e3hNkmb91ju2JsTDBf1xPk3OgJ-_71w";

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables');
  // Don't throw here to allow the app to continue in development
}

// Create and export the Supabase client
const supabase = createClient(supabaseUrl, supabaseAnonKey);

export default supabase;






export { supabase };