#include "card_authoring/cardauthoringservice.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTemporaryDir>

#include <iostream>

namespace {
bool fail(const QString& message) {
    std::cerr << message.toStdString() << '\n';
    return false;
}

bool writeJsonDocument(const QString& path, const QJsonDocument& document) {
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return false;
    }
    return file.write(document.toJson(QJsonDocument::Indented)) > 0;
}

bool writeJson(const QString& path, const QJsonObject& object) {
    return writeJsonDocument(path, QJsonDocument(object));
}

QJsonObject readJson(const QString& path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QJsonDocument::fromJson(file.readAll()).object();
}

QJsonArray readJsonArray(const QString& path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QJsonDocument::fromJson(file.readAll()).array();
}

QJsonObject jsonObjectFromLiteral(const char* json) {
    return QJsonDocument::fromJson(QByteArray(json)).object();
}

QJsonDocument jsonDocumentFromLiteral(const char* json) {
    return QJsonDocument::fromJson(QByteArray(json));
}

QByteArray readBytes(const QString& path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return file.readAll();
}

QJsonObject findById(const QJsonArray& items, const QString& id) {
    for (const QJsonValue& value : items) {
        const QJsonObject item = value.toObject();
        if (item.value(QStringLiteral("id")).toString() == id) {
            return item;
        }
    }
    return {};
}

QJsonObject findByKey(const QJsonArray& items, const QString& keyField, const QString& key) {
    for (const QJsonValue& value : items) {
        const QJsonObject item = value.toObject();
        if (item.value(keyField).toString() == key) {
            return item;
        }
    }
    return {};
}

bool jsonArrayContainsFilename(const QJsonArray& items, const QString& filename) {
    for (const QJsonValue& value : items) {
        if (value.toObject().value(QStringLiteral("filename")).toString() == filename) {
            return true;
        }
    }
    return false;
}

bool jsonArrayContainsGroup(const QJsonArray& items, const QString& groupId) {
    for (const QJsonValue& value : items) {
        if (value.toObject().value(QStringLiteral("group_id")).toString() == groupId) {
            return true;
        }
    }
    return false;
}

QJsonObject findGroupById(const QJsonArray& items, const QString& groupId) {
    for (const QJsonValue& value : items) {
        const QJsonObject item = value.toObject();
        if (item.value(QStringLiteral("group_id")).toString() == groupId) {
            return item;
        }
    }
    return {};
}

bool jsonArrayContainsString(const QJsonArray& items, const QString& expected) {
    for (const QJsonValue& value : items) {
        if (value.toString() == expected) {
            return true;
        }
    }
    return false;
}

bool worldbookContainsExternalTag(const QJsonArray& entries, const QString& trigger) {
    for (const QJsonValue& value : entries) {
        const QJsonObject entry = value.toObject();
        if (entry.value(QStringLiteral("entry_type")).toString() == QStringLiteral("external_tag")
            && entry.value(QStringLiteral("trigger")).toString() == trigger) {
            return true;
        }
    }
    return false;
}

QJsonObject manualFullSample() {
    return jsonObjectFromLiteral(R"JSON({
  "type": "fantareal_card_authoring_project",
  "version": 1,
  "title": "Manual Acceptance Full Project",
  "persona_card": {
    "name": "Manual Acceptance Role",
    "description": "A role used to verify the migrated card authoring workflow.",
    "personality": "Careful, observant, and direct.",
    "scenario": "The user is validating project import, editing, preview, apply, and export.",
    "first_mes": "Ready for the migration acceptance run.",
    "mes_example": "User: Start the check.\nRole: I will keep each module visible and easy to verify.",
    "creator_notes": "Manual acceptance fixture for the PC card authoring migration.",
    "tags": ["manual", "migration", "database"],
    "personas": {
      "2": {
        "name": "Manual Side Persona",
        "description": "A secondary persona used to verify multi persona editing.",
        "personality": "Quieter and more analytical.",
        "scenario": "Appears when the author switches persona variants.",
        "creator_notes": "Side persona acceptance note.",
        "tags": ["side", "manual"]
      }
    },
    "creativeWorkshop": {
      "enabled": true,
      "items": [
        {
          "id": "workshop-popup",
          "name": "Trust Popup",
          "enabled": true,
          "triggerMode": "stage",
          "triggerStage": "trust",
          "actionType": "popup",
          "popupTitle": "Trust stage reached",
          "volume": 0.6,
          "note": "Manual acceptance workshop note."
        }
      ]
    }
  },
  "database": {
    "enabled": true,
    "notes": "Database draft used by the manual acceptance sample.",
    "variables": [
      {
        "id": "var_trust",
        "key": "trust",
        "label": "Trust",
        "value_type": "number",
        "initial_value": "0",
        "scope": "role-main",
        "write_policy": "bounded_delta",
        "description": "Relationship trust score."
      }
    ],
    "stages": [
      {
        "id": "stage_trust",
        "role_id": "role-main",
        "stage_key": "trust",
        "title": "Trust Snapshot",
        "condition": "trust >= 5",
        "active_tag": "database.stage.role-main.trust",
        "emits_tags": ["database.stage.role-main.trust", "database.tag.trust-lore"],
        "description": "Visible when trust reaches the threshold."
      }
    ],
    "tags": [
      {
        "id": "tag_trust_lore",
        "tag": "database.tag.trust-lore",
        "title": "Trust Lore Tag",
        "trigger": "trust lore",
        "target": "worldbook",
        "description": "Worldbook consumer tag generated from the database draft."
      }
    ]
  },
  "worldbook": {
    "entries": [
      {
        "id": "wb_trust_lore",
        "title": "Trust Lore",
        "trigger": "trust lore",
        "secondary_trigger": "role-main",
        "entry_type": "keyword",
        "content": "The role remembers how trust changes the conversation.",
        "group": "manual",
        "comment": "Worldbook acceptance note.",
        "enabled": true,
        "order": 0
      }
    ],
    "settings": {}
  },
  "preset": {
    "active_preset_id": "manual-preset",
    "presets": [
      {
        "id": "manual-preset",
        "name": "Manual Preset",
        "content": "Keep this prompt body unchanged during manual apply.",
        "base_system_prompt": "Keep this base prompt unchanged during preset apply.",
        "enabled": true,
        "modules": { "short_paragraph": true, "long_paragraph": false },
        "extra_prompts": [
          {
            "id": "extra_style",
            "name": "Style Reminder",
            "content": "Write in compact paragraphs.",
            "enabled": true
          }
        ],
        "prompt_groups": [
          {
            "id": "group_database",
            "name": "Database Context",
            "content": "Use database tags when available.",
            "enabled": true
          }
        ]
      }
    ]
  },
  "memory": {
    "items": [
      {
        "id": "memory-first",
        "title": "First Memory",
        "content": "Manual acceptance memory item.",
        "tags": ["manual"],
        "notes": "Memory acceptance note.",
        "memory_status": "active"
      }
    ]
  }
})JSON");
}

QJsonObject legacyStateJournalSample() {
    return jsonObjectFromLiteral(R"JSON({
  "name": "Legacy StateJournal Role",
  "description": "Legacy role card import sample.",
  "personality": "Keeps old stateJournal fields visible for migration checks.",
  "scenario": "Imported as a legacy role card JSON.",
  "first_mes": "This card came from the legacy stateJournal path.",
  "mes_example": "User: Import legacy card.\nRole: I should become a database draft.",
  "creator_notes": "Use this file to verify state_journal.stage.* is normalized to database.stage.*.",
  "tags": ["legacy", "statejournal"],
  "stateJournal": {
    "enabled": true,
    "version": 1,
    "roles": [
      {
        "id": "role-main",
        "role_id": "role-main",
        "role_name": "Legacy Main Role",
        "mode": "full",
        "stateJournalMode": "full",
        "variables": [
          {
            "var_key": "trust",
            "var_name": "Trust",
            "default_value": 1,
            "instruction": "Track trust from the legacy stateJournal sample."
          }
        ],
        "stages": [
          {
            "stage_key": "trust",
            "stage_name": "Legacy Trust Snapshot",
            "conditions": [
              { "var": "trust", "op": ">=", "value": 5 }
            ],
            "activation_tag": "state_journal.stage.role-main.trust",
            "emits_tags": ["state_journal.stage.role-main.trust"]
          }
        ]
      }
    ]
  }
})JSON");
}

QJsonObject manualCandidateReviewSample() {
    return jsonObjectFromLiteral(R"JSON({
  "summary": "Manual acceptance candidate review.",
  "plan": {
    "intent_type": "revise",
    "quality_goal": "Exercise persona, database, worldbook, preset, and memory candidates.",
    "package_mode": "runtime_package",
    "required_containers": ["persona", "database", "worldbook", "preset", "memory"]
  },
  "candidate_groups": [
    {
      "group_id": "manual_acceptance",
      "group_title": "Manual Acceptance",
      "reason": "Provides deterministic candidates for UI acceptance.",
      "draft_only": true
    }
  ],
  "candidates": [
    {
      "id": "manual-personality",
      "module": "persona",
      "action": "json_patch",
      "target": { "path": "persona_card.personality", "operation": "set" },
      "after": "Careful, observant, direct, and migration-aware.",
      "group_id": "manual_acceptance",
      "group_title": "Manual Acceptance"
    },
    {
      "id": "manual-stage",
      "module": "database",
      "action": "json_patch",
      "target": { "path": "database.stages", "operation": "append" },
      "after": {
        "role_id": "role-main",
        "stage_key": "warmth",
        "title": "Warmth Snapshot",
        "condition": "trust >= 8",
        "active_tag": "database.stage.role-main.warmth",
        "description": "Candidate-added database snapshot."
      },
      "group_id": "manual_acceptance",
      "group_title": "Manual Acceptance",
      "draft_only": true
    },
    {
      "id": "manual-memory",
      "module": "memory",
      "action": "append_array_item",
      "after": {
        "id": "memory-candidate",
        "title": "Candidate Memory",
        "content": "Candidate-added memory item.",
        "tags": "candidate,manual"
      },
      "group_id": "manual_acceptance",
      "group_title": "Manual Acceptance"
    }
  ]
})JSON");
}

QJsonDocument manualCandidateArraySample() {
    return jsonDocumentFromLiteral(R"JSON([
  {
    "id": "array-worldbook",
    "module": "worldbook",
    "action": "append_array_item",
    "after": {
      "id": "wb-array-candidate",
      "title": "Array Candidate Lore",
      "trigger": "array candidate lore",
      "content": "This entry verifies bare JSON array candidate normalization."
    }
  },
  {
    "id": "array-preset",
    "module": "preset",
    "action": "append_array_item",
    "after": {
      "id": "preset-array-candidate",
      "name": "Array Candidate Preset",
      "modules": { "short_paragraph": true },
      "extra_prompts": [
        {
          "id": "extra-array",
          "name": "Array Extra",
          "content": "Bare array candidate extra prompt."
        }
      ]
    }
  }
])JSON");
}

