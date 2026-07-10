#include "database/databaseworkerconfigstore.h"

#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QSaveFile>

#include <utility>

namespace {
constexpr int kWorkerConfigSchemaVersion = 1;

QString boundedString(const QVariantMap& draft, const QString& camelKey, const QString& snakeKey,
    const QString& fallback, int maximumLength) {
    QVariant value;
    if (draft.contains(camelKey)) {
        value = draft.value(camelKey);
    } else if (draft.contains(snakeKey)) {
        value = draft.value(snakeKey);
    } else {
        return fallback;
    }
    return value.toString().trimmed().left(maximumLength);
}

bool boolValue(const QVariantMap& draft, const QString& camelKey, const QString& snakeKey, bool fallback) {
    if (draft.contains(camelKey)) {
        return draft.value(camelKey).toBool();
    }
    if (draft.contains(snakeKey)) {
        return draft.value(snakeKey).toBool();
    }
    return fallback;
}

int intValue(const QVariantMap& draft, const QString& camelKey, const QString& snakeKey,
    int fallback, int minimum, int maximum) {
    bool ok = false;
    QVariant value;
    if (draft.contains(camelKey)) {
        value = draft.value(camelKey);
    } else if (draft.contains(snakeKey)) {
        value = draft.value(snakeKey);
    } else {
        return fallback;
    }
    const int result = value.toInt(&ok);
    return ok ? qBound(minimum, result, maximum) : fallback;
}

double numberValue(const QVariantMap& draft, const QString& camelKey, const QString& snakeKey,
    double fallback, double minimum, double maximum) {
    bool ok = false;
    QVariant value;
    if (draft.contains(camelKey)) {
        value = draft.value(camelKey);
    } else if (draft.contains(snakeKey)) {
        value = draft.value(snakeKey);
    } else {
        return fallback;
    }
    const double result = value.toDouble(&ok);
    return ok ? qBound(minimum, result, maximum) : fallback;
}

DatabaseWorkerConfig configFromObject(const QJsonObject& object) {
    DatabaseWorkerConfig config;
    config.schemaVersion = kWorkerConfigSchemaVersion;
    config.enabled = object.value(QStringLiteral("enabled")).toBool(true);
    config.autoUpdate = object.value(QStringLiteral("auto_update")).toBool(true);
    config.apiType = QStringLiteral("openai_compatible");
    config.apiBaseUrl = object.value(QStringLiteral("api_base_url")).toString().trimmed().left(2048);
    config.apiKey = object.value(QStringLiteral("api_key")).toString().trimmed();
    config.model = object.value(QStringLiteral("model")).toString().trimmed().left(256);
    config.temperature = qBound(0.0, object.value(QStringLiteral("temperature")).toDouble(0.0), 2.0);
    config.requestTimeout = qBound(10, object.value(QStringLiteral("request_timeout")).toInt(120), 600);
    config.inputTurnCount = qBound(1, object.value(QStringLiteral("input_turn_count")).toInt(3), 20);
    config.maxRepairAttempts = qBound(0, object.value(QStringLiteral("max_repair_attempts")).toInt(1), 1);
    return config;
}

QVariantMap configDraft(const DatabaseWorkerConfig& config) {
    QVariantMap draft;
    draft.insert(QStringLiteral("enabled"), config.enabled);
    draft.insert(QStringLiteral("autoUpdate"), config.autoUpdate);
    draft.insert(QStringLiteral("apiType"), config.apiType);
    draft.insert(QStringLiteral("apiBaseUrl"), config.apiBaseUrl);
    draft.insert(QStringLiteral("apiKeyConfigured"), config.apiKeyConfigured());
    draft.insert(QStringLiteral("model"), config.model);
    draft.insert(QStringLiteral("temperature"), config.temperature);
    draft.insert(QStringLiteral("requestTimeout"), config.requestTimeout);
    draft.insert(QStringLiteral("inputTurnCount"), config.inputTurnCount);
    draft.insert(QStringLiteral("maxRepairAttempts"), config.maxRepairAttempts);
    return draft;
}
}

DatabaseWorkerConfigStore::DatabaseWorkerConfigStore(DatabasePaths paths)
    : paths_(std::move(paths)) {
}

DatabaseWorkerConfig DatabaseWorkerConfigStore::load(QString* errorMessage) const {
    return configFromObject(readRaw(errorMessage));
}

QVariantMap DatabaseWorkerConfigStore::draft(QString* errorMessage) const {
    return configDraft(load(errorMessage));
}

