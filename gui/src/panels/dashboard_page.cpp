#include "dashboard_page.h"

DashboardPage::DashboardPage(QWidget* parent) : QWidget(parent) {
    setupUi();
}

void DashboardPage::setupUi() {
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(24, 24, 24, 24);

    auto* title = new QLabel("控制台");
    title->setStyleSheet("font-size: 24px; font-weight: bold;");
    layout->addWidget(title);

    auto* desc = new QLabel("SimpleRPA v0.2.0 - Rust + C++/QFluentKit");
    desc->setStyleSheet("font-size: 14px; color: #666;");
    layout->addWidget(desc);

    auto* info = new QLabel(
        "功能特性:\n"
        "  - 可视化操作，无需编程基础\n"
        "  - 支持录制鼠标和键盘操作\n"
        "  - 动作组管理和循环执行\n"
        "  - 后台模式和离屏运行\n"
        "  - 脚本导出为 Python 脚本"
    );
    info->setStyleSheet("font-size: 13px; line-height: 1.5;");
    layout->addWidget(info);

    layout->addStretch();
}
