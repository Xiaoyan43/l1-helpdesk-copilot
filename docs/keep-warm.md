# Keep the Render demo warm

The public demo runs on [Render](https://render.com) **free tier**. After ~15 minutes of
inactivity the service sleeps; the first request then takes **~30–60 seconds** to wake.

## Recommended: cron-job.org (free)

1. Sign up at [cron-job.org](https://cron-job.org) (free tier is enough).
2. Create a cron job:
   - **URL:** `https://l1-helpdesk-copilot.onrender.com/healthz`
   - **Schedule:** every **14 minutes** (`*/14 * * * *`)
   - **Request method:** GET
   - **Expected status:** 200
3. Save and enable the job.

`/healthz` returns `{"ok": true, ...}` and does not call Claude or Graph — safe to ping.

## Alternatives

- [UptimeRobot](https://uptimerobot.com) — HTTP monitor every 5 min (free tier).
- GitHub Actions `schedule` workflow — works but burns Actions minutes; external cron is simpler.

## Notes

- This only reduces **cold starts**; it does not upgrade Render plan or add redundancy.
- If you later enable real Claude on Render, keep the pinger on `/healthz` only (not `/classify`).
