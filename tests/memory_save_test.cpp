#include "fantarealbridge.h"

#include <QByteArray>
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QHash>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTemporaryDir>
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

bool writeBytes(const QString& path, const QByteArray& payload) {
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly)) {
        return false;
    }
    return file.write(payload) == payload.size();
}

QJsonArray readJsonArray(const QString& path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QJsonDocument::fromJson(file.readAll()).array();
}

bool makeRequiredFiles(const QDir& root) {
    const QStringList dirs = {
        QStringLiteral("data"),
        QStringLiteral("data/auto_saga"),
        QStringLiteral("data/mods/state_journal"),
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
        { QStringLiteral("data/current_role_card.json"), QJsonObject{} },
        { QStringLiteral("data/preset.json"), QJsonObject{} },
        { QStringLiteral("data/worldbook.json"), QJsonObject{} },
        { QStringLiteral("data/worldbook_runtime_state.json"), QJsonObject{} },
        { QStringLiteral("data/creative_workshop_state.json"), QJsonObject{} },
        { QStringLiteral("data/persona.json"), QJsonObject{} },
        { QStringLiteral("data/user_profile.json"), QJsonObject{} },
        { QStringLiteral("data/auto_saga/state.json"), QJsonObject{} },
        { QStringLiteral("cards/template_single_role_card.json"), QJsonObject{} },
        { QStringLiteral("cards/template_multi_role_card.json"), QJsonObject{} },
        { QStringLiteral("data/conversations.json"), QJsonArray{} },
    };

    for (auto it = jsonFiles.constBegin(); it != jsonFiles.constEnd(); ++it) {
        const QJsonDocument document = it.value().isArray()
            ? QJsonDocument(it.value().toArray())
            : QJsonDocument(it.value().toObject());
        if (!writeJson(root.absoluteFilePath(it.key()), document)) {
            return false;
        }
    }

    QFile(root.absoluteFilePath(QStringLiteral("data/mods/state_journal/state_journal.db"))).open(QIODevice::WriteOnly);
    QFile(root.absoluteFilePath(QStringLiteral("data/logs/fantareal.log"))).open(QIODevice::WriteOnly);
    return true;
}
}

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);
    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        return fail(QStringLiteral("failed to create temporary directory")) ? 0 : 1;
    }

    QDir root(tempDir.path());
    if (!makeRequiredFiles(root)) {
        return fail(QStringLiteral("failed to create temporary Fantareal fixture")) ? 0 : 1;
    }

    QJsonObject rawCard;
    rawCard.insert(QStringLiteral("name"), QStringLiteral("Memory Tester"));
    QJsonObject currentCard;
    currentCard.insert(QStringLiteral("source_name"), QStringLiteral("memory-card.json"));
    currentCard.insert(QStringLiteral("card_uid"), QStringLiteral("card-memory"));
    currentCard.insert(QStringLiteral("raw"), rawCard);
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/current_role_card.json")), QJsonDocument(currentCard))) {
        return fail(QStringLiteral("failed to write current card fixture")) ? 0 : 1;
    }

    if (!root.mkpath(QStringLiteral("data/card_runtime/cards/card-memory"))) {
        return fail(QStringLiteral("failed to create memory runtime dir")) ? 0 : 1;
    }
    const QString memoriesPath = root.absoluteFilePath(QStringLiteral("data/card_runtime/cards/card-memory/memories.json"));

    QJsonObject firstMemory;
    firstMemory.insert(QStringLiteral("id"), QStringLiteral("memory-1"));
    firstMemory.insert(QStringLiteral("title"), QStringLiteral("Original Memory"));
    firstMemory.insert(QStringLiteral("content"), QStringLiteral("Original content"));
    firstMemory.insert(QStringLiteral("tags"), QJsonArray{ QStringLiteral("pilot"), QStringLiteral("trust") });
    firstMemory.insert(QStringLiteral("notes"), QStringLiteral("Original notes"));
    firstMemory.insert(QStringLiteral("memory_status"), QStringLiteral("active"));
    firstMemory.insert(QStringLiteral("unknown_memory_field"), QStringLiteral("stays"));

    QJsonObject archivedMemory;
    archivedMemory.insert(QStringLiteral("id"), QStringLiteral("memory-2"));
    archivedMemory.insert(QStringLiteral("title"), QStringLiteral("Archived Memory"));
    archivedMemory.insert(QStringLiteral("content"), QStringLiteral("Archived content"));
    archivedMemory.insert(QStringLiteral("memory_status"), QStringLiteral("archived"));

    if (!writeJson(memoriesPath, QJsonDocument(QJsonArray{ firstMemory, archivedMemory }))) {
        return fail(QStringLiteral("failed to write memories fixture")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;

    const QVariantList initialDrafts = bridge.memoryDrafts();
    if (initialDrafts.size() != 2) {
        return fail(QStringLiteral("memoryDrafts should expose editable memories")) ? 0 : 1;
    }
    const QVariantMap firstDraft = initialDrafts.first().toMap();
    if (firstDraft.value(QStringLiteral("content")).toString() != QStringLiteral("Original content")
        || firstDraft.value(QStringLiteral("tagsText")).toString() != QStringLiteral("pilot, trust")
        || firstDraft.contains(QStringLiteral("unknown_memory_field"))) {
        return fail(QStringLiteral("memoryDrafts should expose safe editable fields only")) ? 0 : 1;
    }

    QVariantMap updateDraft;
    updateDraft.insert(QStringLiteral("title"), QStringLiteral("Updated Memory"));
    updateDraft.insert(QStringLiteral("content"), QStringLiteral("Updated memory content"));
    updateDraft.insert(QStringLiteral("tagsText"), QStringLiteral("new, pilot, new"));
    updateDraft.insert(QStringLiteral("notes"), QStringLiteral("Updated notes"));
    updateDraft.insert(QStringLiteral("active"), false);
    const QVariantMap updateResult = bridge.saveMemoryEntry(0, updateDraft);
    if (!updateResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("saveMemoryEntry update failed: %1").arg(updateResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    const QString updateBackupPath = updateResult.value(QStringLiteral("backupPath")).toString();
    if (updateBackupPath.isEmpty() || !QFileInfo::exists(updateBackupPath)) {
        return fail(QStringLiteral("memory update backup was not created")) ? 0 : 1;
    }

    const QJsonArray updated = readJsonArray(memoriesPath);
    const QJsonObject updatedFirst = updated.first().toObject();
    if (updatedFirst.value(QStringLiteral("id")).toString() != QStringLiteral("memory-1")
        || updatedFirst.value(QStringLiteral("unknown_memory_field")).toString() != QStringLiteral("stays")) {
        return fail(QStringLiteral("memory update should preserve identity and unknown fields")) ? 0 : 1;
    }
    if (updatedFirst.value(QStringLiteral("title")).toString() != QStringLiteral("Updated Memory")
        || updatedFirst.value(QStringLiteral("content")).toString() != QStringLiteral("Updated memory content")
        || updatedFirst.value(QStringLiteral("notes")).toString() != QStringLiteral("Updated notes")
        || updatedFirst.value(QStringLiteral("memory_status")).toString() != QStringLiteral("archived")) {
        return fail(QStringLiteral("memory update editable fields were not saved")) ? 0 : 1;
    }
    const QJsonArray updatedTags = updatedFirst.value(QStringLiteral("tags")).toArray();
    if (updatedTags.size() != 2
        || updatedTags.at(0).toString() != QStringLiteral("new")
        || updatedTags.at(1).toString() != QStringLiteral("pilot")) {
        return fail(QStringLiteral("memory tags should be normalized and de-duplicated")) ? 0 : 1;
    }

    QVariantMap addDraft;
    addDraft.insert(QStringLiteral("title"), QStringLiteral("New Memory"));
    addDraft.insert(QStringLiteral("content"), QStringLiteral("A freshly saved memory"));
    addDraft.insert(QStringLiteral("tagsText"), QStringLiteral("fresh, local"));
    addDraft.insert(QStringLiteral("active"), true);
    const QVariantMap addResult = bridge.saveMemoryEntry(-1, addDraft);
    if (!addResult.value(QStringLiteral("ok")).toBool()
        || addResult.value(QStringLiteral("entryIndex")).toInt() != 2) {
        return fail(QStringLiteral("saveMemoryEntry add failed: %1").arg(addResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (addResult.value(QStringLiteral("backupPath")).toString().isEmpty()
        || !QFileInfo::exists(addResult.value(QStringLiteral("backupPath")).toString())) {
        return fail(QStringLiteral("memory add should back up existing memories.json")) ? 0 : 1;
    }

    const QJsonArray afterAdd = readJsonArray(memoriesPath);
    if (afterAdd.size() != 3) {
        return fail(QStringLiteral("memory add should append one entry")) ? 0 : 1;
    }
    const QJsonObject added = afterAdd.at(2).toObject();
    if (added.value(QStringLiteral("id")).toString().trimmed().isEmpty()
        || added.value(QStringLiteral("content")).toString() != QStringLiteral("A freshly saved memory")
        || added.value(QStringLiteral("memory_status")).toString() != QStringLiteral("active")
        || added.value(QStringLiteral("created_at")).toString().trimmed().isEmpty()) {
        return fail(QStringLiteral("added memory should have generated identity and timestamps")) ? 0 : 1;
    }

    QVariantMap invalidDraft;
    invalidDraft.insert(QStringLiteral("title"), QStringLiteral("No Content"));
    const QVariantMap invalidResult = bridge.saveMemoryEntry(-1, invalidDraft);
    if (invalidResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("empty memory content should be rejected")) ? 0 : 1;
    }
    const QVariantMap invalidIndexResult = bridge.saveMemoryEntry(99, addDraft);
    if (invalidIndexResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("invalid memory index should be rejected")) ? 0 : 1;
    }
    if (readJsonArray(memoriesPath).size() != 3) {
        return fail(QStringLiteral("invalid memory saves should not mutate memories.json")) ? 0 : 1;
    }
    if (bridge.memoryDrafts().size() != 3) {
        return fail(QStringLiteral("memoryDrafts should refresh after saves")) ? 0 : 1;
    }

    QTemporaryDir blankTempDir;
    if (!blankTempDir.isValid()) {
        return fail(QStringLiteral("failed to create blank memory temporary directory")) ? 0 : 1;
    }
    QDir blankRoot(blankTempDir.path());
    if (!makeRequiredFiles(blankRoot)) {
        return fail(QStringLiteral("failed to create blank memory Fantareal fixture")) ? 0 : 1;
    }

    QJsonObject blankRawCard;
    blankRawCard.insert(QStringLiteral("name"), QStringLiteral("Blank Memory Tester"));
    QJsonObject blankCurrentCard;
    blankCurrentCard.insert(QStringLiteral("source_name"), QStringLiteral("blank-memory-card.json"));
    blankCurrentCard.insert(QStringLiteral("card_uid"), QStringLiteral("blank-memory-card"));
    blankCurrentCard.insert(QStringLiteral("raw"), blankRawCard);
    if (!writeJson(blankRoot.absoluteFilePath(QStringLiteral("data/current_role_card.json")), QJsonDocument(blankCurrentCard))) {
        return fail(QStringLiteral("failed to write blank current card fixture")) ? 0 : 1;
    }
    if (!blankRoot.mkpath(QStringLiteral("data/card_runtime/cards/blank-memory-card"))) {
        return fail(QStringLiteral("failed to create blank memory runtime dir")) ? 0 : 1;
    }
    const QString blankMemoriesPath = blankRoot.absoluteFilePath(QStringLiteral("data/card_runtime/cards/blank-memory-card/memories.json"));
    if (!writeBytes(blankMemoriesPath, QByteArray::fromHex("efbbbf"))) {
        return fail(QStringLiteral("failed to write BOM-only memories fixture")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(blankRoot.absolutePath()));
    FantarealBridge blankBridge;
    if (!blankBridge.memoryDrafts().isEmpty()) {
        return fail(QStringLiteral("BOM-only memories.json should load as empty memories")) ? 0 : 1;
    }

    QVariantMap blankDraft;
    blankDraft.insert(QStringLiteral("title"), QStringLiteral("Recovered Memory"));
    blankDraft.insert(QStringLiteral("content"), QStringLiteral("Recovered from a blank JSON file"));
    blankDraft.insert(QStringLiteral("active"), true);
    const QVariantMap blankResult = blankBridge.saveMemoryEntry(-1, blankDraft);
    if (!blankResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("saveMemoryEntry should recover BOM-only memories.json: %1").arg(blankResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    const QJsonArray blankSaved = readJsonArray(blankMemoriesPath);
    if (blankSaved.size() != 1
        || blankSaved.first().toObject().value(QStringLiteral("content")).toString() != QStringLiteral("Recovered from a blank JSON file")) {
        return fail(QStringLiteral("BOM-only memories.json should be replaced by one saved memory")) ? 0 : 1;
    }

    return 0;
}
