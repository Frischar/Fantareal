#include "database/databaserules.h"

#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonObject>

#include <iostream>

namespace {
bool fail(const QString& message) {
    std::cerr << message.toStdString() << '\n';
    return false;
}

QJsonObject currentStage(const QJsonObject& decision) {
    return {
        { QStringLiteral("stageKey"), decision.value(QStringLiteral("stageKey")) },
        { QStringLiteral("state"), decision.value(QStringLiteral("state")) },
    };
}
}

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);

    const QJsonObject initialized = DatabaseRules::configureStoryTime(
        DatabaseRules::defaultStoryTimeState(QStringLiteral("rules-card")),
        QJsonObject{
            { QStringLiteral("action"), QStringLiteral("initialize") },
            { QStringLiteral("baseTime"), QStringLiteral("2026-04-02 17:55:00") },
            { QStringLiteral("advanceMode"), QStringLiteral("explicit") },
        }, QStringLiteral("rules-card"));
    const QJsonObject advanced = DatabaseRules::advanceStoryTime(initialized, QJsonObject{
        { QStringLiteral("deltaSeconds"), 600 },
        { QStringLiteral("confidence"), QStringLiteral("high") },
        { QStringLiteral("deltaText"), QStringLiteral("十分钟后") },
    }, QStringLiteral("turn-1"), QStringLiteral("message-1"), 1);
    const QJsonObject storyContext = DatabaseRules::storyTimeContext(advanced);
    if (advanced.value(QStringLiteral("currentTime")).toString() != QStringLiteral("2026-04-02 18:05:00")
        || advanced.value(QStringLiteral("elapsedSeconds")).toInt() != 600
        || storyContext.value(QStringLiteral("current_hour")).toInt() != 18
        || storyContext.value(QStringLiteral("time_slot")).toString() != QStringLiteral("afternoon")
        || storyContext.value(QStringLiteral("season")).toString() != QStringLiteral("spring")) {
        return fail(QStringLiteral("story clock should derive deterministic time context")) ? 0 : 1;
    }

    QJsonObject manual = initialized;
    manual.insert(QStringLiteral("advanceMode"), QStringLiteral("manual"));
    const QJsonObject manualAdvance = DatabaseRules::advanceStoryTime(manual,
        QJsonObject{ { QStringLiteral("deltaSeconds"), 3600 } },
        QStringLiteral("turn-manual"), QStringLiteral("message-manual"), 2);
    if (manualAdvance.value(QStringLiteral("currentTime")).toString()
            != initialized.value(QStringLiteral("currentTime")).toString()
        || manualAdvance.value(QStringLiteral("lastDeltaSeconds")).toInt(-1) != 0) {
        return fail(QStringLiteral("manual story clock must ignore Worker deltas")) ? 0 : 1;
    }
    QJsonObject custom = initialized;
    custom.insert(QStringLiteral("advanceMode"), QStringLiteral("custom"));
    custom.insert(QStringLiteral("customAdvanceType"), QStringLiteral("range"));
    custom.insert(QStringLiteral("customAdvanceMinSeconds"), 300);
    custom.insert(QStringLiteral("customAdvanceMaxSeconds"), 900);
    const QJsonObject customFirst = DatabaseRules::advanceStoryTime(custom, {},
        QStringLiteral("turn-custom"), QStringLiteral("message-custom"), 3);
    const QJsonObject customSecond = DatabaseRules::advanceStoryTime(custom, {},
        QStringLiteral("turn-custom"), QStringLiteral("message-custom"), 3);
    const int customDelta = customFirst.value(QStringLiteral("lastDeltaSeconds")).toInt();
    if (customDelta < 300 || customDelta > 900
        || customSecond.value(QStringLiteral("lastDeltaSeconds")).toInt() != customDelta) {
        return fail(QStringLiteral("custom story clock range should be bounded and deterministic")) ? 0 : 1;
    }

    const QJsonObject startStage{
        { QStringLiteral("role_id"), QStringLiteral("main") },
        { QStringLiteral("stage_key"), QStringLiteral("start") },
        { QStringLiteral("stage_name"), QStringLiteral("初识") },
        { QStringLiteral("enabled"), true },
        { QStringLiteral("priority"), 10 },
        { QStringLiteral("allow_regression"), true },
        { QStringLiteral("conditions"), QJsonArray{} },
        { QStringLiteral("activation_tag"), QStringLiteral("database.stage.main.start") },
    };
    const QJsonObject trustedStage{
        { QStringLiteral("role_id"), QStringLiteral("main") },
        { QStringLiteral("stage_key"), QStringLiteral("trusted") },
        { QStringLiteral("stage_name"), QStringLiteral("信赖") },
        { QStringLiteral("enabled"), true },
        { QStringLiteral("priority"), 20 },
        { QStringLiteral("confirm_turns"), 2 },
        { QStringLiteral("cooldown_turns"), 2 },
        { QStringLiteral("conditions"), QJsonArray{
              QJsonObject{
                  { QStringLiteral("source"), QStringLiteral("variable") },
                  { QStringLiteral("var"), QStringLiteral("trust") },
                  { QStringLiteral("op"), QStringLiteral(">=") },
                  { QStringLiteral("value"), 50 },
              },
              QJsonObject{
                  { QStringLiteral("source"), QStringLiteral("story_time") },
                  { QStringLiteral("field"), QStringLiteral("current_hour") },
                  { QStringLiteral("op"), QStringLiteral(">=") },
                  { QStringLiteral("value"), 18 },
              },
          } },
        { QStringLiteral("condition_mode"), QStringLiteral("all") },
        { QStringLiteral("activation_tag"), QStringLiteral("database.stage.main.trusted") },
        { QStringLiteral("emits_tags"), QJsonArray{
              QStringLiteral("database.stage.main.trusted"),
              QStringLiteral("database.tag.trusted-lore"),
          } },
    };
    const QJsonObject config{
        { QStringLiteral("roles"), QJsonArray{ QJsonObject{
              { QStringLiteral("role_id"), QStringLiteral("main") },
              { QStringLiteral("role_name"), QStringLiteral("主角色") },
              { QStringLiteral("enabled"), true },
              { QStringLiteral("mode"), QStringLiteral("full") },
              { QStringLiteral("initial_stage"), QStringLiteral("start") },
              { QStringLiteral("stages"), QJsonArray{ startStage, trustedStage } },
          } } },
    };
    QHash<QString, QJsonValue> values;
    values.insert(QStringLiteral("main\x1ftrust"), 60);
    QHash<QString, QJsonObject> current;
    current.insert(QStringLiteral("main"), QJsonObject{
        { QStringLiteral("stageKey"), QStringLiteral("start") },
        { QStringLiteral("state"), QJsonObject{
              { QStringLiteral("active"), true },
              { QStringLiteral("stageName"), QStringLiteral("初识") },
              { QStringLiteral("candidateStageKey"), QString() },
              { QStringLiteral("candidateCount"), 0 },
          } },
    });

    const QList<QJsonObject> firstEvaluation = DatabaseRules::evaluateStages(
        config, values, storyContext, current, 10);
    if (firstEvaluation.size() != 1
        || firstEvaluation.first().value(QStringLiteral("stageKey")).toString() != QStringLiteral("start")
        || firstEvaluation.first().value(QStringLiteral("state")).toObject()
                .value(QStringLiteral("candidateCount")).toInt() != 1) {
        return fail(QStringLiteral("stage confirmation should retain the current stage on the first matching turn")) ? 0 : 1;
    }
    current.insert(QStringLiteral("main"), currentStage(firstEvaluation.first()));
    const QList<QJsonObject> secondEvaluation = DatabaseRules::evaluateStages(
        config, values, storyContext, current, 11);
    if (secondEvaluation.first().value(QStringLiteral("stageKey")).toString() != QStringLiteral("trusted")
        || !secondEvaluation.first().value(QStringLiteral("changed")).toBool()
        || secondEvaluation.first().value(QStringLiteral("tags")).toArray().size() != 2) {
        return fail(QStringLiteral("stage confirmation should commit the deterministic stage and emitted tags")) ? 0 : 1;
    }

    values.insert(QStringLiteral("main\x1ftrust"), 0);
    current.insert(QStringLiteral("main"), currentStage(secondEvaluation.first()));
    const QList<QJsonObject> cooldownEvaluation = DatabaseRules::evaluateStages(
        config, values, storyContext, current, 12);
    if (cooldownEvaluation.first().value(QStringLiteral("stageKey")).toString() != QStringLiteral("trusted")) {
        return fail(QStringLiteral("stage cooldown should block an otherwise allowed regression")) ? 0 : 1;
    }
    current.insert(QStringLiteral("main"), currentStage(cooldownEvaluation.first()));
    const QList<QJsonObject> regressionEvaluation = DatabaseRules::evaluateStages(
        config, values, storyContext, current, 13);
    if (regressionEvaluation.first().value(QStringLiteral("stageKey")).toString() != QStringLiteral("start")
        || !regressionEvaluation.first().value(QStringLiteral("changed")).toBool()) {
        return fail(QStringLiteral("stage regression should become eligible after cooldown")) ? 0 : 1;
    }

    return 0;
}
