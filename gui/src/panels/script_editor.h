#ifndef SCRIPT_EDITOR_H
#define SCRIPT_EDITOR_H

#include <QWidget>
#include <QListWidget>
#include <QPushButton>
#include <QVBoxLayout>
#include <QLabel>
#include <QString>
#include <QVector>

class ScriptEditor : public QWidget {
    Q_OBJECT

public:
    explicit ScriptEditor(QWidget* parent = nullptr);

    void addAction(int type);
    void removeAction(int index);
    void refreshActions();
    QString getActionsJson();
    QString getActionJson(int index);
    int getSelectedIndex();
    void clearActions();

signals:
    void actionSelected(int index);
    void actionsChanged();
    void executeSingle(int index);

private:
    void setupUi();
    void onItemClicked(int index);

    QListWidget* actionList;
    QPushButton* deleteBtn;
    QPushButton* runSingleBtn;
    QVector<int> actionTypes;
    QVector<QString> actionJsons;
};

#endif
