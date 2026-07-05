#pragma once

#include <QWidget>
#include <QTreeWidget>
#include <QStringList>
#include <QMap>

#include "simpleRPA_ffi.h"

class SearchLineEdit;

class ActionPanel : public QWidget
{
    Q_OBJECT

public:
    explicit ActionPanel(QWidget* parent = nullptr);

signals:
    void actionAdded(const QString& actionJson);

private:
    void setupUI();
    void loadActions();
    void rebuildTree(const QString& filter);
    void onItemDoubleClicked(QTreeWidgetItem* item, int column);

    SearchLineEdit* m_search;
    QTreeWidget* m_actionTree;
    QStringList m_categories;
    QMap<QString, QStringList> m_actionsByCategory;
    QMap<QString, QString> m_categoryLabels;
    QMap<QString, QString> m_actionLabels;
};
