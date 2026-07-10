#include "database/databasemodels.h"

#include <QJsonArray>
#include <QSet>

namespace {
QString normalizedText(const QJsonValue& value, int maximumLength = 240) {
    return value.toString().trimmed().left(maximumLength);
}

QString objectText(const QJsonObject& object, const QString& camelCase, const QString& snakeCase,
    int maximumLength = 240) {
    const QString camelCaseValue = normalizedText(object.value(camelCase), maximumLength);
    return camelCaseValue.isEmpty() ? normalizedText(object.value(snakeCase), maximumLength) : camelCaseValue;
}

void appendWarning(QStringList* warnings, const QString& warning) {
    if (warnings && !warnings->contains(warning)) {
        warnings->append(warning);
    }
}

QSet<QString> configuredVariableKeys(const QJsonObject& databaseConfig) {
    QSet<QString> keys;
    for (const QJsonValue& value : databaseConfig.value(QStringLiteral("variables")).toArray()) {
        const QJsonObject variable = value.toObject();
        const QString roleId = objectText(variable, QStringLiteral("roleId"), QStringLiteral("role_id"));
        const QString key = objectText(variable, QStringLiteral("key"), QStringLiteral("var_key"));
        if (!roleId.isEmpty() && !key.isEmpty()) {
            keys.insert(roleId + QLatin1Char('\x1f') + key);
        }
    }
    return keys;
}

QSet<QString> configuredRuntimeTags(const QJsonObject& databaseConfig) {
    QSet<QString> tags;
    for (const QJsonValue& value : databaseConfig.value(QStringLiteral("tags")).toArray()) {
        const QString tag = normalizedText(value.toObject().value(QStringLiteral("tag")), 240);
        if (!tag.isEmpty() && !tag.startsWith(QStringLiteral("database.stage."))) {
            tags.insert(tag);
        }
    }
    return tags;
}
}

QString replyDisplayModeToString(ReplyDisplayMode mode) {
    switch (mode) {
    case ReplyDisplayMode::StateRecord:
        return QStringLiteral("state_record");
    case ReplyDisplayMode::SplitBubbles:
    default:
        return QStringLiteral("split_bubbles");
    }
}

ReplyDisplayMode replyDisplayModeFromString(const QString& value, bool* recognized) {
    const QString normalized = value.trimmed().toLower();
    if (normalized == QStringLiteral("state_record")) {
        if (recognized) {
            *recognized = true;
        }
        return ReplyDisplayMode::StateRecord;
    }
    if (recognized) {
        *recognized = normalized == QStringLiteral("split_bubbles");
    }
    return ReplyDisplayMode::SplitBubbles;
}

QString databaseTurnStatusToString(DatabaseTurnStatus status) {
    switch (status) {
    case DatabaseTurnStatus::Ready:
        return QStringLiteral("ready");
    case DatabaseTurnStatus::Error:
        return QStringLiteral("error");
    case DatabaseTurnStatus::Superseded:
        return QStringLiteral("superseded");
    case DatabaseTurnStatus::Pending:
    default:
        return QStringLiteral("pending");
    }
}

DatabaseTurnStatus databaseTurnStatusFromString(const QString& value, bool* recognized) {
    const QString normalized = value.trimmed().toLower();
    if (normalized == QStringLiteral("ready")) {
        if (recognized) {
            *recognized = true;
        }
        return DatabaseTurnStatus::Ready;
    }
    if (normalized == QStringLiteral("error")) {
        if (recognized) {
            *recognized = true;
        }
        return DatabaseTurnStatus::Error;
    }
    if (normalized == QStringLiteral("superseded")) {
        if (recognized) {
            *recognized = true;
        }
        return DatabaseTurnStatus::Superseded;
    }
    if (recognized) {
        *recognized = normalized == QStringLiteral("pending");
    }
    return DatabaseTurnStatus::Pending;
}

bool DatabaseWorkerConfig::apiKeyConfigured() const {
    return !apiKey.trimmed().isEmpty();
}

