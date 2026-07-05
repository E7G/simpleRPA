#include "dashboard_page.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QScrollArea>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QHeaderView>
#include <QFileInfo>
#include <QFrame>
#include <QFileDialog>
#include <QFile>
#include <QMessageBox>
#include <QUuid>
#include <QDateTime>

#include "window_selector.h"
#include "QFluent/CheckBox.h"
#include "QFluent/ComboBox.h"
#include "QFluent/Label.h"
#include "QFluent/PushButton.h"
#include "QFluent/ScrollArea.h"
#include "QFluent/SpinBox.h"
#include "QFluent/TableView.h"
#include "Theme.h"
#include "fluent_theme.h"

using FIT = Fluent::IconType;

DashboardPage::DashboardPage(QWidget* parent)
    : QWidget(parent)
    , m_windowUtils(window_utils_new())
    , m_player(player_new())
    , m_commandManager(command_manager_new())
    , m_currentRunIndex(-1)
    , m_isRunning(false)
{
    setupUI();
    refreshLaunchCommands();
    refreshWindows();

    m_refreshTimer = new QTimer(this);
    connect(m_refreshTimer, &QTimer::timeout, this, &DashboardPage::refreshWindows);
    m_refreshTimer->start(2000);

    m_playerPollTimer = new QTimer(this);
    connect(m_playerPollTimer, &QTimer::timeout, this, &DashboardPage::pollPlayerState);
    m_playerPollTimer->setInterval(200);
}

DashboardPage::~DashboardPage()
{
    if (m_player) {
        player_stop(m_player);
        player_free(m_player);
    }
    if (m_windowUtils) {
        window_utils_free(m_windowUtils);
    }
    if (m_commandManager) {
        command_manager_free(m_commandManager);
    }
}

