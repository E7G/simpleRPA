#include "main_window.h"
#include "Router.h"
#include "FluentIcon.h"
#include "Theme.h"
#include "StyleSheet.h"
#include "fluent_theme.h"

#include <QApplication>
#include <QFileDialog>
#include <QFileInfo>
#include <QMessageBox>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QStatusBar>
#include <QPoint>
#include <QCloseEvent>
#include <QCursor>
#include <QMetaObject>
#include <algorithm>

#include "QFluent/PushButton.h"
#include "QFluent/Label.h"
#include "QFluent/CheckBox.h"
#include "QFluent/SpinBox.h"
#include "QFluent/Progress/ProgressBar.h"
#include "QFluent/Navigation/Pivot.h"

#include "action_panel.h"
#include "script_editor.h"
#include "property_panel.h"
#include "recorder_panel.h"
#include "command_panel.h"
#include "dashboard_page.h"
#include "tray_service.h"
#include "window_selector.h"

using FIT = Fluent::IconType;
using NIP = NavigationPanel::ItemPosition;

namespace {
constexpr int PlayerEventActionStart = 1;
constexpr int PlayerEventActionEnd = 2;
constexpr int PlayerEventProgress = 3;
constexpr int PlayerEventStateChanged = 4;
constexpr int PlayerEventFinished = 5;
}

MainWindow::MainWindow()
{
    m_config = config_new();
    m_player = player_new();
    m_windowUtils = window_utils_new();
    m_exporter = exporter_new();
    m_allowExit = false;
    m_selectedActionIndex = -1;

    setWindowTitle("SimpleRPA");
    setMinimumSize(1280, 850);
    setWindowButtonHints(WindowButtonHint::WindowIcon | WindowButtonHint::Title |
                         WindowButtonHint::Minimize | WindowButtonHint::Maximize |
                         WindowButtonHint::Close | WindowButtonHint::ThemeToggle);

    QHBoxLayout *layout = new QHBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(0);

    m_navPanel = new NavigationPanel(this);
    m_stacked = new StackedWidget(this);

    layout->addWidget(m_navPanel, 0);
    layout->addWidget(m_stacked, 1);

    setContentsMargins(0, 48, 0, 0);
    m_navPanel->setExpandWidth(240);

    initWidget();
    setupTray();
    setupConnections();

    m_mousePosTimer = new QTimer(this);
    connect(m_mousePosTimer, &QTimer::timeout, this, &MainWindow::updateMousePosition);
    m_mousePosTimer->start(100);
}

void MainWindow::initWidget()
{
    m_dashboardPage = new DashboardPage();
    m_dashboardPage->setObjectName("dashboardInterface");
    addSubInterface("dashboard", Fluent::icon(FIT::HOME), "控制台", m_dashboardPage);

    m_homeInterface = new QWidget();
    m_homeInterface->setObjectName("homeInterface");
    addSubInterface("designer", Fluent::icon(FIT::EDIT), "流程设计器", m_homeInterface);

    m_commandInterface = new QWidget();
    m_commandInterface->setObjectName("commandInterface");
    addSubInterface("commands", Fluent::icon(FIT::APPLICATION), "启动命令", m_commandInterface);

    m_navPanel->addSeparator(NIP::BOTTOM);
    addSubInterface("open", Fluent::icon(FIT::FOLDER), "打开", nullptr, false, NIP::BOTTOM);
    addSubInterface("save", Fluent::icon(FIT::SAVE), "保存", nullptr, false, NIP::BOTTOM);
    addSubInterface("export", Fluent::icon(FIT::SHARE), "导出", nullptr, false, NIP::BOTTOM);

    connect(m_navPanel->widget("open"), &NavigationWidget::clicked, this, &MainWindow::openScript);
    connect(m_navPanel->widget("save"), &NavigationWidget::clicked, this, &MainWindow::saveScript);
    connect(m_navPanel->widget("export"), &NavigationWidget::clicked, this, &MainWindow::exportPython);

    m_navPanel->setCurrentItem("designer");

    setupDesignerPage();
    setupCommandPage();
}

