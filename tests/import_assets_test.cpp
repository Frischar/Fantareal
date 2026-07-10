#include "fantarealbridge.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QHash>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTemporaryDir>
#include <QUrl>

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

bool makeRequiredFiles(const QDir& root) {
    const QStringList dirs = {
        QStringLiteral("data"),
        QStringLiteral("data/auto_saga"),
        QStringLiteral("data/database"),
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

    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/current_role_card.json")),
            QJsonDocument(QJsonObject{ { QStringLiteral("raw"), QJsonObject{ { QStringLiteral("name"), QStringLiteral("Old Hero") } } } }))) {
        return false;
    }

    QJsonObject preset;
    preset.insert(QStringLiteral("id"), QStringLiteral("preset_base"));
    preset.insert(QStringLiteral("name"), QStringLiteral("Base"));
    preset.insert(QStringLiteral("enabled"), true);
    preset.insert(QStringLiteral("modules"), QJsonObject{});
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/preset.json")),
            QJsonDocument(QJsonObject{
                { QStringLiteral("active_preset_id"), QStringLiteral("preset_base") },
                { QStringLiteral("presets"), QJsonArray{ preset } },
            }))) {
        return false;
    }

    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/worldbook.json")),
            QJsonDocument(QJsonObject{
                { QStringLiteral("settings"), QJsonObject{ { QStringLiteral("enabled"), true }, { QStringLiteral("max_hits"), 2 } } },
                { QStringLiteral("entries"), QJsonArray{} },
            }))) {
        return false;
    }

    QFile(root.absoluteFilePath(QStringLiteral("data/database/database.db"))).open(QIODevice::WriteOnly);
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
    if (!makeRequiredFiles(root) || !root.mkpath(QStringLiteral("imports"))) {
        return fail(QStringLiteral("failed to create temporary Fantareal fixture")) ? 0 : 1;
    }

    const QString roleImportPath = root.absoluteFilePath(QStringLiteral("imports/role.json"));
    if (!writeJson(roleImportPath,
            QJsonDocument(QJsonObject{
                { QStringLiteral("name"), QStringLiteral("Imported Hero") },
                { QStringLiteral("description"), QStringLiteral("Imported role card description.") },
            }))) {
        return fail(QStringLiteral("failed to write role import fixture")) ? 0 : 1;
    }

    const QString presetImportPath = root.absoluteFilePath(QStringLiteral("imports/preset.json"));
    QJsonObject importedPreset;
    importedPreset.insert(QStringLiteral("id"), QStringLiteral("preset_base"));
    importedPreset.insert(QStringLiteral("name"), QStringLiteral("Imported Preset"));
    importedPreset.insert(QStringLiteral("enabled"), true);
    importedPreset.insert(QStringLiteral("modules"), QJsonObject{ { QStringLiteral("short_paragraph"), true } });
    importedPreset.insert(QStringLiteral("extra_prompts"), QJsonArray{
        QJsonObject{
            { QStringLiteral("id"), QStringLiteral("imported-style") },
            { QStringLiteral("name"), QStringLiteral("Imported Style") },
            { QStringLiteral("enabled"), true },
            { QStringLiteral("content"), QStringLiteral("Imported style content.") },
        },
    });
    if (!writeJson(presetImportPath,
            QJsonDocument(QJsonObject{
                { QStringLiteral("active_preset_id"), QStringLiteral("preset_base") },
                { QStringLiteral("presets"), QJsonArray{ importedPreset } },
            }))) {
        return fail(QStringLiteral("failed to write preset import fixture")) ? 0 : 1;
    }

    const QString worldbookImportPath = root.absoluteFilePath(QStringLiteral("imports/worldbook.json"));
    if (!writeJson(worldbookImportPath,
            QJsonDocument(QJsonObject{
                { QStringLiteral("settings"), QJsonObject{ { QStringLiteral("enabled"), true }, { QStringLiteral("max_hits"), 5 } } },
                { QStringLiteral("items"), QJsonArray{
                    QJsonObject{
                        { QStringLiteral("title"), QStringLiteral("Imported Lore") },
                        { QStringLiteral("trigger"), QStringLiteral("lore") },
                        { QStringLiteral("content"), QStringLiteral("Imported worldbook content.") },
                    },
                } },
            }))) {
        return fail(QStringLiteral("failed to write worldbook import fixture")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;

    const QVariantMap roleResult = bridge.importRoleCardFile(QUrl::fromLocalFile(roleImportPath).toString());
    if (!roleResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("importRoleCardFile failed: %1").arg(roleResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    const QJsonObject currentCard = readJsonObject(root.absoluteFilePath(QStringLiteral("data/current_role_card.json")));
    if (currentCard.value(QStringLiteral("raw")).toObject().value(QStringLiteral("name")).toString() != QStringLiteral("Imported Hero")) {
        return fail(QStringLiteral("imported role card was not activated")) ? 0 : 1;
    }
    if (!QFileInfo::exists(roleResult.value(QStringLiteral("backupPath")).toString())
        || roleResult.value(QStringLiteral("sourcePath")).toString().trimmed().isEmpty()) {
        return fail(QStringLiteral("role import should create backup and activate a managed source")) ? 0 : 1;
    }

    const QVariantMap presetResult = bridge.importPresetFile(QUrl::fromLocalFile(presetImportPath).toString());
    if (!presetResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("importPresetFile failed: %1").arg(presetResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    const QJsonObject presetStore = readJsonObject(root.absoluteFilePath(QStringLiteral("data/preset.json")));
    const QJsonArray presets = presetStore.value(QStringLiteral("presets")).toArray();
    if (presets.size() != 2 || presetStore.value(QStringLiteral("active_preset_id")).toString() == QStringLiteral("preset_base")) {
        return fail(QStringLiteral("preset import should append and activate a non-conflicting id")) ? 0 : 1;
    }
    if (bridge.presetDraft().value(QStringLiteral("subPresetItems")).toList().size() != 1) {
        return fail(QStringLiteral("imported preset should expose sub preset items")) ? 0 : 1;
    }

    const QVariantMap worldbookResult = bridge.importWorldbookFile(QUrl::fromLocalFile(worldbookImportPath).toString());
    if (!worldbookResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("importWorldbookFile failed: %1").arg(worldbookResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    const QJsonObject worldbook = readJsonObject(root.absoluteFilePath(QStringLiteral("data/worldbook.json")));
    const QJsonArray entries = worldbook.value(QStringLiteral("entries")).toArray();
    if (worldbook.value(QStringLiteral("settings")).toObject().value(QStringLiteral("max_hits")).toInt() != 5
        || entries.size() != 1
        || entries.first().toObject().value(QStringLiteral("title")).toString() != QStringLiteral("Imported Lore")) {
        return fail(QStringLiteral("worldbook import should save settings and entries")) ? 0 : 1;
    }

    return 0;
}
