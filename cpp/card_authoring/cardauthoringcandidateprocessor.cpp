#include "card_authoring/cardauthoringcandidateprocessor.h"

#include "card_authoring/cardauthoringmodels.h"

#include <QCryptographicHash>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonValue>
#include <QRegularExpression>
#include <QSet>

namespace {
struct NormalizedCandidateBatch {
    QJsonArray candidates;
    int rawCount = 0;
    int rejectedCount = 0;
};

const QSet<QString>& allowedModules() {
    static const QSet<QString> modules = {
        QStringLiteral("persona"),
        QStringLiteral("worldbook"),
        QStringLiteral("preset"),
        QStringLiteral("memory"),
        QStringLiteral("database"),
    };
    return modules;
}

QString text(const QJsonValue& value) {
    return CardAuthoring::normalizedText(value);
}

QString clippedText(const QString& value, int maxLength) {
    return value.size() > maxLength ? value.left(maxLength).trimmed() : value;
}

bool boolValue(const QJsonValue& value, bool fallback = false) {
    if (value.isBool()) {
        return value.toBool();
    }
    const QString normalized = text(value).toLower();
    if (normalized == QStringLiteral("1") || normalized == QStringLiteral("true") || normalized == QStringLiteral("yes") || normalized == QStringLiteral("on")) {
        return true;
    }
    if (normalized == QStringLiteral("0") || normalized == QStringLiteral("false") || normalized == QStringLiteral("no") || normalized == QStringLiteral("off")) {
        return false;
    }
    return fallback;
}

QString normalizeDatabaseKind(const QJsonValue& value) {
    const QString kind = text(value).toLower();
    if (kind == QStringLiteral("variable") || kind == QStringLiteral("variables") || kind == QStringLiteral("var")) {
        return QStringLiteral("variables");
    }
    if (kind == QStringLiteral("stage") || kind == QStringLiteral("stages")) {
        return QStringLiteral("stages");
    }
    if (kind == QStringLiteral("snapshot") || kind == QStringLiteral("snapshots")
        || kind == QStringLiteral("snapshotfield") || kind == QStringLiteral("snapshotfields")
        || kind == QStringLiteral("snapshot_field") || kind == QStringLiteral("snapshot_fields")) {
        return QStringLiteral("snapshotFields");
    }
    if (kind == QStringLiteral("tag") || kind == QStringLiteral("tags")) {
        return QStringLiteral("tags");
    }
    return {};
}

QString slugify(QString value, const QString& fallback = QStringLiteral("default")) {
    value = value.trimmed().toLower();
    if (value.isEmpty()) {
        value = fallback;
    }
    value.replace(QRegularExpression(QStringLiteral("\\s+")), QStringLiteral("_"));
    value.replace(QRegularExpression(QStringLiteral("[^a-z0-9_.:-]+")), QStringLiteral("_"));
    value.replace(QRegularExpression(QStringLiteral("_+")), QStringLiteral("_"));
    while (value.startsWith(QLatin1Char('_'))) {
        value.remove(0, 1);
    }
    while (value.endsWith(QLatin1Char('_'))) {
        value.chop(1);
    }
    if (value.size() > 80) {
        value = value.left(80);
    }
    return value.isEmpty() ? fallback : value;
}

QString safeTagSlug(QString value) {
    value = value.trimmed();
    value.replace(QRegularExpression(QStringLiteral("\\s+")), QStringLiteral("_"));
    value.replace(QRegularExpression(QStringLiteral("[^0-9A-Za-z_.:-]+")), QStringLiteral("_"));
    value.replace(QRegularExpression(QStringLiteral("_+")), QStringLiteral("_"));
    while (value.startsWith(QLatin1Char('_'))) {
        value.remove(0, 1);
    }
    while (value.endsWith(QLatin1Char('_'))) {
        value.chop(1);
    }
    return value.isEmpty() ? QStringLiteral("stage_tag") : value;
}

QStringList normalizedDependsOn(const QJsonValue& value) {
    QJsonArray items;
    if (value.isArray()) {
        items = value.toArray();
    } else if (!value.isUndefined() && !value.isNull()) {
        items.append(value);
    }

    QStringList result;
    for (const QJsonValue& item : items) {
        const QString groupId = slugify(text(item), QString());
        if (!groupId.isEmpty() && !result.contains(groupId)) {
            result.append(groupId);
        }
        if (result.size() >= 12) {
            break;
        }
    }
    return result;
}

QJsonArray stringListToJsonArray(const QStringList& values) {
    QJsonArray result;
    for (const QString& value : values) {
        result.append(value);
    }
    return result;
}

QStringList jsonArrayToStringList(const QJsonArray& values) {
    QStringList result;
    for (const QJsonValue& value : values) {
        const QString item = text(value);
        if (!item.isEmpty() && !result.contains(item)) {
            result.append(item);
        }
    }
    return result;
}

QStringList pathParts(const QString& path) {
    return path.split(QLatin1Char('.'), Qt::SkipEmptyParts);
}

bool isNumericPart(const QString& part) {
    bool ok = false;
    part.toInt(&ok);
    return ok;
}

bool isAllowedJsonPatchPath(const QString& path) {
    if (path.isEmpty() || path.contains(QStringLiteral(".."))) {
        return false;
    }
    const QStringList parts = pathParts(path);
    if (parts.isEmpty() || parts.join(QLatin1Char('.')) != path) {
        return false;
    }
    if (!QSet<QString>{ QStringLiteral("persona_card"), QStringLiteral("worldbook"), QStringLiteral("preset"), QStringLiteral("memory"), QStringLiteral("database") }.contains(parts.first())) {
        return false;
    }
    const QSet<QString> blocked = {
        QStringLiteral("version"),
        QStringLiteral("type"),
        QStringLiteral("updated_at"),
        QStringLiteral("__proto__"),
        QStringLiteral("prototype"),
        QStringLiteral("constructor"),
    };
    for (const QString& part : parts) {
        if (blocked.contains(part)) {
            return false;
        }
    }
    return true;
}

QJsonValue projectPathValue(const QJsonObject& project, const QString& path) {
    QJsonValue current(project);
    for (const QString& part : pathParts(path)) {
        if (current.isObject()) {
            const QJsonObject object = current.toObject();
            if (!object.contains(part)) {
                return QJsonValue(QJsonValue::Undefined);
            }
            current = object.value(part);
        } else if (current.isArray() && isNumericPart(part)) {
            const int index = part.toInt();
            const QJsonArray array = current.toArray();
            if (index < 0 || index >= array.size()) {
                return QJsonValue(QJsonValue::Undefined);
            }
            current = array.at(index);
        } else {
            return QJsonValue(QJsonValue::Undefined);
        }
    }
    return current;
}

bool shouldKeepPatchValue(const QJsonValue& value) {
    if (value.isUndefined() || value.isNull()) {
        return false;
    }
    if (value.isString()) {
        return !value.toString().trimmed().isEmpty();
    }
    if (value.isArray()) {
        return !value.toArray().isEmpty();
    }
    if (value.isObject()) {
        const QJsonObject object = value.toObject();
        for (auto it = object.constBegin(); it != object.constEnd(); ++it) {
            if (shouldKeepPatchValue(it.value())) {
                return true;
            }
        }
        return false;
    }
    return true;
}

int candidateArrayIndex(const QJsonObject& project, const QString& path) {
    const QStringList parts = pathParts(path);
    if (parts.size() >= 3 && isNumericPart(parts.at(2))) {
        return parts.at(2).toInt();
    }
    const QString arrayPath = parts.size() >= 2 ? QStringList{ parts.at(0), parts.at(1) }.join(QLatin1Char('.')) : path;
    const QJsonValue arrayValue = projectPathValue(project, arrayPath);
    return arrayValue.isArray() ? arrayValue.toArray().size() : 0;
}

QJsonObject mergedObjectForPath(const QJsonObject& project, const QString& path, const QJsonObject& incoming) {
    QJsonObject merged = projectPathValue(project, path).toObject();
    for (auto it = incoming.constBegin(); it != incoming.constEnd(); ++it) {
        merged.insert(it.key(), it.value());
    }
    return merged.isEmpty() ? incoming : merged;
}

QJsonObject normalizeWorldbookEntry(QJsonObject entry, int index) {
    QString id = text(entry.value(QStringLiteral("id")));
    if (id.isEmpty()) {
        id = QStringLiteral("wb_candidate_%1").arg(index + 1, 3, 10, QLatin1Char('0'));
    }
    const QString trigger = text(entry.value(QStringLiteral("trigger")));
    const QString title = text(entry.value(QStringLiteral("title")));
    QString entryType = text(entry.value(QStringLiteral("entry_type"))).toLower();
    if (entryType != QStringLiteral("external_tag") && entryType != QStringLiteral("constant") && entryType != QStringLiteral("keyword")) {
        entryType = trigger.isEmpty() ? QStringLiteral("constant") : QStringLiteral("keyword");
    }
    entry.insert(QStringLiteral("id"), id);
    entry.insert(QStringLiteral("title"), title.isEmpty() ? (trigger.isEmpty() ? QStringLiteral("世界书词条 %1").arg(index + 1) : trigger) : title);
    entry.insert(QStringLiteral("trigger"), trigger);
    entry.insert(QStringLiteral("secondary_trigger"), text(entry.value(QStringLiteral("secondary_trigger"))));
    entry.insert(QStringLiteral("entry_type"), entryType);
    entry.insert(QStringLiteral("content"), text(entry.value(QStringLiteral("content"))));
    entry.insert(QStringLiteral("group"), text(entry.value(QStringLiteral("group"))));
    entry.insert(QStringLiteral("comment"), text(entry.value(QStringLiteral("comment"))));
    entry.insert(QStringLiteral("enabled"), entry.value(QStringLiteral("enabled")).toBool(true));
    return entry;
}

QJsonObject normalizeMemoryItem(QJsonObject item, int index) {
    QString id = text(item.value(QStringLiteral("id")));
    if (id.isEmpty()) {
        id = QStringLiteral("memory_candidate_%1").arg(index + 1, 3, 10, QLatin1Char('0'));
    }
    item.insert(QStringLiteral("id"), id);
    item.insert(QStringLiteral("title"), text(item.value(QStringLiteral("title"))));
    item.insert(QStringLiteral("content"), text(item.value(QStringLiteral("content"))));
    item.insert(QStringLiteral("tags"), CardAuthoring::tagsArray(CardAuthoring::splitTags(item.value(QStringLiteral("tags")))));
    item.insert(QStringLiteral("notes"), text(item.value(QStringLiteral("notes"))));
    item.insert(QStringLiteral("memory_status"), text(item.value(QStringLiteral("memory_status"))).toLower() == QStringLiteral("archived") ? QStringLiteral("archived") : QStringLiteral("active"));
    return item;
}

QJsonValue normalizeAfterValue(const QJsonObject& project, const QString& path, const QString& operation, const QJsonValue& rawAfter) {
    if (operation == QStringLiteral("delete")) {
        return QJsonValue(QJsonValue::Null);
    }
    const QStringList parts = pathParts(path);
    if (parts.isEmpty()) {
        return rawAfter;
    }
    if (parts.first() == QStringLiteral("database")) {
        const int index = candidateArrayIndex(project, path);
        if (parts.size() >= 2 && rawAfter.isObject()) {
            const QJsonObject incoming = rawAfter.toObject();
            QJsonObject object = mergedObjectForPath(project, path, incoming);
            if (parts.at(1) == QStringLiteral("variables")) {
                if (incoming.contains(QStringLiteral("label")) && !incoming.contains(QStringLiteral("var_name"))) {
                    object.insert(QStringLiteral("var_name"), incoming.value(QStringLiteral("label")));
                } else if (incoming.contains(QStringLiteral("var_name")) && !incoming.contains(QStringLiteral("label"))) {
                    object.insert(QStringLiteral("label"), incoming.value(QStringLiteral("var_name")));
                }
                if (incoming.contains(QStringLiteral("key")) && !incoming.contains(QStringLiteral("var_key"))) {
                    object.insert(QStringLiteral("var_key"), incoming.value(QStringLiteral("key")));
                } else if (incoming.contains(QStringLiteral("var_key")) && !incoming.contains(QStringLiteral("key"))) {
                    object.insert(QStringLiteral("key"), incoming.value(QStringLiteral("var_key")));
                }
                if (incoming.contains(QStringLiteral("scope")) && !incoming.contains(QStringLiteral("role_id"))) {
                    object.insert(QStringLiteral("role_id"), incoming.value(QStringLiteral("scope")));
                } else if (incoming.contains(QStringLiteral("role_id")) && !incoming.contains(QStringLiteral("scope"))) {
                    object.insert(QStringLiteral("scope"), incoming.value(QStringLiteral("role_id")));
                }
                if (incoming.contains(QStringLiteral("initial_value")) && !incoming.contains(QStringLiteral("default_value"))) {
                    object.insert(QStringLiteral("default_value"), incoming.value(QStringLiteral("initial_value")));
                } else if (incoming.contains(QStringLiteral("default_value")) && !incoming.contains(QStringLiteral("initial_value"))) {
                    object.insert(QStringLiteral("initial_value"), incoming.value(QStringLiteral("default_value")));
                }
                return CardAuthoring::normalizeDatabaseVariable(object, index);
            }
            if (parts.at(1) == QStringLiteral("stages")) {
                if (incoming.contains(QStringLiteral("title")) && !incoming.contains(QStringLiteral("stage_name"))) {
                    object.insert(QStringLiteral("stage_name"), incoming.value(QStringLiteral("title")));
                } else if (incoming.contains(QStringLiteral("stage_name")) && !incoming.contains(QStringLiteral("title"))) {
                    object.insert(QStringLiteral("title"), incoming.value(QStringLiteral("stage_name")));
                }
                if (incoming.contains(QStringLiteral("active_tag")) && !incoming.contains(QStringLiteral("activation_tag"))) {
                    object.insert(QStringLiteral("activation_tag"), incoming.value(QStringLiteral("active_tag")));
                } else if (incoming.contains(QStringLiteral("activation_tag")) && !incoming.contains(QStringLiteral("active_tag"))) {
                    object.insert(QStringLiteral("active_tag"), incoming.value(QStringLiteral("activation_tag")));
                }
                return CardAuthoring::normalizeDatabaseStage(object, index);
            }
            if (parts.at(1) == QStringLiteral("snapshotFields") || parts.at(1) == QStringLiteral("snapshot_fields")) {
                return CardAuthoring::normalizeDatabaseSnapshotField(object, index);
            }
            if (parts.at(1) == QStringLiteral("tags")) {
                return CardAuthoring::normalizeDatabaseTag(object, index);
            }
        }
        if (parts.size() == 1 && rawAfter.isObject()) {
            return CardAuthoring::normalizeDatabase(rawAfter.toObject());
        }
    }
    if (parts.first() == QStringLiteral("persona_card")) {
        if (parts.size() == 1 && rawAfter.isObject()) {
            QJsonObject merged = project.value(QStringLiteral("persona_card")).toObject();
            const QJsonObject incoming = rawAfter.toObject();
            for (auto it = incoming.constBegin(); it != incoming.constEnd(); ++it) {
                merged.insert(it.key(), it.value());
            }
            return CardAuthoring::normalizePersonaCard(merged);
        }
        if (parts.size() == 2) {
            const QString field = parts.at(1);
            if (field == QStringLiteral("tags")) {
                return CardAuthoring::tagsArray(CardAuthoring::splitTags(rawAfter));
            }
            if (field != QStringLiteral("personas")) {
                return text(rawAfter);
            }
        }
    }
    if (parts.size() >= 2 && parts.first() == QStringLiteral("worldbook") && parts.at(1) == QStringLiteral("entries") && rawAfter.isObject()) {
        return normalizeWorldbookEntry(mergedObjectForPath(project, path, rawAfter.toObject()), candidateArrayIndex(project, path));
    }
    if (parts.size() >= 2 && parts.first() == QStringLiteral("memory") && parts.at(1) == QStringLiteral("items") && rawAfter.isObject()) {
        return normalizeMemoryItem(mergedObjectForPath(project, path, rawAfter.toObject()), candidateArrayIndex(project, path));
    }
    if (parts.size() >= 2 && parts.first() == QStringLiteral("preset") && parts.at(1) == QStringLiteral("presets") && rawAfter.isObject()) {
        return CardAuthoring::normalizePresetItem(mergedObjectForPath(project, path, rawAfter.toObject()), candidateArrayIndex(project, path));
    }
    return rawAfter;
}

QString inferGroupId(const QJsonObject& candidate) {
    const QString explicitGroup = slugify(text(candidate.value(QStringLiteral("group_id"))), QString());
    if (!explicitGroup.isEmpty()) {
        return explicitGroup;
    }
    const QString path = candidate.value(QStringLiteral("target")).toObject().value(QStringLiteral("path")).toString();
    if (path.startsWith(QStringLiteral("database."))) {
        return QStringLiteral("database_mechanism");
    }
    if (path.startsWith(QStringLiteral("worldbook."))) {
        return QStringLiteral("worldbook_context");
    }
    if (path.startsWith(QStringLiteral("preset."))) {
        return QStringLiteral("preset_discipline");
    }
    if (path.startsWith(QStringLiteral("memory."))) {
        return QStringLiteral("memory_continuity");
    }
    if (path.startsWith(QStringLiteral("persona_card."))) {
        return QStringLiteral("persona_foundation");
    }
    return slugify(candidate.value(QStringLiteral("module")).toString(), QStringLiteral("ungrouped"));
}

QString defaultGroupTitle(const QString& groupId) {
    if (groupId == QStringLiteral("persona_foundation")) {
        return QStringLiteral("角色底座");
    }
    if (groupId == QStringLiteral("worldbook_context")) {
        return QStringLiteral("世界书承接");
    }
    if (groupId == QStringLiteral("preset_discipline")) {
        return QStringLiteral("预设纪律");
    }
    if (groupId == QStringLiteral("memory_continuity")) {
        return QStringLiteral("记忆连续性");
    }
    if (groupId == QStringLiteral("database_mechanism")) {
        return QStringLiteral("数据库机制");
    }
    if (groupId == QStringLiteral("tag_consumer_link")) {
        return QStringLiteral("tag 消费闭环");
    }
    if (groupId == QStringLiteral("ungrouped")) {
        return QStringLiteral("候选修改");
    }
    QString title = groupId;
    title.replace(QLatin1Char('_'), QLatin1Char(' '));
    return title.trimmed().isEmpty() ? QStringLiteral("候选修改") : title;
}

QString inferGroupTitle(const QString& groupId, const QJsonArray& candidates) {
    for (const QJsonValue& value : candidates) {
        const QJsonObject candidate = value.toObject();
        if (inferGroupId(candidate) == groupId) {
            const QString title = text(candidate.value(QStringLiteral("group_title")));
            if (!title.isEmpty()) {
                return clippedText(title, 120);
            }
        }
    }
    return defaultGroupTitle(groupId);
}

QJsonArray collectGroupCandidateIds(const QString& groupId, const QJsonArray& candidates) {
    QJsonArray ids;
    for (const QJsonValue& value : candidates) {
        const QJsonObject candidate = value.toObject();
        if (inferGroupId(candidate) == groupId) {
            const QString id = text(candidate.value(QStringLiteral("id")));
            if (!id.isEmpty()) {
                ids.append(id);
            }
        }
    }
    return ids;
}

QString fingerprint(const QString& module, const QString& action, const QJsonObject& target, const QJsonValue& before) {
    const QJsonObject payload{
        { QStringLiteral("module"), module },
        { QStringLiteral("action"), action },
        { QStringLiteral("target"), target },
        { QStringLiteral("before"), before },
    };
    const QByteArray serialized = QJsonDocument(payload).toJson(QJsonDocument::Compact);
    return QString::fromLatin1(QCryptographicHash::hash(serialized, QCryptographicHash::Sha1).toHex());
}

QString normalizedCandidateAction(const QString& module, const QJsonValue& value) {
    const QString action = text(value).toLower();
    if (action == QStringLiteral("json_patch")) {
        return action;
    }
    if (module == QStringLiteral("persona")) {
        return QStringLiteral("replace_field");
    }
    if (action == QStringLiteral("append_array_item") || action == QStringLiteral("update_array_item")) {
        return action;
    }
    return QStringLiteral("update_array_item");
}

QString normalizedPatchOperation(const QJsonObject& raw, const QJsonObject& target, const QString& action) {
    QString operation = text(target.value(QStringLiteral("operation"))).toLower();
    if (operation.isEmpty()) {
        operation = text(raw.value(QStringLiteral("operation"))).toLower();
    }
    if (operation.isEmpty() && (action == QStringLiteral("delete") || action == QStringLiteral("remove") || action == QStringLiteral("unset"))) {
        operation = QStringLiteral("delete");
    }
    if (operation == QStringLiteral("remove") || operation == QStringLiteral("unset")) {
        operation = QStringLiteral("delete");
    }
    if (operation != QStringLiteral("set") && operation != QStringLiteral("append") && operation != QStringLiteral("delete")) {
        operation = QStringLiteral("set");
    }
    return operation;
}

QJsonObject buildJsonPatchCandidate(
    const QJsonObject& project,
    const QJsonObject& raw,
    const QString& module,
    const QString& path,
    const QString& operation,
    const QJsonValue& before,
    const QJsonValue& rawAfter,
    int sourceIndex) {
    if (!isAllowedJsonPatchPath(path)) {
        return {};
    }

    QJsonValue after = normalizeAfterValue(project, path, operation, rawAfter);
    if (operation != QStringLiteral("delete") && !shouldKeepPatchValue(after)) {
        return {};
    }

    const QString label = text(raw.value(QStringLiteral("label")));
    const QString reason = text(raw.value(QStringLiteral("reason")));
    QJsonObject target{
        { QStringLiteral("module"), module },
        { QStringLiteral("action"), QStringLiteral("json_patch") },
        { QStringLiteral("path"), path },
        { QStringLiteral("operation"), operation },
    };

    QJsonObject candidate{
        { QStringLiteral("id"), text(raw.value(QStringLiteral("id"))) },
        { QStringLiteral("module"), module },
        { QStringLiteral("action"), QStringLiteral("json_patch") },
        { QStringLiteral("label"), label.isEmpty() ? QStringLiteral("%1 %2").arg(operation, path) : clippedText(label, 160) },
        { QStringLiteral("reason"), reason.isEmpty() ? QStringLiteral("按 JSON 路径应用候选修改。") : clippedText(reason, 1000) },
        { QStringLiteral("target"), target },
        { QStringLiteral("before"), raw.contains(QStringLiteral("before")) ? raw.value(QStringLiteral("before")) : before },
        { QStringLiteral("after"), operation == QStringLiteral("delete") ? QJsonValue(QJsonValue::Null) : after },
        { QStringLiteral("fingerprint"), fingerprint(module, QStringLiteral("json_patch"), target, before) },
        { QStringLiteral("source_index"), sourceIndex },
    };

    const QString groupId = slugify(text(raw.value(QStringLiteral("group_id"))), QString());
    if (!groupId.isEmpty()) {
        candidate.insert(QStringLiteral("group_id"), groupId);
    }
    const QString groupTitle = text(raw.value(QStringLiteral("group_title")));
    if (!groupTitle.isEmpty()) {
        candidate.insert(QStringLiteral("group_title"), clippedText(groupTitle, 120));
    }
    const QString containerRole = text(raw.value(QStringLiteral("container_role")));
    if (!containerRole.isEmpty()) {
        candidate.insert(QStringLiteral("container_role"), clippedText(containerRole, 240));
    }
    const QStringList dependsOn = normalizedDependsOn(raw.value(QStringLiteral("depends_on")));
    if (!dependsOn.isEmpty()) {
        candidate.insert(QStringLiteral("depends_on"), stringListToJsonArray(dependsOn));
    }
    if (raw.contains(QStringLiteral("draft_only"))) {
        candidate.insert(QStringLiteral("draft_only"), boolValue(raw.value(QStringLiteral("draft_only"))));
    }

    const QString inferredGroupId = inferGroupId(candidate);
    candidate.insert(QStringLiteral("group_id"), inferredGroupId);
    if (!candidate.contains(QStringLiteral("group_title"))) {
        candidate.insert(QStringLiteral("group_title"), defaultGroupTitle(inferredGroupId));
    }
    return candidate;
}

QStringList personaPatchFields() {
    return {
        QStringLiteral("name"),
        QStringLiteral("description"),
        QStringLiteral("personality"),
        QStringLiteral("scenario"),
        QStringLiteral("first_mes"),
        QStringLiteral("mes_example"),
        QStringLiteral("creator_notes"),
        QStringLiteral("creator_comment"),
        QStringLiteral("tags"),
    };
}

QJsonArray personaReplacementCandidates(const QJsonObject& project, const QJsonObject& raw, int sourceIndex) {
    QJsonArray result;
    const QJsonObject after = raw.value(QStringLiteral("after")).toObject();
    if (after.isEmpty()) {
        return result;
    }
    for (const QString& field : personaPatchFields()) {
        if (!after.contains(field)) {
            continue;
        }
        QJsonObject patchedRaw = raw;
        if (!patchedRaw.contains(QStringLiteral("label"))) {
            patchedRaw.insert(QStringLiteral("label"), QStringLiteral("填充 persona_card.%1").arg(field));
        }
        QJsonObject candidate = buildJsonPatchCandidate(
            project,
            patchedRaw,
            QStringLiteral("persona"),
            QStringLiteral("persona_card.%1").arg(field),
            QStringLiteral("set"),
            projectPathValue(project, QStringLiteral("persona_card.%1").arg(field)),
            after.value(field),
            sourceIndex);
        if (!candidate.isEmpty()) {
            result.append(candidate);
        }
    }
    return result;
}

QJsonArray personaKeyReplacementCandidates(const QJsonObject& project, const QJsonObject& raw, int sourceIndex, const QString& personaKey) {
    QJsonArray result;
    if (personaKey.isEmpty() || personaKey.contains(QLatin1Char('.'))) {
        return result;
    }
    const QJsonObject after = raw.value(QStringLiteral("after")).toObject();
    if (after.isEmpty()) {
        return result;
    }
    const QJsonObject personas = project.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("personas")).toObject();
    const QJsonObject currentPersona = personas.value(personaKey).toObject();
    if (currentPersona.isEmpty()) {
        return result;
    }
    QJsonObject merged = currentPersona;
    for (auto it = after.constBegin(); it != after.constEnd(); ++it) {
        merged.insert(it.key(), it.value());
    }
    const QJsonObject normalized = CardAuthoring::normalizePersonaCard(merged);

