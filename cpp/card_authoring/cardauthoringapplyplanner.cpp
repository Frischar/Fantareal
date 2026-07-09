#include "card_authoring/cardauthoringapplyplanner.h"

#include "card_authoring/cardauthoringcompiler.h"
#include "card_authoring/cardauthoringmodels.h"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonValue>
#include <QRegularExpression>
#include <QSaveFile>
#include <QSet>
#include <QUuid>

#include <utility>

namespace {
struct RuntimeWrite {
    QString relativePath;
    QJsonDocument document;
};

QString compactJson(const QJsonValue& value) {
    if (value.isUndefined()) {
        return QStringLiteral("未设置");
    }
    if (value.isNull()) {
        return QStringLiteral("null");
    }
    if (value.isString()) {
        QString text = value.toString().simplified();
        return text.isEmpty() ? QStringLiteral("空文本") : text;
    }
    if (value.isBool()) {
        return value.toBool() ? QStringLiteral("true") : QStringLiteral("false");
    }
    if (value.isDouble()) {
        return QString::number(value.toDouble(), 'g', 12);
    }
    if (value.isArray()) {
        return QString::fromUtf8(QJsonDocument(value.toArray()).toJson(QJsonDocument::Compact));
    }
    if (value.isObject()) {
        return QString::fromUtf8(QJsonDocument(value.toObject()).toJson(QJsonDocument::Compact));
    }
    return {};
}

QString clippedPreview(const QJsonValue& value, int maxLength = 360) {
    QString preview = compactJson(value);
    if (preview.size() <= maxLength) {
        return preview;
    }
    return preview.left(maxLength - 1) + QStringLiteral("…");
}

QString valueKind(const QJsonValue& value) {
    if (value.isUndefined()) {
        return QStringLiteral("missing");
    }
    if (value.isNull()) {
        return QStringLiteral("null");
    }
    if (value.isString()) {
        return QStringLiteral("text");
    }
    if (value.isBool()) {
        return QStringLiteral("bool");
    }
    if (value.isDouble()) {
        return QStringLiteral("number");
    }
    if (value.isArray()) {
        return QStringLiteral("array");
    }
    if (value.isObject()) {
        return QStringLiteral("object");
    }
    return QStringLiteral("unknown");
}

QString changeAction(const QJsonValue& before, const QJsonValue& after) {
    if (before.isUndefined() && !after.isUndefined()) {
        return QStringLiteral("create");
    }
    if (!before.isUndefined() && after.isUndefined()) {
        return QStringLiteral("remove");
    }
    return QStringLiteral("update");
}

QString fieldLabel(const QString& field) {
    if (field == QStringLiteral("name")) {
        return QStringLiteral("角色名");
    }
    if (field == QStringLiteral("description")) {
        return QStringLiteral("Description");
    }
    if (field == QStringLiteral("personality")) {
        return QStringLiteral("性格（personality）");
    }
    if (field == QStringLiteral("scenario")) {
        return QStringLiteral("Scenario");
    }
    if (field == QStringLiteral("first_mes")) {
        return QStringLiteral("First Message");
    }
    if (field == QStringLiteral("mes_example")) {
        return QStringLiteral("Example Messages");
    }
    if (field == QStringLiteral("creator_notes")) {
        return QStringLiteral("Creator Notes");
    }
    if (field == QStringLiteral("creator_comment")) {
        return QStringLiteral("Creator Comment");
    }
    if (field == QStringLiteral("tags")) {
        return QStringLiteral("标签");
    }
    if (field == QStringLiteral("personas")) {
        return QStringLiteral("多角色");
    }
    if (field == QStringLiteral("creativeWorkshop")) {
        return QStringLiteral("演出工坊");
    }
    if (field == QStringLiteral("stateJournal")) {
        return QStringLiteral("数据库兼容字段");
    }
    return field;
}

QString warningText(const QString& warning) {
    if (warning == QStringLiteral("persona_card.name is empty")) {
        return QStringLiteral("角色名为空；应用“主卡”会把当前角色名写成空值。");
    }
    if (warning == QStringLiteral("database draft is empty")) {
        return QStringLiteral("数据库草稿为空；应用数据库模块不会带入变量、状态快照或标签。");
    }
    return warning;
}

QJsonObject warningObject(const QString& id, const QString& message, const QString& severity = QStringLiteral("warning")) {
    return QJsonObject{
        { QStringLiteral("id"), id },
        { QStringLiteral("severity"), severity },
        { QStringLiteral("message"), message },
    };
}

QString normalizedRuntimeKey(const QString& value, const QString& fallback = QStringLiteral("global")) {
    QString text = value.trimmed().isEmpty() ? fallback : value.trimmed().toLower();
    text.replace(QRegularExpression(QStringLiteral("\\s+")), QStringLiteral("_"));
    text.replace(QRegularExpression(QStringLiteral("[^a-z0-9_\\-]+")), QString());
    text.replace(QRegularExpression(QStringLiteral("[_\\-]{2,}")), QStringLiteral("_"));
    while (text.startsWith(QLatin1Char('_')) || text.startsWith(QLatin1Char('-'))) {
        text.remove(0, 1);
    }
    while (text.endsWith(QLatin1Char('_')) || text.endsWith(QLatin1Char('-'))) {
        text.chop(1);
    }
    return text.isEmpty() ? fallback : text;
}

QString safeIdSegment(const QString& value, const QString& fallback) {
    QString text = value.trimmed().toLower();
    text.replace(QRegularExpression(QStringLiteral("\\s+")), QStringLiteral("-"));
    text.replace(QRegularExpression(QStringLiteral("[^a-z0-9_\\-]+")), QStringLiteral("-"));
    text.replace(QRegularExpression(QStringLiteral("[_\\-]{2,}")), QStringLiteral("-"));
    while (text.startsWith(QLatin1Char('_')) || text.startsWith(QLatin1Char('-'))) {
        text.remove(0, 1);
    }
    while (text.endsWith(QLatin1Char('_')) || text.endsWith(QLatin1Char('-'))) {
        text.chop(1);
    }
    return text.isEmpty() ? fallback : text;
}

QString textValue(const QJsonObject& object, const QString& key, const QString& fallback = {}, int maxLength = 12000) {
    QString value = CardAuthoring::normalizedText(object.value(key));
    if (value.isEmpty()) {
        value = fallback;
    }
    if (value.size() > maxLength) {
        value = value.left(maxLength).trimmed();
    }
    return value;
}

QJsonObject overlayObject(QJsonObject base, const QJsonObject& incoming) {
    for (auto it = incoming.constBegin(); it != incoming.constEnd(); ++it) {
        base.insert(it.key(), it.value());
    }
    return base;
}

QJsonObject defaultWorldbookSettings() {
    return QJsonObject{
        { QStringLiteral("enabled"), true },
        { QStringLiteral("debug_enabled"), false },
        { QStringLiteral("max_hits"), 3 },
        { QStringLiteral("default_case_sensitive"), false },
        { QStringLiteral("default_whole_word"), false },
        { QStringLiteral("default_match_mode"), QStringLiteral("any") },
        { QStringLiteral("default_secondary_mode"), QStringLiteral("all") },
        { QStringLiteral("default_entry_type"), QStringLiteral("keyword") },
        { QStringLiteral("default_group_operator"), QStringLiteral("and") },
        { QStringLiteral("default_chance"), 100 },
        { QStringLiteral("default_sticky_turns"), 0 },
        { QStringLiteral("default_cooldown_turns"), 0 },
        { QStringLiteral("default_insertion_position"), QStringLiteral("after_char_defs") },
        { QStringLiteral("default_injection_depth"), 0 },
        { QStringLiteral("default_injection_role"), QStringLiteral("system") },
        { QStringLiteral("default_injection_order"), 100 },
        { QStringLiteral("default_prompt_layer"), QStringLiteral("follow_position") },
        { QStringLiteral("recursive_scan_enabled"), false },
        { QStringLiteral("recursion_max_depth"), 2 },
    };
}

QString normalizedWorldbookEntryType(const QString& value, const QString& trigger) {
    const QString normalized = value.trimmed().toLower();
    if (normalized == QStringLiteral("external_tag")) {
        return trigger.trimmed().isEmpty() ? QStringLiteral("constant") : QStringLiteral("external_tag");
    }
    if (normalized == QStringLiteral("constant")) {
        return QStringLiteral("constant");
    }
    if (normalized == QStringLiteral("keyword")) {
        return trigger.trimmed().isEmpty() ? QStringLiteral("constant") : QStringLiteral("keyword");
    }
    return trigger.trimmed().isEmpty() ? QStringLiteral("constant") : QStringLiteral("keyword");
}

QJsonObject normalizedWorldbookEntry(const QJsonObject& rawEntry, const QJsonObject& currentEntry, int index) {
    QJsonObject entry = overlayObject(currentEntry, rawEntry);
    QString id = textValue(entry, QStringLiteral("id"));
    if (id.isEmpty()) {
        id = QStringLiteral("card-authoring-worldbook-%1").arg(QUuid::createUuid().toString(QUuid::WithoutBraces));
    }

    const QString content = textValue(entry, QStringLiteral("content"));
    if (content.isEmpty()) {
        return {};
    }

    const QString trigger = textValue(entry, QStringLiteral("trigger"), QString(), 1200);
    const QString title = textValue(
        entry,
        QStringLiteral("title"),
        trigger.isEmpty() ? QStringLiteral("词条 %1").arg(index + 1) : trigger,
        160);
    const QString entryType = normalizedWorldbookEntryType(entry.value(QStringLiteral("entry_type")).toString(), trigger);
    const int order = qBound(0, entry.value(QStringLiteral("order")).toInt(entry.value(QStringLiteral("priority")).toInt(100)), 999999);

    entry.insert(QStringLiteral("id"), id);
    entry.insert(QStringLiteral("title"), title);
    entry.insert(QStringLiteral("trigger"), trigger);
    entry.insert(QStringLiteral("secondary_trigger"), textValue(entry, QStringLiteral("secondary_trigger"), QString(), 1200));
    entry.insert(QStringLiteral("entry_type"), entryType);
    entry.insert(QStringLiteral("group_operator"), entry.value(QStringLiteral("group_operator")).toString(QStringLiteral("and")));
    entry.insert(QStringLiteral("match_mode"), entry.value(QStringLiteral("match_mode")).toString(QStringLiteral("any")));
    entry.insert(QStringLiteral("secondary_mode"), entry.value(QStringLiteral("secondary_mode")).toString(QStringLiteral("all")));
    entry.insert(QStringLiteral("content"), content);
    entry.insert(QStringLiteral("group"), textValue(entry, QStringLiteral("group"), QString(), 120));
    entry.insert(QStringLiteral("chance"), qBound(0, entry.value(QStringLiteral("chance")).toInt(100), 100));
    entry.insert(QStringLiteral("sticky_turns"), qBound(0, entry.value(QStringLiteral("sticky_turns")).toInt(0), 999));
    entry.insert(QStringLiteral("cooldown_turns"), qBound(0, entry.value(QStringLiteral("cooldown_turns")).toInt(0), 999));
    entry.insert(QStringLiteral("order"), order);
    entry.insert(QStringLiteral("priority"), order);
    entry.insert(QStringLiteral("insertion_position"), entry.value(QStringLiteral("insertion_position")).toString(QStringLiteral("after_char_defs")));
    entry.insert(QStringLiteral("injection_depth"), qBound(0, entry.value(QStringLiteral("injection_depth")).toInt(0), 999));
    entry.insert(QStringLiteral("injection_role"), entry.value(QStringLiteral("injection_role")).toString(QStringLiteral("system")));
    entry.insert(QStringLiteral("injection_order"), qBound(0, entry.value(QStringLiteral("injection_order")).toInt(order), 999999));
    entry.insert(QStringLiteral("prompt_layer"), entry.value(QStringLiteral("prompt_layer")).toString(QStringLiteral("follow_position")));
    entry.insert(QStringLiteral("recursive_enabled"), entry.value(QStringLiteral("recursive_enabled")).toBool(true));
    entry.insert(QStringLiteral("prevent_further_recursion"), entry.value(QStringLiteral("prevent_further_recursion")).toBool(false));
    entry.insert(QStringLiteral("enabled"), entry.value(QStringLiteral("enabled")).toBool(true));
    entry.insert(QStringLiteral("case_sensitive"), entry.value(QStringLiteral("case_sensitive")).toBool(false));
    entry.insert(QStringLiteral("whole_word"), entry.value(QStringLiteral("whole_word")).toBool(false));
    entry.insert(QStringLiteral("comment"), textValue(entry, QStringLiteral("comment"), QString(), 240));
    return entry;
}

QJsonArray arrayFromValue(const QJsonValue& value, const QStringList& objectKeys) {
    if (value.isArray()) {
        return value.toArray();
    }
    if (value.isObject()) {
        const QJsonObject object = value.toObject();
        for (const QString& key : objectKeys) {
            if (object.value(key).isArray()) {
                return object.value(key).toArray();
            }
        }
    }
    return {};
}

QJsonArray projectWorldbookEntries(const QJsonObject& project) {
    QJsonArray entries = arrayFromValue(project.value(QStringLiteral("worldbook")), {
        QStringLiteral("entries"),
        QStringLiteral("items"),
    });
    return entries;
}

void appendDatabaseWorldbookEntry(QJsonArray* entries, QSet<QString>* ids, const QString& idSeed, const QString& title, const QString& trigger, const QString& content, const QString& comment) {
    if (!entries || !ids || trigger.trimmed().isEmpty() || content.trimmed().isEmpty()) {
        return;
    }
    const QString id = QStringLiteral("card-authoring-database-%1").arg(safeIdSegment(idSeed, QUuid::createUuid().toString(QUuid::WithoutBraces)));
    if (ids->contains(id)) {
        return;
    }
    ids->insert(id);
    entries->append(QJsonObject{
        { QStringLiteral("id"), id },
        { QStringLiteral("title"), title.trimmed().isEmpty() ? trigger.trimmed() : title.trimmed() },
        { QStringLiteral("trigger"), trigger.trimmed() },
        { QStringLiteral("entry_type"), QStringLiteral("external_tag") },
        { QStringLiteral("content"), content.trimmed() },
        { QStringLiteral("group"), QStringLiteral("database") },
        { QStringLiteral("enabled"), true },
        { QStringLiteral("comment"), comment },
    });
}

QJsonArray databaseGeneratedWorldbookEntries(const QJsonObject& project) {
    const QJsonObject database = project.value(QStringLiteral("database")).toObject();
    QJsonArray entries;
    QSet<QString> ids;

    const QJsonArray tags = database.value(QStringLiteral("tags")).toArray();
    for (const QJsonValue& value : tags) {
        const QJsonObject tag = value.toObject();
        const QString target = textValue(tag, QStringLiteral("target"), QStringLiteral("worldbook")).toLower();
        if (!target.isEmpty() && target != QStringLiteral("worldbook")) {
            continue;
        }
        const QString tagValue = textValue(tag, QStringLiteral("tag"));
        const QString trigger = tagValue;
        const QString content = QStringList{
            textValue(tag, QStringLiteral("description")),
            textValue(tag, QStringLiteral("notes")),
        }.join(QStringLiteral("\n")).trimmed();
        appendDatabaseWorldbookEntry(
            &entries,
            &ids,
            QStringLiteral("tag-%1").arg(tagValue),
            textValue(tag, QStringLiteral("title"), tagValue),
            trigger,
            content,
            QStringLiteral("写卡器数据库标签生成"));
    }

    const QJsonArray stages = database.value(QStringLiteral("stages")).toArray();
    for (const QJsonValue& value : stages) {
        const QJsonObject stage = value.toObject();
        const QStringList emittedTags = CardAuthoring::splitTags(stage.value(QStringLiteral("emits_tags")));
        QStringList triggers = emittedTags;
        const QString activeTag = textValue(stage, QStringLiteral("active_tag"));
        if (!activeTag.isEmpty() && !triggers.contains(activeTag)) {
            triggers.prepend(activeTag);
        }
        const QString content = QStringList{
            textValue(stage, QStringLiteral("condition")),
            textValue(stage, QStringLiteral("description")),
            textValue(stage, QStringLiteral("notes")),
        }.join(QStringLiteral("\n")).trimmed();
        for (const QString& trigger : triggers) {
            appendDatabaseWorldbookEntry(
                &entries,
                &ids,
                QStringLiteral("stage-%1-%2-%3").arg(
                    textValue(stage, QStringLiteral("role_id"), QStringLiteral("role")),
                    textValue(stage, QStringLiteral("stage_key"), QStringLiteral("stage")),
                    trigger),
                textValue(stage, QStringLiteral("title"), textValue(stage, QStringLiteral("stage_key"), trigger)),
                trigger,
                content,
                QStringLiteral("写卡器状态快照生成"));
        }
    }
    return entries;
}

int findObjectById(const QJsonArray& array, const QString& id) {
    if (id.trimmed().isEmpty()) {
        return -1;
    }
    for (int i = 0; i < array.size(); ++i) {
        if (array.at(i).toObject().value(QStringLiteral("id")).toString() == id) {
            return i;
        }
    }
    return -1;
}

QJsonObject projectPresetSource(const QJsonObject& project) {
    const QJsonValue presetValue = project.value(QStringLiteral("preset"));
    if (!presetValue.isObject()) {
        return {};
    }
    const QJsonObject presetStore = presetValue.toObject();
    const QJsonArray presets = presetStore.value(QStringLiteral("presets")).toArray();
    if (presets.isEmpty()) {
        return presetStore;
    }

    const QString activePresetId = presetStore.value(QStringLiteral("active_preset_id")).toString();
    for (const QJsonValue& value : presets) {
        const QJsonObject preset = value.toObject();
        if (!activePresetId.isEmpty() && preset.value(QStringLiteral("id")).toString() == activePresetId) {
            return preset;
        }
    }
    return presets.first().toObject();
}

bool hasPresetPayload(const QJsonObject& preset) {
    return !preset.value(QStringLiteral("modules")).toObject().isEmpty()
        || !preset.value(QStringLiteral("extra_prompts")).toArray().isEmpty()
        || !preset.value(QStringLiteral("prompt_groups")).toArray().isEmpty();
}

void applyPresetModuleMutex(QJsonObject* modules) {
    if (!modules) {
        return;
    }
    if (modules->value(QStringLiteral("short_paragraph")).toBool(false)) {
        modules->insert(QStringLiteral("long_paragraph"), false);
    }
    if (modules->value(QStringLiteral("long_paragraph")).toBool(false)) {
        modules->insert(QStringLiteral("short_paragraph"), false);
    }
    if (modules->value(QStringLiteral("second_person")).toBool(false)) {
        modules->insert(QStringLiteral("third_person"), false);
    }
    if (modules->value(QStringLiteral("third_person")).toBool(false)) {
        modules->insert(QStringLiteral("second_person"), false);
    }
}

QJsonArray mergeObjectArrayById(QJsonArray currentItems, const QJsonArray& incomingItems, const QString& idPrefix) {
    for (const QJsonValue& value : incomingItems) {
        if (!value.isObject()) {
            continue;
        }
        QJsonObject incoming = value.toObject();
        if (incoming.isEmpty()) {
            continue;
        }
        QString id = textValue(incoming, QStringLiteral("id"));
        if (id.isEmpty()) {
            id = QStringLiteral("card-authoring-%1-%2").arg(idPrefix, QUuid::createUuid().toString(QUuid::WithoutBraces));
            incoming.insert(QStringLiteral("id"), id);
        }
        const int index = findObjectById(currentItems, id);
        if (index >= 0) {
            currentItems.replace(index, overlayObject(currentItems.at(index).toObject(), incoming));
        } else {
            currentItems.append(incoming);
        }
    }
    return currentItems;
}

QString normalizedLookupKey(const QString& value) {
    QString text = value.trimmed().toLower();
    text.replace(QRegularExpression(QStringLiteral("\\s+")), QString());
    return text;
}

QStringList roleLookupKeys(const QJsonObject& role) {
    QStringList keys;
    for (const QString& field : {
            QStringLiteral("role_id"),
            QStringLiteral("id"),
            QStringLiteral("role_name"),
            QStringLiteral("name"),
        }) {
        const QString key = normalizedLookupKey(role.value(field).toString());
        if (!key.isEmpty() && !keys.contains(key)) {
            keys.append(key);
        }
    }
    const QJsonArray aliases = role.value(QStringLiteral("aliases")).toArray();
    for (const QJsonValue& alias : aliases) {
        const QString key = normalizedLookupKey(alias.toString());
        if (!key.isEmpty() && !keys.contains(key)) {
            keys.append(key);
        }
    }
    return keys;
}

int findRoleIndex(const QJsonArray& roles, const QJsonObject& incomingRole) {
    const QStringList incomingKeys = roleLookupKeys(incomingRole);
    if (incomingKeys.isEmpty()) {
        return -1;
    }
    for (int i = 0; i < roles.size(); ++i) {
        const QStringList currentKeys = roleLookupKeys(roles.at(i).toObject());
        for (const QString& key : incomingKeys) {
            if (currentKeys.contains(key)) {
                return i;
            }
        }
    }
    return -1;
}

int findObjectByKey(const QJsonArray& array, const QString& keyField, const QString& key) {
    if (key.trimmed().isEmpty()) {
        return -1;
    }
    for (int i = 0; i < array.size(); ++i) {
        if (array.at(i).toObject().value(keyField).toString() == key) {
            return i;
        }
    }
    return -1;
}

QJsonArray mergeObjectArrayByKey(QJsonArray currentItems, const QJsonArray& incomingItems, const QString& keyField) {
    for (const QJsonValue& value : incomingItems) {
        if (!value.isObject()) {
            continue;
        }
        const QJsonObject incoming = value.toObject();
        const QString key = incoming.value(keyField).toString();
        const int index = findObjectByKey(currentItems, keyField, key);
        if (index >= 0) {
            currentItems.replace(index, overlayObject(currentItems.at(index).toObject(), incoming));
        } else {
            currentItems.append(incoming);
        }
    }
    return currentItems;
}

QJsonObject mergeStateJournalRole(QJsonObject currentRole, const QJsonObject& incomingRole) {
    if (currentRole.isEmpty()) {
        return incomingRole;
    }

    currentRole.insert(
        QStringLiteral("variables"),
        mergeObjectArrayByKey(
            currentRole.value(QStringLiteral("variables")).toArray(),
            incomingRole.value(QStringLiteral("variables")).toArray(),
            QStringLiteral("var_key")));
    currentRole.insert(
        QStringLiteral("stages"),
        mergeObjectArrayByKey(
            currentRole.value(QStringLiteral("stages")).toArray(),
            incomingRole.value(QStringLiteral("stages")).toArray(),
            QStringLiteral("stage_key")));
    if (!currentRole.value(QStringLiteral("snapshotFields")).isArray()) {
        currentRole.insert(QStringLiteral("snapshotFields"), incomingRole.value(QStringLiteral("snapshotFields")).toArray());
    }
    if (currentRole.value(QStringLiteral("use_default_variables")).isUndefined()
        && !incomingRole.value(QStringLiteral("use_default_variables")).isUndefined()) {
        currentRole.insert(QStringLiteral("use_default_variables"), incomingRole.value(QStringLiteral("use_default_variables")));
    }
    if (!currentRole.value(QStringLiteral("settings")).isObject() && incomingRole.value(QStringLiteral("settings")).isObject()) {
        currentRole.insert(QStringLiteral("settings"), incomingRole.value(QStringLiteral("settings")));
    }
    for (const QString& field : {
            QStringLiteral("mode"),
            QStringLiteral("stateJournalMode"),
            QStringLiteral("has_state_journal_config"),
            QStringLiteral("display_policy"),
        }) {
        if (!incomingRole.value(field).isUndefined()) {
            currentRole.insert(field, incomingRole.value(field));
        }
    }
    const QString currentInitialStage = currentRole.value(QStringLiteral("initial_stage")).toString();
    if (currentInitialStage.trimmed().isEmpty() || currentInitialStage == QStringLiteral("stage_a")) {
        currentRole.insert(QStringLiteral("initial_stage"), incomingRole.value(QStringLiteral("initial_stage")).toString(currentInitialStage));
    }
    return currentRole;
}

QJsonObject mergeStateJournal(QJsonObject currentStateJournal, const QJsonObject& incomingStateJournal) {
    for (auto it = incomingStateJournal.constBegin(); it != incomingStateJournal.constEnd(); ++it) {
        if (it.key() == QStringLiteral("roles")) {
            continue;
        }
        currentStateJournal.insert(it.key(), it.value());
    }

    QJsonArray currentRoles = currentStateJournal.value(QStringLiteral("roles")).toArray();
    const QJsonArray incomingRoles = incomingStateJournal.value(QStringLiteral("roles")).toArray();
    for (const QJsonValue& value : incomingRoles) {
        if (!value.isObject()) {
            continue;
        }
        const QJsonObject incomingRole = value.toObject();
        const int index = findRoleIndex(currentRoles, incomingRole);
        if (index >= 0) {
            currentRoles.replace(index, mergeStateJournalRole(currentRoles.at(index).toObject(), incomingRole));
        } else {
            currentRoles.append(incomingRole);
        }
    }
    currentStateJournal.insert(QStringLiteral("roles"), currentRoles);
    return currentStateJournal;
}

QJsonArray projectMemoryItems(const QJsonObject& project) {
    return arrayFromValue(project.value(QStringLiteral("memory")), {
        QStringLiteral("items"),
        QStringLiteral("entries"),
        QStringLiteral("memories"),
    });
}

QString normalizedMemoryStatus(const QString& value) {
    return value.trimmed().toLower() == QStringLiteral("archived") ? QStringLiteral("archived") : QStringLiteral("active");
}

QJsonObject normalizedMemoryEntry(const QJsonObject& rawEntry, const QSet<QString>& existingIds, int index) {
    QJsonObject entry = rawEntry;
    QString id = textValue(entry, QStringLiteral("id"));
    if (id.isEmpty() || existingIds.contains(id)) {
        id = QStringLiteral("memory-card-authoring-%1").arg(QUuid::createUuid().toString(QUuid::WithoutBraces));
    }

    const QString title = textValue(entry, QStringLiteral("title"), QStringLiteral("记忆 %1").arg(index + 1), 160);
    const QString content = textValue(entry, QStringLiteral("content"), textValue(entry, QStringLiteral("summary")), 12000);
    if (content.isEmpty()) {
        return {};
    }

    const QString now = QDateTime::currentDateTime().toString(QStringLiteral("yyyy-MM-dd HH:mm:ss"));
    entry.insert(QStringLiteral("id"), id);
    entry.insert(QStringLiteral("title"), title);
    entry.insert(QStringLiteral("content"), content);
    entry.insert(QStringLiteral("notes"), textValue(entry, QStringLiteral("notes"), QString(), 2400));
    entry.insert(QStringLiteral("tags"), CardAuthoring::tagsArray(CardAuthoring::splitTags(entry.value(QStringLiteral("tags")))));
    entry.insert(QStringLiteral("memory_status"), normalizedMemoryStatus(entry.value(QStringLiteral("memory_status")).toString(entry.value(QStringLiteral("status")).toString(QStringLiteral("active")))));
    if (entry.value(QStringLiteral("created_at")).toString().trimmed().isEmpty()) {
        entry.insert(QStringLiteral("created_at"), now);
    }
    entry.insert(QStringLiteral("updated_at"), now);
    return entry;
}
}