void DashboardPage::setupUI()
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(16);

    auto* headerLayout = new QHBoxLayout();
    auto* titleCol = new QVBoxLayout();
    titleCol->setSpacing(2);
    titleCol->addWidget(new TitleLabel(QStringLiteral("\u63a7\u5236\u53f0")));
    auto* subtitleLabel = new CaptionLabel(QStringLiteral("\u7ba1\u7406\u5e76\u8fd0\u884c\u684c\u9762\u81ea\u52a8\u5316\u6d41\u7a0b"));
    subtitleLabel->setStyleSheet(FluentTheme::mutedLabelStyle());
    titleCol->addWidget(subtitleLabel);
    headerLayout->addLayout(titleCol);
    headerLayout->addStretch();

    auto* addBtn = new PrimaryPushButton(QStringLiteral("\u6dfb\u52a0\u811a\u672c"), FIT::ADD);
    addBtn->setFixedHeight(32);
    connect(addBtn, &QPushButton::clicked, this, &DashboardPage::onAddScript);
    headerLayout->addWidget(addBtn);

    m_openListBtn = new PushButton(QStringLiteral("\u6253\u5f00\u5217\u8868"), FIT::FOLDER);
    m_openListBtn->setFixedHeight(32);
    connect(m_openListBtn, &QPushButton::clicked, this, &DashboardPage::openScriptList);
    headerLayout->addWidget(m_openListBtn);

    m_saveListBtn = new PushButton(QStringLiteral("\u4fdd\u5b58\u5217\u8868"), FIT::SAVE);
    m_saveListBtn->setFixedHeight(32);
    connect(m_saveListBtn, &QPushButton::clicked, this, &DashboardPage::saveScriptList);
    headerLayout->addWidget(m_saveListBtn);

    m_clearListBtn = new PushButton(QStringLiteral("\u6e05\u7a7a"), FIT::DELETE);
    m_clearListBtn->setFixedHeight(32);
    connect(m_clearListBtn, &QPushButton::clicked, this, &DashboardPage::clearScriptList);
    headerLayout->addWidget(m_clearListBtn);

    m_runAllBtn = new PrimaryPushButton(QStringLiteral("\u8fd0\u884c\u5168\u90e8"), FIT::PLAY);
    m_runAllBtn->setFixedHeight(32);
    connect(m_runAllBtn, &QPushButton::clicked, this, &DashboardPage::runAllScripts);
    headerLayout->addWidget(m_runAllBtn);

    m_stopBtn = new PushButton(QStringLiteral("\u505c\u6b62"), FIT::CANCEL);
    m_stopBtn->setFixedHeight(32);
    m_stopBtn->setEnabled(false);
    connect(m_stopBtn, &QPushButton::clicked, this, &DashboardPage::stopRunning);
    headerLayout->addWidget(m_stopBtn);
    layout->addLayout(headerLayout);

    auto* mainHBox = new QHBoxLayout();
    mainHBox->setSpacing(20);

    auto* leftPanel = new QWidget();
    leftPanel->setStyleSheet(FluentTheme::listItemCardStyle());
    auto* leftLayout = new QVBoxLayout(leftPanel);
    leftLayout->setContentsMargins(16, 10, 16, 12);
    leftLayout->setSpacing(10);
    leftLayout->addWidget(new StrongBodyLabel(QStringLiteral("\u811a\u672c\u5217\u8868")));

    auto* scriptScroll = new ScrollArea();
    scriptScroll->setWidgetResizable(true);
    scriptScroll->setFrameShape(QFrame::NoFrame);
    auto* scriptContent = new QWidget();
    m_scriptListLayout = new QVBoxLayout(scriptContent);
    m_scriptListLayout->setContentsMargins(0, 0, 0, 0);
    m_scriptListLayout->setSpacing(8);

    m_emptyHint = new QWidget();
    auto* emptyLayout = new QVBoxLayout(m_emptyHint);
    emptyLayout->setContentsMargins(24, 48, 24, 48);
    emptyLayout->setSpacing(12);
    auto* et = new SubtitleLabel(QStringLiteral("\u6682\u65e0\u811a\u672c"));
    et->setAlignment(Qt::AlignCenter);
    emptyLayout->addWidget(et);
    auto* ed = new CaptionLabel(QStringLiteral("\u70b9\u51fb\u201c\u6dfb\u52a0\u811a\u672c\u201d\u5f00\u59cb\u521b\u5efa\u81ea\u52a8\u5316\u6d41\u7a0b"));
    ed->setAlignment(Qt::AlignCenter);
    ed->setStyleSheet(FluentTheme::mutedCaptionStyle());
    emptyLayout->addWidget(ed);
    m_scriptListLayout->addWidget(m_emptyHint);
    m_scriptListLayout->addStretch();

    scriptScroll->setWidget(scriptContent);
    leftLayout->addWidget(scriptScroll, 1);
    mainHBox->addWidget(leftPanel, 2);

    auto* rightPanel = new QWidget();
    auto* rightLayout = new QVBoxLayout(rightPanel);
    rightLayout->setContentsMargins(0, 0, 0, 0);
    rightLayout->setSpacing(12);

    auto* windowCard = new QWidget();
    windowCard->setStyleSheet(FluentTheme::listItemCardStyle());
    auto* wcLayout = new QVBoxLayout(windowCard);
    wcLayout->setContentsMargins(16, 10, 16, 12);
    wcLayout->setSpacing(8);
    wcLayout->addWidget(new StrongBodyLabel(QStringLiteral("\u76ee\u6807\u7a97\u53e3")));

    m_windowSelector = new WindowSelector();
    wcLayout->addWidget(m_windowSelector);

    auto* launchRow = new QHBoxLayout();
    launchRow->setSpacing(8);
    launchRow->addWidget(new CaptionLabel(QStringLiteral("\u542f\u52a8\u547d\u4ee4")));
    m_launchCombo = new ComboBox();
    launchRow->addWidget(m_launchCombo, 1);
    auto* refreshLaunchBtn = new PushButton(QStringLiteral("\u5237\u65b0"), FIT::SYNC);
    refreshLaunchBtn->setFixedWidth(72);
    connect(refreshLaunchBtn, &QPushButton::clicked, this, &DashboardPage::refreshLaunchCommands);
    launchRow->addWidget(refreshLaunchBtn);
    wcLayout->addLayout(launchRow);

    m_offscreenCb = new CheckBox(QStringLiteral("\u79bb\u5c4f\u540e\u53f0"));
    m_offscreenCb->setToolTip(QStringLiteral("\u5c06\u76ee\u6807\u7a97\u53e3\u79fb\u5230\u5c4f\u5e55\u5916\u5e76\u9690\u85cf\u4efb\u52a1\u680f\u56fe\u6807\uff0c\u7ed3\u675f\u540e\u81ea\u52a8\u6062\u590d"));
    wcLayout->addWidget(m_offscreenCb);

    m_windowTable = new TableWidget();
    m_windowTable->setColumnCount(3);
    m_windowTable->setHorizontalHeaderLabels({QStringLiteral("\u6807\u9898"), QStringLiteral("\u4f4d\u7f6e"), QStringLiteral("\u5927\u5c0f")});
    m_windowTable->horizontalHeader()->setStretchLastSection(true);
    m_windowTable->setEditTriggers(QTableWidget::NoEditTriggers);
    m_windowTable->setMinimumHeight(200);
    m_windowTable->setBorderVisible(true);
    m_windowTable->setBorderRadius(8);
    wcLayout->addWidget(m_windowTable);
    rightLayout->addWidget(windowCard);

    auto* statusCard = new QWidget();
    statusCard->setStyleSheet(FluentTheme::listItemCardStyle());
    auto* scLayout = new QVBoxLayout(statusCard);
    scLayout->setContentsMargins(16, 10, 16, 12);
    scLayout->setSpacing(8);
    scLayout->addWidget(new StrongBodyLabel(QStringLiteral("\u7cfb\u7edf\u72b6\u6001")));
    m_statusLabel = new BodyLabel(QStringLiteral("\u5c31\u7eea"));
    scLayout->addWidget(m_statusLabel);
    rightLayout->addWidget(statusCard);
    rightLayout->addStretch();

    mainHBox->addWidget(rightPanel, 1);
    layout->addLayout(mainHBox, 1);
}