QJsonObject normalizeDatabaseUpdates(const QJsonValue& value, const QJsonObject& databaseConfig,
    QStringList* warnings) {
    QJsonObject normalized;
    normalized.insert(QStringLiteral("schemaVersion"), 1);
    normalized.insert(QStringLiteral("variables"), QJsonArray{});
    normalized.insert(QStringLiteral("relationships"), QJsonArray{});
    normalized.insert(QStringLiteral("stages"), QJsonArray{});
    normalized.insert(QStringLiteral("ledger"), QJsonArray{});
    normalized.insert(QStringLiteral("tags"), QJsonArray{});

    if (!value.isObject()) {
        appendWarning(warnings, QStringLiteral("状态更新不是对象，已忽略运行态变更"));
        return normalized;
    }
    const QJsonObject source = value.toObject();
    if (source.value(QStringLiteral("schemaVersion")).toInt(1) != 1) {
        appendWarning(warnings, QStringLiteral("状态更新版本不受支持，已按版本 1 兼容处理"));
    }

    const QJsonObject snapshotSource = source.value(QStringLiteral("snapshot")).toObject();
    if (!snapshotSource.isEmpty()) {
        const QString scope = normalizedText(snapshotSource.value(QStringLiteral("scope")), 120);
        const QString title = normalizedText(snapshotSource.value(QStringLiteral("title")), 240);
        const QJsonObject payload = snapshotSource.value(QStringLiteral("payload")).toObject();
        if (scope.isEmpty() || title.isEmpty() || payload.isEmpty()) {
            appendWarning(warnings, QStringLiteral("有一项状态快照缺少范围、标题或内容，已忽略"));
        } else {
            normalized.insert(QStringLiteral("snapshot"), QJsonObject{
                { QStringLiteral("scope"), scope },
                { QStringLiteral("title"), title },
                { QStringLiteral("payload"), payload },
            });
        }
    }

    const QSet<QString> allowedVariables = configuredVariableKeys(databaseConfig);
    QJsonArray variables;
    for (const QJsonValue& itemValue : source.value(QStringLiteral("variables")).toArray()) {
        const QJsonObject item = itemValue.toObject();
        const QString roleId = objectText(item, QStringLiteral("roleId"), QStringLiteral("role_id"));
        const QString key = objectText(item, QStringLiteral("key"), QStringLiteral("var_key"));
        const QJsonValue runtimeValue = item.value(QStringLiteral("value"));
        if (roleId.isEmpty() || key.isEmpty() || runtimeValue.isUndefined() || runtimeValue.isNull()
            || !allowedVariables.contains(roleId + QLatin1Char('\x1f') + key)) {
            appendWarning(warnings, QStringLiteral("有一项变量更新不在角色卡配置中，已忽略"));
            continue;
        }
        QJsonObject variable{
            { QStringLiteral("roleId"), roleId },
            { QStringLiteral("key"), key },
            { QStringLiteral("value"), runtimeValue },
        };
        const QString label = normalizedText(item.value(QStringLiteral("label")));
        const QString reason = normalizedText(item.value(QStringLiteral("reason")), 600);
        if (!label.isEmpty()) {
            variable.insert(QStringLiteral("label"), label);
        }
        if (runtimeValue.isDouble() && item.value(QStringLiteral("maximum")).isDouble()) {
            variable.insert(QStringLiteral("maximum"), item.value(QStringLiteral("maximum")));
        }
        if (runtimeValue.isDouble() && item.value(QStringLiteral("delta")).isDouble()) {
            variable.insert(QStringLiteral("delta"), item.value(QStringLiteral("delta")));
        }
        if (!reason.isEmpty()) {
            variable.insert(QStringLiteral("reason"), reason);
        }
        variables.append(variable);
    }
    normalized.insert(QStringLiteral("variables"), variables);

    QJsonArray relationships;
    for (const QJsonValue& itemValue : source.value(QStringLiteral("relationships")).toArray()) {
        const QJsonObject item = itemValue.toObject();
        QString pairKey = objectText(item, QStringLiteral("pairKey"), QStringLiteral("pair_key"), 240);
        if (pairKey.isEmpty()) {
            pairKey = normalizedText(item.value(QStringLiteral("pair")), 240);
        }
        const QString roleA = objectText(item, QStringLiteral("roleA"), QStringLiteral("role_a"), 120);
        const QString roleB = objectText(item, QStringLiteral("roleB"), QStringLiteral("role_b"), 120);
        if (pairKey.isEmpty() && !roleA.isEmpty() && !roleB.isEmpty()) {
            pairKey = QStringLiteral("%1→%2").arg(roleA, roleB);
        }
        const QString stage = normalizedText(item.value(QStringLiteral("stage")), 160);
        const QString attitude = normalizedText(item.value(QStringLiteral("attitude")), 1200);
        const QString summary = normalizedText(item.value(QStringLiteral("summary")), 2400);
        const QString change = normalizedText(item.value(QStringLiteral("change")), 1200);
        if (pairKey.isEmpty() || (stage.isEmpty() && attitude.isEmpty() && summary.isEmpty() && change.isEmpty())) {
            appendWarning(warnings, QStringLiteral("有一项关系状态缺少关系标识或有效内容，已忽略"));
            continue;
        }
        QJsonObject relationship{
            { QStringLiteral("pairKey"), pairKey },
        };
        if (!roleA.isEmpty()) {
            relationship.insert(QStringLiteral("roleA"), roleA);
        }
        if (!roleB.isEmpty()) {
            relationship.insert(QStringLiteral("roleB"), roleB);
        }
        if (!stage.isEmpty()) {
            relationship.insert(QStringLiteral("stage"), stage);
        }
        if (!attitude.isEmpty()) {
            relationship.insert(QStringLiteral("attitude"), attitude);
        }
        if (!summary.isEmpty()) {
            relationship.insert(QStringLiteral("summary"), summary);
        }
        if (!change.isEmpty()) {
            relationship.insert(QStringLiteral("change"), change);
        }
        relationships.append(relationship);
    }
    normalized.insert(QStringLiteral("relationships"), relationships);

    if (!source.value(QStringLiteral("stages")).toArray().isEmpty()) {
        appendWarning(warnings, QStringLiteral("Worker 阶段更新已忽略，阶段仅由程序规则计算"));
    }

    QJsonObject storyTimeDelta = source.value(QStringLiteral("storyTimeDelta")).toObject();
    if (storyTimeDelta.isEmpty()) {
        storyTimeDelta = source.value(QStringLiteral("story_time_delta")).toObject();
    }
    if (!storyTimeDelta.isEmpty()) {
        QJsonObject delta;
        const QJsonValue seconds = storyTimeDelta.contains(QStringLiteral("deltaSeconds"))
            ? storyTimeDelta.value(QStringLiteral("deltaSeconds"))
            : storyTimeDelta.value(QStringLiteral("delta_seconds"));
        delta.insert(QStringLiteral("deltaSeconds"), qBound(0, seconds.toInt(), 86400));
        delta.insert(QStringLiteral("changed"), storyTimeDelta.value(QStringLiteral("changed")).toBool(seconds.toInt() > 0));
        delta.insert(QStringLiteral("deltaText"), objectText(
            storyTimeDelta, QStringLiteral("deltaText"), QStringLiteral("delta_text"), 160));
        delta.insert(QStringLiteral("confidence"), normalizedText(storyTimeDelta.value(QStringLiteral("confidence")), 32));
        delta.insert(QStringLiteral("reason"), normalizedText(storyTimeDelta.value(QStringLiteral("reason")), 240));
        normalized.insert(QStringLiteral("storyTimeDelta"), delta);
    }

    const QSet<QString> allowedTags = configuredRuntimeTags(databaseConfig);
    QJsonArray tags;
    for (const QJsonValue& itemValue : source.value(QStringLiteral("tags")).toArray()) {
        const QJsonObject item = itemValue.toObject();
        const QString tag = normalizedText(item.value(QStringLiteral("tag")), 240);
        if (tag.isEmpty() || tag.startsWith(QStringLiteral("database.stage.")) || !allowedTags.contains(tag)) {
            appendWarning(warnings, QStringLiteral("有一项运行标签不在角色卡允许集合中，已忽略"));
            continue;
        }
        tags.append(QJsonObject{
            { QStringLiteral("tag"), tag },
            { QStringLiteral("active"), item.value(QStringLiteral("active")).toBool(true) },
            { QStringLiteral("reason"), normalizedText(item.value(QStringLiteral("reason")), 240) },
            { QStringLiteral("sourceType"), QStringLiteral("runtime") },
            { QStringLiteral("sourceKey"), tag },
        });
    }

    QJsonArray ledger;
    for (const QJsonValue& itemValue : source.value(QStringLiteral("ledger")).toArray()) {
        const QJsonObject item = itemValue.toObject();
        const QString entryType = normalizedText(item.value(QStringLiteral("entryType")), 80);
        const QString content = normalizedText(item.value(QStringLiteral("content")), 4000);
        if (entryType.isEmpty() || content.isEmpty()) {
            appendWarning(warnings, QStringLiteral("有一项剧情账本缺少类型或内容，已忽略"));
            continue;
        }
        QJsonObject entry{
            { QStringLiteral("entryType"), entryType },
            { QStringLiteral("content"), content },
        };
        const QJsonObject payload = item.value(QStringLiteral("payload")).toObject();
        if (!payload.isEmpty()) {
            entry.insert(QStringLiteral("payload"), payload);
        }
        QString activationTag = objectText(item,
            QStringLiteral("activationTag"), QStringLiteral("activation_tag"), 240);
        if (activationTag.isEmpty()) {
            activationTag = objectText(payload, QStringLiteral("activationTag"), QStringLiteral("tag"), 240);
        }
        if (!activationTag.isEmpty()) {
            if (activationTag.startsWith(QStringLiteral("database.stage.")) || !allowedTags.contains(activationTag)) {
                appendWarning(warnings, QStringLiteral("有一项剧情账本标签不在角色卡允许集合中，已忽略"));
            } else {
                const QString status = normalizedText(payload.value(QStringLiteral("status")), 40).toLower();
                const bool active = item.value(QStringLiteral("active")).toBool(
                    status != QStringLiteral("inactive") && status != QStringLiteral("hidden"));
                entry.insert(QStringLiteral("activationTag"), activationTag);
                tags.append(QJsonObject{
                    { QStringLiteral("tag"), activationTag },
                    { QStringLiteral("active"), active },
                    { QStringLiteral("reason"), QStringLiteral("剧情账本：%1").arg(content.left(180)) },
                    { QStringLiteral("sourceType"), QStringLiteral("ledger") },
                    { QStringLiteral("sourceKey"), QStringLiteral("%1:%2").arg(entryType, activationTag) },
                });
            }
        }
        ledger.append(entry);
    }
    normalized.insert(QStringLiteral("ledger"), ledger);
    normalized.insert(QStringLiteral("tags"), tags);
    return normalized;
}