CardAuthoringApplyPlanner::CardAuthoringApplyPlanner(QString rootPath)
    : paths_(std::move(rootPath)) {
}

QJsonObject CardAuthoringApplyPlanner::buildPreview(const QJsonObject& project, const QStringList& modules) const {
    QString errorMessage;
    const QJsonObject currentCard = readCurrentCard(&errorMessage);
    if (!errorMessage.isEmpty()) {
        return QJsonObject{ { QStringLiteral("ok"), false }, { QStringLiteral("message"), errorMessage } };
    }

    const CardAuthoringCompiler compiler;
    const QJsonObject compiledCard = compiler.compileRoleCard(project);
    const QStringList validationWarnings = compiler.validateProject(project);
    const QJsonObject beforeRaw = currentCard.value(QStringLiteral("raw")).toObject();
    const QJsonObject afterRaw = compiledCard.value(QStringLiteral("raw")).toObject();
    const QStringList selectedModules = normalizedModules(modules);

    QJsonArray groups;
    if (selectedModules.contains(QStringLiteral("persona"))) {
        QStringList personaFields = {
            QStringLiteral("name"),
            QStringLiteral("description"),
            QStringLiteral("personality"),
            QStringLiteral("scenario"),
            QStringLiteral("first_mes"),
            QStringLiteral("mes_example"),
            QStringLiteral("creator_notes"),
            QStringLiteral("creator_comment"),
            QStringLiteral("tags"),
            QStringLiteral("personas"),
        };
        if (afterRaw.contains(QStringLiteral("creativeWorkshop"))) {
            personaFields.append(QStringLiteral("creativeWorkshop"));
        }
        groups.append(buildGroup(
            QStringLiteral("persona"),
            QStringLiteral("主卡"),
            QStringLiteral("把写卡器里的人设主字段增量写回当前角色卡。"),
            buildChanges(beforeRaw, afterRaw, personaFields)));
    }
    if (selectedModules.contains(QStringLiteral("database"))) {
        const QJsonObject mergedDatabaseRaw = mergedCard(
            currentCard,
            compiledCard,
            QStringList{ QStringLiteral("database") }).value(QStringLiteral("raw")).toObject();
        groups.append(buildGroup(
            QStringLiteral("database"),
            QStringLiteral("角色卡数据库兼容字段"),
            QStringLiteral("把数据库草稿写入角色卡兼容字段；不写运行时 SQLite。"),
            buildChanges(beforeRaw, mergedDatabaseRaw, { QStringLiteral("stateJournal") })));
    }
    if (selectedModules.contains(QStringLiteral("worldbook"))) {
        QJsonObject currentWorldbook;
        if (!readJsonObjectFile(QStringLiteral("data/worldbook.json"), &currentWorldbook, &errorMessage)) {
            return QJsonObject{ { QStringLiteral("ok"), false }, { QStringLiteral("message"), errorMessage } };
        }
        groups.append(buildGroup(
            QStringLiteral("worldbook"),
            QStringLiteral("世界书词条"),
            QStringLiteral("把写卡器 worldbook 草稿和数据库外部标签消费者合并到 data/worldbook.json。"),
            buildDocumentChanges(
                QStringLiteral("worldbook"),
                QStringLiteral("世界书文件"),
                QStringLiteral("data/worldbook.json"),
                currentWorldbook,
                mergedWorldbookStore(currentWorldbook, project))));
    }
    if (selectedModules.contains(QStringLiteral("preset"))) {
        QJsonObject currentPreset;
        if (!readJsonObjectFile(QStringLiteral("data/preset.json"), &currentPreset, &errorMessage)) {
            return QJsonObject{ { QStringLiteral("ok"), false }, { QStringLiteral("message"), errorMessage } };
        }
        groups.append(buildGroup(
            QStringLiteral("preset"),
            QStringLiteral("预设内容"),
            QStringLiteral("只合并 active preset 的 modules、extra_prompts 和 prompt_groups；不覆盖高阶预设正文。"),
            buildDocumentChanges(
                QStringLiteral("preset"),
                QStringLiteral("预设文件"),
                QStringLiteral("data/preset.json"),
                currentPreset,
                mergedPresetStore(currentPreset, project))));
    }
    if (selectedModules.contains(QStringLiteral("memory"))) {
        const QString memoryRelativePath = currentMemoryRelativePath(currentCard);
        QJsonArray currentMemories;
        if (!readJsonArrayFile(memoryRelativePath, &currentMemories, &errorMessage)) {
            return QJsonObject{ { QStringLiteral("ok"), false }, { QStringLiteral("message"), errorMessage } };
        }
        groups.append(buildGroup(
            QStringLiteral("memory"),
            QStringLiteral("当前角色记忆"),
            QStringLiteral("只向当前角色 memories.json 追加写卡器记忆，不触碰合并记忆和记忆大纲。"),
            buildDocumentChanges(
                QStringLiteral("memory"),
                QStringLiteral("当前角色记忆文件"),
                memoryRelativePath,
                currentMemories,
                mergedMemoryEntries(currentMemories, project))));
    }

    int changeCount = 0;
    for (const QJsonValue& groupValue : groups) {
        changeCount += groupValue.toObject().value(QStringLiteral("item_count")).toInt();
    }

    QJsonArray warnings;
    for (const QString& warning : validationWarnings) {
        warnings.append(warningObject(warning, warningText(warning)));
    }
    if (changeCount == 0) {
        warnings.append(warningObject(
            QStringLiteral("no_changes"),
            QStringLiteral("当前选择的模块不会修改任何运行时文件。"),
            QStringLiteral("info")));
    }

    return QJsonObject{
        { QStringLiteral("ok"), true },
        { QStringLiteral("groups"), groups },
        { QStringLiteral("warnings"), warnings },
        { QStringLiteral("summary"), QJsonObject{
            { QStringLiteral("group_count"), groups.size() },
            { QStringLiteral("change_count"), changeCount },
            { QStringLiteral("warning_count"), warnings.size() },
        } },
    };
}

