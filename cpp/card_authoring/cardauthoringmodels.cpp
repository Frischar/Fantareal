#include "card_authoring/cardauthoringmodels.h"

#include <QJsonDocument>
#include <QRegularExpression>
#include <QSet>

namespace {
bool boolValue(const QJsonValue& value, bool fallback = false) {
    if (value.isBool()) {
        return value.toBool();
    }
    const QString text = CardAuthoring::normalizedText(value).toLower();
    if (text == QStringLiteral("1") || text == QStringLiteral("true") || text == QStringLiteral("yes") || text == QStringLiteral("on")) {
        return true;
    }
    if (text.isEmpty()) {
        return fallback;
    }
    if (text == QStringLiteral("0") || text == QStringLiteral("false") || text == QStringLiteral("no") || text == QStringLiteral("off")) {
        return false;
    }
    return fallback;
}

int intValue(const QJsonValue& value, int fallback = 0) {
    if (value.isDouble()) {
        return value.toInt(fallback);
    }
    bool ok = false;
    const int parsed = CardAuthoring::normalizedText(value).toInt(&ok);
    return ok ? parsed : fallback;
}

double doubleValue(const QJsonValue& value, double fallback = 0.0) {
    if (value.isDouble()) {
        return value.toDouble(fallback);
    }
    bool ok = false;
    const double parsed = CardAuthoring::normalizedText(value).toDouble(&ok);
    return ok ? parsed : fallback;
}

QString idOrDefault(const QJsonObject& payload, const QString& key, const QString& fallback) {
    const QString value = CardAuthoring::normalizedText(payload.value(key));
    return value.isEmpty() ? fallback : value;
}
}

