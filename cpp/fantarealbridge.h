#pragma once

#include <QByteArray>
#include <QJsonArray>
#include <QJsonObject>
#include <QObject>
#include <QString>
#include <QStringList>
#include <QVariantList>
#include <QVariantMap>

class QNetworkAccessManager;
class QNetworkReply;
class QTimer;

class FantarealBridge final : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString legacyRoot READ legacyRoot NOTIFY scanChanged)
    Q_PROPERTY(int criticalFileCount READ criticalFileCount NOTIFY scanChanged)
    Q_PROPERTY(int criticalFileFoundCount READ criticalFileFoundCount NOTIFY scanChanged)
    Q_PROPERTY(int assetDirCount READ assetDirCount NOTIFY scanChanged)
    Q_PROPERTY(int assetDirFoundCount READ assetDirFoundCount NOTIFY scanChanged)
    Q_PROPERTY(int cardFileCount READ cardFileCount NOTIFY scanChanged)
    Q_PROPERTY(int assetFileCount READ assetFileCount NOTIFY scanChanged)
    Q_PROPERTY(int pluginManifestCount READ pluginManifestCount NOTIFY scanChanged)
    Q_PROPERTY(double criticalFilePercent READ criticalFilePercent NOTIFY scanChanged)
    Q_PROPERTY(double assetDirPercent READ assetDirPercent NOTIFY scanChanged)
    Q_PROPERTY(QString scanSummary READ scanSummary NOTIFY scanChanged)
    Q_PROPERTY(QStringList foundLegacyItems READ foundLegacyItems NOTIFY scanChanged)
    Q_PROPERTY(QStringList missingLegacyItems READ missingLegacyItems NOTIFY scanChanged)
    Q_PROPERTY(QVariantMap settingsDraft READ settingsDraft NOTIFY scanChanged)
    Q_PROPERTY(double backgroundImagePreviewOpacity READ backgroundImagePreviewOpacity NOTIFY scanChanged)
    Q_PROPERTY(QVariantMap routeDraft READ routeDraft NOTIFY scanChanged)
    Q_PROPERTY(QVariantMap cardDraft READ cardDraft NOTIFY scanChanged)
    Q_PROPERTY(QVariantMap presetDraft READ presetDraft NOTIFY scanChanged)
    Q_PROPERTY(QVariantMap worldbookDraft READ worldbookDraft NOTIFY scanChanged)
    Q_PROPERTY(QVariantList worldbookEntryDrafts READ worldbookEntryDrafts NOTIFY scanChanged)
    Q_PROPERTY(QVariantList memoryDrafts READ memoryDrafts NOTIFY scanChanged)
    Q_PROPERTY(QStringList settingsRows READ settingsRows NOTIFY scanChanged)
    Q_PROPERTY(QStringList routeRows READ routeRows NOTIFY scanChanged)
    Q_PROPERTY(QStringList cardRows READ cardRows NOTIFY scanChanged)
    Q_PROPERTY(QStringList presetRows READ presetRows NOTIFY scanChanged)
    Q_PROPERTY(QStringList worldbookRows READ worldbookRows NOTIFY scanChanged)
    Q_PROPERTY(QVariantList chatMessages READ chatMessages NOTIFY scanChanged)
    Q_PROPERTY(QStringList chatRows READ chatRows NOTIFY scanChanged)
    Q_PROPERTY(QStringList memoryRows READ memoryRows NOTIFY scanChanged)
    Q_PROPERTY(QString settingsStatus READ settingsStatus NOTIFY scanChanged)
    Q_PROPERTY(QString routeStatus READ routeStatus NOTIFY scanChanged)
    Q_PROPERTY(QString cardStatus READ cardStatus NOTIFY scanChanged)
    Q_PROPERTY(QString presetStatus READ presetStatus NOTIFY scanChanged)
    Q_PROPERTY(QString worldbookStatus READ worldbookStatus NOTIFY scanChanged)
    Q_PROPERTY(QString chatStatus READ chatStatus NOTIFY scanChanged)
    Q_PROPERTY(QString memoryStatus READ memoryStatus NOTIFY scanChanged)
    Q_PROPERTY(bool chatGenerating READ chatGenerating NOTIFY chatGenerationChanged)
    Q_PROPERTY(QString chatGenerationStatus READ chatGenerationStatus NOTIFY chatGenerationChanged)
    Q_PROPERTY(QString chatStreamingPreview READ chatStreamingPreview NOTIFY chatGenerationChanged)
    Q_PROPERTY(bool firstLaunchDisclaimerRequired READ firstLaunchDisclaimerRequired NOTIFY scanChanged)
    Q_PROPERTY(QString firstLaunchDisclaimerVersion READ firstLaunchDisclaimerVersion CONSTANT)
    Q_PROPERTY(QString firstLaunchConfirmationText READ firstLaunchConfirmationText CONSTANT)
    Q_PROPERTY(QString buildInfo READ buildInfo CONSTANT)

