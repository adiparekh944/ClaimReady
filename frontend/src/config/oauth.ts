export const oauthConfig = {
  google: {
    clientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
    clientSecret: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_SECRET,
    redirectUrl: process.env.NEXT_PUBLIC_OAUTH_REDIRECT_URL,
    siteUrl: process.env.NEXT_PUBLIC_SITE_URL || 'https://useclaimready.ai',
    scopes: [
      'https://www.googleapis.com/auth/userinfo.email',
      'https://www.googleapis.com/auth/userinfo.profile'
    ]
  }
};

export const getGoogleOAuthUrl = () => {
  const baseUrl = 'https://accounts.google.com/o/oauth2/v2/auth';
  const params = new URLSearchParams({
    client_id: oauthConfig.google.clientId!,
    redirect_uri: oauthConfig.google.redirectUrl!,
    response_type: 'code',
    scope: oauthConfig.google.scopes.join(' '),
    access_type: 'offline',
    prompt: 'consent',
    ...oauthConfig.google.additionalParams
  });
  
  return `${baseUrl}?${params.toString()}`;
};
