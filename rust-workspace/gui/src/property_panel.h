#pragma once

#include <QWidget>
#include <QVBoxLayout>
#include <QLabel>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMap>

class QScrollArea;
class QLineEdit;
class QDoubleSpinBox;
class QSpinBox;
class QCheckBox;
class QComboBox;
class QTextEdit;
class CheckBox;
class DoubleSpinBox;
class ScrollArea;
class SpinBox;
class StrongBodyLabel;

class PropertyPanel : public QWidget
{
    Q_OBJECT

public:
    explicit PropertyPanel(QWidget* parent = nullptr);
    void setAction(const QString& actionJson);
    void clear();

signals:
    void actionUpdated(const QString& actionJson);

private:
    void setupUI();
    void rebuildFields(const QString& actionJson);
    void addSectionTitle(const QString& text);
    void addParamRow(const QString& key, const QJsonValue& value);
    QWidget* createImageParamWidget(const QString& key, const QString& value);
    QString collectActionJson() const;
    void emitUpdated();

    ScrollArea* m_scrollArea;
    QVBoxLayout* m_fieldsLayout;
    StrongBodyLabel* m_titleLabel;
    QString m_currentActionJson;

    QMap<QString, QWidget*> m_paramWidgets;
    DoubleSpinBox* m_delayBefore;
    DoubleSpinBox* m_delayAfter;
    SpinBox* m_repeatCount;
    CheckBox* m_relativeMode;
};
