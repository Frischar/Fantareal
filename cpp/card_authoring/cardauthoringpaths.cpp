#include "card_authoring/cardauthoringpaths.h"

#include <QDir>

#include <utility>

CardAuthoringPaths::CardAuthoringPaths(QString rootPath)
    : rootPath_(QDir::cleanPath(rootPath.trimmed().isEmpty() ? QDir::currentPath() : std::move(rootPath))) {
}

QString CardAuthoringPaths::directoryRelativePath() {
    return QStringLiteral("data/card_authoring");
}

QString CardAuthoringPaths::projectsRelativePath() {
    return QStringLiteral("data/card_authoring/projects");
}

QString CardAuthoringPaths::autosavesRelativePath() {
    return QStringLiteral("data/card_authoring/autosaves");
}

QString CardAuthoringPaths::exportsRelativePath() {
    return QStringLiteral("data/card_authoring/exports");
}

QString CardAuthoringPaths::backupsRelativePath() {
    return QStringLiteral("data/card_authoring/fa_backups");
}

QString CardAuthoringPaths::workspaceRelativePath() {
    return QStringLiteral("data/card_authoring/workspace.cardwork.json");
}

QString CardAuthoringPaths::currentRoleCardRelativePath() {
    return QStringLiteral("data/current_role_card.json");
}

QString CardAuthoringPaths::projectFileExtension() {
    return QStringLiteral(".cardwork.json");
}

QString CardAuthoringPaths::rootPath() const {
    return rootPath_;
}

QString CardAuthoringPaths::directoryPath() const {
    return QDir(rootPath_).absoluteFilePath(directoryRelativePath());
}

QString CardAuthoringPaths::projectsPath() const {
    return QDir(rootPath_).absoluteFilePath(projectsRelativePath());
}

QString CardAuthoringPaths::autosavesPath() const {
    return QDir(rootPath_).absoluteFilePath(autosavesRelativePath());
}

QString CardAuthoringPaths::exportsPath() const {
    return QDir(rootPath_).absoluteFilePath(exportsRelativePath());
}

QString CardAuthoringPaths::backupsPath() const {
    return QDir(rootPath_).absoluteFilePath(backupsRelativePath());
}

QString CardAuthoringPaths::workspacePath() const {
    return QDir(rootPath_).absoluteFilePath(workspaceRelativePath());
}

QString CardAuthoringPaths::currentRoleCardPath() const {
    return QDir(rootPath_).absoluteFilePath(currentRoleCardRelativePath());
}

QString CardAuthoringPaths::projectPath(const QString& filename) const {
    return QDir(projectsPath()).absoluteFilePath(filename);
}

bool CardAuthoringPaths::ensureRuntimeDirectories(QString* errorMessage) const {
    QDir root(rootPath_);
    const QStringList relativePaths = {
        directoryRelativePath(),
        projectsRelativePath(),
        autosavesRelativePath(),
        exportsRelativePath(),
        backupsRelativePath(),
    };
    for (const QString& relativePath : relativePaths) {
        if (!root.mkpath(relativePath)) {
            if (errorMessage) {
                *errorMessage = QStringLiteral("failed to create card authoring directory: %1")
                    .arg(root.absoluteFilePath(relativePath));
            }
            return false;
        }
    }
    return true;
}