DatabaseOperationResult DatabaseWorkerConfigStore::save(const QVariantMap& draft, bool clearApiKey) const {
    QString readError;
    QJsonObject object = readRaw(&readError);
    if (!readError.isEmpty()) {
        return {false, QStringLiteral("config_invalid"), readError};
    }

    const DatabaseWorkerConfig existing = configFromObject(object);
    object.insert(QStringLiteral("schema_version"), kWorkerConfigSchemaVersion);
    object.insert(QStringLiteral("enabled"), boolValue(draft, QStringLiteral("enabled"), QStringLiteral("enabled"), existing.enabled));
    object.insert(QStringLiteral("auto_update"), boolValue(draft, QStringLiteral("autoUpdate"), QStringLiteral("auto_update"), existing.autoUpdate));
    object.insert(QStringLiteral("api_type"), QStringLiteral("openai_compatible"));
    object.insert(QStringLiteral("api_base_url"), boundedString(draft, QStringLiteral("apiBaseUrl"), QStringLiteral("api_base_url"), existing.apiBaseUrl, 2048));
    object.insert(QStringLiteral("model"), boundedString(draft, QStringLiteral("model"), QStringLiteral("model"), existing.model, 256));
    object.insert(QStringLiteral("temperature"), numberValue(draft, QStringLiteral("temperature"), QStringLiteral("temperature"), existing.temperature, 0.0, 2.0));
    object.insert(QStringLiteral("request_timeout"), intValue(draft, QStringLiteral("requestTimeout"), QStringLiteral("request_timeout"), existing.requestTimeout, 10, 600));
    object.insert(QStringLiteral("input_turn_count"), intValue(draft, QStringLiteral("inputTurnCount"), QStringLiteral("input_turn_count"), existing.inputTurnCount, 1, 20));
    object.insert(QStringLiteral("max_repair_attempts"), intValue(draft, QStringLiteral("maxRepairAttempts"), QStringLiteral("max_repair_attempts"), existing.maxRepairAttempts, 0, 1));

    if (clearApiKey) {
        object.insert(QStringLiteral("api_key"), QString());
    } else {
        const QString apiKey = boundedString(draft, QStringLiteral("apiKey"), QStringLiteral("api_key"), QString(), 8192);
        object.insert(QStringLiteral("api_key"), apiKey.isEmpty() ? existing.apiKey : apiKey);
    }
    return writeRaw(object);
}

DatabaseOperationResult DatabaseWorkerConfigStore::copyMainSettings(const QJsonObject& mainSettings) const {
    QVariantMap draft;
    draft.insert(QStringLiteral("apiBaseUrl"), mainSettings.value(QStringLiteral("llm_base_url")).toString());
    draft.insert(QStringLiteral("model"), mainSettings.value(QStringLiteral("llm_model")).toString());
    draft.insert(QStringLiteral("temperature"), mainSettings.value(QStringLiteral("temperature")).toDouble(0.0));
    draft.insert(QStringLiteral("requestTimeout"), mainSettings.value(QStringLiteral("request_timeout")).toInt(120));
    const QString apiKey = mainSettings.value(QStringLiteral("llm_api_key")).toString().trimmed();
    if (!apiKey.isEmpty()) {
        draft.insert(QStringLiteral("apiKey"), apiKey);
    }
    return save(draft);
}

QJsonObject DatabaseWorkerConfigStore::readRaw(QString* errorMessage) const {
    QFile file(paths_.workerSettingsPath());
    if (!file.exists()) {
        return {};
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("failed to read DatabaseWorker settings: %1").arg(file.errorString());
        }
        return {};
    }
    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("invalid DatabaseWorker settings JSON: %1").arg(parseError.errorString());
        }
        return {};
    }
    return document.object();
}

DatabaseOperationResult DatabaseWorkerConfigStore::writeRaw(const QJsonObject& object) const {
    QString directoryError;
    if (!paths_.ensureRuntimeDirectory(&directoryError)) {
        return {false, QStringLiteral("config_write_error"), directoryError};
    }

    const QString path = paths_.workerSettingsPath();
    const QString backupPath = path + QStringLiteral(".bak");
    if (QFileInfo::exists(path)) {
        QFile::remove(backupPath);
        if (!QFile::copy(path, backupPath)) {
            return {false, QStringLiteral("config_backup_error"), QStringLiteral("failed to back up DatabaseWorker settings")};
        }
    }

    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return {false, QStringLiteral("config_write_error"), QStringLiteral("failed to open DatabaseWorker settings: %1").arg(file.errorString())};
    }
    const QByteArray payload = QJsonDocument(object).toJson(QJsonDocument::Indented);
    if (file.write(payload) != payload.size() || !file.commit()) {
        return {false, QStringLiteral("config_write_error"), QStringLiteral("failed to save DatabaseWorker settings: %1").arg(file.errorString())};
    }
    return {true, {}, QStringLiteral("DatabaseWorker settings saved")};
}