void MainWindow::addSubInterface(const QString& routeKey, const QIcon& icon, const QString& text,
                                  QWidget* widget, bool selectable,
                                  NavigationPanel::ItemPosition position, const QString& tooltip)
{
    if (widget) {
        widget->setObjectName(routeKey);
        m_navPanel->addItem(routeKey, icon, text,
            [this, routeKey]() { m_stacked->setCurrentIndex(m_stacked->indexOf(m_stacked->findChild<QWidget*>(routeKey))); },
            selectable, position, tooltip);
        m_stacked->addWidget(widget);
    } else {
        m_navPanel->addItem(routeKey, icon, text, nullptr, selectable, position, tooltip);
    }
}

QFrame* MainWindow::vline()
{
    auto* line = new QFrame();
    line->setFrameShape(QFrame::VLine);
    line->setFixedWidth(1);
    line->setStyleSheet("color: rgba(128,128,128,0.3);");
    return line;
}

void MainWindow::setupDesignerPage()
{
    auto* root = new QVBoxLayout(m_homeInterface);
    root->setContentsMargins(12, 12, 12, 8);
    root->setSpacing(8);

    // ===== Toolbar (AutomateToolbar) =====
    auto* toolbar = new QWidget();
    toolbar->setObjectName("automateToolbar");
    toolbar->setFixedHeight(48);
    auto* tb = new QHBoxLayout(toolbar);
    tb->setContentsMargins(12, 6, 12, 6);
    tb->setSpacing(10);

    // Window selector
    m_windowSelector = new WindowSelector();
    m_windowSelector->setMinimumWidth(200);
    tb->addWidget(m_windowSelector);

    tb->addWidget(vline());

    // Speed
    tb->addWidget(new BodyLabel("速度"));
    m_speedSpin = new DoubleSpinBox();
    m_speedSpin->setRange(0.1, 10.0);
    m_speedSpin->setValue(config_get_default_speed(m_config));
    m_speedSpin->setSuffix("x");
    m_speedSpin->setSingleStep(0.1);
    m_speedSpin->setFixedWidth(76);
    m_speedSpin->setFixedHeight(28);
    tb->addWidget(m_speedSpin);

    // Repeat
    tb->addWidget(new BodyLabel("重复"));
    m_repeatSpin = new SpinBox();
    m_repeatSpin->setRange(1, 999);
    m_repeatSpin->setValue(config_get_default_repeat_count(m_config));
    m_repeatSpin->setFixedWidth(68);
    m_repeatSpin->setFixedHeight(28);
    tb->addWidget(m_repeatSpin);

    // Offscreen
    m_offscreenCb = new CheckBox("离屏后台(隐藏图标)");
    m_offscreenCb->setToolTip("把目标窗口移到屏幕外并隐藏任务栏图标，结束后自动恢复");
    m_offscreenCb->setChecked(config_get_run_window_offscreen(m_config) != 0);
    tb->addWidget(m_offscreenCb);

    // Infinite
    m_infiniteCb = new CheckBox("无限");
    m_infiniteCb->setChecked(config_get_infinite_loop(m_config) != 0);
    connect(m_infiniteCb, &QCheckBox::toggled, this, [this](bool checked) {
        m_repeatSpin->setEnabled(!checked);
        if (checked) {
            m_statusLabel->setText("无限循环模式");
        }
    });
    tb->addWidget(m_infiniteCb);

    // Timeout
    tb->addWidget(new BodyLabel("超时"));
    m_timeoutSpin = new SpinBox();
    m_timeoutSpin->setRange(0, 3600);
    m_timeoutSpin->setValue(static_cast<int>(config_get_timeout_seconds(m_config)));
    m_timeoutSpin->setSuffix("s");
    m_timeoutSpin->setSpecialValueText("∞");
    m_timeoutSpin->setFixedWidth(76);
    m_timeoutSpin->setFixedHeight(28);
    tb->addWidget(m_timeoutSpin);
    m_repeatSpin->setEnabled(!m_infiniteCb->isChecked());

    tb->addStretch();

    // Run button (PrimaryPushButton with icon)
    m_runBtn = new PrimaryPushButton("运行", Fluent::icon(FIT::PLAY));
    m_runBtn->setFixedHeight(28);
    connect(m_runBtn, &QPushButton::clicked, this, &MainWindow::runScript);
    tb->addWidget(m_runBtn);

    // Pause button
    m_pauseBtn = new PushButton("暂停", Fluent::icon(FIT::PAUSE));
    m_pauseBtn->setFixedHeight(28);
    m_pauseBtn->setEnabled(false);
    connect(m_pauseBtn, &QPushButton::clicked, this, &MainWindow::pauseScript);
    tb->addWidget(m_pauseBtn);

    // Stop button
    m_stopBtn = new PushButton("停止", Fluent::icon(FIT::CANCEL));
    m_stopBtn->setFixedHeight(28);
    m_stopBtn->setEnabled(false);
    connect(m_stopBtn, &QPushButton::clicked, this, &MainWindow::stopScript);
    tb->addWidget(m_stopBtn);

    root->addWidget(toolbar);

    // ===== 3-column layout =====
    auto* columns = new QHBoxLayout();
    columns->setSpacing(8);

    // --- Left Panel (AutomatePanel) ---
    auto* leftPanel = new QWidget();
    leftPanel->setMinimumWidth(260);
    leftPanel->setMaximumWidth(320);

    auto* leftLayout = new QVBoxLayout(leftPanel);
    leftLayout->setContentsMargins(0, 0, 0, 0);
    leftLayout->setSpacing(0);

    m_leftStack = new QStackedWidget();
    m_actionPanel = new ActionPanel();
    m_recorderPanel = new RecorderPanel();
    m_leftStack->addWidget(m_actionPanel);
    m_leftStack->addWidget(m_recorderPanel);
    leftLayout->addWidget(m_leftStack, 1);

    // SegmentedWidget for switching (matching Python: SegmentedWidget)
    m_leftSegment = new Pivot();
    m_leftSegment->addItem("actions", "操作库");
    m_leftSegment->addItem("recorder", "录制");
    connect(m_leftSegment, &Pivot::currentRouteKeyChanged, this, [this](const QString& key) {
        if (key == "recorder") {
            m_leftStack->setCurrentWidget(m_recorderPanel);
        } else {
            m_leftStack->setCurrentWidget(m_actionPanel);
        }
    });
    m_leftSegment->setCurrentItem("actions");
    leftLayout->addWidget(m_leftSegment);

    columns->addWidget(leftPanel);

    // --- Center Panel (AutomatePanel with canvas=True) ---
    auto* flowPanel = new QWidget();
    auto* flowLayout = new QVBoxLayout(flowPanel);
    flowLayout->setContentsMargins(0, 0, 0, 0);
    flowLayout->setSpacing(0);
    auto* flowHeader = new QWidget();
    auto* fhLayout = new QHBoxLayout(flowHeader);
    fhLayout->setContentsMargins(12, 8, 12, 4);
    auto* flowTitle = new CaptionLabel("流程");
    flowTitle->setStyleSheet(FluentTheme::panelTitleStyle());
    fhLayout->addWidget(flowTitle);
    fhLayout->addStretch();
    flowLayout->addWidget(flowHeader);
    auto* fSep = new QFrame();
    fSep->setFixedHeight(1);
    fSep->setStyleSheet(QString("background-color: %1; border: none;").arg(FluentTheme::panelBorderColor()));
    flowLayout->addWidget(fSep);
    m_scriptEditor = new ScriptEditor();
    flowLayout->addWidget(m_scriptEditor, 1);
    columns->addWidget(flowPanel, 1);

    // --- Right Panel (AutomatePanel) ---
    auto* propsPanel = new QWidget();
    propsPanel->setMinimumWidth(280);
    propsPanel->setMaximumWidth(380);
    auto* propsLayout = new QVBoxLayout(propsPanel);
    propsLayout->setContentsMargins(0, 0, 0, 0);
    propsLayout->setSpacing(0);
    auto* propsHeader = new QWidget();
    auto* phLayout = new QHBoxLayout(propsHeader);
    phLayout->setContentsMargins(12, 8, 12, 4);
    auto* propsTitle = new CaptionLabel("属性");
    propsTitle->setStyleSheet(FluentTheme::panelTitleStyle());
    phLayout->addWidget(propsTitle);
    phLayout->addStretch();
    propsLayout->addWidget(propsHeader);
    auto* pSep = new QFrame();
    pSep->setFixedHeight(1);
    pSep->setStyleSheet(QString("background-color: %1; border: none;").arg(FluentTheme::panelBorderColor()));
    propsLayout->addWidget(pSep);
    m_propertyPanel = new PropertyPanel();
    propsLayout->addWidget(m_propertyPanel, 1);
    columns->addWidget(propsPanel);

    root->addLayout(columns, 1);

    // ===== Progress bar (matching Python) =====
    m_progressBar = new ProgressBar();
    m_progressBar->setFixedHeight(3);
    m_progressBar->setRange(0, 100);
    m_progressBar->setValue(0);
    m_progressBar->setTextVisible(false);
    m_progressBar->setVisible(false);
    root->addWidget(m_progressBar);

    // ===== Status bar (matching Python) =====
    auto* statusBarWidget = new QWidget();
    statusBarWidget->setObjectName("statusBar");
    statusBarWidget->setFixedHeight(28);
    statusBarWidget->setStyleSheet(FluentTheme::statusBarStyle());
    auto* sbLayout = new QHBoxLayout(statusBarWidget);
    sbLayout->setContentsMargins(12, 0, 12, 0);
    m_statusLabel = new BodyLabel("就绪");
    sbLayout->addWidget(m_statusLabel);
    sbLayout->addStretch();
    m_coordLabel = new BodyLabel("屏幕坐标: (0, 0)");
    sbLayout->addWidget(m_coordLabel);
    root->addWidget(statusBarWidget);
}