void DashboardPage::refreshWindows()
{
    char* json = window_utils_get_all_windows_json(m_windowUtils);
    if (!json) return;

    QJsonDocument doc = QJsonDocument::fromJson(QString::fromUtf8(json).toUtf8());
    window_utils_free_string(json);

    QJsonArray arr = doc.array();
    m_windowTable->setRowCount(arr.size());

    for (int i = 0; i < arr.size(); ++i) {
        QJsonObject obj = arr[i].toObject();
        m_windowTable->setItem(i, 0, new QTableWidgetItem(obj["title"].toString()));
        m_windowTable->setItem(i, 1, new QTableWidgetItem(
            QString("(%1, %2)").arg(obj["x"].toInt()).arg(obj["y"].toInt())));
        m_windowTable->setItem(i, 2, new QTableWidgetItem(
            QString("%1x%2").arg(obj["width"].toInt()).arg(obj["height"].toInt())));
    }

    if (!m_isRunning) {
        m_statusLabel->setText(QString("发现 %1 个窗口 | 就绪").arg(arr.size()));
    }
}

void DashboardPage::onAddScript()
{
    QStringList paths = QFileDialog::getOpenFileNames(
        this, "添加脚本", "", "RPA脚本 (*.rpa.json *.json);;所有文件 (*)");
    if (paths.isEmpty()) {
        return;
    }

    int added = 0;
    for (const QString& fp : paths) {
        if (appendScriptFromPath(fp)) {
            added++;
        }
    }

    if (added > 0) {
        refreshScriptList();
        m_statusLabel->setText(QString("已添加 %1 个脚本").arg(added));
    }
}

void DashboardPage::openListDialog()
{
    openScriptList();
}

void DashboardPage::saveListDialog()
{
    saveScriptList();
}

void DashboardPage::exportPython()
{
    if (m_scripts.isEmpty()) {
        QMessageBox::information(this, "提示", "请先添加脚本");
        return;
    }

    QString fp = QFileDialog::getSaveFileName(this, "导出Python脚本", "", "Python文件 (*.py)");
    if (fp.isEmpty()) {
        return;
    }
    if (!fp.endsWith(".py", Qt::CaseInsensitive)) {
        fp += ".py";
    }

    QFile file(fp);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text)) {
        QMessageBox::warning(this, "错误", QString("无法写入文件: %1").arg(fp));
        return;
    }

    file.write(generateBatchPythonCode().toUtf8());
    file.close();
    m_statusLabel->setText(QString("已导出到 %1").arg(QFileInfo(fp).fileName()));
    QMessageBox::information(this, "导出成功", QString("脚本已导出到:\n%1").arg(fp));
}

bool DashboardPage::appendScriptFromPath(const QString& filepath, const QJsonObject& savedState)
{
    char* imported = exporter_import_from_json(filepath.toUtf8().constData());
    if (!imported) {
        return false;
    }

    QJsonDocument doc = QJsonDocument::fromJson(QString::fromUtf8(imported).toUtf8());
    action_free_string(imported);

    QJsonObject obj = doc.object();
    if (!obj["success"].toBool(false)) {
        QMessageBox::warning(this, "加载失败",
            QString("%1\n%2").arg(filepath, obj["message"].toString("无法导入脚本")));
        return false;
    }

    QJsonArray actions = obj["actions"].toArray();
    if (actions.isEmpty()) {
        QMessageBox::warning(this, "加载失败", QString("%1\n脚本中没有可运行动作").arg(filepath));
        return false;
    }

    ScriptItem item;
    item.id = savedState["id"].toString(QUuid::createUuid().toString(QUuid::WithoutBraces));
    item.name = savedState["name"].toString(QFileInfo(filepath).baseName());
    item.path = filepath;
    item.actionsJson = QString::fromUtf8(QJsonDocument(actions).toJson(QJsonDocument::Compact));
    QJsonValue localGroups = savedState.value("local_action_groups");
    if (localGroups.isUndefined()) {
        localGroups = obj.value("local_action_groups");
    }
    item.localActionGroupsJson = localGroups.isObject()
        ? QString::fromUtf8(QJsonDocument(localGroups.toObject()).toJson(QJsonDocument::Compact))
        : QStringLiteral("{}");
    item.actionCount = actions.size();
    item.delayBefore = savedState["delay_before"].toDouble(0.0);
    item.repeatCount = savedState["repeat_count"].toInt(1);
    item.enabled = savedState.contains("enabled") ? savedState["enabled"].toBool(true) : true;
    m_scripts.append(item);
    return true;
}

