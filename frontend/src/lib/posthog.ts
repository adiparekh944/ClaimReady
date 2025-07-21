import posthog from 'posthog-js';

if (typeof window !== 'undefined') {
  posthog.init('phc_B6w0jn8ETkJOcXAbJPtlkqhnqznQAryp0Fvhdg5VjuG', {
    api_host: 'https://app.posthog.com', // or your self-hosted URL
  });
}

export default posthog;