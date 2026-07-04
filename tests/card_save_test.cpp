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

bool makeRequiredFiles(const QDir& root) {
    const QStringList dirs = {
        QStringLiteral("data"),
        QStringLiteral("data/auto_saga"),
        QStringLiteral("data/mods/state_journal"),
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

    QFile(root.absoluteFilePath(QStringLiteral("data/mods/state_journal/state_journal.db"))).open(QIODevice::WriteOnly);
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
    personaOne.insert(QStringLiteral("unknown_persona_field"), QStringLiteral("persona-stays"));
    QJsonObject personas;
    personas.insert(QStringLiteral("1"), personaOne);
    personas.insert(QStringLiteral("2"), QJsonObject{ { QStringLiteral("name"), QStringLiteral("Persona Two") } });

    QJsonObject stateJournal;
    stateJournal.insert(QStringLiteral("version"), 1);
    stateJournal.insert(QStringLiteral("enabled"), false);
    stateJournal.insert(QStringLiteral("roles"), QJsonArray{ QJsonObject{ { QStringLiteral("id"), QStringLiteral("role-1") } } });
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
    if (initialDraft.value(QStringLiteral("name")).toString() != QStringLiteral("Old Name")
        || initialDraft.value(QStringLiteral("tagCount")).toInt() != 2
        || initialDraft.value(QStringLiteral("personaCount")).toInt() != 2
        || initialDraft.value(QStringLiteral("dynamicSceneCount")).toInt() != 1) {
        return fail(QStringLiteral("cardDraft should expose safe card summary fields")) ? 0 : 1;
    }
    if (initialDraft.contains(QStringLiteral("personas"))
        || initialDraft.contains(QStringLiteral("creativeWorkshop"))
        || initialDraft.contains(QStringLiteral("stateJournal"))) {
        return fail(QStringLiteral("cardDraft should not expose nested mutable card objects")) ? 0 : 1;
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
    draft.insert(QStringLiteral("stateJournalEnabled"), true);
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
        || savedStateJournal.value("roles").toArray().size() != 1) {
        return fail(QStringLiteral("stateJournal nested data should be preserved")) ? 0 : 1;
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
        || savedPersonas.value("1").toObject().value("unknown_persona_field").toString() != QStringLiteral("persona-stays")) {
        return fail(QStringLiteral("personas should be preserved")) ? 0 : 1;
    }

    const QVariantMap refreshedDraft = bridge.cardDraft();
    if (refreshedDraft.value(QStringLiteral("name")).toString() != QStringLiteral("New Name")
        || refreshedDraft.value(QStringLiteral("tagCount")).toInt() != 24
        || !refreshedDraft.value(QStringLiteral("stateJournalEnabled")).toBool()
        || refreshedDraft.value(QStringLiteral("creativeWorkshopEnabled")).toBool()
        || !refreshedDraft.value(QStringLiteral("openingEnabled")).toBool()) {
        return fail(QStringLiteral("cardDraft should refresh after save")) ? 0 : 1;
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
