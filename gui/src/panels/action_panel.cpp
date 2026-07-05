#include "action_panel.h"
#include <QLabel>

ActionPanel::ActionPanel(QWidget* parent) : QWidget(parent) {
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);

    auto* title = new QLabel("操作库");
    title->setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;");
    layout->addWidget(title);

    actionList = new QListWidget();
    layout->addWidget(actionList, 1);

    setupCategories();

    connect(actionList, &QListWidget::itemClicked, [this](QListWidgetItem* item) {
        int type = item->data(Qt::UserRole).toInt();
        emit actionAdded(type);
    });
}

void ActionPanel::setupCategories() {
    struct ActionDef { QString name; int type; QString category; };
    QList<ActionDef> defs = {
        {"鼠标单击", 0, "鼠标操作"},
        {"鼠标双击", 1, "鼠标操作"},
        {"鼠标右键", 2, "鼠标操作"},
        {"鼠标移动", 3, "鼠标操作"},
        {"鼠标拖拽", 4, "鼠标操作"},
        {"鼠标滚轮", 5, "鼠标操作"},
        {"按键", 6, "键盘操作"},
        {"输入文本", 7, "键盘操作"},
        {"快捷键", 8, "键盘操作"},
        {"等待", 9, "控制"},
        {"截图", 10, "其他"},
        {"窗口内移动", 11, "窗口操作"},
        {"窗口内点击", 12, "窗口操作"},
        {"图片点击", 13, "图像操作"},
        {"等待图片点击", 14, "图像操作"},
        {"检查图片", 15, "图像操作"},
        {"动作组引用", 16, "其他"},
    };

    for (const auto& def : defs) {
        auto* item = new QListWidgetItem(def.name);
        item->setData(Qt::UserRole, def.type);
        item->setToolTip(def.category);
        actionList->addItem(item);
    }
}