    for (const QString& field : personaPatchFields()) {
        if (!after.contains(field)) {
            continue;
        }
        QJsonObject patchedRaw = raw;
        if (!patchedRaw.contains(QStringLiteral("label"))) {
            patchedRaw.insert(QStringLiteral("label"), QStringLiteral("更新多角色 %1.%2").arg(personaKey, field));
        }
        const QString path = QStringLiteral("persona_card.personas.%1.%2").arg(personaKey, field);
        QJsonObject candidate = buildJsonPatchCandidate(
            project,
            patchedRaw,
            QStringLiteral("persona"),
            path,
            QStringLiteral("set"),
            projectPathValue(project, path),
            normalized.value(field),
            sourceIndex);
        if (!candidate.isEmpty()) {
            result.append(candidate);
        }
    }
    return result;
}

int findObjectIndexById(const QJsonArray& items, const QString& id) {
    if (id.isEmpty()) {
        return -1;
    }
    for (int i = 0; i < items.size(); ++i) {
        if (items.at(i).toObject().value(QStringLiteral("id")).toString() == id) {
            return i;
        }
    }
    return -1;
}

QString legacyArrayPathForCandidate(const QJsonObject& project, const QJsonObject& raw, const QString& module, const QString& action) {
    const QJsonObject target = raw.value(QStringLiteral("target")).toObject();
    if (module == QStringLiteral("worldbook")) {
        if (action == QStringLiteral("append_array_item")) {
            return QStringLiteral("worldbook.entries");
        }
        const int index = findObjectIndexById(project.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray(), text(target.value(QStringLiteral("id"))));
        return index >= 0 ? QStringLiteral("worldbook.entries.%1").arg(index) : QString();
    }
    if (module == QStringLiteral("memory")) {
        if (action == QStringLiteral("append_array_item")) {
            return QStringLiteral("memory.items");
        }
        const int index = findObjectIndexById(project.value(QStringLiteral("memory")).toObject().value(QStringLiteral("items")).toArray(), text(target.value(QStringLiteral("id"))));
        return index >= 0 ? QStringLiteral("memory.items.%1").arg(index) : QString();
    }
    if (module == QStringLiteral("database")) {
        QString kind = normalizeDatabaseKind(target.value(QStringLiteral("kind")));
        if (kind.isEmpty()) {
            kind = normalizeDatabaseKind(raw.value(QStringLiteral("kind")));
        }
        if (kind.isEmpty()) {
            kind = QStringLiteral("variables");
        }
        if (action == QStringLiteral("append_array_item")) {
            return QStringLiteral("database.%1").arg(kind);
        }
        const int index = findObjectIndexById(project.value(QStringLiteral("database")).toObject().value(kind).toArray(), text(target.value(QStringLiteral("id"))));
        return index >= 0 ? QStringLiteral("database.%1.%2").arg(kind).arg(index) : QString();
    }
    if (module == QStringLiteral("preset")) {
        if (action == QStringLiteral("append_array_item")) {
            return QStringLiteral("preset.presets");
        }
        const int index = findObjectIndexById(project.value(QStringLiteral("preset")).toObject().value(QStringLiteral("presets")).toArray(), text(target.value(QStringLiteral("id"))));
        return index >= 0 ? QStringLiteral("preset.presets.%1").arg(index) : QString();
    }
    return {};
}

