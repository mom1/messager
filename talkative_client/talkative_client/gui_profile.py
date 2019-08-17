# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-08-14 09:16:25
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-18 00:33:13

import base64
import io
import logging
import sys
from pathlib import Path

from dynaconf import settings
from PIL import Image, ImageFilter, ImageOps
from PIL.ImageQt import ImageQt
from PyQt5 import uic
from PyQt5.QtCore import QBuffer, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from .db import User
from .jim_mes import Message

logger = logging.getLogger('gui')
if getattr(sys, 'frozen', False):
    # frozen
    cfile = Path(sys.executable).parent
else:
    cfile = Path(__file__).parent


class UserWindow(QDialog):
    """Класс окна профиля пользователя."""
    def __init__(self, parent):
        """Инициализация."""
        self.parent_gui = parent
        super().__init__()
        uic.loadUi(cfile.joinpath(Path('templates/profile.ui')), self)
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса."""
        self.messages = QMessageBox()
        user = User.by_name(settings.USER_NAME)
        if user.avatar:
            ava = QPixmap()
            ava.loadFromData(user.avatar)
            self.lblAvatar.setPixmap(ava)
        self.origin_img = self.lblAvatar.pixmap().toImage()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.buttonBox.accepted.connect(self.save_data)
        self.lblAvatar.mousePressEvent = self.choose_avatar
        param = {'username': settings.USER_NAME}
        self.lblUserName.setText(self.lblUserName.text().format(**param))
        self.setWindowTitle(self.windowTitle().format(**param))
        self.btnGrayScale.clicked.connect(lambda: self.apply_effects())
        self.btnNegative.clicked.connect(lambda: self.apply_effects(['INVERT']))
        self.btnBW.clicked.connect(lambda: self.apply_effects(['BW']))
        self.btnSepia.clicked.connect(lambda: self.apply_effects(['SEPIA']))
        self.btnEmboss.clicked.connect(lambda: self.apply_effects(['EMBOSS']))
        self.btnClear.clicked.connect(self.restore_ava)
        self.show()

    def save_data(self):
        user = User.by_name(settings.USER_NAME)
        image = Image.open(io.BytesIO(self.img_to_buff(self.lblAvatar.pixmap().toImage())))
        bimg = self.img_to_buff(ImageQt(image.convert('RGBA')))

        user.avatar = bimg
        user.save()
        image = image.resize((100, 100), Image.ANTIALIAS)
        msg = Message(**{
            settings.ACTION: settings.AVA_INFO,
            settings.SENDER: settings.USER_NAME,
            settings.DATA: base64.b64encode(bimg.toBase64()).decode('ascii'),
        })
        self.parent_gui.client.send_message(msg)

    def restore_ava(self):
        if self.origin_img:
            self.lblAvatar.setPixmap(QPixmap.fromImage(self.origin_img))

    def choose_avatar(self, event=None):
        """Выбор Авы

        Args:
            event: Имя события (default: {None})

        """

        file_name, _ = QFileDialog.getOpenFileName(self, 'Open File', '', 'Images (*.png, *.jpg)')
        if file_name:
            image = Image.open(file_name)
            image = image.resize((self.lblAvatar.height(), self.lblAvatar.width()), Image.ANTIALIAS)
            img = ImageQt(image.convert('RGBA'))
            self.lblAvatar.setPixmap(QPixmap.fromImage(img))
            self.origin_img = self.lblAvatar.pixmap().toImage()

    def make_sepia_palette(self, color):
        palette = []
        r, g, b = color
        for i in range(255):
            palette.extend((int(r * i / 255), int(g * i / 255), int(b * i / 255)))
        return palette

    def img_to_buff(self, img):
        buffer_ = QBuffer()
        buffer_.open(QBuffer.ReadWrite)
        img.save(buffer_, 'PNG')
        return buffer_.data()

    def apply_effects(self, effects=None):
        """Применяет эффект к картинке."""

        if not self.origin_img:
            return
        whitish = (255, 240, 192)
        sepia = self.make_sepia_palette(whitish)
        image = Image.open(io.BytesIO(self.img_to_buff(self.origin_img)))
        effects = effects if effects else ['GREYSCALE']
        sepi = image
        if image.mode != 'L':
            sepi = image.convert('L')
            sepi.putpalette(sepia)

        gray = ImageOps.grayscale(image)
        all_effects = {
            'BW': image.convert('L').convert('1', dither=Image.NONE),
            'BLUR': image.filter(ImageFilter.BLUR),
            'CONTOUR': image.filter(ImageFilter.CONTOUR),
            'EMBOSS': image.filter(ImageFilter.EMBOSS),
            'SMOOTH': image.filter(ImageFilter.SMOOTH),
            'FLIP': ImageOps.flip(image),
            'MIRROR': ImageOps.mirror(image),
            'INVERT': ImageOps.invert(image),
            'SOLARIZE': ImageOps.solarize(image),
            'SEPIA': sepi,
            'HULK': ImageOps.colorize(gray, (0, 0, 0, 0), '#00ff00'),
            'GREYSCALE': gray,
        }
        for effect in effects:
            image = all_effects[effect]
        img_tmp = ImageQt(image.convert('RGBA'))
        self.lblAvatar.setPixmap(QPixmap.fromImage(img_tmp))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    uw = UserWindow(app)
    sys.exit(app.exec_())
