#include "fantarealbridge.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QHash>
#include <QHostAddress>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <QList>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>
#include <QUrl>
#include <QVariantList>
#include <QVariantMap>

#include <iostream>

namespace {
bool fail(const QString& message) {
    std::cerr << message.toStdString() << '\n';
    return false;
}

bool writeJson(const QString& path, const QJsonDocument& document) {
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return false;
    }
    return file.write(document.toJson(QJsonDocument::Indented)) > 0;
}

QJsonObject readJsonObject(const QString& path) {
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

QByteArray readFileBytes(const QString& path) {
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

QJsonObject findByKey(const QJsonArray& items, const QString& key, const QString& value) {
    for (const QJsonValue& itemValue : items) {
        const QJsonObject item = itemValue.toObject();
        if (item.value(key).toString() == value) {
            return item;
        }
    }
    return {};
}

bool jsonArrayContainsString(const QJsonArray& items, const QString& value) {
    for (const QJsonValue& item : items) {
        if (item.toString() == value) {
            return true;
        }
    }
    return false;
}

QVariantMap findVariantMapByValue(const QVariantList& items, const QString& key, const QString& value) {
    for (const QVariant& itemValue : items) {
        const QVariantMap item = itemValue.toMap();
        if (item.value(key).toString() == value) {
            return item;
        }
    }
    return {};
}

bool variantListContainsFilename(const QVariantList& items, const QString& filename) {
    for (const QVariant& value : items) {
        if (value.toMap().value(QStringLiteral("filename")).toString() == filename) {
            return true;
        }
    }
    return false;
}

bool variantListContainsExternalTag(const QVariantList& items, const QString& trigger) {
    for (const QVariant& value : items) {
        const QVariantMap item = value.toMap();
        if (item.value(QStringLiteral("entry_type")).toString() == QStringLiteral("external_tag")
            && item.value(QStringLiteral("trigger")).toString() == trigger) {
            return true;
        }
    }
    return false;
}

bool variantListContainsCandidateAfterExternalTag(const QVariantList& items, const QString& trigger) {
    for (const QVariant& value : items) {
        const QVariantMap after = value.toMap().value(QStringLiteral("after")).toMap();
        if (after.value(QStringLiteral("entry_type")).toString() == QStringLiteral("external_tag")
            && after.value(QStringLiteral("trigger")).toString() == trigger) {
            return true;
        }
    }
    return false;
}

int contentLengthFromHeader(const QByteArray& header) {
    const QList<QByteArray> lines = header.split('\n');
    for (QByteArray line : lines) {
        line = line.trimmed();
        if (line.toLower().startsWith("content-length:")) {
            return line.mid(line.indexOf(':') + 1).trimmed().toInt();
        }
    }
    return 0;
}

bool makeFixture(const QDir& root) {
    const QStringList dirs = {
        QStringLiteral("data"),
        QStringLiteral("data/auto_saga"),
        QStringLiteral("data/card_runtime/cards/card-123"),
        QStringLiteral("data/logs"),
        QStringLiteral("cards"),
    };
    for (const QString& dir : dirs) {
        if (!root.mkpath(dir)) {
            return false;
        }
    }

    const QHash<QString, QJsonValue> jsonFiles = {
        { QStringLiteral("data/settings.json"), QJsonObject{} },
        { QStringLiteral("data/route_forwarding.json"), QJsonObject{} },
        { QStringLiteral("data/preset.json"), QJsonObject{
            { QStringLiteral("active_preset_id"), QStringLiteral("base") },
            { QStringLiteral("presets"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("base") },
                    { QStringLiteral("name"), QStringLiteral("Base") },
                    { QStringLiteral("enabled"), true },
                    { QStringLiteral("base_system_prompt"), QStringLiteral("KEEP BRIDGE BASE") },
                    { QStringLiteral("modules"), QJsonObject{} },
                    { QStringLiteral("extra_prompts"), QJsonArray{} },
                    { QStringLiteral("prompt_groups"), QJsonArray{} },
                },
            } },
        } },
        { QStringLiteral("data/worldbook.json"), QJsonObject{
            { QStringLiteral("settings"), QJsonObject{ { QStringLiteral("enabled"), true } } },
            { QStringLiteral("entries"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("id"), QStringLiteral("runtime-worldbook") },
                    { QStringLiteral("title"), QStringLiteral("Runtime Lore") },
                    { QStringLiteral("trigger"), QStringLiteral("runtime lore") },
                    { QStringLiteral("content"), QStringLiteral("runtime worldbook content") },
                    { QStringLiteral("enabled"), true },
                },
            } },
        } },
        { QStringLiteral("data/worldbook_runtime_state.json"), QJsonObject{} },
        { QStringLiteral("data/creative_workshop_state.json"), QJsonObject{} },
        { QStringLiteral("data/persona.json"), QJsonObject{} },
        { QStringLiteral("data/user_profile.json"), QJsonObject{} },
        { QStringLiteral("data/auto_saga/state.json"), QJsonObject{} },
        { QStringLiteral("data/conversations.json"), QJsonArray{} },
        { QStringLiteral("cards/template_single_role_card.json"), QJsonObject{} },
        { QStringLiteral("cards/template_multi_role_card.json"), QJsonObject{} },
    };
    for (auto it = jsonFiles.constBegin(); it != jsonFiles.constEnd(); ++it) {
        const QJsonDocument document = it.value().isArray()
            ? QJsonDocument(it.value().toArray())
            : QJsonDocument(it.value().toObject());
        if (!writeJson(root.absoluteFilePath(it.key()), document)) {
            return false;
        }
    }
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/card_runtime/cards/card-123/memories.json")),
            QJsonDocument(QJsonArray{ QJsonObject{
                { QStringLiteral("id"), QStringLiteral("memory-existing") },
                { QStringLiteral("title"), QStringLiteral("Existing Memory") },
                { QStringLiteral("content"), QStringLiteral("existing memory") },
                { QStringLiteral("memory_status"), QStringLiteral("active") },
            } }))
        || !writeJson(root.absoluteFilePath(QStringLiteral("data/card_runtime/cards/card-123/merged_memories.json")),
            QJsonDocument(QJsonArray{ QJsonObject{ { QStringLiteral("id"), QStringLiteral("merged-stays") } } }))
        || !writeJson(root.absoluteFilePath(QStringLiteral("data/card_runtime/cards/card-123/memory_outline.json")),
            QJsonDocument(QJsonArray{ QJsonObject{ { QStringLiteral("id"), QStringLiteral("outline-stays") } } }))) {
        return false;
    }

    QJsonObject stateJournal;
    stateJournal.insert(QStringLiteral("enabled"), false);
    stateJournal.insert(QStringLiteral("version"), 1);
    stateJournal.insert(QStringLiteral("unknown_state_field"), QStringLiteral("state-stays"));
    stateJournal.insert(QStringLiteral("roles"), QJsonArray{
        QJsonObject{
            { QStringLiteral("role_id"), QStringLiteral("main") },
            { QStringLiteral("role_name"), QStringLiteral("Main Role") },
            { QStringLiteral("variables"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("var_key"), QStringLiteral("trust") },
                    { QStringLiteral("var_name"), QStringLiteral("Trust") },
                    { QStringLiteral("default_value"), 5 },
                    { QStringLiteral("instruction"), QStringLiteral("legacy trust variable") },
                },
            } },
            { QStringLiteral("stages"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("stage_key"), QStringLiteral("bonded") },
                    { QStringLiteral("stage_name"), QStringLiteral("Bonded") },
                    { QStringLiteral("conditions"), QJsonArray{
                        QJsonObject{
                            { QStringLiteral("var"), QStringLiteral("trust") },
                            { QStringLiteral("op"), QStringLiteral(">=") },
                            { QStringLiteral("value"), 5 },
                        },
                    } },
                    { QStringLiteral("activation_tag"), QStringLiteral("state_journal.stage.main.bonded") },
                },
            } },
        },
    });

    QJsonObject raw;
    raw.insert(QStringLiteral("name"), QStringLiteral("Old Name"));
    raw.insert(QStringLiteral("description"), QStringLiteral("old description"));
    raw.insert(QStringLiteral("stateJournal"), stateJournal);
    raw.insert(QStringLiteral("unknown_raw_field"), QStringLiteral("raw-stays"));

    QJsonObject card;
    card.insert(QStringLiteral("source_name"), QStringLiteral("current-card.json"));
    card.insert(QStringLiteral("card_uid"), QStringLiteral("card-123"));
    card.insert(QStringLiteral("raw"), raw);
    return writeJson(root.absoluteFilePath(QStringLiteral("data/current_role_card.json")), QJsonDocument(card));
}

