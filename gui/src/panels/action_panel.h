#ifndef ACTION_PANEL_H
#define ACTION_PANEL_H

#include <QWidget>
#include <QVBoxLayout>
#include <QListWidget>
#include <QPushButton>
#include <QMap>

class ActionPanel : public QWidget {
    Q_OBJECT

public:
    explicit ActionPanel(QWidget* parent = nullptr);

signals:
    void actionAdded(int type);

private:
    void setupCategories();
    QListWidget* actionList;
    QMap<QString, QList<QPair<QString, int>>> categories;
};

#endif