QJsonArray normalizeSingleCandidate(const QJsonObject& project, const QJsonValue& rawValue, int sourceIndex) {
    QJsonArray result;
    if (!rawValue.isObject()) {
        return result;
    }
    const QJsonObject raw = rawValue.toObject();
    const QString module = text(raw.value(QStringLiteral("module"))).toLower();
    if (!allowedModules().contains(module)) {
        return result;
    }

    QString action = normalizedCandidateAction(module, raw.value(QStringLiteral("action")));
    const QJsonObject target = raw.value(QStringLiteral("target")).toObject();
    QString path = text(target.value(QStringLiteral("path")));
    if (path.isEmpty()) {
        path = text(raw.value(QStringLiteral("path")));
    }

    if (action == QStringLiteral("json_patch") || !path.isEmpty()) {
        const QString operation = normalizedPatchOperation(raw, target, text(raw.value(QStringLiteral("action"))).toLower());
        const QJsonValue before = projectPathValue(project, path);
        const QJsonObject candidate = buildJsonPatchCandidate(project, raw, module, path, operation, before, raw.value(QStringLiteral("after")), sourceIndex);
        if (!candidate.isEmpty()) {
            result.append(candidate);
        }
        return result;
    }

    if (module == QStringLiteral("persona")) {
        const QString personaKey = text(target.value(QStringLiteral("persona_key")));
        if (!personaKey.isEmpty()) {
            return personaKeyReplacementCandidates(project, raw, sourceIndex, personaKey);
        }
        return personaReplacementCandidates(project, raw, sourceIndex);
    }

    if (action != QStringLiteral("append_array_item") && action != QStringLiteral("update_array_item")) {
        return result;
    }
    path = legacyArrayPathForCandidate(project, raw, module, action);
    if (path.isEmpty()) {
        return result;
    }
    const QString operation = action == QStringLiteral("append_array_item") ? QStringLiteral("append") : QStringLiteral("set");
    const QJsonObject candidate = buildJsonPatchCandidate(
        project,
        raw,
        module,
        path,
        operation,
        projectPathValue(project, path),
        raw.value(QStringLiteral("after")),
        sourceIndex);
    if (!candidate.isEmpty()) {
        result.append(candidate);
    }
    return result;
}

