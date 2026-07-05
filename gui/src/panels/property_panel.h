#ifndef PROPERTY_PANEL_H
#define PROPERTY_PANEL_H

#include <QWidget>
#include <QVBoxLayout>
#include <QFormLayout>
#include <QLineEdit>
#include <QDoubleSpinBox>
#include <QSpinBox>
#include <QCheckBox>
#include <QComboBox>
#include <QLabel>
#include <QString>

class PropertyPanel : public QWidget {
    Q_OBJECT

public:
    explicit PropertyPanel(QWidget* parent = nullptr);
    void setAction(const QString& actionJson);
    void clear();

signals:
    void actionUpdated(const QString& json);

private:
    void setupUi();
    void clearFields();

    QVBoxLayout* mainLayout;
    QLabel* titleLabel;
    QFormLayout* formLayout;
    QWidget* formWidget;

    QLineEdit* nameEdit;
    QDoubleSpinBox* delayBeforeSpin;
    QDoubleSpinBox* delayAfterSpin;
    QSpinBox* repeatSpin;
    QLineEdit* conditionEdit;
    QCheckBox* backgroundModeCb;
    QLineEdit* windowTitleEdit;

    // Common params
    QLineEdit* xEdit;
    QLineEdit* yEdit;
    QComboBox* buttonCombo;
    QLineEdit* textEdit;
    QLineEdit* keyEdit;
    QDoubleSpinBox* secondsSpin;
    QLineEdit* imagePathEdit;
    QDoubleSpinBox* confidenceSpin;

    QString currentJson;
};

#endif
