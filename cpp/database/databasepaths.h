#pragma once

#include <QString>

class DatabasePaths final {
public:
    explicit DatabasePaths(QString rootPath);

    static QString directoryRelativePath();
    static QString databaseRelativePath();
    static QString workerSettingsRelativePath();

    QString rootPath() const;
    QString directoryPath() const;
    QString databasePath() const;
    QString workerSettingsPath() const;

    bool ensureRuntimeDirectory(QString* errorMessage = nullptr) const;

private:
    QString rootPath_;
};
