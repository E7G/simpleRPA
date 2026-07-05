#include "property_panel.h"
#include <QScrollArea>
#include <QJsonDocument>
#include <QJsonObject>

PropertyPanel::PropertyPanel(QWidget* parent) : QWidget(parent) {
    mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(0, 0, 0, 0);

    titleLabel = new QLabel("属性");
    titleLabel->setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;");
    mainLayout->addWidget(titleLabel);

    setupUi();
    clear();
}

void PropertyPanel::setupUi() {
    auto* scroll = new QScrollArea();
    scroll->setWidgetResizable(true);
    formWidget = new QWidget();
    formLayout = new QFormLayout(formWidget);
    formLayout->setContentsMargins(8, 8, 8, 8);

    nameEdit = new QLineEdit();
    formLayout->addRow("名称:", nameEdit);

    delayBeforeSpin = new QDoubleSpinBox();
    delayBeforeSpin->setRange(0, 3600);
    delayBeforeSpin->setSuffix("s");
    formLayout->addRow("前置延迟:", delayBeforeSpin);

    delayAfterSpin = new QDoubleSpinBox();
    delayAfterSpin->setRange(0, 3600);
    delayAfterSpin->setSuffix("s");
    formLayout->addRow("后置延迟:", delayAfterSpin);

    repeatSpin = new QSpinBox();
    repeatSpin->setRange(1, 999);
    formLayout->addRow("重复次数:", repeatSpin);

    conditionEdit = new QLineEdit();
    conditionEdit->setPlaceholderText("例: $var_name == true");
    formLayout->addRow("条件:", conditionEdit);

    backgroundModeCb = new QCheckBox("后台模式");
    formLayout->addRow("", backgroundModeCb);

    windowTitleEdit = new QLineEdit();
    windowTitleEdit->setPlaceholderText("窗口标题关键字");
    formLayout->addRow("窗口:", windowTitleEdit);

    formLayout->addRow(new QLabel("--- 参数 ---"));

    xEdit = new QLineEdit("0");
    formLayout->addRow("X:", xEdit);

    yEdit = new QLineEdit("0");
    formLayout->addRow("Y:", yEdit);

    buttonCombo = new QComboBox();
    buttonCombo->addItems({"left", "right", "middle"});
    formLayout->addRow("按钮:", buttonCombo);

    textEdit = new QLineEdit();
    formLayout->addRow("文本:", textEdit);

    keyEdit = new QLineEdit();
    formLayout->addRow("按键:", keyEdit);

    secondsSpin = new QDoubleSpinBox();
    secondsSpin->setRange(0, 3600);
    secondsSpin->setValue(1.0);
    secondsSpin->setSuffix("s");
    formLayout->addRow("秒数:", secondsSpin);

    imagePathEdit = new QLineEdit();
    formLayout->addRow("图片路径:", imagePathEdit);

    confidenceSpin = new QDoubleSpinBox();
    confidenceSpin->setRange(0.0, 1.0);
    confidenceSpin->setValue(0.9);
    confidenceSpin->setSingleStep(0.05);
    formLayout->addRow("置信度:", confidenceSpin);

    scroll->setWidget(formWidget);
    mainLayout->addWidget(scroll, 1);
}

void PropertyPanel::setAction(const QString& actionJson) {
    currentJson = actionJson;
    QJsonDocument doc = QJsonDocument::fromJson(actionJson.toUtf8());
    QJsonObject obj = doc.object();

    nameEdit->setText(obj["name"].toString());
    delayBeforeSpin->setValue(obj["delay_before"].toDouble());
    delayAfterSpin->setValue(obj["delay_after"].toDouble());
    repeatSpin->setValue(obj["repeat_count"].toInt(1));
    conditionEdit->setText(obj["condition"].toString());
    backgroundModeCb->setChecked(obj["background_mode"].toBool());
    windowTitleEdit->setText(obj["window_title"].toString());

    QJsonObject params = obj["params"].toObject();
    xEdit->setText(QString::number(params["x"].toInt(0)));
    yEdit->setText(QString::number(params["y"].toInt(0)));

    int btnIdx = buttonCombo->findText(params["button"].toString("left"));
    if (btnIdx >= 0) buttonCombo->setCurrentIndex(btnIdx);

    textEdit->setText(params["text"].toString());
    keyEdit->setText(params["key"].toString());
    secondsSpin->setValue(params["seconds"].toDouble(1.0));
    imagePathEdit->setText(params["image_path"].toString());
    confidenceSpin->setValue(params["confidence"].toDouble(0.9));
}

void PropertyPanel::clear() {
    currentJson.clear();
    titleLabel->setText("属性");
    nameEdit->clear();
    delayBeforeSpin->setValue(0);
    delayAfterSpin->setValue(0);
    repeatSpin->setValue(1);
    conditionEdit->clear();
    backgroundModeCb->setChecked(false);
    windowTitleEdit->clear();
    xEdit->setText("0");
    yEdit->setText("0");
    buttonCombo->setCurrentIndex(0);
    textEdit->clear();
    keyEdit->clear();
    secondsSpin->setValue(1.0);
    imagePathEdit->clear();
    confidenceSpin->setValue(0.9);
}

void PropertyPanel::clearFields() {
    clear();
}