QJsonObject CardAuthoringApplyPlanner::applySelected(const QJsonObject& project, const QStringList& selectedGroupIds) const {
    const QJsonObject preview = buildPreview(project, selectedGroupIds);
    if (!preview.value(QStringLiteral("ok")).toBool()) {
        return preview;
    }

    QSet<QString> selected;
    for (const QString& groupId : selectedGroupIds) {
        if (!groupId.trimmed().isEmpty()) {
            selected.insert(groupId.trimmed());
        }
    }

    QStringList groupIds;
    const QJsonArray groups = preview.value(QStringLiteral("groups")).toArray();
    for (const QJsonValue& value : groups) {
        const QJsonObject group = value.toObject();
        const QString id = group.value(QStringLiteral("id")).toString();
        if ((selected.isEmpty() || selected.contains(id)) && group.value(QStringLiteral("item_count")).toInt() > 0) {
            groupIds.append(id);
        }
    }
    if (groupIds.isEmpty()) {
        return QJsonObject{
            { QStringLiteral("ok"), true },
            { QStringLiteral("applied"), QJsonArray{} },
            { QStringLiteral("backups"), QJsonArray{} },
            { QStringLiteral("preview"), preview },
        };
    }

    QString errorMessage;
    QList<RuntimeWrite> writes;
    if (groupIds.contains(QStringLiteral("persona")) || groupIds.contains(QStringLiteral("database"))) {
        const CardAuthoringCompiler compiler;
        const QJsonObject currentCard = readCurrentCard(&errorMessage);
        if (!errorMessage.isEmpty()) {
            return QJsonObject{ { QStringLiteral("ok"), false }, { QStringLiteral("message"), errorMessage } };
        }
        const QJsonObject nextCard = mergedCard(currentCard, compiler.compileRoleCard(project), groupIds);
        if (CardAuthoring::stableJson(currentCard) != CardAuthoring::stableJson(nextCard)) {
            writes.append(RuntimeWrite{ CardAuthoringPaths::currentRoleCardRelativePath(), QJsonDocument(nextCard) });
        }
    }
    if (groupIds.contains(QStringLiteral("worldbook"))) {
        QJsonObject currentWorldbook;
        if (!readJsonObjectFile(QStringLiteral("data/worldbook.json"), &currentWorldbook, &errorMessage)) {
            return QJsonObject{ { QStringLiteral("ok"), false }, { QStringLiteral("message"), errorMessage } };
        }
        const QJsonObject nextWorldbook = mergedWorldbookStore(currentWorldbook, project);
        if (CardAuthoring::stableJson(currentWorldbook) != CardAuthoring::stableJson(nextWorldbook)) {
            writes.append(RuntimeWrite{ QStringLiteral("data/worldbook.json"), QJsonDocument(nextWorldbook) });
        }
    }
    if (groupIds.contains(QStringLiteral("preset"))) {
        QJsonObject currentPreset;
        if (!readJsonObjectFile(QStringLiteral("data/preset.json"), &currentPreset, &errorMessage)) {
            return QJsonObject{ { QStringLiteral("ok"), false }, { QStringLiteral("message"), errorMessage } };
        }
        const QJsonObject nextPreset = mergedPresetStore(currentPreset, project);
        if (CardAuthoring::stableJson(currentPreset) != CardAuthoring::stableJson(nextPreset)) {
            writes.append(RuntimeWrite{ QStringLiteral("data/preset.json"), QJsonDocument(nextPreset) });
        }
    }
    if (groupIds.contains(QStringLiteral("memory"))) {
        const QJsonObject currentCard = readCurrentCard(&errorMessage);
        if (!errorMessage.isEmpty()) {
            return QJsonObject{ { QStringLiteral("ok"), false }, { QStringLiteral("message"), errorMessage } };
        }
        const QString memoryRelativePath = currentMemoryRelativePath(currentCard);
        QJsonArray currentMemories;
        if (!readJsonArrayFile(memoryRelativePath, &currentMemories, &errorMessage)) {
            return QJsonObject{ { QStringLiteral("ok"), false }, { QStringLiteral("message"), errorMessage } };
        }
        const QJsonArray nextMemories = mergedMemoryEntries(currentMemories, project);
        if (CardAuthoring::stableJson(currentMemories) != CardAuthoring::stableJson(nextMemories)) {
            writes.append(RuntimeWrite{ memoryRelativePath, QJsonDocument(nextMemories) });
        }
    }

    QJsonArray backups;
    for (const RuntimeWrite& write : writes) {
        const QString backupPath = backupRuntimeFile(write.relativePath, &errorMessage);
        if (!errorMessage.isEmpty()) {
            return QJsonObject{ { QStringLiteral("ok"), false }, { QStringLiteral("message"), errorMessage } };
        }
        if (!backupPath.isEmpty()) {
            backups.append(backupPath);
        }
    }
    for (const RuntimeWrite& write : writes) {
        if (!writeJsonDocumentFile(write.relativePath, write.document, &errorMessage)) {
            return QJsonObject{ { QStringLiteral("ok"), false }, { QStringLiteral("message"), errorMessage }, { QStringLiteral("backups"), backups } };
        }
    }

    QJsonArray applied;
    for (const QString& groupId : groupIds) {
        applied.append(groupId);
    }
    return QJsonObject{
        { QStringLiteral("ok"), true },
        { QStringLiteral("applied"), applied },
        { QStringLiteral("backups"), backups },
        { QStringLiteral("preview"), preview },
    };
}