QString DashboardPage::generateBatchPythonCode() const
{
    QStringList lines;
    lines << "#!/usr/bin/env python3";
    lines << "# -*- coding: utf-8 -*-";
    lines << "";
    lines << "\"\"\"";
    lines << "RPA Batch Script";
    lines << QString("Generated: %1").arg(QDateTime::currentDateTime().toString("yyyy-MM-dd HH:mm:ss"));
    lines << QString("Total Scripts: %1").arg(m_scripts.size());
    lines << "\"\"\"";
    lines << "";
    lines << "import pyautogui";
    lines << "import time";
    lines << "import os";
    lines << "import sys";
    lines << "";
    lines << "pyautogui.FAILSAFE = True";
    lines << "pyautogui.PAUSE = 0.1";
    lines << "";
    lines << "";
    lines << "def launch_application(command):";
    lines << "    \"\"\"启动应用程序\"\"\"";
    lines << "    import subprocess";
    lines << "    try:";
    lines << "        if os.name == 'nt':";
    lines << "            subprocess.Popen(command, shell=True)";
    lines << "        else:";
    lines << "            subprocess.Popen(command, shell=True, start_new_session=True)";
    lines << "        print(f'已执行启动命令: {command}')";
    lines << "        return True";
    lines << "    except Exception as e:";
    lines << "        print(f'启动命令执行失败: {e}')";
    lines << "        return False";
    lines << "";
    lines << "";

    for (int i = 0; i < m_scripts.size(); ++i) {
        const ScriptItem& item = m_scripts[i];
        if (!item.enabled) {
            continue;
        }
        const QString funcName = QString("script_%1_%2")
            .arg(i + 1)
            .arg(sanitizePythonIdentifier(item.name));
        lines << QString("def %1():").arg(funcName);
        lines << QString("    \"\"\"执行脚本: %1\"\"\"").arg(item.name);
        if (item.delayBefore > 0.0) {
            lines << QString("    time.sleep(%1)").arg(item.delayBefore, 0, 'g', 12);
            lines << "";
        }

        const QString actionCode = actionsToPythonCode(
            item.actionsJson,
            item.localActionGroupsJson,
            "    ");
        if (!actionCode.trimmed().isEmpty()) {
            lines << actionCode;
        } else {
            lines << "    pass";
        }
        lines << QString("    print(%1)").arg(pythonStringLiteral(QString("脚本 [%1] 执行完成").arg(item.name)));
        lines << "";
        lines << "";
    }

    lines << "def main():";
    lines << "    \"\"\"主函数：按顺序执行所有脚本\"\"\"";
    lines << "    print('开始执行批量脚本...')";
    lines << "    print(f'共 {len([s for s in scripts if s[\"enabled\"]])} 个脚本')";
    lines << "    print()";
    lines << "";

    int scriptIndex = 0;
    for (int i = 0; i < m_scripts.size(); ++i) {
        const ScriptItem& item = m_scripts[i];
        if (!item.enabled) {
            continue;
        }
        scriptIndex++;
        const QString funcName = QString("script_%1_%2")
            .arg(i + 1)
            .arg(sanitizePythonIdentifier(item.name));
        lines << QString("    print(%1)").arg(pythonStringLiteral(QString("=== 脚本 %1: %2 ===").arg(scriptIndex).arg(item.name)));
        if (item.repeatCount > 1) {
            lines << QString("    for repeat in range(%1):").arg(item.repeatCount);
            lines << QString("        print(f'  第 {repeat + 1}/%1 次')").arg(item.repeatCount);
            lines << QString("        %1()").arg(funcName);
        } else {
            lines << QString("    %1()").arg(funcName);
        }
        lines << "    print()";
    }

    lines << "    print('所有脚本执行完成!')";
    lines << "";
    lines << "";
    lines << "scripts = [";
    for (const ScriptItem& item : m_scripts) {
        lines << QString("    dict(name=%1, enabled=%2),")
            .arg(pythonStringLiteral(item.name), pythonBoolLiteral(item.enabled));
    }
    lines << "]";
    lines << "";
    lines << "";
    lines << "if __name__ == '__main__':";
    lines << "    try:";
    lines << "        main()";
    lines << "    except KeyboardInterrupt:";
    lines << "        print('\\n脚本被用户中断')";
    lines << "    except Exception as e:";
    lines << "        print(f'执行错误: {e}')";
    lines << "";

    return lines.join("\n");
}