bool verifyManualSamples() {
    QTemporaryDir sampleTempDir;
    if (!sampleTempDir.isValid()) {
        return fail(QStringLiteral("failed to create manual sample temporary directory"));
    }

    CardAuthoringService service(sampleTempDir.path());

    const QJsonObject fullSample = manualFullSample();
    const QJsonObject normalizedFull = service.normalizeProject(fullSample);
    const QJsonObject fullPersona = normalizedFull.value(QStringLiteral("persona_card")).toObject();
    const QJsonObject fullDatabase = normalizedFull.value(QStringLiteral("database")).toObject();
    if (normalizedFull.value(QStringLiteral("type")).toString() != QStringLiteral("fantareal_card_authoring_project")
        || fullPersona.value(QStringLiteral("name")).toString() != QStringLiteral("Manual Acceptance Role")
        || fullPersona.value(QStringLiteral("personas")).toObject().value(QStringLiteral("2")).toObject().value(QStringLiteral("name")).toString() != QStringLiteral("Manual Side Persona")
        || fullPersona.value(QStringLiteral("creativeWorkshop")).toObject().value(QStringLiteral("items")).toArray().isEmpty()
        || fullDatabase.value(QStringLiteral("variables")).toArray().isEmpty()
        || fullDatabase.value(QStringLiteral("stages")).toArray().isEmpty()
        || fullDatabase.value(QStringLiteral("tags")).toArray().isEmpty()
        || normalizedFull.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray().isEmpty()
        || normalizedFull.value(QStringLiteral("preset")).toObject().value(QStringLiteral("presets")).toArray().isEmpty()
        || normalizedFull.value(QStringLiteral("memory")).toObject().value(QStringLiteral("items")).toArray().isEmpty()) {
        return fail(QStringLiteral("manual full cardwork sample should normalize into every migrated module"));
    }

    const QJsonObject compiledFull = service.compileRoleCard(normalizedFull);
    const QJsonObject compiledRaw = compiledFull.value(QStringLiteral("raw")).toObject();
    if (compiledRaw.value(QStringLiteral("name")).toString() != QStringLiteral("Manual Acceptance Role")
        || compiledRaw.value(QStringLiteral("creativeWorkshop")).toObject().value(QStringLiteral("items")).toArray().isEmpty()
        || compiledRaw.value(QStringLiteral("stateJournal")).toObject().value(QStringLiteral("databaseDraft")).toObject().value(QStringLiteral("stages")).toArray().isEmpty()) {
        return fail(QStringLiteral("manual full cardwork sample should compile into role card raw and compatible stateJournal draft"));
    }

    QString errorMessage;
    QString importedPath;
    const QString legacySamplePath = QDir(sampleTempDir.path()).absoluteFilePath(QStringLiteral("legacy-statejournal-role.json"));
    if (!writeJson(legacySamplePath, legacyStateJournalSample())) {
        return fail(QStringLiteral("failed to write inline legacy stateJournal sample"));
    }
    const QJsonObject importedLegacy = service.importProjectFile(legacySamplePath, &importedPath, &errorMessage);
    const QJsonObject importedLegacyDatabase = importedLegacy.value(QStringLiteral("database")).toObject();
    const QJsonObject importedLegacyStage = importedLegacyDatabase.value(QStringLiteral("stages")).toArray().first().toObject();
    if (importedLegacy.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("name")).toString() != QStringLiteral("Legacy StateJournal Role")
        || importedPath.isEmpty()
        || importedLegacyDatabase.value(QStringLiteral("variables")).toArray().isEmpty()
        || importedLegacyStage.value(QStringLiteral("active_tag")).toString() != QStringLiteral("database.stage.role-main.trust")
        || importedLegacyDatabase.value(QStringLiteral("tags")).toArray().first().toObject().value(QStringLiteral("tag")).toString() != QStringLiteral("database.stage.role-main.trust")) {
        return fail(QStringLiteral("manual legacy stateJournal sample should import into database draft with normalized stage tags: %1").arg(errorMessage));
    }

    const QJsonObject reviewSample = manualCandidateReviewSample();
    const QJsonObject normalizedReview = service.normalizeCandidateReview(normalizedFull, reviewSample);
    const QJsonObject appliedReview = service.applyCandidateReview(normalizedFull, reviewSample);
    const QJsonObject reviewProject = appliedReview.value(QStringLiteral("project")).toObject();
    if (!normalizedReview.value(QStringLiteral("ok")).toBool()
        || normalizedReview.value(QStringLiteral("candidates")).toArray().size() < 3
        || !appliedReview.value(QStringLiteral("ok")).toBool()
        || appliedReview.value(QStringLiteral("summary")).toObject().value(QStringLiteral("applied_count")).toInt() < 3
        || reviewProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("personality")).toString() != QStringLiteral("Careful, observant, direct, and migration-aware.")
        || reviewProject.value(QStringLiteral("database")).toObject().value(QStringLiteral("stages")).toArray().size() < 2
        || !worldbookContainsExternalTag(
            reviewProject.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray(),
            QStringLiteral("database.stage.role-main.warmth"))) {
        return fail(QStringLiteral("manual candidate review sample should normalize and apply selected candidates to the draft"));
    }

    const QJsonDocument arrayDocument = manualCandidateArraySample();
    const QJsonObject wrappedArrayReview{
        { QStringLiteral("summary"), QStringLiteral("manual bare array wrapper") },
        { QStringLiteral("candidates"), arrayDocument.array() },
    };
    const QJsonObject normalizedArrayReview = service.normalizeCandidateReview(normalizedFull, wrappedArrayReview);
    if (!arrayDocument.isArray()
        || !normalizedArrayReview.value(QStringLiteral("ok")).toBool()
        || normalizedArrayReview.value(QStringLiteral("candidates")).toArray().size() < 2) {
        return fail(QStringLiteral("manual bare array candidate sample should normalize when wrapped by the bridge-style object"));
    }

    return true;
}
}

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);

    if (!verifyManualSamples()) {
        return 1;
    }

    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        return fail(QStringLiteral("failed to create temporary directory")) ? 0 : 1;
    }

    QDir root(tempDir.path());
    if (!root.mkpath(QStringLiteral("data"))
        || !root.mkpath(QStringLiteral("data/card_runtime/cards/card-123"))) {
        return fail(QStringLiteral("failed to create data directory")) ? 0 : 1;
    }

    QJsonObject currentRaw;
    currentRaw.insert(QStringLiteral("name"), QStringLiteral("Old Name"));
    currentRaw.insert(QStringLiteral("description"), QStringLiteral("old description"));
    currentRaw.insert(QStringLiteral("stateJournal"), QJsonObject{
        { QStringLiteral("enabled"), false },
        { QStringLiteral("unknown_state_field"), QStringLiteral("state-stays") },
        { QStringLiteral("roles"), QJsonArray{
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("role-1") },
                { QStringLiteral("role_id"), QStringLiteral("role-1") },
                { QStringLiteral("role_name"), QStringLiteral("Existing Role") },
                { QStringLiteral("unknown_role_field"), QStringLiteral("role-stays") },
                { QStringLiteral("initial_stage"), QStringLiteral("stage_a") },
                { QStringLiteral("variables"), QJsonArray{
                    QJsonObject{
                        { QStringLiteral("var_key"), QStringLiteral("legacy") },
                        { QStringLiteral("unknown_variable_field"), QStringLiteral("variable-stays") },
                    },
                } },
                { QStringLiteral("stages"), QJsonArray{
                    QJsonObject{
                        { QStringLiteral("stage_key"), QStringLiteral("legacy_stage") },
                        { QStringLiteral("unknown_stage_field"), QStringLiteral("stage-stays") },
                    },
                } },
            },
        } },
    });
    QJsonObject currentCard;
    currentCard.insert(QStringLiteral("source_name"), QStringLiteral("current-card.json"));
    currentCard.insert(QStringLiteral("card_uid"), QStringLiteral("card-123"));
    currentCard.insert(QStringLiteral("raw"), currentRaw);
    const QString currentCardPath = root.absoluteFilePath(QStringLiteral("data/current_role_card.json"));
    if (!writeJson(currentCardPath, currentCard)) {
        return fail(QStringLiteral("failed to write current_role_card.json fixture")) ? 0 : 1;
    }
    const QString worldbookPath = root.absoluteFilePath(QStringLiteral("data/worldbook.json"));
    if (!writeJson(worldbookPath, QJsonObject{
            { QStringLiteral("settings"), QJsonObject{ { QStringLiteral("enabled"), true }, { QStringLiteral("max_hits"), 3 } } },
            { QStringLiteral("entries"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("wb-existing") },
                    { QStringLiteral("title"), QStringLiteral("Old Lore") },
                    { QStringLiteral("trigger"), QStringLiteral("old lore") },
                    { QStringLiteral("content"), QStringLiteral("old content") },
                    { QStringLiteral("unknown_worldbook_field"), QStringLiteral("entry-stays") },
                },
            } },
            { QStringLiteral("unknown_root_field"), QStringLiteral("worldbook-root-stays") },
        })) {
        return fail(QStringLiteral("failed to write worldbook fixture")) ? 0 : 1;
    }
    const QString presetPath = root.absoluteFilePath(QStringLiteral("data/preset.json"));
    if (!writeJson(presetPath, QJsonObject{
            { QStringLiteral("active_preset_id"), QStringLiteral("base") },
            { QStringLiteral("presets"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("base") },
                    { QStringLiteral("name"), QStringLiteral("Base") },
                    { QStringLiteral("enabled"), true },
                    { QStringLiteral("base_system_prompt"), QStringLiteral("KEEP BASE PROMPT") },
                    { QStringLiteral("modules"), QJsonObject{ { QStringLiteral("long_paragraph"), true } } },
                    { QStringLiteral("extra_prompts"), QJsonArray{
                        QJsonObject{
                            { QStringLiteral("id"), QStringLiteral("extra-existing") },
                            { QStringLiteral("name"), QStringLiteral("Existing") },
                            { QStringLiteral("content"), QStringLiteral("existing prompt") },
                            { QStringLiteral("enabled"), true },
                        },
                    } },
                    { QStringLiteral("prompt_groups"), QJsonArray{} },
                    { QStringLiteral("unknown_preset_field"), QStringLiteral("preset-stays") },
                },
            } },
        })) {
        return fail(QStringLiteral("failed to write preset fixture")) ? 0 : 1;
    }
    const QString memoryPath = root.absoluteFilePath(QStringLiteral("data/card_runtime/cards/card-123/memories.json"));
    const QString mergedMemoryPath = root.absoluteFilePath(QStringLiteral("data/card_runtime/cards/card-123/merged_memories.json"));
    const QString memoryOutlinePath = root.absoluteFilePath(QStringLiteral("data/card_runtime/cards/card-123/memory_outline.json"));
    if (!writeJsonDocument(memoryPath, QJsonDocument(QJsonArray{
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("memory-existing") },
                { QStringLiteral("title"), QStringLiteral("Old Memory") },
                { QStringLiteral("content"), QStringLiteral("old memory content") },
                { QStringLiteral("memory_status"), QStringLiteral("active") },
            },
        }))
        || !writeJsonDocument(mergedMemoryPath, QJsonDocument(QJsonArray{ QJsonObject{ { QStringLiteral("id"), QStringLiteral("merged-stays") } } }))
        || !writeJsonDocument(memoryOutlinePath, QJsonDocument(QJsonArray{ QJsonObject{ { QStringLiteral("id"), QStringLiteral("outline-stays") } } }))) {
        return fail(QStringLiteral("failed to write memory fixtures")) ? 0 : 1;
    }

    CardAuthoringService service(tempDir.path());
    QJsonObject project = service.createEmptyProject();
    const QJsonObject emptyProjectPersonas = project.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("personas")).toObject();
    if (!emptyProjectPersonas.contains(QStringLiteral("1"))
        || !emptyProjectPersonas.contains(QStringLiteral("2"))
        || !emptyProjectPersonas.contains(QStringLiteral("3"))) {
        return fail(QStringLiteral("empty card authoring project should seed multi-role slots 1/2/3")) ? 0 : 1;
    }
    project.insert(QStringLiteral("title"), QStringLiteral("Authoring Hero"));
    project.insert(QStringLiteral("persona_card"), QJsonObject{
        { QStringLiteral("name"), QStringLiteral("New Name") },
        { QStringLiteral("description"), QStringLiteral("new description") },
        { QStringLiteral("personality"), QStringLiteral("new personality") },
        { QStringLiteral("scenario"), QStringLiteral("new scenario") },
        { QStringLiteral("first_mes"), QStringLiteral("new first") },
        { QStringLiteral("mes_example"), QStringLiteral("new example dialogue") },
        { QStringLiteral("creator_notes"), QStringLiteral("new hidden rules") },
        { QStringLiteral("tags"), QJsonArray{ QStringLiteral("alpha"), QStringLiteral("beta") } },
        { QStringLiteral("creativeWorkshop"), QJsonObject{
            { QStringLiteral("enabled"), true },
            { QStringLiteral("items"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("workshop-main") },
                    { QStringLiteral("name"), QStringLiteral("Main Workshop") },
                    { QStringLiteral("actionType"), QStringLiteral("note") },
                    { QStringLiteral("note"), QStringLiteral("main workshop note") },
                    { QStringLiteral("volume"), 0.5 },
                },
            } },
        } },
        { QStringLiteral("personas"), QJsonObject{
            { QStringLiteral("2"), QJsonObject{
                { QStringLiteral("name"), QStringLiteral("Second Role") },
                { QStringLiteral("description"), QStringLiteral("second old description") },
                { QStringLiteral("personality"), QStringLiteral("second personality") },
                { QStringLiteral("scenario"), QStringLiteral("second scenario") },
                { QStringLiteral("creator_notes"), QStringLiteral("second notes") },
                { QStringLiteral("tags"), QJsonArray{ QStringLiteral("side") } },
            } },
        } },
    });
    project.insert(QStringLiteral("database"), QJsonObject{
        { QStringLiteral("enabled"), true },
        { QStringLiteral("variables"), QJsonArray{
            QJsonObject{
                { QStringLiteral("key"), QStringLiteral("affection") },
                { QStringLiteral("label"), QStringLiteral("Affection") },
                { QStringLiteral("scope"), QStringLiteral("role-1") },
                { QStringLiteral("initial_value"), QStringLiteral("0") },
                { QStringLiteral("description"), QStringLiteral("relationship score") },
            },
        } },
        { QStringLiteral("stages"), QJsonArray{
            QJsonObject{
                { QStringLiteral("role_id"), QStringLiteral("role-1") },
                { QStringLiteral("stage_key"), QStringLiteral("trust") },
                { QStringLiteral("title"), QStringLiteral("Trust") },
                { QStringLiteral("condition"), QStringLiteral("affection >= 10") },
                { QStringLiteral("active_tag"), QStringLiteral("database.stage.role-1.trust") },
                { QStringLiteral("description"), QStringLiteral("trust stage content") },
            },
        } },
        { QStringLiteral("tags"), QJsonArray{
            QJsonObject{
                { QStringLiteral("tag"), QStringLiteral("database.tag.trust") },
                { QStringLiteral("title"), QStringLiteral("Trust Tag") },
                { QStringLiteral("trigger"), QStringLiteral("trust tag") },
                { QStringLiteral("target"), QStringLiteral("worldbook") },
                { QStringLiteral("description"), QStringLiteral("trust tag content") },
            },
        } },
    });
    project.insert(QStringLiteral("worldbook"), QJsonObject{
        { QStringLiteral("entries"), QJsonArray{
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("wb-existing") },
                { QStringLiteral("title"), QStringLiteral("Updated Lore") },
                { QStringLiteral("trigger"), QStringLiteral("updated lore") },
                { QStringLiteral("content"), QStringLiteral("updated worldbook content") },
                { QStringLiteral("unknown_project_field"), QStringLiteral("project-entry-stays") },
            },
        } },
    });
    project.insert(QStringLiteral("preset"), QJsonObject{
        { QStringLiteral("active_preset_id"), QStringLiteral("project-preset") },
        { QStringLiteral("presets"), QJsonArray{
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("project-preset") },
                { QStringLiteral("base_system_prompt"), QStringLiteral("DO NOT COPY THIS PROMPT") },
                { QStringLiteral("modules"), QJsonObject{
                    { QStringLiteral("short_paragraph"), true },
                    { QStringLiteral("long_paragraph"), true },
                } },
                { QStringLiteral("extra_prompts"), QJsonArray{
                    QJsonObject{
                        { QStringLiteral("id"), QStringLiteral("extra-new") },
                        { QStringLiteral("name"), QStringLiteral("New Extra") },
                        { QStringLiteral("content"), QStringLiteral("new extra prompt") },
                        { QStringLiteral("enabled"), true },
                        { QStringLiteral("unknown_extra_field"), QStringLiteral("extra-stays") },
                    },
                } },
                { QStringLiteral("prompt_groups"), QJsonArray{
                    QJsonObject{
                        { QStringLiteral("id"), QStringLiteral("group-new") },
                        { QStringLiteral("name"), QStringLiteral("New Group") },
                        { QStringLiteral("content"), QStringLiteral("new grouped prompt") },
                        { QStringLiteral("enabled"), true },
                    },
                } },
            },
        } },
    });
    project.insert(QStringLiteral("memory"), QJsonObject{
        { QStringLiteral("items"), QJsonArray{
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("memory-existing") },
                { QStringLiteral("title"), QStringLiteral("New Memory") },
                { QStringLiteral("content"), QStringLiteral("new memory content") },
                { QStringLiteral("tags"), QJsonArray{ QStringLiteral("tag-a") } },
                { QStringLiteral("unknown_memory_field"), QStringLiteral("memory-stays") },
            },
        } },
    });

    QString errorMessage;
    QString savedPath;
    const QJsonObject savedWorkspace = service.saveWorkspace(project, &savedPath, &errorMessage);
    if (savedWorkspace.isEmpty() || !QFileInfo::exists(savedPath) || !QFileInfo::exists(service.paths().workspacePath())) {
        return fail(QStringLiteral("saveWorkspace should create workspace project: %1").arg(errorMessage)) ? 0 : 1;
    }
    const QJsonObject savedProject = service.saveProject(QStringLiteral("hero"), project, &savedPath, &errorMessage);
    if (savedProject.isEmpty()
        || !savedPath.endsWith(QStringLiteral("hero.cardwork.json"))
        || !QFileInfo::exists(savedPath)) {
        return fail(QStringLiteral("saveProject should create .cardwork.json project: %1").arg(errorMessage)) ? 0 : 1;
    }
    const QJsonArray projectItems = service.listProjects(&errorMessage);
    if (projectItems.size() != 1
        || projectItems.first().toObject().value(QStringLiteral("filename")).toString() != QStringLiteral("hero.cardwork.json")
        || projectItems.first().toObject().value(QStringLiteral("stage_count")).toInt() != 1) {
        return fail(QStringLiteral("listProjects should expose saved project metadata")) ? 0 : 1;
    }
    const QJsonObject loadedProject = service.loadProject(QStringLiteral("hero.cardwork.json"), &errorMessage);
    if (loadedProject.value(QStringLiteral("title")).toString() != QStringLiteral("Authoring Hero")) {
        return fail(QStringLiteral("loadProject should load a saved .cardwork.json project: %1").arg(errorMessage)) ? 0 : 1;
    }
    if (!root.mkpath(QStringLiteral("exports"))) {
        return fail(QStringLiteral("failed to create export directory")) ? 0 : 1;
    }
    QString exportedPath;
    const QJsonObject exportedProject = service.exportProjectFile(
        root.absoluteFilePath(QStringLiteral("exports/hero-export.json")),
        project,
        &exportedPath,
        &errorMessage);
    if (exportedProject.value(QStringLiteral("title")).toString() != QStringLiteral("Authoring Hero")
        || !exportedPath.endsWith(QStringLiteral("hero-export.cardwork.json"))
        || !QFileInfo::exists(exportedPath)
        || readJson(exportedPath).value(QStringLiteral("type")).toString() != QStringLiteral("fantareal_card_authoring_project")) {
        return fail(QStringLiteral("exportProjectFile should write a normalized external .cardwork.json: %1").arg(errorMessage)) ? 0 : 1;
    }
    const QJsonObject fastPromptPack = service.buildCandidatePromptPack(QStringLiteral("fast"));
    if (!fastPromptPack.value(QStringLiteral("ok")).toBool()
        || fastPromptPack.value(QStringLiteral("thinking_mode")).toString() != QStringLiteral("fast")
        || fastPromptPack.value(QStringLiteral("file_count")).toInt() != 7
        || !fastPromptPack.value(QStringLiteral("system_prompt")).toString().contains(QStringLiteral("候选输出规则"))
        || fastPromptPack.value(QStringLiteral("candidate_schema")).toObject().value(QStringLiteral("candidates")).toArray().isEmpty()) {
        return fail(QStringLiteral("buildCandidatePromptPack should load fast prompt resources")) ? 0 : 1;
    }
    const QJsonObject deepPromptPack = service.buildCandidatePromptPack(QStringLiteral("deep"));
    if (!deepPromptPack.value(QStringLiteral("ok")).toBool()
        || deepPromptPack.value(QStringLiteral("file_count")).toInt() <= fastPromptPack.value(QStringLiteral("file_count")).toInt()
        || !jsonArrayContainsFilename(deepPromptPack.value(QStringLiteral("prompt_files")).toArray(), QStringLiteral("orchestration_planner.md"))) {
        return fail(QStringLiteral("buildCandidatePromptPack should include deep prompt resources")) ? 0 : 1;
    }
    const QJsonObject candidateReview{
        { QStringLiteral("summary"), QStringLiteral("candidate review") },
        { QStringLiteral("plan"), QJsonObject{
            { QStringLiteral("intent_type"), QStringLiteral("create") },
            { QStringLiteral("quality_goal"), QStringLiteral("keep runtime package coherent") },
            { QStringLiteral("package_mode"), QStringLiteral("runtime_package") },
            { QStringLiteral("required_containers"), QJsonArray{ QStringLiteral("persona"), QStringLiteral("database") } },
            { QStringLiteral("container_plan"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("module"), QStringLiteral("database") },
                    { QStringLiteral("role"), QStringLiteral("drive stage tags") },
                },
            } },
            { QStringLiteral("coverage"), QJsonObject{
                { QStringLiteral("database"), QStringLiteral("stage candidate coverage") },
            } },
            { QStringLiteral("risks"), QJsonArray{ QStringLiteral("missing tag consumers") } },
        } },
        { QStringLiteral("candidate_groups"), QJsonArray{
            QJsonObject{
                { QStringLiteral("group_id"), QStringLiteral("database_mechanism") },
                { QStringLiteral("group_title"), QStringLiteral("Database Mechanism") },
                { QStringLiteral("reason"), QStringLiteral("stage tag must have consumer") },
                { QStringLiteral("depends_on"), QJsonArray{ QStringLiteral("persona_foundation") } },
                { QStringLiteral("draft_only"), true },
            },
        } },
        { QStringLiteral("candidates"), QJsonArray{
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("persona_personality") },
                { QStringLiteral("module"), QStringLiteral("persona") },
                { QStringLiteral("action"), QStringLiteral("json_patch") },
                { QStringLiteral("target"), QJsonObject{
                    { QStringLiteral("path"), QStringLiteral("persona_card.personality") },
                    { QStringLiteral("operation"), QStringLiteral("set") },
                } },
                { QStringLiteral("after"), QStringLiteral("candidate personality") },
                { QStringLiteral("group_id"), QStringLiteral("persona_foundation") },
                { QStringLiteral("group_title"), QStringLiteral("Persona Foundation") },
                { QStringLiteral("container_role"), QStringLiteral("stabilize persona voice") },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("unsafe_path") },
                { QStringLiteral("module"), QStringLiteral("database") },
                { QStringLiteral("action"), QStringLiteral("json_patch") },
                { QStringLiteral("target"), QJsonObject{
                    { QStringLiteral("path"), QStringLiteral("database.updated_at") },
                    { QStringLiteral("operation"), QStringLiteral("set") },
                } },
                { QStringLiteral("after"), QStringLiteral("should be rejected") },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("stage_candidate") },
                { QStringLiteral("module"), QStringLiteral("database") },
                { QStringLiteral("action"), QStringLiteral("json_patch") },
                { QStringLiteral("target"), QJsonObject{
                    { QStringLiteral("path"), QStringLiteral("database.stages") },
                    { QStringLiteral("operation"), QStringLiteral("append") },
                } },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("role_id"), QStringLiteral("role-1") },
                    { QStringLiteral("stage_key"), QStringLiteral("boundaries") },
                    { QStringLiteral("title"), QStringLiteral("Boundaries") },
                    { QStringLiteral("condition"), QStringLiteral("affection < 20") },
                    { QStringLiteral("description"), QStringLiteral("keep distance") },
                } },
                { QStringLiteral("group_id"), QStringLiteral("database_mechanism") },
                { QStringLiteral("group_title"), QStringLiteral("Database Mechanism") },
                { QStringLiteral("container_role"), QStringLiteral("emit boundary stage tag") },
                { QStringLiteral("depends_on"), QJsonArray{ QStringLiteral("persona_foundation") } },
                { QStringLiteral("draft_only"), true },
            },
        } },
    };
    const QJsonObject normalizedCandidateReview = service.normalizeCandidateReview(project, candidateReview);
    const QJsonArray normalizedCandidates = normalizedCandidateReview.value(QStringLiteral("candidates")).toArray();
    const QJsonObject candidateAudit = normalizedCandidateReview.value(QStringLiteral("package_audit")).toObject();
    const QJsonObject normalizedStageCandidate = findById(normalizedCandidates, QStringLiteral("stage_candidate"));
    const QJsonObject normalizedDatabaseGroup = findGroupById(normalizedCandidateReview.value(QStringLiteral("candidate_groups")).toArray(), QStringLiteral("database_mechanism"));
    const QJsonObject normalizedPlan = normalizedCandidateReview.value(QStringLiteral("plan")).toObject();
    if (!normalizedCandidateReview.value(QStringLiteral("ok")).toBool()
        || normalizedCandidateReview.value(QStringLiteral("rejected_count")).toInt() != 1
        || normalizedCandidates.size() != 3
        || !jsonArrayContainsGroup(normalizedCandidateReview.value(QStringLiteral("candidate_groups")).toArray(), QStringLiteral("tag_consumer_link"))
        || normalizedStageCandidate.value(QStringLiteral("container_role")).toString() != QStringLiteral("emit boundary stage tag")
        || !jsonArrayContainsString(normalizedStageCandidate.value(QStringLiteral("depends_on")).toArray(), QStringLiteral("persona_foundation"))
        || !normalizedStageCandidate.value(QStringLiteral("draft_only")).toBool(false)
        || normalizedDatabaseGroup.value(QStringLiteral("group_title")).toString() != QStringLiteral("Database Mechanism")
        || !jsonArrayContainsString(normalizedDatabaseGroup.value(QStringLiteral("depends_on")).toArray(), QStringLiteral("persona_foundation"))
        || !normalizedDatabaseGroup.value(QStringLiteral("draft_only")).toBool(false)
        || normalizedPlan.value(QStringLiteral("package_mode")).toString() != QStringLiteral("runtime_package")
        || !jsonArrayContainsString(normalizedPlan.value(QStringLiteral("required_containers")).toArray(), QStringLiteral("database"))
        || normalizedPlan.value(QStringLiteral("container_plan")).toArray().first().toObject().value(QStringLiteral("module")).toString() != QStringLiteral("database")
        || normalizedPlan.value(QStringLiteral("coverage")).toObject().value(QStringLiteral("database")).toString() != QStringLiteral("stage candidate coverage")
        || !jsonArrayContainsString(candidateAudit.value(QStringLiteral("emitted_tags")).toArray(), QStringLiteral("database.stage.role-1.boundaries"))
        || !jsonArrayContainsString(candidateAudit.value(QStringLiteral("consumed_tags")).toArray(), QStringLiteral("database.stage.role-1.boundaries"))
        || !candidateAudit.value(QStringLiteral("missing_tag_consumers")).toArray().isEmpty()) {
        return fail(QStringLiteral("normalizeCandidateReview should preserve candidate metadata, reject unsafe paths, and auto-fill database tag consumers")) ? 0 : 1;
    }
    const QJsonObject candidateApply = service.applyCandidateReview(project, candidateReview);
    const QJsonObject candidateProject = candidateApply.value(QStringLiteral("project")).toObject();
    if (!candidateApply.value(QStringLiteral("ok")).toBool()
        || candidateApply.value(QStringLiteral("summary")).toObject().value(QStringLiteral("applied_count")).toInt() != 3
        || candidateProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("personality")).toString() != QStringLiteral("candidate personality")
        || candidateProject.value(QStringLiteral("database")).toObject().value(QStringLiteral("stages")).toArray().size() != 2
        || !worldbookContainsExternalTag(
            candidateProject.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray(),
            QStringLiteral("database.stage.role-1.boundaries"))) {
        return fail(QStringLiteral("applyCandidateReview should apply selected candidates to the project draft only")) ? 0 : 1;
    }

    const QJsonObject legacyCandidateReview{
        { QStringLiteral("summary"), QStringLiteral("legacy candidate review") },
        { QStringLiteral("candidates"), QJsonArray{
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("legacy_persona") },
                { QStringLiteral("module"), QStringLiteral("persona") },
                { QStringLiteral("action"), QStringLiteral("replace_field") },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("description"), QStringLiteral("legacy description") },
                    { QStringLiteral("tags"), QStringLiteral("legacy, candidate") },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("legacy_worldbook") },
                { QStringLiteral("module"), QStringLiteral("worldbook") },
                { QStringLiteral("action"), QStringLiteral("append_array_item") },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("legacy-wb") },
                    { QStringLiteral("title"), QStringLiteral("Legacy Worldbook") },
                    { QStringLiteral("trigger"), QStringLiteral("legacy lore") },
                    { QStringLiteral("content"), QStringLiteral("legacy worldbook content") },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("legacy_persona_key") },
                { QStringLiteral("module"), QStringLiteral("persona") },
                { QStringLiteral("target"), QJsonObject{ { QStringLiteral("persona_key"), QStringLiteral("2") } } },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("description"), QStringLiteral("second candidate description") },
                    { QStringLiteral("tags"), QStringLiteral("side,candidate") },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("legacy_worldbook_default_action") },
                { QStringLiteral("module"), QStringLiteral("worldbook") },
                { QStringLiteral("target"), QJsonObject{ { QStringLiteral("id"), QStringLiteral("wb-existing") } } },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("content"), QStringLiteral("default action worldbook content") },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("legacy_memory") },
                { QStringLiteral("module"), QStringLiteral("memory") },
                { QStringLiteral("action"), QStringLiteral("append_array_item") },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("legacy-memory") },
                    { QStringLiteral("title"), QStringLiteral("Legacy Memory") },
                    { QStringLiteral("content"), QStringLiteral("legacy memory content") },
                    { QStringLiteral("tags"), QStringLiteral("legacy") },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("legacy_preset") },
                { QStringLiteral("module"), QStringLiteral("preset") },
                { QStringLiteral("action"), QStringLiteral("append_array_item") },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("legacy-preset") },
                    { QStringLiteral("name"), QStringLiteral("Legacy Preset") },
                    { QStringLiteral("modules"), QJsonObject{ { QStringLiteral("short_paragraph"), true } } },
                    { QStringLiteral("extra_prompts"), QJsonArray{
                        QJsonObject{
                            { QStringLiteral("id"), QStringLiteral("legacy-extra") },
                            { QStringLiteral("name"), QStringLiteral("Legacy Extra") },
                            { QStringLiteral("content"), QStringLiteral("legacy extra prompt") },
                        },
                    } },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("legacy_stage") },
                { QStringLiteral("module"), QStringLiteral("database") },
                { QStringLiteral("action"), QStringLiteral("append_array_item") },
                { QStringLiteral("target"), QJsonObject{ { QStringLiteral("kind"), QStringLiteral("stages") } } },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("role_id"), QStringLiteral("role-1") },
                    { QStringLiteral("stage_key"), QStringLiteral("legacy") },
                    { QStringLiteral("title"), QStringLiteral("Legacy Stage") },
                    { QStringLiteral("condition"), QStringLiteral("legacy condition") },
                } },
            },
        } },
    };
    const QJsonObject legacyApply = service.applyCandidateReview(project, legacyCandidateReview);
    const QJsonObject legacyProject = legacyApply.value(QStringLiteral("project")).toObject();
    if (!legacyApply.value(QStringLiteral("ok")).toBool()
        || legacyApply.value(QStringLiteral("summary")).toObject().value(QStringLiteral("applied_count")).toInt() != 10
        || legacyProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("description")).toString() != QStringLiteral("legacy description")
        || !jsonArrayContainsString(legacyProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("tags")).toArray(), QStringLiteral("candidate"))
        || legacyProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("personas")).toObject().value(QStringLiteral("2")).toObject().value(QStringLiteral("description")).toString() != QStringLiteral("second candidate description")
        || !jsonArrayContainsString(legacyProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("personas")).toObject().value(QStringLiteral("2")).toObject().value(QStringLiteral("tags")).toArray(), QStringLiteral("candidate"))
        || findById(legacyProject.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray(), QStringLiteral("wb-existing")).value(QStringLiteral("content")).toString() != QStringLiteral("default action worldbook content")
        || findById(legacyProject.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray(), QStringLiteral("legacy-wb")).isEmpty()
        || findById(legacyProject.value(QStringLiteral("memory")).toObject().value(QStringLiteral("items")).toArray(), QStringLiteral("legacy-memory")).value(QStringLiteral("memory_status")).toString() != QStringLiteral("active")
        || findById(legacyProject.value(QStringLiteral("preset")).toObject().value(QStringLiteral("presets")).toArray(), QStringLiteral("legacy-preset")).value(QStringLiteral("enabled")).toBool(false) != true
        || !worldbookContainsExternalTag(
            legacyProject.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray(),
            QStringLiteral("database.stage.role-1.legacy"))) {
        return fail(QStringLiteral("applyCandidateReview should preserve old non-json_patch candidate actions")) ? 0 : 1;
    }

    const QJsonObject edgeCandidateReview{
        { QStringLiteral("summary"), QStringLiteral("edge candidate review") },
        { QStringLiteral("candidates"), QJsonArray{
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("remove_worldbook_alias") },
                { QStringLiteral("module"), QStringLiteral("worldbook") },
                { QStringLiteral("action"), QStringLiteral("json_patch") },
                { QStringLiteral("target"), QJsonObject{
                    { QStringLiteral("path"), QStringLiteral("worldbook.entries.0") },
                    { QStringLiteral("operation"), QStringLiteral("remove") },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("delete_memory_item") },
                { QStringLiteral("module"), QStringLiteral("memory") },
                { QStringLiteral("action"), QStringLiteral("delete") },
                { QStringLiteral("target"), QJsonObject{
                    { QStringLiteral("path"), QStringLiteral("memory.items.0") },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("update_memory_item") },
                { QStringLiteral("module"), QStringLiteral("memory") },
                { QStringLiteral("action"), QStringLiteral("update_array_item") },
                { QStringLiteral("target"), QJsonObject{ { QStringLiteral("id"), QStringLiteral("memory-existing") } } },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("content"), QStringLiteral("candidate updated memory") },
                    { QStringLiteral("tags"), QStringLiteral("edge,updated") },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("update_preset_item") },
                { QStringLiteral("module"), QStringLiteral("preset") },
                { QStringLiteral("action"), QStringLiteral("update_array_item") },
                { QStringLiteral("target"), QJsonObject{ { QStringLiteral("id"), QStringLiteral("project-preset") } } },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("modules"), QJsonObject{
                        { QStringLiteral("short_paragraph"), false },
                        { QStringLiteral("second_person"), true },
                    } },
                    { QStringLiteral("extra_prompts"), QJsonArray{
                        QJsonObject{
                            { QStringLiteral("id"), QStringLiteral("edge-extra") },
                            { QStringLiteral("name"), QStringLiteral("Edge Extra") },
                            { QStringLiteral("content"), QStringLiteral("edge extra prompt") },
                        },
                    } },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("update_database_variable") },
                { QStringLiteral("module"), QStringLiteral("database") },
                { QStringLiteral("action"), QStringLiteral("update_array_item") },
                { QStringLiteral("target"), QJsonObject{
                    { QStringLiteral("kind"), QStringLiteral("variables") },
                    { QStringLiteral("id"), QStringLiteral("db_var_001") },
                } },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("label"), QStringLiteral("Affection Updated") },
                    { QStringLiteral("write_policy"), QStringLiteral("only update after explicit affection signal") },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("append_database_stage_singular") },
                { QStringLiteral("module"), QStringLiteral("database") },
                { QStringLiteral("action"), QStringLiteral("append_array_item") },
                { QStringLiteral("target"), QJsonObject{
                    { QStringLiteral("kind"), QStringLiteral("stage") },
                } },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("role_id"), QStringLiteral("role-1") },
                    { QStringLiteral("stage_key"), QStringLiteral("boundary") },
                    { QStringLiteral("title"), QStringLiteral("Boundary") },
                    { QStringLiteral("condition"), QStringLiteral("affection >= 20") },
                } },
            },
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("update_database_tag_singular") },
                { QStringLiteral("module"), QStringLiteral("database") },
                { QStringLiteral("action"), QStringLiteral("update_array_item") },
                { QStringLiteral("target"), QJsonObject{
                    { QStringLiteral("kind"), QStringLiteral("tag") },
                    { QStringLiteral("id"), QStringLiteral("db_tag_001") },
                } },
                { QStringLiteral("after"), QJsonObject{
                    { QStringLiteral("title"), QStringLiteral("Trust Tag Updated") },
                    { QStringLiteral("description"), QStringLiteral("updated by singular kind alias") },
                } },
            },
        } },
    };
    const QJsonObject edgeNormalized = service.normalizeCandidateReview(project, edgeCandidateReview);
    const QJsonArray edgeCandidates = edgeNormalized.value(QStringLiteral("candidates")).toArray();
    if (!edgeNormalized.value(QStringLiteral("ok")).toBool()
        || edgeCandidates.size() != 9
        || edgeCandidates.first().toObject().value(QStringLiteral("target")).toObject().value(QStringLiteral("operation")).toString() != QStringLiteral("delete")
        || edgeCandidates.at(1).toObject().value(QStringLiteral("target")).toObject().value(QStringLiteral("operation")).toString() != QStringLiteral("delete")) {
        return fail(QStringLiteral("normalizeCandidateReview should normalize delete aliases and keep database stage tag consumers: count=%1, op0=%2, op1=%3")
                        .arg(edgeCandidates.size())
                        .arg(edgeCandidates.size() > 0 ? edgeCandidates.at(0).toObject().value(QStringLiteral("target")).toObject().value(QStringLiteral("operation")).toString() : QStringLiteral("<missing>"))
                        .arg(edgeCandidates.size() > 1 ? edgeCandidates.at(1).toObject().value(QStringLiteral("target")).toObject().value(QStringLiteral("operation")).toString() : QStringLiteral("<missing>")))
            ? 0
            : 1;
    }
    const QJsonObject edgeApply = service.applyCandidateReview(project, edgeCandidateReview, {
        QStringLiteral("update_memory_item"),
        QStringLiteral("update_preset_item"),
        QStringLiteral("update_database_variable"),
        QStringLiteral("append_database_stage_singular"),
        QStringLiteral("update_database_tag_singular"),
    });
    const QJsonObject edgeProject = edgeApply.value(QStringLiteral("project")).toObject();
    const QJsonObject updatedMemoryCandidate = findById(edgeProject.value(QStringLiteral("memory")).toObject().value(QStringLiteral("items")).toArray(), QStringLiteral("memory-existing"));
    const QJsonObject updatedPresetCandidate = findById(edgeProject.value(QStringLiteral("preset")).toObject().value(QStringLiteral("presets")).toArray(), QStringLiteral("project-preset"));
    const QJsonObject updatedDatabaseVariable = findById(edgeProject.value(QStringLiteral("database")).toObject().value(QStringLiteral("variables")).toArray(), QStringLiteral("db_var_001"));
    const QJsonObject appendedDatabaseStage = findById(edgeProject.value(QStringLiteral("database")).toObject().value(QStringLiteral("stages")).toArray(), QStringLiteral("db_stage_002"));
    const QJsonObject updatedDatabaseTag = findById(edgeProject.value(QStringLiteral("database")).toObject().value(QStringLiteral("tags")).toArray(), QStringLiteral("db_tag_001"));
    if (!edgeApply.value(QStringLiteral("ok")).toBool()
        || edgeApply.value(QStringLiteral("summary")).toObject().value(QStringLiteral("applied_count")).toInt() != 5
        || edgeApply.value(QStringLiteral("summary")).toObject().value(QStringLiteral("skipped_count")).toInt() != 4
        || updatedMemoryCandidate.value(QStringLiteral("content")).toString() != QStringLiteral("candidate updated memory")
        || !jsonArrayContainsString(updatedMemoryCandidate.value(QStringLiteral("tags")).toArray(), QStringLiteral("updated"))
        || updatedPresetCandidate.value(QStringLiteral("modules")).toObject().value(QStringLiteral("second_person")).toBool(false) != true
        || findById(updatedPresetCandidate.value(QStringLiteral("extra_prompts")).toArray(), QStringLiteral("edge-extra")).value(QStringLiteral("content")).toString() != QStringLiteral("edge extra prompt")
        || updatedDatabaseVariable.value(QStringLiteral("label")).toString() != QStringLiteral("Affection Updated")
        || updatedDatabaseVariable.value(QStringLiteral("write_policy")).toString() != QStringLiteral("only update after explicit affection signal")
        || appendedDatabaseStage.value(QStringLiteral("stage_key")).toString() != QStringLiteral("boundary")
        || updatedDatabaseTag.value(QStringLiteral("title")).toString() != QStringLiteral("Trust Tag Updated")) {
        return fail(QStringLiteral("applyCandidateReview should handle selected update_array_item candidates and database kind aliases")) ? 0 : 1;
    }
    const QJsonObject edgeDeleteApply = service.applyCandidateReview(project, edgeCandidateReview, {
        QStringLiteral("remove_worldbook_alias"),
        QStringLiteral("delete_memory_item"),
    });
    const QJsonObject edgeDeleteProject = edgeDeleteApply.value(QStringLiteral("project")).toObject();
    if (!edgeDeleteApply.value(QStringLiteral("ok")).toBool()
        || edgeDeleteApply.value(QStringLiteral("summary")).toObject().value(QStringLiteral("applied_count")).toInt() != 2
        || !edgeDeleteProject.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray().isEmpty()
        || !edgeDeleteProject.value(QStringLiteral("memory")).toObject().value(QStringLiteral("items")).toArray().isEmpty()) {
        return fail(QStringLiteral("applyCandidateReview should apply json_patch delete/remove candidates to project arrays")) ? 0 : 1;
    }

    const QJsonObject importedStateJournal{
        { QStringLiteral("enabled"), true },
        { QStringLiteral("roles"), QJsonArray{
            QJsonObject{
                { QStringLiteral("role_id"), QStringLiteral("legacy-role") },
                { QStringLiteral("role_name"), QStringLiteral("Legacy Role") },
                { QStringLiteral("variables"), QJsonArray{
                    QJsonObject{
                        { QStringLiteral("var_key"), QStringLiteral("trust") },
                        { QStringLiteral("var_name"), QStringLiteral("Trust") },
                        { QStringLiteral("default_value"), 5 },
                        { QStringLiteral("instruction"), QStringLiteral("track trust from old stateJournal") },
                    },
                } },
                { QStringLiteral("stages"), QJsonArray{
                    QJsonObject{
                        { QStringLiteral("stage_key"), QStringLiteral("warm") },
                        { QStringLiteral("stage_name"), QStringLiteral("Warm") },
                        { QStringLiteral("activation_tag"), QStringLiteral("state_journal.stage.legacy-role.warm") },
                        { QStringLiteral("conditions"), QJsonArray{
                            QJsonObject{
                                { QStringLiteral("var"), QStringLiteral("trust") },
                                { QStringLiteral("op"), QStringLiteral(">=") },
                                { QStringLiteral("value"), 5 },
                            },
                        } },
                    },
                } },
            },
        } },
    };
    const QString roleImportPath = root.absoluteFilePath(QStringLiteral("imported-role.json"));
    const QString wrappedRoleImportPath = root.absoluteFilePath(QStringLiteral("imported-wrapped-role.json"));
    if (!writeJson(roleImportPath, QJsonObject{
            { QStringLiteral("name"), QStringLiteral("Imported Role") },
            { QStringLiteral("description"), QStringLiteral("imported description") },
            { QStringLiteral("stateJournal"), importedStateJournal },
        })
        || !writeJson(wrappedRoleImportPath, QJsonObject{
            { QStringLiteral("source_name"), QStringLiteral("Wrapped Source") },
            { QStringLiteral("raw"), QJsonObject{
                { QStringLiteral("name"), QStringLiteral("Wrapped Role") },
                { QStringLiteral("description"), QStringLiteral("wrapped description") },
                { QStringLiteral("stateJournal"), importedStateJournal },
            } },
        })) {
        return fail(QStringLiteral("failed to write imported role fixture")) ? 0 : 1;
    }
    QString importedPath;
    const QJsonObject importedProject = service.importProjectFile(roleImportPath, &importedPath, &errorMessage);
    const QJsonObject importedWrappedProject = service.importProjectFile(wrappedRoleImportPath, nullptr, &errorMessage);
    const QJsonObject importedDatabase = importedProject.value(QStringLiteral("database")).toObject();
    const QJsonObject importedStateVariable = findById(importedDatabase.value(QStringLiteral("variables")).toArray(), QStringLiteral("db_var_legacy-role_trust"));
    const QJsonObject importedStateStage = findById(importedDatabase.value(QStringLiteral("stages")).toArray(), QStringLiteral("db_stage_legacy-role_warm"));
    const QJsonObject importedStateTag = findById(importedDatabase.value(QStringLiteral("tags")).toArray(), QStringLiteral("db_tag_legacy-role_warm"));
    if (importedProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("name")).toString() != QStringLiteral("Imported Role")
        || importedStateVariable.value(QStringLiteral("key")).toString() != QStringLiteral("trust")
        || importedStateVariable.value(QStringLiteral("initial_value")).toString() != QStringLiteral("5")
        || importedStateStage.value(QStringLiteral("condition")).toString() != QStringLiteral("trust >= 5")
        || importedStateStage.value(QStringLiteral("active_tag")).toString() != QStringLiteral("database.stage.legacy-role.warm")
        || importedStateTag.value(QStringLiteral("tag")).toString() != QStringLiteral("database.stage.legacy-role.warm")
        || importedWrappedProject.value(QStringLiteral("title")).toString() != QStringLiteral("Wrapped Source")
        || importedWrappedProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("name")).toString() != QStringLiteral("Wrapped Role")
        || findById(importedWrappedProject.value(QStringLiteral("database")).toObject().value(QStringLiteral("variables")).toArray(), QStringLiteral("db_var_legacy-role_trust")).isEmpty()
        || !QFileInfo::exists(importedPath)
        || QFileInfo(importedPath).absolutePath() != service.paths().projectsPath()) {
        return fail(QStringLiteral("importProjectFile should normalize external role JSON and stateJournal database drafts into projects: %1").arg(errorMessage)) ? 0 : 1;
    }
    const QString worldbookImportPath = root.absoluteFilePath(QStringLiteral("imported-worldbook.json"));
    const QString memoryImportPath = root.absoluteFilePath(QStringLiteral("imported-memory.json"));
    const QString presetImportPath = root.absoluteFilePath(QStringLiteral("imported-preset.json"));
    if (!writeJson(worldbookImportPath, QJsonObject{
            { QStringLiteral("entries"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("import-wb") },
                    { QStringLiteral("trigger"), QStringLiteral("import trigger") },
                    { QStringLiteral("content"), QStringLiteral("import worldbook") },
                },
            } },
        })
        || !writeJson(memoryImportPath, QJsonObject{
            { QStringLiteral("items"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("import-memory") },
                    { QStringLiteral("content"), QStringLiteral("import memory") },
                    { QStringLiteral("tags"), QStringLiteral("imported") },
                },
            } },
        })
        || !writeJson(presetImportPath, QJsonObject{
            { QStringLiteral("active_preset_id"), QStringLiteral("import-preset") },
            { QStringLiteral("presets"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("import-preset") },
                    { QStringLiteral("name"), QStringLiteral("Import Preset") },
                    { QStringLiteral("modules"), QJsonObject{ { QStringLiteral("short_paragraph"), true } } },
                },
            } },
        })) {
        return fail(QStringLiteral("failed to write external import fixtures")) ? 0 : 1;
    }
    const QJsonObject importedWorldbook = service.importProjectFile(worldbookImportPath, nullptr, &errorMessage);
    const QJsonObject importedMemory = service.importProjectFile(memoryImportPath, nullptr, &errorMessage);
    const QJsonObject importedPreset = service.importProjectFile(presetImportPath, nullptr, &errorMessage);
    if (importedWorldbook.value(QStringLiteral("title")).toString() != QStringLiteral("导入的世界书")
        || findById(importedWorldbook.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray(), QStringLiteral("import-wb")).value(QStringLiteral("entry_type")).toString() != QStringLiteral("keyword")
        || importedMemory.value(QStringLiteral("title")).toString() != QStringLiteral("导入的记忆")
        || findById(importedMemory.value(QStringLiteral("memory")).toObject().value(QStringLiteral("items")).toArray(), QStringLiteral("import-memory")).value(QStringLiteral("memory_status")).toString() != QStringLiteral("active")
        || importedPreset.value(QStringLiteral("title")).toString() != QStringLiteral("导入的预设")
        || findById(importedPreset.value(QStringLiteral("preset")).toObject().value(QStringLiteral("presets")).toArray(), QStringLiteral("import-preset")).value(QStringLiteral("enabled")).toBool(false) != true) {
        return fail(QStringLiteral("importProjectFile should normalize old standalone worldbook, memory, and preset JSON: %1").arg(errorMessage)) ? 0 : 1;
    }
    const QString oldProjectImportPath = root.absoluteFilePath(QStringLiteral("old-card-writer-project.json"));
    const QString nodeProjectImportPath = root.absoluteFilePath(QStringLiteral("old-node-cardwork.json"));
    if (!writeJson(oldProjectImportPath, QJsonObject{
            { QStringLiteral("title"), QStringLiteral("Old Writer Project") },
            { QStringLiteral("card"), QJsonObject{
                { QStringLiteral("name"), QStringLiteral("Old Role") },
                { QStringLiteral("description"), QStringLiteral("old role description") },
                { QStringLiteral("personality"), QStringLiteral("old role personality") },
                { QStringLiteral("scenario"), QStringLiteral("old scenario") },
                { QStringLiteral("first_mes"), QStringLiteral("old first") },
                { QStringLiteral("tags"), QStringLiteral("old,writer") },
                { QStringLiteral("creativeWorkshop"), QJsonObject{
                    { QStringLiteral("enabled"), false },
                    { QStringLiteral("items"), QJsonArray{
                        QJsonObject{
                            { QStringLiteral("id"), QStringLiteral("legacy-workshop") },
                            { QStringLiteral("name"), QStringLiteral("Legacy Workshop") },
                            { QStringLiteral("triggerMode"), QStringLiteral("stage") },
                            { QStringLiteral("triggerStage"), QStringLiteral("stage_a") },
                            { QStringLiteral("actionType"), QStringLiteral("image") },
                            { QStringLiteral("imageUrl"), QStringLiteral("legacy.png") },
                            { QStringLiteral("note"), QStringLiteral("legacy workshop note") },
                        },
                    } },
                } },
            } },
            { QStringLiteral("personas"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("2") },
                    { QStringLiteral("name"), QStringLiteral("Second Role") },
                    { QStringLiteral("description"), QStringLiteral("second description") },
                },
            } },
            { QStringLiteral("worldbooks"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("old-wb") },
                    { QStringLiteral("title"), QStringLiteral("Old WB") },
                    { QStringLiteral("keywords"), QStringLiteral("old keyword") },
                    { QStringLiteral("content"), QStringLiteral("old worldbook content") },
                    { QStringLiteral("notes"), QStringLiteral("old worldbook notes") },
                },
            } },
            { QStringLiteral("memories"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("old-memory") },
                    { QStringLiteral("title"), QStringLiteral("Old Memory") },
                    { QStringLiteral("content"), QStringLiteral("old memory content") },
                    { QStringLiteral("summary"), QStringLiteral("old memory summary") },
                },
            } },
            { QStringLiteral("presets"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("old-preset") },
                    { QStringLiteral("title"), QStringLiteral("Old Preset") },
                    { QStringLiteral("content"), QStringLiteral("old preset body") },
                },
            } },
            { QStringLiteral("database"), QJsonObject{
                { QStringLiteral("stages"), QJsonArray{
                    QJsonObject{
                        { QStringLiteral("role_id"), QStringLiteral("old_role") },
                        { QStringLiteral("stage_key"), QStringLiteral("stage_a") },
                    },
                } },
            } },
        })
        || !writeJson(nodeProjectImportPath, QJsonObject{
            { QStringLiteral("title"), QStringLiteral("Node Project") },
            { QStringLiteral("nodes"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("type"), QStringLiteral("basic") },
                    { QStringLiteral("content"), QStringLiteral("角色名：Node Role\n标签：node,legacy") },
                },
                QJsonObject{
                    { QStringLiteral("type"), QStringLiteral("description") },
                    { QStringLiteral("content"), QStringLiteral("node description") },
                },
                QJsonObject{
                    { QStringLiteral("type"), QStringLiteral("first_mes") },
                    { QStringLiteral("content"), QStringLiteral("node first") },
                },
                QJsonObject{
                    { QStringLiteral("type"), QStringLiteral("personas") },
                    { QStringLiteral("content"), QStringLiteral("角色 2：Node Side\n描述：node side description\n性格：node side personality\n场景：node side scenario\n备注：node side notes") },
                },
            } },
        })) {
        return fail(QStringLiteral("failed to write old card writer import fixtures")) ? 0 : 1;
    }
    const QJsonObject importedOldProject = service.importProjectFile(oldProjectImportPath, nullptr, &errorMessage);
    const QJsonObject importedNodeProject = service.importProjectFile(nodeProjectImportPath, nullptr, &errorMessage);
    if (importedOldProject.value(QStringLiteral("type")).toString() != QStringLiteral("fantareal_card_authoring_project")
        || importedOldProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("name")).toString() != QStringLiteral("Old Role")
        || !jsonArrayContainsString(importedOldProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("tags")).toArray(), QStringLiteral("writer"))
        || importedOldProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("personas")).toObject().value(QStringLiteral("2")).toObject().value(QStringLiteral("name")).toString() != QStringLiteral("Second Role")
        || importedOldProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("creativeWorkshop")).toObject().value(QStringLiteral("items")).toArray().first().toObject().value(QStringLiteral("note")).toString() != QStringLiteral("legacy workshop note")
        || findById(importedOldProject.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray(), QStringLiteral("old-wb")).value(QStringLiteral("trigger")).toString() != QStringLiteral("old keyword")
        || findById(importedOldProject.value(QStringLiteral("memory")).toObject().value(QStringLiteral("items")).toArray(), QStringLiteral("old-memory")).value(QStringLiteral("notes")).toString() != QStringLiteral("old memory summary")
        || findById(importedOldProject.value(QStringLiteral("preset")).toObject().value(QStringLiteral("presets")).toArray(), QStringLiteral("old-preset")).value(QStringLiteral("base_system_prompt")).toString() != QStringLiteral("old preset body")
        || importedOldProject.value(QStringLiteral("database")).toObject().value(QStringLiteral("stages")).toArray().first().toObject().value(QStringLiteral("active_tag")).toString() != QStringLiteral("database.stage.old_role.stage_a")
        || importedNodeProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("name")).toString() != QStringLiteral("Node Role")
        || !jsonArrayContainsString(importedNodeProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("tags")).toArray(), QStringLiteral("legacy"))
        || importedNodeProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("first_mes")).toString() != QStringLiteral("node first")
        || importedNodeProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("personas")).toObject().value(QStringLiteral("2")).toObject().value(QStringLiteral("personality")).toString() != QStringLiteral("node side personality")) {
        return fail(QStringLiteral("importProjectFile should normalize old card writer project and node cardwork JSON: %1").arg(errorMessage)) ? 0 : 1;
    }
    QString archivedPath;
    const QJsonObject archivedProject = service.deleteProject(QFileInfo(importedPath).fileName(), &archivedPath, &errorMessage);
    if (archivedProject.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("name")).toString() != QStringLiteral("Imported Role")
        || QFileInfo::exists(importedPath)
        || !QFileInfo::exists(archivedPath)) {
        return fail(QStringLiteral("deleteProject should archive project instead of dropping it: %1").arg(errorMessage)) ? 0 : 1;
    }

    const QJsonObject compiled = service.compileRoleCard(project);
    const QJsonObject compiledRaw = compiled.value(QStringLiteral("raw")).toObject();
    const QJsonObject stateJournal = compiledRaw.value(QStringLiteral("stateJournal")).toObject();
    const QJsonObject compiledSidePersona = compiledRaw.value(QStringLiteral("personas")).toObject().value(QStringLiteral("2")).toObject();
    if (compiledRaw.value(QStringLiteral("name")).toString() != QStringLiteral("New Name")
        || compiledRaw.value(QStringLiteral("creativeWorkshop")).toObject().value(QStringLiteral("items")).toArray().first().toObject().value(QStringLiteral("note")).toString() != QStringLiteral("main workshop note")
        || compiledRaw.value(QStringLiteral("mes_example")).toString() != QStringLiteral("new example dialogue")
        || compiledRaw.value(QStringLiteral("creator_notes")).toString() != QStringLiteral("new hidden rules")
        || compiledSidePersona.value(QStringLiteral("description")).toString() != QStringLiteral("second old description")
        || compiledSidePersona.value(QStringLiteral("personality")).toString() != QStringLiteral("second personality")
        || compiledSidePersona.value(QStringLiteral("scenario")).toString() != QStringLiteral("second scenario")
        || compiledSidePersona.value(QStringLiteral("creator_notes")).toString() != QStringLiteral("second notes")
        || !jsonArrayContainsString(compiledSidePersona.value(QStringLiteral("tags")).toArray(), QStringLiteral("side"))
        || !stateJournal.value(QStringLiteral("enabled")).toBool(false)
        || stateJournal.value(QStringLiteral("databaseDraft")).toObject().value(QStringLiteral("stages")).toArray().isEmpty()) {
        return fail(QStringLiteral("compileRoleCard should produce persona and compatible stateJournal draft")) ? 0 : 1;
    }
    const QJsonObject compiledRole = findById(stateJournal.value(QStringLiteral("roles")).toArray(), QStringLiteral("role-1"));
    const QJsonObject compiledVariable = findByKey(compiledRole.value(QStringLiteral("variables")).toArray(), QStringLiteral("var_key"), QStringLiteral("affection"));
    const QJsonObject compiledStage = findByKey(compiledRole.value(QStringLiteral("stages")).toArray(), QStringLiteral("stage_key"), QStringLiteral("trust"));
    const QJsonArray compiledConditions = compiledStage.value(QStringLiteral("conditions")).toArray();
    const QJsonObject compiledCondition = compiledConditions.isEmpty() ? QJsonObject{} : compiledConditions.first().toObject();
    if (stateJournal.value(QStringLiteral("role_source_mode")).toString() != QStringLiteral("auto")
        || compiledRole.value(QStringLiteral("mode")).toString() != QStringLiteral("full")
        || compiledRole.value(QStringLiteral("stateJournalMode")).toString() != QStringLiteral("full")
        || !compiledRole.value(QStringLiteral("has_state_journal_config")).toBool(false)
        || compiledRole.value(QStringLiteral("display_policy")).toString() != QStringLiteral("show")
        || compiledRole.value(QStringLiteral("use_default_variables")).toBool(true)
        || compiledRole.value(QStringLiteral("settings")).toObject().value(QStringLiteral("confirm_turns")).toInt(0) != 1
        || compiledRole.value(QStringLiteral("initial_stage")).toString() != QStringLiteral("trust")
        || compiledVariable.value(QStringLiteral("default_value")).toDouble(-1) != 0
        || compiledVariable.value(QStringLiteral("min_value")).toInt(-1) != 0
        || compiledVariable.value(QStringLiteral("max_value")).toInt(-1) != 100
        || compiledVariable.value(QStringLiteral("instruction")).toString() != QStringLiteral("relationship score")
        || compiledStage.value(QStringLiteral("activation_tag")).toString() != QStringLiteral("database.stage.role-1.trust")
        || compiledStage.value(QStringLiteral("condition_text")).toString() != QStringLiteral("affection >= 10")
        || compiledConditions.size() != 1
        || compiledCondition.value(QStringLiteral("var")).toString() != QStringLiteral("affection")
        || compiledCondition.value(QStringLiteral("op")).toString() != QStringLiteral(">=")
        || compiledCondition.value(QStringLiteral("value")).toDouble(-1) != 10) {
        return fail(QStringLiteral("compileRoleCard should emit legacy-compatible stateJournal role, variable, and stage fields")) ? 0 : 1;
    }

    const QJsonObject preview = service.buildApplyPreview(project, { QStringLiteral("database") });
    if (!preview.value(QStringLiteral("ok")).toBool()
        || preview.value(QStringLiteral("summary")).toObject().value(QStringLiteral("change_count")).toInt() <= 0) {
        return fail(QStringLiteral("buildApplyPreview should report database changes")) ? 0 : 1;
    }
    const QJsonArray previewGroups = preview.value(QStringLiteral("groups")).toArray();
    const QJsonArray previewChanges = previewGroups.first().toObject().value(QStringLiteral("changes")).toArray();
    const QJsonObject firstChange = previewChanges.first().toObject();
    if (firstChange.value(QStringLiteral("label")).toString() != QStringLiteral("数据库兼容字段")
        || firstChange.value(QStringLiteral("path")).toString() != QStringLiteral("raw.stateJournal")
        || firstChange.value(QStringLiteral("action")).toString().isEmpty()
        || firstChange.value(QStringLiteral("after_preview")).toString().isEmpty()) {
        return fail(QStringLiteral("buildApplyPreview should expose readable diff metadata")) ? 0 : 1;
    }
    const QJsonObject emptyPreview = service.buildApplyPreview(service.createEmptyProject(), { QStringLiteral("persona"), QStringLiteral("database") });
    if (emptyPreview.value(QStringLiteral("warnings")).toArray().size() < 2
        || emptyPreview.value(QStringLiteral("summary")).toObject().value(QStringLiteral("warning_count")).toInt() < 2) {
        return fail(QStringLiteral("buildApplyPreview should expose validation warnings")) ? 0 : 1;
    }
    const QJsonObject afterPreview = readJson(currentCardPath);
    if (afterPreview.value(QStringLiteral("raw")).toObject().value(QStringLiteral("stateJournal")).toObject().value(QStringLiteral("unknown_state_field")).toString()
        != QStringLiteral("state-stays")) {
        return fail(QStringLiteral("buildApplyPreview must not write current_role_card.json")) ? 0 : 1;
    }
    const QByteArray worldbookBeforePreview = readBytes(worldbookPath);
    const QByteArray presetBeforePreview = readBytes(presetPath);
    const QByteArray memoryBeforePreview = readBytes(memoryPath);
    const QByteArray mergedMemoryBeforePreview = readBytes(mergedMemoryPath);
    const QByteArray outlineBeforePreview = readBytes(memoryOutlinePath);
    const QJsonObject runtimePreview = service.buildApplyPreview(project, {
        QStringLiteral("worldbook"),
        QStringLiteral("preset"),
        QStringLiteral("memory"),
    });
    if (!runtimePreview.value(QStringLiteral("ok")).toBool()
        || runtimePreview.value(QStringLiteral("summary")).toObject().value(QStringLiteral("change_count")).toInt() < 3) {
        return fail(QStringLiteral("buildApplyPreview should report worldbook/preset/memory changes")) ? 0 : 1;
    }
    if (worldbookBeforePreview != readBytes(worldbookPath)
        || presetBeforePreview != readBytes(presetPath)
        || memoryBeforePreview != readBytes(memoryPath)
        || mergedMemoryBeforePreview != readBytes(mergedMemoryPath)
        || outlineBeforePreview != readBytes(memoryOutlinePath)) {
        return fail(QStringLiteral("runtime apply preview must not write runtime files")) ? 0 : 1;
    }

    const QJsonObject applyResult = service.applySelected(project, { QStringLiteral("database") });
    if (!applyResult.value(QStringLiteral("ok")).toBool()
        || applyResult.value(QStringLiteral("applied")).toArray().size() != 1
        || applyResult.value(QStringLiteral("backups")).toArray().isEmpty()) {
        return fail(QStringLiteral("applySelected should apply database group and create backup")) ? 0 : 1;
    }
    if (applyResult.value(QStringLiteral("preview")).toObject().value(QStringLiteral("summary")).toObject().value(QStringLiteral("change_count")).toInt() <= 0) {
        return fail(QStringLiteral("applySelected should return the diff that was applied")) ? 0 : 1;
    }
    const QString backupPath = applyResult.value(QStringLiteral("backups")).toArray().at(0).toString();
    if (!QFileInfo::exists(backupPath)) {
        return fail(QStringLiteral("backup file should exist")) ? 0 : 1;
    }
    const QJsonObject afterApply = readJson(currentCardPath);
    const QJsonObject afterApplyRaw = afterApply.value(QStringLiteral("raw")).toObject();
    const QJsonObject afterApplyStateJournal = afterApplyRaw.value(QStringLiteral("stateJournal")).toObject();
    if (afterApplyRaw.value(QStringLiteral("name")).toString() != QStringLiteral("Old Name")
        || !afterApplyStateJournal.value(QStringLiteral("enabled")).toBool(false)
        || afterApplyStateJournal.value(QStringLiteral("unknown_state_field")).toString() != QStringLiteral("state-stays")
        || afterApplyStateJournal.value(QStringLiteral("databaseDraft")).toObject().value(QStringLiteral("variables")).toArray().isEmpty()) {
        return fail(QStringLiteral("database apply should update stateJournal without applying persona fields")) ? 0 : 1;
    }
    const QJsonObject afterApplyRole = findById(afterApplyStateJournal.value(QStringLiteral("roles")).toArray(), QStringLiteral("role-1"));
    const QJsonObject afterApplyLegacyVariable = findByKey(afterApplyRole.value(QStringLiteral("variables")).toArray(), QStringLiteral("var_key"), QStringLiteral("legacy"));
    const QJsonObject afterApplyVariable = findByKey(afterApplyRole.value(QStringLiteral("variables")).toArray(), QStringLiteral("var_key"), QStringLiteral("affection"));
    const QJsonObject afterApplyLegacyStage = findByKey(afterApplyRole.value(QStringLiteral("stages")).toArray(), QStringLiteral("stage_key"), QStringLiteral("legacy_stage"));
    const QJsonObject afterApplyStage = findByKey(afterApplyRole.value(QStringLiteral("stages")).toArray(), QStringLiteral("stage_key"), QStringLiteral("trust"));
    const QJsonArray afterApplyConditions = afterApplyStage.value(QStringLiteral("conditions")).toArray();
    if (afterApplyRole.value(QStringLiteral("role_name")).toString() != QStringLiteral("Existing Role")
        || afterApplyRole.value(QStringLiteral("unknown_role_field")).toString() != QStringLiteral("role-stays")
        || afterApplyRole.value(QStringLiteral("mode")).toString() != QStringLiteral("full")
        || afterApplyRole.value(QStringLiteral("stateJournalMode")).toString() != QStringLiteral("full")
        || afterApplyRole.value(QStringLiteral("use_default_variables")).toBool(true)
        || afterApplyRole.value(QStringLiteral("settings")).toObject().value(QStringLiteral("cooldown_turns")).toInt(-1) != 0
        || afterApplyRole.value(QStringLiteral("initial_stage")).toString() != QStringLiteral("trust")
        || afterApplyLegacyVariable.value(QStringLiteral("unknown_variable_field")).toString() != QStringLiteral("variable-stays")
        || afterApplyVariable.value(QStringLiteral("default_value")).toDouble(-1) != 0
        || afterApplyLegacyStage.value(QStringLiteral("unknown_stage_field")).toString() != QStringLiteral("stage-stays")
        || afterApplyStage.value(QStringLiteral("activation_tag")).toString() != QStringLiteral("database.stage.role-1.trust")
        || afterApplyConditions.size() != 1
        || afterApplyConditions.first().toObject().value(QStringLiteral("var")).toString() != QStringLiteral("affection")) {
        return fail(QStringLiteral("database apply should merge legacy stateJournal roles without dropping old role fields")) ? 0 : 1;
    }
    const QJsonObject runtimeApply = service.applySelected(project, {
        QStringLiteral("worldbook"),
        QStringLiteral("preset"),
        QStringLiteral("memory"),
    });
    if (!runtimeApply.value(QStringLiteral("ok")).toBool()
        || runtimeApply.value(QStringLiteral("applied")).toArray().size() != 3
        || runtimeApply.value(QStringLiteral("backups")).toArray().size() < 3) {
        return fail(QStringLiteral("applySelected should apply worldbook/preset/memory and backup existing runtime files")) ? 0 : 1;
    }
    const QJsonObject appliedWorldbook = readJson(worldbookPath);
    const QJsonArray appliedWorldbookEntries = appliedWorldbook.value(QStringLiteral("entries")).toArray();
    const QJsonObject updatedWorldbookEntry = findById(appliedWorldbookEntries, QStringLiteral("wb-existing"));
    if (appliedWorldbook.value(QStringLiteral("unknown_root_field")).toString() != QStringLiteral("worldbook-root-stays")
        || updatedWorldbookEntry.value(QStringLiteral("content")).toString() != QStringLiteral("updated worldbook content")
        || updatedWorldbookEntry.value(QStringLiteral("unknown_worldbook_field")).toString() != QStringLiteral("entry-stays")
        || updatedWorldbookEntry.value(QStringLiteral("unknown_project_field")).toString() != QStringLiteral("project-entry-stays")
        || findById(appliedWorldbookEntries, QStringLiteral("card-authoring-database-tag-database-tag-trust")).isEmpty()) {
        return fail(QStringLiteral("worldbook apply should merge entries, preserve unknown fields, and add database tag consumers")) ? 0 : 1;
    }
    const QJsonObject appliedPresetStore = readJson(presetPath);
    const QJsonObject appliedPreset = findById(appliedPresetStore.value(QStringLiteral("presets")).toArray(), QStringLiteral("base"));
    const QJsonObject appliedModules = appliedPreset.value(QStringLiteral("modules")).toObject();
    if (appliedPreset.value(QStringLiteral("base_system_prompt")).toString() != QStringLiteral("KEEP BASE PROMPT")
        || appliedPreset.value(QStringLiteral("unknown_preset_field")).toString() != QStringLiteral("preset-stays")
        || !appliedModules.value(QStringLiteral("short_paragraph")).toBool(false)
        || appliedModules.value(QStringLiteral("long_paragraph")).toBool(true)
        || findById(appliedPreset.value(QStringLiteral("extra_prompts")).toArray(), QStringLiteral("extra-new")).value(QStringLiteral("unknown_extra_field")).toString() != QStringLiteral("extra-stays")
        || findById(appliedPreset.value(QStringLiteral("prompt_groups")).toArray(), QStringLiteral("group-new")).isEmpty()) {
        return fail(QStringLiteral("preset apply should merge lightweight fields without overwriting high-level prompt body")) ? 0 : 1;
    }
    const QJsonArray appliedMemories = readJsonArray(memoryPath);
    if (appliedMemories.size() != 2
        || appliedMemories.at(0).toObject().value(QStringLiteral("id")).toString() != QStringLiteral("memory-existing")
        || appliedMemories.at(1).toObject().value(QStringLiteral("id")).toString() == QStringLiteral("memory-existing")
        || appliedMemories.at(1).toObject().value(QStringLiteral("content")).toString() != QStringLiteral("new memory content")
        || appliedMemories.at(1).toObject().value(QStringLiteral("unknown_memory_field")).toString() != QStringLiteral("memory-stays")
        || mergedMemoryBeforePreview != readBytes(mergedMemoryPath)
        || outlineBeforePreview != readBytes(memoryOutlinePath)) {
        return fail(QStringLiteral("memory apply should append only to current role memories and leave merged memory files untouched")) ? 0 : 1;
    }

    QTemporaryDir legacyMemoryTempDir;
    if (!legacyMemoryTempDir.isValid()) {
        return fail(QStringLiteral("failed to create legacy memory temporary directory")) ? 0 : 1;
    }
    QDir legacyRoot(legacyMemoryTempDir.path());
    if (!legacyRoot.mkpath(QStringLiteral("data"))) {
        return fail(QStringLiteral("failed to create legacy memory data directory")) ? 0 : 1;
    }
    const QString legacyCurrentCardPath = legacyRoot.absoluteFilePath(QStringLiteral("data/current_role_card.json"));
    const QString legacyMemoriesPath = legacyRoot.absoluteFilePath(QStringLiteral("data/memories.json"));
    const QString unexpectedPrimaryMemoryPath = legacyRoot.absoluteFilePath(QStringLiteral("data/card_runtime/cards/legacy-card/memories.json"));
    if (!writeJson(legacyCurrentCardPath, QJsonObject{
            { QStringLiteral("raw"), QJsonObject{
                { QStringLiteral("uid"), QStringLiteral("Legacy Card") },
                { QStringLiteral("name"), QStringLiteral("Legacy Runtime Role") },
            } },
        })
        || !writeJsonDocument(legacyMemoriesPath, QJsonDocument(QJsonArray{
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("legacy-existing") },
                { QStringLiteral("content"), QStringLiteral("legacy memory content") },
            },
        }))) {
        return fail(QStringLiteral("failed to write legacy memory fallback fixtures")) ? 0 : 1;
    }
    CardAuthoringService legacyMemoryService(legacyMemoryTempDir.path());
    const QJsonObject legacyMemoryPreview = legacyMemoryService.buildApplyPreview(project, { QStringLiteral("memory") });
    const QJsonArray legacyMemoryGroups = legacyMemoryPreview.value(QStringLiteral("groups")).toArray();
    const QJsonArray legacyMemoryChanges = legacyMemoryGroups.first().toObject().value(QStringLiteral("changes")).toArray();
    if (!legacyMemoryPreview.value(QStringLiteral("ok")).toBool()
        || legacyMemoryChanges.first().toObject().value(QStringLiteral("path")).toString() != QStringLiteral("data/memories.json")
        || QFileInfo::exists(unexpectedPrimaryMemoryPath)) {
        return fail(QStringLiteral("memory preview should fall back to legacy data/memories.json when per-card memories are absent")) ? 0 : 1;
    }
    const QJsonObject legacyMemoryApply = legacyMemoryService.applySelected(project, { QStringLiteral("memory") });
    const QJsonArray legacyAppliedMemories = readJsonArray(legacyMemoriesPath);
    if (!legacyMemoryApply.value(QStringLiteral("ok")).toBool()
        || legacyMemoryApply.value(QStringLiteral("backups")).toArray().isEmpty()
        || legacyAppliedMemories.size() != 2
        || legacyAppliedMemories.at(0).toObject().value(QStringLiteral("id")).toString() != QStringLiteral("legacy-existing")
        || legacyAppliedMemories.at(1).toObject().value(QStringLiteral("content")).toString() != QStringLiteral("new memory content")
        || QFileInfo::exists(unexpectedPrimaryMemoryPath)) {
        return fail(QStringLiteral("memory apply should use legacy data/memories.json fallback and avoid creating a per-card memory file")) ? 0 : 1;
    }

    return 0;
}
