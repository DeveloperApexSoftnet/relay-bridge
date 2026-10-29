# Relay Bridge: one-click ERPNext WhatsApp sending

This directory is the standalone Frappe app root (`pyproject.toml` plus `relay_bridge/`). Publish this directory as a separate Git repository for Frappe Cloud custom-app installation. Do not point Frappe Cloud at the Node/React monorepo root. A private bench/custom-app-capable host is required.

Relay's Node API, worker, PostgreSQL, Redis and managed WhatsApp browser run as a separate service. Installing this app does not host those services inside Frappe.

## Administrator setup for each ERPNext site

1. Deploy Relay behind HTTPS and add this site's public HTTPS hostname to its ERP allowlist.
2. In Relay create a separate ERP connection with this site's integration-user credentials. Use a separate random signing secret (32+ characters) per connection.
3. Pair a WhatsApp QR transport. In the ERP connection, select the default direct-send transport and a saved template for every enabled DocType. Select PDF + caption or text-only; choose each Print Format. Enable one-click sending and save. Only Relay administrators can change these defaults. Updating/creating a template version does not automatically replace the selected template ID.
4. Install/update `relay_bridge` on this ERPNext site and run site migration/assets build using the hosting provider's deployment process.
5. As System Manager open `/app/relay-settings`. Enable Relay and enter the Relay HTTPS URL, this site's ERP connection UUID from the portal, and the matching signing secret. Save and click **Test Relay configuration**. The secret uses Frappe's Password field and never goes into a Client Script.
6. Remove/disable the old handoff Client Scripts for Quotation, Lead and Sales Invoice. The app supplies a shared Send WhatsApp button. Optional replacement Client Scripts from the main project require this app and have the same duplicate-registration guard.
7. Test one saved document of each enabled type with an intended test recipient. No public-URL action, Relay login, preview selection or queue click is needed for employees.

ERPNext's public URL must match the Relay ERP connection URL. A mismatch returns ERP_SOURCE_SITE_MISMATCH. Keep Frappe's configured public hostname/scheme correct behind proxies. Defaults are per connection; do not reuse one connection for unrelated sites. The same document name on two sites remains two separate events.

## Employee flow

Save a Quotation, Lead or Sales Invoice and click **Send WhatsApp**. The server checks read/write permission, rejects cancelled/unsupported documents and submits a signed identity-only request. Relay selects administrator defaults, fetches ERP data and sends using the background worker. ERPNext displays queued/progress/result status without opening Relay. It does not report queue acceptance as successful transmission. The employee can poll only notifications they initiated and must retain document read permission.

Repeating the same document/trigger returns the existing notification rather than resending. Changing admin defaults does not resend historical records. Failed/ambiguous sends require administrator review/revalidation; the button does not silently retry them. A session requiring a QR scan still needs administrator intervention.

Automatic save/submit hooks remain off unless both `relay_triggers` in site configuration and Relay's matching event toggles are enabled. They are separate from button-triggered sending. Existing site-config keys `relay_url`, `relay_connection_id`, `relay_signing_secret` remain a legacy fallback only while Relay Settings is entirely unconfigured. Explicitly disabling configured Relay Settings blocks new requests.

## Deployment

On Frappe Cloud, add this repository to the private bench group, deploy it, then install the app on the site. For a self-managed bench:

```bash
bench get-app https://github.com/OWNER/relay-bridge.git
bench --site YOUR_SITE install-app relay_bridge
bench --site YOUR_SITE migrate
bench build --app relay_bridge
```

Use your hosting provider's restart/update process. Back up the site and its encryption key; Password values depend on Frappe's encryption key. Never commit live secrets or site_config.json.

The code is covered by offline Frappe contract tests and Relay HTTP/database tests. Installation in a real Frappe Cloud bench and live one-click WhatsApp sending must still be validated in staging before production use.
