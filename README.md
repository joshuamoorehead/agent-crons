# agent-crons

Scheduled GitHub Actions workflows for the Marcus agent swarm.

## Overview

This repository contains all scheduled automation jobs that run on behalf of the Marcus agent collective. Each workflow is triggered by GitHub Actions cron schedules and operates independently as a coordinated agent task.

## Current Workflows

### good-morning.yml (TEST)
- **Status**: Test workflow to verify plumbing
- **Schedule**: Daily at 11:30 UTC (6:30 AM ET)
- **Purpose**: Posts a morning greeting to Discord
- **Trigger**: Cron + manual dispatch

## Planned Workflows

Future automations will include:

- **Morning Brief** - Daily summary of news, calendar, and priorities
- **Paper Monitor** - ArXiv/research paper alerts matching interest areas
- **Job Scanner** - Automated job board monitoring and filtering
- **Health Checks** - System status and uptime monitoring
- **Reminder Engine** - Scheduled notifications and follow-ups

## Architecture

- Each workflow is a standalone `.yml` file under `.github/workflows/`
- Secrets are stored as GitHub repository secrets
- Discord notifications use webhook integration
- All workflows support `workflow_dispatch` for manual testing

## Secrets

Configure the following repository secrets in Settings → Secrets and variables → Actions:

- `DISCORD_WEBHOOK` - Discord webhook URL for notifications

## Usage

Workflows run automatically on their schedules. To manually trigger a workflow:

1. Go to the **Actions** tab
2. Select the workflow from the sidebar
3. Click **Run workflow**
4. Confirm the branch and click **Run workflow**

---

Part of the Marcus agent ecosystem.