QJsonObject CardAuthoringApplyPlanner::readCurrentCard(QString* errorMessage) const {
    QFile file(paths_.currentRoleCardPath());
    if (!file.exists()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("current_role_card.json missing: %1").arg(paths_.currentRoleCardPath());
        }
        return {};
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("current_role_card.json read failed: %1").arg(file.errorString());
        }
        return {};
    }
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("current_role_card.json invalid: %1").arg(error.errorString());
        }
        return {};
    }
    return document.object();
}

bool CardAuthoringApplyPlanner::readJsonObjectFile(const QString& relativePath, QJsonObject* object, QString* errorMessage) const {
    if (object) {
        *object = {};
    }
    const QString path = QDir(paths_.rootPath()).absoluteFilePath(relativePath);
    QFile file(path);
    if (!file.exists()) {
        return true;
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("%1 read failed: %2").arg(relativePath, file.errorString());
        }
        return false;
    }
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("%1 invalid: %2").arg(relativePath, error.errorString());
        }
        return false;
    }
    if (object) {
        *object = document.object();
    }
    return true;
}

bool CardAuthoringApplyPlanner::readJsonArrayFile(const QString& relativePath, QJsonArray* array, QString* errorMessage) const {
    if (array) {
        *array = {};
    }
    const QString path = QDir(paths_.rootPath()).absoluteFilePath(relativePath);
    QFile file(path);
    if (!file.exists()) {
        return true;
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("%1 read failed: %2").arg(relativePath, file.errorString());
        }
        return false;
    }
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isArray()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("%1 invalid: %2").arg(relativePath, error.errorString());
        }
        return false;
    }
    if (array) {
        *array = document.array();
    }
    return true;
}

