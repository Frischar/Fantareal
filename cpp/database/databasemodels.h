#pragma once

#include <QMap>
#include <QString>
#include <QStringList>

struct DatabaseStatus {
    bool ok{};
    QString databasePath;
    QString message;
    int schemaVersion{};
};

struct DatabaseOverview {
    DatabaseStatus status;
    QString rootPath;
    QString directoryPath;
    QString relativePath;
    bool fileExists{};
    qint64 fileSizeBytes{};
    QStringList tableNames;
    QMap<QString, int> tableCounts;
};
