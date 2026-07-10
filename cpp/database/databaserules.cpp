#include "database/databaserules.h"

#include <QCryptographicHash>
#include <QDateTime>
#include <QJsonArray>
#include <QSet>
#include <QStringList>

#include <algorithm>

namespace {
constexpr auto kStoryTimeFormat = "yyyy-MM-dd HH:mm:ss";

QString objectText(const QJsonObject& object, const QString& primary, const QString& fallback = {}) {
    QString value = object.value(primary).toString().trimmed();
    if (value.isEmpty() && !fallback.isEmpty()) {
        value = object.value(fallback).toString().trimmed();
    }
    return value;
}

int boundedInt(const QJsonValue& value, int fallback, int minimum, int maximum) {
    bool ok = false;
    int result = value.toVariant().toInt(&ok);
    return qBound(minimum, ok ? result : fallback, maximum);
}

QDateTime parseStoryTime(const QString& source) {
    const QString text = source.trimmed();
    const QStringList formats{
        QString::fromLatin1(kStoryTimeFormat),
        QStringLiteral("yyyy-MM-dd HH:mm"),
        QStringLiteral("yyyy-MM-dd"),
        QStringLiteral("yyyy/MM/dd HH:mm:ss"),
        QStringLiteral("yyyy/MM/dd HH:mm"),
    };
    for (const QString& format : formats) {
        const QDateTime parsed = QDateTime::fromString(text, format);
        if (parsed.isValid()) {
            return parsed;
        }
    }
    const QDateTime iso = QDateTime::fromString(text, Qt::ISODate);
    return iso.isValid() ? iso : QDateTime{};
}

QString storyTimeText(const QDateTime& value) {
    return value.isValid() ? value.toString(QString::fromLatin1(kStoryTimeFormat)) : QString{};
}

QString seasonForMonth(int month) {
    if (month >= 3 && month <= 5) {
        return QStringLiteral("spring");
    }
    if (month >= 6 && month <= 8) {
        return QStringLiteral("summer");
    }
    if (month >= 9 && month <= 11) {
        return QStringLiteral("autumn");
    }
    return QStringLiteral("winter");
}

QString timeSlotForHour(int hour) {
    if (hour >= 23 || hour <= 6) {
        return QStringLiteral("late_night");
    }
    if (hour <= 8) {
        return QStringLiteral("dawn");
    }
    if (hour <= 11) {
        return QStringLiteral("morning");
    }
    if (hour <= 14) {
        return QStringLiteral("noon");
    }
    if (hour <= 18) {
        return QStringLiteral("afternoon");
    }
    if (hour <= 20) {
        return QStringLiteral("dusk");
    }
    return QStringLiteral("night");
}

QString seasonLabel(const QString& season) {
    if (season == QStringLiteral("spring")) return QStringLiteral("春");
    if (season == QStringLiteral("summer")) return QStringLiteral("夏");
    if (season == QStringLiteral("autumn")) return QStringLiteral("秋");
    return QStringLiteral("冬");
}

QString timeSlotLabel(const QString& slot) {
    if (slot == QStringLiteral("late_night")) return QStringLiteral("深夜");
    if (slot == QStringLiteral("dawn")) return QStringLiteral("清晨");
    if (slot == QStringLiteral("morning")) return QStringLiteral("上午");
    if (slot == QStringLiteral("noon")) return QStringLiteral("正午");
    if (slot == QStringLiteral("afternoon")) return QStringLiteral("下午");
    if (slot == QStringLiteral("dusk")) return QStringLiteral("黄昏");
    return QStringLiteral("夜晚");
}

QString normalizedAdvanceMode(const QString& value) {
    const QString mode = value.trimmed().toLower();
    return QStringList{
        QStringLiteral("smart"), QStringLiteral("explicit"),
        QStringLiteral("custom"), QStringLiteral("manual"),
    }.contains(mode) ? mode : QStringLiteral("smart");
}

QString normalizedDisplayMode(const QString& value) {
    const QString mode = value.trimmed().toLower();
    return QStringList{
        QStringLiteral("datetime_minute"), QStringLiteral("datetime_second"), QStringLiteral("day_slot"),
    }.contains(mode) ? mode : QStringLiteral("datetime_minute");
}

QString normalizedCustomType(const QString& value) {
    return value.trimmed().toLower() == QStringLiteral("fixed")
        ? QStringLiteral("fixed") : QStringLiteral("range");
}

QString formatDuration(int seconds) {
    int remaining = qMax(0, seconds);
    const int days = remaining / 86400;
    remaining %= 86400;
    const int hours = remaining / 3600;
    remaining %= 3600;
    const int minutes = remaining / 60;
    const int secs = remaining % 60;
    QStringList parts;
    if (days > 0) {
        parts.append(QStringLiteral("%1天").arg(days));
    }
    if (hours > 0) {
        parts.append(QStringLiteral("%1小时").arg(hours));
    }
    if (minutes > 0) {
        parts.append(QStringLiteral("%1分钟").arg(minutes));
    }
    if (secs > 0 || parts.isEmpty()) {
        parts.append(QStringLiteral("%1秒").arg(secs));
    }
    return parts.join(QString());
}

bool roleUsesStages(const QJsonObject& role) {
    if (!role.value(QStringLiteral("enabled")).toBool(true)) {
        return false;
    }
    const QString mode = objectText(role, QStringLiteral("mode"), QStringLiteral("stateJournalMode")).toLower();
    return mode.isEmpty() || mode == QStringLiteral("default") || mode == QStringLiteral("stages")
        || mode == QStringLiteral("full");
}

QString roleIdOf(const QJsonObject& object) {
    return objectText(object, QStringLiteral("role_id"), QStringLiteral("roleId"));
}

QString stageKeyOf(const QJsonObject& object) {
    return objectText(object, QStringLiteral("stage_key"), QStringLiteral("stageKey"));
}

QJsonArray stagesForRole(const QJsonObject& databaseConfig, const QJsonObject& role, const QString& roleId) {
    QJsonArray stages = role.value(QStringLiteral("stages")).toArray();
    if (!stages.isEmpty()) {
        return stages;
    }
    for (const QJsonValue& value : databaseConfig.value(QStringLiteral("stages")).toArray()) {
        if (roleIdOf(value.toObject()) == roleId) {
            stages.append(value);
        }
    }
    return stages;
}

QJsonObject stageByKey(const QJsonArray& stages, const QString& key) {
    for (const QJsonValue& value : stages) {
        const QJsonObject stage = value.toObject();
        if (stageKeyOf(stage) == key) {
            return stage;
        }
    }
    return {};
}

bool compareCondition(const QJsonValue& current, const QString& op, const QJsonValue& target) {
    if (current.isUndefined() || current.isNull()) {
        return false;
    }
    if (current.isDouble() && target.isDouble()) {
        const double left = current.toDouble();
        const double right = target.toDouble();
        if (op == QStringLiteral(">")) return left > right;
        if (op == QStringLiteral(">=")) return left >= right;
        if (op == QStringLiteral("<")) return left < right;
        if (op == QStringLiteral("<=")) return left <= right;
        if (op == QStringLiteral("!=")) return left != right;
        return left == right;
    }
    const QString left = current.toVariant().toString().trimmed();
    const QString right = target.toVariant().toString().trimmed();
    if (op == QStringLiteral("!=")) {
        return left != right;
    }
    return op == QStringLiteral("=") && left == right;
}

QPair<bool, QJsonObject> stageMatches(const QJsonObject& stage, const QString& roleId,
    const QHash<QString, QJsonValue>& runtimeValues, const QJsonObject& storyContext) {
    const QJsonArray conditions = stage.value(QStringLiteral("conditions")).toArray();
    if (conditions.isEmpty()) {
        return {false, {}};
    }
    QList<bool> results;
    QJsonObject triggers;
    for (const QJsonValue& value : conditions) {
        const QJsonObject condition = value.toObject();
        const QString source = condition.value(QStringLiteral("source")).toString().trimmed().toLower();
        QString op = condition.value(QStringLiteral("op")).toString(QStringLiteral(">=")).trimmed();
        if (!QStringList{
                QStringLiteral(">"), QStringLiteral(">="), QStringLiteral("<"),
                QStringLiteral("<="), QStringLiteral("="), QStringLiteral("!="),
            }.contains(op)) {
            op = QStringLiteral(">=");
        }
        QJsonValue current;
        QJsonValue target = condition.value(QStringLiteral("value"));
        QString triggerKey;
        if (source == QStringLiteral("story_time")) {
            const QString field = condition.value(QStringLiteral("field")).toString().trimmed();
            if (!QStringList{
                    QStringLiteral("elapsed_seconds"), QStringLiteral("elapsed_hours"),
                    QStringLiteral("elapsed_days"), QStringLiteral("current_hour"),
                    QStringLiteral("current_date"), QStringLiteral("time_slot"), QStringLiteral("season"),
                }.contains(field)) {
                continue;
            }
            current = storyContext.value(field);
            triggerKey = QStringLiteral("story_time.%1").arg(field);
        } else {
            const QString key = objectText(condition, QStringLiteral("var"), QStringLiteral("field"));
            if (key.isEmpty()) {
                continue;
            }
            current = runtimeValues.value(roleId + QLatin1Char('\x1f') + key);
            triggerKey = key;
        }
        triggers.insert(triggerKey, current);
        results.append(compareCondition(current, op, target));
    }
    if (results.isEmpty()) {
        return {false, triggers};
    }
    const bool any = stage.value(QStringLiteral("condition_mode")).toString().trimmed().toLower()
        == QStringLiteral("any");
    return {any ? std::any_of(results.cbegin(), results.cend(), [](bool result) { return result; })
                : std::all_of(results.cbegin(), results.cend(), [](bool result) { return result; }),
        triggers};
}

QStringList stageTags(const QJsonObject& stage, const QString& roleId, const QString& stageKey) {
    QString activeTag = objectText(stage, QStringLiteral("activation_tag"), QStringLiteral("active_tag"));
    if (activeTag.isEmpty()) {
        activeTag = QStringLiteral("database.stage.%1.%2").arg(roleId, stageKey);
    }
    QStringList tags{activeTag};
    for (const QJsonValue& value : stage.value(QStringLiteral("emits_tags")).toArray()) {
        const QString tag = value.toString().trimmed();
        if (!tag.isEmpty() && !tags.contains(tag)) {
            tags.append(tag);
        }
    }
    return tags;
}

QJsonArray stringArray(const QStringList& values) {
    QJsonArray result;
    for (const QString& value : values) {
        result.append(value);
    }
    return result;
}
}

