#include "fantarealbridge.h"

#include <QCoreApplication>
#include <QCryptographicHash>
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

bool writeJson(const QString& path, const QJsonObject& object) {
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return false;
    }
    return file.write(QJsonDocument(object).toJson(QJsonDocument::Indented)) > 0;
}

QJsonObject readJson(const QString& path) {
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
        QFile file(root.absoluteFilePath(it.key()));
        if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
            return false;
        }
        if (file.write(document.toJson(QJsonDocument::Compact)) <= 0) {
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
    QFile backgroundFile(root.absoluteFilePath(QStringLiteral("data/background.png")));
    if (!backgroundFile.open(QIODevice::WriteOnly) || backgroundFile.write("background") <= 0) {
        return fail(QStringLiteral("failed to create temporary background file")) ? 0 : 1;
    }

    QJsonObject initialSettings;
    initialSettings.insert(QStringLiteral("llm_base_url"), QStringLiteral("https://old.example/v1"));
    initialSettings.insert(QStringLiteral("llm_api_key"), QStringLiteral("keep-llm-key"));
    initialSettings.insert(QStringLiteral("llm_model"), QStringLiteral("old-model"));
    initialSettings.insert(QStringLiteral("theme"), QStringLiteral("dark"));
    initialSettings.insert(QStringLiteral("background_image_path"), QStringLiteral("data/background.png"));
    initialSettings.insert(QStringLiteral("background_image_opacity"), 0.33);
    initialSettings.insert(QStringLiteral("temperature"), 0.85);
    initialSettings.insert(QStringLiteral("history_limit"), 20);
    initialSettings.insert(QStringLiteral("request_timeout"), 120);
    initialSettings.insert(QStringLiteral("demo_mode"), false);
    initialSettings.insert(QStringLiteral("embedding_base_url"), QStringLiteral("https://embedding.example/v1"));
    initialSettings.insert(QStringLiteral("embedding_api_key"), QStringLiteral("keep-embedding-key"));
    initialSettings.insert(QStringLiteral("embedding_model"), QStringLiteral("embed-old"));
    initialSettings.insert(QStringLiteral("retrieval_top_k"), 4);
    initialSettings.insert(QStringLiteral("rerank_enabled"), false);
    initialSettings.insert(QStringLiteral("rerank_base_url"), QStringLiteral("https://rerank.example/v1"));
    initialSettings.insert(QStringLiteral("rerank_api_key"), QStringLiteral("keep-rerank-key"));
    initialSettings.insert(QStringLiteral("rerank_model"), QStringLiteral("rerank-old"));
    initialSettings.insert(QStringLiteral("rerank_top_n"), 3);
    initialSettings.insert(QStringLiteral("memory_summary_length"), QStringLiteral("medium"));
    initialSettings.insert(QStringLiteral("memory_summary_max_chars"), 520);
    initialSettings.insert(QStringLiteral("unknown_plugin_field"), QStringLiteral("must-stay"));

    const QString settingsPath = root.absoluteFilePath(QStringLiteral("data/settings.json"));
    if (!writeJson(settingsPath, initialSettings)) {
        return fail(QStringLiteral("failed to write fixture settings.json")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;
    if (!bridge.firstLaunchDisclaimerRequired()) {
        return fail(QStringLiteral("first launch disclaimer should be required when no acceptance is stored")) ? 0 : 1;
    }
    if (bridge.acceptFirstLaunchDisclaimer(QStringLiteral("bad_age"), bridge.firstLaunchConfirmationText()).value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("invalid age group should not accept first launch disclaimer")) ? 0 : 1;
    }
    if (bridge.acceptFirstLaunchDisclaimer(QStringLiteral("18_plus"), QStringLiteral("wrong text")).value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("wrong confirmation text should not accept first launch disclaimer")) ? 0 : 1;
    }
    QString compactConfirmation = bridge.firstLaunchConfirmationText();
    compactConfirmation.remove(QLatin1Char(' '));
    compactConfirmation.replace(QStringLiteral("本地部署、第三方"), QStringLiteral("本地部署，第三方"));
    const QVariantMap acceptResult = bridge.acceptFirstLaunchDisclaimer(QStringLiteral("14_to_17"), compactConfirmation);
    if (!acceptResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("acceptFirstLaunchDisclaimer failed: %1").arg(acceptResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (bridge.firstLaunchDisclaimerRequired()) {
        return fail(QStringLiteral("first launch disclaimer should not be required after acceptance")) ? 0 : 1;
    }
    const QJsonObject acceptedSettings = readJson(settingsPath);
    const QString confirmationHash = acceptedSettings.value(QStringLiteral("typed_confirmation_hash")).toString();
    const QString expectedHash = QString::fromLatin1(QCryptographicHash::hash(
        compactConfirmation.toUtf8(),
        QCryptographicHash::Sha256).toHex());
    if (!acceptedSettings.value(QStringLiteral("first_launch_disclaimer_accepted")).toBool()
        || acceptedSettings.value(QStringLiteral("disclaimer_version")).toString() != bridge.firstLaunchDisclaimerVersion()
        || acceptedSettings.value(QStringLiteral("age_group")).toString() != QStringLiteral("14_to_17")
        || !acceptedSettings.value(QStringLiteral("minor_mode_enabled")).toBool()
        || acceptedSettings.value(QStringLiteral("accepted_at")).toString().isEmpty()
        || confirmationHash != expectedHash
        || confirmationHash == bridge.firstLaunchConfirmationText()) {
        return fail(QStringLiteral("first launch disclaimer acceptance was not persisted safely")) ? 0 : 1;
    }
    if (bridge.settingsDraft().value(QStringLiteral("demo_mode")).toBool()) {
        return fail(QStringLiteral("initial demo_mode draft should be false")) ? 0 : 1;
    }
    if (!bridge.settingsDraft().value(QStringLiteral("output_splitting_enabled")).toBool()) {
        return fail(QStringLiteral("output_splitting_enabled should default to true")) ? 0 : 1;
    }
    if (bridge.settingsDraft().value(QStringLiteral("background_image_path")).toString() != QStringLiteral("data/background.png")
        || !bridge.settingsDraft().value(QStringLiteral("background_image_url")).toString().startsWith(QStringLiteral("file:///"))) {
        return fail(QStringLiteral("initial background draft should expose a local image URL")) ? 0 : 1;
    }
    if (bridge.backgroundImagePreviewOpacity() < 0.32 || bridge.backgroundImagePreviewOpacity() > 0.34) {
        return fail(QStringLiteral("initial background preview opacity should come from settings")) ? 0 : 1;
    }
    bridge.previewBackgroundImageOpacity(99.0);
    if (bridge.backgroundImagePreviewOpacity() != 1.0) {
        return fail(QStringLiteral("background preview opacity should clamp high values")) ? 0 : 1;
    }
    if (bridge.settingsDraft().value(QStringLiteral("background_image_opacity")).toDouble() < 0.32
        || bridge.settingsDraft().value(QStringLiteral("background_image_opacity")).toDouble() > 0.34) {
        return fail(QStringLiteral("background preview should not mutate the saved settings draft")) ? 0 : 1;
    }
    bridge.previewBackgroundImageOpacity(-99.0);
    if (bridge.backgroundImagePreviewOpacity() != 0.0) {
        return fail(QStringLiteral("background preview opacity should clamp low values")) ? 0 : 1;
    }
    bridge.previewBackgroundImageOpacity(0.33);

    QVariantMap draft;
    draft.insert(QStringLiteral("llm_base_url"), QStringLiteral("https://new.example/v1"));
    draft.insert(QStringLiteral("llm_api_key"), QString());
    draft.insert(QStringLiteral("llm_model"), QStringLiteral("new-model"));
    draft.insert(QStringLiteral("theme"), QStringLiteral("unsupported-theme"));
    draft.insert(QStringLiteral("background_image_path"), QStringLiteral("file:///E:/Pictures/new-bg.png"));
    draft.insert(QStringLiteral("background_image_opacity"), 99.0);
    draft.insert(QStringLiteral("temperature"), 8.0);
    draft.insert(QStringLiteral("history_limit"), -10);
    draft.insert(QStringLiteral("request_timeout"), 3);
    draft.insert(QStringLiteral("demo_mode"), true);
    draft.insert(QStringLiteral("output_splitting_enabled"), false);
    draft.insert(QStringLiteral("embedding_api_key"), QStringLiteral("new-embedding-key"));
    draft.insert(QStringLiteral("retrieval_top_k"), 99);
    draft.insert(QStringLiteral("rerank_enabled"), true);
    draft.insert(QStringLiteral("rerank_api_key"), QString());
    draft.insert(QStringLiteral("rerank_top_n"), 99);
    draft.insert(QStringLiteral("memory_summary_length"), QStringLiteral("bad-value"));
    draft.insert(QStringLiteral("memory_summary_max_chars"), 99999);

    const QVariantMap result = bridge.saveSettingsDraft(draft);
    if (!result.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("saveSettingsDraft failed: %1").arg(result.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }

    const QString backupPath = result.value(QStringLiteral("backupPath")).toString();
    if (backupPath.isEmpty() || !QFileInfo::exists(backupPath)) {
        return fail(QStringLiteral("settings backup was not created")) ? 0 : 1;
    }

    const QJsonObject saved = readJson(settingsPath);
    if (saved.value("llm_base_url").toString() != QStringLiteral("https://new.example/v1")) {
        return fail(QStringLiteral("llm_base_url was not saved")) ? 0 : 1;
    }
    if (saved.value("llm_api_key").toString() != QStringLiteral("keep-llm-key")) {
        return fail(QStringLiteral("blank llm_api_key should preserve the old secret")) ? 0 : 1;
    }
    if (saved.value("embedding_api_key").toString() != QStringLiteral("new-embedding-key")) {
        return fail(QStringLiteral("non-blank embedding_api_key should replace the old secret")) ? 0 : 1;
    }
    if (saved.value("rerank_api_key").toString() != QStringLiteral("keep-rerank-key")) {
        return fail(QStringLiteral("blank rerank_api_key should preserve the old secret")) ? 0 : 1;
    }
    if (saved.value("unknown_plugin_field").toString() != QStringLiteral("must-stay")) {
        return fail(QStringLiteral("unknown settings field was not preserved")) ? 0 : 1;
    }
    if (!saved.value(QStringLiteral("first_launch_disclaimer_accepted")).toBool()
        || saved.value(QStringLiteral("disclaimer_version")).toString() != bridge.firstLaunchDisclaimerVersion()
        || saved.value(QStringLiteral("age_group")).toString() != QStringLiteral("14_to_17")
        || !saved.value(QStringLiteral("minor_mode_enabled")).toBool()
        || saved.value(QStringLiteral("typed_confirmation_hash")).toString() != expectedHash) {
        return fail(QStringLiteral("settings save should preserve first launch disclaimer fields")) ? 0 : 1;
    }
    if (saved.value("theme").toString() != QStringLiteral("light")) {
        return fail(QStringLiteral("theme should normalize to light unless dark")) ? 0 : 1;
    }
    if (saved.value("background_image_path").toString() != QStringLiteral("E:/Pictures/new-bg.png")) {
        return fail(QStringLiteral("background_image_path should normalize local file URLs")) ? 0 : 1;
    }
    if (saved.value("background_image_opacity").toDouble() != 1.0) {
        return fail(QStringLiteral("background_image_opacity clamp failed")) ? 0 : 1;
    }
    if (saved.value("temperature").toDouble() != 2.0) {
        return fail(QStringLiteral("temperature clamp failed")) ? 0 : 1;
    }
    if (saved.value("history_limit").toInt() != 1) {
        return fail(QStringLiteral("history_limit clamp failed")) ? 0 : 1;
    }
    if (saved.value("request_timeout").toInt() != 10) {
        return fail(QStringLiteral("request_timeout clamp failed")) ? 0 : 1;
    }
    if (!saved.value("demo_mode").toBool(false)) {
        return fail(QStringLiteral("demo_mode should be saved")) ? 0 : 1;
    }
    if (saved.value("output_splitting_enabled").toBool(true)) {
        return fail(QStringLiteral("output_splitting_enabled should be saved")) ? 0 : 1;
    }
    if (saved.value("retrieval_top_k").toInt() != 12) {
        return fail(QStringLiteral("retrieval_top_k clamp failed")) ? 0 : 1;
    }
    if (saved.value("rerank_top_n").toInt() != 12) {
        return fail(QStringLiteral("rerank_top_n clamp failed")) ? 0 : 1;
    }
    if (saved.value("memory_summary_length").toString() != QStringLiteral("medium")) {
        return fail(QStringLiteral("memory_summary_length normalization failed")) ? 0 : 1;
    }
    if (saved.value("memory_summary_max_chars").toInt() != 2000) {
        return fail(QStringLiteral("memory_summary_max_chars clamp failed")) ? 0 : 1;
    }

    return 0;
}
