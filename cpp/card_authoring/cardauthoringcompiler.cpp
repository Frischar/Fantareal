#include "card_authoring/cardauthoringcompiler.h"

#include "card_authoring/cardauthoringmodels.h"

#include <QJsonArray>
#include <QJsonObject>
#include <QRegularExpression>
#include <QSet>

namespace {
QString normalizeFaKey(const QString& value, const QString& fallback) {
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

double numberValue(const QJsonValue& value, double fallback = 0.0) {
    if (value.isDouble()) {
        return value.toDouble(fallback);
    }
    bool ok = false;
    const double parsed = CardAuthoring::normalizedText(value).toDouble(&ok);
    return ok ? parsed : fallback;
}

bool boolValue(const QJsonValue& value, bool fallback) {
    if (value.isBool()) {
        return value.toBool();
    }
    const QString text = CardAuthoring::normalizedText(value).toLower();
    if (text == QStringLiteral("true") || text == QStringLiteral("yes") || text == QStringLiteral("on") || text == QStringLiteral("1")) {
        return true;
    }
    if (text == QStringLiteral("false") || text == QStringLiteral("no") || text == QStringLiteral("off") || text == QStringLiteral("0")) {
        return false;
    }
    return fallback;
}

int intValue(const QJsonValue& value, int fallback, int minimum = -100000, int maximum = 100000) {
    return qBound(minimum, static_cast<int>(qRound(numberValue(value, fallback))), maximum);
}

QJsonObject ensureRole(QJsonObject role, const QString& roleId) {
    if (role.value(QStringLiteral("id")).toString().trimmed().isEmpty()) {
        role.insert(QStringLiteral("id"), roleId);
    }
    role.insert(QStringLiteral("role_id"), roleId);
    if (role.value(QStringLiteral("role_name")).toString().trimmed().isEmpty()) {
        role.insert(QStringLiteral("role_name"), roleId);
    }
    if (!role.value(QStringLiteral("aliases")).isArray()) {
        role.insert(QStringLiteral("aliases"), QJsonArray{ roleId });
    }
    if (!role.value(QStringLiteral("enabled")).isBool()) {
        role.insert(QStringLiteral("enabled"), true);
    }
    if (!role.value(QStringLiteral("variables")).isArray()) {
        role.insert(QStringLiteral("variables"), QJsonArray{});
    }
    if (!role.value(QStringLiteral("stages")).isArray()) {
        role.insert(QStringLiteral("stages"), QJsonArray{});
    }
    if (!role.value(QStringLiteral("snapshotFields")).isArray()) {
        role.insert(QStringLiteral("snapshotFields"), QJsonArray{});
    }
    if (role.value(QStringLiteral("use_default_variables")).isUndefined()) {
        role.insert(QStringLiteral("use_default_variables"), false);
    }
    QJsonObject settings = role.value(QStringLiteral("settings")).toObject();
    if (!settings.value(QStringLiteral("allow_regression")).isBool()) {
        settings.insert(QStringLiteral("allow_regression"), false);
    }
    if (!settings.value(QStringLiteral("confirm_turns")).isDouble()) {
        settings.insert(QStringLiteral("confirm_turns"), 1);
    }
    if (!settings.value(QStringLiteral("cooldown_turns")).isDouble()) {
        settings.insert(QStringLiteral("cooldown_turns"), 0);
    }
    role.insert(QStringLiteral("settings"), settings);
    if (role.value(QStringLiteral("initial_stage")).toString().trimmed().isEmpty()) {
        role.insert(QStringLiteral("initial_stage"), QStringLiteral("stage_a"));
    }
    if (role.value(QStringLiteral("source")).toString().trimmed().isEmpty()) {
        role.insert(QStringLiteral("source"), QStringLiteral("card_authoring"));
    }
    if (role.value(QStringLiteral("display_policy")).toString().trimmed().isEmpty()) {
        role.insert(QStringLiteral("display_policy"), QStringLiteral("show"));
    }
    if (role.value(QStringLiteral("mode")).toString().trimmed().isEmpty()) {
        role.insert(QStringLiteral("mode"), QStringLiteral("default"));
    }
    if (role.value(QStringLiteral("stateJournalMode")).toString().trimmed().isEmpty()) {
        role.insert(QStringLiteral("stateJournalMode"), role.value(QStringLiteral("mode")).toString(QStringLiteral("default")));
    }
    return role;
}

QJsonObject databaseVariableToState(const QJsonObject& variable, int index) {
    const QString key = normalizeFaKey(
        CardAuthoring::normalizedText(variable.value(QStringLiteral("key"))).isEmpty()
            ? CardAuthoring::normalizedText(variable.value(QStringLiteral("id")))
            : CardAuthoring::normalizedText(variable.value(QStringLiteral("key"))),
        QStringLiteral("var_%1").arg(index));
    QStringList instructionParts;
    for (const QString& field : {
            QStringLiteral("description"),
            QStringLiteral("write_policy"),
            QStringLiteral("notes"),
        }) {
        const QString part = CardAuthoring::normalizedText(variable.value(field));
        if (!part.isEmpty()) {
            instructionParts.append(part);
        }
    }
    double minimum = numberValue(variable.value(QStringLiteral("min_value")), 0.0);
    double maximum = numberValue(variable.value(QStringLiteral("max_value")), 100.0);
    if (maximum <= minimum) {
        maximum = minimum + 100.0;
    }
    double deltaMinimum = numberValue(variable.value(QStringLiteral("delta_min")), -5.0);
    double deltaMaximum = numberValue(variable.value(QStringLiteral("delta_max")), 5.0);
    if (deltaMaximum < deltaMinimum) {
        const double swap = deltaMinimum;
        deltaMinimum = deltaMaximum;
        deltaMaximum = swap;
    }
    QString instruction = CardAuthoring::normalizedText(variable.value(QStringLiteral("instruction")));
    if (instruction.isEmpty()) {
        instruction = instructionParts.join(QLatin1Char('\n'));
    }
    const QJsonValue defaultSource = variable.contains(QStringLiteral("default_value"))
        ? variable.value(QStringLiteral("default_value"))
        : variable.value(QStringLiteral("initial_value"));
    return QJsonObject{
        { QStringLiteral("var_key"), key },
        { QStringLiteral("var_name"), CardAuthoring::normalizedText(variable.value(QStringLiteral("var_name"))).isEmpty()
                ? (CardAuthoring::normalizedText(variable.value(QStringLiteral("label"))).isEmpty()
                        ? key
                        : CardAuthoring::normalizedText(variable.value(QStringLiteral("label"))))
                : CardAuthoring::normalizedText(variable.value(QStringLiteral("var_name"))) },
        { QStringLiteral("enabled"), boolValue(variable.value(QStringLiteral("enabled")), true) },
        { QStringLiteral("default_value"), qBound(minimum, numberValue(defaultSource, minimum), maximum) },
        { QStringLiteral("min_value"), minimum },
        { QStringLiteral("max_value"), maximum },
        { QStringLiteral("delta_min"), deltaMinimum },
        { QStringLiteral("delta_max"), deltaMaximum },
        { QStringLiteral("display"), boolValue(variable.value(QStringLiteral("display")), true) },
        { QStringLiteral("stage_relevant"), boolValue(variable.value(QStringLiteral("stage_relevant")), true) },
        { QStringLiteral("instruction"), instruction },
    };
}

QJsonArray parseDatabaseStageConditions(const QString& conditionText, const QSet<QString>& variableKeys, bool* parsed) {
    QJsonArray conditions;
    if (parsed) {
        *parsed = true;
    }

    const QString text = conditionText.trimmed();
    if (text.isEmpty()) {
        return conditions;
    }

    bool parsedAny = false;
    const QStringList parts = text.split(
        QRegularExpression(QStringLiteral("(?:\\n|；|;|，|,|、|\\band\\b|&&)+"), QRegularExpression::CaseInsensitiveOption),
        Qt::SkipEmptyParts);
    const QRegularExpression conditionPattern(QStringLiteral("([A-Za-z_][A-Za-z0-9_\\-]*)\\s*(>=|<=|==|!=|=|>|<)\\s*(-?\\d+(?:\\.\\d+)?)"));
    for (const QString& part : parts) {
        const QRegularExpressionMatch match = conditionPattern.match(part);
        if (!match.hasMatch()) {
            continue;
        }
        const QString varKey = normalizeFaKey(match.captured(1), QString());
        if (!variableKeys.isEmpty() && !variableKeys.contains(varKey)) {
            continue;
        }
        QString op = match.captured(2);
        if (op == QStringLiteral("==")) {
            op = QStringLiteral("=");
        }
        conditions.append(QJsonObject{
            { QStringLiteral("var"), varKey },
            { QStringLiteral("op"), op },
            { QStringLiteral("value"), match.captured(3).toDouble() },
        });
        parsedAny = true;
    }
    if (parsed) {
        *parsed = parsedAny;
    }
    return conditions;
}

QJsonObject databaseStageToState(const QJsonObject& stage, int index, const QSet<QString>& variableKeys) {
    const QString roleId = normalizeFaKey(CardAuthoring::normalizedText(stage.value(QStringLiteral("role_id"))), QString());
    const QString stageKey = normalizeFaKey(
        CardAuthoring::normalizedText(stage.value(QStringLiteral("stage_key"))).isEmpty()
            ? CardAuthoring::normalizedText(stage.value(QStringLiteral("id")))
            : CardAuthoring::normalizedText(stage.value(QStringLiteral("stage_key"))),
        QStringLiteral("stage_%1").arg(index));
    const QString configuredActiveTag = CardAuthoring::normalizedText(stage.value(QStringLiteral("activation_tag"))).isEmpty()
        ? CardAuthoring::normalizedText(stage.value(QStringLiteral("active_tag")))
        : CardAuthoring::normalizedText(stage.value(QStringLiteral("activation_tag")));
    const QString activeTag = configuredActiveTag.isEmpty()
        ? (roleId.isEmpty() ? QString() : QStringLiteral("database.stage.%1.%2").arg(roleId, stageKey))
        : configuredActiveTag;
    bool parsed = true;
    const QString conditionText = CardAuthoring::normalizedText(stage.value(QStringLiteral("condition")));
    QJsonArray conditions = stage.value(QStringLiteral("conditions")).toArray();
    if (conditions.isEmpty() && !conditionText.isEmpty()) {
        conditions = parseDatabaseStageConditions(conditionText, variableKeys, &parsed);
    }

    QJsonObject stateStage{
        { QStringLiteral("stage_key"), stageKey },
        { QStringLiteral("stage_name"), CardAuthoring::normalizedText(stage.value(QStringLiteral("stage_name"))).isEmpty()
                ? (CardAuthoring::normalizedText(stage.value(QStringLiteral("title"))).isEmpty()
                        ? stageKey
                        : CardAuthoring::normalizedText(stage.value(QStringLiteral("title"))))
                : CardAuthoring::normalizedText(stage.value(QStringLiteral("stage_name"))) },
        { QStringLiteral("enabled"), boolValue(stage.value(QStringLiteral("enabled")), true) },
        { QStringLiteral("priority"), intValue(stage.value(QStringLiteral("priority")), index * 10) },
        { QStringLiteral("condition_mode"), CardAuthoring::normalizedText(stage.value(QStringLiteral("condition_mode"))).toLower() == QStringLiteral("any")
                ? QStringLiteral("any")
                : QStringLiteral("all") },
        { QStringLiteral("conditions"), conditions },
        { QStringLiteral("condition_text"), conditionText },
        { QStringLiteral("allow_regression"), boolValue(stage.value(QStringLiteral("allow_regression")), false) },
        { QStringLiteral("confirm_turns"), intValue(stage.value(QStringLiteral("confirm_turns")), 1, 1, 10000) },
        { QStringLiteral("cooldown_turns"), intValue(stage.value(QStringLiteral("cooldown_turns")), 0, 0, 10000) },
        { QStringLiteral("activation_tag"), activeTag },
        { QStringLiteral("emits_tags"), stage.value(QStringLiteral("emits_tags")).toArray() },
    };
    if (!parsed && !conditionText.isEmpty()) {
        stateStage.insert(QStringLiteral("condition_parse_status"), QStringLiteral("unparsed"));
    }
    const QString description = CardAuthoring::normalizedText(stage.value(QStringLiteral("description")));
    if (!description.isEmpty()) {
        stateStage.insert(QStringLiteral("description"), description);
    }
    const QString notes = CardAuthoring::normalizedText(stage.value(QStringLiteral("notes")));
    if (!notes.isEmpty()) {
        stateStage.insert(QStringLiteral("notes"), notes);
    }
    return stateStage;
}

QJsonObject databaseSnapshotFieldToState(const QJsonObject& field, int index) {
    const QString key = normalizeFaKey(
        CardAuthoring::normalizedText(field.value(QStringLiteral("key"))).isEmpty()
            ? CardAuthoring::normalizedText(field.value(QStringLiteral("id")))
            : CardAuthoring::normalizedText(field.value(QStringLiteral("key"))),
        QStringLiteral("snapshot_%1").arg(index));
    const QString label = CardAuthoring::normalizedText(field.value(QStringLiteral("label"))).isEmpty()
        ? key
        : CardAuthoring::normalizedText(field.value(QStringLiteral("label")));
    QString instruction = CardAuthoring::normalizedText(field.value(QStringLiteral("instruction")));
    const QString notes = CardAuthoring::normalizedText(field.value(QStringLiteral("notes")));
    if (!notes.isEmpty()) {
        instruction = instruction.isEmpty() ? notes : QStringLiteral("%1\n%2").arg(instruction, notes);
    }
    return QJsonObject{
        { QStringLiteral("key"), key },
        { QStringLiteral("label"), label },
        { QStringLiteral("enabled"), boolValue(field.value(QStringLiteral("enabled")), true) },
        { QStringLiteral("display"), boolValue(field.value(QStringLiteral("display")), true) },
        { QStringLiteral("instruction"), instruction.isEmpty() ? QStringLiteral("根据本轮上下文生成该状态快照字段。") : instruction },
    };
}

QJsonObject updateRoleStateMode(QJsonObject role) {
    const bool hasVariables = !role.value(QStringLiteral("variables")).toArray().isEmpty();
    const bool hasStages = !role.value(QStringLiteral("stages")).toArray().isEmpty();
    const bool hasSnapshot = !role.value(QStringLiteral("snapshotFields")).toArray().isEmpty();
    QString mode = role.value(QStringLiteral("mode")).toString(
        role.value(QStringLiteral("stateJournalMode")).toString()).trimmed().toLower();
    if (mode == QStringLiteral("disabled") || role.value(QStringLiteral("enabled")).toBool(true) == false) {
        mode = QStringLiteral("disabled");
    } else if (mode == QStringLiteral("snapshot_only")) {
        mode = QStringLiteral("snapshot_only");
    } else if (mode == QStringLiteral("full") || mode == QStringLiteral("variables")
        || mode == QStringLiteral("stages")) {
    } else if (hasVariables && hasStages) {
        mode = QStringLiteral("full");
    } else if (hasVariables) {
        mode = QStringLiteral("variables");
    } else if (hasStages) {
        mode = QStringLiteral("stages");
    } else if (hasSnapshot) {
        mode = QStringLiteral("snapshot_only");
    } else {
        mode = role.value(QStringLiteral("mode")).toString(role.value(QStringLiteral("stateJournalMode")).toString(QStringLiteral("default")));
    }
    role.insert(QStringLiteral("mode"), mode);
    role.insert(QStringLiteral("stateJournalMode"), mode);
    if (mode != QStringLiteral("default")) {
        role.insert(QStringLiteral("has_state_journal_config"), true);
        if (role.value(QStringLiteral("display_policy")).toString().trimmed().isEmpty()) {
            role.insert(QStringLiteral("display_policy"), QStringLiteral("show"));
        }
    }
    return role;
}
}

QJsonObject CardAuthoringCompiler::compileRoleCard(const QJsonObject& project) const {
    const QJsonObject normalized = CardAuthoring::normalizeProject(project);
    const QJsonObject persona = normalized.value(QStringLiteral("persona_card")).toObject();

    QJsonObject raw;
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
        raw.insert(field, persona.value(field));
    }
    raw.insert(QStringLiteral("tags"), persona.value(QStringLiteral("tags")).toArray());
    if (persona.contains(QStringLiteral("creativeWorkshop"))) {
        raw.insert(QStringLiteral("creativeWorkshop"), persona.value(QStringLiteral("creativeWorkshop")).toObject());
    }
    raw.insert(QStringLiteral("personas"), persona.value(QStringLiteral("personas")).toObject());
    raw.insert(QStringLiteral("stateJournal"), databaseToStateJournal(normalized.value(QStringLiteral("database")).toObject()));