bool CardAuthoringApplyPlanner::writeJsonDocumentFile(const QString& relativePath, const QJsonDocument& document, QString* errorMessage) const {
    const QString path = QDir(paths_.rootPath()).absoluteFilePath(relativePath);
    const QFileInfo fileInfo(path);
    QDir parentDir = fileInfo.absoluteDir();
    if (!parentDir.exists() && !parentDir.mkpath(QStringLiteral("."))) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("failed to create parent directory for %1").arg(relativePath);
        }
        return false;
    }

    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("%1 write failed: %2").arg(relativePath, file.errorString());
        }
        return false;
    }
    file.write(document.toJson(QJsonDocument::Indented));
    if (!file.commit()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("%1 commit failed: %2").arg(relativePath, file.errorString());
        }
        return false;
    }
    return true;
}

QString CardAuthoringApplyPlanner::backupRuntimeFile(const QString& relativePath, QString* errorMessage) const {
    if (errorMessage) {
        errorMessage->clear();
    }
    if (!paths_.ensureRuntimeDirectories(errorMessage)) {
        return {};
    }

    const QString sourcePath = QDir(paths_.rootPath()).absoluteFilePath(relativePath);
    const QFileInfo source(sourcePath);
    if (!source.exists()) {
        return {};
    }

    const QString backupDirPath = QDir(paths_.backupsPath()).absoluteFilePath(QDateTime::currentDateTimeUtc().toString(QStringLiteral("yyyyMMdd_HHmmss_zzz")));
    QDir root(paths_.rootPath());
    if (!root.mkpath(root.relativeFilePath(backupDirPath))) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("failed to create card authoring backup directory: %1").arg(backupDirPath);
        }
        return {};
    }

    QString backupName = relativePath;
    backupName.replace(QRegularExpression(QStringLiteral("[\\\\/:]+")), QStringLiteral("__"));
    if (backupName.trimmed().isEmpty()) {
        backupName = QStringLiteral("runtime.json");
    }
    const QString targetPath = QDir(backupDirPath).absoluteFilePath(backupName);
    if (!QFile::copy(source.absoluteFilePath(), targetPath)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("failed to backup %1").arg(relativePath);
        }
        return {};
    }
    return targetPath;
}

