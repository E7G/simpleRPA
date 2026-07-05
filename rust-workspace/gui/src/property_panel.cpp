#include "property_panel.h"
#include <QScrollArea>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QHBoxLayout>
#include <QFormLayout>
#include <QLineEdit>
#include <QDoubleSpinBox>
#include <QSpinBox>
#include <QCheckBox>
#include <QTextEdit>
#include <QPushButton>
#include <QFileDialog>
#include <QFrame>
#include <QImage>
#include <QPixmap>
#include "QFluent/CheckBox.h"
#include "QFluent/ComboBox.h"
#include "QFluent/Label.h"
#include "QFluent/LineEdit.h"
#include "QFluent/PushButton.h"
#include "QFluent/ScrollArea.h"
#include "QFluent/SpinBox.h"
#include "QFluent/TextEdit.h"

PropertyPanel::PropertyPanel(QWidget* parent)
    : QWidget(parent)
{
    setupUI();
}

void PropertyPanel::setupUI()
{
    auto* mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(0, 0, 0, 0);
    mainLayout->setSpacing(8);

    m_titleLabel = new StrongBodyLabel(QString::fromUtf8("\u5c5e\u6027"));
    m_titleLabel->setStyleSheet(
        "font-weight: bold; font-size: 14px; color: #0078D4;"
        "padding: 4px 0px;");
    mainLayout->addWidget(m_titleLabel);

    m_scrollArea = new ScrollArea();
    m_scrollArea->setWidgetResizable(true);
    m_scrollArea->setFrameShape(QFrame::NoFrame);

    auto* fieldsWidget = new QWidget();
    m_fieldsLayout = new QVBoxLayout(fieldsWidget);
    m_fieldsLayout->setContentsMargins(0, 0, 0, 0);
    m_fieldsLayout->setSpacing(6);
    m_fieldsLayout->addStretch();
    m_scrollArea->setWidget(fieldsWidget);
    mainLayout->addWidget(m_scrollArea, 1);
}

void PropertyPanel::setAction(const QString& actionJson)
{
    m_currentActionJson = actionJson;
    rebuildFields(actionJson);
}

void PropertyPanel::clear()
{
    QLayoutItem* item;
    while ((item = m_fieldsLayout->takeAt(0)) != nullptr) {
        if (item->widget()) item->widget()->deleteLater();
        if (item->layout()) {
            QLayoutItem* subItem;
            while ((subItem = item->layout()->takeAt(0)) != nullptr) {
                if (subItem->widget()) subItem->widget()->deleteLater();
                delete subItem;
            }
        }
        delete item;
    }
    m_paramWidgets.clear();
    m_delayBefore = nullptr;
    m_delayAfter = nullptr;
    m_repeatCount = nullptr;
    m_relativeMode = nullptr;
    m_fieldsLayout->addStretch();
    m_titleLabel->setText(QString::fromUtf8("\u5c5e\u6027"));
}

