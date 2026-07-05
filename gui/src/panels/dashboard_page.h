#ifndef DASHBOARD_PAGE_H
#define DASHBOARD_PAGE_H

#include <QWidget>
#include <QVBoxLayout>
#include <QLabel>

class DashboardPage : public QWidget {
    Q_OBJECT

public:
    explicit DashboardPage(QWidget* parent = nullptr);

private:
    void setupUi();
};

#endif