void MainWindow::setupCommandPage()
{
    auto* layout = new QVBoxLayout(m_commandInterface);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(16);
    m_commandPanel = new CommandManagerWidget();
    layout->addWidget(m_commandPanel);
}

void MainWindow::setupConnections()
{
    connect(m_actionPanel, &ActionPanel::actionAdded, this, &MainWindow::onActionAdded);
    connect(m_scriptEditor, &ScriptEditor::actionSelected, this, &MainWindow::onActionSelected);
    connect(m_scriptEditor, &ScriptEditor::executeSingle, this, &MainWindow::onExecuteSingle);
    connect(m_scriptEditor, &ScriptEditor::actionsChanged, this, &MainWindow::onActionsChanged);
    connect(m_propertyPanel, &PropertyPanel::actionUpdated, this, &MainWindow::onActionUpdated);
    connect(m_recorderPanel, &RecorderPanel::actionRecorded, this, &MainWindow::onActionAdded);
    connect(m_recorderPanel, &RecorderPanel::actionsCleared, m_scriptEditor, &ScriptEditor::clearActions);
}

void MainWindow::setupTray()
{
    m_trayService = new TrayService(this);
    if (m_trayService->setup(QApplication::windowIcon(), "SimpleRPA")) {
        m_trayService->show();
        connect(m_trayService, &TrayService::showWindowRequested, this, [this]() {
            showNormal(); activateWindow(); raise();
        });
        connect(m_trayService, &TrayService::runDashboardRequested,
            this, &MainWindow::runDashboardFromTray);
        connect(m_trayService, &TrayService::quitRequested, this, [this]() {
            m_allowExit = true; close();
        });
    }
}

