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
        { QStringLiteral("data/current_role_card.json"), QJsonObject{} },
        { QStringLiteral("data/preset.json"), QJsonObject{} },
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
    if (!makeRequiredFiles(root)) {
        return fail(QStringLiteral("failed to create temporary Fantareal fixture")) ? 0 : 1;
    }

    QJsonObject settings;
    settings.insert(QStringLiteral("enabled"), false);
    settings.insert(QStringLiteral("debug_enabled"), false);
    settings.insert(QStringLiteral("max_hits"), 3);
    settings.insert(QStringLiteral("default_case_sensitive"), true);
    settings.insert(QStringLiteral("default_whole_word"), false);
    settings.insert(QStringLiteral("default_match_mode"), QStringLiteral("all"));
    settings.insert(QStringLiteral("default_secondary_mode"), QStringLiteral("any"));
    settings.insert(QStringLiteral("default_entry_type"), QStringLiteral("external_tag"));
    settings.insert(QStringLiteral("default_group_operator"), QStringLiteral("or"));
    settings.insert(QStringLiteral("default_chance"), 25);
    settings.insert(QStringLiteral("default_sticky_turns"), 2);
    settings.insert(QStringLiteral("default_cooldown_turns"), 3);
    settings.insert(QStringLiteral("default_insertion_position"), QStringLiteral("before_char_defs"));
    settings.insert(QStringLiteral("default_injection_depth"), 4);
    settings.insert(QStringLiteral("default_injection_role"), QStringLiteral("user"));
    settings.insert(QStringLiteral("default_injection_order"), 88);
    settings.insert(QStringLiteral("default_prompt_layer"), QStringLiteral("stable"));
    settings.insert(QStringLiteral("recursive_scan_enabled"), false);
    settings.insert(QStringLiteral("recursion_max_depth"), 1);
    settings.insert(QStringLiteral("unknown_settings_field"), QStringLiteral("settings-stays"));

    QJsonObject entry;
    entry.insert(QStringLiteral("id"), QStringLiteral("entry-1"));
    entry.insert(QStringLiteral("title"), QStringLiteral("Entry One"));
    entry.insert(QStringLiteral("trigger"), QStringLiteral("alpha"));
    entry.insert(QStringLiteral("content"), QStringLiteral("world fact"));
    entry.insert(QStringLiteral("enabled"), true);
    entry.insert(QStringLiteral("unknown_entry_field"), QStringLiteral("entry-stays"));

    QJsonObject worldbook;
    worldbook.insert(QStringLiteral("settings"), settings);
    worldbook.insert(QStringLiteral("entries"), QJsonArray{ entry });
    worldbook.insert(QStringLiteral("unknown_root_field"), QStringLiteral("root-stays"));

    const QString worldbookPath = root.absoluteFilePath(QStringLiteral("data/worldbook.json"));
    if (!writeJson(worldbookPath, QJsonDocument(worldbook))) {
        return fail(QStringLiteral("failed to write fixture worldbook.json")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;
    const QVariantMap initialDraft = bridge.worldbookDraft();
    if (initialDraft.value(QStringLiteral("entryCount")).toInt() != 1
        || initialDraft.value(QStringLiteral("enabledEntryCount")).toInt() != 1) {
        return fail(QStringLiteral("worldbookDraft should expose entry counts")) ? 0 : 1;
    }
    if (initialDraft.value(QStringLiteral("default_entry_type")).toString() != QStringLiteral("external_tag")
        || initialDraft.value(QStringLiteral("default_prompt_layer")).toString() != QStringLiteral("stable")) {
        return fail(QStringLiteral("worldbookDraft should expose normalized settings")) ? 0 : 1;
    }
    if (initialDraft.contains(QStringLiteral("entries"))) {
        return fail(QStringLiteral("worldbookDraft should not expose full entries")) ? 0 : 1;
    }
    const QVariantList initialEntryDrafts = bridge.worldbookEntryDrafts();
    if (initialEntryDrafts.size() != 1) {
        return fail(QStringLiteral("worldbookEntryDrafts should expose editable entry summaries")) ? 0 : 1;
    }
    const QVariantMap initialEntryDraft = initialEntryDrafts.first().toMap();
    if (initialEntryDraft.value(QStringLiteral("content")).toString() != QStringLiteral("world fact")
        || initialEntryDraft.value(QStringLiteral("trigger")).toString() != QStringLiteral("alpha")) {
        return fail(QStringLiteral("worldbookEntryDrafts should expose safe editable fields")) ? 0 : 1;
    }

    QVariantMap draft;
    draft.insert(QStringLiteral("enabled"), true);
    draft.insert(QStringLiteral("debug_enabled"), true);
    draft.insert(QStringLiteral("max_hits"), 99);
    draft.insert(QStringLiteral("default_case_sensitive"), false);
    draft.insert(QStringLiteral("default_whole_word"), true);
    draft.insert(QStringLiteral("default_match_mode"), QStringLiteral("bad-mode"));
    draft.insert(QStringLiteral("default_secondary_mode"), QStringLiteral("all"));
    draft.insert(QStringLiteral("default_entry_type"), QStringLiteral("bad-type"));
    draft.insert(QStringLiteral("default_group_operator"), QStringLiteral("any"));
    draft.insert(QStringLiteral("default_chance"), -40);
    draft.insert(QStringLiteral("default_sticky_turns"), 2000);
    draft.insert(QStringLiteral("default_cooldown_turns"), -2);
    draft.insert(QStringLiteral("default_insertion_position"), QStringLiteral("depth_ai"));
    draft.insert(QStringLiteral("default_injection_depth"), 10000);
    draft.insert(QStringLiteral("default_injection_role"), QStringLiteral("model"));
    draft.insert(QStringLiteral("default_injection_order"), -8);
    draft.insert(QStringLiteral("default_prompt_layer"), QStringLiteral("bad-layer"));
    draft.insert(QStringLiteral("recursive_scan_enabled"), true);
    draft.insert(QStringLiteral("recursion_max_depth"), 99);

    const QVariantMap result = bridge.saveWorldbookDraft(draft);
    if (!result.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("saveWorldbookDraft failed: %1").arg(result.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }

    const QString backupPath = result.value(QStringLiteral("backupPath")).toString();
    if (backupPath.isEmpty() || !QFileInfo::exists(backupPath)) {
        return fail(QStringLiteral("worldbook backup was not created")) ? 0 : 1;
    }

    const QJsonObject saved = readJsonObject(worldbookPath);
    const QJsonObject savedSettings = saved.value("settings").toObject();
    if (!savedSettings.value("enabled").toBool(false) || !savedSettings.value("debug_enabled").toBool(false)) {
        return fail(QStringLiteral("worldbook booleans were not saved")) ? 0 : 1;
    }
    if (savedSettings.value("max_hits").toInt() != 20
        || savedSettings.value("default_chance").toInt() != 0
        || savedSettings.value("default_sticky_turns").toInt() != 999
        || savedSettings.value("default_cooldown_turns").toInt() != 0
        || savedSettings.value("default_injection_depth").toInt() != 999
        || savedSettings.value("default_injection_order").toInt() != 0
        || savedSettings.value("recursion_max_depth").toInt() != 5) {
        return fail(QStringLiteral("worldbook numeric clamps failed")) ? 0 : 1;
    }
    if (savedSettings.value("default_match_mode").toString() != QStringLiteral("any")
        || savedSettings.value("default_secondary_mode").toString() != QStringLiteral("all")
        || savedSettings.value("default_entry_type").toString() != QStringLiteral("keyword")
        || savedSettings.value("default_group_operator").toString() != QStringLiteral("or")
        || savedSettings.value("default_insertion_position").toString() != QStringLiteral("at_depth_assistant")
        || savedSettings.value("default_injection_role").toString() != QStringLiteral("assistant")
        || savedSettings.value("default_prompt_layer").toString() != QStringLiteral("follow_position")) {
        return fail(QStringLiteral("worldbook enum normalization failed")) ? 0 : 1;
    }
    if (savedSettings.value("unknown_settings_field").toString() != QStringLiteral("settings-stays")
        || saved.value("unknown_root_field").toString() != QStringLiteral("root-stays")) {
        return fail(QStringLiteral("unknown worldbook fields should be preserved")) ? 0 : 1;
    }

    const QJsonArray savedEntries = saved.value("entries").toArray();
    if (savedEntries.size() != 1
        || savedEntries.first().toObject().value("unknown_entry_field").toString() != QStringLiteral("entry-stays")) {
        return fail(QStringLiteral("worldbook entries should be preserved")) ? 0 : 1;
    }

    QVariantMap entryDraft;
    entryDraft.insert(QStringLiteral("title"), QStringLiteral("Updated Entry"));
    entryDraft.insert(QStringLiteral("trigger"), QStringLiteral("beta"));
    entryDraft.insert(QStringLiteral("secondary_trigger"), QStringLiteral("gamma"));
    entryDraft.insert(QStringLiteral("entry_type"), QStringLiteral("keyword"));
    entryDraft.insert(QStringLiteral("group_operator"), QStringLiteral("any"));
    entryDraft.insert(QStringLiteral("match_mode"), QStringLiteral("bad-mode"));
    entryDraft.insert(QStringLiteral("secondary_mode"), QStringLiteral("all"));
    entryDraft.insert(QStringLiteral("content"), QStringLiteral("updated world fact"));
    entryDraft.insert(QStringLiteral("group"), QStringLiteral("lore"));
    entryDraft.insert(QStringLiteral("chance"), 150);
    entryDraft.insert(QStringLiteral("sticky_turns"), -1);
    entryDraft.insert(QStringLiteral("cooldown_turns"), 1000);
    entryDraft.insert(QStringLiteral("order"), 42);
    entryDraft.insert(QStringLiteral("insertion_position"), QStringLiteral("at_depth_user"));
    entryDraft.insert(QStringLiteral("injection_depth"), 12);
    entryDraft.insert(QStringLiteral("injection_role"), QStringLiteral("assistant"));
    entryDraft.insert(QStringLiteral("injection_order"), -4);
    entryDraft.insert(QStringLiteral("prompt_layer"), QStringLiteral("current_state"));
    entryDraft.insert(QStringLiteral("recursive_enabled"), false);
    entryDraft.insert(QStringLiteral("prevent_further_recursion"), true);
    entryDraft.insert(QStringLiteral("enabled"), false);
    entryDraft.insert(QStringLiteral("case_sensitive"), false);
    entryDraft.insert(QStringLiteral("whole_word"), true);
    entryDraft.insert(QStringLiteral("comment"), QStringLiteral("updated comment"));

    const QVariantMap entryResult = bridge.saveWorldbookEntry(0, entryDraft);
    if (!entryResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("saveWorldbookEntry update failed: %1").arg(entryResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (entryResult.value(QStringLiteral("backupPath")).toString().isEmpty()
        || !QFileInfo::exists(entryResult.value(QStringLiteral("backupPath")).toString())) {
        return fail(QStringLiteral("worldbook entry update backup was not created")) ? 0 : 1;
    }

    const QJsonObject afterEntrySave = readJsonObject(worldbookPath);
    const QJsonArray updatedEntries = afterEntrySave.value("entries").toArray();
    const QJsonObject updatedEntry = updatedEntries.first().toObject();
    if (updatedEntry.value("id").toString() != QStringLiteral("entry-1")
        || updatedEntry.value("unknown_entry_field").toString() != QStringLiteral("entry-stays")) {
        return fail(QStringLiteral("worldbook entry identity or unknown fields should be preserved")) ? 0 : 1;
    }
    if (updatedEntry.value("title").toString() != QStringLiteral("Updated Entry")
        || updatedEntry.value("trigger").toString() != QStringLiteral("beta")
        || updatedEntry.value("content").toString() != QStringLiteral("updated world fact")
        || updatedEntry.value("enabled").toBool(true)) {
        return fail(QStringLiteral("worldbook entry editable fields were not saved")) ? 0 : 1;
    }
    if (updatedEntry.value("chance").toInt() != 100
        || updatedEntry.value("sticky_turns").toInt() != 0
        || updatedEntry.value("cooldown_turns").toInt() != 999
        || updatedEntry.value("injection_order").toInt() != 0) {
        return fail(QStringLiteral("worldbook entry numeric clamps failed")) ? 0 : 1;
    }
    if (updatedEntry.value("match_mode").toString() != QStringLiteral("any")
        || updatedEntry.value("group_operator").toString() != QStringLiteral("or")
        || updatedEntry.value("insertion_position").toString() != QStringLiteral("at_depth_user")
        || updatedEntry.value("injection_role").toString() != QStringLiteral("user")
        || updatedEntry.value("prompt_layer").toString() != QStringLiteral("current_state")) {
        return fail(QStringLiteral("worldbook entry enum normalization failed")) ? 0 : 1;
    }

    QVariantMap newEntryDraft;
    newEntryDraft.insert(QStringLiteral("title"), QStringLiteral("Constant Entry"));
    newEntryDraft.insert(QStringLiteral("entry_type"), QStringLiteral("constant"));
    newEntryDraft.insert(QStringLiteral("content"), QStringLiteral("always injected fact"));
    newEntryDraft.insert(QStringLiteral("enabled"), true);
    const QVariantMap addResult = bridge.saveWorldbookEntry(-1, newEntryDraft);
    if (!addResult.value(QStringLiteral("ok")).toBool()
        || addResult.value(QStringLiteral("entryIndex")).toInt() != 1) {
        return fail(QStringLiteral("saveWorldbookEntry add failed: %1").arg(addResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }

    const QJsonArray afterAddEntries = readJsonObject(worldbookPath).value("entries").toArray();
    if (afterAddEntries.size() != 2) {
        return fail(QStringLiteral("worldbook entry add should append one entry")) ? 0 : 1;
    }
    const QJsonObject addedEntry = afterAddEntries.at(1).toObject();
    if (addedEntry.value("id").toString().trimmed().isEmpty()
        || addedEntry.value("entry_type").toString() != QStringLiteral("constant")
        || addedEntry.value("content").toString() != QStringLiteral("always injected fact")) {
        return fail(QStringLiteral("added worldbook entry should have generated identity and saved fields")) ? 0 : 1;
    }

    QVariantMap invalidEntryDraft;
    invalidEntryDraft.insert(QStringLiteral("entry_type"), QStringLiteral("keyword"));
    invalidEntryDraft.insert(QStringLiteral("content"), QStringLiteral("content without trigger"));
    const QVariantMap invalidEntryResult = bridge.saveWorldbookEntry(-1, invalidEntryDraft);
    if (invalidEntryResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("keyword worldbook entry without trigger should be rejected")) ? 0 : 1;
    }

    const QVariantMap refreshedDraft = bridge.worldbookDraft();
    if (refreshedDraft.value(QStringLiteral("max_hits")).toInt() != 20
        || refreshedDraft.value(QStringLiteral("default_insertion_position")).toString() != QStringLiteral("at_depth_assistant")
        || !refreshedDraft.value(QStringLiteral("recursive_scan_enabled")).toBool()) {
        return fail(QStringLiteral("worldbookDraft should refresh after save")) ? 0 : 1;
    }
    if (bridge.worldbookEntryDrafts().size() != 2) {
        return fail(QStringLiteral("worldbookEntryDrafts should refresh after entry save")) ? 0 : 1;
    }

    return 0;
}