QString DashboardPage::actionsToPythonCode(
    const QString& actionsJson,
    const QString& localGroupsJson,
    const QString& indent) const
{
    char* code = exporter_actions_to_python_code_with_groups(
        actionsJson.toUtf8().constData(),
        localGroupsJson.toUtf8().constData(),
        indent.toUtf8().constData());
    if (!code) {
        return QString();
    }
    QString result = QString::fromUtf8(code);
    action_free_string(code);
    return result;
}

QString DashboardPage::sanitizePythonIdentifier(const QString& text) const
{
    QString result;
    for (const QChar& ch : text) {
        result += (ch.isLetterOrNumber() || ch == '_') ? ch : QChar('_');
    }
    if (result.isEmpty() || result.front().isDigit()) {
        result.prepend("script_");
    }
    return result;
}

QString DashboardPage::pythonStringLiteral(const QString& text) const
{
    QString escaped = text;
    escaped.replace("\\", "\\\\");
    escaped.replace("'", "\\'");
    escaped.replace("\n", "\\n");
    escaped.replace("\r", "\\r");
    return QString("'%1'").arg(escaped);
}

QString DashboardPage::pythonBoolLiteral(bool value) const
{
    return value ? "True" : "False";
}

void DashboardPage::openScriptList()
{
    if (m_isRunning) {
        return;
    }

    QString fp = QFileDialog::getOpenFileName(this, "打开脚本列表", "", "脚本列表 (*.scripts.json);;JSON (*.json)");
    if (!fp.isEmpty()) {
        loadScriptListFromFile(fp);
    }
}

void DashboardPage::saveScriptList()
{
    if (m_currentListFile.isEmpty()) {
        m_currentListFile = QFileDialog::getSaveFileName(
            this, "保存脚本列表", "", "脚本列表 (*.scripts.json)");
    }
    if (!m_currentListFile.isEmpty()) {
        saveScriptListToFile(m_currentListFile);
    }
}

void DashboardPage::clearScriptList()
{
    if (m_isRunning || m_scripts.isEmpty()) {
        return;
    }

    if (QMessageBox::question(this, "确认清空", "确定要清空脚本列表吗？") != QMessageBox::Yes) {
        return;
    }

    m_scripts.clear();
    m_currentListFile.clear();
    refreshScriptList();
    m_statusLabel->setText("脚本列表已清空");
}

bool DashboardPage::loadScriptListFromFile(const QString& filepath)
{
    QFile file(filepath);
    if (!file.open(QIODevice::ReadOnly)) {
        QMessageBox::warning(this, "打开失败", QString("无法读取文件: %1").arg(filepath));
        return false;
    }

    QJsonParseError err;
    QJsonDocument doc = QJsonDocument::fromJson(file.readAll(), &err);
    if (err.error != QJsonParseError::NoError || !doc.isObject()) {
        QMessageBox::warning(this, "打开失败", QString("脚本列表格式错误: %1").arg(err.errorString()));
        return false;
    }

    QJsonArray scripts = doc.object()["scripts"].toArray();
    QVector<ScriptItem> oldScripts = m_scripts;
    m_scripts.clear();

    int loaded = 0;
    for (const QJsonValue& val : scripts) {
        QJsonObject obj = val.toObject();
        QString path = obj["path"].toString();
        if (path.isEmpty() || !QFileInfo::exists(path)) {
            continue;
        }
        if (appendScriptFromPath(path, obj)) {
            loaded++;
        }
    }

    if (loaded == 0 && !scripts.isEmpty()) {
        m_scripts = oldScripts;
        QMessageBox::warning(this, "打开失败", "列表中的脚本文件均无法加载");
        refreshScriptList();
        return false;
    }

    m_currentListFile = filepath;

    QJsonObject windowInfo = doc.object()["window"].toObject();
    if (!windowInfo.isEmpty() && m_windowSelector) {
        m_windowSelector->setSelectedWindow(
            windowInfo["hwnd"].toVariant().toLongLong(),
            windowInfo["title"].toString());
    }
    if (doc.object().contains("offscreen")) {
        m_offscreenCb->setChecked(doc.object()["offscreen"].toBool(false));
    }
    if (doc.object().contains("launch_command_id")) {
        setSelectedLaunchCommand(doc.object()["launch_command_id"].toString());
    }

    refreshScriptList();
    m_statusLabel->setText(QString("已加载 %1 个脚本").arg(loaded));
    return true;
}

