# PulseMCP Submission Packet

Use this page like a filled-out shipping envelope for the `PulseMCP` lane.

## Strongest Repo-Owned Inputs

- `config/public/mcp-directory-profile.json`
- `starter-packs/mcp-registry/sourceharbor-server.template.json`
- `pyproject.toml`
- `docs/mcp-quickstart.md`
- `docs/media-kit.md`
- `docs/assets/sourceharbor-social-preview.png`
- `docs/assets/sourceharbor-square-icon.png`
- `docs/assets/sourceharbor-mcp-directory-shot-01.png`

## Suggested Field Mapping

| PulseMCP field shape | SourceHarbor repo-owned source |
| --- | --- |
| server name / slug | `config/public/mcp-directory-profile.json -> name` |
| title | `config/public/mcp-directory-profile.json -> title` |
| short description | `config/public/mcp-directory-profile.json -> short_description` |
| long description | `config/public/mcp-directory-profile.json -> long_description` |
| repository / docs / homepage | `config/public/mcp-directory-profile.json` |
| install / command / transport | `config/public/mcp-directory-profile.json -> entrypoint`, `starter-packs/mcp-registry/sourceharbor-server.template.json` |
| environment variables | `config/public/mcp-directory-profile.json -> environment_variables` |
| preview image | `docs/assets/sourceharbor-social-preview.png` |
| square icon | `docs/assets/sourceharbor-square-icon.png` |
| screenshot | `docs/assets/sourceharbor-mcp-directory-shot-01.png` |

## Receipt To Capture

After submission, write back one of these:

1. submission receipt URL
2. pending-review URL
3. live listing URL
4. exact rejection or blocker reason