void ensureUniqueCandidateIds(QJsonArray* candidates) {
    QSet<QString> seen;
    for (int i = 0; i < candidates->size(); ++i) {
        QJsonObject candidate = candidates->at(i).toObject();
        QString id = slugify(text(candidate.value(QStringLiteral("id"))), QString());
        if (id.isEmpty()) {
            id = QStringLiteral("candidate_%1").arg(i + 1, 3, 10, QLatin1Char('0'));
        }
        const QString base = id;
        int attempt = 2;
        while (seen.contains(id)) {
            id = QStringLiteral("%1_%2").arg(base).arg(attempt++);
        }
        seen.insert(id);
        candidate.insert(QStringLiteral("id"), id);
        candidates->replace(i, candidate);
    }
}

QStringList candidateEmittedTags(const QJsonObject& candidate) {
    if (candidate.value(QStringLiteral("module")).toString() != QStringLiteral("database")) {
        return {};
    }
    const QJsonObject after = candidate.value(QStringLiteral("after")).toObject();
    const QString path = candidate.value(QStringLiteral("target")).toObject().value(QStringLiteral("path")).toString();
    QStringList tags;
    for (const QString& key : { QStringLiteral("active_tag"), QStringLiteral("tag") }) {
        const QString value = text(after.value(key));
        if (!value.isEmpty() && !tags.contains(value)) {
            tags.append(value);
        }
    }
    if (tags.isEmpty() && path.startsWith(QStringLiteral("database.stages"))) {
        const QString roleId = text(after.value(QStringLiteral("role_id")));
        const QString stageKey = text(after.value(QStringLiteral("stage_key")));
        if (!roleId.isEmpty() && !stageKey.isEmpty()) {
            tags.append(QStringLiteral("database.stage.%1.%2").arg(roleId, stageKey));
        }
    }
    for (const QString& value : CardAuthoring::splitTags(after.value(QStringLiteral("emits_tags")))) {
        if (!value.isEmpty() && !tags.contains(value)) {
            tags.append(value);
        }
    }
    return tags;
}