namespace DatabaseRules {

QJsonObject defaultStoryTimeState(const QString& cardUid) {
    const QDateTime base = QDateTime::currentDateTime();
    return {
        { QStringLiteral("cardUid"), cardUid.trimmed() },
        { QStringLiteral("enabled"), false },
        { QStringLiteral("showInRecord"), true },
        { QStringLiteral("baseTime"), storyTimeText(base) },
        { QStringLiteral("currentTime"), QString() },
        { QStringLiteral("elapsedSeconds"), 0 },
        { QStringLiteral("season"), seasonForMonth(base.date().month()) },
        { QStringLiteral("timeSlot"), timeSlotForHour(base.time().hour()) },
        { QStringLiteral("advanceMode"), QStringLiteral("smart") },
        { QStringLiteral("customAdvanceType"), QStringLiteral("range") },
        { QStringLiteral("customAdvanceMinSeconds"), 300 },
        { QStringLiteral("customAdvanceMaxSeconds"), 900 },
        { QStringLiteral("displayMode"), QStringLiteral("datetime_minute") },
        { QStringLiteral("lastDeltaSeconds"), 0 },
        { QStringLiteral("lastDeltaText"), QString() },
        { QStringLiteral("lastConfidence"), QString() },
        { QStringLiteral("initialized"), false },
    };
}

QJsonObject normalizeStoryTimeState(const QJsonObject& input, const QString& cardUid) {
    QJsonObject state = defaultStoryTimeState(cardUid);
    for (auto it = input.constBegin(); it != input.constEnd(); ++it) {
        state.insert(it.key(), it.value());
    }
    state.insert(QStringLiteral("cardUid"), cardUid.trimmed());
    state.insert(QStringLiteral("enabled"), state.value(QStringLiteral("enabled")).toBool(false));
    state.insert(QStringLiteral("showInRecord"), state.value(QStringLiteral("showInRecord")).toBool(true));
    state.insert(QStringLiteral("advanceMode"), normalizedAdvanceMode(state.value(QStringLiteral("advanceMode")).toString()));
    state.insert(QStringLiteral("displayMode"), normalizedDisplayMode(state.value(QStringLiteral("displayMode")).toString()));
    const QString customType = normalizedCustomType(state.value(QStringLiteral("customAdvanceType")).toString());
    int minimum = boundedInt(state.value(QStringLiteral("customAdvanceMinSeconds")), 300, 0, 86400);
    int maximum = boundedInt(state.value(QStringLiteral("customAdvanceMaxSeconds")), 900, 0, 86400);
    if (customType == QStringLiteral("fixed")) {
        maximum = minimum;
    } else if (maximum < minimum) {
        std::swap(minimum, maximum);
    }
    state.insert(QStringLiteral("customAdvanceType"), customType);
    state.insert(QStringLiteral("customAdvanceMinSeconds"), minimum);
    state.insert(QStringLiteral("customAdvanceMaxSeconds"), maximum);

    QDateTime current = parseStoryTime(state.value(QStringLiteral("currentTime")).toString());
    QDateTime base = parseStoryTime(state.value(QStringLiteral("baseTime")).toString());
    if (!base.isValid()) {
        base = current.isValid() ? current : QDateTime::currentDateTime();
    }
    state.insert(QStringLiteral("baseTime"), storyTimeText(base));
    state.insert(QStringLiteral("currentTime"), storyTimeText(current));
    const qint64 elapsed = current.isValid() ? qMax<qint64>(0, base.secsTo(current)) : 0;
    state.insert(QStringLiteral("elapsedSeconds"), elapsed);
    state.insert(QStringLiteral("season"), seasonForMonth((current.isValid() ? current : base).date().month()));
    state.insert(QStringLiteral("timeSlot"), timeSlotForHour((current.isValid() ? current : base).time().hour()));
    state.insert(QStringLiteral("initialized"), current.isValid());
    state.insert(QStringLiteral("seasonLabel"), seasonLabel(state.value(QStringLiteral("season")).toString()));
    state.insert(QStringLiteral("timeSlotLabel"), timeSlotLabel(state.value(QStringLiteral("timeSlot")).toString()));
    QString displayTime;
    if (current.isValid()) {
        if (state.value(QStringLiteral("displayMode")).toString() == QStringLiteral("datetime_second")) {
            displayTime = current.toString(QStringLiteral("yyyy年M月d日 HH:mm:ss"));
        } else if (state.value(QStringLiteral("displayMode")).toString() == QStringLiteral("day_slot")) {
            displayTime = QStringLiteral("第 %1 日 · %2")
                              .arg(state.value(QStringLiteral("elapsedSeconds")).toVariant().toLongLong() / 86400 + 1)
                              .arg(state.value(QStringLiteral("timeSlotLabel")).toString());
        } else {
            displayTime = current.toString(QStringLiteral("yyyy年M月d日 HH:mm"));
        }
    }
    state.insert(QStringLiteral("displayTime"), displayTime);
    return state;
}

QJsonObject configureStoryTime(const QJsonObject& current, const QJsonObject& draft, const QString& cardUid) {
    QJsonObject merged = normalizeStoryTimeState(current, cardUid);
    const QStringList copiedFields{
        QStringLiteral("enabled"), QStringLiteral("showInRecord"), QStringLiteral("baseTime"),
        QStringLiteral("currentTime"), QStringLiteral("advanceMode"), QStringLiteral("customAdvanceType"),
        QStringLiteral("customAdvanceMinSeconds"), QStringLiteral("customAdvanceMaxSeconds"),
        QStringLiteral("displayMode"),
    };
    for (const QString& field : copiedFields) {
        if (draft.contains(field)) {
            merged.insert(field, draft.value(field));
        }
    }
    const QString action = draft.value(QStringLiteral("action")).toString().trimmed().toLower();
    if (action == QStringLiteral("initialize")) {
        const QString baseTime = draft.value(QStringLiteral("baseTime")).toString(
            merged.value(QStringLiteral("baseTime")).toString());
        merged.insert(QStringLiteral("baseTime"), baseTime);
        merged.insert(QStringLiteral("currentTime"), baseTime);
        merged.insert(QStringLiteral("enabled"), true);
    } else if (action == QStringLiteral("reset")) {
        merged.insert(QStringLiteral("currentTime"), merged.value(QStringLiteral("baseTime")));
        merged.insert(QStringLiteral("lastDeltaSeconds"), 0);
        merged.insert(QStringLiteral("lastDeltaText"), QString());
        merged.insert(QStringLiteral("lastConfidence"), QString());
    } else if (action == QStringLiteral("calibrate") && draft.contains(QStringLiteral("currentTime"))) {
        merged.insert(QStringLiteral("currentTime"), draft.value(QStringLiteral("currentTime")));
    }
    return normalizeStoryTimeState(merged, cardUid);
}

QJsonObject advanceStoryTime(const QJsonObject& current, const QJsonObject& rawDelta,
    const QString& turnId, const QString& messageId, qint64 turnOrdinal) {
    QJsonObject state = normalizeStoryTimeState(current, current.value(QStringLiteral("cardUid")).toString());
    if (!state.value(QStringLiteral("enabled")).toBool() || !state.value(QStringLiteral("initialized")).toBool()) {
        return {};
    }
    const QString mode = state.value(QStringLiteral("advanceMode")).toString();
    int deltaSeconds = 0;
    QString confidence = rawDelta.value(QStringLiteral("confidence")).toString().trimmed().toLower();
    QString deltaText = objectText(rawDelta, QStringLiteral("deltaText"), QStringLiteral("delta_text"));
    QString reason = rawDelta.value(QStringLiteral("reason")).toString().trimmed().left(240);
    QString source = QStringLiteral("worker");
    if (mode == QStringLiteral("custom")) {
        const int minimum = state.value(QStringLiteral("customAdvanceMinSeconds")).toInt(300);
        const int maximum = state.value(QStringLiteral("customAdvanceMaxSeconds")).toInt(900);
        deltaSeconds = minimum;
        if (maximum > minimum) {
            const QByteArray seed = QStringLiteral("%1|%2|%3|%4|%5")
                                        .arg(state.value(QStringLiteral("cardUid")).toString(),
                                            state.value(QStringLiteral("currentTime")).toString(),
                                            turnId, messageId)
                                        .arg(turnOrdinal)
                                        .toUtf8();
            const QByteArray digest = QCryptographicHash::hash(seed, QCryptographicHash::Sha256).toHex().left(8);
            bool ok = false;
            const quint32 number = digest.toUInt(&ok, 16);
            deltaSeconds += ok ? static_cast<int>(number % static_cast<quint32>(maximum - minimum + 1)) : 0;
        }
        confidence = deltaSeconds > 0 ? QStringLiteral("high") : QStringLiteral("none");
        deltaText = QStringLiteral("自定义推进 %1").arg(formatDuration(deltaSeconds));
        reason = QStringLiteral("按数据库剧情时间的自定义规则推进");
        source = QStringLiteral("custom");
    } else if (mode != QStringLiteral("manual")) {
        const QJsonValue rawSeconds = rawDelta.contains(QStringLiteral("deltaSeconds"))
            ? rawDelta.value(QStringLiteral("deltaSeconds")) : rawDelta.value(QStringLiteral("delta_seconds"));
        deltaSeconds = boundedInt(rawSeconds, 0, 0, 86400);
        if (!QStringList{QStringLiteral("none"), QStringLiteral("low"), QStringLiteral("medium"), QStringLiteral("high")}.contains(confidence)) {
            confidence = deltaSeconds > 0 ? QStringLiteral("medium") : QStringLiteral("none");
        }
        if (deltaSeconds > 7200 && confidence != QStringLiteral("high")) {
            deltaSeconds = 7200;
        }
    }
    if (mode == QStringLiteral("manual")) {
        confidence = QStringLiteral("none");
        deltaText.clear();
        reason = QStringLiteral("手动推进模式");
        source = QStringLiteral("manual");
    }

    const QDateTime oldTime = parseStoryTime(state.value(QStringLiteral("currentTime")).toString());
    const QDateTime newTime = oldTime.addSecs(deltaSeconds);
    state.insert(QStringLiteral("currentTime"), storyTimeText(newTime));
    state.insert(QStringLiteral("lastDeltaSeconds"), deltaSeconds);
    state.insert(QStringLiteral("lastDeltaText"), deltaText.left(160));
    state.insert(QStringLiteral("lastConfidence"), confidence);
    state = normalizeStoryTimeState(state, state.value(QStringLiteral("cardUid")).toString());
    state.insert(QStringLiteral("oldTime"), storyTimeText(oldTime));
    state.insert(QStringLiteral("deltaReason"), reason);
    state.insert(QStringLiteral("deltaSource"), source);
    return state;
}

QJsonObject storyTimeContext(const QJsonObject& stateValue) {
    const QJsonObject state = normalizeStoryTimeState(
        stateValue, stateValue.value(QStringLiteral("cardUid")).toString());
    const QDateTime current = parseStoryTime(state.value(QStringLiteral("currentTime")).toString());
    if (!current.isValid()) {
        return {};
    }
    const qint64 elapsed = state.value(QStringLiteral("elapsedSeconds")).toVariant().toLongLong();
    return {
        { QStringLiteral("elapsed_seconds"), elapsed },
        { QStringLiteral("elapsed_hours"), elapsed / 3600 },
        { QStringLiteral("elapsed_days"), elapsed / 86400 },
        { QStringLiteral("current_hour"), current.time().hour() },
        { QStringLiteral("current_date"), current.date().toString(QStringLiteral("yyyy-MM-dd")) },
        { QStringLiteral("time_slot"), timeSlotForHour(current.time().hour()) },
        { QStringLiteral("season"), seasonForMonth(current.date().month()) },
    };
}

QList<QJsonObject> evaluateStages(const QJsonObject& databaseConfig,
    const QHash<QString, QJsonValue>& runtimeValues, const QJsonObject& storyContext,
    const QHash<QString, QJsonObject>& currentStages, qint64 turnOrdinal) {
    QList<QJsonObject> decisions;
    for (const QJsonValue& roleValue : databaseConfig.value(QStringLiteral("roles")).toArray()) {
        const QJsonObject role = roleValue.toObject();
        if (!roleUsesStages(role)) {
            continue;
        }
        const QString roleId = roleIdOf(role);
        if (roleId.isEmpty()) {
            continue;
        }
        QJsonArray stages = stagesForRole(databaseConfig, role, roleId);
        if (stages.isEmpty()) {
            continue;
        }
        QList<QJsonObject> enabledStages;
        for (const QJsonValue& value : stages) {
            if (value.toObject().value(QStringLiteral("enabled")).toBool(true)) {
                enabledStages.append(value.toObject());
            }
        }
        std::sort(enabledStages.begin(), enabledStages.end(), [](const QJsonObject& left, const QJsonObject& right) {
            return left.value(QStringLiteral("priority")).toInt() > right.value(QStringLiteral("priority")).toInt();
        });

        QJsonObject target;
        QJsonObject triggerValues;
        for (const QJsonObject& stage : enabledStages) {
            const auto [matched, triggers] = stageMatches(stage, roleId, runtimeValues, storyContext);
            if (matched) {
                target = stage;
                triggerValues = triggers;
                break;
            }
        }
        if (target.isEmpty()) {
            target = stageByKey(stages, role.value(QStringLiteral("initial_stage")).toString(QStringLiteral("stage_a")));
        }
        if (target.isEmpty()) {
            continue;
        }

        const QJsonObject current = currentStages.value(roleId);
        const QString currentKey = current.value(QStringLiteral("stageKey")).toString();
        const QJsonObject currentState = current.value(QStringLiteral("state")).toObject();
        const QJsonObject currentStage = stageByKey(stages, currentKey);
        QString targetKey = stageKeyOf(target);
        QString candidateKey = currentState.value(QStringLiteral("candidateStageKey")).toString();
        int candidateCount = currentState.value(QStringLiteral("candidateCount")).toInt();
        bool changed = targetKey != currentKey;
        QString reason = triggerValues.isEmpty()
            ? QStringLiteral("使用初始阶段") : QStringLiteral("阶段条件已满足");

        const QJsonObject roleSettings = role.value(QStringLiteral("settings")).toObject();
        const bool allowRegression = target.value(QStringLiteral("allow_regression")).toBool(
            roleSettings.value(QStringLiteral("allow_regression")).toBool(false));
        const int targetPriority = target.value(QStringLiteral("priority")).toInt();
        const int currentPriority = currentStage.value(QStringLiteral("priority")).toInt(-10000);
        const qint64 cooldownUntil = currentState.value(QStringLiteral("cooldownUntilTurn")).toVariant().toLongLong();
        if (changed && !currentKey.isEmpty() && targetPriority < currentPriority && !allowRegression) {
            target = currentStage;
            targetKey = currentKey;
            changed = false;
            reason = QStringLiteral("目标阶段优先级较低且未允许回退");
        } else if (changed && !currentKey.isEmpty() && cooldownUntil > turnOrdinal) {
            target = currentStage;
            targetKey = currentKey;
            changed = false;
            reason = QStringLiteral("阶段仍在冷却期");
        }

        const int confirmTurns = qMax(1, target.value(QStringLiteral("confirm_turns")).toInt(
            roleSettings.value(QStringLiteral("confirm_turns")).toInt(1)));
        if (changed && !currentKey.isEmpty()) {
            candidateCount = candidateKey == targetKey ? candidateCount + 1 : 1;
            candidateKey = targetKey;
            if (candidateCount < confirmTurns) {
                target = currentStage;
                targetKey = currentKey;
                changed = false;
                reason = QStringLiteral("候选阶段等待连续确认（%1/%2）").arg(candidateCount).arg(confirmTurns);
            }
        } else if (targetKey == currentKey) {
            candidateKey.clear();
            candidateCount = 0;
        }

        const QString stageName = objectText(target, QStringLiteral("stage_name"), QStringLiteral("title"));
        const QString currentName = objectText(currentStage, QStringLiteral("stage_name"), QStringLiteral("title"));
        const QStringList tags = stageTags(target, roleId, targetKey);
        qint64 nextCooldown = cooldownUntil;
        if (changed) {
            const int cooldownTurns = qMax(0, target.value(QStringLiteral("cooldown_turns")).toInt(
                roleSettings.value(QStringLiteral("cooldown_turns")).toInt(0)));
            nextCooldown = turnOrdinal + cooldownTurns;
            candidateKey.clear();
            candidateCount = 0;
        }
        const qint64 changedAtTurn = changed ? turnOrdinal
            : currentState.value(QStringLiteral("changedAtTurn")).toVariant().toLongLong();
        QJsonObject state{
            { QStringLiteral("active"), true },
            { QStringLiteral("stageName"), stageName.isEmpty() ? targetKey : stageName },
            { QStringLiteral("previousStageKey"), changed ? currentKey : currentState.value(QStringLiteral("previousStageKey")).toString() },
            { QStringLiteral("previousStageName"), changed ? currentName : currentState.value(QStringLiteral("previousStageName")).toString() },
            { QStringLiteral("changed"), changed },
            { QStringLiteral("activeTag"), tags.value(0) },
            { QStringLiteral("emitsTags"), stringArray(tags) },
            { QStringLiteral("candidateStageKey"), candidateKey },
            { QStringLiteral("candidateCount"), candidateCount },
            { QStringLiteral("changedAtTurn"), changedAtTurn },
            { QStringLiteral("cooldownUntilTurn"), nextCooldown },
            { QStringLiteral("reason"), reason },
            { QStringLiteral("triggerValues"), triggerValues },
        };
        decisions.append(QJsonObject{
            { QStringLiteral("roleId"), roleId },
            { QStringLiteral("roleName"), objectText(role, QStringLiteral("role_name"), QStringLiteral("name")) },
            { QStringLiteral("stageKey"), targetKey },
            { QStringLiteral("stageName"), state.value(QStringLiteral("stageName")) },
            { QStringLiteral("previousStageKey"), currentKey },
            { QStringLiteral("previousStageName"), currentName },
            { QStringLiteral("changed"), changed },
            { QStringLiteral("state"), state },
            { QStringLiteral("tags"), stringArray(tags) },
            { QStringLiteral("reason"), reason },
            { QStringLiteral("triggerValues"), triggerValues },
        });
    }
    return decisions;
}

}
