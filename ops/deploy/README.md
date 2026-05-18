# Yandex Cloud staging deploy

These YAML files document the **expected** runtime configuration of the
Serverless Containers backing `staging.proshli.ru`. They are reference
material — the actual deploy happens from
`.github/workflows/deploy-staging.yml` via
[`yc-actions/yc-sls-container-deploy@v3`][gha-yc-deploy], which only
needs the image URL, cores, and memory; the env vars and bindings below
are configured once via `yc serverless container update` and then
inherited by every new revision.

Set the following GitHub Actions secrets in `Settings → Secrets and
variables → Actions`:

| Secret | Source |
| --- | --- |
| `YC_SA_JSON_KEY` | `yc-sa-key.json` for the deployer service account |
| `YC_REGISTRY_ID` | `yc container registry list` |
| `YC_DEPLOY_SA_ID` | service account the containers run as |
| `YC_PG_DSN` | managed Postgres DSN (`postgresql+asyncpg://…`) |
| `YC_REDIS_URL` | managed Redis URL (`redis://…`) |
| `YC_S3_KEY` / `YC_S3_SECRET` | object storage credentials |
| `JWT_SECRET` / `BOT_SERVICE_KEY` | app secrets |
| `SENTRY_DSN` / `ANTHROPIC_API_KEY` | app secrets |

Local one-shot bootstrap (before the workflow ever runs):

```bash
yc serverless container create --name proshli-api-staging
yc serverless container create --name proshli-web-staging
yc serverless container create --name proshli-workers-staging
# tgbot can run as a Serverless Container too (long-poll) or on a
# Compute VM with webhook mode — pick once the Sprint 2 bot launch is
# closer.

# Then, per service, set immutable runtime config:
yc serverless container update --name proshli-api-staging \
  --service-account-id "$YC_DEPLOY_SA_ID" \
  --environment DATABASE_URL="$YC_PG_DSN" \
  --environment REDIS_URL="$YC_REDIS_URL" \
  --environment JWT_SECRET="$JWT_SECRET" \
  --environment BOT_SERVICE_KEY="$BOT_SERVICE_KEY" \
  --environment SENTRY_DSN="$SENTRY_DSN_API" \
  --environment ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
```

Domain binding (`staging.proshli.ru`) lives behind a Yandex Cloud API
Gateway routing `/api/*` to the api container and `/*` to the web
container; SSL is managed via the Certificate Manager. See the YC
console for the gateway spec.

[gha-yc-deploy]: https://github.com/yc-actions/yc-sls-container-deploy
