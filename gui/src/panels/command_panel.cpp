#include "command_panel.h"

CommandManagerWidget::CommandManagerWidget(QWidget* parent) : QWidget(parent) {
    setupUi();
}

void CommandManagerWidget::setupUi() {
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);

    auto* title = new QLabel("启动命令管理");
    title->setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;");
    layout->addWidget(title);

    auto* formLayout = new QHBoxLayout();
    nameEdit = new QLineEdit();
    nameEdit->setPlaceholderText("名称");
    cmdEdit = new QLineEdit();
    cmdEdit->setPlaceholderText("启动命令");
    patternEdit = new QLineEdit();
    patternEdit->setPlaceholderText("窗口标题匹配");
    addBtn = new QPushButton("添加");
    connect(addBtn, &QPushButton::clicked, this, &CommandManagerWidget::onAddClicked);
    formLayout->addWidget(nameEdit);
    formLayout->addWidget(cmdEdit);
    formLayout->addWidget(patternEdit);
    formLayout->addWidget(addBtn);
    layout->addLayout(formLayout);

    commandTable = new QTableWidget();
    commandTable->setColumnCount(3);
    commandTable->setHorizontalHeaderLabels({"名称", "命令", "窗口匹配"});
    commandTable->horizontalHeader()->setStretchLastSection(true);
    layout->addWidget(commandTable, 1);

    refreshBtn = new QPushButton("刷新");
    connect(refreshBtn, &QPushButton::clicked, this, &CommandManagerWidget::onRefreshClicked);
    layout->addWidget(refreshBtn);

    refreshCommands();
}

void CommandManagerWidget::refreshCommands() {
    commandTable->setRowCount(0);
}

void CommandManagerWidget::onAddClicked() {
    // TODO: Add command via bridge
}

void CommandManagerWidget::onRefreshClicked() {
    refreshCommands();
}
