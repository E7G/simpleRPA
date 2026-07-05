#include "main_window.h"
#include <QApplication>
#include <QScreen>
#include <QCloseEvent>
#include <QFileDialog>
#include <QMessageBox>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>

MainWindow::MainWindow(QWidget* parent) : MSFluentWindow(parent) {
    setWindowTitle("SimpleRPA");
    setMinimumSize(1280, 850);

    setupUi();
    setupNavigation();
    setupConnections();
    loadSettings();

    mousePosTimer = new QTimer(this);
    connect(mousePosTimer, &QTimer::timeout, this, &MainWindow::updateMousePosition);
    mousePosTimer->start(100);

    stateTimer = new QTimer(this);
    connect(stateTimer, &QTimer::timeout, this, &MainWindow::updateRunButtons);
    stateTimer->start(200);
}

MainWindow::~MainWindow() {
    if (playerHandle) bridge.destroyPlayer(playerHandle);
}

void MainWindow::setupUi() {
    // Dashboard
    dashboardPage = new DashboardPage();
    dashboardInterface = dashboardPage;
    addSubInterface(dashboardInterface, FluentIcon::HOME, "控制台");

    // Designer
    homeInterface = new QWidget();
    homeInterface->setObjectName("homeInterface");
    addSubInterface(homeInterface, FluentIcon::EDIT, "流程设计器");

    // Commands
    commandInterface = new QWidget();
    commandInterface->setObjectName("commandInterface");
    addSubInterface(commandInterface, FluentIcon::APPLICATION, "启动命令");

    setupDesignerInterface();
    setupCommandInterface();
}

void MainWindow::setupDesignerInterface() {
    auto* root = new QVBoxLayout(homeInterface);
    root->setContentsMargins(12, 12, 12, 8);
    root->setSpacing(8);

    // Toolbar
    auto* toolbar = new QWidget();
    auto* tb = new QHBoxLayout(toolbar);
    tb->setContentsMargins(8, 4, 8, 4);
    tb->setSpacing(6);

    windowSelector = new WindowSelector();
    windowSelector->setMinimumWidth(200);
    tb->addWidget(windowSelector);

    tb->addWidget(createVLine());

    speedSpin = new QDoubleSpinBox();
    speedSpin->setRange(0.1, 10.0);
    speedSpin->setValue(bridge.getDefaultSpeed());
    speedSpin->setSuffix("x");
    speedSpin->setFixedWidth(76);
    tb->addWidget(new QLabel("速度"));
    tb->addWidget(speedSpin);

    repeatSpin = new QSpinBox();
    repeatSpin->setRange(1, 999);
    repeatSpin->setValue(bridge.getDefaultRepeatCount());
    repeatSpin->setFixedWidth(68);
    tb->addWidget(new QLabel("重复"));
    tb->addWidget(repeatSpin);

    offscreenCb = new CheckBox("离屏后台");
    offscreenCb->setChecked(bridge.getRunWindowOffscreen());
    tb->addWidget(offscreenCb);

    infiniteCb = new CheckBox("无限");
    infiniteCb->setChecked(bridge.getInfiniteLoop());
    tb->addWidget(infiniteCb);

    timeoutSpin = new QDoubleSpinBox();
    timeoutSpin->setRange(0, 3600);
    timeoutSpin->setValue(bridge.getTimeout());
    timeoutSpin->setSuffix("s");
    timeoutSpin->setFixedWidth(76);
    tb->addWidget(new QLabel("超时"));
    tb->addWidget(timeoutSpin);

    tb->addStretch();

    runBtn = new PrimaryPushButton("运行");
    runBtn->setFixedHeight(28);
    tb->addWidget(runBtn);

    pauseBtn = new PushButton("暂停");
    pauseBtn->setFixedHeight(28);
    pauseBtn->setEnabled(false);
    tb->addWidget(pauseBtn);

    stopBtn = new PushButton("停止");
    stopBtn->setFixedHeight(28);
    stopBtn->setEnabled(false);
    tb->addWidget(stopBtn);

    root->addWidget(toolbar);

    // Columns
    auto* columns = new QHBoxLayout();
    columns->setSpacing(8);

    // Left panel
    auto* leftPanel = new QWidget();
    leftPanel->setMinimumWidth(260);
    leftPanel->setMaximumWidth(320);
    auto* leftLayout = new QVBoxLayout(leftPanel);
    leftLayout->setContentsMargins(0, 0, 0, 0);

    leftStack = new QStackedWidget();
    actionPanel = new ActionPanel();
    recorderPanel = new RecorderPanel();
    leftStack->addWidget(actionPanel);
    leftStack->addWidget(recorderPanel);
    leftLayout->addWidget(leftStack, 1);

    leftSegment = new SegmentedWidget();
    leftSegment->addItem("actions", "操作库");
    leftSegment->addItem("recorder", "录制");
    connect(leftSegment, &SegmentedWidget::currentItemChanged, [this](const QString& key) {
        if (key == "recorder") leftStack->setCurrentWidget(recorderPanel);
        else leftStack->setCurrentWidget(actionPanel);
    });
    leftLayout->insertWidget(0, leftSegment);
    columns->addWidget(leftPanel);

    // Center - Script editor
    auto* flowPanel = new QWidget();
    auto* flowLayout = new QVBoxLayout(flowPanel);
    flowLayout->setContentsMargins(0, 0, 0, 0);
    scriptEditor = new ScriptEditor();
    flowLayout->addWidget(scriptEditor);
    columns->addWidget(flowPanel, 1);

    // Right panel - Properties
    auto* propsPanel = new QWidget();
    propsPanel->setMinimumWidth(280);
    propsPanel->setMaximumWidth(380);
    auto* propsLayout = new QVBoxLayout(propsPanel);
    propsLayout->setContentsMargins(0, 0, 0, 0);
    propertyPanel = new PropertyPanel();
    propsLayout->addWidget(propertyPanel);
    columns->addWidget(propsPanel);

    root->addLayout(columns, 1);

    // Progress bar
    progressBar = new ProgressBar();
    progressBar->setFixedHeight(3);
    progressBar->setVisible(false);
    root->addWidget(progressBar);

    // Status bar
    auto* statusBar = new QWidget();
    statusBar->setFixedHeight(28);
    auto* statusLayout = new QHBoxLayout(statusBar);
    statusLayout->setContentsMargins(12, 0, 12, 0);
    statusLabel = new BodyLabel("就绪");
    coordLabel = new BodyLabel("屏幕坐标: (0, 0)");
    statusLayout->addWidget(statusLabel);
    statusLayout->addStretch();
    statusLayout->addWidget(coordLabel);
    root->addWidget(statusBar);
}

