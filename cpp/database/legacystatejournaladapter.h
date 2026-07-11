#pragma once

#include <QJsonObject>
#include <QString>

class LegacyStateJournalAdapter final {
public:
    static QString legacyDatabaseRelativePath();
    static QString legacyStageTagPrefix();

    static bool hasStateJournal(const QJsonObject& raw);
    static bool databaseEnabled(const QJsonObject& raw, bool defaultEnabled = true);
    static QJsonObject applyDatabaseEnabled(QJsonObject raw, bool enabled);
};
