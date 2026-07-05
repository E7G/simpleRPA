#pragma once

#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QScrollArea>
#include <QLabel>
#include <QPushButton>
#include <QTimer>
#include <QFrame>
#include <QVector>
#include <QString>
#include <QJsonObject>

#include "QFluent/Label.h"
#include "QFluent/PushButton.h"
#include "QFluent/ScrollArea.h"
#include "QFluent/CheckBox.h"
#include "QFluent/ComboBox.h"
#include "QFluent/SpinBox.h"
#include "fluent_theme.h"
#include "simpleRPA_ffi.h"

class WindowSelector;
class TableWidget;

class DashboardPage : public QWidget
{
    Q_OBJECT

public:
    explicit DashboardPage(QWidget* parent = nullptr);
    ~DashboardPage();
    void refreshWindows();

public slots:
    void openListDialog();
    void saveListDialog();
    void exportPython();
    void runAllScripts();

private:
    struct ScriptItem {
        QString id;
        QString name;
        QString path;
        QString actionsJson;
        QString localActionGroupsJson;
        int actionCount;
        double delayBefore;
        int repeatCount;
        bool enabled;
    };

    void setupUI();
    void onAddScript();
    void openScriptList();
    void saveScriptList();
    void clearScriptList();
    bool loadScriptListFromFile(const QString& filepath);
    bool saveScriptListToFile(const QString& filepath);
    bool appendScriptFromPath(const QString& filepath, const QJsonObject& savedState = QJsonObject());
    QString generateBatchPythonCode() const;
    QString actionsToPythonCode(const QString& actionsJson, const QString& localGroupsJson, const QString& indent) const;
    QString sanitizePythonIdentifier(const QString& text) const;
    QString pythonStringLiteral(const QString& text) const;
    QString pythonBoolLiteral(bool value) const;
    void refreshLaunchCommands();
    QString selectedLaunchCommandId() const;
    void setSelectedLaunchCommand(const QString& commandId);
    void refreshScriptList();
    void runScript(const QString& scriptId);
    void stopRunning();
    void pollPlayerState();
    void runScriptAt(int index);
    void removeScript(const QString& scriptId);
    void setScriptEnabled(const QString& scriptId, bool enabled);
    void setScriptDelayBefore(const QString& scriptId, double seconds);
    void setScriptRepeatCount(const QString& scriptId, int repeatCount);
    int findScriptIndex(const QString& scriptId) const;

    FfiWindowUtils* m_windowUtils;
    FfiPlayer* m_player;
    FfiCommandManager* m_commandManager;
    WindowSelector* m_windowSelector;
    CheckBox* m_offscreenCb;
    ComboBox* m_launchCombo;
    TableWidget* m_windowTable;
    QLabel* m_statusLabel;
    QTimer* m_refreshTimer;
    QTimer* m_playerPollTimer;
    QVBoxLayout* m_scriptListLayout;
    QWidget* m_emptyHint;
    PushButton* m_openListBtn;
    PushButton* m_saveListBtn;
    PushButton* m_clearListBtn;
    PrimaryPushButton* m_runAllBtn;
    PushButton* m_stopBtn;
    QVector<ScriptItem> m_scripts;
    QVector<int> m_runQueue;
    QString m_currentListFile;
    int m_currentRunIndex;
    bool m_isRunning;
};