void MainWindow::setupCommandInterface() {
    auto* layout = new QVBoxLayout(commandInterface);
    layout->setContentsMargins(12, 12, 12, 12);
    commandPanel = new CommandManagerWidget();
    layout->addWidget(commandPanel);
}

void MainWindow::setupNavigation() {
    navigationInterface->addItem("open", FluentIcon::FOLDER, "打开",
        [this]() { /* TODO: open script */ }, NavigationItemPosition::BOTTOM);
    navigationInterface->addItem("save", FluentIcon::SAVE, "保存",
        [this]() { /* TODO: save script */ }, NavigationItemPosition::BOTTOM);
    navigationInterface->addItem("export", FluentIcon::SHARE, "导出",
        [this]() { /* TODO: export */ }, NavigationItemPosition::BOTTOM);
}

void MainWindow::setupConnections() {
    connect(runBtn, &QPushButton::clicked, this, &MainWindow::onRunClicked);
    connect(pauseBtn, &QPushButton::clicked, this, &MainWindow::onPauseClicked);
    connect(stopBtn, &QPushButton::clicked, this, &MainWindow::onStopClicked);
    connect(speedSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged), this, &MainWindow::onSpeedChanged);
    connect(repeatSpin, QOverload<int>::of(&QSpinBox::valueChanged), this, &MainWindow::onRepeatChanged);
    connect(infiniteCb, &QCheckBox::stateChanged, this, &MainWindow::onInfiniteChanged);
    connect(timeoutSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged), this, &MainWindow::onTimeoutChanged);
    connect(offscreenCb, &QCheckBox::stateChanged, this, [this](int) { bridge.setRunWindowOffscreen(offscreenCb->isChecked()); });
    connect(windowSelector, &WindowSelector::windowSelected, this, &MainWindow::onWindowSelected);
}

void MainWindow::loadSettings() {
    int x = 100, y = 100, w = 1280, h = 850;
    auto* screen = QApplication::primaryScreen();
    if (screen) {
        auto geo = screen->availableGeometry();
        if (x < geo.left() - 100 || x > geo.right() - 100) x = 100;
        if (y < geo.top() - 50 || y > geo.bottom() - 100) y = 100;
    }
    setGeometry(x, y, w, h);
}

void MainWindow::saveSettings() {
    bridge.setDefaultSpeed(speedSpin->value());
    bridge.setDefaultRepeatCount(repeatSpin->value());
    bridge.setInfiniteLoop(infiniteCb->isChecked());
    bridge.setTimeout(timeoutSpin->value());
    bridge.setRunWindowOffscreen(offscreenCb->isChecked());
    bridge.saveConfig();
}

void MainWindow::closeEvent(QCloseEvent* event) {
    if (playerHandle) bridge.playerStop(playerHandle);
    saveSettings();
    event->accept();
}

