# ANMA Cloud inside Home Assistant

1. Copy `anma_cloud/settings.py` and `anma_cloud/embed_security.py` into the corresponding folder of your current project. Back up `settings.py` before replacing it; merge if it has newer modifications.
2. Add to server `.env` (substitute your own HA origin):

   ANMA_FRAME_ANCESTORS=http://100.114.0.63:8123

   For multiple installations use a comma-separated list of **trusted** origins. Use origins, not `/cloud-anma/0` paths.
3. Rebuild/restart the application: `docker compose up -d --build`.
4. Check: `curl -I https://cloud.anma-electric.com.ua/`. Expected: `Content-Security-Policy: frame-ancestors 'self' http://100.114.0.63:8123` and NO `X-Frame-Options: DENY`.
5. If X-Frame-Options is still present, check the external Nginx and intermediary proxies for a separately added header.

Notes:
- This patch does not grant users authorization. It only permits browsers to frame your site from listed origins.
- Google OAuth sign-in and session cookies may be blocked in a third-party iframe. Test sign-in directly on the top-level site first. Cookies requiring cross-site use often need `SameSite=None; Secure`, but some browsers still block them. Consider a same-origin reverse proxy or a dedicated embedding flow if this is a general public product.
- Every customer's arbitrary Home Assistant URL cannot be securely whitelisted in a **static** frame-ancestors policy. Consider a dedicated embed domain / authenticated embedding strategy rather than `frame-ancestors *`.
- Do not commit `.env` or secrets.
