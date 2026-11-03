# helper
Nothing to say...


## Secret configuration

Set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_INVOICE_TOKEN`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_SHOP_ID` in the process environment before starting. Each is required; missing or blank values stop startup without printing credentials. `.env.example` lists the names only. The application does not automatically load `.env`; export the variables in your shell or configure your service/container environment. Never commit real values.

Credentials previously committed to this repository must be revoked or rotated in the relevant provider or deployment. Removing them from current source does not remove Git history; assess historical exposure separately. No live credentials are needed for the offline configuration tests:

```sh
python -m unittest discover -s tests -v
```

Start from `helper/` (or run `python helper/main.py`) after setting the environment. `TELEGRAM_INVOICE_TOKEN` is the Telegram payment-provider token; YooKassa API access requires its own secret and shop ID. `/pay` rejects usernames shorter than four characters after trimming before calling the provider. Payment tests mock both provider and database; no financial operations are performed.

The webhook path uses a one-way digest instead of the Telegram API token, preventing ordinary URL access logs from revealing the bot credential. Startup updates the registered webhook URL when it changes; retain normal HTTPS and restrict access to webhook logs.
