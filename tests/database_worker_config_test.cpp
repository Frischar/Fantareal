#include "database/databaseservice.h"

#include <QCoreApplication>
#include <QFile>
#include <QJsonDocument>
#include <QTemporaryDir>

#include <iostream>

namespace {
bool fail(const QString& message) {
    std::cerr << message.toStdString() << '\n';
    return false;
}

QJsonObject readJsonFile(const QString& path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll());
    return document.isObject() ? document.object() : QJsonObject{};
}
}

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);

    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        return fail(QStringLiteral("failed to create temporary directory")) ? 0 : 1;
    }

    DatabaseService service(tempDir.path());
    const DatabasePaths paths = service.paths();
    if (!paths.ensureRuntimeDirectory()) {
        return fail(QStringLiteral("failed to create worker settings directory")) ? 0 : 1;
    }

    QJsonObject legacyRaw;
    legacyRaw.insert(QStringLiteral("unknown_extension"), QStringLiteral("preserve-me"));
    legacyRaw.insert(QStringLiteral("api_key"), QStringLiteral("old-secret"));
    QFile seed(paths.workerSettingsPath());
    if (!seed.open(QIODevice::WriteOnly | QIODevice::Text)
        || seed.write(QJsonDocument(legacyRaw).toJson()) < 1) {
        return fail(QStringLiteral("failed to seed worker settings")) ? 0 : 1;
    }
    seed.close();

    QVariantMap draft;
    draft.insert(QStringLiteral("enabled"), false);
    draft.insert(QStringLiteral("autoUpdate"), false);
    draft.insert(QStringLiteral("apiBaseUrl"), QStringLiteral(" https://example.invalid/v1 "));
    draft.insert(QStringLiteral("model"), QStringLiteral("fast-json"));
    draft.insert(QStringLiteral("temperature"), 3.5);
    draft.insert(QStringLiteral("requestTimeout"), 1);
    draft.insert(QStringLiteral("inputTurnCount"), 99);
    draft.insert(QStringLiteral("maxRepairAttempts"), 9);
    if (!service.saveWorkerConfig(draft).ok) {
        return fail(QStringLiteral("failed to save worker configuration")) ? 0 : 1;
    }

    const QVariantMap exposed = service.workerConfigDraft();
    if (exposed.contains(QStringLiteral("apiKey")) || !exposed.value(QStringLiteral("apiKeyConfigured")).toBool()
        || exposed.value(QStringLiteral("temperature")).toDouble() != 2.0
        || exposed.value(QStringLiteral("requestTimeout")).toInt() != 10
        || exposed.value(QStringLiteral("inputTurnCount")).toInt() != 20
        || exposed.value(QStringLiteral("maxRepairAttempts")).toInt() != 1) {
        return fail(QStringLiteral("worker draft should clamp fields and never expose API key")) ? 0 : 1;
    }

    const QJsonObject saved = readJsonFile(paths.workerSettingsPath());
    if (saved.value(QStringLiteral("unknown_extension")).toString() != QStringLiteral("preserve-me")
        || saved.value(QStringLiteral("api_key")).toString() != QStringLiteral("old-secret")
        || saved.value(QStringLiteral("api_type")).toString() != QStringLiteral("openai_compatible")
        || !QFile::exists(paths.workerSettingsPath() + QStringLiteral(".bak"))) {
        return fail(QStringLiteral("worker save should preserve key/unknown fields and create a backup")) ? 0 : 1;
    }

    QJsonObject mainSettings;
    mainSettings.insert(QStringLiteral("llm_base_url"), QStringLiteral("https://main.example/v1"));
    mainSettings.insert(QStringLiteral("llm_api_key"), QStringLiteral("main-secret"));
    mainSettings.insert(QStringLiteral("llm_model"), QStringLiteral("main-model"));
    mainSettings.insert(QStringLiteral("temperature"), 0.4);
    mainSettings.insert(QStringLiteral("request_timeout"), 240);
    if (!service.copyMainModelConfig(mainSettings).ok) {
        return fail(QStringLiteral("failed to copy main model config")) ? 0 : 1;
    }
    const DatabaseWorkerConfig copied = service.loadWorkerConfig();
    if (copied.apiBaseUrl != QStringLiteral("https://main.example/v1")
        || copied.model != QStringLiteral("main-model") || copied.apiKey != QStringLiteral("main-secret")) {
        return fail(QStringLiteral("main model copy should remain internal and one-time")) ? 0 : 1;
    }

    if (!service.saveWorkerConfig({}, true).ok || service.loadWorkerConfig().apiKeyConfigured()) {
        return fail(QStringLiteral("explicit clear should remove DatabaseWorker API key")) ? 0 : 1;
    }
    return 0;
}
