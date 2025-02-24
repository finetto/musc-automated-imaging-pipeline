# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'reprocess_session_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLayout,
    QPushButton, QRadioButton, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_reprocess_session_dialog(object):
    def setupUi(self, reprocess_session_dialog):
        if not reprocess_session_dialog.objectName():
            reprocess_session_dialog.setObjectName(u"reprocess_session_dialog")
        reprocess_session_dialog.setWindowModality(Qt.WindowModal)
        reprocess_session_dialog.resize(395, 212)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(reprocess_session_dialog.sizePolicy().hasHeightForWidth())
        reprocess_session_dialog.setSizePolicy(sizePolicy)
        reprocess_session_dialog.setModal(True)
        self.gridLayout = QGridLayout(reprocess_session_dialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.pushButton_ok = QPushButton(reprocess_session_dialog)
        self.pushButton_ok.setObjectName(u"pushButton_ok")

        self.gridLayout.addWidget(self.pushButton_ok, 12, 2, 1, 1)

        self.groupBox_description = QGroupBox(reprocess_session_dialog)
        self.groupBox_description.setObjectName(u"groupBox_description")
        self.horizontalLayout = QHBoxLayout(self.groupBox_description)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setSizeConstraint(QLayout.SetNoConstraint)
        self.label_5 = QLabel(self.groupBox_description)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout.addWidget(self.label_5)

        self.label_session_description = QLabel(self.groupBox_description)
        self.label_session_description.setObjectName(u"label_session_description")
        font = QFont()
        font.setBold(True)
        self.label_session_description.setFont(font)

        self.horizontalLayout.addWidget(self.label_session_description)

        self.horizontalLayout.setStretch(0, 1)
        self.horizontalLayout.setStretch(1, 2)

        self.gridLayout.addWidget(self.groupBox_description, 7, 0, 1, 3)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 8, 0, 1, 1)

        self.pushButton_cancel = QPushButton(reprocess_session_dialog)
        self.pushButton_cancel.setObjectName(u"pushButton_cancel")

        self.gridLayout.addWidget(self.pushButton_cancel, 12, 1, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 12, 0, 1, 1)

        self.groupBox_reprocess = QGroupBox(reprocess_session_dialog)
        self.groupBox_reprocess.setObjectName(u"groupBox_reprocess")
        self.gridLayout_2 = QGridLayout(self.groupBox_reprocess)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.radioButton_1 = QRadioButton(self.groupBox_reprocess)
        self.buttonGroup_reprocess = QButtonGroup(reprocess_session_dialog)
        self.buttonGroup_reprocess.setObjectName(u"buttonGroup_reprocess")
        self.buttonGroup_reprocess.addButton(self.radioButton_1)
        self.radioButton_1.setObjectName(u"radioButton_1")

        self.gridLayout_2.addWidget(self.radioButton_1, 0, 0, 1, 1)

        self.radioButton_2 = QRadioButton(self.groupBox_reprocess)
        self.buttonGroup_reprocess.addButton(self.radioButton_2)
        self.radioButton_2.setObjectName(u"radioButton_2")

        self.gridLayout_2.addWidget(self.radioButton_2, 1, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_reprocess, 10, 0, 1, 3)


        self.retranslateUi(reprocess_session_dialog)

        QMetaObject.connectSlotsByName(reprocess_session_dialog)
    # setupUi

    def retranslateUi(self, reprocess_session_dialog):
        reprocess_session_dialog.setWindowTitle(QCoreApplication.translate("reprocess_session_dialog", u"Dialog", None))
        self.pushButton_ok.setText(QCoreApplication.translate("reprocess_session_dialog", u"OK", None))
        self.groupBox_description.setTitle("")
        self.label_5.setText(QCoreApplication.translate("reprocess_session_dialog", u"Description", None))
        self.label_session_description.setText(QCoreApplication.translate("reprocess_session_dialog", u"TextLabel", None))
        self.pushButton_cancel.setText(QCoreApplication.translate("reprocess_session_dialog", u"Cancel", None))
        self.groupBox_reprocess.setTitle("")
        self.radioButton_1.setText(QCoreApplication.translate("reprocess_session_dialog", u"Rerun validation", None))
        self.radioButton_2.setText(QCoreApplication.translate("reprocess_session_dialog", u"Download and reprocess all data", None))
    # retranslateUi

