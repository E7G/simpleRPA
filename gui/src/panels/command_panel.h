#ifndef COMMAND_PANEL_H
#define COMMAND_PANEL_H

#include <QWidget>
#include <QVBoxLayout>
#include <QTableWidget>
#include <QPushButton>
#include <QLineEdit>
#include <QLabel>

class CommandManagerWidget : public QWidget {
    Q_OBJECT

public:
    explicit CommandManagerWidget(QWidget* parent = nullptr);
    void refreshCommands();

private:
    void setupUi();
    void onAddClicked();
    void onRefreshClicked();

    QTableWidget* commandTable;
    QPushButton* addBtn;
    QPushButton* refreshBtn;
    QLineEdit* nameEdit;
    QLineEdit* cmdEdit;
    QLineEdit* patternEdit;
};

#endif
