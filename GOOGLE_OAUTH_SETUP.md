# Google OAuth Setup Guide

This guide will help you set up Google OAuth authentication for your ClaimReady application.

## Prerequisites

- A Google Cloud Console account
- Access to your Supabase project dashboard

## Step 1: Google Cloud Console Setup

### 1.1 Create a New Project or Select Existing One
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API (if not already enabled)

### 1.2 Configure OAuth Consent Screen
1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type
3. Fill in the required information:
   - App name: "ClaimReady"
   - User support email: Your email
   - Developer contact information: Your email
   - App domain: Add `useclaimready.ai` as an authorized domain
4. Add scopes:
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
5. Add test users (your email addresses for testing)
6. **Important**: Make sure your app domain is set to `useclaimready.ai` to show the correct domain in the OAuth consent screen

### 1.3 Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Web application"
4. Set authorized redirect URIs:
   - `https://hjomhelzgvdmjyhijyxr.supabase.co/auth/v1/callback`
   - `https://useclaimready.ai/auth/callback`
   - `http://localhost:3000/auth/callback` (for local development)
5. In "Authorized JavaScript origins", add:
   - `https://useclaimready.ai`
   - `http://localhost:3000`
6. Copy the Client ID and Client Secret

## Step 2: Supabase Configuration

### 2.1 Enable Google Provider
1. Go to your Supabase project dashboard
2. Navigate to "Authentication" > "Providers"
3. Find "Google" and click "Enable"
4. Enter your Google OAuth credentials:
   - Client ID: Your Google Client ID
   - Client Secret: Your Google Client Secret
5. Save the configuration

### 2.2 Configure Redirect URLs
1. In Supabase, go to "Authentication" > "URL Configuration"
2. Add your redirect URLs:
   - Site URL: `https://useclaimready.ai` (for production)
   - Redirect URLs: 
     - `https://useclaimready.ai/auth/callback`
     - `http://localhost:3000/auth/callback` (for local development)

## Step 3: Environment Variables

Update your `frontend/.env.local` file with your Google OAuth credentials:

```bash
# Google OAuth Configuration
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_actual_google_client_id_here
NEXT_PUBLIC_GOOGLE_CLIENT_SECRET=your_actual_google_client_secret_here

# OAuth Redirect Configuration
NEXT_PUBLIC_OAUTH_REDIRECT_URL=https://useclaimready.ai/auth/callback
NEXT_PUBLIC_LOCAL_OAUTH_REDIRECT_URL=http://localhost:3000/auth/callback
NEXT_PUBLIC_SITE_URL=https://useclaimready.ai
```

**Important**: Replace the placeholder values with your actual Google OAuth credentials.

## Step 4: Testing

1. Start your application: `make application`
2. Go to the login or signup page
3. Click "Sign in with Google"
4. You should be redirected to Google's OAuth consent screen
5. After authorization, you'll be redirected back to your app

## Troubleshooting

### Common Issues

1. **"Invalid redirect URI" error**
   - Ensure the redirect URI in Google Cloud Console matches exactly
   - Check that Supabase redirect URLs are configured correctly

2. **"OAuth provider not enabled" error**
   - Verify Google provider is enabled in Supabase
   - Check that credentials are entered correctly

3. **Callback page not found**
   - Ensure the `/auth/callback` route exists
   - Check that the callback page is properly configured

### Debug Steps

1. Check browser console for errors
2. Verify environment variables are loaded correctly
3. Check Supabase logs for authentication errors
4. Ensure all redirect URLs are properly configured

## Security Considerations

1. **Never commit OAuth secrets to version control**
2. **Use environment variables for sensitive data**
3. **Restrict OAuth consent screen to necessary scopes only**
4. **Regularly rotate OAuth credentials**
5. **Monitor OAuth usage and access patterns**

## Production Deployment

When deploying to production:

1. Update redirect URIs in Google Cloud Console
2. Update Supabase site URL and redirect URLs
3. Ensure HTTPS is enabled for all production URLs
4. Consider implementing additional security measures

## Support

If you encounter issues:

1. Check the [Supabase Auth documentation](https://supabase.com/docs/guides/auth)
2. Review [Google OAuth documentation](https://developers.google.com/identity/protocols/oauth2)
3. Check your browser's network tab for failed requests
4. Verify all configuration steps have been completed

---

**Note**: This setup enables Google OAuth for both sign-in and sign-up. Users can create accounts or sign in to existing accounts using their Google credentials.
