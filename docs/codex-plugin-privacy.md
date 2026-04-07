# AgentContract Codex Plugin Privacy

AgentContract plugins are distributed as local Codex plugin bundles for private or team use.

## Data handling

- Plugin code and skill instructions run in the user's local Codex environment.
- This repository does not operate a hosted backend for plugin execution, analytics, or telemetry collection.
- Some skills can call third-party APIs or local services when the user invokes them and supplies credentials. Examples include Zotero and Mistral OCR.
- Data sent to those external systems is governed by the user's configuration and the third-party provider's privacy policy.

## Credentials

- API keys and local credentials are managed by the user in their own environment.
- Users are responsible for deciding which secrets to configure and which prompts or files to share with external services.

## Contact

Repository: https://github.com/FuZhiyu/AgentContract