QStringList candidateConsumedTags(const QJsonObject& candidate) {
    if (candidate.value(QStringLiteral("module")).toString() != QStringLiteral("worldbook")) {
        return {};
    }
    const QJsonObject after = candidate.value(QStringLiteral("after")).toObject();
    if (text(after.value(QStringLiteral("entry_type"))).toLower() != QStringLiteral("external_tag")) {
        return {};
    }
    QStringList tags;
    for (const QString& key : { QStringLiteral("trigger"), QStringLiteral("secondary_trigger") }) {
        for (const QString& value : CardAuthoring::splitTags(after.value(key))) {
            if (!value.isEmpty() && !tags.contains(value)) {
                tags.append(value);
            }
        }
    }
    return tags;
}

QJsonObject buildWorldbookConsumerCandidate(const QJsonObject& project, const QString& tag, const QJsonObject& sourceCandidate, int index) {
    const QString slug = safeTagSlug(tag);
    const QJsonObject sourceAfter = sourceCandidate.value(QStringLiteral("after")).toObject();
    const QString title = text(sourceAfter.value(QStringLiteral("title"))).isEmpty()
        ? text(sourceAfter.value(QStringLiteral("label")))
        : text(sourceAfter.value(QStringLiteral("title")));
    const QString displayTitle = title.isEmpty() ? QStringLiteral("阶段状态") : title;
    const QString description = text(sourceAfter.value(QStringLiteral("description"))).isEmpty()
        ? text(sourceAfter.value(QStringLiteral("notes")))
        : text(sourceAfter.value(QStringLiteral("description")));

    QStringList contentParts{
        QStringLiteral("当外部 tag `%1` 命中时，说明当前进入「%2」状态。").arg(tag, displayTitle),
        QStringLiteral("角色表现必须服从当前阶段：先体现可观察的情绪、距离、掩饰和身体反应，不要跳到更高亲密或完全信任。"),
    };
    if (!description.isEmpty()) {
        contentParts.append(description);
    }
    contentParts.append(QStringLiteral("如果后续记忆或互动没有支撑升级，保持本阶段边界。"));

    QJsonObject raw{
        { QStringLiteral("id"), QStringLiteral("tag_consumer_%1").arg(slug.left(48)) },
        { QStringLiteral("module"), QStringLiteral("worldbook") },
        { QStringLiteral("action"), QStringLiteral("json_patch") },
        { QStringLiteral("label"), QStringLiteral("补齐 tag 消费者 - %1").arg(displayTitle) },
        { QStringLiteral("reason"), QStringLiteral("数据库 tag 需要 worldbook external_tag 消费者；这里先补一个可审核的世界书消费者，保证运行包联动不断链。") },
        { QStringLiteral("target"), QJsonObject{
            { QStringLiteral("path"), QStringLiteral("worldbook.entries") },
            { QStringLiteral("operation"), QStringLiteral("append") },
        } },
        { QStringLiteral("before"), QJsonValue(QJsonValue::Null) },
        { QStringLiteral("after"), QJsonObject{
            { QStringLiteral("id"), QStringLiteral("wb_tag_%1").arg(slug.left(48)) },
            { QStringLiteral("title"), QStringLiteral("%1 tag 消费").arg(displayTitle) },
            { QStringLiteral("trigger"), tag },
            { QStringLiteral("entry_type"), QStringLiteral("external_tag") },
            { QStringLiteral("match_mode"), QStringLiteral("includes") },
            { QStringLiteral("secondary_mode"), QStringLiteral("includes") },
            { QStringLiteral("content"), contentParts.join(QStringLiteral("\n")) },
            { QStringLiteral("group"), QStringLiteral("状态联动") },
            { QStringLiteral("order"), project.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray().size() + index },
            { QStringLiteral("priority"), 20 },
            { QStringLiteral("insertion_position"), QStringLiteral("after_char_defs") },
            { QStringLiteral("prompt_layer"), QStringLiteral("current_state") },
            { QStringLiteral("comment"), QStringLiteral("自动补齐的世界书消费者，对应 database tag: %1").arg(tag) },
        } },
        { QStringLiteral("group_id"), QStringLiteral("tag_consumer_link") },
        { QStringLiteral("group_title"), QStringLiteral("tag 消费闭环") },
        { QStringLiteral("container_role"), QStringLiteral("消费数据库阶段 tag，让状态能实际影响角色表现。") },
        { QStringLiteral("depends_on"), QJsonArray{ sourceCandidate.value(QStringLiteral("group_id")).toString(QStringLiteral("database_mechanism")) } },
        { QStringLiteral("draft_only"), true },
    };
    return buildJsonPatchCandidate(
        project,
        raw,
        QStringLiteral("worldbook"),
        QStringLiteral("worldbook.entries"),
        QStringLiteral("append"),
        projectPathValue(project, QStringLiteral("worldbook.entries")),
        raw.value(QStringLiteral("after")),
        index);
}