QVariantMap buildProject(const QVariantMap& baseDraft) {
    QVariantMap project = baseDraft;
    project.insert(QStringLiteral("title"), QStringLiteral("Bridge Authored Card"));

    QVariantMap persona;
    persona.insert(QStringLiteral("name"), QStringLiteral("New Name"));
    persona.insert(QStringLiteral("description"), QStringLiteral("new description"));
    persona.insert(QStringLiteral("personality"), QStringLiteral("new personality"));
    persona.insert(QStringLiteral("scenario"), QStringLiteral("new scenario"));
    persona.insert(QStringLiteral("first_mes"), QStringLiteral("new first"));
    persona.insert(QStringLiteral("mes_example"), QStringLiteral("new example dialogue"));
    persona.insert(QStringLiteral("creator_notes"), QStringLiteral("new hidden rules"));
    persona.insert(QStringLiteral("tags"), QVariantList{ QStringLiteral("alpha"), QStringLiteral("beta") });
    persona.insert(QStringLiteral("creativeWorkshop"), QVariantMap{
        { QStringLiteral("enabled"), true },
        { QStringLiteral("items"), QVariantList{
            QVariantMap{
                { QStringLiteral("id"), QStringLiteral("bridge-workshop") },
                { QStringLiteral("name"), QStringLiteral("Bridge Workshop") },
                { QStringLiteral("enabled"), true },
                { QStringLiteral("triggerMode"), QStringLiteral("manual") },
                { QStringLiteral("triggerStage"), QStringLiteral("database.stage.role-1.trust") },
                { QStringLiteral("triggerTempMin"), 0 },
                { QStringLiteral("triggerTempMax"), 1 },
                { QStringLiteral("actionType"), QStringLiteral("note") },
                { QStringLiteral("popupTitle"), QStringLiteral("Bridge Popup") },
                { QStringLiteral("musicPreset"), QStringLiteral("piano") },
                { QStringLiteral("musicUrl"), QStringLiteral("https://example.test/music.mp3") },
                { QStringLiteral("autoplay"), false },
                { QStringLiteral("loop"), true },
                { QStringLiteral("volume"), 0.6 },
                { QStringLiteral("imageUrl"), QStringLiteral("https://example.test/image.png") },
                { QStringLiteral("imageAlt"), QStringLiteral("bridge image") },
                { QStringLiteral("note"), QStringLiteral("bridge workshop note") },
            },
        } },
    });
    persona.insert(QStringLiteral("personas"), QVariantMap{
        { QStringLiteral("2"), QVariantMap{
            { QStringLiteral("name"), QStringLiteral("Bridge Side") },
            { QStringLiteral("description"), QStringLiteral("bridge side description") },
            { QStringLiteral("personality"), QStringLiteral("bridge side personality") },
            { QStringLiteral("scenario"), QStringLiteral("bridge side scenario") },
            { QStringLiteral("creator_notes"), QStringLiteral("bridge side notes") },
            { QStringLiteral("tags"), QVariantList{ QStringLiteral("side"), QStringLiteral("bridge") } },
        } },
    });
    project.insert(QStringLiteral("persona_card"), persona);

    QVariantMap variable;
    variable.insert(QStringLiteral("id"), QStringLiteral("db_var_affection"));
    variable.insert(QStringLiteral("key"), QStringLiteral("affection"));
    variable.insert(QStringLiteral("label"), QStringLiteral("Affection"));
    variable.insert(QStringLiteral("value_type"), QStringLiteral("number"));
    variable.insert(QStringLiteral("scope"), QStringLiteral("role-1"));
    variable.insert(QStringLiteral("initial_value"), QStringLiteral("0"));
    variable.insert(QStringLiteral("write_policy"), QStringLiteral("manual_review"));
    variable.insert(QStringLiteral("description"), QStringLiteral("relationship score"));
    variable.insert(QStringLiteral("notes"), QStringLiteral("affection note"));

    QVariantMap stage;
    stage.insert(QStringLiteral("id"), QStringLiteral("db_stage_trust"));
    stage.insert(QStringLiteral("role_id"), QStringLiteral("role-1"));
    stage.insert(QStringLiteral("stage_key"), QStringLiteral("trust"));
    stage.insert(QStringLiteral("title"), QStringLiteral("Trust"));
    stage.insert(QStringLiteral("condition"), QStringLiteral("affection >= 10"));
    stage.insert(QStringLiteral("active_tag"), QStringLiteral("state_journal.stage.role-1.trust"));
    stage.insert(QStringLiteral("emits_tags"), QVariantList{
        QStringLiteral("state_journal.stage.role-1.trust"),
        QStringLiteral("database.tag.bridge-signal"),
    });
    stage.insert(QStringLiteral("description"), QStringLiteral("trust stage description"));
    stage.insert(QStringLiteral("notes"), QStringLiteral("trust stage note"));

    QVariantMap snapshotField;
    snapshotField.insert(QStringLiteral("id"), QStringLiteral("db_snapshot_mood"));
    snapshotField.insert(QStringLiteral("role_id"), QStringLiteral("role-1"));
    snapshotField.insert(QStringLiteral("key"), QStringLiteral("mood"));
    snapshotField.insert(QStringLiteral("label"), QStringLiteral("Mood"));
    snapshotField.insert(QStringLiteral("enabled"), true);
    snapshotField.insert(QStringLiteral("display"), true);
    snapshotField.insert(QStringLiteral("instruction"), QStringLiteral("Summarize the visible mood for the state record."));
    snapshotField.insert(QStringLiteral("notes"), QStringLiteral("mood snapshot note"));

    QVariantMap databaseTag;
    databaseTag.insert(QStringLiteral("id"), QStringLiteral("db_tag_lore"));
    databaseTag.insert(QStringLiteral("tag"), QStringLiteral("database.tag.bridge-lore"));
    databaseTag.insert(QStringLiteral("title"), QStringLiteral("Bridge Lore Tag"));
    databaseTag.insert(QStringLiteral("trigger"), QStringLiteral("bridge lore trigger"));
    databaseTag.insert(QStringLiteral("target"), QStringLiteral("worldbook"));
    databaseTag.insert(QStringLiteral("description"), QStringLiteral("bridge lore tag description"));
    databaseTag.insert(QStringLiteral("notes"), QStringLiteral("bridge lore tag note"));

    QVariantMap database;
    database.insert(QStringLiteral("enabled"), true);
    database.insert(QStringLiteral("notes"), QStringLiteral("bridge test database draft"));
    database.insert(QStringLiteral("variables"), QVariantList{ variable });
    database.insert(QStringLiteral("stages"), QVariantList{ stage });
    database.insert(QStringLiteral("snapshotFields"), QVariantList{ snapshotField });
    database.insert(QStringLiteral("tags"), QVariantList{ databaseTag });
    project.insert(QStringLiteral("database"), database);
    QVariantMap worldbookEntry;
    worldbookEntry.insert(QStringLiteral("id"), QStringLiteral("bridge-worldbook"));
    worldbookEntry.insert(QStringLiteral("title"), QStringLiteral("Bridge Lore"));
    worldbookEntry.insert(QStringLiteral("trigger"), QStringLiteral("bridge lore"));
    worldbookEntry.insert(QStringLiteral("content"), QStringLiteral("bridge worldbook content"));
    project.insert(QStringLiteral("worldbook"), QVariantMap{
        { QStringLiteral("entries"), QVariantList{ worldbookEntry } },
    });
    QVariantMap preset;
    QVariantMap modules;
    modules.insert(QStringLiteral("short_paragraph"), true);
    preset.insert(QStringLiteral("modules"), modules);
    preset.insert(QStringLiteral("extra_prompts"), QVariantList{
        QVariantMap{
            { QStringLiteral("id"), QStringLiteral("bridge-extra") },
            { QStringLiteral("name"), QStringLiteral("Bridge Extra") },
            { QStringLiteral("content"), QStringLiteral("bridge extra prompt") },
            { QStringLiteral("enabled"), true },
        },
    });
    preset.insert(QStringLiteral("prompt_groups"), QVariantList{
        QVariantMap{
            { QStringLiteral("id"), QStringLiteral("bridge-group") },
            { QStringLiteral("name"), QStringLiteral("Bridge Group") },
            { QStringLiteral("enabled"), true },
            { QStringLiteral("prompts"), QVariantList{ QStringLiteral("bridge-extra") } },
        },
    });
    project.insert(QStringLiteral("preset"), preset);
    project.insert(QStringLiteral("memory"), QVariantMap{
        { QStringLiteral("items"), QVariantList{
            QVariantMap{
                { QStringLiteral("id"), QStringLiteral("bridge-memory") },
                { QStringLiteral("title"), QStringLiteral("Bridge Memory") },
                { QStringLiteral("content"), QStringLiteral("bridge memory content") },
                { QStringLiteral("tags"), QVariantList{ QStringLiteral("bridge") } },
                { QStringLiteral("notes"), QStringLiteral("bridge memory note") },
                { QStringLiteral("memory_status"), QStringLiteral("active") },
            },
        } },
    });
    return project;
}
}

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);

    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        return fail(QStringLiteral("failed to create temporary directory")) ? 0 : 1;
    }

    QDir root(tempDir.path());
    if (!makeFixture(root)) {
        return fail(QStringLiteral("failed to create card authoring bridge fixture")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;
    const QVariantMap initialDraft = bridge.cardAuthoringDraft();
    if (initialDraft.value(QStringLiteral("type")).toString() != QStringLiteral("fantareal_card_authoring_project")) {
        return fail(QStringLiteral("bridge should expose a normalized card authoring draft")) ? 0 : 1;
    }

    const QVariantMap project = buildProject(initialDraft);
    const QVariantMap saveResult = bridge.saveCardAuthoringWorkspace(project);
    if (!saveResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("saveCardAuthoringWorkspace failed: %1").arg(saveResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (!QFileInfo::exists(root.absoluteFilePath(QStringLiteral("data/card_authoring/workspace.cardwork.json")))) {
        return fail(QStringLiteral("workspace.cardwork.json should be created")) ? 0 : 1;
    }
    if (bridge.cardAuthoringDraft().value(QStringLiteral("title")).toString() != QStringLiteral("Bridge Authored Card")) {
        return fail(QStringLiteral("bridge cardAuthoringDraft should refresh after workspace save")) ? 0 : 1;
    }
    const QVariantMap savedProjectResult = bridge.saveCardAuthoringProject(QStringLiteral("Bridge Project"), project);
    if (!savedProjectResult.value(QStringLiteral("ok")).toBool()
        || !QFileInfo::exists(savedProjectResult.value(QStringLiteral("savedPath")).toString())
        || bridge.cardAuthoringProjectItems().isEmpty()) {
        return fail(QStringLiteral("saveCardAuthoringProject should save and refresh project items")) ? 0 : 1;
    }
    const QString savedProjectFilename = QFileInfo(savedProjectResult.value(QStringLiteral("savedPath")).toString()).fileName();
    const QVariantMap loadedProjectResult = bridge.loadCardAuthoringProject(savedProjectFilename);
    if (!loadedProjectResult.value(QStringLiteral("ok")).toBool()
        || bridge.cardAuthoringDraft().value(QStringLiteral("title")).toString() != QStringLiteral("Bridge Authored Card")) {
        return fail(QStringLiteral("loadCardAuthoringProject should load saved project through bridge")) ? 0 : 1;
    }
    const QVariantMap refreshProjectsResult = bridge.refreshCardAuthoringProjects();
    if (!refreshProjectsResult.value(QStringLiteral("ok")).toBool()
        || refreshProjectsResult.value(QStringLiteral("count")).toInt() <= 0) {
        return fail(QStringLiteral("refreshCardAuthoringProjects should expose project count")) ? 0 : 1;
    }
    const QString exportProjectPath = root.absoluteFilePath(QStringLiteral("bridge-export"));
    const QVariantMap exportProjectResult = bridge.exportCardAuthoringProjectFile(QUrl::fromLocalFile(exportProjectPath).toString(), project);
    const QString exportedPath = exportProjectResult.value(QStringLiteral("exportedPath")).toString();
    const QVariantMap defaultExportProjectResult = bridge.exportCardAuthoringProjectToDefaultDir(project);
    const QString defaultExportedPath = defaultExportProjectResult.value(QStringLiteral("exportedPath")).toString();
    if (!exportProjectResult.value(QStringLiteral("ok")).toBool()
        || !exportedPath.endsWith(QStringLiteral("bridge-export.cardwork.json"))
        || !QFileInfo::exists(exportedPath)
        || !defaultExportProjectResult.value(QStringLiteral("ok")).toBool()
        || !defaultExportedPath.contains(QStringLiteral("data/card_authoring/exports"))
        || !defaultExportedPath.endsWith(QStringLiteral(".cardwork.json"))
        || !QFileInfo::exists(defaultExportedPath)
        || readJsonObject(exportedPath).value(QStringLiteral("type")).toString() != QStringLiteral("fantareal_card_authoring_project")
        || bridge.cardAuthoringDraft().value(QStringLiteral("title")).toString() != QStringLiteral("Bridge Authored Card")) {
        return fail(QStringLiteral("card authoring project export should write explicit and default .cardwork.json files")) ? 0 : 1;
    }
    const QString cardPath = root.absoluteFilePath(QStringLiteral("data/current_role_card.json"));
    const QByteArray beforeCompileCard = readFileBytes(cardPath);
    const QVariantMap emptyValidation = bridge.validateCardAuthoringDraft(QVariantMap{});
    const QVariantMap validation = bridge.validateCardAuthoringDraft(project);
    const QVariantMap compiledRoleCard = bridge.compileCardAuthoringDraft(project);
    const QVariantMap compiledSummary = compiledRoleCard.value(QStringLiteral("summary")).toMap();
    const QVariantMap compiledRaw = compiledRoleCard.value(QStringLiteral("raw")).toMap();
    const QVariantMap compiledPersonas = compiledRaw.value(QStringLiteral("personas")).toMap();
    const QVariantMap compiledSidePersona = compiledPersonas.value(QStringLiteral("2")).toMap();
    const QVariantList compiledWorkshopItems = compiledRaw.value(QStringLiteral("creativeWorkshop")).toMap().value(QStringLiteral("items")).toList();
    const QVariantMap compiledStateJournal = compiledRaw.value(QStringLiteral("stateJournal")).toMap();
    const QVariantMap compiledDatabaseDraft = compiledStateJournal.value(QStringLiteral("databaseDraft")).toMap();
    const QVariantMap compiledDatabaseVariable = findVariantMapByValue(
        compiledDatabaseDraft.value(QStringLiteral("variables")).toList(),
        QStringLiteral("id"),
        QStringLiteral("db_var_affection"));
    const QVariantMap compiledDatabaseStage = findVariantMapByValue(
        compiledDatabaseDraft.value(QStringLiteral("stages")).toList(),
        QStringLiteral("id"),
        QStringLiteral("db_stage_trust"));
    const QVariantMap compiledDatabaseSnapshot = findVariantMapByValue(
        compiledDatabaseDraft.value(QStringLiteral("snapshotFields")).toList(),
        QStringLiteral("id"),
        QStringLiteral("db_snapshot_mood"));
    const QVariantMap compiledDatabaseTag = findVariantMapByValue(
        compiledDatabaseDraft.value(QStringLiteral("tags")).toList(),
        QStringLiteral("id"),
        QStringLiteral("db_tag_lore"));
    const QString compiledExportTarget = root.absoluteFilePath(QStringLiteral("compiled-bridge-role"));
    const QVariantMap compiledExport = bridge.exportCompiledCardAuthoringRoleCardFile(
        QUrl::fromLocalFile(compiledExportTarget).toString(),
        project);
    const QString compiledExportedPath = compiledExport.value(QStringLiteral("exportedPath")).toString();
    const QVariantMap defaultCompiledExport = bridge.exportCompiledCardAuthoringRoleCardToDefaultDir(project);
    const QString defaultCompiledExportedPath = defaultCompiledExport.value(QStringLiteral("exportedPath")).toString();
    const QJsonObject exportedCompiledCard = readJsonObject(compiledExportedPath);
    const QJsonObject defaultExportedCompiledCard = readJsonObject(defaultCompiledExportedPath);
    const QJsonObject exportedDatabaseDraft = exportedCompiledCard.value(QStringLiteral("raw")).toObject()
        .value(QStringLiteral("stateJournal")).toObject()
        .value(QStringLiteral("databaseDraft")).toObject();
    const QJsonObject exportedDatabaseVariable = findById(
        exportedDatabaseDraft.value(QStringLiteral("variables")).toArray(),
        QStringLiteral("db_var_affection"));
    const QJsonObject exportedDatabaseStage = findById(
        exportedDatabaseDraft.value(QStringLiteral("stages")).toArray(),
        QStringLiteral("db_stage_trust"));
    const QJsonObject exportedDatabaseSnapshot = findById(
        exportedDatabaseDraft.value(QStringLiteral("snapshotFields")).toArray(),
        QStringLiteral("db_snapshot_mood"));
    const QJsonObject exportedDatabaseTag = findById(
        exportedDatabaseDraft.value(QStringLiteral("tags")).toArray(),
        QStringLiteral("db_tag_lore"));
    if (!emptyValidation.value(QStringLiteral("ok")).toBool()
        || emptyValidation.value(QStringLiteral("warning_count")).toInt() < 2
        || !validation.value(QStringLiteral("ok")).toBool()
        || validation.value(QStringLiteral("warning_count")).toInt() != 0
        || !compiledRoleCard.value(QStringLiteral("ok")).toBool()
        || compiledSummary.value(QStringLiteral("name")).toString() != QStringLiteral("New Name")
        || compiledSummary.value(QStringLiteral("variable_count")).toInt() != 1
        || compiledSummary.value(QStringLiteral("stage_count")).toInt() != 1
        || compiledSummary.value(QStringLiteral("snapshot_field_count")).toInt() != 1
        || compiledSummary.value(QStringLiteral("database_tag_count")).toInt() != 1
        || compiledRaw.value(QStringLiteral("name")).toString() != QStringLiteral("New Name")
        || compiledRaw.value(QStringLiteral("mes_example")).toString() != QStringLiteral("new example dialogue")
        || compiledRaw.value(QStringLiteral("creator_notes")).toString() != QStringLiteral("new hidden rules")
        || compiledWorkshopItems.isEmpty()
        || compiledWorkshopItems.first().toMap().value(QStringLiteral("note")).toString() != QStringLiteral("bridge workshop note")
        || compiledWorkshopItems.first().toMap().value(QStringLiteral("loop")).toBool() != true
        || compiledSidePersona.value(QStringLiteral("description")).toString() != QStringLiteral("bridge side description")
        || compiledSidePersona.value(QStringLiteral("personality")).toString() != QStringLiteral("bridge side personality")
        || compiledSidePersona.value(QStringLiteral("scenario")).toString() != QStringLiteral("bridge side scenario")
        || compiledSidePersona.value(QStringLiteral("creator_notes")).toString() != QStringLiteral("bridge side notes")
        || !compiledSidePersona.value(QStringLiteral("tags")).toList().contains(QStringLiteral("side"))
        || compiledDatabaseVariable.value(QStringLiteral("value_type")).toString() != QStringLiteral("number")
        || compiledDatabaseVariable.value(QStringLiteral("write_policy")).toString() != QStringLiteral("manual_review")
        || compiledDatabaseVariable.value(QStringLiteral("notes")).toString() != QStringLiteral("affection note")
        || compiledDatabaseStage.value(QStringLiteral("active_tag")).toString() != QStringLiteral("database.stage.role-1.trust")
        || !compiledDatabaseStage.value(QStringLiteral("emits_tags")).toList().contains(QStringLiteral("database.tag.bridge-signal"))
        || compiledDatabaseStage.value(QStringLiteral("notes")).toString() != QStringLiteral("trust stage note")
        || compiledDatabaseSnapshot.value(QStringLiteral("label")).toString() != QStringLiteral("Mood")
        || compiledDatabaseSnapshot.value(QStringLiteral("instruction")).toString() != QStringLiteral("Summarize the visible mood for the state record.")
        || compiledDatabaseTag.value(QStringLiteral("trigger")).toString() != QStringLiteral("bridge lore trigger")
        || compiledDatabaseTag.value(QStringLiteral("notes")).toString() != QStringLiteral("bridge lore tag note")
        || !compiledExport.value(QStringLiteral("ok")).toBool()
        || !compiledExportedPath.endsWith(QStringLiteral("compiled-bridge-role.json"))
        || !QFileInfo::exists(compiledExportedPath)
        || !defaultCompiledExport.value(QStringLiteral("ok")).toBool()
        || !defaultCompiledExportedPath.contains(QStringLiteral("data/card_authoring/exports"))
        || !QFileInfo::exists(defaultCompiledExportedPath)
        || exportedCompiledCard.value(QStringLiteral("raw")).toObject().value(QStringLiteral("name")).toString() != QStringLiteral("New Name")
        || defaultExportedCompiledCard.value(QStringLiteral("raw")).toObject().value(QStringLiteral("name")).toString() != QStringLiteral("New Name")
        || exportedCompiledCard.value(QStringLiteral("raw")).toObject().value(QStringLiteral("mes_example")).toString() != QStringLiteral("new example dialogue")
        || exportedCompiledCard.value(QStringLiteral("raw")).toObject().value(QStringLiteral("creator_notes")).toString() != QStringLiteral("new hidden rules")
        || exportedCompiledCard.value(QStringLiteral("raw")).toObject().value(QStringLiteral("creativeWorkshop")).toObject().value(QStringLiteral("items")).toArray().first().toObject().value(QStringLiteral("musicPreset")).toString() != QStringLiteral("piano")
        || exportedCompiledCard.value(QStringLiteral("raw")).toObject().value(QStringLiteral("personas")).toObject().value(QStringLiteral("2")).toObject().value(QStringLiteral("scenario")).toString() != QStringLiteral("bridge side scenario")
        || exportedDatabaseVariable.value(QStringLiteral("value_type")).toString() != QStringLiteral("number")
        || exportedDatabaseStage.value(QStringLiteral("active_tag")).toString() != QStringLiteral("database.stage.role-1.trust")
        || !jsonArrayContainsString(exportedDatabaseStage.value(QStringLiteral("emits_tags")).toArray(), QStringLiteral("database.tag.bridge-signal"))
        || exportedDatabaseSnapshot.value(QStringLiteral("label")).toString() != QStringLiteral("Mood")
        || exportedDatabaseTag.value(QStringLiteral("description")).toString() != QStringLiteral("bridge lore tag description")
        || beforeCompileCard != readFileBytes(cardPath)) {
        return fail(QStringLiteral("compile/export/validate bridge APIs should expose compiled role card JSON without writing runtime files")) ? 0 : 1;
    }
    const QVariantMap promptPack = bridge.buildCardAuthoringPromptPack(QStringLiteral("deep"));
    if (!promptPack.value(QStringLiteral("ok")).toBool()
        || promptPack.value(QStringLiteral("thinking_mode")).toString() != QStringLiteral("deep")
        || promptPack.value(QStringLiteral("file_count")).toInt() <= 7
        || !variantListContainsFilename(promptPack.value(QStringLiteral("prompt_files")).toList(), QStringLiteral("fa_container_deep_router.md"))
        || promptPack.value(QStringLiteral("system_prompt")).toString().isEmpty()) {
        return fail(QStringLiteral("buildCardAuthoringPromptPack should expose deep prompt pack through bridge")) ? 0 : 1;
    }

    const QString workspacePath = root.absoluteFilePath(QStringLiteral("data/card_authoring/workspace.cardwork.json"));
    const QByteArray beforeRuntimeLoadCard = readFileBytes(cardPath);
    const QByteArray beforeRuntimeLoadWorkspace = readFileBytes(workspacePath);
    const QVariantMap runtimeLoadResult = bridge.loadCurrentRuntimeCardAuthoringDraft();
    const QByteArray afterRuntimeLoadCard = readFileBytes(cardPath);
    const QByteArray afterRuntimeLoadWorkspace = readFileBytes(workspacePath);
    const QVariantMap runtimeProject = runtimeLoadResult.value(QStringLiteral("project")).toMap();
    const QVariantMap runtimePersona = runtimeProject.value(QStringLiteral("persona_card")).toMap();
    const QVariantMap runtimeDatabase = runtimeProject.value(QStringLiteral("database")).toMap();
    const QVariantMap runtimeVariable = findVariantMapByValue(
        runtimeDatabase.value(QStringLiteral("variables")).toList(),
        QStringLiteral("key"),
        QStringLiteral("trust"));
    const QVariantMap runtimeStage = findVariantMapByValue(
        runtimeDatabase.value(QStringLiteral("stages")).toList(),
        QStringLiteral("stage_key"),
        QStringLiteral("bonded"));
    const QVariantMap runtimeTag = findVariantMapByValue(
        runtimeDatabase.value(QStringLiteral("tags")).toList(),
        QStringLiteral("tag"),
        QStringLiteral("database.stage.main.bonded"));
    const QVariantMap runtimeWorldbook = findVariantMapByValue(
        runtimeProject.value(QStringLiteral("worldbook")).toMap().value(QStringLiteral("entries")).toList(),
        QStringLiteral("id"),
        QStringLiteral("runtime-worldbook"));
    const QVariantMap runtimePreset = findVariantMapByValue(
        runtimeProject.value(QStringLiteral("preset")).toMap().value(QStringLiteral("presets")).toList(),
        QStringLiteral("id"),
        QStringLiteral("base"));
    const QVariantMap runtimeMemory = findVariantMapByValue(
        runtimeProject.value(QStringLiteral("memory")).toMap().value(QStringLiteral("items")).toList(),
        QStringLiteral("id"),
        QStringLiteral("memory-existing"));
    if (!runtimeLoadResult.value(QStringLiteral("ok")).toBool()
        || runtimePersona.value(QStringLiteral("name")).toString() != QStringLiteral("Old Name")
        || runtimeDatabase.value(QStringLiteral("enabled")).toBool()
        || runtimeVariable.value(QStringLiteral("label")).toString() != QStringLiteral("Trust")
        || runtimeVariable.value(QStringLiteral("initial_value")).toString() != QStringLiteral("5")
        || runtimeStage.value(QStringLiteral("role_id")).toString() != QStringLiteral("main")
        || runtimeStage.value(QStringLiteral("condition")).toString() != QStringLiteral("trust >= 5")
        || runtimeStage.value(QStringLiteral("active_tag")).toString() != QStringLiteral("database.stage.main.bonded")
        || runtimeTag.value(QStringLiteral("target")).toString() != QStringLiteral("worldbook")
        || runtimeWorldbook.value(QStringLiteral("content")).toString() != QStringLiteral("runtime worldbook content")
        || runtimeProject.value(QStringLiteral("preset")).toMap().value(QStringLiteral("active_preset_id")).toString() != QStringLiteral("base")
        || runtimePreset.value(QStringLiteral("base_system_prompt")).toString() != QStringLiteral("KEEP BRIDGE BASE")
        || runtimeMemory.value(QStringLiteral("content")).toString() != QStringLiteral("existing memory")
        || bridge.cardAuthoringDraft().value(QStringLiteral("persona_card")).toMap().value(QStringLiteral("name")).toString() != QStringLiteral("Old Name")
        || beforeRuntimeLoadCard != afterRuntimeLoadCard
        || beforeRuntimeLoadWorkspace != afterRuntimeLoadWorkspace) {
        return fail(QStringLiteral("loadCurrentRuntimeCardAuthoringDraft should import current runtime into a draft without writing runtime or workspace files")) ? 0 : 1;
    }

    QTcpServer aiServer;
    QByteArray aiRequestHeader;
    QByteArray aiRequestBody;
    int aiRequestCount = 0;
    if (!aiServer.listen(QHostAddress::LocalHost, 0)) {
        return fail(QStringLiteral("failed to start local fake card authoring AI server")) ? 0 : 1;
    }
    QObject::connect(&aiServer, &QTcpServer::newConnection, [&]() {
        QTcpSocket* socket = aiServer.nextPendingConnection();
        QByteArray* buffer = new QByteArray;
        QObject::connect(socket, &QTcpSocket::readyRead, [&, socket, buffer]() {
            buffer->append(socket->readAll());
            const int split = buffer->indexOf("\r\n\r\n");
            if (split < 0) {
                return;
            }
            const QByteArray header = buffer->left(split);
            const int expectedLength = contentLengthFromHeader(header);
            const QByteArray body = buffer->mid(split + 4);
            if (body.size() < expectedLength) {
                return;
            }

            aiRequestHeader = header;
            aiRequestBody = body.left(expectedLength);
            ++aiRequestCount;

            QString content;
            if (aiRequestCount == 1) {
                const QJsonObject review{
                    { QStringLiteral("summary"), QStringLiteral("generated bridge review") },
                    { QStringLiteral("plan"), QJsonObject{
                        { QStringLiteral("package_mode"), QStringLiteral("runtime_package") },
                        { QStringLiteral("required_containers"), QJsonArray{ QStringLiteral("database") } },
                    } },
                    { QStringLiteral("candidates"), QJsonArray{
                        QJsonObject{
                            { QStringLiteral("id"), QStringLiteral("generated_database_tag") },
                            { QStringLiteral("module"), QStringLiteral("database") },
                            { QStringLiteral("action"), QStringLiteral("json_patch") },
                            { QStringLiteral("target"), QJsonObject{
                                { QStringLiteral("path"), QStringLiteral("database.tags") },
                                { QStringLiteral("operation"), QStringLiteral("append") },
                            } },
                            { QStringLiteral("after"), QJsonObject{
                                { QStringLiteral("tag"), QStringLiteral("database.tag.generated") },
                                { QStringLiteral("title"), QStringLiteral("Generated Tag") },
                                { QStringLiteral("target"), QStringLiteral("worldbook") },
                                { QStringLiteral("description"), QStringLiteral("generated tag content") },
                            } },
                            { QStringLiteral("group_id"), QStringLiteral("database_mechanism") },
                        },
                    } },
                };
                content = QStringLiteral("```json\n%1\n```")
                    .arg(QString::fromUtf8(QJsonDocument(review).toJson(QJsonDocument::Compact)));
            } else if (aiRequestCount == 2) {
                const QJsonArray bareArrayReview{
                    QJsonObject{
                        { QStringLiteral("id"), QStringLiteral("generated_bare_array_stage") },
                        { QStringLiteral("module"), QStringLiteral("database") },
                        { QStringLiteral("action"), QStringLiteral("json_patch") },
                        { QStringLiteral("target"), QJsonObject{
                            { QStringLiteral("path"), QStringLiteral("database.stages") },
                            { QStringLiteral("operation"), QStringLiteral("append") },
                        } },
                        { QStringLiteral("after"), QJsonObject{
                            { QStringLiteral("role_id"), QStringLiteral("main") },
                            { QStringLiteral("stage_key"), QStringLiteral("bare_array") },
                            { QStringLiteral("title"), QStringLiteral("Bare Array Stage") },
                            { QStringLiteral("condition"), QStringLiteral("trust >= 5") },
                            { QStringLiteral("active_tag"), QStringLiteral("state_journal.stage.main.bare_array") },
                            { QStringLiteral("emits_tags"), QJsonArray{ QStringLiteral("state_journal.stage.main.bare_array") } },
                            { QStringLiteral("description"), QStringLiteral("bare array candidate from legacy fallback") },
                        } },
                    },
                };
                content = QString::fromUtf8(QJsonDocument(bareArrayReview).toJson(QJsonDocument::Compact));
            } else {
                content = QStringLiteral("I could not decide. Maybe add a stage, but this is not JSON.");
            }
            const QJsonObject responseObject{
                { QStringLiteral("choices"), QJsonArray{
                    QJsonObject{
                        { QStringLiteral("message"), QJsonObject{
                            { QStringLiteral("content"), content },
                        } },
                    },
                } },
            };
            const QByteArray responseBody = QJsonDocument(responseObject).toJson(QJsonDocument::Compact);
            const QByteArray response = QByteArray("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ")
                + QByteArray::number(responseBody.size())
                + QByteArray("\r\nConnection: close\r\n\r\n")
                + responseBody;
            socket->write(response);
            socket->flush();
            socket->disconnectFromHost();
        });
        QObject::connect(socket, &QTcpSocket::disconnected, socket, &QTcpSocket::deleteLater);
        QObject::connect(socket, &QTcpSocket::destroyed, [buffer]() {
            delete buffer;
        });
    });

    QJsonObject aiSettings;
    aiSettings.insert(QStringLiteral("temperature"), 0.3);
    aiSettings.insert(QStringLiteral("request_timeout"), 10);
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/settings.json")), QJsonDocument(aiSettings))) {
        return fail(QStringLiteral("failed to write card authoring AI settings fixture")) ? 0 : 1;
    }
    QJsonObject aiProvider;
    aiProvider.insert(QStringLiteral("id"), QStringLiteral("local-ai"));
    aiProvider.insert(QStringLiteral("enabled"), true);
    aiProvider.insert(QStringLiteral("priority"), 1);
    aiProvider.insert(QStringLiteral("base_url"), QStringLiteral("http://127.0.0.1:%1").arg(aiServer.serverPort()));
    aiProvider.insert(QStringLiteral("model"), QStringLiteral("Card Writer Model"));
    aiProvider.insert(QStringLiteral("keys"), QJsonArray{ QStringLiteral("card-writer-key") });
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/route_forwarding.json")), QJsonDocument(QJsonObject{
            { QStringLiteral("enabled"), true },
            { QStringLiteral("providers"), QJsonArray{ aiProvider } },
        }))) {
        return fail(QStringLiteral("failed to write card authoring AI route fixture")) ? 0 : 1;
    }

    const QVariantMap generatedCandidates = bridge.generateCardAuthoringCandidates(
        project,
        QStringLiteral("琛ヤ竴涓彲琚笘鐣屼功娑堣垂鐨勬暟鎹簱 tag"),
        QStringLiteral("database"),
        QStringLiteral("deep"));
    const QJsonObject generatedAudit = QJsonObject::fromVariantMap(generatedCandidates.value(QStringLiteral("package_audit")).toMap());
    const QJsonObject aiRequestPayload = QJsonDocument::fromJson(aiRequestBody).object();
    const QJsonArray aiRequestMessages = aiRequestPayload.value(QStringLiteral("messages")).toArray();
    if (!generatedCandidates.value(QStringLiteral("ok")).toBool()
        || !generatedCandidates.value(QStringLiteral("generated")).toBool()
        || generatedCandidates.value(QStringLiteral("thinking_mode")).toString() != QStringLiteral("deep")
        || generatedCandidates.value(QStringLiteral("candidates")).toList().size() != 2
        || generatedCandidates.value(QStringLiteral("raw_response")).toString().isEmpty()
        || aiRequestCount != 1
        || !aiRequestHeader.contains("POST /v1/chat/completions ")
        || !aiRequestHeader.contains("Authorization: Bearer card-writer-key")
        || aiRequestPayload.value(QStringLiteral("model")).toString() != QStringLiteral("card-writer-model")
        || aiRequestPayload.value(QStringLiteral("temperature")).toDouble() != 0.3
        || aiRequestMessages.size() != 2
        || !aiRequestMessages.first().toObject().value(QStringLiteral("content")).toString().contains(QStringLiteral("json_patch"))
        || !aiRequestMessages.last().toObject().value(QStringLiteral("content")).toString().contains(QStringLiteral("琛ヤ竴涓彲琚笘鐣屼功娑堣垂鐨勬暟鎹簱 tag"))
        || !aiRequestMessages.last().toObject().value(QStringLiteral("content")).toString().contains(QStringLiteral("Bridge Authored Card"))
        || !variantListContainsCandidateAfterExternalTag(
            generatedCandidates.value(QStringLiteral("candidates")).toList(),
            QStringLiteral("database.tag.generated"))
        || !generatedAudit.value(QStringLiteral("missing_tag_consumers")).toArray().isEmpty()) {
        return fail(QStringLiteral("generateCardAuthoringCandidates should call the configured LLM and normalize generated review candidates")) ? 0 : 1;
    }

    const QVariantMap generatedBareArrayCandidates = bridge.generateCardAuthoringCandidates(
        project,
        QStringLiteral("return bare JSON array legacy fallback candidate"),
        QStringLiteral("database"),
        QStringLiteral("fast"));
    const QVariantList generatedBareArrayItems = generatedBareArrayCandidates.value(QStringLiteral("candidates")).toList();
    const QVariantMap generatedBareArrayFirst = generatedBareArrayItems.isEmpty() ? QVariantMap{} : generatedBareArrayItems.first().toMap();
    const QVariantMap generatedBareArrayAfter = generatedBareArrayFirst.value(QStringLiteral("after")).toMap();
    if (!generatedBareArrayCandidates.value(QStringLiteral("ok")).toBool()
        || !generatedBareArrayCandidates.value(QStringLiteral("generated")).toBool()
        || generatedBareArrayCandidates.value(QStringLiteral("thinking_mode")).toString() != QStringLiteral("fast")
        || generatedBareArrayItems.size() != 2
        || generatedBareArrayFirst.value(QStringLiteral("id")).toString() != QStringLiteral("generated_bare_array_stage")
        || generatedBareArrayAfter.value(QStringLiteral("active_tag")).toString() != QStringLiteral("database.stage.main.bare_array")
        || !generatedBareArrayAfter.value(QStringLiteral("emits_tags")).toList().contains(QStringLiteral("database.stage.main.bare_array"))
        || !variantListContainsCandidateAfterExternalTag(
            generatedBareArrayCandidates.value(QStringLiteral("candidates")).toList(),
            QStringLiteral("database.stage.main.bare_array"))
        || aiRequestCount != 2) {
        return fail(QStringLiteral("generateCardAuthoringCandidates should normalize bare JSON array model output and legacy state_journal stage tags")) ? 0 : 1;
    }

    const QVariantMap malformedGeneratedCandidates = bridge.generateCardAuthoringCandidates(
        project,
        QStringLiteral("return malformed non JSON candidate response"),
        QStringLiteral("database"),
        QStringLiteral("deep"));
    if (malformedGeneratedCandidates.value(QStringLiteral("ok")).toBool()
        || malformedGeneratedCandidates.value(QStringLiteral("raw_response")).toString().isEmpty()
        || !malformedGeneratedCandidates.value(QStringLiteral("message")).toString().contains(QStringLiteral("JSON"))
        || aiRequestCount != 3) {
        return fail(QStringLiteral("generateCardAuthoringCandidates should surface malformed model output with raw_response for manual repair")) ? 0 : 1;
    }

    const QVariantMap candidateReview{
        { QStringLiteral("candidates"), QVariantList{
            QVariantMap{
                { QStringLiteral("id"), QStringLiteral("bridge_database_tag") },
                { QStringLiteral("module"), QStringLiteral("database") },
                { QStringLiteral("action"), QStringLiteral("json_patch") },
                { QStringLiteral("target"), QVariantMap{
                    { QStringLiteral("path"), QStringLiteral("database.tags") },
                    { QStringLiteral("operation"), QStringLiteral("append") },
                } },
                { QStringLiteral("after"), QVariantMap{
                    { QStringLiteral("tag"), QStringLiteral("database.tag.bridge-candidate") },
                    { QStringLiteral("title"), QStringLiteral("Bridge Candidate Tag") },
                    { QStringLiteral("trigger"), QStringLiteral("this trigger is not the consumer key") },
                    { QStringLiteral("target"), QStringLiteral("worldbook") },
                    { QStringLiteral("description"), QStringLiteral("bridge candidate tag content") },
                } },
                { QStringLiteral("group_id"), QStringLiteral("database_mechanism") },
            },
        } },
    };
    const QVariantMap normalizedCandidates = bridge.normalizeCardAuthoringCandidates(project, candidateReview);
    if (!normalizedCandidates.value(QStringLiteral("ok")).toBool()
        || normalizedCandidates.value(QStringLiteral("candidates")).toList().size() != 2
        || normalizedCandidates.value(QStringLiteral("package_audit")).toMap().value(QStringLiteral("missing_tag_consumers")).toList().size() != 0) {
        return fail(QStringLiteral("normalizeCardAuthoringCandidates should expose normalized candidate review through bridge")) ? 0 : 1;
    }
    const QVariantMap selectedCandidateApply = bridge.applyCardAuthoringCandidates(
        project,
        candidateReview,
        QVariantList{ QStringLiteral("bridge_database_tag") });
    const QVariantMap selectedCandidateProject = selectedCandidateApply.value(QStringLiteral("project")).toMap();
    if (!selectedCandidateApply.value(QStringLiteral("ok")).toBool()
        || selectedCandidateApply.value(QStringLiteral("summary")).toMap().value(QStringLiteral("applied_count")).toInt() != 1
        || selectedCandidateApply.value(QStringLiteral("summary")).toMap().value(QStringLiteral("skipped_count")).toInt() != 1
        || !selectedCandidateApply.value(QStringLiteral("applied_candidate_ids")).toList().contains(QStringLiteral("bridge_database_tag"))
        || selectedCandidateProject.value(QStringLiteral("database")).toMap().value(QStringLiteral("tags")).toList().size() != 2
        || variantListContainsExternalTag(
            selectedCandidateProject.value(QStringLiteral("worldbook")).toMap().value(QStringLiteral("entries")).toList(),
            QStringLiteral("database.tag.bridge-candidate"))) {
        return fail(QStringLiteral("applyCardAuthoringCandidates should apply only selected candidate ids")) ? 0 : 1;
    }
    const QVariantMap candidateApply = bridge.applyCardAuthoringCandidates(project, candidateReview, QVariantList{});
    const QVariantMap candidateProject = candidateApply.value(QStringLiteral("project")).toMap();
    if (!candidateApply.value(QStringLiteral("ok")).toBool()
        || candidateApply.value(QStringLiteral("summary")).toMap().value(QStringLiteral("applied_count")).toInt() != 2
        || candidateProject.value(QStringLiteral("database")).toMap().value(QStringLiteral("tags")).toList().size() != 2
        || !variantListContainsExternalTag(
            candidateProject.value(QStringLiteral("worldbook")).toMap().value(QStringLiteral("entries")).toList(),
            QStringLiteral("database.tag.bridge-candidate"))
        || !variantListContainsExternalTag(
            bridge.cardAuthoringDraft().value(QStringLiteral("worldbook")).toMap().value(QStringLiteral("entries")).toList(),
            QStringLiteral("database.tag.bridge-candidate"))) {
        return fail(QStringLiteral("applyCardAuthoringCandidates should apply candidates to bridge draft and auto-fill tag consumers")) ? 0 : 1;
    }

    const QString importProjectPath = root.absoluteFilePath(QStringLiteral("imported-bridge-role.json"));
    if (!writeJson(importProjectPath, QJsonDocument(QJsonObject{
            { QStringLiteral("name"), QStringLiteral("Imported Bridge Role") },
            { QStringLiteral("description"), QStringLiteral("bridge import description") },
        }))) {
        return fail(QStringLiteral("failed to write bridge import project fixture")) ? 0 : 1;
    }
    const QVariantMap importProjectResult = bridge.importCardAuthoringProjectFile(QUrl::fromLocalFile(importProjectPath).toString());
    const QString importedPath = importProjectResult.value(QStringLiteral("importedPath")).toString();
    if (!importProjectResult.value(QStringLiteral("ok")).toBool()
        || !QFileInfo::exists(importedPath)
        || bridge.cardAuthoringDraft().value(QStringLiteral("persona_card")).toMap().value(QStringLiteral("name")).toString() != QStringLiteral("Imported Bridge Role")) {
        return fail(QStringLiteral("importCardAuthoringProjectFile should import external role JSON as project")) ? 0 : 1;
    }
    const QVariantMap deleteProjectResult = bridge.deleteCardAuthoringProject(QFileInfo(importedPath).fileName());
    if (!deleteProjectResult.value(QStringLiteral("ok")).toBool()
        || QFileInfo::exists(importedPath)
        || !QFileInfo::exists(deleteProjectResult.value(QStringLiteral("archivedPath")).toString())) {
        return fail(QStringLiteral("deleteCardAuthoringProject should archive imported project")) ? 0 : 1;
    }

    const QByteArray beforePreview = readFileBytes(cardPath);
    const QVariantMap previewResult = bridge.previewCardAuthoringApply(project, QVariantList{ QStringLiteral("database") });
    if (!previewResult.value(QStringLiteral("ok")).toBool()
        || previewResult.value(QStringLiteral("summary")).toMap().value(QStringLiteral("change_count")).toInt() <= 0) {
        return fail(QStringLiteral("previewCardAuthoringApply should report database changes")) ? 0 : 1;
    }
    const QVariantList previewGroups = previewResult.value(QStringLiteral("groups")).toList();
    const QVariantList previewChanges = previewGroups.first().toMap().value(QStringLiteral("changes")).toList();
    const QVariantMap firstPreviewChange = previewChanges.first().toMap();
    if (firstPreviewChange.value(QStringLiteral("label")).toString().isEmpty()
        || firstPreviewChange.value(QStringLiteral("path")).toString() != QStringLiteral("raw.stateJournal")
        || firstPreviewChange.value(QStringLiteral("action")).toString().isEmpty()
        || firstPreviewChange.value(QStringLiteral("after_preview")).toString().isEmpty()) {
        return fail(QStringLiteral("previewCardAuthoringApply should expose readable diff metadata")) ? 0 : 1;
    }
    const QByteArray afterPreview = readFileBytes(cardPath);
    if (beforePreview != afterPreview) {
        return fail(QStringLiteral("previewCardAuthoringApply must not write current_role_card.json")) ? 0 : 1;
    }

    const QVariantMap applyResult = bridge.applyCardAuthoringDraft(project, QVariantList{ QStringLiteral("database") });
    if (!applyResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("applyCardAuthoringDraft failed: %1").arg(applyResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (applyResult.value(QStringLiteral("preview")).toMap().value(QStringLiteral("summary")).toMap().value(QStringLiteral("change_count")).toInt() <= 0) {
        return fail(QStringLiteral("applyCardAuthoringDraft should return the diff that was applied")) ? 0 : 1;
    }
    const QString backupPath = applyResult.value(QStringLiteral("backupPath")).toString();
    if (backupPath.isEmpty() || !QFileInfo::exists(backupPath)) {
        return fail(QStringLiteral("applyCardAuthoringDraft should expose an existing backupPath")) ? 0 : 1;
    }

    const QJsonObject afterApply = readJsonObject(cardPath);
    const QJsonObject afterApplyRaw = afterApply.value(QStringLiteral("raw")).toObject();
    const QJsonObject afterApplyStateJournal = afterApplyRaw.value(QStringLiteral("stateJournal")).toObject();
    const QJsonObject afterApplyDatabaseDraft = afterApplyStateJournal.value(QStringLiteral("databaseDraft")).toObject();
    const QJsonObject afterApplyDatabaseVariable = findById(
        afterApplyDatabaseDraft.value(QStringLiteral("variables")).toArray(),
        QStringLiteral("db_var_affection"));
    const QJsonObject afterApplyDatabaseStage = findById(
        afterApplyDatabaseDraft.value(QStringLiteral("stages")).toArray(),
        QStringLiteral("db_stage_trust"));
    const QJsonObject afterApplyDatabaseSnapshot = findById(
        afterApplyDatabaseDraft.value(QStringLiteral("snapshotFields")).toArray(),
        QStringLiteral("db_snapshot_mood"));
    const QJsonObject afterApplyDatabaseTag = findById(
        afterApplyDatabaseDraft.value(QStringLiteral("tags")).toArray(),
        QStringLiteral("db_tag_lore"));
    if (afterApplyRaw.value(QStringLiteral("name")).toString() != QStringLiteral("Old Name")
        || afterApplyRaw.value(QStringLiteral("unknown_raw_field")).toString() != QStringLiteral("raw-stays")
        || !afterApplyStateJournal.value(QStringLiteral("enabled")).toBool(false)
        || afterApplyStateJournal.value(QStringLiteral("unknown_state_field")).toString() != QStringLiteral("state-stays")
        || afterApplyDatabaseVariable.value(QStringLiteral("write_policy")).toString() != QStringLiteral("manual_review")
        || afterApplyDatabaseVariable.value(QStringLiteral("notes")).toString() != QStringLiteral("affection note")
        || afterApplyDatabaseStage.value(QStringLiteral("active_tag")).toString() != QStringLiteral("database.stage.role-1.trust")
        || !jsonArrayContainsString(afterApplyDatabaseStage.value(QStringLiteral("emits_tags")).toArray(), QStringLiteral("database.tag.bridge-signal"))
        || afterApplyDatabaseStage.value(QStringLiteral("description")).toString() != QStringLiteral("trust stage description")
        || afterApplyDatabaseSnapshot.value(QStringLiteral("notes")).toString() != QStringLiteral("mood snapshot note")
        || afterApplyDatabaseTag.value(QStringLiteral("target")).toString() != QStringLiteral("worldbook")
        || afterApplyDatabaseTag.value(QStringLiteral("notes")).toString() != QStringLiteral("bridge lore tag note")) {
        return fail(QStringLiteral("database apply should preserve persona/raw fields and merge compatible database payload")) ? 0 : 1;
    }
    if (bridge.cardAuthoringPreview().value(QStringLiteral("summary")).toMap().value(QStringLiteral("group_count")).toInt() <= 0) {
        return fail(QStringLiteral("bridge should expose the latest cardAuthoringPreview")) ? 0 : 1;
    }
    const QVariantMap runtimePreview = bridge.previewCardAuthoringApply(
        project,
        QVariantList{ QStringLiteral("worldbook"), QStringLiteral("preset"), QStringLiteral("memory") });
    if (!runtimePreview.value(QStringLiteral("ok")).toBool()
        || runtimePreview.value(QStringLiteral("summary")).toMap().value(QStringLiteral("change_count")).toInt() < 3) {
        return fail(QStringLiteral("previewCardAuthoringApply should report runtime module changes")) ? 0 : 1;
    }
    const QVariantMap runtimeApply = bridge.applyCardAuthoringDraft(
        project,
        QVariantList{ QStringLiteral("worldbook"), QStringLiteral("preset"), QStringLiteral("memory") });
    if (!runtimeApply.value(QStringLiteral("ok")).toBool()
        || runtimeApply.value(QStringLiteral("backups")).toList().size() < 3) {
        return fail(QStringLiteral("applyCardAuthoringDraft should apply runtime modules with backups")) ? 0 : 1;
    }
    const QJsonObject bridgeWorldbook = readJsonObject(root.absoluteFilePath(QStringLiteral("data/worldbook.json")));
    const QJsonArray bridgeWorldbookEntries = bridgeWorldbook.value(QStringLiteral("entries")).toArray();
    const QJsonObject bridgeDatabaseTagEntry = findByKey(
        bridgeWorldbookEntries,
        QStringLiteral("trigger"),
        QStringLiteral("database.tag.bridge-lore"));
    const QJsonObject bridgeDatabaseStageEntry = findByKey(
        bridgeWorldbookEntries,
        QStringLiteral("trigger"),
        QStringLiteral("database.tag.bridge-signal"));
    if (findById(bridgeWorldbook.value(QStringLiteral("entries")).toArray(), QStringLiteral("bridge-worldbook")).value(QStringLiteral("content")).toString()
            != QStringLiteral("bridge worldbook content")
        || bridgeDatabaseTagEntry.value(QStringLiteral("entry_type")).toString() != QStringLiteral("external_tag")
        || !bridgeDatabaseTagEntry.value(QStringLiteral("content")).toString().contains(QStringLiteral("bridge lore tag note"))
        || bridgeDatabaseStageEntry.value(QStringLiteral("entry_type")).toString() != QStringLiteral("external_tag")
        || !bridgeDatabaseStageEntry.value(QStringLiteral("content")).toString().contains(QStringLiteral("trust stage note"))) {
        return fail(QStringLiteral("bridge runtime apply should write worldbook entries")) ? 0 : 1;
    }
    const QJsonObject bridgePreset = findById(
        readJsonObject(root.absoluteFilePath(QStringLiteral("data/preset.json"))).value(QStringLiteral("presets")).toArray(),
        QStringLiteral("base"));
    if (bridgePreset.value(QStringLiteral("base_system_prompt")).toString() != QStringLiteral("KEEP BRIDGE BASE")
        || findById(bridgePreset.value(QStringLiteral("extra_prompts")).toArray(), QStringLiteral("bridge-extra")).isEmpty()
        || findById(bridgePreset.value(QStringLiteral("prompt_groups")).toArray(), QStringLiteral("bridge-group")).isEmpty()) {
        return fail(QStringLiteral("bridge runtime apply should merge preset lightweight fields only")) ? 0 : 1;
    }
    const QJsonArray bridgeMemories = readJsonArray(root.absoluteFilePath(QStringLiteral("data/card_runtime/cards/card-123/memories.json")));
    if (bridgeMemories.size() != 2
        || bridgeMemories.at(1).toObject().value(QStringLiteral("content")).toString() != QStringLiteral("bridge memory content")
        || bridgeMemories.at(1).toObject().value(QStringLiteral("memory_status")).toString() != QStringLiteral("active")
        || bridgeMemories.at(1).toObject().value(QStringLiteral("notes")).toString() != QStringLiteral("bridge memory note")
        || !jsonArrayContainsString(bridgeMemories.at(1).toObject().value(QStringLiteral("tags")).toArray(), QStringLiteral("bridge"))) {
        return fail(QStringLiteral("bridge runtime apply should append current role memory")) ? 0 : 1;
    }

    return 0;
}
