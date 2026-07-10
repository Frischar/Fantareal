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

    QJsonObject personas;
    personas.insert(QStringLiteral("1"), QJsonObject{
        { QStringLiteral("name"), QStringLiteral("Luna") },
        { QStringLiteral("description"), QStringLiteral("Keeps the engine-room rituals.") },
        { QStringLiteral("personality"), QStringLiteral("Playful but precise.") },
        { QStringLiteral("scenario"), QStringLiteral("Listening from engineering.") },
    });
    personas.insert(QStringLiteral("2"), QJsonObject{
        { QStringLiteral("name"), QStringLiteral("Vox") },
        { QStringLiteral("description"), QStringLiteral("Shipboard analyst.") },
        { QStringLiteral("personality"), QStringLiteral("Dry and concise.") },
        { QStringLiteral("scenario"), QStringLiteral("Watching telemetry.") },
    });
    personas.insert(QStringLiteral("3"), QJsonObject{
        { QStringLiteral("name"), QStringLiteral("Mira") },
        { QStringLiteral("description"), QStringLiteral("Navigator apprentice.") },
        { QStringLiteral("personality"), QStringLiteral("Earnest and observant.") },
        { QStringLiteral("scenario"), QStringLiteral("Standing beside Astra.") },
    });

    QJsonObject raw;
    raw.insert(QStringLiteral("name"), QStringLiteral("Astra"));
    raw.insert(QStringLiteral("description"), QStringLiteral("A calm starship navigator."));
    raw.insert(QStringLiteral("personality"), QStringLiteral("Patient and observant."));
    raw.insert(QStringLiteral("scenario"), QStringLiteral("A quiet bridge before a jump."));
    raw.insert(QStringLiteral("first_mes"), QStringLiteral("Welcome aboard, pilot."));
    raw.insert(QStringLiteral("mes_example"), QStringLiteral("Astra: Keep one hand on the rail."));
    raw.insert(QStringLiteral("creator_notes"), QStringLiteral("Keep the tone soft and practical."));
    raw.insert(QStringLiteral("personas"), personas);
    raw.insert(QStringLiteral("unknown_raw_field"), QStringLiteral("raw-stays"));

    QJsonObject card;
    card.insert(QStringLiteral("source_name"), QStringLiteral("astra.json"));
    card.insert(QStringLiteral("card_uid"), QStringLiteral("card-astra"));
    card.insert(QStringLiteral("raw"), raw);
    card.insert(QStringLiteral("unknown_root_field"), QStringLiteral("root-stays"));
    const QString cardPath = root.absoluteFilePath(QStringLiteral("data/current_role_card.json"));
    if (!writeJson(cardPath, QJsonDocument(card))) {
        return fail(QStringLiteral("failed to write current role card fixture")) ? 0 : 1;
    }

    QJsonObject oldPersona;
    oldPersona.insert(QStringLiteral("name"), QStringLiteral("Old Persona"));
    oldPersona.insert(QStringLiteral("greeting"), QStringLiteral("old greeting"));
    oldPersona.insert(QStringLiteral("system_prompt"), QStringLiteral("old prompt"));
    oldPersona.insert(QStringLiteral("unknown_persona_root"), QStringLiteral("persona-stays"));
    oldPersona.insert(QStringLiteral("nested"), QJsonObject{ { QStringLiteral("keep"), true } });
    const QString personaPath = root.absoluteFilePath(QStringLiteral("data/persona.json"));
    if (!writeJson(personaPath, QJsonDocument(oldPersona))) {
        return fail(QStringLiteral("failed to write persona fixture")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;
    const QVariantMap result = bridge.syncCurrentCardToPersona();
    if (!result.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("syncCurrentCardToPersona failed: %1").arg(result.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }

    const QString backupPath = result.value(QStringLiteral("backupPath")).toString();
    if (backupPath.isEmpty() || !QFileInfo::exists(backupPath)) {
        return fail(QStringLiteral("persona backup was not created")) ? 0 : 1;
    }

    const QJsonObject savedPersona = readJsonObject(personaPath);
    const QString systemPrompt = savedPersona.value(QStringLiteral("system_prompt")).toString();
    if (savedPersona.value(QStringLiteral("name")).toString() != QStringLiteral("Astra")
        || savedPersona.value(QStringLiteral("greeting")).toString() != QStringLiteral("Welcome aboard, pilot.")
        || savedPersona.value(QStringLiteral("unknown_persona_root")).toString() != QStringLiteral("persona-stays")
        || !savedPersona.value(QStringLiteral("nested")).toObject().value(QStringLiteral("keep")).toBool(false)) {
        return fail(QStringLiteral("persona sync should update generated fields and preserve unknown fields")) ? 0 : 1;
    }

    if (!systemPrompt.contains(QStringLiteral("Character Description: A calm starship navigator."))
        || !systemPrompt.contains(QStringLiteral("Personality: Patient and observant."))
        || !systemPrompt.contains(QStringLiteral("Scenario: A quiet bridge before a jump."))
        || !systemPrompt.contains(QStringLiteral("Creator Notes: Keep the tone soft and practical."))
        || !systemPrompt.contains(QStringLiteral("Dialogue Example: Astra: Keep one hand on the rail."))
        || !systemPrompt.contains(QStringLiteral("Every assistant turn must include all of these characters speaking"))
        || !systemPrompt.contains(QStringLiteral("Luna: Keeps the engine-room rituals."))
        || !systemPrompt.contains(QStringLiteral("Vox: Shipboard analyst."))
        || !systemPrompt.contains(QStringLiteral("Mira: Navigator apprentice."))) {
        return fail(QStringLiteral("persona system prompt should be generated from role card content")) ? 0 : 1;
    }

    const QJsonObject untouchedCard = readJsonObject(cardPath);
    if (untouchedCard.value(QStringLiteral("unknown_root_field")).toString() != QStringLiteral("root-stays")
        || untouchedCard.value(QStringLiteral("raw")).toObject().value(QStringLiteral("unknown_raw_field")).toString() != QStringLiteral("raw-stays")) {
        return fail(QStringLiteral("persona sync should not rewrite current_role_card.json")) ? 0 : 1;
    }

    const QString rows = bridge.chatRows().join(QStringLiteral("\n"));
    if (!rows.contains(QStringLiteral("Astra")) || !rows.contains(QStringLiteral("Welcome aboard, pilot."))) {
        return fail(QStringLiteral("chatRows should refresh after persona sync")) ? 0 : 1;
    }

    return 0;
}