namespace CardAuthoring {

QString importedDatabaseTag(QString value);

QString projectType() {
    return QStringLiteral("fantareal_card_authoring_project");
}

QString legacyProjectType() {
    return QStringLiteral("fantareal_card_writer_project");
}

int projectVersion() {
    return 1;
}

QString normalizedText(const QJsonValue& value) {
    QString text;
    if (value.isString()) {
        text = value.toString();
    } else if (value.isDouble()) {
        text = QString::number(value.toDouble(), 'g', 12);
    } else if (value.isBool()) {
        text = value.toBool() ? QStringLiteral("true") : QStringLiteral("false");
    }
    text.replace(QStringLiteral("\r\n"), QStringLiteral("\n"));
    text.replace(QLatin1Char('\r'), QLatin1Char('\n'));
    return text.trimmed();
}

QStringList splitTags(const QJsonValue& value) {
    QStringList tags;
    if (value.isArray()) {
        const QJsonArray array = value.toArray();
        for (const QJsonValue& item : array) {
            const QString tag = normalizedText(item);
            if (!tag.isEmpty() && !tags.contains(tag)) {
                tags.append(tag);
            }
        }
        return tags;
    }

    const QString text = normalizedText(value);
    for (const QString& part : text.split(QRegularExpression(QStringLiteral("[,，、;；\\n]+")), Qt::SkipEmptyParts)) {
        const QString tag = part.trimmed();
        if (!tag.isEmpty() && !tags.contains(tag)) {
            tags.append(tag);
        }
    }
    return tags;
}

QJsonArray tagsArray(const QStringList& tags) {
    QJsonArray array;
    for (const QString& tag : tags) {
        if (!tag.trimmed().isEmpty()) {
            array.append(tag.trimmed());
        }
    }
    return array;
}

QString stableJson(const QJsonValue& value) {
    return QString::fromUtf8(QJsonDocument(QJsonArray{ value }).toJson(QJsonDocument::Compact));
}

QJsonObject normalizePersonasMap(const QJsonValue& value);

QJsonObject normalizeWorkshopItem(const QJsonObject& payload, int index) {
    QJsonObject item;
    item.insert(QStringLiteral("id"), idOrDefault(payload, QStringLiteral("id"), QStringLiteral("workshop_%1").arg(index + 1, 3, 10, QLatin1Char('0'))));
    item.insert(QStringLiteral("name"), normalizedText(payload.value(QStringLiteral("name"))));
    item.insert(QStringLiteral("enabled"), boolValue(payload.value(QStringLiteral("enabled")), true));
    item.insert(QStringLiteral("triggerMode"), idOrDefault(payload, QStringLiteral("triggerMode"), QStringLiteral("manual")));
    item.insert(QStringLiteral("triggerStage"), normalizedText(payload.value(QStringLiteral("triggerStage"))));
    item.insert(QStringLiteral("triggerTempMin"), intValue(payload.value(QStringLiteral("triggerTempMin")), 0));
    item.insert(QStringLiteral("triggerTempMax"), intValue(payload.value(QStringLiteral("triggerTempMax")), 1));
    item.insert(QStringLiteral("actionType"), idOrDefault(payload, QStringLiteral("actionType"), QStringLiteral("note")));
    item.insert(QStringLiteral("popupTitle"), normalizedText(payload.value(QStringLiteral("popupTitle"))));
    item.insert(QStringLiteral("musicPreset"), normalizedText(payload.value(QStringLiteral("musicPreset"))));
    item.insert(QStringLiteral("musicUrl"), normalizedText(payload.value(QStringLiteral("musicUrl"))));
    item.insert(QStringLiteral("autoplay"), boolValue(payload.value(QStringLiteral("autoplay")), false));
    item.insert(QStringLiteral("loop"), boolValue(payload.value(QStringLiteral("loop")), false));
    item.insert(QStringLiteral("volume"), doubleValue(payload.value(QStringLiteral("volume")), 0.7));
    item.insert(QStringLiteral("imageUrl"), normalizedText(payload.value(QStringLiteral("imageUrl"))));
    item.insert(QStringLiteral("imageAlt"), normalizedText(payload.value(QStringLiteral("imageAlt"))));
    item.insert(QStringLiteral("note"), normalizedText(payload.value(QStringLiteral("note"))));
    return item;
}

QJsonObject normalizeCreativeWorkshop(const QJsonValue& value) {
    const QJsonObject raw = value.toObject();
    QJsonArray items;
    const QJsonArray rawItems = raw.value(QStringLiteral("items")).toArray();
    for (int i = 0; i < rawItems.size(); ++i) {
        if (rawItems.at(i).isObject()) {
            items.append(normalizeWorkshopItem(rawItems.at(i).toObject(), i));
        }
    }
    return QJsonObject{
        { QStringLiteral("enabled"), boolValue(raw.value(QStringLiteral("enabled")), true) },
        { QStringLiteral("items"), items },
    };
}

QJsonObject normalizePersonaCard(const QJsonObject& payload) {
    QJsonObject persona;
    const QStringList fields = {
        QStringLiteral("name"),
        QStringLiteral("description"),
        QStringLiteral("personality"),
        QStringLiteral("scenario"),
        QStringLiteral("first_mes"),
        QStringLiteral("mes_example"),
        QStringLiteral("creator_notes"),
        QStringLiteral("creator_comment"),
    };
    for (const QString& field : fields) {
        persona.insert(field, normalizedText(payload.value(field)));
    }
    persona.insert(QStringLiteral("tags"), tagsArray(splitTags(payload.value(QStringLiteral("tags")))));
    if (payload.contains(QStringLiteral("creativeWorkshop"))) {
        persona.insert(QStringLiteral("creativeWorkshop"), normalizeCreativeWorkshop(payload.value(QStringLiteral("creativeWorkshop"))));
    }
    const QJsonObject personas = normalizePersonasMap(payload.value(QStringLiteral("personas")));
    persona.insert(QStringLiteral("personas"), personas.isEmpty() ? QJsonObject{} : personas);
    return persona;
}

QJsonObject defaultMultiRolePersonas() {
    QJsonObject personas;
    for (int i = 1; i <= 3; ++i) {
        personas.insert(QString::number(i), QJsonObject{
            { QStringLiteral("name"), QString() },
            { QStringLiteral("description"), QString() },
            { QStringLiteral("personality"), QString() },
            { QStringLiteral("scenario"), QString() },
            { QStringLiteral("creator_notes"), QString() },
            { QStringLiteral("tags"), QJsonArray{} },
        });
    }
    return personas;
}

QJsonObject normalizeWorldbookEntry(const QJsonObject& payload, int index) {
    QJsonObject entry = payload;
    const QString id = idOrDefault(entry, QStringLiteral("id"), QStringLiteral("wb_%1").arg(index + 1, 3, 10, QLatin1Char('0')));
    const QString trigger = normalizedText(entry.value(QStringLiteral("trigger")));
    QString entryType = normalizedText(entry.value(QStringLiteral("entry_type"))).toLower();
    if (entryType != QStringLiteral("external_tag") && entryType != QStringLiteral("constant") && entryType != QStringLiteral("keyword")) {
        entryType = trigger.isEmpty() ? QStringLiteral("constant") : QStringLiteral("keyword");
    }
    entry.insert(QStringLiteral("id"), id);
    entry.insert(QStringLiteral("title"), idOrDefault(entry, QStringLiteral("title"), trigger.isEmpty() ? QStringLiteral("世界书词条 %1").arg(index + 1) : trigger));
    entry.insert(QStringLiteral("trigger"), trigger);
    entry.insert(QStringLiteral("secondary_trigger"), normalizedText(entry.value(QStringLiteral("secondary_trigger"))));
    entry.insert(QStringLiteral("entry_type"), entryType);
    entry.insert(QStringLiteral("content"), normalizedText(entry.value(QStringLiteral("content"))));
    entry.insert(QStringLiteral("group"), normalizedText(entry.value(QStringLiteral("group"))));
    entry.insert(QStringLiteral("comment"), normalizedText(entry.value(QStringLiteral("comment"))));
    entry.insert(QStringLiteral("enabled"), boolValue(entry.value(QStringLiteral("enabled")), true));
    if (!entry.contains(QStringLiteral("order"))) {
        entry.insert(QStringLiteral("order"), index);
    }
    return entry;
}

QJsonObject normalizeWorldbook(const QJsonObject& payload) {
    QJsonObject worldbook = payload;
    QJsonArray entries;
    const QJsonArray rawEntries = payload.value(QStringLiteral("entries")).toArray();
    for (int i = 0; i < rawEntries.size(); ++i) {
        entries.append(normalizeWorldbookEntry(rawEntries.at(i).toObject(), i));
    }
    worldbook.insert(QStringLiteral("entries"), entries);
    if (!worldbook.contains(QStringLiteral("settings"))) {
        worldbook.insert(QStringLiteral("settings"), QJsonObject{});
    }
    return worldbook;
}

QJsonObject normalizeMemoryItem(const QJsonObject& payload, int index) {
    QJsonObject item = payload;
    item.insert(QStringLiteral("id"), idOrDefault(item, QStringLiteral("id"), QStringLiteral("memory_%1").arg(index + 1, 3, 10, QLatin1Char('0'))));
    item.insert(QStringLiteral("title"), normalizedText(item.value(QStringLiteral("title"))));
    item.insert(QStringLiteral("content"), normalizedText(item.value(QStringLiteral("content"))));
    item.insert(QStringLiteral("tags"), tagsArray(splitTags(item.value(QStringLiteral("tags")))));
    item.insert(QStringLiteral("notes"), normalizedText(item.value(QStringLiteral("notes"))));
    item.insert(QStringLiteral("memory_status"), normalizedText(item.value(QStringLiteral("memory_status"))).toLower() == QStringLiteral("archived")
            ? QStringLiteral("archived")
            : QStringLiteral("active"));
    return item;
}

QJsonObject normalizeMemory(const QJsonObject& payload) {
    QJsonObject memory = payload;
    QJsonArray items;
    const QJsonArray rawItems = payload.value(QStringLiteral("items")).toArray();
    for (int i = 0; i < rawItems.size(); ++i) {
        items.append(normalizeMemoryItem(rawItems.at(i).toObject(), i));
    }
    memory.insert(QStringLiteral("items"), items);
    return memory;
}

QJsonObject normalizePresetItem(const QJsonObject& payload, int index) {
    QJsonObject item = payload;
    item.insert(QStringLiteral("id"), idOrDefault(item, QStringLiteral("id"), QStringLiteral("preset_%1").arg(index + 1, 3, 10, QLatin1Char('0'))));
    item.insert(QStringLiteral("name"), idOrDefault(item, QStringLiteral("name"), normalizedText(item.value(QStringLiteral("title")))));
    item.insert(QStringLiteral("content"), normalizedText(item.value(QStringLiteral("content"))));
    item.insert(QStringLiteral("base_system_prompt"), idOrDefault(item, QStringLiteral("base_system_prompt"), normalizedText(item.value(QStringLiteral("content")))));
    item.insert(QStringLiteral("enabled"), boolValue(item.value(QStringLiteral("enabled")), true));
    item.insert(QStringLiteral("modules"), item.value(QStringLiteral("modules")).toObject());
    item.insert(QStringLiteral("extra_prompts"), item.value(QStringLiteral("extra_prompts")).toArray());
    item.insert(QStringLiteral("prompt_groups"), item.value(QStringLiteral("prompt_groups")).toArray());
    return item;
}

QJsonObject normalizePreset(const QJsonObject& payload) {
    QJsonObject preset = payload;
    QJsonArray presets;
    const QJsonArray rawPresets = payload.value(QStringLiteral("presets")).toArray();
    for (int i = 0; i < rawPresets.size(); ++i) {
        presets.append(normalizePresetItem(rawPresets.at(i).toObject(), i));
    }
    QString activePresetId = normalizedText(payload.value(QStringLiteral("active_preset_id")));
    if (activePresetId.isEmpty() && !presets.isEmpty()) {
        activePresetId = presets.first().toObject().value(QStringLiteral("id")).toString();
    }
    preset.insert(QStringLiteral("active_preset_id"), activePresetId);
    preset.insert(QStringLiteral("presets"), presets);
    return preset;
}

QJsonObject normalizeDatabaseVariable(const QJsonObject& payload, int index) {
    QJsonObject variable;
    variable.insert(QStringLiteral("id"), idOrDefault(payload, QStringLiteral("id"), QStringLiteral("db_var_%1").arg(index + 1, 3, 10, QLatin1Char('0'))));
    variable.insert(QStringLiteral("key"), normalizedText(payload.value(QStringLiteral("key"))));
    variable.insert(QStringLiteral("label"), normalizedText(payload.value(QStringLiteral("label"))));
    variable.insert(QStringLiteral("value_type"), idOrDefault(payload, QStringLiteral("value_type"), QStringLiteral("text")));
    variable.insert(QStringLiteral("initial_value"), normalizedText(payload.value(QStringLiteral("initial_value"))));
    variable.insert(QStringLiteral("scope"), idOrDefault(payload, QStringLiteral("scope"), QStringLiteral("role")));
    variable.insert(QStringLiteral("description"), normalizedText(payload.value(QStringLiteral("description"))));
    variable.insert(QStringLiteral("write_policy"), normalizedText(payload.value(QStringLiteral("write_policy"))));
    variable.insert(QStringLiteral("notes"), normalizedText(payload.value(QStringLiteral("notes"))));
    return variable;
}

QJsonObject normalizeDatabaseStage(const QJsonObject& payload, int index) {
    QJsonObject stage;
    const QString roleId = idOrDefault(payload, QStringLiteral("role_id"), QStringLiteral("role"));
    const QString stageKey = idOrDefault(payload, QStringLiteral("stage_key"), QStringLiteral("stage_%1").arg(index + 1));
    const QString defaultTag = QStringLiteral("database.stage.%1.%2").arg(roleId, stageKey);
    const QString activeTag = importedDatabaseTag(idOrDefault(payload, QStringLiteral("active_tag"), defaultTag));
    stage.insert(QStringLiteral("id"), idOrDefault(payload, QStringLiteral("id"), QStringLiteral("db_stage_%1").arg(index + 1, 3, 10, QLatin1Char('0'))));
    stage.insert(QStringLiteral("role_id"), roleId);
    stage.insert(QStringLiteral("stage_key"), stageKey);
    stage.insert(QStringLiteral("title"), normalizedText(payload.value(QStringLiteral("title"))));
    stage.insert(QStringLiteral("condition"), normalizedText(payload.value(QStringLiteral("condition"))));
    stage.insert(QStringLiteral("active_tag"), activeTag);
    QStringList emitsTags;
    for (const QString& tag : splitTags(payload.value(QStringLiteral("emits_tags")))) {
        const QString normalizedTag = importedDatabaseTag(tag);
        if (!normalizedTag.isEmpty() && !emitsTags.contains(normalizedTag)) {
            emitsTags.append(normalizedTag);
        }
    }
    stage.insert(QStringLiteral("emits_tags"), tagsArray(emitsTags.isEmpty() ? QStringList{ activeTag } : emitsTags));
    stage.insert(QStringLiteral("description"), normalizedText(payload.value(QStringLiteral("description"))));
    stage.insert(QStringLiteral("notes"), normalizedText(payload.value(QStringLiteral("notes"))));
    return stage;
}

QJsonObject normalizeDatabaseTag(const QJsonObject& payload, int index) {
    QJsonObject tag;
    tag.insert(QStringLiteral("id"), idOrDefault(payload, QStringLiteral("id"), QStringLiteral("db_tag_%1").arg(index + 1, 3, 10, QLatin1Char('0'))));
    tag.insert(QStringLiteral("tag"), importedDatabaseTag(normalizedText(payload.value(QStringLiteral("tag")))));
    tag.insert(QStringLiteral("title"), normalizedText(payload.value(QStringLiteral("title"))));
    tag.insert(QStringLiteral("trigger"), normalizedText(payload.value(QStringLiteral("trigger"))));
    tag.insert(QStringLiteral("target"), idOrDefault(payload, QStringLiteral("target"), QStringLiteral("worldbook")));
    tag.insert(QStringLiteral("description"), normalizedText(payload.value(QStringLiteral("description"))));
    tag.insert(QStringLiteral("notes"), normalizedText(payload.value(QStringLiteral("notes"))));
    return tag;
}

QJsonObject normalizeDatabase(const QJsonObject& payload) {
    QJsonObject database;
    database.insert(QStringLiteral("enabled"), boolValue(payload.value(QStringLiteral("enabled")), true));
    database.insert(QStringLiteral("notes"), normalizedText(payload.value(QStringLiteral("notes"))));

    QJsonArray variables;
    const QJsonArray rawVariables = payload.value(QStringLiteral("variables")).toArray();
    for (int i = 0; i < rawVariables.size(); ++i) {
        variables.append(normalizeDatabaseVariable(rawVariables.at(i).toObject(), i));
    }
    database.insert(QStringLiteral("variables"), variables);

    QJsonArray stages;
    const QJsonArray rawStages = payload.value(QStringLiteral("stages")).toArray();
    for (int i = 0; i < rawStages.size(); ++i) {
        stages.append(normalizeDatabaseStage(rawStages.at(i).toObject(), i));
    }
    database.insert(QStringLiteral("stages"), stages);

    QJsonArray tags;
    const QJsonArray rawTags = payload.value(QStringLiteral("tags")).toArray();
    for (int i = 0; i < rawTags.size(); ++i) {
        tags.append(normalizeDatabaseTag(rawTags.at(i).toObject(), i));
    }
    database.insert(QStringLiteral("tags"), tags);
    return database;
}

QString importedDatabaseTag(QString value) {
    value = value.trimmed();
    const QString legacyPrefix = QStringLiteral("state_journal.stage.");
    if (value.startsWith(legacyPrefix)) {
        return QStringLiteral("database.stage.%1").arg(value.mid(legacyPrefix.size()));
    }
    return value;
}

QString summarizeStateJournalConditions(const QJsonValue& value) {
    const QJsonArray conditions = value.toArray();
    QStringList parts;
    for (const QJsonValue& conditionValue : conditions) {
        const QJsonObject condition = conditionValue.toObject();
        const QString variable = normalizedText(condition.value(QStringLiteral("var"))).isEmpty()
            ? normalizedText(condition.value(QStringLiteral("field")))
            : normalizedText(condition.value(QStringLiteral("var")));
        if (variable.isEmpty()) {
            continue;
        }
        const QString op = normalizedText(condition.value(QStringLiteral("op"))).isEmpty()
            ? QStringLiteral(">=")
            : normalizedText(condition.value(QStringLiteral("op")));
        QString conditionValueText = normalizedText(condition.value(QStringLiteral("value")));
        if (conditionValueText.isEmpty()) {
            conditionValueText = QStringLiteral("0");
        }
        parts.append(QStringLiteral("%1 %2 %3").arg(variable, op, conditionValueText));
    }
    return parts.join(QStringLiteral("；"));
}

QJsonObject databaseFromStateJournal(const QJsonObject& stateJournal) {
    QJsonArray variables;
    QJsonArray stages;
    QJsonArray tags;
    QSet<QString> seenTags;

    const QJsonArray roles = stateJournal.value(QStringLiteral("roles")).toArray();
    for (const QJsonValue& roleValue : roles) {
        const QJsonObject role = roleValue.toObject();
        const QString roleId = normalizedText(role.value(QStringLiteral("role_id"))).isEmpty()
            ? normalizedText(role.value(QStringLiteral("id")))
            : normalizedText(role.value(QStringLiteral("role_id")));
        const QString roleName = normalizedText(role.value(QStringLiteral("role_name"))).isEmpty()
            ? idOrDefault(role, QStringLiteral("name"), roleId)
            : normalizedText(role.value(QStringLiteral("role_name")));

        const QJsonArray roleVariables = role.value(QStringLiteral("variables")).toArray();
        for (int i = 0; i < roleVariables.size(); ++i) {
            const QJsonObject variable = roleVariables.at(i).toObject();
            const QString varKey = normalizedText(variable.value(QStringLiteral("var_key"))).isEmpty()
                ? normalizedText(variable.value(QStringLiteral("key")))
                : normalizedText(variable.value(QStringLiteral("var_key")));
            if (varKey.isEmpty()) {
                continue;
            }
            variables.append(normalizeDatabaseVariable(QJsonObject{
                    { QStringLiteral("id"), roleId.isEmpty()
                            ? QStringLiteral("db_var_%1").arg(i + 1, 3, 10, QLatin1Char('0'))
                            : QStringLiteral("db_var_%1_%2").arg(roleId, varKey) },
                    { QStringLiteral("key"), varKey },
                    { QStringLiteral("label"), idOrDefault(variable, QStringLiteral("var_name"), idOrDefault(variable, QStringLiteral("label"), varKey)) },
                    { QStringLiteral("value_type"), QStringLiteral("number") },
                    { QStringLiteral("initial_value"), normalizedText(variable.value(QStringLiteral("default_value"))) },
                    { QStringLiteral("scope"), roleId.isEmpty() ? idOrDefault(role, QStringLiteral("role_name"), QStringLiteral("role")) : roleId },
                    { QStringLiteral("description"), normalizedText(variable.value(QStringLiteral("instruction"))) },
                    { QStringLiteral("notes"), QStringLiteral("来自 Fa 角色：%1").arg(roleName) },
                },
                variables.size()));
        }

        const QJsonArray roleStages = role.value(QStringLiteral("stages")).toArray();
        for (int i = 0; i < roleStages.size(); ++i) {
            const QJsonObject stage = roleStages.at(i).toObject();
            const QString stageKey = normalizedText(stage.value(QStringLiteral("stage_key"))).isEmpty()
                ? normalizedText(stage.value(QStringLiteral("key")))
                : normalizedText(stage.value(QStringLiteral("stage_key")));
            if (stageKey.isEmpty()) {
                continue;
            }
            const QString defaultTag = roleId.isEmpty() ? QString() : QStringLiteral("database.stage.%1.%2").arg(roleId, stageKey);
            const QString activeTag = importedDatabaseTag(idOrDefault(stage, QStringLiteral("activation_tag"), defaultTag));
            QStringList emitsTags;
            for (const QString& tag : splitTags(stage.value(QStringLiteral("emits_tags")))) {
                const QString imported = importedDatabaseTag(tag);
                if (!imported.isEmpty() && !emitsTags.contains(imported)) {
                    emitsTags.append(imported);
                }
            }
            if (emitsTags.isEmpty() && !activeTag.isEmpty()) {
                emitsTags.append(activeTag);
            }
            stages.append(normalizeDatabaseStage(QJsonObject{
                    { QStringLiteral("id"), roleId.isEmpty()
                            ? QStringLiteral("db_stage_%1").arg(i + 1, 3, 10, QLatin1Char('0'))
                            : QStringLiteral("db_stage_%1_%2").arg(roleId, stageKey) },
                    { QStringLiteral("role_id"), roleId },
                    { QStringLiteral("stage_key"), stageKey },
                    { QStringLiteral("title"), idOrDefault(stage, QStringLiteral("stage_name"), idOrDefault(stage, QStringLiteral("name"), stageKey)) },
                    { QStringLiteral("condition"), summarizeStateJournalConditions(stage.value(QStringLiteral("conditions"))) },
                    { QStringLiteral("active_tag"), activeTag },
                    { QStringLiteral("emits_tags"), tagsArray(emitsTags) },
                    { QStringLiteral("notes"), QStringLiteral("来自 Fa 角色：%1").arg(roleName) },
                },
                stages.size()));
            for (const QString& tag : emitsTags) {
                if (tag.isEmpty() || seenTags.contains(tag)) {
                    continue;
                }
                seenTags.insert(tag);
                tags.append(normalizeDatabaseTag(QJsonObject{
                        { QStringLiteral("id"), roleId.isEmpty()
                                ? QStringLiteral("db_tag_%1").arg(tags.size() + 1, 3, 10, QLatin1Char('0'))
                                : QStringLiteral("db_tag_%1_%2").arg(roleId, stageKey) },
                        { QStringLiteral("tag"), tag },
                        { QStringLiteral("title"), idOrDefault(stage, QStringLiteral("stage_name"), idOrDefault(stage, QStringLiteral("name"), stageKey)) },
                        { QStringLiteral("trigger"), QStringLiteral("由 stateJournal 阶段命中发出。") },
                        { QStringLiteral("target"), QStringLiteral("worldbook") },
                        { QStringLiteral("notes"), QStringLiteral("来自 Fa 阶段：%1 / %2").arg(roleName, stageKey) },
                    },
                    tags.size()));
            }
        }
    }

    return normalizeDatabase(QJsonObject{
        { QStringLiteral("enabled"), stateJournal.value(QStringLiteral("enabled")).isBool() ? stateJournal.value(QStringLiteral("enabled")).toBool() : true },
        { QStringLiteral("variables"), variables },
        { QStringLiteral("stages"), stages },
        { QStringLiteral("tags"), tags },
    });
}

bool hasDatabaseDraftContent(const QJsonObject& database) {
    return !database.value(QStringLiteral("variables")).toArray().isEmpty()
        || !database.value(QStringLiteral("stages")).toArray().isEmpty()
        || !database.value(QStringLiteral("tags")).toArray().isEmpty()
        || !database.value(QStringLiteral("notes")).toString().trimmed().isEmpty();
}

QJsonObject normalizePersonasMap(const QJsonValue& value) {
    QJsonObject result;
    if (value.isObject()) {
        const QJsonObject raw = value.toObject();
        for (auto it = raw.constBegin(); it != raw.constEnd(); ++it) {
            if (!it.value().isObject()) {
                continue;
            }
            const QString key = it.key().trimmed().isEmpty() ? QStringLiteral("1") : it.key().trimmed();
            result.insert(key, normalizePersonaCard(it.value().toObject()));
        }
    } else if (value.isArray()) {
        const QJsonArray raw = value.toArray();
        for (int i = 0; i < raw.size(); ++i) {
            if (!raw.at(i).isObject()) {
                continue;
            }
            const QJsonObject item = raw.at(i).toObject();
            QString key = normalizedText(item.value(QStringLiteral("id")));
            if (key.isEmpty()) {
                key = QString::number(i + 1);
            }
            result.insert(key, normalizePersonaCard(item));
        }
    }
    return result;
}

QJsonObject legacyWorldbookEntry(const QJsonObject& payload, int index) {
    QJsonObject entry = payload;
    if (!entry.contains(QStringLiteral("trigger"))) {
        entry.insert(QStringLiteral("trigger"), normalizedText(payload.value(QStringLiteral("keywords"))));
    }
    if (!entry.contains(QStringLiteral("comment"))) {
        entry.insert(QStringLiteral("comment"), normalizedText(payload.value(QStringLiteral("notes"))));
    }
    if (!entry.contains(QStringLiteral("entry_type"))) {
        entry.insert(QStringLiteral("entry_type"), QStringLiteral("keyword"));
    }
    if (!entry.contains(QStringLiteral("order"))) {
        entry.insert(QStringLiteral("order"), index);
    }
    return normalizeWorldbookEntry(entry, index);
}

QJsonObject legacyMemoryItem(const QJsonObject& payload, int index) {
    QJsonObject item = payload;
    if (!item.contains(QStringLiteral("notes"))) {
        item.insert(QStringLiteral("notes"), normalizedText(payload.value(QStringLiteral("summary"))));
    }
    return normalizeMemoryItem(item, index);
}

QJsonObject legacyPresetItem(const QJsonObject& payload, int index) {
    QJsonObject item = payload;
    if (!item.contains(QStringLiteral("name"))) {
        item.insert(QStringLiteral("name"), normalizedText(payload.value(QStringLiteral("title"))));
    }
    if (!item.contains(QStringLiteral("base_system_prompt"))) {
        item.insert(QStringLiteral("base_system_prompt"), normalizedText(payload.value(QStringLiteral("content"))));
    }
    return normalizePresetItem(item, index);
}

QJsonObject normalizeOldProject(const QJsonObject& payload) {
    QJsonObject project = createEmptyProject();
    const QJsonObject card = payload.value(QStringLiteral("card")).toObject();
    QJsonObject personaCard{
        { QStringLiteral("name"), normalizedText(card.value(QStringLiteral("name"))) },
        { QStringLiteral("description"), normalizedText(card.value(QStringLiteral("description"))) },
        { QStringLiteral("personality"), normalizedText(card.value(QStringLiteral("personality"))) },
        { QStringLiteral("scenario"), normalizedText(card.value(QStringLiteral("scenario"))) },
        { QStringLiteral("first_mes"), normalizedText(card.value(QStringLiteral("first_mes"))) },
        { QStringLiteral("mes_example"), normalizedText(card.value(QStringLiteral("mes_example"))) },
        { QStringLiteral("creator_notes"), normalizedText(card.value(QStringLiteral("creator_notes"))) },
        { QStringLiteral("tags"), tagsArray(splitTags(card.value(QStringLiteral("tags")))) },
        { QStringLiteral("personas"), normalizePersonasMap(payload.value(QStringLiteral("personas"))) },
    };
    if (card.contains(QStringLiteral("creativeWorkshop"))) {
        personaCard.insert(QStringLiteral("creativeWorkshop"), card.value(QStringLiteral("creativeWorkshop")));
    }
    project.insert(QStringLiteral("title"), idOrDefault(payload, QStringLiteral("title"), personaCard.value(QStringLiteral("name")).toString()));
    project.insert(QStringLiteral("updated_at"), normalizedText(payload.value(QStringLiteral("updated_at"))));
    project.insert(QStringLiteral("persona_card"), normalizePersonaCard(personaCard));

    QJsonArray worldbookEntries;
    const QJsonArray rawWorldbooks = payload.value(QStringLiteral("worldbooks")).toArray();
    for (int i = 0; i < rawWorldbooks.size(); ++i) {
        worldbookEntries.append(legacyWorldbookEntry(rawWorldbooks.at(i).toObject(), i));
    }
    project.insert(QStringLiteral("worldbook"), normalizeWorldbook(QJsonObject{ { QStringLiteral("entries"), worldbookEntries } }));

    QJsonArray memoryItems;
    const QJsonArray rawMemories = payload.value(QStringLiteral("memories")).toArray();
    for (int i = 0; i < rawMemories.size(); ++i) {
        memoryItems.append(legacyMemoryItem(rawMemories.at(i).toObject(), i));
    }
    project.insert(QStringLiteral("memory"), normalizeMemory(QJsonObject{ { QStringLiteral("items"), memoryItems } }));

    QJsonArray presetItems;
    const QJsonArray rawPresets = payload.value(QStringLiteral("presets")).toArray();
    for (int i = 0; i < rawPresets.size(); ++i) {
        presetItems.append(legacyPresetItem(rawPresets.at(i).toObject(), i));
    }
    project.insert(QStringLiteral("preset"), normalizePreset(QJsonObject{ { QStringLiteral("presets"), presetItems } }));
    project.insert(QStringLiteral("database"), normalizeDatabase(payload.value(QStringLiteral("database")).toObject()));
    return project;
}

QString extractLabeledLine(const QString& text, const QString& label) {
    const QRegularExpression pattern(QStringLiteral("^\\s*%1[：:]\\s*(.+)\\s*$").arg(QRegularExpression::escape(label)), QRegularExpression::MultilineOption);
    const QRegularExpressionMatch match = pattern.match(text);
    return match.hasMatch() ? match.captured(1).trimmed() : QString();
}

QJsonObject personaSectionsFromText(const QString& body) {
    QJsonObject sections;
    QString currentSection;
    const QRegularExpression sectionHeader(QStringLiteral("^\\s*(描述|性格|场景|备注)[：:]\\s*(.*)$"));
    const QStringList lines = body.split(QLatin1Char('\n'));
    for (const QString& line : lines) {
        const QRegularExpressionMatch match = sectionHeader.match(line);
        if (match.hasMatch()) {
            currentSection = match.captured(1);
            sections.insert(currentSection, match.captured(2).trimmed());
            continue;
        }
        if (currentSection.isEmpty()) {
            continue;
        }
        const QString previous = sections.value(currentSection).toString();
        sections.insert(currentSection, previous.isEmpty() ? line.trimmed() : QStringLiteral("%1\n%2").arg(previous, line.trimmed()));
    }
    return sections;
}

QJsonArray parsePersonasText(const QString& content) {
    QJsonArray personas;
    const QString text = normalizedText(content);
    if (text.isEmpty()) {
        return personas;
    }

    QStringList currentBlock;
    const QRegularExpression blockHeader(QStringLiteral("^\\s*角色\\s*(\\d+)[：:]\\s*(.*)$"));
    auto flushBlock = [&]() {
        if (currentBlock.isEmpty()) {
            return;
        }
        const QRegularExpressionMatch header = blockHeader.match(currentBlock.first());
        if (!header.hasMatch()) {
            currentBlock.clear();
            return;
        }
        const QString key = header.captured(1).trimmed();
        const QString name = header.captured(2).trimmed();
        const QString body = currentBlock.mid(1).join(QLatin1Char('\n'));
        const QJsonObject sections = personaSectionsFromText(body);
        personas.append(QJsonObject{
            { QStringLiteral("id"), key },
            { QStringLiteral("name"), name },
            { QStringLiteral("description"), sections.value(QStringLiteral("描述")).toString().trimmed() },
            { QStringLiteral("personality"), sections.value(QStringLiteral("性格")).toString().trimmed() },
            { QStringLiteral("scenario"), sections.value(QStringLiteral("场景")).toString().trimmed() },
            { QStringLiteral("creator_notes"), sections.value(QStringLiteral("备注")).toString().trimmed() },
        });
        currentBlock.clear();
    };

    const QStringList lines = text.split(QLatin1Char('\n'));
    for (const QString& line : lines) {
        if (blockHeader.match(line).hasMatch()) {
            flushBlock();
        }
        currentBlock.append(line);
    }
    flushBlock();
    return personas;
}

QJsonObject normalizeNodeProject(const QJsonObject& payload) {
    QJsonObject nodesByType;
    const QJsonArray nodes = payload.value(QStringLiteral("nodes")).toArray();
    for (const QJsonValue& value : nodes) {
        const QJsonObject node = value.toObject();
        const QString type = normalizedText(node.value(QStringLiteral("type")));
        if (!type.isEmpty()) {
            nodesByType.insert(type, normalizedText(node.value(QStringLiteral("content"))));
        }
    }
    const QString basic = nodesByType.value(QStringLiteral("basic")).toString();
    const QJsonObject personas = normalizePersonasMap(parsePersonasText(nodesByType.value(QStringLiteral("personas")).toString()));
    QJsonObject project = createEmptyProject();
    project.insert(QStringLiteral("title"), idOrDefault(payload, QStringLiteral("title"), extractLabeledLine(basic, QStringLiteral("角色名"))));
    project.insert(QStringLiteral("updated_at"), normalizedText(payload.value(QStringLiteral("updated_at"))));
    project.insert(QStringLiteral("persona_card"), normalizePersonaCard(QJsonObject{
        { QStringLiteral("name"), extractLabeledLine(basic, QStringLiteral("角色名")) },
        { QStringLiteral("tags"), tagsArray(splitTags(extractLabeledLine(basic, QStringLiteral("标签")))) },
        { QStringLiteral("description"), nodesByType.value(QStringLiteral("description")).toString() },
        { QStringLiteral("personality"), nodesByType.value(QStringLiteral("personality")).toString() },
        { QStringLiteral("scenario"), nodesByType.value(QStringLiteral("scenario")).toString() },
        { QStringLiteral("first_mes"), nodesByType.value(QStringLiteral("first_mes")).toString() },
        { QStringLiteral("mes_example"), nodesByType.value(QStringLiteral("mes_example")).toString() },
        { QStringLiteral("creator_notes"), nodesByType.value(QStringLiteral("creator_notes")).toString() },
        { QStringLiteral("personas"), personas },
    }));
    return project;
}

QJsonObject createEmptyProject() {
    QJsonObject project;
    project.insert(QStringLiteral("type"), projectType());
    project.insert(QStringLiteral("version"), projectVersion());
    project.insert(QStringLiteral("title"), QString());
    project.insert(QStringLiteral("updated_at"), QString());
    project.insert(QStringLiteral("persona_card"), normalizePersonaCard(QJsonObject{
        { QStringLiteral("personas"), defaultMultiRolePersonas() },
    }));
    project.insert(QStringLiteral("worldbook"), normalizeWorldbook({}));
    project.insert(QStringLiteral("preset"), normalizePreset({}));
    project.insert(QStringLiteral("memory"), normalizeMemory({}));
    project.insert(QStringLiteral("database"), normalizeDatabase({}));
    return project;
}

bool looksLikeOldCardWriterProject(const QJsonObject& payload) {
    return payload.contains(QStringLiteral("card"))
        || payload.contains(QStringLiteral("personas"))
        || payload.contains(QStringLiteral("worldbooks"))
        || payload.contains(QStringLiteral("memories"))
        || payload.contains(QStringLiteral("database"))
        || payload.contains(QStringLiteral("plot_stages"));
}

QJsonObject normalizeProject(const QJsonObject& payload) {
    QJsonObject project = createEmptyProject();
    const QString type = normalizedText(payload.value(QStringLiteral("type")));
    if (type == projectType() || type == legacyProjectType()) {
        project.insert(QStringLiteral("type"), projectType());
        project.insert(QStringLiteral("version"), projectVersion());
        project.insert(QStringLiteral("title"), normalizedText(payload.value(QStringLiteral("title"))));
        project.insert(QStringLiteral("updated_at"), normalizedText(payload.value(QStringLiteral("updated_at"))));
        project.insert(QStringLiteral("persona_card"), normalizePersonaCard(payload.value(QStringLiteral("persona_card")).toObject()));
        project.insert(QStringLiteral("worldbook"), normalizeWorldbook(payload.value(QStringLiteral("worldbook")).toObject()));
        project.insert(QStringLiteral("preset"), normalizePreset(payload.value(QStringLiteral("preset")).toObject()));
        project.insert(QStringLiteral("memory"), normalizeMemory(payload.value(QStringLiteral("memory")).toObject()));
        project.insert(QStringLiteral("database"), normalizeDatabase(payload.value(QStringLiteral("database")).toObject()));
        if (project.value(QStringLiteral("title")).toString().isEmpty()) {
            project.insert(QStringLiteral("title"), project.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("name")).toString());
        }
        return project;
    }

