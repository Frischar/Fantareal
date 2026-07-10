#include "database/databasepaths.h"

#include <QDir>

#include <utility>

DatabasePaths::DatabasePaths(QString rootPath)
    : rootPath_(QDir::cleanPath(rootPath.trimmed().isEmpty() ? QDir::currentPath() : std::move(rootPath))) {
}

QString DatabasePaths::directoryRelativePath() {
    return QStringLiteral("data/database");
}

QString DatabasePaths::databaseRelativePath() {
    return QStringLiteral("data/database/database.db");
}

QString DatabasePaths::rootPath() const {
    return rootPath_;
}

QString DatabasePaths::directoryPath() const {
    return QDir(rootPath_).absoluteFilePath(directoryRelativePath());
}

QString DatabasePaths::databasePath() const {
    return QDir(rootPath_).absoluteFilePath(databaseRelativePath());
}

bool DatabasePaths::ensureRuntimeDirectory(QString* errorMessage) const {
    QDir root(rootPath_);
    if (root.mkpath(directoryRelativePath())) {
        return true;
    }
    if (errorMessage) {
        *errorMessage = QStringLiteral("failed to create database directory: %1").arg(directoryPath());
    }
    return false;
}