bool DashboardPage::saveScriptListToFile(const QString& filepath)
{
    QJsonArray scripts;
    for (const ScriptItem& script : m_scripts) {
        QJsonObject obj;
        obj["id"] = script.id;
        obj["name"] = script.name;
        obj["path"] = script.path;
        QJsonDocument localGroupsDoc = QJsonDocument::fromJson(script.localActionGroupsJson.toUtf8());
        if (localGroupsDoc.isObject() && !localGroupsDoc.object().isEmpty()) {
            obj["local_action_groups"] = localGroupsDoc.object();
        }
        obj["delay_before"] = script.delayBefore;
        obj["repeat_count"] = script.repeatCount;
        obj["enabled"] = script.enabled;
        scripts.append(obj);
    }

    QJsonObject root;
    root["scripts"] = scripts;
    root["version"] = "2.1";

    QJsonObject windowInfo;
    const int64_t selectedHwnd = m_windowSelector ? m_windowSelector->getSelectedHwnd() : 0;
    if (selectedHwnd) {
        windowInfo["hwnd"] = static_cast<double>(selectedHwnd);
        windowInfo["title"] = m_windowSelector->getSelectedTitle();
    }
    root["window"] = windowInfo;
    root["offscreen"] = m_offscreenCb ? m_offscreenCb->isChecked() : false;
    root["launch_command_id"] = selectedLaunchCommandId();

    QFile file(filepath);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        QMessageBox::warning(this, "保存失败", QString("无法写入文件: %1").arg(filepath));
        return false;
    }

    file.write(QJsonDocument(root).toJson(QJsonDocument::Indented));
    m_currentListFile = filepath;
    m_statusLabel->setText("脚本列表已保存");
    return true;
}

void DashboardPage::refreshLaunchCommands()
{
    if (!m_launchCombo || !m_commandManager) {
        return;
    }

    const QString current = selectedLaunchCommandId();
    m_launchCombo->clear();
    m_launchCombo->addItem(QStringLiteral("\u4e0d\u4f7f\u7528\u542f\u52a8\u547d\u4ee4"), QString());

    char* json = command_manager_get_all_json(m_commandManager);
    if (!json) {
        return;
    }

    QJsonDocument doc = QJsonDocument::fromJson(QString::fromUtf8(json).toUtf8());
    action_free_string(json);

    for (const QJsonValue& value : doc.array()) {
        QJsonObject obj = value.toObject();
        QString id = obj["id"].toString();
        QString name = obj["name"].toString();
        QString command = obj["command"].toString();
        if (!id.isEmpty()) {
            m_launchCombo->addItem(name.isEmpty() ? command : name, id);
        }
    }

    setSelectedLaunchCommand(current);
}
QString DashboardPage::selectedLaunchCommandId() const
{
    if (!m_launchCombo) {
        return QString();
    }
    return m_launchCombo->currentData().toString();
}

void DashboardPage::setSelectedLaunchCommand(const QString& commandId)
{
    if (!m_launchCombo) {
        return;
    }
    for (int i = 0; i < m_launchCombo->count(); ++i) {
        if (m_launchCombo->itemData(i).toString() == commandId) {
            m_launchCombo->setCurrentIndex(i);
            return;
        }
    }
    m_launchCombo->setCurrentIndex(0);
}