public:
    explicit FantarealBridge(QObject* parent = nullptr);

    QString legacyRoot() const;
    int criticalFileCount() const;
    int criticalFileFoundCount() const;
    int assetDirCount() const;
    int assetDirFoundCount() const;
    int cardFileCount() const;
    int assetFileCount() const;
    int pluginManifestCount() const;
    double criticalFilePercent() const;
    double assetDirPercent() const;
    QString scanSummary() const;
    QStringList foundLegacyItems() const;
    QStringList missingLegacyItems() const;
    QVariantMap settingsDraft() const;
    double backgroundImagePreviewOpacity() const;
    QVariantMap routeDraft() const;
    QVariantMap cardDraft() const;
    QVariantMap presetDraft() const;
    QVariantMap worldbookDraft() const;
    QVariantList worldbookEntryDrafts() const;
    QVariantList memoryDrafts() const;
    QStringList settingsRows() const;
    QStringList routeRows() const;
    QStringList cardRows() const;
    QStringList presetRows() const;
    QStringList worldbookRows() const;
    QVariantList chatMessages() const;
    QStringList chatRows() const;
    QStringList memoryRows() const;
    QString settingsStatus() const;
    QString routeStatus() const;
    QString cardStatus() const;
    QString presetStatus() const;
    QString worldbookStatus() const;
    QString chatStatus() const;
    QString memoryStatus() const;
    bool chatGenerating() const;
    QString chatGenerationStatus() const;
    QString chatStreamingPreview() const;
    bool firstLaunchDisclaimerRequired() const;
    QString firstLaunchDisclaimerVersion() const;
    QString firstLaunchConfirmationText() const;
    QString buildInfo() const;

    Q_INVOKABLE void refreshLegacyScan();
    Q_INVOKABLE void previewBackgroundImageOpacity(double opacity);
    Q_INVOKABLE QVariantMap saveSettingsDraft(const QVariantMap& draft);
    Q_INVOKABLE QVariantMap saveRouteDraft(const QVariantMap& draft);
    Q_INVOKABLE QVariantMap saveRouteProviderDraft(int providerIndex, const QVariantMap& draft);
    Q_INVOKABLE QVariantMap deleteRouteProvider(int providerIndex);
    Q_INVOKABLE QVariantMap saveRouteProviderKey(int providerIndex, const QString& newKey);
    Q_INVOKABLE QVariantMap saveCardDraft(const QVariantMap& draft);
    Q_INVOKABLE QVariantMap activateRoleCard(const QString& relativePath);
    Q_INVOKABLE QVariantMap importRoleCardFile(const QString& sourcePath);
    Q_INVOKABLE QVariantMap savePresetDraft(const QVariantMap& draft);
    Q_INVOKABLE QVariantMap importPresetFile(const QString& sourcePath);
    Q_INVOKABLE QVariantMap saveWorldbookDraft(const QVariantMap& draft);
    Q_INVOKABLE QVariantMap saveWorldbookEntry(int entryIndex, const QVariantMap& draft);
    Q_INVOKABLE QVariantMap importWorldbookFile(const QString& sourcePath);
    Q_INVOKABLE QVariantMap saveMemoryEntry(int entryIndex, const QVariantMap& draft);
    Q_INVOKABLE QVariantMap syncCurrentCardToPersona();
    Q_INVOKABLE QVariantMap sendChatMessage(const QString& message);
    Q_INVOKABLE QVariantMap sendChatMessageDemoReply(const QString& message);
    Q_INVOKABLE QVariantMap sendChatMessageWithReply(const QString& message);
    Q_INVOKABLE QVariantMap regenerateLastChatReply();
    Q_INVOKABLE QVariantMap startChatMessageWithReply(const QString& message);
    Q_INVOKABLE QVariantMap startRegenerateLastChatReply();
    Q_INVOKABLE QVariantMap stopChatGeneration();
    Q_INVOKABLE QVariantMap endChatConversation();
    Q_INVOKABLE QVariantMap acceptFirstLaunchDisclaimer(const QString& ageGroup, const QString& typedConfirmation);

