#pragma once

#include "card_authoring/cardauthoringpaths.h"

#include <QJsonArray>
#include <QJsonObject>
#include <QString>

class CardAuthoringProjectStore final {
public:
    explicit CardAuthoringProjectStore(QString rootPath);

    CardAuthoringPaths paths() const;
    QJsonObject createEmptyProject() const;
    QJsonObject normalizeProject(const QJsonObject& project) const;

    QJsonObject loadWorkspace(QString* errorMessage = nullptr) const;
    QJsonObject saveWorkspace(const QJsonObject& project, QString* savedPath = nullptr, QString* errorMessage = nullptr) const;
    QJsonArray listProjects(QString* errorMessage = nullptr) const;
    QJsonObject loadProject(const QString& filename, QString* errorMessage = nullptr) const;
    QJsonObject saveProject(const QString& filename, const QJsonObject& project, QString* savedPath = nullptr, QString* errorMessage = nullptr) const;
    QJsonObject deleteProject(const QString& filename, QString* archivedPath = nullptr, QString* errorMessage = nullptr) const;
    QJsonObject importProjectFile(const QString& sourcePath, QString* importedPath = nullptr, QString* errorMessage = nullptr) const;
    QJsonObject exportProjectFile(const QString& targetPath, const QJsonObject& project, QString* exportedPath = nullptr, QString* errorMessage = nullptr) const;

    static QString safeProjectFilename(const QString& filename);

private:
    bool writeProjectFile(const QString& path, const QJsonObject& project, QString* errorMessage) const;
    QJsonObject readProjectFile(const QString& path, QString* errorMessage) const;
    QString exportFilePath(const QString& targetPath, const QJsonObject& project, QString* errorMessage) const;
    QString uniqueProjectFilename(const QString& filename) const;

    CardAuthoringPaths paths_;
};