void ensureTagConsumers(const QJsonObject& project, QJsonArray* candidates) {
    QSet<QString> consumed;
    const QJsonArray entries = project.value(QStringLiteral("worldbook")).toObject().value(QStringLiteral("entries")).toArray();
    for (const QJsonValue& value : entries) {
        const QJsonObject entry = value.toObject();
        if (text(entry.value(QStringLiteral("entry_type"))).toLower() != QStringLiteral("external_tag")) {
            continue;
        }
        for (const QString& key : { QStringLiteral("trigger"), QStringLiteral("secondary_trigger") }) {
            for (const QString& tag : CardAuthoring::splitTags(entry.value(key))) {
                consumed.insert(tag);
            }
        }
    }
    for (const QJsonValue& value : *candidates) {
        for (const QString& tag : candidateConsumedTags(value.toObject())) {
            consumed.insert(tag);
        }
    }

    QJsonArray additions;
    for (const QJsonValue& value : *candidates) {
        const QJsonObject candidate = value.toObject();
        for (const QString& tag : candidateEmittedTags(candidate)) {
            if (consumed.contains(tag)) {
                continue;
            }
            const QJsonObject consumer = buildWorldbookConsumerCandidate(project, tag, candidate, additions.size());
            if (!consumer.isEmpty()) {
                additions.append(consumer);
                consumed.insert(tag);
            }
        }
    }
    for (const QJsonValue& value : additions) {
        candidates->append(value);
    }
}

void annotateTagConsumers(QJsonArray* candidates) {
    QSet<QString> consumedTags;
    for (int i = 0; i < candidates->size(); ++i) {
        QJsonObject candidate = candidates->at(i).toObject();
        const QStringList consumed = candidateConsumedTags(candidate);
        if (!consumed.isEmpty()) {
            candidate.insert(QStringLiteral("consumes_tags"), stringListToJsonArray(consumed));
            for (const QString& tag : consumed) {
                consumedTags.insert(tag);
            }
            candidates->replace(i, candidate);
        }
    }
    for (int i = 0; i < candidates->size(); ++i) {
        QJsonObject candidate = candidates->at(i).toObject();
        const QStringList emitted = candidateEmittedTags(candidate);
        if (emitted.isEmpty()) {
            continue;
        }
        candidate.insert(QStringLiteral("emits_tags"), stringListToJsonArray(emitted));
        QJsonArray warnings;
        for (const QString& tag : emitted) {
            if (!consumedTags.contains(tag)) {
                warnings.append(QStringLiteral("%1 当前只是设计草稿，后续需要世界书 external_tag 或演出工坊消费。").arg(tag));
            }
        }
        if (!warnings.isEmpty()) {
            candidate.insert(QStringLiteral("tag_warnings"), warnings);
        }
        candidates->replace(i, candidate);
    }
}

NormalizedCandidateBatch normalizeCandidateBatch(const QJsonObject& project, const QJsonArray& rawCandidates) {
    NormalizedCandidateBatch batch;
    batch.rawCount = rawCandidates.size();
    for (int i = 0; i < rawCandidates.size(); ++i) {
        const QJsonArray normalized = normalizeSingleCandidate(project, rawCandidates.at(i), i);
        if (normalized.isEmpty()) {
            ++batch.rejectedCount;
            continue;
        }
        for (const QJsonValue& value : normalized) {
            batch.candidates.append(value);
        }
    }
    ensureTagConsumers(project, &batch.candidates);
    ensureUniqueCandidateIds(&batch.candidates);
    annotateTagConsumers(&batch.candidates);
    return batch;
}

QJsonArray buildDefaultGroups(const QJsonArray& candidates) {
    QStringList groupIds;
    for (const QJsonValue& value : candidates) {
        const QString groupId = inferGroupId(value.toObject());
        if (!groupIds.contains(groupId)) {
            groupIds.append(groupId);
        }
    }
    QJsonArray groups;
    for (const QString& groupId : groupIds) {
        const QJsonArray candidateIds = collectGroupCandidateIds(groupId, candidates);
        if (candidateIds.isEmpty()) {
            continue;
        }
        groups.append(QJsonObject{
            { QStringLiteral("group_id"), groupId },
            { QStringLiteral("group_title"), inferGroupTitle(groupId, candidates) },
            { QStringLiteral("reason"), QString() },
            { QStringLiteral("candidate_ids"), candidateIds },
        });
    }
    return groups;
}

QJsonArray normalizeGroups(const QJsonValue& rawValue, const QJsonArray& candidates) {
    const QJsonArray rawGroups = rawValue.isArray() ? rawValue.toArray() : QJsonArray{};
    QJsonObject groupsById;
    QStringList orderedIds;
    for (const QJsonValue& value : rawGroups) {
        if (!value.isObject()) {
            continue;
        }
        const QJsonObject raw = value.toObject();
        const QString groupId = slugify(text(raw.value(QStringLiteral("group_id"))).isEmpty()
                ? text(raw.value(QStringLiteral("id")))
                : text(raw.value(QStringLiteral("group_id"))),
            QString());
        if (groupId.isEmpty()) {
            continue;
        }
        const QJsonArray candidateIds = collectGroupCandidateIds(groupId, candidates);
        if (candidateIds.isEmpty()) {
            continue;
        }
        QJsonObject group{
            { QStringLiteral("group_id"), groupId },
            { QStringLiteral("group_title"), text(raw.value(QStringLiteral("group_title"))).isEmpty()
                    ? inferGroupTitle(groupId, candidates)
                    : clippedText(text(raw.value(QStringLiteral("group_title"))), 120) },
            { QStringLiteral("reason"), clippedText(text(raw.value(QStringLiteral("reason"))), 400) },
            { QStringLiteral("candidate_ids"), candidateIds },
        };
        const QStringList dependsOn = normalizedDependsOn(raw.value(QStringLiteral("depends_on")));
        if (!dependsOn.isEmpty()) {
            group.insert(QStringLiteral("depends_on"), stringListToJsonArray(dependsOn));
        }
        if (raw.contains(QStringLiteral("draft_only"))) {
            group.insert(QStringLiteral("draft_only"), boolValue(raw.value(QStringLiteral("draft_only"))));
        }
        groupsById.insert(groupId, group);
        orderedIds.append(groupId);
    }

    const QJsonArray defaults = buildDefaultGroups(candidates);
    for (const QJsonValue& value : defaults) {
        const QJsonObject group = value.toObject();
        const QString groupId = group.value(QStringLiteral("group_id")).toString();
        if (!groupsById.contains(groupId)) {
            groupsById.insert(groupId, group);
            orderedIds.append(groupId);
        }
    }

    QJsonArray result;
    QSet<QString> seen;
    for (const QString& groupId : orderedIds) {
        if (seen.contains(groupId) || !groupsById.value(groupId).isObject()) {
            continue;
        }
        seen.insert(groupId);
        result.append(groupsById.value(groupId).toObject());
    }
    return result;
}

