# Documentation and brand assets

`logo.svg`, `icon.svg` and `icon.png` are the Workbench brand assets. The installed package includes these fixed resources for CLI/MCP charts; documentation screenshots are not runtime resources.

## Grok real-data examples

The README uses two assets captured from the actual Grok Bot Health Buddy chat
on November 5, 2026, over the owner's existing Garmin archive. These contain
real dated sleep measurements, not generated fixtures. The question was prompted
for this README; the native answer was captured as returned, not reconstructed.

- `grok-sleep-conversation.png` is a pixel-exact rectangular crop of the native
  app screenshot. It retains the full question and opening answer. Account and
  sidebar content, the horizontally clipped follow-up table, and unrelated
  conversation content are outside the crop. No text, number or UI element was
  replaced, stitched or regenerated.
- `grok-sleep-week.png` is the original downloaded `wide` sleep chart attachment,
  unchanged. It covers October 30–November 5, 2026, with seven available nights.
  Dates, units, coverage, source fetch times and Garmin-estimate notes remain visible.

Grok reported using `garmin-archive sleep`, `status` and `chart sleep` from an
installed 0.1.0 package built at source revision
`501b40a8632b4c83840f0bef0cfca14de4784dc1`. This is an earlier checkout, not the
first tagged release revision `5c305182bb80fcab9accd1dcbed3848b88efc718`.
The chat and attachment were directly observed; remote command/version/import
claims were not independently audited. The supporting comparison table was
formatted by the assistant. This example does not establish MCP connectivity,
new live collection, medical conclusions or recurring execution.

The owner approved these exact two images for the public README on November 5,
2026. This permission covers the selected images only. Raw app
captures and the rest of the conversation remain private outside the repository.
Credentials, archive files, account details and private paths are not included.

SHA-256 `grok-sleep-conversation.png`: `d18aaf435ba3899914cbc8ee04754aec8f41ea776999ce451b730cfd8ee07cb5`.

SHA-256 `grok-sleep-week.png`: `f8cb3d42c60ee32350f1a6f5a7a2a0bab82cd3d552d06ea4c616313b12fb89f5`.

## Muse sleep demonstration

`muse-sleep-demo.png` is a reviewed privacy crop of an actual Muse app screenshot captured November 4, 2026. Its question, answer and chart thumbnail are unchanged. No dialogue, number or UI element was replaced. It uses generated corpus v2, seed 42, with April 24–30, 2026 dates and simulated collection timestamps; no personal health records are shown.

The app interaction and visible attachment were directly observed. The agent reported CLI use on an Ubuntu workstation and source revision `47dcd68`; remote execution details were not independently audited. This screenshot does not establish live Garmin collection, MCP support, persistence or recurring execution. Muse is a separate assistant application, not a UI shipped by this repository.

SHA-256: `53d9f77e788383d47d68e6cbab490c79a6537f252cd063954af9bf61c523928c`.

## Sleep chart preview

`sleep-example.png` is a direct Workbench export from the same default generated corpus and dates, using the `wide` layout. It is not an assistant screenshot. See [reproduction instructions](../docs/VISUALIZATION.md#keep-images-concise). Charts remain illustrative wearable estimates; the generated scores and stages do not establish physiological relationships.
