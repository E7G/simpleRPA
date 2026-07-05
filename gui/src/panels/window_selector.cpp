#include "window_selector.h"
#include <QLabel>

WindowSelector::WindowSelector(QWidget* parent) : QWidget(parent) {
    auto* layout = new QHBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(4);

    windowCombo = new QComboBox();
    windowCombo->setMinimumWidth(180);
    windowCombo->setPlaceholderText("选择目标窗口...");
    connect(windowCombo, QOverload<int>::of(&QComboBox::currentIndexChanged), this, &WindowSelector::onSelectionChanged);
    layout->addWidget(windowCombo, 1);

    refreshBtn = new QPushButton("刷新");
    refreshBtn->setFixedWidth(48);
    connect(refreshBtn, &QPushButton::clicked, this, &WindowSelector::onRefreshClicked);
    layout->addWidget(refreshBtn);

    refreshWindows();
}

void WindowSelector::refreshWindows() {
    windowCombo->clear();
    hwnds.clear();

    // This will be populated via the bridge from main_window
    // For now, the main_window will call this
}

void WindowSelector::onRefreshClicked() {
    refreshWindows();
}

void WindowSelector::onSelectionChanged(int index) {
    if (index >= 0 && index < hwnds.size()) {
        emit windowSelected(hwnds[index]);
    }
}

int64_t WindowSelector::getSelectedHwnd() {
    int idx = windowCombo->currentIndex();
    if (idx >= 0 && idx < hwnds.size()) return hwnds[idx];
    return 0;
}

QString WindowSelector::getSelectedTitle() {
    return windowCombo->currentText();
}

void WindowSelector::setSelectedWindow(int64_t hwnd, const QString& title) {
    hwnds.append(hwnd);
    windowCombo->addItem(title);
    windowCombo->setCurrentIndex(windowCombo->count() - 1);
}
