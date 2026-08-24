# Security and configuration notes

This web prototype has no client-side need for Google Drive credentials, OAuth refresh tokens, or model-provider secrets. The browser receives only rendered image URLs and retrieval fields returned by the FastAPI service.

## Safe configuration boundary

| Category | Correct location | Never place in |
|---|---|---|
| Retrieval model identifier and non-secret flags | Server environment or local shell | Browser bundle |
| Google Drive OAuth client configuration | Server-side secret store, only for offline ingestion | Frontend, repository history, API response |
| OAuth refresh/access tokens | Server-side secret store, scoped per ingestion user | Source tree, logs, browser local storage |
| Retrieval assets | Versioned artifact bundle and managed image storage | Browser source code |

## Rotation/removal procedure

If the original repository’s tracked credential files are real and active, the owner should revoke/rotate them in the relevant provider console immediately, issue fresh credentials only to an approved secret store, update the active branch through a reviewed change, and remove old files from repository history using the organization’s approved incident-response process. Do not print the values while investigating.

## Optional retained-query feature

The first prototype does not retain uploaded query images or generate persistent reports. If that feature is enabled later, store encrypted uploads in managed object storage, persist only minimal metadata and a storage key in a database, apply access controls and retention periods, and never use the application container filesystem as durable storage.
