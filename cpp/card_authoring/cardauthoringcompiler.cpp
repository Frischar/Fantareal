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

QJsonObject ensureRole(QJsonObject role, const QString& roleId) {
    role.insert(QStringLiteral("id"), roleId);
    role.insert(QStringLiteral("role_id"), roleId);
    if (role.value(QStringLiteral("role_name")).toString().trimmed().isEmpty()) {
        role.insert(QStringLiteral("role_name"), roleId);
    }
    if (!role.value(QStringLiteral("aliases")).isArray()) {
        role.insert(QStringLiteral("aliases"), QJsonArray{ roleId });
    }
    role.insert(QStringLiteral("enabled"), true);
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
    if (!role.value(QStringLiteral("settings")).isObject()) {
        role.insert(QStringLiteral("settings"), QJsonObject{
            { QStringLiteral("allow_regression"), false },
            { QStringLiteral("confirm_turns"), 1 },
            { QStringLiteral("cooldown_turns"), 0 },
        });
    }
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
    return QJsonObject{
        { QStringLiteral("var_key"), key },
        { QStringLiteral("var_name"), CardAuthoring::normalizedText(variable.value(QStringLiteral("label"))).isEmpty()
                ? key
                : CardAuthoring::normalizedText(variable.value(QStringLiteral("label"))) },
        { QStringLiteral("enabled"), true },
        { QStringLiteral("default_value"), numberValue(variable.value(QStringLiteral("initial_value")), 0.0) },
        { QStringLiteral("min_value"), 0 },
        { QStringLiteral("max_value"), 100 },
        { QStringLiteral("delta_min"), -5 },
        { QStringLiteral("delta_max"), 5 },
        { QStringLiteral("display"), true },
        { QStringLiteral("stage_relevant"), true },
        { QStringLiteral("instruction"), instructionParts.join(QLatin1Char('\n')) },
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
    const QString activeTag = CardAuthoring::normalizedText(stage.value(QStringLiteral("active_tag"))).isEmpty()
        ? (roleId.isEmpty() ? QString() : QStringLiteral("database.stage.%1.%2").arg(roleId, stageKey))
        : CardAuthoring::normalizedText(stage.value(QStringLiteral("active_tag")));
    bool parsed = true;
    const QString conditionText = CardAuthoring::normalizedText(stage.value(QStringLiteral("condition")));
    const QJsonArray conditions = parseDatabaseStageConditions(conditionText, variableKeys, &parsed);

    QJsonObject stateStage{
        { QStringLiteral("stage_key"), stageKey },
        { QStringLiteral("stage_name"), CardAuthoring::normalizedText(stage.value(QStringLiteral("title"))).isEmpty()
                ? stageKey
                : CardAuthoring::normalizedText(stage.value(QStringLiteral("title"))) },
        { QStringLiteral("enabled"), true },
        { QStringLiteral("priority"), index * 10 },
        { QStringLiteral("condition_mode"), QStringLiteral("all") },
        { QStringLiteral("conditions"), conditions },
        { QStringLiteral("condition_text"), conditionText },
        { QStringLiteral("allow_regression"), false },
        { QStringLiteral("confirm_turns"), 1 },
        { QStringLiteral("cooldown_turns"), 0 },
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

QJsonObject updateRoleStateMode(QJsonObject role) {
    const bool hasVariables = !role.value(QStringLiteral("variables")).toArray().isEmpty();
    const bool hasStages = !role.value(QStringLiteral("stages")).toArray().isEmpty();
    const bool hasSnapshot = !role.value(QStringLiteral("snapshotFields")).toArray().isEmpty();
    QString mode;
    if (hasVariables && hasStages) {
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
    stateJournal.insert(QStringLiteral("version"), 1);
    stateJournal.insert(QStringLiteral("role_source_mode"), QStringLiteral("auto"));

    QJsonArray roles;
    QJsonObject roleById;

    const QJsonArray variables = normalized.value(QStringLiteral("variables")).toArray();
    for (int i = 0; i < variables.size(); ++i) {
        const QJsonValue value = variables.at(i);
        const QJsonObject variable = value.toObject();
        const QString roleId = normalizeFaKey(variable.value(QStringLiteral("scope")).toString(QStringLiteral("role")), QStringLiteral("role"));
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

    const QStringList roleIds = roleById.keys();
    for (const QString& roleId : roleIds) {
        roles.append(updateRoleStateMode(roleById.value(roleId).toObject()));
    }
    stateJournal.insert(QStringLiteral("roles"), roles);
    stateJournal.insert(QStringLiteral("databaseDraft"), normalized);
    return stateJournal;
}
