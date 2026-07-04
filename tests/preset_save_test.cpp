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

    QJsonObject activePreset;
    activePreset.insert(QStringLiteral("id"), QStringLiteral("preset_default"));
    activePreset.insert(QStringLiteral("name"), QStringLiteral("默认预设"));
    activePreset.insert(QStringLiteral("enabled"), true);
    activePreset.insert(QStringLiteral("unknown_preset_field"), QStringLiteral("must-stay"));
    activePreset.insert(QStringLiteral("modules"), QJsonObject{
        { QStringLiteral("no_user_speaking"), true },
        { QStringLiteral("short_paragraph"), false },
        { QStringLiteral("long_paragraph"), false },
        { QStringLiteral("second_person"), false },
        { QStringLiteral("third_person"), false },
        { QStringLiteral("anti_repeat"), true },
        { QStringLiteral("custom_plugin_module"), true },
    });
    activePreset.insert(QStringLiteral("extra_prompts"), QJsonArray{
        QJsonObject{
            { QStringLiteral("id"), QStringLiteral("style-core") },
            { QStringLiteral("name"), QStringLiteral("核心风格") },
            { QStringLiteral("enabled"), true },
            { QStringLiteral("content"), QStringLiteral("保留我") },
        },
    });
    activePreset.insert(QStringLiteral("prompt_groups"), QJsonArray{
        QJsonObject{
            { QStringLiteral("id"), QStringLiteral("group-1") },
            { QStringLiteral("name"), QStringLiteral("规则组") },
        },
    });

    QJsonObject otherPreset;
    otherPreset.insert(QStringLiteral("id"), QStringLiteral("preset_other"));
    otherPreset.insert(QStringLiteral("name"), QStringLiteral("另一个预设"));
    otherPreset.insert(QStringLiteral("enabled"), true);
    otherPreset.insert(QStringLiteral("modules"), QJsonObject{
        { QStringLiteral("long_paragraph"), true },
    });

    QJsonObject store;
    store.insert(QStringLiteral("active_preset_id"), QStringLiteral("preset_default"));
    store.insert(QStringLiteral("unknown_store_field"), QStringLiteral("must-stay"));
    store.insert(QStringLiteral("presets"), QJsonArray{ activePreset, otherPreset });

    const QString presetPath = root.absoluteFilePath(QStringLiteral("data/preset.json"));
    if (!writeJson(presetPath, QJsonDocument(store))) {
        return fail(QStringLiteral("failed to write fixture preset.json")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;
    const QVariantMap initialDraft = bridge.presetDraft();
    if (initialDraft.value(QStringLiteral("id")).toString() != QStringLiteral("preset_default")) {
        return fail(QStringLiteral("presetDraft should expose active preset id")) ? 0 : 1;
    }
    if (initialDraft.value(QStringLiteral("subPresetItems")).toList().size() != 2) {
        return fail(QStringLiteral("presetDraft should expose extra prompts and prompt groups as sub presets")) ? 0 : 1;
    }

    QVariantMap moduleDraft;
    moduleDraft.insert(QStringLiteral("short_paragraph"), true);
    moduleDraft.insert(QStringLiteral("long_paragraph"), true);
    moduleDraft.insert(QStringLiteral("second_person"), true);
    moduleDraft.insert(QStringLiteral("third_person"), true);
    moduleDraft.insert(QStringLiteral("anti_horny"), true);
    moduleDraft.insert(QStringLiteral("custom_plugin_module"), false);

    QVariantMap draft;
    draft.insert(QStringLiteral("id"), QStringLiteral("preset_default"));
    draft.insert(QStringLiteral("name"), QStringLiteral("  HuskarUI 预设  "));
    draft.insert(QStringLiteral("enabled"), false);
    draft.insert(QStringLiteral("modules"), moduleDraft);
    draft.insert(QStringLiteral("subPresets"), QVariantMap{
        { QStringLiteral("extra_prompts:style-core"), false },
        { QStringLiteral("prompt_groups:group-1"), false },
    });

    const QVariantMap result = bridge.savePresetDraft(draft);
    if (!result.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("savePresetDraft failed: %1").arg(result.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }

    const QString backupPath = result.value(QStringLiteral("backupPath")).toString();
    if (backupPath.isEmpty() || !QFileInfo::exists(backupPath)) {
        return fail(QStringLiteral("preset backup was not created")) ? 0 : 1;
    }

    const QJsonObject saved = readJsonObject(presetPath);
    if (saved.value("unknown_store_field").toString() != QStringLiteral("must-stay")) {
        return fail(QStringLiteral("unknown top-level preset store field was not preserved")) ? 0 : 1;
    }

    const QJsonArray savedPresets = saved.value("presets").toArray();
    if (savedPresets.size() != 2) {
        return fail(QStringLiteral("preset array size changed unexpectedly")) ? 0 : 1;
    }

    const QJsonObject savedActive = savedPresets.at(0).toObject();
    if (savedActive.value("name").toString() != QStringLiteral("HuskarUI 预设")) {
        return fail(QStringLiteral("preset name was not trimmed/saved")) ? 0 : 1;
    }
    if (savedActive.value("enabled").toBool(true)) {
        return fail(QStringLiteral("preset enabled state was not saved")) ? 0 : 1;
    }
    if (savedActive.value("unknown_preset_field").toString() != QStringLiteral("must-stay")) {
        return fail(QStringLiteral("unknown active preset field was not preserved")) ? 0 : 1;
    }
    const QJsonArray savedExtraPrompts = savedActive.value("extra_prompts").toArray();
    const QJsonArray savedPromptGroups = savedActive.value("prompt_groups").toArray();
    if (savedExtraPrompts.size() != 1 || savedPromptGroups.size() != 1) {
        return fail(QStringLiteral("prompt data should be preserved")) ? 0 : 1;
    }
    if (savedExtraPrompts.first().toObject().value("enabled").toBool(true)
        || savedPromptGroups.first().toObject().value("enabled").toBool(true)) {
        return fail(QStringLiteral("sub preset enabled switches were not saved")) ? 0 : 1;
    }

    const QJsonObject savedModules = savedActive.value("modules").toObject();
    if (!savedModules.value("short_paragraph").toBool(false) || savedModules.value("long_paragraph").toBool(true)) {
        return fail(QStringLiteral("paragraph mutex should keep short_paragraph and disable long_paragraph")) ? 0 : 1;
    }
    if (!savedModules.value("second_person").toBool(false) || savedModules.value("third_person").toBool(true)) {
        return fail(QStringLiteral("person mutex should keep second_person and disable third_person")) ? 0 : 1;
    }
    if (!savedModules.value("anti_horny").toBool(false)) {
        return fail(QStringLiteral("known module anti_horny was not saved")) ? 0 : 1;
    }
    if (!savedModules.value("custom_plugin_module").toBool(false)) {
        return fail(QStringLiteral("unknown module key should be preserved and not patched by the UI draft")) ? 0 : 1;
    }

    const QJsonObject savedOther = savedPresets.at(1).toObject();
    if (savedOther.value("name").toString() != QStringLiteral("另一个预设")
        || !savedOther.value("modules").toObject().value("long_paragraph").toBool(false)) {
        return fail(QStringLiteral("non-active preset should not be modified")) ? 0 : 1;
    }

    const QVariantMap refreshedDraft = bridge.presetDraft();
    const QVariantMap refreshedModules = refreshedDraft.value(QStringLiteral("modules")).toMap();
    if (refreshedDraft.value(QStringLiteral("name")).toString() != QStringLiteral("HuskarUI 预设")) {
        return fail(QStringLiteral("presetDraft should refresh after save")) ? 0 : 1;
    }
    if (!refreshedModules.value(QStringLiteral("short_paragraph")).toBool()
        || refreshedModules.value(QStringLiteral("long_paragraph")).toBool()) {
        return fail(QStringLiteral("presetDraft should expose mutex-normalized modules")) ? 0 : 1;
    }

    QVariantMap staleDraft = draft;
    staleDraft.insert(QStringLiteral("id"), QStringLiteral("preset_missing"));
    const QVariantMap staleResult = bridge.savePresetDraft(staleDraft);
    if (staleResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("saving a missing preset id should fail")) ? 0 : 1;
    }

    return 0;
}