QString CardAuthoringApplyPlanner::memoryCardUid(const QJsonObject& currentCard) const {
    const QJsonObject raw = currentCard.value(QStringLiteral("raw")).toObject();
    const QJsonObject stateJournal = raw.value(QStringLiteral("stateJournal")).toObject();
    const QStringList candidates = {
        currentCard.value(QStringLiteral("card_uid")).toString(),
        stateJournal.value(QStringLiteral("card_uid")).toString(),
        raw.value(QStringLiteral("card_uid")).toString(),
        raw.value(QStringLiteral("uid")).toString(),
        raw.value(QStringLiteral("id")).toString(),
    };
    for (const QString& candidate : candidates) {
        const QString runtimeKey = normalizedRuntimeKey(candidate);
        if (!runtimeKey.trimmed().isEmpty() && runtimeKey != QStringLiteral("global")) {
            return runtimeKey;
        }
    }
    return QStringLiteral("global");
}

QString CardAuthoringApplyPlanner::currentMemoryRelativePath(const QJsonObject& currentCard) const {
    const QString runtimeKey = memoryCardUid(currentCard);
    const QString primaryRelativePath = QStringLiteral("data/card_runtime/cards/%1/memories.json").arg(runtimeKey);
    const QString legacyRelativePath = QStringLiteral("data/memories.json");
    const QDir root(paths_.rootPath());
    if (QFileInfo::exists(root.absoluteFilePath(primaryRelativePath))
        || !QFileInfo::exists(root.absoluteFilePath(legacyRelativePath))) {
        return primaryRelativePath;
    }
    return legacyRelativePath;
}