QJsonObject normalizePlan(const QJsonValue& rawValue, const QJsonArray& candidates) {
    const QJsonObject raw = rawValue.isObject() ? rawValue.toObject() : QJsonObject{};
    QJsonObject plan;
    for (const QString& key : { QStringLiteral("intent_type"), QStringLiteral("quality_goal"), QStringLiteral("summary"), QStringLiteral("package_mode") }) {
        const QString value = text(raw.value(key));
        if (!value.isEmpty()) {
            plan.insert(key, clippedText(value, 500));
        }
    }
    QStringList required;
    const QJsonArray rawRequired = raw.value(QStringLiteral("required_containers")).toArray();
    for (const QJsonValue& value : rawRequired) {
        const QString module = text(value).toLower();
        if (allowedModules().contains(module) && !required.contains(module)) {
            required.append(module);
        }
    }
    QJsonArray containerPlan;
    const QJsonArray rawContainerPlan = raw.value(QStringLiteral("container_plan")).toArray();
    for (const QJsonValue& value : rawContainerPlan) {
        const QJsonObject item = value.toObject();
        const QString module = text(item.value(QStringLiteral("module"))).toLower();
        const QString role = text(item.value(QStringLiteral("role")));
        if (allowedModules().contains(module) && !role.isEmpty()) {
            containerPlan.append(QJsonObject{
                { QStringLiteral("module"), module },
                { QStringLiteral("role"), clippedText(role, 300) },
            });
        }
        if (containerPlan.size() >= 12) {
            break;
        }
    }
    if (!containerPlan.isEmpty()) {
        plan.insert(QStringLiteral("container_plan"), containerPlan);
    }
    QJsonArray risks;
    for (const QJsonValue& value : raw.value(QStringLiteral("risks")).toArray()) {
        const QString risk = text(value);
        if (!risk.isEmpty()) {
            risks.append(clippedText(risk, 240));
        }
        if (risks.size() >= 8) {
            break;
        }
    }
    if (!risks.isEmpty()) {
        plan.insert(QStringLiteral("risks"), risks);
    }
    QJsonObject coverage;
    const QJsonObject rawCoverage = raw.value(QStringLiteral("coverage")).toObject();
    for (const QString& module : allowedModules()) {
        const QString value = text(rawCoverage.value(module));
        if (!value.isEmpty()) {
            coverage.insert(module, clippedText(value, 240));
        }
    }

    QStringList touchedModules;
    for (const QJsonValue& value : candidates) {
        const QString module = value.toObject().value(QStringLiteral("module")).toString();
        if (allowedModules().contains(module) && !touchedModules.contains(module)) {
            touchedModules.append(module);
        }
    }
    for (const QString& module : touchedModules) {
        if (!required.contains(module)) {
            required.append(module);
        }
    }
    if (!required.isEmpty()) {
        plan.insert(QStringLiteral("required_containers"), stringListToJsonArray(required));
    }
    if (!coverage.isEmpty()) {
        plan.insert(QStringLiteral("coverage"), coverage);
    }
    if (!touchedModules.isEmpty() && text(plan.value(QStringLiteral("package_mode"))).isEmpty()) {
        plan.insert(QStringLiteral("package_mode"), touchedModules.size() > 1 || touchedModules.contains(QStringLiteral("database")) ? QStringLiteral("runtime_package") : QStringLiteral("single_edit"));
    }
    if (text(plan.value(QStringLiteral("summary"))).isEmpty() && !touchedModules.isEmpty()) {
        plan.insert(QStringLiteral("summary"), QStringLiteral("本轮候选涉及 %1。").arg(touchedModules.join(QStringLiteral(", "))));
    }
    return plan;
}

QJsonObject buildPackageAudit(const QJsonArray& candidates, const QJsonObject& plan) {
    QStringList modules;
    QStringList emittedTags;
    QStringList consumedTags;
    for (const QJsonValue& value : candidates) {
        const QJsonObject candidate = value.toObject();
        const QString module = candidate.value(QStringLiteral("module")).toString();
        if (!module.isEmpty() && !modules.contains(module)) {
            modules.append(module);
        }
        for (const QString& tag : candidateEmittedTags(candidate)) {
            if (!emittedTags.contains(tag)) {
                emittedTags.append(tag);
            }
        }
        for (const QString& tag : candidateConsumedTags(candidate)) {
            if (!consumedTags.contains(tag)) {
                consumedTags.append(tag);
            }
        }
    }

    QStringList required = jsonArrayToStringList(plan.value(QStringLiteral("required_containers")).toArray());
    if (required.isEmpty() && plan.value(QStringLiteral("package_mode")).toString() == QStringLiteral("runtime_package")) {
        required = { QStringLiteral("persona"), QStringLiteral("worldbook"), QStringLiteral("memory"), QStringLiteral("database") };
    }
    QStringList missingContainers;
    for (const QString& module : required) {
        if (allowedModules().contains(module) && !modules.contains(module)) {
            missingContainers.append(module);
        }
    }
    QStringList missingTagConsumers;
    for (const QString& tag : emittedTags) {
        if (!consumedTags.contains(tag)) {
            missingTagConsumers.append(tag);
        }
    }
    QJsonArray warnings;
    if (!missingContainers.isEmpty()) {
        warnings.append(QStringLiteral("运行包候选缺少容器：%1。").arg(missingContainers.join(QStringLiteral(", "))));
    }
    if (!missingTagConsumers.isEmpty()) {
        warnings.append(QStringLiteral("有数据库 tag 暂未被世界书 external_tag 消费：%1。").arg(missingTagConsumers.join(QStringLiteral(", "))));
    }
    if (!modules.contains(QStringLiteral("preset"))) {
        warnings.append(QStringLiteral("没有轻量预设适配候选；若已有外部预设可忽略。"));
    }
    return QJsonObject{
        { QStringLiteral("package_mode"), plan.value(QStringLiteral("package_mode")).toString(modules.size() > 1 ? QStringLiteral("runtime_package") : QStringLiteral("single_edit")) },
        { QStringLiteral("modules"), stringListToJsonArray(modules) },
        { QStringLiteral("required_containers"), stringListToJsonArray(required) },
        { QStringLiteral("missing_containers"), stringListToJsonArray(missingContainers) },
        { QStringLiteral("emitted_tags"), stringListToJsonArray(emittedTags) },
        { QStringLiteral("consumed_tags"), stringListToJsonArray(consumedTags) },
        { QStringLiteral("missing_tag_consumers"), stringListToJsonArray(missingTagConsumers) },
        { QStringLiteral("has_light_preset"), modules.contains(QStringLiteral("preset")) },
        { QStringLiteral("ready"), missingContainers.isEmpty() && missingTagConsumers.isEmpty() },
        { QStringLiteral("warnings"), warnings },
    };
}