void PropertyPanel::rebuildFields(const QString& actionJson)
{
    clear();
    QJsonDocument doc = QJsonDocument::fromJson(actionJson.toUtf8());
    if (!doc.isObject()) return;

    QJsonObject obj = doc.object();
    QString actionType = obj["action_type"].toString();
    m_titleLabel->setText(actionType);

    QJsonObject params = obj["params"].toObject();
    for (auto it = params.begin(); it != params.end(); ++it) {
        addParamRow(it.key(), it.value());
    }

    addSectionTitle(QString::fromUtf8("\u5ef6\u8fdf\u8bbe\u7f6e"));

    auto* delayLayout = new QHBoxLayout();

    auto* delayBeforeLabel = new BodyLabel(QString::fromUtf8("\u6267\u884c\u524d\u5ef6\u8fdf:"));
    delayBeforeLabel->setFixedWidth(90);
    delayLayout->addWidget(delayBeforeLabel);

    m_delayBefore = new DoubleSpinBox();
    m_delayBefore->setRange(0, 99999);
    m_delayBefore->setSuffix(" ms");
    m_delayBefore->setValue(obj["delay_before"].toDouble() * 1000.0);
    delayLayout->addWidget(m_delayBefore);

    auto* delayAfterLabel = new BodyLabel(QString::fromUtf8("\u6267\u884c\u540e\u5ef6\u8fdf:"));
    delayAfterLabel->setFixedWidth(90);
    delayLayout->addWidget(delayAfterLabel);

    m_delayAfter = new DoubleSpinBox();
    m_delayAfter->setRange(0, 99999);
    m_delayAfter->setSuffix(" ms");
    m_delayAfter->setValue(obj["delay_after"].toDouble() * 1000.0);
    delayLayout->addWidget(m_delayAfter);

    m_fieldsLayout->addLayout(delayLayout);

    addSectionTitle(QString::fromUtf8("\u91cd\u590d\u4e0e\u6a21\u5f0f"));

    auto* repeatLayout = new QHBoxLayout();

    auto* repeatLabel = new BodyLabel(QString::fromUtf8("\u91cd\u590d\u6b21\u6570:"));
    repeatLabel->setFixedWidth(90);
    repeatLayout->addWidget(repeatLabel);

    m_repeatCount = new SpinBox();
    m_repeatCount->setRange(0, 9999);
    m_repeatCount->setValue(obj["repeat_count"].toInt(1));
    repeatLayout->addWidget(m_repeatCount);

    m_relativeMode = new CheckBox(QString::fromUtf8("\u7a97\u53e3\u5185\u76f8\u5bf9\u6a21\u5f0f"));
    m_relativeMode->setChecked(obj["use_relative_coords"].toBool(false));
    repeatLayout->addWidget(m_relativeMode);
    repeatLayout->addStretch();

    m_fieldsLayout->addLayout(repeatLayout);

    connect(m_delayBefore, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
        this, &PropertyPanel::emitUpdated);
    connect(m_delayAfter, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
        this, &PropertyPanel::emitUpdated);
    connect(m_repeatCount, QOverload<int>::of(&QSpinBox::valueChanged),
        this, &PropertyPanel::emitUpdated);
    connect(m_relativeMode, &QCheckBox::toggled,
        this, &PropertyPanel::emitUpdated);
}

void PropertyPanel::addSectionTitle(const QString& text)
{
    auto* sep = new QFrame();
    sep->setFrameShape(QFrame::HLine);
    sep->setStyleSheet("color: rgba(0,0,0,0.08);");
    m_fieldsLayout->addWidget(sep);

    auto* label = new StrongBodyLabel(text);
    label->setStyleSheet(
        "font-size: 12px; font-weight: bold; color: #666;"
        "padding: 4px 0px 2px 0px;");
    m_fieldsLayout->addWidget(label);
}

