# NextAuth Setup Guide

This guide explains how to set up NextAuth with Google OAuth for ClaimReady, replacing the previous Supabase authentication.

## What Changed

- **Replaced Supabase Auth** with NextAuth.js
- **Direct Google OAuth integration** - no more domain restrictions
- **Custom authentication context** for better control
- **Cleaner user experience** with your own domain

## Setup Steps

### 1. Environment Variables

Copy `.env.local.example` to `.env.local` and fill in your values:

```bash
cp .env.local.example .env.local
```

Required environment variables:
- `NEXTAUTH_SECRET`: A random string for JWT encryption
- `NEXTAUTH_URL`: Your site URL (http://localhost:3000 for development)
- `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret

### 2. Google OAuth Configuration

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select your project
3. Enable Google+ API
4. Configure OAuth consent screen:
   - App name: "ClaimReady"
   - User support email: Your email
   - Developer contact: Your email
   - **Important**: Set domain to `useclaimready.ai` (not Supabase domain)
5. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs:
     - `http://localhost:3000/api/auth/callback/google` (development)
     - `https://useclaimready.ai/api/auth/callback/google` (production)
   - Authorized JavaScript origins:
     - `http://localhost:3000` (development)
     - `https://useclaimready.ai` (production)

### 3. Generate NextAuth Secret

Generate a secure random string for `NEXTAUTH_SECRET`:

```bash
openssl rand -base64 32
```

Or use an online generator.

## How It Works

1. **User clicks "Sign in with Google"**
2. **Redirects to Google OAuth** (using your domain)
3. **Google redirects back** to your NextAuth callback
4. **NextAuth creates a session** and stores user data
5. **User is authenticated** and redirected to home page

## Benefits

- ✅ **No domain restrictions** - uses your own domain throughout
- ✅ **Better user experience** - clean OAuth flow
- ✅ **Full control** - customize authentication logic
- ✅ **No third-party branding** - your app, your domain
- ✅ **Scalable** - easy to add more providers later

## Files Changed

- `src/app/api/auth/[...nextauth]/route.ts` - NextAuth API routes
- `src/components/NextAuthContext.tsx` - New auth context
- `src/components/NextAuthGoogleSignInButton.tsx` - Google sign-in button
- `src/app/ClientLayout.tsx` - Updated to use NextAuth
- `src/app/login/page.tsx` - Updated login page
- `src/app/signup/page.tsx` - Updated signup page
- `src/components/Navbar.tsx` - Updated navigation
- `src/components/ProfileCard.tsx` - Updated profile display

## Testing

1. Start your development server: `npm run dev`
2. Go to `/login` or `/signup`
3. Click "Sign in with Google"
4. Complete Google OAuth flow
5. You should be redirected back to your app

## Troubleshooting

### Common Issues

1. **"Invalid redirect URI" error**
   - Check Google OAuth redirect URIs match exactly
   - Ensure `NEXTAUTH_URL` is set correctly

2. **"OAuth provider not enabled" error**
   - Verify Google provider is configured in NextAuth
   - Check environment variables are loaded

3. **Session not persisting**
   - Ensure `NEXTAUTH_SECRET` is set
   - Check browser cookies are enabled

### Debug Steps

1. Check browser console for errors
2. Verify environment variables in `.env.local`
3. Check NextAuth logs in terminal
4. Ensure all redirect URLs are configured correctly

## Production Deployment

When deploying to production:

1. Update `NEXTAUTH_URL` to your production domain
2. Update Google OAuth redirect URIs
3. Generate a new `NEXTAUTH_SECRET` for production
4. Ensure HTTPS is enabled

## Next Steps

- [ ] Implement email/password authentication
- [ ] Add user profile management
- [ ] Implement guest mode
- [ ] Add password reset functionality
- [ ] Integrate with your backend for user data storage

---

**Note**: This implementation focuses on Google OAuth. Additional authentication methods can be added later as needed.
