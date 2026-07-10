#pragma once

#include <QString>

class CardAuthoringPaths final {
public:
    explicit CardAuthoringPaths(QString rootPath);

    static QString directoryRelativePath();
    static QString projectsRelativePath();
    static QString autosavesRelativePath();
    static QString exportsRelativePath();
    static QString backupsRelativePath();
    static QString workspaceRelativePath();
    static QString currentRoleCardRelativePath();
    static QString projectFileExtension();

    QString rootPath() const;
    QString directoryPath() const;
    QString projectsPath() const;
    QString autosavesPath() const;
    QString exportsPath() const;
    QString backupsPath() const;
    QString workspacePath() const;
    QString currentRoleCardPath() const;
    QString projectPath(const QString& filename) const;

    bool ensureRuntimeDirectories(QString* errorMessage = nullptr) const;

private:
    QString rootPath_;
};
