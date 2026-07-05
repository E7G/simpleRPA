#include "script_editor.h"
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>

ScriptEditor::ScriptEditor(QWidget* parent) : QWidget(parent) {
    setupUi();
}

void ScriptEditor::setupUi() {
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);

    auto* toolbar = new QHBoxLayout();
    runSingleBtn = new QPushButton("单步执行");
    runSingleBtn->setFixedHeight(28);
    connect(runSingleBtn, &QPushButton::clicked, [this]() {
        int idx = getSelectedIndex();
        if (idx >= 0) emit executeSingle(idx);
    });
    toolbar->addWidget(runSingleBtn);

    deleteBtn = new QPushButton("删除");
    deleteBtn->setFixedHeight(28);
    connect(deleteBtn, &QPushButton::clicked, [this]() {
        int idx = getSelectedIndex();
        if (idx >= 0) removeAction(idx);
    });
    toolbar->addWidget(deleteBtn);
    toolbar->addStretch();
    layout->addLayout(toolbar);

    actionList = new QListWidget();
    actionList->setDragDropMode(QAbstractItemView::InternalMove);
    connect(actionList, &QListWidget::currentRowChanged, this, &ScriptEditor::onItemClicked);
    layout->addWidget(actionList, 1);
}

static const char* ACTION_TYPE_NAMES[] = {
    "鼠标单击", "鼠标双击", "鼠标右键", "鼠标移动", "鼠标拖拽", "鼠标滚轮",
    "按键", "输入文本", "快捷键", "等待", "截图", "窗口内移动", "窗口内点击",
    "图片点击", "等待图片点击", "检查图片", "动作组引用"
};

void ScriptEditor::addAction(int type) {
    QJsonObject action;
    action["action_type"] = type;
    action["delay_before"] = 0;
    action["delay_after"] = 0;
    action["repeat_count"] = 1;
    action["use_relative_coords"] = false;
    action["background_mode"] = false;

    QJsonObject params;
    params["x"] = 0;
    params["y"] = 0;
    params["button"] = "left";
    params["clicks"] = 1;
    params["text"] = "";
    params["key"] = "";
    params["seconds"] = 1.0;
    params["image_path"] = "";
    params["confidence"] = 0.9;
    params["timeout"] = 10.0;
    action["params"] = params;

    QString json = QJsonDocument(action).toJson(QJsonDocument::Compact);
    actionTypes.append(type);
    actionJsons.append(json);

    QString name = (type >= 0 && type <= 16) ? ACTION_TYPE_NAMES[type] : "未知动作";
    int idx = actionTypes.size();
    actionList->addItem(QString("%1. %2").arg(idx).arg(name));

    emit actionsChanged();
}

void ScriptEditor::removeAction(int index) {
    if (index < 0 || index >= actionTypes.size()) return;
    actionTypes.removeAt(index);
    actionJsons.removeAt(index);
    refreshActions();
    emit actionsChanged();
}

void ScriptEditor::refreshActions() {
    actionList->clear();
    for (int i = 0; i < actionTypes.size(); ++i) {
        int type = actionTypes[i];
        QString name = (type >= 0 && type <= 16) ? ACTION_TYPE_NAMES[type] : "未知动作";
        actionList->addItem(QString("%1. %2").arg(i + 1).arg(name));
    }
}

QString ScriptEditor::getActionsJson() {
    QJsonArray arr;
    for (const auto& json : actionJsons) {
        QJsonDocument doc = QJsonDocument::fromJson(json.toUtf8());
        arr.append(doc.object());
    }
    return QJsonDocument(arr).toJson(QJsonDocument::Compact);
}

QString ScriptEditor::getActionJson(int index) {
    if (index >= 0 && index < actionJsons.size()) {
        return actionJsons[index];
    }
    return "{}";
}

int ScriptEditor::getSelectedIndex() {
    return actionList->currentRow();
}

void ScriptEditor::clearActions() {
    actionTypes.clear();
    actionJsons.clear();
    actionList->clear();
    emit actionsChanged();
}

void ScriptEditor::onItemClicked(int index) {
    if (index >= 0) emit actionSelected(index);
}
