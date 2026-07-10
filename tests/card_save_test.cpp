#include "fantarealbridge.h"
#include "card_authoring/cardauthoringservice.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QHash>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTemporaryDir>
#include <QVariantList>
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

QJsonObject findByKey(const QJsonArray& items, const QString& key, const QString& value) {
    for (const QJsonValue& item : items) {
        const QJsonObject object = item.toObject();
        if (object.value(key).toString() == value) {
            return object;
        }
    }
    return {};
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

    QJsonObject personaOne;
    personaOne.insert(QStringLiteral("name"), QStringLiteral("Persona One"));
    personaOne.insert(QStringLiteral("role_id"), QStringLiteral("role-one"));
    personaOne.insert(QStringLiteral("aliases"), QJsonArray{ QStringLiteral("One"), QStringLiteral("First") });
    personaOne.insert(QStringLiteral("description"), QStringLiteral("persona one description"));
    personaOne.insert(QStringLiteral("personality"), QStringLiteral("persona one personality"));
    personaOne.insert(QStringLiteral("scenario"), QStringLiteral("persona one scenario"));
    personaOne.insert(QStringLiteral("creator_notes"), QStringLiteral("persona one notes"));
    personaOne.insert(QStringLiteral("tags"), QJsonArray{ QStringLiteral("lead") });
    personaOne.insert(QStringLiteral("unknown_persona_field"), QStringLiteral("persona-stays"));
    QJsonObject personas;
    personas.insert(QStringLiteral("1"), personaOne);
    personas.insert(QStringLiteral("2"), QJsonObject{ { QStringLiteral("name"), QStringLiteral("Persona Two") } });

    QJsonObject stateJournal;
    stateJournal.insert(QStringLiteral("version"), 1);
    stateJournal.insert(QStringLiteral("enabled"), false);
    stateJournal.insert(QStringLiteral("role_source_mode"), QStringLiteral("auto"));
    stateJournal.insert(QStringLiteral("roles"), QJsonArray{
        QJsonObject{
            { QStringLiteral("id"), QStringLiteral("legacy-role-id") },
            { QStringLiteral("role_id"), QStringLiteral("role-one") },
            { QStringLiteral("role_name"), QStringLiteral("Persona One") },
            { QStringLiteral("aliases"), QJsonArray{ QStringLiteral("One") } },
            { QStringLiteral("enabled"), true },
            { QStringLiteral("mode"), QStringLiteral("full") },
            { QStringLiteral("stateJournalMode"), QStringLiteral("full") },
            { QStringLiteral("use_default_variables"), false },
            { QStringLiteral("initial_stage"), QStringLiteral("stage_a") },
            { QStringLiteral("variables"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("var_key"), QStringLiteral("trust") },
                    { QStringLiteral("var_name"), QStringLiteral("Trust") },
                    { QStringLiteral("enabled"), true },
                    { QStringLiteral("default_value"), 10 },
                    { QStringLiteral("min_value"), -20 },
                    { QStringLiteral("max_value"), 80 },
                    { QStringLiteral("delta_min"), -3 },
                    { QStringLiteral("delta_max"), 4 },
                    { QStringLiteral("display"), false },
                    { QStringLiteral("stage_relevant"), true },
                    { QStringLiteral("instruction"), QStringLiteral("old trust instruction") },
                    { QStringLiteral("unknown_variable_field"), QStringLiteral("variable-stays") },
                },
            } },
            { QStringLiteral("stages"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("stage_key"), QStringLiteral("stage_a") },
                    { QStringLiteral("stage_name"), QStringLiteral("Opening") },
                    { QStringLiteral("enabled"), true },
                    { QStringLiteral("priority"), 10 },
                    { QStringLiteral("condition_mode"), QStringLiteral("all") },
                    { QStringLiteral("conditions"), QJsonArray{
                        QJsonObject{
                            { QStringLiteral("source"), QStringLiteral("variable") },
                            { QStringLiteral("var"), QStringLiteral("trust") },
                            { QStringLiteral("op"), QStringLiteral(">=") },
                            { QStringLiteral("value"), 10 },
                            { QStringLiteral("unknown_condition_field"), QStringLiteral("condition-stays") },
                        },
                    } },
                    { QStringLiteral("allow_regression"), false },
                    { QStringLiteral("confirm_turns"), 1 },
                    { QStringLiteral("cooldown_turns"), 2 },
                    { QStringLiteral("activation_tag"), QStringLiteral("state_journal.stage.role-one.stage_a") },
                    { QStringLiteral("unknown_stage_field"), QStringLiteral("stage-stays") },
                },
            } },
            { QStringLiteral("snapshotFields"), QJsonArray{
                QJsonObject{
                    { QStringLiteral("key"), QStringLiteral("mood") },
                    { QStringLiteral("label"), QStringLiteral("Mood") },
                    { QStringLiteral("enabled"), true },
                    { QStringLiteral("display"), true },
                    { QStringLiteral("instruction"), QStringLiteral("old mood instruction") },
                    { QStringLiteral("unknown_snapshot_field"), QStringLiteral("snapshot-stays") },
                },
            } },
            { QStringLiteral("settings"), QJsonObject{
                { QStringLiteral("allow_regression"), false },
                { QStringLiteral("confirm_turns"), 1 },
                { QStringLiteral("cooldown_turns"), 2 },
                { QStringLiteral("unknown_settings_field"), QStringLiteral("settings-stays") },
            } },
            { QStringLiteral("unknown_role_field"), QStringLiteral("role-stays") },
        },
        QJsonObject{
            { QStringLiteral("role_id"), QStringLiteral("role-two") },
            { QStringLiteral("role_name"), QStringLiteral("Persona Two") },
            { QStringLiteral("variables"), QJsonArray{} },
            { QStringLiteral("stages"), QJsonArray{} },
            { QStringLiteral("snapshotFields"), QJsonArray{} },
        },
    });
    stateJournal.insert(QStringLiteral("databaseDraft"), QJsonObject{
        { QStringLiteral("enabled"), false },
        { QStringLiteral("variables"), QJsonArray{} },
        { QStringLiteral("stages"), QJsonArray{} },
        { QStringLiteral("snapshotFields"), QJsonArray{} },
        { QStringLiteral("tags"), QJsonArray{
            QJsonObject{
                { QStringLiteral("id"), QStringLiteral("existing-tag") },
                { QStringLiteral("tag"), QStringLiteral("database.existing") },
            },
        } },
        { QStringLiteral("unknown_database_draft_field"), QStringLiteral("draft-stays") },
    });
    stateJournal.insert(QStringLiteral("unknown_state_field"), QStringLiteral("state-stays"));

    QJsonObject opening;
    opening.insert(QStringLiteral("enabled"), false);
    opening.insert(QStringLiteral("title"), QStringLiteral("Old Opening"));
    opening.insert(QStringLiteral("volume"), 0.42);

    QJsonObject workshop;
    workshop.insert(QStringLiteral("version"), 2);
    workshop.insert(QStringLiteral("enabled"), true);
    workshop.insert(QStringLiteral("opening"), opening);
    workshop.insert(QStringLiteral("dynamicScenes"), QJsonArray{ QJsonObject{ { QStringLiteral("id"), QStringLiteral("scene-1") } } });
    workshop.insert(QStringLiteral("ambience"), QJsonObject{ { QStringLiteral("musicUrl"), QStringLiteral("old.mp3") } });
    workshop.insert(QStringLiteral("unknown_workshop_field"), QStringLiteral("workshop-stays"));

    QJsonObject raw;
    raw.insert(QStringLiteral("name"), QStringLiteral("Old Name"));
    raw.insert(QStringLiteral("description"), QStringLiteral("old description"));
    raw.insert(QStringLiteral("personality"), QStringLiteral("old personality"));
    raw.insert(QStringLiteral("scenario"), QStringLiteral("old scenario"));
    raw.insert(QStringLiteral("first_mes"), QStringLiteral("old first"));
    raw.insert(QStringLiteral("mes_example"), QStringLiteral("old example"));
    raw.insert(QStringLiteral("creator_notes"), QStringLiteral("old notes"));
    raw.insert(QStringLiteral("creator_comment"), QStringLiteral("old comment"));
    raw.insert(QStringLiteral("tags"), QJsonArray{ QStringLiteral("alpha"), QStringLiteral("beta") });
    raw.insert(QStringLiteral("stateJournal"), stateJournal);
    raw.insert(QStringLiteral("creativeWorkshop"), workshop);
    raw.insert(QStringLiteral("personas"), personas);
    raw.insert(QStringLiteral("unknown_raw_field"), QStringLiteral("raw-stays"));

    QJsonObject card;
    card.insert(QStringLiteral("source_name"), QStringLiteral("source-card.json"));
    card.insert(QStringLiteral("card_uid"), QStringLiteral("card-123"));
    card.insert(QStringLiteral("raw"), raw);
    card.insert(QStringLiteral("unknown_root_field"), QStringLiteral("root-stays"));

    const QString cardPath = root.absoluteFilePath(QStringLiteral("data/current_role_card.json"));
    if (!writeJson(cardPath, QJsonDocument(card))) {
        return fail(QStringLiteral("failed to write fixture current_role_card.json")) ? 0 : 1;
    }

    QJsonObject activationRaw;
    activationRaw.insert(QStringLiteral("name"), QStringLiteral("Activation Hero"));
    activationRaw.insert(QStringLiteral("description"), QStringLiteral("activation description"));
    activationRaw.insert(QStringLiteral("personality"), QStringLiteral("activation personality"));
    activationRaw.insert(QStringLiteral("scenario"), QStringLiteral("activation scenario"));
    activationRaw.insert(QStringLiteral("first_mes"), QStringLiteral("activation first"));
    activationRaw.insert(QStringLiteral("tags"), QJsonArray{ QStringLiteral("library"), QStringLiteral("hero") });
    activationRaw.insert(QStringLiteral("unknown_activation_raw"), QStringLiteral("activation-raw-stays"));
    const QString activationCardPath = root.absoluteFilePath(QStringLiteral("cards/activation_card.json"));
    if (!writeJson(activationCardPath, QJsonDocument(activationRaw))) {
        return fail(QStringLiteral("failed to write activation role card fixture")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;
    const QVariantMap initialDraft = bridge.cardDraft();
    const QVariantList initialPersonas = initialDraft.value(QStringLiteral("personas")).toList();
    const QVariantMap initialDatabase = initialDraft.value(QStringLiteral("databaseConfig")).toMap();
    const QVariantMap initialRole = initialDatabase.value(QStringLiteral("roles")).toList().value(0).toMap();
    const QVariantMap initialVariable = initialRole.value(QStringLiteral("variables")).toList().value(0).toMap();
    if (initialDraft.value(QStringLiteral("name")).toString() != QStringLiteral("Old Name")
        || initialDraft.value(QStringLiteral("tagCount")).toInt() != 2
        || initialDraft.value(QStringLiteral("personaCount")).toInt() != 2
        || initialPersonas.size() != 2
        || initialPersonas.value(0).toMap().value(QStringLiteral("role_id")).toString() != QStringLiteral("role-one")
        || initialDatabase.value(QStringLiteral("roles")).toList().size() != 2
        || initialVariable.value(QStringLiteral("min_value")).toDouble() != -20.0) {
        return fail(QStringLiteral("cardDraft should expose controlled personas and databaseConfig")) ? 0 : 1;
    }
    if (initialDraft.contains(QStringLiteral("creativeWorkshop"))
        || initialDraft.contains(QStringLiteral("stateJournal"))
        || initialPersonas.value(0).toMap().contains(QStringLiteral("unknown_persona_field"))
        || initialDatabase.contains(QStringLiteral("unknown_state_field"))
        || initialRole.contains(QStringLiteral("unknown_role_field"))
        || initialVariable.contains(QStringLiteral("unknown_variable_field"))) {
        return fail(QStringLiteral("cardDraft should expose only controlled nested fields")) ? 0 : 1;
    }
    QStringList tagParts = { QStringLiteral("alpha"), QStringLiteral("beta"), QStringLiteral("alpha") };
    for (int i = 1; i <= 30; ++i) {
        tagParts.append(QStringLiteral("tag%1").arg(i));
    }

    QVariantMap draft;
    draft.insert(QStringLiteral("name"), QStringLiteral("New Name"));
    draft.insert(QStringLiteral("description"), QStringLiteral("new description"));
    draft.insert(QStringLiteral("personality"), QStringLiteral("new personality"));
    draft.insert(QStringLiteral("scenario"), QStringLiteral("new scenario"));
    draft.insert(QStringLiteral("first_mes"), QStringLiteral("new first"));
    draft.insert(QStringLiteral("mes_example"), QStringLiteral("new example"));
    draft.insert(QStringLiteral("creator_notes"), QStringLiteral("new notes"));
    draft.insert(QStringLiteral("creator_comment"), QStringLiteral("new comment"));
    draft.insert(QStringLiteral("tagsText"), tagParts.join(QStringLiteral(";\n")));
    draft.insert(QStringLiteral("source_name"), QStringLiteral("injected-source.json"));
    draft.insert(QStringLiteral("raw"), QVariantMap{ { QStringLiteral("unknown_raw_field"), QStringLiteral("overwritten") } });
    draft.insert(QStringLiteral("personas"), QJsonArray{
        QJsonObject{
            { QStringLiteral("key"), QStringLiteral("1") },
            { QStringLiteral("name"), QStringLiteral("Persona One Edited") },
            { QStringLiteral("role_id"), QStringLiteral("role-one") },
            { QStringLiteral("aliases"), QJsonArray{ QStringLiteral("One"), QStringLiteral("Leader") } },
            { QStringLiteral("description"), QStringLiteral("edited persona description") },
            { QStringLiteral("personality"), QStringLiteral("edited persona personality") },
            { QStringLiteral("scenario"), QStringLiteral("edited persona scenario") },
            { QStringLiteral("creator_notes"), QStringLiteral("edited persona notes") },
            { QStringLiteral("tags"), QJsonArray{ QStringLiteral("lead"), QStringLiteral("edited") } },
            { QStringLiteral("unknown_persona_field"), QStringLiteral("should-not-overwrite") },
        },
        QJsonObject{
            { QStringLiteral("key"), QStringLiteral("1") },
            { QStringLiteral("name"), QStringLiteral("Persona Three") },
            { QStringLiteral("role_id"), QStringLiteral("role-three") },
            { QStringLiteral("aliases"), QJsonArray{ QStringLiteral("Three") } },
            { QStringLiteral("description"), QStringLiteral("new persona") },
            { QStringLiteral("personality"), QStringLiteral("new personality") },
            { QStringLiteral("scenario"), QStringLiteral("new scenario") },
            { QStringLiteral("creator_notes"), QStringLiteral("new persona notes") },
            { QStringLiteral("tags"), QJsonArray{ QStringLiteral("new") } },
        },
    }.toVariantList());
    const QJsonObject editedVariable{
        { QStringLiteral("var_key"), QStringLiteral("trust") },
        { QStringLiteral("var_name"), QStringLiteral("Trust Edited") },
        { QStringLiteral("enabled"), false },
        { QStringLiteral("default_value"), 25 },
        { QStringLiteral("min_value"), -50 },
        { QStringLiteral("max_value"), 150 },
        { QStringLiteral("delta_min"), -7 },
        { QStringLiteral("delta_max"), 9 },
        { QStringLiteral("display"), true },
        { QStringLiteral("stage_relevant"), false },
        { QStringLiteral("instruction"), QStringLiteral("edited trust instruction") },
        { QStringLiteral("unknown_variable_field"), QStringLiteral("should-not-overwrite") },
    };
    const QJsonObject editedStage{
        { QStringLiteral("stage_key"), QStringLiteral("stage_a") },
        { QStringLiteral("stage_name"), QStringLiteral("Opening Edited") },
        { QStringLiteral("enabled"), false },
        { QStringLiteral("priority"), 77 },
        { QStringLiteral("condition_mode"), QStringLiteral("any") },
        { QStringLiteral("conditions"), QJsonArray{
            QJsonObject{
                { QStringLiteral("source"), QStringLiteral("variable") },
                { QStringLiteral("var"), QStringLiteral("trust") },
                { QStringLiteral("op"), QStringLiteral(">") },
                { QStringLiteral("value"), 30 },
                { QStringLiteral("unknown_condition_field"), QStringLiteral("should-not-overwrite") },
            },
            QJsonObject{
                { QStringLiteral("source"), QStringLiteral("story_time") },
                { QStringLiteral("field"), QStringLiteral("hour") },
                { QStringLiteral("op"), QStringLiteral(">=") },
                { QStringLiteral("value"), 18 },
            },
        } },
        { QStringLiteral("allow_regression"), true },
        { QStringLiteral("confirm_turns"), 3 },
        { QStringLiteral("cooldown_turns"), 6 },
        { QStringLiteral("activation_tag"), QStringLiteral("state_journal.stage.role-one.stage_a") },
        { QStringLiteral("unknown_stage_field"), QStringLiteral("should-not-overwrite") },
    };
    const QJsonObject editedSnapshot{
        { QStringLiteral("key"), QStringLiteral("mood") },
        { QStringLiteral("label"), QStringLiteral("Mood Edited") },
        { QStringLiteral("enabled"), false },
        { QStringLiteral("display"), false },
        { QStringLiteral("instruction"), QStringLiteral("edited mood instruction") },
    };
    draft.insert(QStringLiteral("databaseConfig"), QJsonObject{
        { QStringLiteral("version"), 2 },
        { QStringLiteral("enabled"), true },
        { QStringLiteral("role_source_mode"), QStringLiteral("personas_only") },
        { QStringLiteral("roles"), QJsonArray{
            QJsonObject{
                { QStringLiteral("role_id"), QStringLiteral("role-one") },
                { QStringLiteral("role_name"), QStringLiteral("Persona One Edited") },
                { QStringLiteral("aliases"), QJsonArray{ QStringLiteral("One"), QStringLiteral("Leader") } },
                { QStringLiteral("enabled"), true },
                { QStringLiteral("mode"), QStringLiteral("variables") },
                { QStringLiteral("stateJournalMode"), QStringLiteral("variables") },
                { QStringLiteral("use_default_variables"), true },
                { QStringLiteral("initial_stage"), QStringLiteral("stage_a") },
                { QStringLiteral("variables"), QJsonArray{ editedVariable } },
                { QStringLiteral("stages"), QJsonArray{ editedStage } },
                { QStringLiteral("snapshotFields"), QJsonArray{ editedSnapshot } },
                { QStringLiteral("settings"), QJsonObject{
                    { QStringLiteral("allow_regression"), true },
                    { QStringLiteral("confirm_turns"), 4 },
                    { QStringLiteral("cooldown_turns"), 8 },
                } },
                { QStringLiteral("unknown_role_field"), QStringLiteral("should-not-overwrite") },
            },
            QJsonObject{
                { QStringLiteral("role_id"), QStringLiteral("role-three") },
                { QStringLiteral("role_name"), QStringLiteral("Persona Three") },
                { QStringLiteral("aliases"), QJsonArray{ QStringLiteral("Three") } },
                { QStringLiteral("enabled"), true },
                { QStringLiteral("mode"), QStringLiteral("snapshot_only") },
                { QStringLiteral("stateJournalMode"), QStringLiteral("snapshot_only") },
                { QStringLiteral("variables"), QJsonArray{} },
                { QStringLiteral("stages"), QJsonArray{} },
                { QStringLiteral("snapshotFields"), QJsonArray{
                    QJsonObject{
                        { QStringLiteral("key"), QStringLiteral("status") },
                        { QStringLiteral("label"), QStringLiteral("Status") },
                        { QStringLiteral("enabled"), true },
                        { QStringLiteral("display"), true },
                        { QStringLiteral("instruction"), QStringLiteral("new role status") },
                    },
                } },
            },
        } },
        { QStringLiteral("unknown_state_field"), QStringLiteral("should-not-overwrite") },
    }.toVariantMap());
    draft.insert(QStringLiteral("creativeWorkshopEnabled"), false);
    draft.insert(QStringLiteral("openingEnabled"), true);

    const QVariantMap result = bridge.saveCardDraft(draft);
    if (!result.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("saveCardDraft failed: %1").arg(result.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }

    const QString backupPath = result.value(QStringLiteral("backupPath")).toString();
    if (backupPath.isEmpty() || !QFileInfo::exists(backupPath)) {
        return fail(QStringLiteral("card backup was not created")) ? 0 : 1;
    }

    const QJsonObject saved = readJsonObject(cardPath);
    const QJsonObject savedRaw = saved.value("raw").toObject();
    if (saved.value("source_name").toString() != QStringLiteral("source-card.json")
        || saved.value("card_uid").toString() != QStringLiteral("card-123")
        || saved.value("unknown_root_field").toString() != QStringLiteral("root-stays")
        || savedRaw.value("unknown_raw_field").toString() != QStringLiteral("raw-stays")) {
        return fail(QStringLiteral("card identity and unknown fields should be preserved")) ? 0 : 1;
    }
    if (savedRaw.value("name").toString() != QStringLiteral("New Name")
        || savedRaw.value("description").toString() != QStringLiteral("new description")
        || savedRaw.value("personality").toString() != QStringLiteral("new personality")
        || savedRaw.value("scenario").toString() != QStringLiteral("new scenario")
        || savedRaw.value("first_mes").toString() != QStringLiteral("new first")
        || savedRaw.value("mes_example").toString() != QStringLiteral("new example")
        || savedRaw.value("creator_notes").toString() != QStringLiteral("new notes")
        || savedRaw.value("creator_comment").toString() != QStringLiteral("new comment")) {
        return fail(QStringLiteral("card safe text fields were not saved")) ? 0 : 1;
    }

    const QJsonArray savedTags = savedRaw.value("tags").toArray();
    if (savedTags.size() != 24
        || savedTags.at(0).toString() != QStringLiteral("alpha")
        || savedTags.at(1).toString() != QStringLiteral("beta")
        || savedTags.at(23).toString() != QStringLiteral("tag22")) {
        return fail(QStringLiteral("card tags should be deduplicated and clamped")) ? 0 : 1;
    }

    const QJsonObject savedStateJournal = savedRaw.value("stateJournal").toObject();
    if (!savedStateJournal.value("enabled").toBool(false)
        || savedStateJournal.value("unknown_state_field").toString() != QStringLiteral("state-stays")
        || savedStateJournal.value("version").toInt() != 2
        || savedStateJournal.value("role_source_mode").toString() != QStringLiteral("personas_only")
        || savedStateJournal.value("roles").toArray().size() != 2
        || !findByKey(savedStateJournal.value("roles").toArray(), QStringLiteral("role_id"), QStringLiteral("role-two")).isEmpty()) {
        return fail(QStringLiteral("databaseConfig should update roles while preserving stateJournal fields")) ? 0 : 1;
    }
    const QJsonObject savedRole = findByKey(savedStateJournal.value("roles").toArray(), QStringLiteral("role_id"), QStringLiteral("role-one"));
    const QJsonObject savedVariable = findByKey(savedRole.value("variables").toArray(), QStringLiteral("var_key"), QStringLiteral("trust"));
    const QJsonObject savedStage = findByKey(savedRole.value("stages").toArray(), QStringLiteral("stage_key"), QStringLiteral("stage_a"));
    const QJsonObject savedCondition = savedStage.value(QStringLiteral("conditions")).toArray().at(0).toObject();
    const QJsonObject savedSnapshot = findByKey(savedRole.value("snapshotFields").toArray(), QStringLiteral("key"), QStringLiteral("mood"));
    if (savedRole.value(QStringLiteral("mode")).toString() != QStringLiteral("variables")
        || savedRole.value(QStringLiteral("stateJournalMode")).toString() != QStringLiteral("variables")
        || savedRole.value(QStringLiteral("unknown_role_field")).toString() != QStringLiteral("role-stays")
        || savedRole.value(QStringLiteral("settings")).toObject().value(QStringLiteral("unknown_settings_field")).toString() != QStringLiteral("settings-stays")
        || savedVariable.value(QStringLiteral("unknown_variable_field")).toString() != QStringLiteral("variable-stays")
        || savedVariable.value(QStringLiteral("default_value")).toDouble() != 25.0
        || savedVariable.value(QStringLiteral("min_value")).toDouble() != -50.0
        || savedVariable.value(QStringLiteral("max_value")).toDouble() != 150.0
        || savedVariable.value(QStringLiteral("delta_min")).toDouble() != -7.0
        || savedVariable.value(QStringLiteral("delta_max")).toDouble() != 9.0
        || savedVariable.value(QStringLiteral("enabled")).toBool(true)
        || !savedVariable.value(QStringLiteral("display")).toBool(false)
        || savedVariable.value(QStringLiteral("stage_relevant")).toBool(true)
        || savedVariable.value(QStringLiteral("instruction")).toString() != QStringLiteral("edited trust instruction")
        || savedStage.value(QStringLiteral("unknown_stage_field")).toString() != QStringLiteral("stage-stays")
        || savedStage.value(QStringLiteral("priority")).toInt() != 77
        || savedStage.value(QStringLiteral("condition_mode")).toString() != QStringLiteral("any")
        || !savedStage.value(QStringLiteral("allow_regression")).toBool()
        || savedStage.value(QStringLiteral("confirm_turns")).toInt() != 3
        || savedStage.value(QStringLiteral("cooldown_turns")).toInt() != 6
        || savedCondition.value(QStringLiteral("unknown_condition_field")).toString() != QStringLiteral("condition-stays")
        || savedSnapshot.value(QStringLiteral("unknown_snapshot_field")).toString() != QStringLiteral("snapshot-stays")
        || savedSnapshot.value(QStringLiteral("display")).toBool(true)) {
        return fail(QStringLiteral("database variable, stage, condition, snapshot and unknown fields should round-trip")) ? 0 : 1;
    }
    const QJsonObject savedDatabaseDraft = savedStateJournal.value(QStringLiteral("databaseDraft")).toObject();
    const QJsonObject draftVariable = findByKey(savedDatabaseDraft.value(QStringLiteral("variables")).toArray(), QStringLiteral("var_key"), QStringLiteral("trust"));
    if (savedDatabaseDraft.value(QStringLiteral("unknown_database_draft_field")).toString() != QStringLiteral("draft-stays")
        || savedDatabaseDraft.value(QStringLiteral("tags")).toArray().isEmpty()
        || draftVariable.value(QStringLiteral("min_value")).toDouble() != -50.0
        || draftVariable.value(QStringLiteral("delta_max")).toDouble() != 9.0
        || draftVariable.value(QStringLiteral("stage_relevant")).toBool(true)
        || savedDatabaseDraft.value(QStringLiteral("roles")).toArray().size() != 2) {
        return fail(QStringLiteral("stateJournal.databaseDraft should stay synchronized and preserve unknown fields")) ? 0 : 1;
    }

    const QJsonObject savedWorkshop = savedRaw.value("creativeWorkshop").toObject();
    const QJsonObject savedOpening = savedWorkshop.value("opening").toObject();
    if (savedWorkshop.value("enabled").toBool(true)
        || !savedOpening.value("enabled").toBool(false)
        || savedOpening.value("title").toString() != QStringLiteral("Old Opening")
        || savedWorkshop.value("dynamicScenes").toArray().size() != 1
        || savedWorkshop.value("ambience").toObject().value("musicUrl").toString() != QStringLiteral("old.mp3")
        || savedWorkshop.value("unknown_workshop_field").toString() != QStringLiteral("workshop-stays")) {
        return fail(QStringLiteral("creativeWorkshop nested data should be preserved")) ? 0 : 1;
    }

    const QJsonObject savedPersonas = savedRaw.value("personas").toObject();
    if (savedPersonas.size() != 2
        || savedPersonas.contains(QStringLiteral("2"))
        || savedPersonas.value("1").toObject().value("name").toString() != QStringLiteral("Persona One Edited")
        || savedPersonas.value("1").toObject().value("unknown_persona_field").toString() != QStringLiteral("persona-stays")
        || savedPersonas.value("1_2").toObject().value("role_id").toString() != QStringLiteral("role-three")) {
        return fail(QStringLiteral("personas should support controlled add, remove, edit and duplicate-key recovery")) ? 0 : 1;
    }

    const QVariantMap refreshedDraft = bridge.cardDraft();
    if (refreshedDraft.value(QStringLiteral("name")).toString() != QStringLiteral("New Name")
        || refreshedDraft.value(QStringLiteral("tagCount")).toInt() != 24
        || !refreshedDraft.value(QStringLiteral("databaseEnabled")).toBool()
        || refreshedDraft.value(QStringLiteral("personas")).toList().size() != 2
        || refreshedDraft.value(QStringLiteral("databaseConfig")).toMap().value(QStringLiteral("roles")).toList().size() != 2
        || refreshedDraft.value(QStringLiteral("creativeWorkshopEnabled")).toBool()
        || !refreshedDraft.value(QStringLiteral("openingEnabled")).toBool()) {
        return fail(QStringLiteral("cardDraft should refresh after save")) ? 0 : 1;
    }

    CardAuthoringService cardAuthoringService(root.absolutePath());
    QJsonObject authoringProject = cardAuthoringService.createEmptyProject();
    authoringProject.insert(QStringLiteral("database"), savedDatabaseDraft);
    const QJsonObject compiledStateJournal = cardAuthoringService.compileRoleCard(authoringProject)
        .value(QStringLiteral("raw")).toObject()
        .value(QStringLiteral("stateJournal")).toObject();
    const QJsonObject compiledRole = findByKey(compiledStateJournal.value(QStringLiteral("roles")).toArray(), QStringLiteral("role_id"), QStringLiteral("role-one"));
    const QJsonObject compiledVariable = findByKey(compiledRole.value(QStringLiteral("variables")).toArray(), QStringLiteral("var_key"), QStringLiteral("trust"));
    const QJsonObject compiledStage = findByKey(compiledRole.value(QStringLiteral("stages")).toArray(), QStringLiteral("stage_key"), QStringLiteral("stage_a"));
    const QJsonObject compiledSnapshot = findByKey(compiledRole.value(QStringLiteral("snapshotFields")).toArray(), QStringLiteral("key"), QStringLiteral("mood"));
    if (compiledRole.value(QStringLiteral("mode")).toString() != QStringLiteral("variables")
        || compiledRole.value(QStringLiteral("stateJournalMode")).toString() != QStringLiteral("variables")
        || compiledVariable.value(QStringLiteral("min_value")).toDouble() != -50.0
        || compiledVariable.value(QStringLiteral("max_value")).toDouble() != 150.0
        || compiledVariable.value(QStringLiteral("delta_min")).toDouble() != -7.0
        || compiledVariable.value(QStringLiteral("delta_max")).toDouble() != 9.0
        || compiledVariable.value(QStringLiteral("display")).toBool(false) != true
        || compiledVariable.value(QStringLiteral("stage_relevant")).toBool(true)
        || compiledStage.value(QStringLiteral("priority")).toInt() != 77
        || compiledStage.value(QStringLiteral("conditions")).toArray().size() != 2
        || !compiledStage.value(QStringLiteral("allow_regression")).toBool()
        || compiledStage.value(QStringLiteral("confirm_turns")).toInt() != 3
        || compiledStage.value(QStringLiteral("cooldown_turns")).toInt() != 6
        || compiledSnapshot.value(QStringLiteral("display")).toBool(true)) {
        return fail(QStringLiteral("CardAuthoring compiler should preserve complete WebUI database fields")) ? 0 : 1;
    }

    const QVariantMap activateResult = bridge.activateRoleCard(QStringLiteral("cards/activation_card.json"));
    if (!activateResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("activateRoleCard failed: %1").arg(activateResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    const QString activateBackupPath = activateResult.value(QStringLiteral("backupPath")).toString();
    if (activateBackupPath.isEmpty() || !QFileInfo::exists(activateBackupPath)) {
        return fail(QStringLiteral("activateRoleCard should back up current_role_card.json")) ? 0 : 1;
    }

    const QJsonObject activated = readJsonObject(cardPath);
    const QJsonObject activatedRaw = activated.value("raw").toObject();
    if (activated.value("source_name").toString() != QStringLiteral("activation_card.json")
        || activated.value("source_path").toString() != QStringLiteral("cards/activation_card.json")
        || activated.value("card_uid").toString().trimmed().isEmpty()) {
        return fail(QStringLiteral("activated role card should record source identity")) ? 0 : 1;
    }
    if (activatedRaw.value("name").toString() != QStringLiteral("Activation Hero")
        || activatedRaw.value("description").toString() != QStringLiteral("activation description")
        || activatedRaw.value("unknown_activation_raw").toString() != QStringLiteral("activation-raw-stays")) {
        return fail(QStringLiteral("activated role card should wrap and preserve source raw fields")) ? 0 : 1;
    }
    const QVariantMap activatedDraft = bridge.cardDraft();
    if (activatedDraft.value(QStringLiteral("name")).toString() != QStringLiteral("Activation Hero")
        || activatedDraft.value(QStringLiteral("source_path")).toString() != QStringLiteral("cards/activation_card.json")) {
        return fail(QStringLiteral("cardDraft should refresh after activating a library card")) ? 0 : 1;
    }
    const QVariantMap traversalResult = bridge.activateRoleCard(QStringLiteral("../data/current_role_card.json"));
    if (traversalResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("activateRoleCard should reject path traversal")) ? 0 : 1;
    }

    return 0;
}