QJsonArray CardAuthoringApplyPlanner::buildChanges(const QJsonObject& beforeRaw, const QJsonObject& afterRaw, const QStringList& fields) const {
    QJsonArray changes;
    for (const QString& field : fields) {
        const QJsonValue before = beforeRaw.value(field);
        const QJsonValue after = afterRaw.value(field);
        if (CardAuthoring::stableJson(before) == CardAuthoring::stableJson(after)) {
            continue;
        }
        const QString beforePreview = clippedPreview(before);
        const QString afterPreview = clippedPreview(after);
        changes.append(QJsonObject{
            { QStringLiteral("field"), field },
            { QStringLiteral("label"), fieldLabel(field) },
            { QStringLiteral("path"), QStringLiteral("raw.%1").arg(field) },
            { QStringLiteral("action"), changeAction(before, after) },
            { QStringLiteral("value_kind"), valueKind(after.isUndefined() ? before : after) },
            { QStringLiteral("before_preview"), beforePreview },
            { QStringLiteral("after_preview"), afterPreview },
            { QStringLiteral("before_size"), compactJson(before).size() },
            { QStringLiteral("after_size"), compactJson(after).size() },
            { QStringLiteral("large"), beforePreview.endsWith(QStringLiteral("…")) || afterPreview.endsWith(QStringLiteral("…")) },
        });
    }
    return changes;
}

QJsonArray CardAuthoringApplyPlanner::buildDocumentChanges(const QString& field, const QString& label, const QString& path, const QJsonValue& before, const QJsonValue& after) const {
    if (CardAuthoring::stableJson(before) == CardAuthoring::stableJson(after)) {
        return {};
    }
    const QString beforePreview = clippedPreview(before);
    const QString afterPreview = clippedPreview(after);
    return QJsonArray{
        QJsonObject{
            { QStringLiteral("field"), field },
            { QStringLiteral("label"), label },
            { QStringLiteral("path"), path },
            { QStringLiteral("action"), changeAction(before, after) },
            { QStringLiteral("value_kind"), valueKind(after.isUndefined() ? before : after) },
            { QStringLiteral("before_preview"), beforePreview },
            { QStringLiteral("after_preview"), afterPreview },
            { QStringLiteral("before_size"), compactJson(before).size() },
            { QStringLiteral("after_size"), compactJson(after).size() },
            { QStringLiteral("large"), beforePreview.endsWith(QStringLiteral("…")) || afterPreview.endsWith(QStringLiteral("…")) },
        },
    };
}

QJsonObject CardAuthoringApplyPlanner::buildGroup(const QString& id, const QString& title, const QString& description, const QJsonArray& changes) const {
    return QJsonObject{
        { QStringLiteral("id"), id },
        { QStringLiteral("module"), id },
        { QStringLiteral("title"), title },
        { QStringLiteral("description"), description },
        { QStringLiteral("changes"), changes },
        { QStringLiteral("item_count"), changes.size() },
        { QStringLiteral("has_changes"), changes.size() > 0 },
    };
}

QStringList CardAuthoringApplyPlanner::normalizedModules(const QStringList& modules) const {
    QStringList selected;
    const QSet<QString> accepted = {
        QStringLiteral("persona"),
        QStringLiteral("database"),
        QStringLiteral("worldbook"),
        QStringLiteral("preset"),
        QStringLiteral("memory"),
    };
    for (const QString& module : modules) {
        const QString normalized = module.trimmed();
        if (accepted.contains(normalized) && !selected.contains(normalized)) {
            selected.append(normalized);
        }
    }
    return selected.isEmpty() ? QStringList{ QStringLiteral("persona"), QStringLiteral("database") } : selected;
}