signals:
    void scanChanged();
    void chatGenerationChanged();
    void chatGenerationFinished(const QVariantMap& result);

private:
    QVariantMap startPendingChatRequest(
        const QString& url,
        const QString& apiKey,
        int requestTimeout,
        const QJsonObject& payload,
        const QJsonArray& conversations,
        const QString& assistantSource,
        const QString& successMessage);
    void finishPendingChatRequest(bool ok, const QString& message, const QString& backupPath = {});
    void completePendingChatRequest(const QString& assistantContent);
    void completeEndChatConversation(const QString& memorySummary, const QString& transcript);
    void clearPendingChatRequest();
    void setChatGenerationState(bool generating, const QString& status);
    void setChatStreamingPreview(const QString& preview);

    QString legacyRoot_;
    int criticalFileCount_{};
    int criticalFileFoundCount_{};
    int assetDirCount_{};
    int assetDirFoundCount_{};
    int cardFileCount_{};
    int assetFileCount_{};
    int pluginManifestCount_{};
    double criticalFilePercent_{};
    double assetDirPercent_{};
    QString scanSummary_;
    QStringList foundLegacyItems_;
    QStringList missingLegacyItems_;
    QVariantMap settingsDraft_;
    double backgroundImagePreviewOpacity_ = 0.42;
    QVariantMap routeDraft_;
    QVariantMap cardDraft_;
    QVariantMap presetDraft_;
    QVariantMap worldbookDraft_;
    QVariantList worldbookEntryDrafts_;
    QVariantList memoryDrafts_;
    QStringList settingsRows_;
    QStringList routeRows_;
    QStringList cardRows_;
    QStringList presetRows_;
    QStringList worldbookRows_;
    QVariantList chatMessages_;
    QStringList chatRows_;
    QStringList memoryRows_;
    QString settingsStatus_;
    QString routeStatus_;
    QString cardStatus_;
    QString presetStatus_;
    QString worldbookStatus_;
    QString chatStatus_;
    QString memoryStatus_;
    bool chatGenerating_{};
    QString chatGenerationStatus_;
    QString chatStreamingPreview_;
    QNetworkAccessManager* chatNetwork_{};
    QNetworkReply* chatReply_{};
    QTimer* chatTimer_{};
    QByteArray pendingChatResponseBuffer_;
    QJsonArray pendingChatConversations_;
    QString pendingChatConversationPath_;
    QString pendingChatRelativePath_;
    QString pendingChatAssistantSource_;
    QString pendingChatSuccessMessage_;
    QString pendingChatAbortMessage_;
    bool pendingChatSawStream_{};
};
