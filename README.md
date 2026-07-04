# Fantareal PC

Fantareal PC desktop client built with Qt 6, QML, C++, and HuskarUI. This source
tree contains Fantareal application code only. HuskarUI is an external UI
dependency and should be provided as a separate checkout or an installed CMake
package.

This is the active UI direction for the current plan. The older `native\`
Direct2D experiment is retained for reference but is no longer the main UI path.

## Build

Required dependencies:

- Qt 6.7 or newer.
- A C++20 compiler supported by Qt.
- CMake 3.25 or newer.
- HuskarUI, either as a source checkout passed through `HUSKARUI_ROOT` or as an
  installed package discoverable by `find_package(HuskarUI)`.

Example on Windows PowerShell:

```powershell
$env:HUSKARUI_ROOT = "C:\path\to\HuskarUI"
.\tools\Verify-HuskarUI.ps1 -QtPrefix "C:\path\to\Qt\6.7.3\msvc2019_64" -HuskarUIRoot $env:HUSKARUI_ROOT -Build
```

`Verify-HuskarUI.ps1` loads the VS x64 build environment automatically for MSVC
Qt prefixes, uses Visual Studio's bundled CMake/Ninja, configures Release, and
builds `build-verify\FantarealHuskarUI.exe`. The `-Build` path also starts the
app once with the Qt/HuskarUI runtime paths and checks the runtime log for
QML/C++ errors.

## Scope

- `HusWindow` application shell.
- HuskarUI Gallery-style caption bar, rounded translucent hover sidebar,
  dashboard, cards, badges, tags, segmented controls, inputs, buttons, and scroll bars.
- Read-only legacy data scanner through `FantarealBridge`, including critical
  JSON files, asset directories, card/material counts, and plugin manifests.
- JSON summaries for Settings, Routes, Cards, Presets, Worldbook, Chat, and
  Memory. API keys are exposed only as configured/unconfigured status.
- Editable Settings page for the safe `data/settings.json` subset: model
  endpoint/model, generation limits, custom background image path/opacity,
  embedding/rerank connection fields, and memory summary limits, plus the local
  chat demo toggle. Saves use a merge patch so unknown fields remain, blank API
  key inputs preserve existing secrets, and the previous file is backed up under
  `data\backups`. A blank or invalid background path falls back to the built-in
  frosted gradient; valid local paths render as an image layer under the glass
  overlay.
- Chat page is the highest-priority workspace and is now the default launch
  page. It uses a full-width, chat-first layout without a persistent side panel.
  The app shell now uses one global hover sidebar: a 68px compact icon rail by
  default, smoothly expanding into the full navigation when the mouse approaches
  it and collapsing again when the mouse leaves. The page margins are minimized,
  the message surface gets the largest possible area, and the composer actions
  sit in a compact bottom bar instead of a tall tool column. It reads
  `data/conversations.json` into a local message list, can append user messages,
  and now has a first-pass C++/Qt ChatCompletion path that
  posts to an OpenAI-compatible `/v1/chat/completions` endpoint without starting
  the old FastAPI server. Base URLs may be saved as either a root domain or a
  `/v1` path, and display-style model names such as `Grok 4.3` are normalized to
  API IDs such as `grok-4.3` before sending. It prefers `settings.json` model config, falls back to the
  first enabled route provider, preserves existing message objects, creates
  `data\backups\conversations.*.json.bak`, and marks generated replies with
  `source: "huskarui-llm"`. The page also exposes a direct local demo reply
  action and `settings.demo_mode` fallback so the chat workspace is usable before
  a real model endpoint is configured; demo replies are marked with
  `source: "huskarui-demo"`. The chat composer also has a retry action backed by
  `regenerateLastChatReply()`: it finds the last user message, replaces only the
  trailing assistant reply after a successful new generation, preserves earlier
  history, and backs up `conversations.json` before saving. The QML page now uses
  async generation entry points (`startChatMessageWithReply()` and
  `startRegenerateLastChatReply()`) plus `stopChatGeneration()` so long model
  calls do not block the UI and stopped requests do not write partial history.
  Async requests ask for OpenAI-compatible streaming responses and expose
  `chatStreamingPreview`, which the Chat page renders as a temporary assistant
  bubble while tokens arrive; ordinary JSON model responses remain supported.
  ChatCompletion prompt construction now injects a
  first-pass worldbook context from `data/worldbook.json`: enabled
  `constant` entries, keyword entries matched against recent conversation text,
  primary/secondary triggers, `any`/`all`, whole-word matching, `chance: 0`
  exclusion, ordering, and `max_hits`. It also injects a first-pass
  memory context from the current card runtime files: `memories.json`,
  `merged_memories.json`, and `memory_outline.json`, excluding archived memory
  records.
- Planned chat post-processing is documented in
  `docs/output-splitting-subagent-issue.md`: after the main model reply returns,
  a dedicated output-splitting subagent should filter obvious status/system
  panels, preserve the original prose without rewriting it, and return a JSON
  string array where each item maps to one chat bubble. Invalid JSON must fall
  back safely to a single raw-output bubble so normal chat is never blocked.
- Routes page edits the safe global fields in `data/route_forwarding.json`:
  enablement, POST hook, failover, key rotation, retry attempts, and strategy.
  Saves preserve providers, provider keys, legacy key fields, and unknown
  fields, create `data\backups\route_forwarding.*.json.bak`, clamp retry
  attempts to `1-10`, and expose provider keys only as counts/status. Existing
  providers can be added, edited, and deleted through safe metadata drafts
  (`id`, `name`, `base_url`, `model`, `enabled`, `priority`, `weight`): edits
  preserve keys and unknown fields, new providers start without any secret, and
  deletes are backed up first. Provider keys can still be replaced from the
  Routes page without echoing the old secret; blank input preserves the current
  key, while a non-empty replacement writes a single `keys` entry and removes
  that provider's legacy `api_key`.
- Cards page edits the safe `data/current_role_card.json` text subset: name,
  description, personality, scenario, first message, message examples, creator
  notes/comment, tags, and state-journal/workshop/opening switches. Saves
  preserve source/card identity, personas, nested workshop/state data, unknown
  fields, create `data\backups\current_role_card.*.json.bak`, and clamp tags
  to a deduplicated safe list. The page can also sync the current card into
  `data/persona.json`, preserving unknown persona fields while regenerating
  `name`, `greeting`, and `system_prompt`. It also scans local role-card
  candidates under `cards/` and `assets/???/`, exposes safe summaries, and can
  activate a selected JSON card after validating the relative path and backing up
  `data/current_role_card.json`.
- Preset page edits the active `data/preset.json` preset name, enabled flag, and
  known module toggles. Saves preserve other presets, extra prompts, prompt
  groups, unknown fields, and unknown module keys, create
  `data\backups\preset.*.json.bak`, and enforce the old mutex pairs:
  `short_paragraph/long_paragraph` and `second_person/third_person`.
- Memory page exposes the current card runtime `memories.json` as safe editable
  drafts. `saveMemoryEntry(entryIndex, draft)` updates one entry or appends a
  new one with `entryIndex=-1`, backs up existing files to
  `data\backups\memories.*.json.bak`, preserves ids, unknown fields, and other
  entries, normalizes/deduplicates tags, supports active/archived status, and
  rejects empty content or invalid indexes.
- Worldbook page edits the safe `data/worldbook.json` settings subset:
  enablement, debug mode, match defaults, default entry behavior, injection
  defaults, and recursive scan limits. Saves preserve entries, root-level unknown
  fields, settings-level unknown fields, create
  `data\backups\worldbook.*.json.bak`, and clamp/normalize values to the old
  worldbook sanitizer ranges. It now also exposes a first-pass entry editor for
  safe `entries` fields: title, triggers, type, enabled state, matching,
  content, group, chance, order, injection position, prompt layer, and comment.
  Entry saves patch one entry at a time, preserve unknown entry/root/settings
  fields, back up `worldbook.json`, reject empty content, and require triggers
  for `keyword` entries. New entries receive generated ids.
- First-pass pages for Chat, Settings, Routes, Cards, Presets, Memory,
  Worldbook, Workshop, and Plugins.
- No WebView.
- No FastAPI runtime dependency.

## Verification

Completed locally:

```powershell
.\tools\Verify-HuskarUI.ps1
.\tools\Verify-HuskarUI.ps1 -QtPrefix "C:\path\to\Qt\6.7.3\msvc2019_64" -HuskarUIRoot "C:\path\to\HuskarUI" -Build
```

Latest result after the configurable-background pass: required
files exist, QML parser/format syntax check passed, known
HuskarUI API mistake patterns are absent, CMake configure passed, Release build
passed, `FantarealBridgeSettingsSaveTest`, `FantarealBridgeChatSendTest`,
`FantarealBridgeChatGenerateTest`, `FantarealBridgeChatAsyncTest`,
`FantarealBridgeRouteSaveTest`,
`FantarealBridgeCardSaveTest`, `FantarealBridgePersonaSyncTest`,
`FantarealBridgeWorldbookSaveTest`, `FantarealBridgeMemorySaveTest`, and
`FantarealBridgePresetSaveTest`
passed, and the smoke test opened the
`Fantareal PC` main window directly on the Chat,
Settings, Routes, Cards, Memory, Worldbook, and Preset pages.

The Chat page is weighted as the primary product surface: it is the default
startup page, keeps the app sidebar in a compact rail on Chat so hover does not
steal width, renders messages on a full main canvas, and pins the composer as a
bottom overlay instead of shrinking the conversation into a small workbench.

The app background can now be changed from Settings: `background_image_path` is
stored in `data/settings.json`, normalized from local file URLs when needed, and
exposed to QML as `background_image_url`. `background_image_opacity` is clamped
to `0-1`, can be previewed live from the Settings slider, and also reduces the
glass mask and glow layers, making custom images visibly stronger at higher
values.

`FantarealBridgeChatSendTest` also covers the no-network demo reply path:
it appends a user message and a character-aware assistant reply locally while
preserving old conversation metadata.

`FantarealBridgeChatGenerateTest` captures the fake OpenAI-compatible request
payload and verifies that matched worldbook notes and current-card memory notes
are present in the system prompt while disabled/probability-zero/overflow
worldbook notes and archived memories are excluded. The same test also verifies
the retry flow: a second fake model response replaces the last assistant message
without duplicating the last user message or losing existing metadata.

`FantarealBridgeChatAsyncTest` covers non-blocking generation, streaming preview,
and cancellation: the fake model returns OpenAI SSE chunks, the bridge requests
`stream: true`, `chatStreamingPreview` updates before finish and clears after
save, while a stopped request emits a failed finish and leaves
`conversations.json` unchanged.

`FantarealBridgeSettingsSaveTest` also covers the background settings path:
existing settings expose a local image URL, saved file URLs normalize to local
paths, opacity clamps safely, unknown fields remain, and API key preservation
still holds.

`FantarealBridgeWorldbookSaveTest` covers both worldbook settings and entry
editing: settings saves preserve entries and unknown fields, entry saves preserve
entry identity and unknown fields, clamp/normalize editable values, append new
constant entries with generated ids, reject invalid keyword entries, and refresh
`worldbookEntryDrafts`.

`FantarealBridgeMemorySaveTest` covers current-card memory editing and creation:
entry saves preserve identity and unknown fields, back up existing
`memories.json`, normalize tags, write active/archived status, append generated
memory ids and timestamps, reject empty content/invalid indexes, and refresh
`memoryDrafts`.

`FantarealBridgeRouteSaveTest` also covers provider metadata management:
existing provider edits preserve secrets and unknown fields, duplicate ids are
rejected, enabled providers require endpoint/model, new providers are appended
without keys, deletes are backed up, and invalid deletes are rejected.
