'use client';
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import supabase from './supabase';
import { Session, User } from '@supabase/supabase-js';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  isGuest: boolean;
  signIn: (email: string, password: string) => Promise<{ error: any } | undefined>;
  signUp: (email: string, password: string, username: string) => Promise<{ error: any } | undefined>;
  signInWithGoogle: () => Promise<{ error: any } | undefined>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ error: any } | undefined>;
  signInAsGuest: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [isGuest, setIsGuest] = useState(false);

  useEffect(() => {
    if (isGuest) {
      setUser(null);
      setSession(null);
      setLoading(false);
      return;
    }
    const setData = async () => {
      const { data } = await supabase.auth.getSession();
      setSession(data.session);
      setUser(data.session?.user ?? null);
      setLoading(false);
    };
    setData();
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user) setIsGuest(false); // <-- Add this line
    });
    return () => {
      listener.subscription.unsubscribe();
    };
  }, [isGuest]);

  const signIn = async (email: string, password: string) => {
    setLoading(true);
    setIsGuest(false); // <-- Add this line
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    return { error };
  };

  const signUp = async (email: string, password: string, username: string) => {
    setLoading(true);
    setIsGuest(false); // <-- Add this line
    const { error } = await supabase.auth.signUp({ 
      email, 
      password,
      options: {
        data: {
          username: username
        }
      }
    });
    setLoading(false);
    return { error };
  };

  const signInWithGoogle = async () => {
    setLoading(true);
    setIsGuest(false);
    
    // For production, redirect to your domain's callback
    // For local development, use localhost
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const redirectUrl = isLocalhost 
      ? 'http://localhost:3000/auth/callback'
      : 'https://useclaimready.ai/auth/callback';
    
    // Debug logging
    console.log('Current origin:', window.location.origin);
    console.log('Is localhost:', isLocalhost);
    console.log('Final redirect URL being sent:', redirectUrl);
    
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: redirectUrl,
        queryParams: {
          // Force account selection
          prompt: 'select_account'
        }
      }
    });
    setLoading(false);
    return { error };
  };

  const signOut = async () => {
    setLoading(true);
    await supabase.auth.signOut();
    setIsGuest(false);
    setLoading(false);
  };

  const resetPassword = async (email: string) => {
    setLoading(true);
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`
    });
    setLoading(false);
    return { error };
  };

  const signInAsGuest = () => {
    setIsGuest(true);
    setUser(null);
    setSession(null);
    setLoading(false);
  };

  return (
    <AuthContext.Provider value={{ user, session, loading, isGuest, signIn, signUp, signInWithGoogle, signOut, resetPassword, signInAsGuest }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
} 