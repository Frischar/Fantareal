#include "database/legacystatejournaladapter.h"

#include <QJsonValue>

QString LegacyStateJournalAdapter::legacyDatabaseRelativePath() {
    return QStringLiteral("data/mods/state_journal/state_journal.db");
}

QString LegacyStateJournalAdapter::legacyStageTagPrefix() {
    return QStringLiteral("state_journal.stage.");
}

bool LegacyStateJournalAdapter::hasStateJournal(const QJsonObject& raw) {
    return raw.value(QStringLiteral("stateJournal")).isObject();
}

bool LegacyStateJournalAdapter::databaseEnabled(const QJsonObject& raw, bool defaultEnabled) {
    const QJsonObject stateJournal = raw.value(QStringLiteral("stateJournal")).toObject();
    if (stateJournal.isEmpty() && !hasStateJournal(raw)) {
        return defaultEnabled;
    }
    return stateJournal.value(QStringLiteral("enabled")).toBool(defaultEnabled);
}

QJsonObject LegacyStateJournalAdapter::applyDatabaseEnabled(QJsonObject raw, bool enabled) {
    QJsonObject stateJournal = raw.value(QStringLiteral("stateJournal")).toObject();
    stateJournal.insert(QStringLiteral("enabled"), enabled);
    raw.insert(QStringLiteral("stateJournal"), stateJournal);
    return raw;
}