void MainWindow::closeEvent(QCloseEvent* event)
{
    if (!m_allowExit
        && m_trayService
        && m_trayService->is_visible()
        && config_get_minimize_to_tray(m_config) != 0) {
        event->ignore();
        hide();
        return;
    }

    if (m_player) {
        player_stop(m_player);
    }
    if (m_trayService) {
        m_trayService->hide();
    }
    saveRuntimeSettings();
    event->accept();
}

void MainWindow::onActionAdded(const QString& actionJson) { m_scriptEditor->addAction(actionJson); }

void MainWindow::onActionSelected(const QString& actionJson, int index)
{
    m_selectedActionIndex = index;
    m_propertyPanel->setAction(actionJson);
}

void MainWindow::onActionUpdated(const QString& actionJson)
{
    int index = m_scriptEditor->selectedActionIndex();
    if (index < 0) {
        index = m_selectedActionIndex;
    }
    if (index >= 0) {
        m_scriptEditor->updateAction(index, actionJson);
    }
}

void MainWindow::onActionsChanged() { updateRunButtons(); }

void MainWindow::saveRuntimeSettings()
{
    if (!m_config) {
        return;
    }
    config_set_default_speed(m_config, m_speedSpin->value());
    config_set_default_repeat_count(m_config, m_repeatSpin->value());
    config_set_infinite_loop(m_config, m_infiniteCb->isChecked() ? 1 : 0);
    config_set_timeout_seconds(m_config, m_timeoutSpin->value());
    config_set_run_window_offscreen(m_config, m_offscreenCb->isChecked() ? 1 : 0);
    config_save(m_config);
}