QJsonValue setAt(QJsonValue current, const QStringList& parts, int depth, const QJsonValue& after, bool* ok) {
    if (depth == parts.size()) {
        *ok = true;
        return after;
    }
    const QString part = parts.at(depth);
    if (current.isObject() || current.isUndefined()) {
        QJsonObject object = current.toObject();
        QJsonValue child = object.value(part);
        if (depth + 1 < parts.size() && child.isUndefined()) {
            child = isNumericPart(parts.at(depth + 1)) ? QJsonValue(QJsonArray{}) : QJsonValue(QJsonObject{});
        }
        const QJsonValue next = setAt(child, parts, depth + 1, after, ok);
        if (!*ok) {
            return current;
        }
        object.insert(part, next);
        return object;
    }
    if (current.isArray() && isNumericPart(part)) {
        QJsonArray array = current.toArray();
        const int index = part.toInt();
        if (index < 0 || index > array.size()) {
            *ok = false;
            return current;
        }
        if (index == array.size()) {
            if (depth + 1 == parts.size()) {
                array.append(after);
                *ok = true;
                return array;
            }
            array.append(isNumericPart(parts.at(depth + 1)) ? QJsonValue(QJsonArray{}) : QJsonValue(QJsonObject{}));
        }
        const QJsonValue next = setAt(array.at(index), parts, depth + 1, after, ok);
        if (!*ok) {
            return current;
        }
        array.replace(index, next);
        return array;
    }
    *ok = false;
    return current;
}

QJsonValue appendAt(QJsonValue current, const QStringList& parts, int depth, const QJsonValue& after, bool* ok) {
    if (depth == parts.size()) {
        QJsonArray array = current.toArray();
        if (!current.isArray() && !current.isUndefined()) {
            *ok = false;
            return current;
        }
        array.append(after);
        *ok = true;
        return array;
    }
    const QString part = parts.at(depth);
    if (current.isObject() || current.isUndefined()) {
        QJsonObject object = current.toObject();
        QJsonValue child = object.value(part);
        if (child.isUndefined()) {
            child = depth + 1 == parts.size() ? QJsonValue(QJsonArray{}) : QJsonValue(QJsonObject{});
        }
        const QJsonValue next = appendAt(child, parts, depth + 1, after, ok);
        if (!*ok) {
            return current;
        }
        object.insert(part, next);
        return object;
    }
    if (current.isArray() && isNumericPart(part)) {
        QJsonArray array = current.toArray();
        const int index = part.toInt();
        if (index < 0 || index >= array.size()) {
            *ok = false;
            return current;
        }
        const QJsonValue next = appendAt(array.at(index), parts, depth + 1, after, ok);
        if (!*ok) {
            return current;
        }
        array.replace(index, next);
        return array;
    }
    *ok = false;
    return current;
}

QJsonValue deleteAt(QJsonValue current, const QStringList& parts, int depth, bool* ok) {
    if (depth >= parts.size()) {
        *ok = false;
        return current;
    }
    const QString part = parts.at(depth);
    const bool leaf = depth + 1 == parts.size();
    if (current.isObject()) {
        QJsonObject object = current.toObject();
        if (!object.contains(part)) {
            *ok = false;
            return current;
        }
        if (leaf) {
            object.remove(part);
            *ok = true;
            return object;
        }
        const QJsonValue next = deleteAt(object.value(part), parts, depth + 1, ok);
        if (!*ok) {
            return current;
        }
        object.insert(part, next);
        return object;
    }
    if (current.isArray() && isNumericPart(part)) {
        QJsonArray array = current.toArray();
        const int index = part.toInt();
        if (index < 0 || index >= array.size()) {
            *ok = false;
            return current;
        }
        if (leaf) {
            array.removeAt(index);
            *ok = true;
            return array;
        }
        const QJsonValue next = deleteAt(array.at(index), parts, depth + 1, ok);
        if (!*ok) {
            return current;
        }
        array.replace(index, next);
        return array;
    }
    *ok = false;
    return current;
}

bool applyCandidatePatch(QJsonObject* project, const QJsonObject& candidate) {
    const QJsonObject target = candidate.value(QStringLiteral("target")).toObject();
    const QString path = target.value(QStringLiteral("path")).toString();
    const QString operation = target.value(QStringLiteral("operation")).toString(QStringLiteral("set"));
    if (!project || !isAllowedJsonPatchPath(path)) {
        return false;
    }
    bool ok = false;
    QJsonValue next;
    if (operation == QStringLiteral("append")) {
        next = appendAt(QJsonValue(*project), pathParts(path), 0, candidate.value(QStringLiteral("after")), &ok);
    } else if (operation == QStringLiteral("delete")) {
        next = deleteAt(QJsonValue(*project), pathParts(path), 0, &ok);
    } else {
        next = setAt(QJsonValue(*project), pathParts(path), 0, candidate.value(QStringLiteral("after")), &ok);
    }
    if (!ok || !next.isObject()) {
        return false;
    }
    *project = next.toObject();
    return true;
}
}

QJsonObject CardAuthoringCandidateProcessor::normalizeReview(const QJsonObject& project, const QJsonObject& review) const {
    const QJsonObject normalizedProject = CardAuthoring::normalizeProject(project);
    const QJsonArray rawCandidates = review.value(QStringLiteral("candidates")).toArray();
    const NormalizedCandidateBatch batch = normalizeCandidateBatch(normalizedProject, rawCandidates);
    const QJsonObject plan = normalizePlan(review.value(QStringLiteral("plan")), batch.candidates);
    const QJsonArray groups = normalizeGroups(review.value(QStringLiteral("candidate_groups")), batch.candidates);
    const QJsonObject audit = buildPackageAudit(batch.candidates, plan);
    const QString summary = text(review.value(QStringLiteral("summary"))).isEmpty()
        ? QStringLiteral("已整理出 %1 条可审核候选。").arg(batch.candidates.size())
        : text(review.value(QStringLiteral("summary")));

    return QJsonObject{
        { QStringLiteral("ok"), true },
        { QStringLiteral("summary"), summary },
        { QStringLiteral("plan"), plan },
        { QStringLiteral("candidate_groups"), groups },
        { QStringLiteral("candidates"), batch.candidates },
        { QStringLiteral("package_audit"), audit },
        { QStringLiteral("rejected_count"), batch.rejectedCount },
        { QStringLiteral("raw_candidate_count"), batch.rawCount },
    };
}

QJsonObject CardAuthoringCandidateProcessor::applyCandidates(const QJsonObject& project, const QJsonObject& review, const QStringList& selectedCandidateIds) const {
    const QJsonObject normalizedReview = normalizeReview(project, review);
    QJsonObject nextProject = CardAuthoring::normalizeProject(project);
    const QSet<QString> selected(selectedCandidateIds.constBegin(), selectedCandidateIds.constEnd());
    const bool applyAll = selected.isEmpty();

    QJsonArray applied;
    QJsonArray skipped;
    const QJsonArray candidates = normalizedReview.value(QStringLiteral("candidates")).toArray();
    for (const QJsonValue& value : candidates) {
        const QJsonObject candidate = value.toObject();
        const QString id = candidate.value(QStringLiteral("id")).toString();
        if (!applyAll && !selected.contains(id)) {
            skipped.append(id);
            continue;
        }
        if (applyCandidatePatch(&nextProject, candidate)) {
            applied.append(id);
        } else {
            skipped.append(id);
        }
    }

    nextProject = CardAuthoring::normalizeProject(nextProject);
    return QJsonObject{
        { QStringLiteral("ok"), true },
        { QStringLiteral("project"), nextProject },
        { QStringLiteral("review"), normalizedReview },
        { QStringLiteral("applied_candidate_ids"), applied },
        { QStringLiteral("skipped_candidate_ids"), skipped },
        { QStringLiteral("summary"), QJsonObject{
            { QStringLiteral("candidate_count"), candidates.size() },
            { QStringLiteral("applied_count"), applied.size() },
            { QStringLiteral("skipped_count"), skipped.size() },
        } },
    };
}