void DashboardPage::refreshScriptList()
{
    for (int i = m_scriptListLayout->count() - 1; i >= 0; --i) {
        QLayoutItem* item = m_scriptListLayout->itemAt(i);
        QWidget* widget = item ? item->widget() : nullptr;
        if (widget && widget != m_emptyHint) {
            m_scriptListLayout->removeWidget(widget);
            widget->deleteLater();
        }
    }

    m_emptyHint->setVisible(m_scripts.isEmpty());

    for (const ScriptItem& script : m_scripts) {
        auto* card = new QWidget();
        card->setStyleSheet(FluentTheme::listItemCardStyle());
        auto* cardLayout = new QHBoxLayout(card);
        cardLayout->setContentsMargins(14, 10, 12, 10);
        cardLayout->setSpacing(10);

        auto* enabledBox = new CheckBox();
        enabledBox->setChecked(script.enabled);
        enabledBox->setToolTip(QStringLiteral("\u542f\u7528/\u7981\u7528"));
        enabledBox->setEnabled(!m_isRunning);
        connect(enabledBox, &QCheckBox::toggled, this, [this, id = script.id](bool checked) {
            setScriptEnabled(id, checked);
        });
        cardLayout->addWidget(enabledBox);

        auto* infoLayout = new QVBoxLayout();
        infoLayout->setSpacing(2);
        infoLayout->addWidget(new StrongBodyLabel(script.name));
        auto* metaLabel = new CaptionLabel(QStringLiteral("%1 \u4e2a\u52a8\u4f5c | %2").arg(script.actionCount).arg(script.path));
        metaLabel->setStyleSheet(FluentTheme::mutedCaptionStyle());
        infoLayout->addWidget(metaLabel);
        cardLayout->addLayout(infoLayout, 1);

        cardLayout->addWidget(new CaptionLabel(QStringLiteral("\u5ef6\u8fdf")));
        auto* delaySpin = new DoubleSpinBox();
        delaySpin->setRange(0, 3600);
        delaySpin->setDecimals(1);
        delaySpin->setSingleStep(0.5);
        delaySpin->setSuffix("s");
        delaySpin->setValue(script.delayBefore);
        delaySpin->setFixedWidth(82);
        delaySpin->setEnabled(!m_isRunning);
        connect(delaySpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, [this, id = script.id](double value) {
                setScriptDelayBefore(id, value);
            });
        cardLayout->addWidget(delaySpin);

        cardLayout->addWidget(new CaptionLabel(QStringLiteral("\u91cd\u590d")));
        auto* repeatSpin = new SpinBox();
        repeatSpin->setRange(1, 999);
        repeatSpin->setValue(script.repeatCount);
        repeatSpin->setFixedWidth(72);
        repeatSpin->setEnabled(!m_isRunning);
        connect(repeatSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, [this, id = script.id](int value) {
                setScriptRepeatCount(id, value);
            });
        cardLayout->addWidget(repeatSpin);

        auto* runBtn = new PrimaryPushButton(QStringLiteral("\u8fd0\u884c"), FIT::PLAY);
        runBtn->setFixedHeight(28);
        runBtn->setEnabled(script.enabled && !m_isRunning);
        connect(runBtn, &QPushButton::clicked, this, [this, id = script.id]() {
            runScript(id);
        });
        cardLayout->addWidget(runBtn);

        auto* delBtn = new PushButton(QStringLiteral("\u5220\u9664"), FIT::DELETE);
        delBtn->setFixedHeight(28);
        delBtn->setEnabled(!m_isRunning);
        connect(delBtn, &QPushButton::clicked, this, [this, id = script.id]() {
            removeScript(id);
        });
        cardLayout->addWidget(delBtn);

        m_scriptListLayout->insertWidget(m_scriptListLayout->count() - 1, card);
    }
}
int DashboardPage::findScriptIndex(const QString& scriptId) const
{
    for (int i = 0; i < m_scripts.size(); ++i) {
        if (m_scripts[i].id == scriptId) {
            return i;
        }
    }
    return -1;
}

void DashboardPage::runScript(const QString& scriptId)
{
    int index = findScriptIndex(scriptId);
    if (index < 0 || m_isRunning) {
        return;
    }

    m_runQueue.clear();
    runScriptAt(index);
}

void DashboardPage::runAllScripts()
{
    if (m_isRunning) {
        return;
    }

    m_runQueue.clear();
    for (int i = 0; i < m_scripts.size(); ++i) {
        if (m_scripts[i].enabled) {
            m_runQueue.append(i);
        }
    }

    if (m_runQueue.isEmpty()) {
        QMessageBox::information(this, "提示", "请添加并启用至少一个脚本");
        return;
    }

    int next = m_runQueue.takeFirst();
    runScriptAt(next);
}