void MainWindow::updateMousePosition()
{
    const QPoint pos = QCursor::pos();
    const int64_t hwnd = m_windowSelector ? m_windowSelector->getSelectedHwnd() : 0;
    if (hwnd) {
        const QPoint offset = m_windowSelector->getSelectedWindowOffset();
        m_coordLabel->setText(QString("屏幕: (%1, %2)  窗口: (%3, %4)")
            .arg(pos.x())
            .arg(pos.y())
            .arg(pos.x() - offset.x())
            .arg(pos.y() - offset.y()));
    } else {
        m_coordLabel->setText(QString("屏幕坐标: (%1, %2)").arg(pos.x()).arg(pos.y()));
    }
}

void MainWindow::onExecuteSingle(int index)
{
    QString json = m_scriptEditor->getCurrentActionsJson();
    if (json == "[]" || index < 0) {
        return;
    }

    if (!player_set_actions_json(m_player, json.toUtf8().constData())) {
        QMessageBox::warning(this, "错误", "动作数据格式错误，无法调试");
        return;
    }
    player_set_local_groups_json(m_player, m_scriptEditor->getLocalActionGroupsJson().toUtf8().constData());

    player_set_speed(m_player, m_speedSpin->value());
    player_set_timeout(m_player, m_timeoutSpin->value());
    int64_t hwnd = m_windowSelector->getSelectedHwnd();
    int hasOffset = 0;
    QPoint offset;
    if (hwnd) {
        offset = m_windowSelector->getSelectedWindowOffset();
        hasOffset = 1;
        player_set_window_hwnd(m_player, hwnd);
        player_set_window_title(m_player, m_windowSelector->getSelectedTitle().toUtf8().constData());
        player_set_window_offset(m_player, offset.x(), offset.y(), 1);
        player_set_window_run_mode(m_player, m_offscreenCb->isChecked()
            ? "offscreen_hidden_taskbar"
            : "normal");
    } else {
        player_set_window_hwnd(m_player, 0);
        player_set_window_title(m_player, "");
        player_set_window_offset(m_player, 0, 0, 0);
        player_set_window_run_mode(m_player, "normal");
    }

    m_statusLabel->setText(QString("正在调试第 %1 个动作...").arg(index + 1));
    m_scriptEditor->setActionRunning(index);
    const int ok = player_execute_single_action(m_player, index, offset.x(), offset.y(), hasOffset);
    m_scriptEditor->clearAllRunning();
    m_statusLabel->setText(ok ? "单步调试完成" : "单步调试失败");
    updateRunButtons();
}

