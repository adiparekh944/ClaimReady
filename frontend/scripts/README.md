# Fake User Generation Script

This script generates 348 fake user accounts with believable names, email addresses, and creation dates, then uploads them to your Supabase database.

## Features

- **348 unique users** with realistic names
- **Believable email addresses** using common domains (Gmail, Yahoo, Hotmail, etc.)
- **Random creation dates** within the last 2 years
- **Unique usernames** based on first and last names
- **Strong passwords** for each account
- **Email verification status** (90% verified, 10% pending)
- **Last sign-in dates** (80% have signed in at least once)

## Prerequisites

1. **Supabase Service Role Key**: You need the service role key (not the anon key) to create users
2. **Environment Variables**: Make sure your `.env` file in the frontend directory has:
   ```
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   ```

## Installation

1. Navigate to the scripts directory:
   ```bash
   cd frontend/scripts
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Usage

Run the script to generate and upload 348 fake users:

```bash
npm run generate-users
```

Or run directly with Node:

```bash
node generate-fake-users.js
```

## What the Script Does

1. **Generates 348 unique users** with:
   - Realistic first and last names
   - Unique email addresses
   - Unique usernames
   - Strong passwords
   - Random creation dates (last 2 years)
   - Email verification status
   - Last sign-in dates

2. **Uploads to Supabase** in batches of 10 users to avoid rate limits

3. **Provides progress updates** and final summary

## Sample Output

```
Generating 348 fake user accounts...
Sample users generated:
1. Sarah Johnson (sarahjohnson) - sarah.johnson@gmail.com
2. Michael Chen (michaelchen) - michaelchen@yahoo.com
3. Emily Rodriguez (emilyrodriguez) - emily.rodriguez@hotmail.com

Starting upload to Supabase...
Processing batch 1/35...
✓ Created user: sarah.johnson@gmail.com (sarahjohnson)
✓ Created user: michaelchen@yahoo.com (michaelchen)
...

=== Upload Complete ===
Successfully created: 348 users
Errors: 0 users
Total processed: 348 users
```

## Important Notes

- **Service Role Key Required**: This script uses the service role key to create users directly
- **Rate Limiting**: The script processes users in batches with delays to avoid Supabase rate limits
- **Unique Constraints**: The script ensures all emails and usernames are unique
- **Realistic Data**: All generated data looks realistic and believable

## Troubleshooting

### "Missing Supabase environment variables"
- Make sure your `.env` file exists in the frontend directory
- Verify the environment variable names are correct
- Ensure you're using the service role key, not the anon key

### "Error creating user"
- Check your Supabase service role key permissions
- Verify your Supabase project is active
- Check for any unique constraint violations

### Rate limiting errors
- The script includes delays between batches, but if you still get rate limited, increase the delay in the script

## Customization

You can modify the script to:
- Change the number of users (modify the `count` parameter)
- Adjust the date range for creation dates
- Modify email patterns or domains
- Change the batch size for uploads
- Add additional user metadata fields

## Security Note

This script is for development/testing purposes only. The generated passwords are random and not stored anywhere - users would need to use the "forgot password" feature to access their accounts. 