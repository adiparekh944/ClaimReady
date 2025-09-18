/**
 * Frontend configuration
 */

// Get backend URL from environment or default to localhost
export const getBackendUrl = (): string => {
  // Check for environment variable first
  if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_BACKEND_URL) {
    return process.env.NEXT_PUBLIC_BACKEND_URL;
  }
  
  // Default to localhost for development
  return 'http://127.0.0.1:8080';
};

// Helper function to build API endpoints
export const buildApiUrl = (endpoint: string): string => {
  const baseUrl = getBackendUrl().replace(/\/$/, ''); // Remove trailing slash
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${baseUrl}${cleanEndpoint}`;
};

// API endpoints
export const API_ENDPOINTS = {
  HEALTH: buildApiUrl('/health'),
  ANALYZE_IMAGE: buildApiUrl('/api/analyze-image'),
  ANALYZE_MULTIPLE_IMAGES: buildApiUrl('/api/analyze-multiple-images'),
} as const;