void PropertyPanel::addParamRow(const QString& key, const QJsonValue& value)
{
    auto* rowLayout = new QHBoxLayout();
    rowLayout->setContentsMargins(0, 0, 0, 0);

    auto* label = new BodyLabel(key);
    label->setFixedWidth(100);
    label->setStyleSheet("font-size: 12px;");
    rowLayout->addWidget(label);

    if (key == "button") {
        auto* combo = new ComboBox();
        combo->addItem("left");
        combo->addItem("right");
        combo->addItem("middle");
        combo->setCurrentText(value.toString("left"));
        rowLayout->addWidget(combo);
        m_paramWidgets[key] = combo;
        connect(combo, &ComboBox::currentTextChanged,
            this, &PropertyPanel::emitUpdated);
    }
    else if (key == "image_path") {
        auto* imageWidget = createImageParamWidget(key, value.toString());
        rowLayout->addWidget(imageWidget);
        m_paramWidgets[key] = imageWidget;
    }
    else if (key == "key") {
        auto* edit = new LineEdit();
        edit->setText(value.toString());
        edit->setPlaceholderText(QString::fromUtf8("\u8f93\u5165\u6309\u952e\u540d\u79f0\uff0c\u5982 a, enter, space..."));
        rowLayout->addWidget(edit);
        m_paramWidgets[key] = edit;
        connect(edit, &QLineEdit::textChanged,
            this, &PropertyPanel::emitUpdated);
    }
    else if (key == "keys") {
        auto* textEdit = new TextEdit();
        textEdit->setPlaceholderText(QString::fromUtf8("\u9017\u53f7\u5206\u9694\u7684\u5feb\u6377\u952e\uff0c\u5982 ctrl, c"));
        textEdit->setMaximumHeight(60);
        if (value.isArray()) {
            QJsonArray arr = value.toArray();
            QStringList parts;
            for (const auto& v : arr) parts.append(v.toString());
            textEdit->setPlainText(parts.join(", "));
        } else if (value.isString()) {
            textEdit->setPlainText(value.toString());
        }
        rowLayout->addWidget(textEdit);
        m_paramWidgets[key] = textEdit;
        connect(textEdit, &QTextEdit::textChanged,
            this, &PropertyPanel::emitUpdated);
    }
    else if (key == "x" || key == "y") {
        auto* spin = new DoubleSpinBox();
        spin->setRange(-99999, 99999);
        spin->setDecimals(0);
        spin->setValue(value.toDouble(0));
        QString suffix = (key == "x") ? QString::fromUtf8(" \u50cf\u7d20 X") : QString::fromUtf8(" \u50cf\u7d20 Y");
        spin->setSuffix(suffix);
        rowLayout->addWidget(spin);
        m_paramWidgets[key] = spin;
        connect(spin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &PropertyPanel::emitUpdated);
    }
    else if (value.isDouble()) {
        bool isInt = (value.toDouble() == static_cast<int>(value.toDouble()));
        if (isInt && key != "width" && key != "height" && key != "scale") {
            auto* spin = new SpinBox();
            spin->setRange(-99999, 99999);
            spin->setValue(value.toInt());
            rowLayout->addWidget(spin);
            m_paramWidgets[key] = spin;
            connect(spin, QOverload<int>::of(&QSpinBox::valueChanged),
                this, &PropertyPanel::emitUpdated);
        } else {
            auto* spin = new DoubleSpinBox();
            spin->setRange(-99999, 99999);
            spin->setDecimals(2);
            spin->setValue(value.toDouble());
            rowLayout->addWidget(spin);
            m_paramWidgets[key] = spin;
            connect(spin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
                this, &PropertyPanel::emitUpdated);
        }
    }
    else if (value.isBool()) {
        auto* check = new CheckBox();
        check->setChecked(value.toBool());
        rowLayout->addWidget(check);
        m_paramWidgets[key] = check;
        connect(check, &QCheckBox::toggled,
            this, &PropertyPanel::emitUpdated);
    }
    else if (value.isString()) {
        auto* edit = new LineEdit();
        edit->setText(value.toString());
        rowLayout->addWidget(edit);
        m_paramWidgets[key] = edit;
        connect(edit, &QLineEdit::textChanged,
            this, &PropertyPanel::emitUpdated);
    }

    m_fieldsLayout->addLayout(rowLayout);
}