QJsonObject CardAuthoringApplyPlanner::mergedCard(const QJsonObject& currentCard, const QJsonObject& compiledCard, const QStringList& groupIds) const {
    QJsonObject nextCard = currentCard;
    QJsonObject nextRaw = currentCard.value(QStringLiteral("raw")).toObject();
    const QJsonObject compiledRaw = compiledCard.value(QStringLiteral("raw")).toObject();

    if (groupIds.contains(QStringLiteral("persona"))) {
        const QStringList fields = {
            QStringLiteral("name"),
            QStringLiteral("description"),
            QStringLiteral("personality"),
            QStringLiteral("scenario"),
            QStringLiteral("first_mes"),
            QStringLiteral("mes_example"),
            QStringLiteral("creator_notes"),
            QStringLiteral("creator_comment"),
            QStringLiteral("tags"),
            QStringLiteral("personas"),
        };
        for (const QString& field : fields) {
            nextRaw.insert(field, compiledRaw.value(field));
        }
        if (compiledRaw.contains(QStringLiteral("creativeWorkshop"))) {
            nextRaw.insert(QStringLiteral("creativeWorkshop"), compiledRaw.value(QStringLiteral("creativeWorkshop")));
        }
    }
    if (groupIds.contains(QStringLiteral("database"))) {
        const QJsonObject compiledStateJournal = compiledRaw.value(QStringLiteral("stateJournal")).toObject();
        nextRaw.insert(QStringLiteral("stateJournal"), mergeStateJournal(nextRaw.value(QStringLiteral("stateJournal")).toObject(), compiledStateJournal));
    }
    nextCard.insert(QStringLiteral("raw"), nextRaw);
    return nextCard;
}

QJsonObject CardAuthoringApplyPlanner::mergedWorldbookStore(const QJsonObject& currentStore, const QJsonObject& project) const {
    QJsonArray incomingEntries = projectWorldbookEntries(project);
    const QJsonArray databaseEntries = databaseGeneratedWorldbookEntries(project);
    for (const QJsonValue& value : databaseEntries) {
        incomingEntries.append(value);
    }
    if (incomingEntries.isEmpty()) {
        return currentStore;
    }

    QJsonObject nextStore = currentStore;
    if (!nextStore.value(QStringLiteral("settings")).isObject()) {
        nextStore.insert(QStringLiteral("settings"), defaultWorldbookSettings());
    }
    QJsonArray entries = nextStore.value(QStringLiteral("entries")).toArray();
    bool changed = false;
    for (const QJsonValue& value : incomingEntries) {
        if (!value.isObject()) {
            continue;
        }
        const QJsonObject rawEntry = value.toObject();
        const QString id = textValue(rawEntry, QStringLiteral("id"));
        const int existingIndex = findObjectById(entries, id);
        const QJsonObject currentEntry = existingIndex >= 0 ? entries.at(existingIndex).toObject() : QJsonObject{};
        const QJsonObject normalized = normalizedWorldbookEntry(rawEntry, currentEntry, existingIndex >= 0 ? existingIndex : entries.size());
        if (normalized.isEmpty()) {
            continue;
        }
        if (existingIndex >= 0) {
            entries.replace(existingIndex, normalized);
        } else {
            entries.append(normalized);
        }
        changed = true;
    }
    if (!changed) {
        return currentStore;
    }
    nextStore.insert(QStringLiteral("entries"), entries);
    return nextStore;
}

QJsonObject CardAuthoringApplyPlanner::mergedPresetStore(const QJsonObject& currentStore, const QJsonObject& project) const {
    const QJsonObject sourcePreset = projectPresetSource(project);
    if (!hasPresetPayload(sourcePreset)) {
        return currentStore;
    }

    QJsonObject nextStore = currentStore;
    QJsonArray presets = nextStore.value(QStringLiteral("presets")).toArray();
    if (presets.isEmpty()) {
        const QString newPresetId = textValue(sourcePreset, QStringLiteral("id"), QStringLiteral("card-authoring-preset"));
        presets.append(QJsonObject{
            { QStringLiteral("id"), newPresetId },
            { QStringLiteral("name"), QStringLiteral("写卡器预设") },
            { QStringLiteral("enabled"), true },
            { QStringLiteral("modules"), QJsonObject{} },
            { QStringLiteral("extra_prompts"), QJsonArray{} },
            { QStringLiteral("prompt_groups"), QJsonArray{} },
        });
        nextStore.insert(QStringLiteral("active_preset_id"), newPresetId);
    }

    QString activePresetId = nextStore.value(QStringLiteral("active_preset_id")).toString();
    int activeIndex = findObjectById(presets, activePresetId);
    if (activeIndex < 0) {
        activeIndex = 0;
        activePresetId = presets.first().toObject().value(QStringLiteral("id")).toString();
    }

    QJsonObject activePreset = presets.at(activeIndex).toObject();
    QJsonObject modules = activePreset.value(QStringLiteral("modules")).toObject();
    const QJsonObject sourceModules = sourcePreset.value(QStringLiteral("modules")).toObject();
    for (auto it = sourceModules.constBegin(); it != sourceModules.constEnd(); ++it) {
        modules.insert(it.key(), it.value().toBool());
    }
    applyPresetModuleMutex(&modules);
    activePreset.insert(QStringLiteral("modules"), modules);
    activePreset.insert(
        QStringLiteral("extra_prompts"),
        mergeObjectArrayById(
            activePreset.value(QStringLiteral("extra_prompts")).toArray(),
            sourcePreset.value(QStringLiteral("extra_prompts")).toArray(),
            QStringLiteral("extra-prompt")));
    activePreset.insert(
        QStringLiteral("prompt_groups"),
        mergeObjectArrayById(
            activePreset.value(QStringLiteral("prompt_groups")).toArray(),
            sourcePreset.value(QStringLiteral("prompt_groups")).toArray(),
            QStringLiteral("prompt-group")));

    presets.replace(activeIndex, activePreset);
    nextStore.insert(QStringLiteral("presets"), presets);
    if (!activePresetId.isEmpty()) {
        nextStore.insert(QStringLiteral("active_preset_id"), activePresetId);
    }
    return nextStore;
}

QJsonArray CardAuthoringApplyPlanner::mergedMemoryEntries(const QJsonArray& currentEntries, const QJsonObject& project) const {
    const QJsonArray incomingItems = projectMemoryItems(project);
    if (incomingItems.isEmpty()) {
        return currentEntries;
    }

    QJsonArray nextEntries = currentEntries;
    QSet<QString> existingIds;
    for (const QJsonValue& value : nextEntries) {
        const QString id = value.toObject().value(QStringLiteral("id")).toString();
        if (!id.isEmpty()) {
            existingIds.insert(id);
        }
    }
    for (const QJsonValue& value : incomingItems) {
        if (!value.isObject()) {
            continue;
        }
        const QJsonObject entry = normalizedMemoryEntry(value.toObject(), existingIds, nextEntries.size());
        if (entry.isEmpty()) {
            continue;
        }
        existingIds.insert(entry.value(QStringLiteral("id")).toString());
        nextEntries.append(entry);
    }
    return nextEntries;
}
