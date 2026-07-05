#include "recorder_panel.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include "QFluent/CheckBox.h"
#include "QFluent/Label.h"
#include "QFluent/ListView.h"
#include "QFluent/PushButton.h"
#include "QFluent/SpinBox.h"

using FIT = Fluent::IconType;

RecorderPanel::RecorderPanel(QWidget* parent)
    : QWidget(parent)
    , m_recorder(recorder_new())
    , m_isRecording(false)
{
    setupUI();
}

void RecorderPanel::setupUI()
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(8);

    auto* btnLayout = new QHBoxLayout();
    m_recordBtn = new PrimaryPushButton("开始录制", FIT::VIDEO);
    m_recordBtn->setFixedHeight(32);
    connect(m_recordBtn, &QPushButton::clicked, this, &RecorderPanel::toggleRecording);
    btnLayout->addWidget(m_recordBtn);

    m_clearBtn = new PushButton("清除录制");
    m_clearBtn->setFixedHeight(32);
    connect(m_clearBtn, &QPushButton::clicked, this, &RecorderPanel::clearActions);
    btnLayout->addWidget(m_clearBtn);
    layout->addLayout(btnLayout);

    m_statusLabel = new StrongBodyLabel("就绪");
    m_statusLabel->setAlignment(Qt::AlignCenter);
    layout->addWidget(m_statusLabel);

    m_countLabel = new BodyLabel("已录制: 0 个动作");
    m_countLabel->setAlignment(Qt::AlignCenter);
    layout->addWidget(m_countLabel);

    layout->addWidget(new StrongBodyLabel("录制选项"));
    m_recordClickCb = new CheckBox("录制鼠标点击");
    m_recordScrollCb = new CheckBox("录制滚轮");
    m_recordKeyboardCb = new CheckBox("录制键盘");
    m_recordMoveCb = new CheckBox("录制鼠标移动");
    m_ignoreLastClickCb = new CheckBox("忽略停止录制点击");
    for (auto* cb : {m_recordClickCb, m_recordScrollCb, m_recordKeyboardCb, m_ignoreLastClickCb}) {
        cb->setChecked(true);
    }
    m_recordMoveCb->setChecked(false);
    for (auto* cb : {m_recordClickCb, m_recordScrollCb, m_recordKeyboardCb, m_recordMoveCb, m_ignoreLastClickCb}) {
        connect(cb, &QCheckBox::stateChanged, this, &RecorderPanel::updateConfig);
        layout->addWidget(cb);
    }

    layout->addWidget(new BodyLabel("最小移动距离"));
    m_minDistanceSpin = new SpinBox();
    m_minDistanceSpin->setRange(1, 100);
    m_minDistanceSpin->setValue(10);
    connect(m_minDistanceSpin, QOverload<int>::of(&QSpinBox::valueChanged), this, &RecorderPanel::updateConfig);
    layout->addWidget(m_minDistanceSpin);

    layout->addWidget(new BodyLabel("采样间隔(秒)"));
    m_intervalSpin = new DoubleSpinBox();
    m_intervalSpin->setRange(0.01, 1.0);
    m_intervalSpin->setDecimals(2);
    m_intervalSpin->setValue(0.1);
    connect(m_intervalSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged), this, &RecorderPanel::updateConfig);
    layout->addWidget(m_intervalSpin);

    m_actionList = new ListWidget();
    layout->addWidget(m_actionList, 1);
    updateConfig();
}

void RecorderPanel::toggleRecording()
{
    if (m_isRecording) {
        char* json = recorder_stop(m_recorder);
        if (json) {
            QString result = QString::fromUtf8(json);
            action_free_string(json);
            QJsonDocument doc = QJsonDocument::fromJson(result.toUtf8());
            if (doc.isArray()) {
                m_countLabel->setText(QString("已录制: %1 个动作").arg(doc.array().size()));
                for (const QJsonValue& val : doc.array()) {
                    emit actionRecorded(QString::fromUtf8(QJsonDocument(val.toObject()).toJson()));
                }
            }
        }
        m_recordBtn->setText("开始录制");
        m_statusLabel->setText("录制完成");
        m_isRecording = false;
        emit recordingStopped();
    } else {
        updateConfig();
        recorder_start(m_recorder);
        m_recordBtn->setText("停止录制");
        m_statusLabel->setText("正在录制...");
        m_isRecording = true;
        emit recordingStarted();
    }
}

void RecorderPanel::clearActions()
{
    m_actionList->clear();
    m_countLabel->setText("已录制: 0 个动作");
    emit actionsCleared();
}

void RecorderPanel::updateConfig()
{
    recorder_set_config(
        m_recorder,
        m_recordClickCb && m_recordClickCb->isChecked(),
        m_recordScrollCb && m_recordScrollCb->isChecked(),
        m_recordKeyboardCb && m_recordKeyboardCb->isChecked(),
        m_recordMoveCb && m_recordMoveCb->isChecked(),
        m_minDistanceSpin ? m_minDistanceSpin->value() : 10,
        m_intervalSpin ? m_intervalSpin->value() : 0.1,
        m_ignoreLastClickCb && m_ignoreLastClickCb->isChecked());
}