QWidget* PropertyPanel::createImageParamWidget(const QString& key, const QString& value)
{
    auto* container = new QWidget();
    auto* layout = new QHBoxLayout(container);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(4);

    auto* edit = new LineEdit();
    edit->setText(value);
    edit->setPlaceholderText(QString::fromUtf8("\u56fe\u7247\u8def\u5f84"));
    layout->addWidget(edit, 1);

    auto* browseBtn = new PushButton(QString::fromUtf8("\u6d4f\u89c8"));
    browseBtn->setFixedWidth(50);
    layout->addWidget(browseBtn);

    auto* preview = new QLabel();
    preview->setFixedSize(40, 40);
    preview->setStyleSheet("border: 1px solid #ddd; border-radius: 4px;");
    preview->setScaledContents(true);
    layout->addWidget(preview);

    if (!value.isEmpty()) {
        QPixmap pix(value);
        if (!pix.isNull()) {
            preview->setPixmap(pix);
        }
    }

    connect(browseBtn, &QPushButton::clicked, this, [this, edit, preview, key]() {
        QString file = QFileDialog::getOpenFileName(
            this, QString::fromUtf8("\u9009\u62e9\u56fe\u7247"),
            QString(),
            QString::fromUtf8("\u56fe\u7247\u6587\u4ef6 (*.png *.jpg *.jpeg *.bmp *.gif)"));
        if (!file.isEmpty()) {
            edit->setText(file);
            QPixmap pix(file);
            if (!pix.isNull()) {
                preview->setPixmap(pix);
            }
            emitUpdated();
        }
    });

    connect(edit, &QLineEdit::textChanged, this, [preview](const QString& text) {
        QPixmap pix(text);
        if (!pix.isNull()) {
            preview->setPixmap(pix);
        } else {
            preview->clear();
        }
    });

    m_paramWidgets[key] = edit;
    connect(edit, &QLineEdit::textChanged,
        this, &PropertyPanel::emitUpdated);

    return container;
}

QString PropertyPanel::collectActionJson() const
{
    QJsonDocument doc = QJsonDocument::fromJson(m_currentActionJson.toUtf8());
    if (!doc.isObject()) return m_currentActionJson;

    QJsonObject obj = doc.object();

    for (auto it = m_paramWidgets.constBegin(); it != m_paramWidgets.constEnd(); ++it) {
        QString key = it.key();
        QWidget* widget = it.value();

        QJsonObject params = obj["params"].toObject();

        if (key == "button") {
            auto* combo = qobject_cast<ComboBox*>(widget);
            if (combo) params[key] = combo->currentText();
        }
        else if (key == "image_path") {
            auto* line = widget->findChild<QLineEdit*>();
            if (line) params[key] = line->text();
        }
        else if (key == "key") {
            auto* line = qobject_cast<QLineEdit*>(widget);
            if (line) params[key] = line->text();
        }
        else if (key == "keys") {
            auto* text = qobject_cast<QTextEdit*>(widget);
            if (text) {
                params[key] = text->toPlainText().trimmed();
            }
        }
        else if (key == "x" || key == "y") {
            auto* spin = qobject_cast<QDoubleSpinBox*>(widget);
            if (spin) params[key] = static_cast<int>(spin->value());
        }
        else {
            auto* spinD = qobject_cast<QDoubleSpinBox*>(widget);
            auto* spinI = qobject_cast<QSpinBox*>(widget);
            auto* line = qobject_cast<QLineEdit*>(widget);
            auto* check = qobject_cast<QCheckBox*>(widget);

            if (spinD) {
                params[key] = spinD->value();
            } else if (spinI) {
                params[key] = spinI->value();
            } else if (check) {
                params[key] = check->isChecked();
            } else if (line) {
                params[key] = line->text();
            }
        }

        obj["params"] = params;
    }

    if (m_delayBefore) obj["delay_before"] = m_delayBefore->value() / 1000.0;
    if (m_delayAfter) obj["delay_after"] = m_delayAfter->value() / 1000.0;
    if (m_repeatCount) obj["repeat_count"] = m_repeatCount->value();
    if (m_relativeMode) obj["use_relative_coords"] = m_relativeMode->isChecked();

    return QString::fromUtf8(QJsonDocument(obj).toJson(QJsonDocument::Compact));
}

void PropertyPanel::emitUpdated()
{
    m_currentActionJson = collectActionJson();
    emit actionUpdated(m_currentActionJson);
}