    QJsonObject card;
    card.insert(QStringLiteral("raw"), raw);
    card.insert(QStringLiteral("source_name"), normalized.value(QStringLiteral("title")).toString());
    return card;
}

QStringList CardAuthoringCompiler::validateProject(const QJsonObject& project) const {
    const QJsonObject normalized = CardAuthoring::normalizeProject(project);
    QStringList warnings;
    const QJsonObject persona = normalized.value(QStringLiteral("persona_card")).toObject();
    if (persona.value(QStringLiteral("name")).toString().trimmed().isEmpty()) {
        warnings.append(QStringLiteral("persona_card.name is empty"));
    }
    const QJsonObject database = normalized.value(QStringLiteral("database")).toObject();
    if (database.value(QStringLiteral("variables")).toArray().isEmpty()
        && database.value(QStringLiteral("stages")).toArray().isEmpty()
        && database.value(QStringLiteral("snapshotFields")).toArray().isEmpty()
        && database.value(QStringLiteral("tags")).toArray().isEmpty()
        && database.value(QStringLiteral("notes")).toString().trimmed().isEmpty()) {
        warnings.append(QStringLiteral("database draft is empty"));
    }
    return warnings;
}

QJsonObject CardAuthoringCompiler::databaseToStateJournal(const QJsonObject& database) const {
    const QJsonObject normalized = CardAuthoring::normalizeDatabase(database);

    QJsonObject stateJournal;
    stateJournal.insert(QStringLiteral("enabled"), normalized.value(QStringLiteral("enabled")).toBool(true));
    stateJournal.insert(QStringLiteral("version"), qMax(1, normalized.value(QStringLiteral("version")).toInt(1)));
    stateJournal.insert(QStringLiteral("role_source_mode"), normalized.value(QStringLiteral("role_source_mode")).toString(QStringLiteral("auto")));

    QJsonArray roles;
    QJsonObject roleById;
    const QJsonArray roleDrafts = normalized.value(QStringLiteral("roles")).toArray();
    for (const QJsonValue& roleValue : roleDrafts) {
        QJsonObject role = roleValue.toObject();
        const QString roleId = normalizeFaKey(
            CardAuthoring::normalizedText(role.value(QStringLiteral("role_id"))).isEmpty()
                ? CardAuthoring::normalizedText(role.value(QStringLiteral("id")))
                : CardAuthoring::normalizedText(role.value(QStringLiteral("role_id"))),
            QStringLiteral("role"));
        role.insert(QStringLiteral("variables"), QJsonArray{});
        role.insert(QStringLiteral("stages"), QJsonArray{});
        role.insert(QStringLiteral("snapshotFields"), QJsonArray{});
        roleById.insert(roleId, ensureRole(role, roleId));
    }

    const QJsonArray variables = normalized.value(QStringLiteral("variables")).toArray();
    for (int i = 0; i < variables.size(); ++i) {
        const QJsonValue value = variables.at(i);
        const QJsonObject variable = value.toObject();
        const QString roleId = normalizeFaKey(
            variable.value(QStringLiteral("role_id")).toString(
                variable.value(QStringLiteral("scope")).toString(QStringLiteral("role"))),
            QStringLiteral("role"));
        QJsonObject role = ensureRole(roleById.value(roleId).toObject(), roleId);
        QJsonArray roleVariables = role.value(QStringLiteral("variables")).toArray();
        roleVariables.append(databaseVariableToState(variable, i + 1));
        role.insert(QStringLiteral("variables"), roleVariables);
        roleById.insert(roleId, role);
    }

    const QJsonArray stages = normalized.value(QStringLiteral("stages")).toArray();
    for (int i = 0; i < stages.size(); ++i) {
        const QJsonValue value = stages.at(i);
        const QJsonObject stage = value.toObject();
        const QString roleId = normalizeFaKey(stage.value(QStringLiteral("role_id")).toString(QStringLiteral("role")), QStringLiteral("role"));
        QJsonObject role = ensureRole(roleById.value(roleId).toObject(), roleId);
        QJsonArray roleStages = role.value(QStringLiteral("stages")).toArray();
        QSet<QString> variableKeys;
        const QJsonArray roleVariables = role.value(QStringLiteral("variables")).toArray();
        for (const QJsonValue& variableValue : roleVariables) {
            const QString key = variableValue.toObject().value(QStringLiteral("var_key")).toString();
            if (!key.isEmpty()) {
                variableKeys.insert(key);
            }
        }
        const QJsonObject stateStage = databaseStageToState(stage, i + 1, variableKeys);
        roleStages.append(stateStage);
        role.insert(QStringLiteral("stages"), roleStages);
        if (role.value(QStringLiteral("initial_stage")).toString().trimmed().isEmpty()
            || role.value(QStringLiteral("initial_stage")).toString() == QStringLiteral("stage_a")) {
            role.insert(QStringLiteral("initial_stage"), stateStage.value(QStringLiteral("stage_key")).toString());
        }
        roleById.insert(roleId, role);
    }

    const QJsonArray snapshotFields = normalized.value(QStringLiteral("snapshotFields")).toArray();
    for (int i = 0; i < snapshotFields.size(); ++i) {
        const QJsonObject field = snapshotFields.at(i).toObject();
        const QString roleId = normalizeFaKey(field.value(QStringLiteral("role_id")).toString(QStringLiteral("role")), QStringLiteral("role"));
        QJsonObject role = ensureRole(roleById.value(roleId).toObject(), roleId);
        QJsonArray roleSnapshotFields = role.value(QStringLiteral("snapshotFields")).toArray();
        roleSnapshotFields.append(databaseSnapshotFieldToState(field, i + 1));
        role.insert(QStringLiteral("snapshotFields"), roleSnapshotFields);
        roleById.insert(roleId, role);
    }

    const QStringList roleIds = roleById.keys();
    for (const QString& roleId : roleIds) {
        roles.append(updateRoleStateMode(roleById.value(roleId).toObject()));
    }
    stateJournal.insert(QStringLiteral("roles"), roles);
    stateJournal.insert(QStringLiteral("databaseDraft"), normalized);
    return stateJournal;
}
