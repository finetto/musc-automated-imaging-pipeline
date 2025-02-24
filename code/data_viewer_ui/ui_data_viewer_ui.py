# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'data_viewer_ui.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QHeaderView, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QSpacerItem,
    QTabWidget, QTableWidget, QTableWidgetItem, QWidget)

class Ui_data_viewer_ui(object):
    def setupUi(self, data_viewer_ui):
        if not data_viewer_ui.objectName():
            data_viewer_ui.setObjectName(u"data_viewer_ui")
        data_viewer_ui.resize(1500, 800)
        self.gridLayout = QGridLayout(data_viewer_ui)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 1, 2, 1, 1)

        self.pushButton_reload_db = QPushButton(data_viewer_ui)
        self.pushButton_reload_db.setObjectName(u"pushButton_reload_db")

        self.gridLayout.addWidget(self.pushButton_reload_db, 1, 1, 1, 1)

        self.tabWidget = QTabWidget(data_viewer_ui)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setTabPosition(QTabWidget.West)
        self.tab_participants = QWidget()
        self.tab_participants.setObjectName(u"tab_participants")
        self.gridLayout_5 = QGridLayout(self.tab_participants)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_5.addItem(self.horizontalSpacer_2, 1, 1, 1, 1)

        self.pushButton_new_participant = QPushButton(self.tab_participants)
        self.pushButton_new_participant.setObjectName(u"pushButton_new_participant")

        self.gridLayout_5.addWidget(self.pushButton_new_participant, 1, 0, 1, 1)

        self.tableWidget_participants = QTableWidget(self.tab_participants)
        self.tableWidget_participants.setObjectName(u"tableWidget_participants")

        self.gridLayout_5.addWidget(self.tableWidget_participants, 0, 0, 1, 2)

        self.tabWidget.addTab(self.tab_participants, "")
        self.tab_mri = QWidget()
        self.tab_mri.setObjectName(u"tab_mri")
        self.gridLayout_3 = QGridLayout(self.tab_mri)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.tabWidget_2 = QTabWidget(self.tab_mri)
        self.tabWidget_2.setObjectName(u"tabWidget_2")
        self.tab_mri_sessions = QWidget()
        self.tab_mri_sessions.setObjectName(u"tab_mri_sessions")
        self.gridLayout_4 = QGridLayout(self.tab_mri_sessions)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.tableWidget_mri_sessions = QTableWidget(self.tab_mri_sessions)
        self.tableWidget_mri_sessions.setObjectName(u"tableWidget_mri_sessions")

        self.gridLayout_4.addWidget(self.tableWidget_mri_sessions, 0, 0, 1, 1)

        self.tabWidget_2.addTab(self.tab_mri_sessions, "")
        self.tab_mri_series = QWidget()
        self.tab_mri_series.setObjectName(u"tab_mri_series")
        self.gridLayout_6 = QGridLayout(self.tab_mri_series)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.tableWidget_mri_series = QTableWidget(self.tab_mri_series)
        self.tableWidget_mri_series.setObjectName(u"tableWidget_mri_series")

        self.gridLayout_6.addWidget(self.tableWidget_mri_series, 0, 1, 1, 1)

        self.listWidget_mri_session_series = QListWidget(self.tab_mri_series)
        self.listWidget_mri_session_series.setObjectName(u"listWidget_mri_session_series")

        self.gridLayout_6.addWidget(self.listWidget_mri_session_series, 0, 0, 1, 1)

        self.gridLayout_6.setColumnStretch(0, 1)
        self.gridLayout_6.setColumnStretch(1, 3)
        self.tabWidget_2.addTab(self.tab_mri_series, "")

        self.gridLayout_3.addWidget(self.tabWidget_2, 0, 0, 1, 2)

        self.tabWidget.addTab(self.tab_mri, "")

        self.gridLayout.addWidget(self.tabWidget, 0, 1, 1, 2)


        self.retranslateUi(data_viewer_ui)

        self.tabWidget.setCurrentIndex(0)
        self.tabWidget_2.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(data_viewer_ui)
    # setupUi

    def retranslateUi(self, data_viewer_ui):
        data_viewer_ui.setWindowTitle(QCoreApplication.translate("data_viewer_ui", u"Data Viewer", None))
        self.pushButton_reload_db.setText(QCoreApplication.translate("data_viewer_ui", u"Reload DB", None))
        self.pushButton_new_participant.setText(QCoreApplication.translate("data_viewer_ui", u"New Participant", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_participants), QCoreApplication.translate("data_viewer_ui", u"Participants", None))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab_mri_sessions), QCoreApplication.translate("data_viewer_ui", u"Sessions", None))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab_mri_series), QCoreApplication.translate("data_viewer_ui", u"Series", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_mri), QCoreApplication.translate("data_viewer_ui", u"MRI", None))
    # retranslateUi