void MainWindow::onRunClicked() {
    if (!playerHandle) playerHandle = bridge.createPlayer();

    auto actionsJson = scriptEditor->getActionsJson();
    if (actionsJson.isEmpty() || actionsJson == "[]") {
        updateStatusBar("脚本为空，请先添加动作");
        return;
    }

    bridge.playerSetSpeed(playerHandle, speedSpin->value());
    bridge.playerSetRepeatCount(playerHandle, repeatSpin->value());
    bridge.playerSetInfiniteLoop(playerHandle, infiniteCb->isChecked());
    bridge.playerSetTimeout(playerHandle, timeoutSpin->value());

    int64_t hwnd = windowSelector->getSelectedHwnd();
    if (hwnd) {
        bridge.playerSetWindowHwnd(playerHandle, hwnd);
        bridge.playerSetWindowTitle(playerHandle, windowSelector->getSelectedTitle().toUtf8().constData());

        if (offscreenCb->isChecked()) {
            bridge.playerSetWindowRunMode(playerHandle, "offscreen_hidden_taskbar");
        }
    }

    bridge.playerPlay(playerHandle);

    runBtn->setEnabled(false);
    pauseBtn->setEnabled(true);
    stopBtn->setEnabled(true);
    progressBar->setVisible(true);
    progressBar->setValue(0);
    updateStatusBar("开始执行...");
}

void MainWindow::onPauseClicked() {
    if (!playerHandle) return;
    int state = bridge.playerGetState(playerHandle);
    if (state == 1) { // Playing
        bridge.playerPause(playerHandle);
        pauseBtn->setText("继续");
    } else if (state == 2) { // Paused
        bridge.playerResume(playerHandle);
        pauseBtn->setText("暂停");
    }
}

void MainWindow::onStopClicked() {
    if (!playerHandle) return;
    bridge.playerStop(playerHandle);
    runBtn->setEnabled(true);
    pauseBtn->setEnabled(false);
    stopBtn->setEnabled(false);
    pauseBtn->setText("暂停");
    progressBar->setVisible(false);
    updateStatusBar("已停止");
}

void MainWindow::onSpeedChanged() {
    if (playerHandle) bridge.playerSetSpeed(playerHandle, speedSpin->value());
}

void MainWindow::onRepeatChanged() {
    if (playerHandle) bridge.playerSetRepeatCount(playerHandle, repeatSpin->value());
}

void MainWindow::onInfiniteChanged(int state) {
    bool infinite = state == Qt::Checked;
    repeatSpin->setEnabled(!infinite);
    bridge.setInfiniteLoop(infinite);
    if (playerHandle) bridge.playerSetInfiniteLoop(playerHandle, infinite);
}

void MainWindow::onTimeoutChanged() {
    double val = timeoutSpin->value();
    bridge.setTimeout(val);
    if (playerHandle) bridge.playerSetTimeout(playerHandle, val);
}

void MainWindow::onWindowSelected(int64_t hwnd) {
    if (playerHandle) bridge.playerSetWindowHwnd(playerHandle, hwnd);
}

void MainWindow::onActionAdded(int type) {
    scriptEditor->addAction(type);
}

void MainWindow::onActionSelected(int index) {
    propertyPanel->setAction(scriptEditor->getActionJson(index));
}

void MainWindow::onActionsChanged() {
    scriptEditor->refreshActions();
}

void MainWindow::updateRunButtons() {
    if (!playerHandle) return;
    int state = bridge.playerGetState(playerHandle);
    bool running = (state == 1 || state == 2 || state == 3);

    runBtn->setEnabled(!running);
    pauseBtn->setEnabled(running);
    stopBtn->setEnabled(running);

    if (state == 1) { // Playing
        pauseBtn->setText("暂停");
        int idx = bridge.playerGetCurrentIndex(playerHandle);
        int total = bridge.playerGetTotalActions(playerHandle);
        int rep = bridge.playerGetCurrentRepeat(playerHandle);
        updateStatusBar(QString("第 %1 轮 | 动作 %2/%3").arg(rep + 1).arg(idx + 1).arg(total));
        progressBar->setValue(total > 0 ? (idx * 100 / total) : 0);
    } else if (state == 2) { // Paused
        pauseBtn->setText("继续");
    } else if (state == 0) { // Idle
        progressBar->setVisible(false);
        runBtn->setEnabled(true);
        pauseBtn->setEnabled(false);
        stopBtn->setEnabled(false);
        pauseBtn->setText("暂停");
    }
}

void MainWindow::updateMousePosition() {
    // TODO: implement via Rust FFI or native API
}

void MainWindow::updateStatusBar(const QString& text) {
    if (statusLabel) statusLabel->setText(text);
}

void MainWindow::onActionAdded(int /* type */) {
    // Handled by ScriptEditor
}
