# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-08-14 09:16:25
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-15 01:14:43

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
        pass

    def restore_ava(self):
        if self.origin_img:
            self.lblAvatar.setPixmap(QPixmap.fromImage(self.origin_img))

    def choose_avatar(self, event=None):
        """Выбор Авы

        Args:
            event: Имя события (default: {None})
        """
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open File', '', 'Images (*.png *.jpg)')
        if file_name:
            img = ImageQt(Image.open(file_name).convert('RGBA'))
            self.lblAvatar.setPixmap(QPixmap.fromImage(img))
            self.origin_img = self.lblAvatar.pixmap().toImage()

    def make_sepia_palette(self, color):
        palette = []
        r, g, b = color
        for i in range(255):
            palette.extend((int(r * i / 255), int(g * i / 255), int(b * i / 255)))
        return palette

    def apply_effects(self, effects=None):
        """Применяет эффект к картинке"""
        buffer_ = QBuffer()
        buffer_.open(QBuffer.ReadWrite)
        if not self.origin_img:
            return
        whitish = (255, 240, 192)
        sepia = self.make_sepia_palette(whitish)
        self.origin_img.save(buffer_, 'PNG')
        image = Image.open(io.BytesIO(buffer_.data()))
        effects = effects if effects else ['GREYSCALE']
        sepi = image
        if image.mode != 'L':
            sepi = image.convert('L')
            sepi.putpalette(sepia)

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
        }
        for effect in effects:
            gray = ImageOps.grayscale(image)
            all_effects['HULK'] = ImageOps.colorize(gray, (0, 0, 0, 0), '#00ff00')
            all_effects['GREYSCALE'] = gray
            image = all_effects[effect]
        img_tmp = ImageQt(image.convert('RGBA'))
        self.lblAvatar.setPixmap(QPixmap.fromImage(img_tmp))
        # return phedited


if __name__ == '__main__':
    app = QApplication(sys.argv)
    uw = UserWindow(app)
    sys.exit(app.exec_())