void DashboardPage::runScriptAt(int index)
{
    if (index < 0 || index >= m_scripts.size()) {
        return;
    }

    const ScriptItem& script = m_scripts[index];
    if (!script.enabled) {
        return;
    }

    if (!player_set_actions_json(m_player, script.actionsJson.toUtf8().constData())) {
        QMessageBox::warning(this, "错误", QString("脚本动作数据无效: %1").arg(script.name));
        return;
    }

    const QString launchId = selectedLaunchCommandId();
    if (!launchId.isEmpty()) {
        char* result = command_manager_check_and_launch(m_commandManager, launchId.toUtf8().constData());
        if (result) {
            QJsonDocument doc = QJsonDocument::fromJson(QString::fromUtf8(result).toUtf8());
            action_free_string(result);
            QJsonObject obj = doc.object();
            if (!obj["success"].toBool(false)) {
                QMessageBox::warning(this, "启动失败", obj["message"].toString("启动命令执行失败"));
                return;
            }
            if (m_windowSelector) {
                m_windowSelector->refreshWindows();
            }
            refreshWindows();
        }
    }

    player_set_repeat_count(m_player, script.repeatCount);
    player_set_speed(m_player, 1.0);

    const int64_t hwnd = m_windowSelector ? m_windowSelector->getSelectedHwnd() : 0;
    if (hwnd) {
        QPoint offset = m_windowSelector->getSelectedWindowOffset();
        player_set_window_hwnd(m_player, hwnd);
        player_set_window_title(m_player, m_windowSelector->getSelectedTitle().toUtf8().constData());
        player_set_window_offset(m_player, offset.x(), offset.y(), 1);
        player_set_window_run_mode(m_player, (m_offscreenCb && m_offscreenCb->isChecked())
            ? "offscreen_hidden_taskbar"
            : "normal");
    } else {
        player_set_window_hwnd(m_player, 0);
        player_set_window_title(m_player, "");
        player_set_window_offset(m_player, 0, 0, 0);
        player_set_window_run_mode(m_player, "normal");
    }

    m_currentRunIndex = index;
    m_isRunning = true;
    m_openListBtn->setEnabled(false);
    m_saveListBtn->setEnabled(false);
    m_clearListBtn->setEnabled(false);
    m_windowSelector->setEnabled(false);
    m_offscreenCb->setEnabled(false);
    m_launchCombo->setEnabled(false);
    m_runAllBtn->setEnabled(false);
    m_stopBtn->setEnabled(true);
    m_statusLabel->setText(QString("正在运行: %1").arg(script.name));
    refreshScriptList();

    const int delayMs = static_cast<int>(script.delayBefore * 1000.0);
    if (delayMs > 0) {
        m_statusLabel->setText(QString("等待 %1 秒后运行: %2").arg(script.delayBefore).arg(script.name));
        QTimer::singleShot(delayMs, this, [this]() {
            if (!m_isRunning) {
                return;
            }
            player_play(m_player);
            m_playerPollTimer->start();
        });
        return;
    }

    player_play(m_player);
    m_playerPollTimer->start();
}

void DashboardPage::stopRunning()
{
    if (!m_isRunning) {
        return;
    }

    player_stop(m_player);
    m_runQueue.clear();
    m_playerPollTimer->stop();
    m_isRunning = false;
    m_currentRunIndex = -1;
    m_openListBtn->setEnabled(true);
    m_saveListBtn->setEnabled(true);
    m_clearListBtn->setEnabled(true);
    m_windowSelector->setEnabled(true);
    m_offscreenCb->setEnabled(true);
    m_launchCombo->setEnabled(true);
    m_runAllBtn->setEnabled(true);
    m_stopBtn->setEnabled(false);
    m_statusLabel->setText("已停止");
    refreshScriptList();
}

void DashboardPage::pollPlayerState()
{
    if (!m_isRunning) {
        m_playerPollTimer->stop();
        return;
    }

    int state = player_get_state(m_player);
    if (state == 1 || state == 2) {
        return;
    }

    if (!m_runQueue.isEmpty()) {
        int next = m_runQueue.takeFirst();
        runScriptAt(next);
        return;
    }

    m_playerPollTimer->stop();
    QString finishedName;
    if (m_currentRunIndex >= 0 && m_currentRunIndex < m_scripts.size()) {
        finishedName = m_scripts[m_currentRunIndex].name;
    }
    m_isRunning = false;
    m_currentRunIndex = -1;
    m_openListBtn->setEnabled(true);
    m_saveListBtn->setEnabled(true);
    m_clearListBtn->setEnabled(true);
    m_windowSelector->setEnabled(true);
    m_offscreenCb->setEnabled(true);
    m_launchCombo->setEnabled(true);
    m_runAllBtn->setEnabled(true);
    m_stopBtn->setEnabled(false);
    m_statusLabel->setText(finishedName.isEmpty() ? "运行完成" : QString("运行完成: %1").arg(finishedName));
    refreshScriptList();
}

void DashboardPage::removeScript(const QString& scriptId)
{
    if (m_isRunning) {
        return;
    }

    int index = findScriptIndex(scriptId);
    if (index >= 0) {
        m_scripts.removeAt(index);
        refreshScriptList();
    }
}

void DashboardPage::setScriptEnabled(const QString& scriptId, bool enabled)
{
    int index = findScriptIndex(scriptId);
    if (index >= 0) {
        m_scripts[index].enabled = enabled;
    }
}

void DashboardPage::setScriptDelayBefore(const QString& scriptId, double seconds)
{
    int index = findScriptIndex(scriptId);
    if (index >= 0) {
        m_scripts[index].delayBefore = seconds;
    }
}

void DashboardPage::setScriptRepeatCount(const QString& scriptId, int repeatCount)
{
    int index = findScriptIndex(scriptId);
    if (index >= 0) {
        m_scripts[index].repeatCount = repeatCount;
    }
}
