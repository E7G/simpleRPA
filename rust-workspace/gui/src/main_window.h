#pragma once

#include "FluentWidget.h"
#include "QFluent/StackedWidget.h"
#include "QFluent/Navigation/NavigationPanel.h"
#include "QFluent/Navigation/NavigationWidget.h"
#include "QFluent/Navigation/Pivot.h"

#include <QTimer>
#include <QFrame>

#include "simpleRPA_ffi.h"

class ActionPanel;
class ScriptEditor;
class PropertyPanel;
class RecorderPanel;
class DashboardPage;
class CommandManagerWidget;
class TrayService;
class WindowSelector;
class QCloseEvent;
class BodyLabel;
class CheckBox;
class DoubleSpinBox;
class PrimaryPushButton;
class ProgressBar;
class PushButton;
class SpinBox;

class MainWindow : public FluentWidget
{
    Q_OBJECT
public:
    explicit MainWindow();

protected:
    void closeEvent(QCloseEvent* event) override;

private:
    void initWidget();
    void setupDesignerPage();
    void setupCommandPage();
    void setupTray();
    void setupConnections();

    void addSubInterface(const QString& routeKey, const QIcon& icon, const QString& text,
                         QWidget* widget, bool selectable = true,
                         NavigationPanel::ItemPosition position = NavigationPanel::ItemPosition::TOP,
                         const QString& tooltip = QString());

    QFrame* vline();

    void openScript();
    void saveScript();
    void exportPython();
    void runDashboardFromTray();
    void runScript();
    void pauseScript();
    void stopScript();
    void onActionAdded(const QString& actionJson);
    void onActionSelected(const QString& actionJson, int index);
    void onActionUpdated(const QString& actionJson);
    void onActionsChanged();
    void onExecuteSingle(int index);
    void updateMousePosition();
    void saveRuntimeSettings();
    void updateRunButtons();
    static void handlePlayerEvent(int event, int index, int total, int repeat, int value, void* userData);
    void onPlayerEvent(int event, int index, int total, int repeat, int value);

    FfiConfig* m_config;
    FfiPlayer* m_player;
    FfiWindowUtils* m_windowUtils;
    FfiExporter* m_exporter;

    NavigationPanel* m_navPanel;
    StackedWidget* m_stacked;

    DashboardPage* m_dashboardPage;
    QWidget* m_homeInterface;
    QWidget* m_commandInterface;

    ActionPanel* m_actionPanel;
    ScriptEditor* m_scriptEditor;
    PropertyPanel* m_propertyPanel;
    RecorderPanel* m_recorderPanel;
    WindowSelector* m_windowSelector;
    DoubleSpinBox* m_speedSpin;
    SpinBox* m_repeatSpin;
    SpinBox* m_timeoutSpin;
    CheckBox* m_offscreenCb;
    CheckBox* m_infiniteCb;
    QStackedWidget* m_leftStack;
    Pivot* m_leftSegment;
    PrimaryPushButton* m_runBtn;
    PushButton* m_pauseBtn;
    PushButton* m_stopBtn;
    ProgressBar* m_progressBar;
    BodyLabel* m_statusLabel;
    BodyLabel* m_coordLabel;

    CommandManagerWidget* m_commandPanel;
    TrayService* m_trayService;
    QTimer* m_mousePosTimer;
    int m_selectedActionIndex;
    bool m_allowExit;
};