    const QJsonObject wrappedRaw = payload.value(QStringLiteral("raw")).toObject();
    if (!wrappedRaw.isEmpty()) {
        project.insert(QStringLiteral("persona_card"), normalizePersonaCard(wrappedRaw));
        project.insert(QStringLiteral("title"), idOrDefault(payload, QStringLiteral("title"),
                idOrDefault(payload, QStringLiteral("source_name"), project.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("name")).toString())));
        const QJsonObject database = databaseFromStateJournal(wrappedRaw.value(QStringLiteral("stateJournal")).toObject());
        if (hasDatabaseDraftContent(database)) {
            project.insert(QStringLiteral("database"), database);
        }
        return project;
    }

    if (payload.contains(QStringLiteral("name")) || payload.contains(QStringLiteral("description")) || payload.contains(QStringLiteral("stateJournal"))) {
        project.insert(QStringLiteral("persona_card"), normalizePersonaCard(payload));
        project.insert(QStringLiteral("title"), project.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("name")).toString());
        const QJsonObject database = databaseFromStateJournal(payload.value(QStringLiteral("stateJournal")).toObject());
        if (hasDatabaseDraftContent(database)) {
            project.insert(QStringLiteral("database"), database);
        }
        return project;
    }

    if (payload.contains(QStringLiteral("variables")) || payload.contains(QStringLiteral("stages")) || payload.contains(QStringLiteral("tags"))) {
        project.insert(QStringLiteral("database"), normalizeDatabase(payload));
        project.insert(QStringLiteral("title"), QStringLiteral("导入的数据库草稿"));
        return project;
    }

    if (looksLikeOldCardWriterProject(payload)) {
        return normalizeOldProject(payload);
    }

    if (payload.contains(QStringLiteral("entries"))) {
        project.insert(QStringLiteral("worldbook"), normalizeWorldbook(payload));
        project.insert(QStringLiteral("title"), QStringLiteral("导入的世界书"));
        return project;
    }

    if (payload.contains(QStringLiteral("active_preset_id")) || payload.contains(QStringLiteral("presets"))) {
        project.insert(QStringLiteral("preset"), normalizePreset(payload));
        project.insert(QStringLiteral("title"), QStringLiteral("导入的预设"));
        return project;
    }

    if (payload.contains(QStringLiteral("items"))) {
        project.insert(QStringLiteral("memory"), normalizeMemory(payload));
        project.insert(QStringLiteral("title"), QStringLiteral("导入的记忆"));
        return project;
    }

    if (payload.contains(QStringLiteral("nodes"))) {
        return normalizeNodeProject(payload);
    }

    return project;
}

}