void MainWindow::openScript()
{
    if (m_stacked->currentWidget() == m_dashboardPage) {
        m_dashboardPage->openListDialog();
        return;
    }

    QString fp = QFileDialog::getOpenFileName(this, "打开脚本", "",
        "RPA脚本 (*.rpa.json);;所有文件 (*)");
    if (!fp.isEmpty()) {
        char* imported = exporter_import_from_json(fp.toUtf8().constData());
        if (!imported) {
            QMessageBox::warning(this, "打开失败", "无法导入脚本");
            return;
        }

        QJsonDocument doc = QJsonDocument::fromJson(QByteArray(imported));
        action_free_string(imported);
        QJsonObject obj = doc.object();
        if (!obj["success"].toBool(false)) {
            QMessageBox::warning(this, "打开失败", obj["message"].toString("脚本格式错误"));
            return;
        }

        m_scriptEditor->setActions(QString::fromUtf8(QJsonDocument(obj["actions"].toArray()).toJson()));
        QJsonValue localGroups = obj.value("local_action_groups");
        m_scriptEditor->setLocalActionGroupsJson(localGroups.isObject()
            ? QString::fromUtf8(QJsonDocument(localGroups.toObject()).toJson(QJsonDocument::Compact))
            : "{}");
        m_scriptEditor->setCurrentTabName(QFileInfo(fp).baseName());
    }
}

void MainWindow::saveScript()
{
    if (m_stacked->currentWidget() == m_dashboardPage) {
        m_dashboardPage->saveListDialog();
        return;
    }

    const QString defaultName = m_scriptEditor->currentTabName().isEmpty()
        ? QString()
        : QString("%1.rpa.json").arg(m_scriptEditor->currentTabName());
    QString fp = QFileDialog::getSaveFileName(this, "保存脚本", defaultName, "RPA脚本 (*.rpa.json)");
    if (!fp.isEmpty()) {
        if (!fp.endsWith(".json")) fp += ".json";
        exporter_set_local_groups_json(m_exporter,
            m_scriptEditor->getLocalActionGroupsJson().toUtf8().constData());
        exporter_export_to_json(m_exporter,
            m_scriptEditor->getCurrentActionsJson().toUtf8().constData(),
            fp.toUtf8().constData());
    }
}

void MainWindow::exportPython()
{
    if (m_stacked->currentWidget() == m_dashboardPage) {
        m_dashboardPage->exportPython();
        return;
    }

    const QString defaultName = m_scriptEditor->currentTabName().isEmpty()
        ? QString()
        : QString("%1.py").arg(m_scriptEditor->currentTabName());
    QString fp = QFileDialog::getSaveFileName(this, "导出", defaultName, "Python (*.py)");
    if (!fp.isEmpty()) {
        if (!fp.endsWith(".py")) fp += ".py";
        exporter_set_local_groups_json(m_exporter,
            m_scriptEditor->getLocalActionGroupsJson().toUtf8().constData());
        exporter_export_to_python(m_exporter,
            m_scriptEditor->getCurrentActionsJson().toUtf8().constData(),
            fp.toUtf8().constData());
    }
}

void MainWindow::runDashboardFromTray()
{
    showNormal();
    activateWindow();
    raise();
    m_stacked->setCurrentWidget(m_dashboardPage);
    m_navPanel->setCurrentItem("dashboard");
    m_dashboardPage->runAllScripts();
}

