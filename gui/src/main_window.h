#ifndef MAIN_WINDOW_H
#define MAIN_WINDOW_H

#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QStackedWidget>
#include <QTimer>
#include <QLabel>

#include "QFluent/FluentWindow.h"
#include "QFluent/FluentIcon.h"
#include "QFluent/PushButton.h"
#include "QFluent/PrimaryPushButton.h"
#include "QFluent/CheckBox.h"
#include "QFluent/ProgressBar.h"
#include "QFluent/BodyLabel.h"
#include "QFluent/SegmentedWidget.h"
#include "QFluent/NavigationBar.h"

#include "ffi/rpa_bridge.h"
#include "panels/action_panel.h"
#include "panels/property_panel.h"
#include "panels/recorder_panel.h"
#include "panels/script_editor.h"
#include "panels/window_selector.h"
#include "panels/dashboard_page.h"
#include "panels/command_panel.h"

class MainWindow : public MSFluentWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow();

protected:
    void closeEvent(QCloseEvent* event) override;

private:
    void setupUi();
    void setupNavigation();
    void setupDesignerInterface();
    void setupCommandInterface();
    void setupConnections();
    void loadSettings();
    void saveSettings();

    void onRunClicked();
    void onPauseClicked();
    void onStopClicked();
    void onSpeedChanged();
    void onRepeatChanged();
    void onInfiniteChanged(int state);
    void onTimeoutChanged();
    void onOffscreenChanged();
    void onWindowSelected(int64_t hwnd);
    void onActionAdded(int type);
    void onActionSelected(int index);
    void onActionsChanged();
    void updateRunButtons();
    void updateMousePosition();
    void updateStatusBar(const QString& text);

    // Interfaces
    QWidget* dashboardInterface;
    QWidget* homeInterface;
    QWidget* commandInterface;

    // Panels
    ActionPanel* actionPanel;
    PropertyPanel* propertyPanel;
    RecorderPanel* recorderPanel;
    ScriptEditor* scriptEditor;
    WindowSelector* windowSelector;
    DashboardPage* dashboardPage;
    CommandManagerWidget* commandPanel;

    // Controls
    PrimaryPushButton* runBtn;
    PushButton* pauseBtn;
    PushButton* stopBtn;
    CheckBox* infiniteCb;
    CheckBox* offscreenCb;
    ProgressBar* progressBar;
    BodyLabel* statusLabel;
    BodyLabel* coordLabel;
    QDoubleSpinBox* speedSpin;
    QSpinBox* repeatSpin;
    QDoubleSpinBox* timeoutSpin;

    QStackedWidget* leftStack;
    SegmentedWidget* leftSegment;

    // Core
    RpaBridge bridge;
    QTimer* mousePosTimer;
    QTimer* stateTimer;
    void* playerHandle = nullptr;

    static constexpr const char* APP_VERSION = "0.2.0";
};

#endif // MAIN_WINDOW_H
