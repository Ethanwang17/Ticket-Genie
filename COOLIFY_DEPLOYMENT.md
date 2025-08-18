# Coolify Deployment Guide

This guide will help you deploy the Ticket Genie Discord bots to your Coolify homelab.

## Prerequisites

-   Coolify installed and running on your homelab
-   Git repository (GitHub/GitLab) containing this code
-   Discord bot tokens for both HouseSeats and FillASeat bots

## Deployment Steps

### 1. Prepare Your Repository

Make sure your repository is pushed to GitHub/GitLab with the following files:

-   `Dockerfile` ✅
-   `.dockerignore` ✅
-   Updated `.gitignore` ✅
-   All bot source code

**Important**: The `config.py` file should NOT be in your repository (it's ignored by `.gitignore`).

### 2. Create New Application in Coolify

1. Open your Coolify dashboard
2. Click "New Application"
3. Choose "Git Repository" as the source
4. Connect your GitHub/GitLab repository
5. Select the repository: `Ticket-Genie`
6. Set the build pack to "Docker"

### 3. Configure Environment Variables

In Coolify, navigate to your application's "Environment Variables" section and add the following:

#### Required Discord Bot Tokens

```
HOUSESEATS_DISCORD_BOT_TOKEN=your_houseseats_bot_token_here
FILLASEAT_DISCORD_BOT_TOKEN=your_fillaseat_bot_token_here
```

#### Required Discord Channel IDs

```
HOUSESEATS_DISCORD_CHANNEL_ID=your_houseseats_channel_id
FILLASEAT_DISCORD_CHANNEL_ID=your_fillaseat_channel_id
```

#### Supabase Configuration

```
SUPABASE_URL=https://ivktfxucuzeokbxkwgpz.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_key_here
```

#### HouseSeats Credentials

```
HOUSESEATS_EMAIL=your_houseseats_email
HOUSESEATS_PASSWORD=your_houseseats_password
```

#### FillASeat Credentials

```
FILLASEAT_USERNAME=your_fillaseat_username
FILLASEAT_PASSWORD=your_fillaseat_password
```

#### Email Configuration (if used)

```
SENDER_EMAIL=your_email@example.com
SENDER_PASSWORD=your_email_app_password
RECEIVER_EMAIL=receiver@example.com
```

### 4. Deploy the Application

1. After configuring all environment variables, click "Deploy"
2. Coolify will:
    - Clone your repository
    - Build the Docker image using your `Dockerfile`
    - Start the container with your environment variables
    - Run `python run_bots.py` as the main process

### 5. Monitor the Deployment

1. Check the "Logs" section in Coolify to see the application startup
2. You should see messages like:
    ```
    Starting Ticket Genie bots...
    Python version: 3.11.x
    SUPABASE_URL: SET
    SUPABASE_SERVICE_KEY: SET
    Starting HouseSeats bot...
    Starting FillASeat bot...
    Both bots started successfully!
    ```

### 6. Verify Bots are Working

1. Check your Discord servers to confirm the bots are online
2. Monitor the application logs for any error messages
3. Verify that the bots are posting updates as expected

## Troubleshooting

### Common Issues

1. **Bot tokens not working**:

    - Verify tokens are correct in environment variables
    - Check Discord Developer Portal for bot permissions

2. **Database connection issues**:

    - Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are correct
    - Ensure your homelab can reach supabase.co (outbound HTTPS)

3. **Build failures**:

    - Check Coolify build logs
    - Verify all dependencies in `requirements.txt` are available

4. **Memory/CPU issues**:
    - Monitor resource usage in Coolify
    - Adjust container limits if needed

### Accessing Logs

-   Real-time logs: Coolify dashboard → Your app → Logs
-   Container logs: `docker logs <container_name>` on your homelab

## Maintenance

### Updating the Application

1. Push changes to your Git repository
2. In Coolify, click "Redeploy" or enable auto-deployment
3. Monitor logs to ensure successful deployment

### Backup Considerations

-   Environment variables are stored in Coolify
-   Application data is in Supabase (already backed up)
-   Consider backing up your Coolify configuration

## Cost Savings

By moving from Heroku ($5/month) to Coolify on your homelab:

-   **Monthly savings**: $5
-   **Annual savings**: $60
-   **Additional benefits**: Full control, better monitoring, dedicated resources

## Security Notes

-   Never commit `config.py` to your repository
-   Use strong passwords for all credentials
-   Consider rotating credentials periodically
-   Monitor access logs regularly