void MainWindow::runScript()
{
    QString json = m_scriptEditor->getCurrentActionsJson();
    if (json == "[]") return;

    const int totalActions = QJsonDocument::fromJson(json.toUtf8()).array().size();
    if (!player_set_actions_json(m_player, json.toUtf8().constData())) {
        QMessageBox::warning(this, "错误", "动作数据格式错误，无法运行");
        return;
    }
    player_set_local_groups_json(m_player, m_scriptEditor->getLocalActionGroupsJson().toUtf8().constData());
    player_set_speed(m_player, m_speedSpin->value());
    player_set_repeat_count(m_player, m_repeatSpin->value());
    player_set_infinite_loop(m_player, m_infiniteCb->isChecked() ? 1 : 0);
    player_set_timeout(m_player, m_timeoutSpin->value());
    player_set_event_callback(m_player, &MainWindow::handlePlayerEvent, this);

    saveRuntimeSettings();

    int64_t hwnd = m_windowSelector->getSelectedHwnd();
    if (hwnd) {
        QPoint offset = m_windowSelector->getSelectedWindowOffset();
        player_set_window_hwnd(m_player, hwnd);
        player_set_window_title(m_player, m_windowSelector->getSelectedTitle().toUtf8().constData());
        player_set_window_offset(m_player, offset.x(), offset.y(), 1);
        player_set_window_run_mode(m_player, m_offscreenCb->isChecked()
            ? "offscreen_hidden_taskbar"
            : "normal");
    } else {
        player_set_window_hwnd(m_player, 0);
        player_set_window_title(m_player, "");
        player_set_window_offset(m_player, 0, 0, 0);
        player_set_window_run_mode(m_player, "normal");
    }

    m_runBtn->setEnabled(false);
    m_pauseBtn->setEnabled(true);
    m_stopBtn->setEnabled(true);
    if (m_infiniteCb->isChecked()) {
        m_progressBar->setRange(0, 0);
    } else {
        m_progressBar->setRange(0, std::max(1, totalActions * m_repeatSpin->value()));
        m_progressBar->setValue(0);
    }
    m_progressBar->setVisible(true);
    m_statusLabel->setText(m_infiniteCb->isChecked()
        ? QString("开始执行 %1 个动作 (无限循环)...").arg(totalActions)
        : QString("开始执行 %1 个动作，共 %2 轮...")
              .arg(totalActions)
              .arg(m_repeatSpin->value()));
    player_play(m_player);
}

void MainWindow::pauseScript()
{
    player_toggle_pause(m_player);
    updateRunButtons();
}

void MainWindow::stopScript()
{
    player_stop(m_player);
    m_progressBar->setVisible(false);
    updateRunButtons();
}

void MainWindow::updateRunButtons()
{
    int state = player_get_state(m_player);
    bool running = (state == 1 || state == 2);
    m_runBtn->setEnabled(!running);
    m_pauseBtn->setEnabled(running);
    m_stopBtn->setEnabled(running);
    if (state != 1 && state != 2) {
        m_progressBar->setVisible(false);
    }
}

void MainWindow::handlePlayerEvent(int event, int index, int total, int repeat, int value, void* userData)
{
    auto* window = static_cast<MainWindow*>(userData);
    if (!window) {
        return;
    }

    QMetaObject::invokeMethod(window, [window, event, index, total, repeat, value]() {
        window->onPlayerEvent(event, index, total, repeat, value);
    }, Qt::QueuedConnection);
}

void MainWindow::onPlayerEvent(int event, int index, int total, int repeat, int value)
{
    switch (event) {
    case PlayerEventActionStart:
        if (index >= 0) {
            m_scriptEditor->setActionRunning(index);
            m_statusLabel->setText(QString("正在执行第 %1 / %2 个动作").arg(index + 1).arg(total));
        }
        break;
    case PlayerEventActionEnd:
        if (index >= 0 && value == 0) {
            m_statusLabel->setText(QString("第 %1 个动作执行失败").arg(index + 1));
        }
        break;
    case PlayerEventProgress:
        if (m_progressBar->maximum() > 0 && total > 0 && index >= 0) {
            const int completed = repeat * total + index + 1;
            m_progressBar->setValue(std::min(completed, m_progressBar->maximum()));
        }
        break;
    case PlayerEventStateChanged:
        if (value == 2) {
            m_statusLabel->setText("已暂停");
        } else if (value == 1) {
            m_statusLabel->setText("正在运行...");
        }
        updateRunButtons();
        break;
    case PlayerEventFinished:
        m_scriptEditor->clearAllRunning();
        m_progressBar->setVisible(false);
        m_progressBar->setRange(0, 100);
        m_progressBar->setValue(0);
        m_statusLabel->setText(value != 0 ? "执行完成" : "执行已停止");
        updateRunButtons();
        break;
    default:
        break;
    }
}
