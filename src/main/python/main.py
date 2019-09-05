# -*- coding: utf-8 -*-
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from os.path import expanduser

import ffmpeg
import numpy as np
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QStringListModel, QMutexLocker, QMutex, QThread, QObject, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QCompleter
from fbs_runtime.application_context.PyQt5 import ApplicationContext

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

home = expanduser('~')


def get_video_size(filename):
    logger.info('Getting video size for {!r}'.format(filename))
    probe = ffmpeg.probe(filename)
    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    width = int(video_info['width'])
    height = int(video_info['height'])
    return width, height


def start_ffmpeg_process1(in_filename):
    logger.info('Starting ffmpeg process1')
    args = (
        ffmpeg
            .input(in_filename, allowed_media_types='video', rtsp_transport='tcp')
            # .filter('scale', 512, -1)
            .output('pipe:', format='rawvideo', pix_fmt='rgb24')
            .compile()
    )
    return subprocess.Popen(args, stdout=subprocess.PIPE)


def read_frame(process1, width, height):
    logger.debug('Reading frame')

    # Note: RGB24 == 3 bytes per pixel.
    frame_size = width * height * 3
    in_bytes = process1.stdout.read(frame_size)
    if len(in_bytes) == 0:
        frame = None
    else:
        assert len(in_bytes) == frame_size
        frame = (
            np
                .frombuffer(in_bytes, np.uint8)
                .reshape([height, width, 3])
        )
    return frame


def save_url_data(url_base):
    config_dir = os.path.join(home, 'rtsp_saved', 'config')
    os.makedirs(config_dir, exist_ok=True)
    config_fpath = os.path.join(config_dir, 'config.json')
    if os.path.exists(config_fpath):
        str_list = list(json.load(open(config_fpath)))
    else:
        str_list = []
    str_list.append(url_base.strip())
    str_list = list(set(str_list))
    json.dump(str_list, open(config_fpath, 'w'))


def get_url_data(model):
    config_dir = os.path.join(home, 'rtsp_saved', 'config')
    config_fpath = os.path.join(config_dir, 'config.json')
    if os.path.exists(config_fpath):
        str_list = json.load(open(config_fpath))
    else:
        str_list = []
    model.setStringList(str_list)


def save_mp4(video_path):
    date_now = datetime.now().strftime('%Y%m%d')
    output_dir = os.path.join(home, 'rtsp_saved', date_now)
    os.makedirs(output_dir, exist_ok=True)

    date_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_fpath = os.path.join(output_dir, 'saved_{}.mp4'.format(date_time))

    in1 = ffmpeg.input(video_path, rtsp_transport='tcp')
    v1 = in1.video
    a1 = in1.audio
    v2 = v1.filter('scale', 860, -1)
    joined = ffmpeg.concat(v2, a1, v=1, a=1).node
    out = ffmpeg.output(joined[0], joined[1], output_fpath)
    process1 = out.run_async()
    return process1


class Communicate(QObject):
    signal = pyqtSignal(str)


class VideoTimer(QThread):
    def __init__(self, frequent=20):
        QThread.__init__(self)
        self.stopped = False
        self.frequent = frequent
        self.timeSignal = Communicate()
        self.mutex = QMutex()

    def run(self):
        with QMutexLocker(self.mutex):
            self.stopped = False
        while True:
            if self.stopped:
                return
            self.timeSignal.signal.emit("1")
            time.sleep(1 / self.frequent)

    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True

    def is_stopped(self):
        with QMutexLocker(self.mutex):
            return self.stopped

    def set_fps(self, fps):
        self.frequent = fps


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('main.ui', self)
        self.button = self.findChild(QtWidgets.QPushButton, 'pushButton')
        self.button.clicked.connect(self.playButtonPressed)

        self.input = self.findChild(QtWidgets.QLineEdit, 'lineEdit')

        completer = QCompleter()
        self.input.setCompleter(completer)

        model = QStringListModel()
        completer.setModel(model)
        get_url_data(model)

        # timer 设置
        self.timer = VideoTimer()
        self.timer.timeSignal.signal[str].connect(self.show_video_images)

        #
        self.save_mp4_process = None
        self.process1 = None
        self.width, self.height = None, None

        self.show()

    def playButtonPressed(self):
        print('play text: {}'.format(self.input.text()))

        save_url_data(self.input.text())

        url_base = self.input.text().strip()
        video_path = os.path.join(url_base, "h264/ch1/sub/av_stream")
        video_path_main = os.path.join(url_base, "h264/ch1/main/av_stream")
        self.save_mp4_process = save_mp4(video_path_main)

        self.process1 = start_ffmpeg_process1(video_path)
        self.width, self.height = get_video_size(video_path)

    def show_video_images(self):
        width, height = self.width, self.height
        if True:
            if True:
                frame = read_frame(self.process1, width, height)

                temp_image = QImage(frame.flatten(), width, height, QImage.Format_RGB888)
                temp_pixmap = QPixmap.fromImage(temp_image)
                self.pictureLabel.setPixmap(temp_pixmap)

                # write_frame(process2, frame)
            else:
                print("read failed, no frame data")
                success, frame = self.playCapture.read()
                if not success and self.video_type is VideoBox.VIDEO_TYPE_OFFLINE:
                    print("play finished")  # 判断本地文件播放完毕
                    self.reset()
                    self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
                return
        else:
            print("open file or capturing device error, init again")
            self.reset()

    def exit(self):
        if self.process1:
            self.process1.terminate()
        if self.save_mp4_process:
            self.save_mp4_process.terminate()


if __name__ == '__main__':
    appctxt = ApplicationContext()  # 1. Instantiate ApplicationContext
    window = Ui()
    exit_code = appctxt.app.exec_()  # 2. Invoke appctxt.app.exec_()
    logger.info('exit_code {}'.format(exit_code))
    window.exit()
    sys.exit(exit_code)
