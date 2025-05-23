# Supabase Migration Guide for Ticket Genie

## Overview

This guide walks you through migrating your Ticket Genie project from PostgreSQL to Supabase while keeping your Python bots running on Heroku.

## Step 1: Set Up Supabase Project

### 1.1 Create Supabase Account

1. Go to [supabase.com](https://supabase.com)
2. Sign up for a free account
3. Create a new project
4. Choose your organization and set project details
5. Set a strong database password
6. Select a region (preferably close to your Heroku app)

### 1.2 Get Your Credentials

1. Go to Settings → API in your Supabase dashboard
2. Copy the following values:
    - Project URL
    - `anon/public` key
    - `service_role` key (this is what we'll use for backend operations)

## Step 2: Create Database Schema

### 2.1 Run SQL Commands

1. Go to SQL Editor in your Supabase dashboard
2. Create a new query and run this SQL:

```sql
-- HouseSeats Current Shows Table
CREATE TABLE houseseats_current_shows (
    id TEXT PRIMARY KEY,
    name TEXT,
    url TEXT,
    image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- HouseSeats All Shows Table
CREATE TABLE houseseats_all_shows (
    id TEXT PRIMARY KEY,
    name TEXT,
    url TEXT,
    image_url TEXT,
    first_seen_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- HouseSeats User Blacklists Table
CREATE TABLE houseseats_user_blacklists (
    user_id BIGINT NOT NULL,
    show_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, show_id)
);

-- FillASeat Current Shows Table
CREATE TABLE fillaseat_current_shows (
    id TEXT PRIMARY KEY,
    name TEXT,
    url TEXT,
    image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- FillASeat All Shows Table
CREATE TABLE fillaseat_all_shows (
    id TEXT PRIMARY KEY,
    name TEXT,
    url TEXT,
    image_url TEXT,
    first_seen_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- FillASeat User Blacklists Table
CREATE TABLE fillaseat_user_blacklists (
    user_id BIGINT NOT NULL,
    show_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, show_id)
);

-- Add indexes for better performance
CREATE INDEX idx_houseseats_current_shows_created_at ON houseseats_current_shows(created_at);
CREATE INDEX idx_houseseats_all_shows_first_seen_date ON houseseats_all_shows(first_seen_date);
CREATE INDEX idx_houseseats_user_blacklists_user_id ON houseseats_user_blacklists(user_id);
CREATE INDEX idx_fillaseat_current_shows_created_at ON fillaseat_current_shows(created_at);
CREATE INDEX idx_fillaseat_all_shows_first_seen_date ON fillaseat_all_shows(first_seen_date);
CREATE INDEX idx_fillaseat_user_blacklists_user_id ON fillaseat_user_blacklists(user_id);
```

## Step 3: Update Heroku Environment Variables

### 3.1 Set New Environment Variables

In your Heroku dashboard, go to Settings → Config Vars and add:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key_here
```

### 3.2 Remove Old Environment Variable (Optional)

You can optionally remove the `DATABASE_URL` environment variable since it's no longer needed.

## Step 4: Deploy Updated Code

### 4.1 Commit and Push Changes

```bash
git add .
git commit -m "Migrate to Supabase database"
git push heroku main
```

### 4.2 Monitor Deployment

1. Watch the Heroku logs: `heroku logs --tail`
2. Ensure the bots start successfully
3. Check that new dependencies are installed correctly

## Step 5: Data Migration (Optional)

If you have existing data in your PostgreSQL database that you want to migrate:

### 5.1 Export Data from PostgreSQL

```bash
# Connect to your Heroku Postgres database
heroku pg:psql

# Export data to CSV
\copy houseseats_current_shows TO 'houseseats_current_shows.csv' CSV HEADER;
\copy houseseats_all_shows TO 'houseseats_all_shows.csv' CSV HEADER;
\copy houseseats_user_blacklists TO 'houseseats_user_blacklists.csv' CSV HEADER;
\copy fillaseat_current_shows TO 'fillaseat_current_shows.csv' CSV HEADER;
\copy fillaseat_all_shows TO 'fillaseat_all_shows.csv' CSV HEADER;
\copy fillaseat_user_blacklists TO 'fillaseat_user_blacklists.csv' CSV HEADER;
```

### 5.2 Import Data to Supabase

1. Go to your Supabase dashboard
2. Navigate to Table Editor
3. Select each table and use the Import data feature
4. Upload your CSV files

## Step 6: Testing

### 6.1 Verify Bot Functionality

1. Check that both bots are running in Heroku logs
2. Test slash commands in Discord:
    - `/current_shows`
    - `/houseseats_all_shows`
    - `/blacklist_add [show_id]`
    - `/blacklist_list`

### 6.2 Monitor Database Operations

1. Go to Supabase dashboard → Logs
2. Check for any database errors
3. Verify that data is being inserted correctly

## Step 7: Cleanup

### 7.1 Remove Old Dependencies (Optional)

If everything is working correctly, you can remove `psycopg2-binary` from your `requirements.txt` file.

### 7.2 Update Documentation

Update your project documentation to reflect the new Supabase setup.

## Troubleshooting

### Common Issues

#### 1. Authentication Errors

-   Verify your `SUPABASE_SERVICE_KEY` is correct
-   Ensure you're using the service role key, not the anon key

#### 2. Table Not Found Errors

-   Verify all tables were created correctly in Supabase
-   Check table names match exactly (case-sensitive)

#### 3. Connection Timeouts

-   Supabase has connection limits on the free tier
-   Consider upgrading if you hit rate limits

#### 4. Heroku Deployment Issues

-   Check that all new dependencies are in `requirements.txt`
-   Verify environment variables are set correctly
-   Monitor Heroku logs for specific error messages

### Getting Help

1. Check Supabase documentation: [docs.supabase.com](https://docs.supabase.com)
2. Join Supabase Discord community
3. Check Heroku logs for specific error details

## Benefits of Supabase Migration

1. **Better Performance**: Supabase offers optimized PostgreSQL with built-in connection pooling
2. **Real-time Features**: Future ability to add real-time subscriptions
3. **Better Monitoring**: Built-in dashboard for monitoring database performance
4. **Scalability**: Easy to scale as your bot grows
5. **Backup & Recovery**: Automated backups and point-in-time recovery
6. **Cost Effective**: Generous free tier, potentially cheaper than Heroku Postgres

## Rollback Plan

If you need to rollback to PostgreSQL:

1. Revert to previous commit: `git revert [commit_hash]`
2. Re-add `DATABASE_URL` environment variable
3. Deploy previous version: `git push heroku main`
4. Restore data from backup if needed

This migration maintains all existing functionality while providing a more robust and feature-rich database solution.
