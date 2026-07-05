#include "recorder_panel.h"

RecorderPanel::RecorderPanel(QWidget* parent) : QWidget(parent) {
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(8, 8, 8, 8);

    auto* title = new QLabel("录制");
    title->setStyleSheet("font-weight: bold; font-size: 14px;");
    layout->addWidget(title);

    startBtn = new QPushButton("开始录制");
    startBtn->setFixedHeight(32);
    connect(startBtn, &QPushButton::clicked, this, &RecorderPanel::onStartRecording);
    layout->addWidget(startBtn);

    stopBtn = new QPushButton("停止录制");
    stopBtn->setFixedHeight(32);
    stopBtn->setEnabled(false);
    connect(stopBtn, &QPushButton::clicked, this, &RecorderPanel::onStopRecording);
    layout->addWidget(stopBtn);

    statusLabel = new QLabel("未录制");
    layout->addWidget(statusLabel);

    layout->addStretch();
}

void RecorderPanel::onStartRecording() {
    recording = true;
    startBtn->setEnabled(false);
    stopBtn->setEnabled(true);
    statusLabel->setText("正在录制...");
    emit recordingStarted();
}

void RecorderPanel::onStopRecording() {
    recording = false;
    startBtn->setEnabled(true);
    stopBtn->setEnabled(false);
    statusLabel->setText("录制完成");
    emit recordingStopped();
}
