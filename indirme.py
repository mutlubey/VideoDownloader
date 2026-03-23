# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 04:10:06 2026

@author: mutlu
"""

import sys
import os
import re
import subprocess
import ffmpeg

from PyQt5.QtGui import QIcon,QFont
from PyQt5.QtCore import Qt,QTimer,pyqtSignal,QThread
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, 
    QLabel, QMessageBox,QMainWindow,QStackedWidget,QLineEdit,
    QProgressBar, QHBoxLayout,QComboBox
)
import pytubefix


def safe_filename(name):
    return re.sub( r'[\\/*?:"<>|]',"", name)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class VideoInfoThread(QThread):
    """Video bilgilerini almak için thread"""
    info_received = pyqtSignal(dict)
    error_occurred=pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            yt = pytubefix.YouTube(self.url)
            #print(yt)
            # Video bilgilerini topla
            info = {
                'title': yt.title,
                'author': yt.author,
                'length': yt.length,
                'views': yt.views,
                'description': yt.description[:500] + "..." if len(yt.description) > 500 else yt.description,
                'thumbnail_url': yt.thumbnail_url,
                'streams': []
            }
            # Mevcut stream'leri al
            for stream in yt.streams.filter(adaptive=True):
                stream_info = {
                    'itag': stream.itag,
                    'resolution': stream.resolution or 'Audio Only',
                    
                    'file_extension': stream.subtype,
                    'filesize': stream.filesize,
                    'stream': stream,
                    'title':yt.title
                }
                #print(stream)
                info['streams'].append(stream_info)

            self.info_received.emit(info)

        except Exception as e:
            self.error_occurred.emit(f"Hata: {str(e)}")


class DownloadThread(QThread):
    """İndirme işlemi için thread"""
    progress_updated = pyqtSignal(int)
    download_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, output_path, video_stream, audio_stream,mode,title):
        super().__init__()
        self.output_path    = output_path
        self.video_stream   = video_stream
        self.audio_stream   = audio_stream
        self.mode           = mode
        self.title          = title
        
    def download_mp4(self,file,audioPath,videoPath):
        AudioPath = audioPath
        VideoPath = videoPath
        dosya = file
      
        try:
            input_audio = ffmpeg.input(AudioPath)
            input_video = ffmpeg.input(VideoPath)
            
            (
                ffmpeg
                .output(input_video.video,input_audio.audio,dosya,vcodec="libx264",acodec="aac")
                .run(overwrite_output=True)
                
            )
        except Exception as e:
                 QMessageBox.critical(self, "ERROR", f"Error occured while combining !\n\n{e}")
        
        
        
    def download_mp3(self,file,audioPath):
        audio_file = audioPath
        mp3_file = file
        print("download mp3 fonksiyonu çalışıyor")
        try:
            (
             ffmpeg
             .input(audio_file)
             .output(mp3_file,format="mp3", acodec="libmp3lame",audio_bitrate="320k" )
             .run(overwrite_output = True)
            )
        except Exception as e:
            QMessageBox.critical(self, "ERROR", f"Error occured while converting!\n\n{e}")
    def run(self):   
        try:
            
            title = safe_filename(self.title)
            video_file = f"{title}_video.webm"
            audio_file = f"{title}_audio.webm"
        
            video_path = os.path.join(self.output_path, video_file)
            audio_path = os.path.join(self.output_path, audio_file)
        
            output_file = os.path.join(self.output_path, f"{title}.mp4")
            mp3_file = os.path.join(self.output_path, f"{title}.mp3")
        
        
            if self.mode == 0:
                self.video_stream.download(output_path=self.output_path, filename=video_file)
                self.audio_stream.download(output_path=self.output_path, filename=audio_file)
                print( "rgvc")
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    output_file
                    ])
        
                os.remove(video_path)
                os.remove(audio_path)
        
                self.download_completed.emit("Video hazır!")
        
            elif self.mode == 1:
                self.audio_stream.download(output_path=self.output_path, filename=audio_file)
                print("bura girdi")
                self.download_mp3(file=mp3_file,audioPath=audio_path)
                
                os.remove(audio_path)
        
                self.download_completed.emit("MP3 hazır!")
        
        except Exception as e:
            self.error_occurred.emit(f" Downloading Error: {str(e)}")

class VideoDownloader(QMainWindow):

    def __init__(self):
        super().__init__()
        self.path_input = None
        self.current_video_info = None
        self.selected_stream = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Video Download Manager")
        self.setGeometry(100, 100, 600, 700)
        self.setMinimumSize(500,600)
        self.setWindowIcon(QIcon(resource_path("icon.png")))

        # Ana widget ve layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Stacked widget - sayfa geçişleri için
        self.stacked_widget = QStackedWidget()

        # Ana layout
        main_layout = QVBoxLayout(main_widget)
        main_layout.addWidget(self.stacked_widget)

        # Sayfaları oluştur
        self.create_search_page()
        self.create_download_page()

        # İlk sayfayı göster
        self.stacked_widget.setCurrentIndex(0)

    def create_search_page(self):
        """Arama sayfası oluştur"""
        search_page =QWidget()
        layout = QVBoxLayout(search_page)

        # Başlık
        title_label = QLabel("Video Download Manager")
        title_label.setAlignment(Qt.AlignCenter)
        title_font =QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Boşluk
        layout.addStretch()

        # URL giriş alanı
        url_layout = QVBoxLayout()

        url_label = QLabel("Video Link:")
        url_label.setFont(QFont("Arial", 12))
        url_layout.addWidget(url_label)

        self.url_input =QLineEdit()
        self.url_input.setPlaceholderText(
            "https://www.video.com/watch?v=...")
        self.url_input.setFont(QFont("Arial", 11))
        self.url_input.setMinimumHeight(40)
        self.url_input.textChanged.connect(self.on_url_changed)
        url_layout.addWidget(self.url_input)

        layout.addLayout(url_layout)

        # Arama butonu
        self.search_button = QPushButton("Take Video Information")
        self.search_button.setEnabled(False)
        self.search_button.setMinimumHeight(45)
        self.search_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.search_button.setStyleSheet("""
            QPushButton:enabled {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
                border: none;
                border-radius: 5px;
            }
            QPushButton:enabled:hover {
                background-color: #45a049;
            }
        """)
        self.search_button.clicked.connect(self.search_video)
        layout.addWidget(self.search_button)

        # Boşluk
        layout.addStretch()

        self.stacked_widget.addWidget(search_page)

    def create_download_page(self):
        """İndirme sayfası oluştur"""
        download_page = QWidget()
        download_page.setMinimumHeight(600)
 
        layout = QVBoxLayout(download_page)

        # Geri butonu
        back_button = QPushButton("← Back")
        back_button.setMaximumWidth(100)
        back_button.clicked.connect(self.go_back)
        back_button.setStyleSheet("""QPushButton{
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 5px;}
            QPushButton:hover{
                background-color: #1085E2;
                color: white;
                border: none;
                border-radius: 5px;}"""
            )
        layout.addWidget(back_button)
        layout.setSpacing(10)

        # Video bilgileri alanı
        
        info_layout=QVBoxLayout()

        self.video_title = QLabel()
        self.video_title.setFont(QFont("Arial", 14,QFont.Bold))
        self.video_title.setWordWrap(True)
        self.video_title.setMinimumHeight(100)


        self.video_title.setMargin(10)

        self.video_title.setStyleSheet("""
                                       QLabel{
                                           background-color: #dddddd;
                                           border-radius:5px;
                                         }
                                       """)                        
        info_layout.addWidget(self.video_title)
        

        self.video_author = QLabel()
        self.video_author.setFont(QFont("Arial", 12))
        self.video_author.setMinimumHeight(20)
        info_layout.addWidget(self.video_author)

        self.video_stats = QLabel()
        self.video_stats.setFont(QFont("Arial", 12))
        info_layout.addWidget(self.video_stats)

        layout.addLayout(info_layout)

        # Kalite seçimi
        quality_layout = QHBoxLayout()

        quality_label = QLabel("Choose Quality:")
        quality_label.setFont(QFont("Arial", 12))
        quality_layout.addWidget(quality_label)

        self.quality_combo =QComboBox()
        self.quality_combo.setMinimumHeight(35)
        quality_layout.addWidget(self.quality_combo)

        layout.addLayout(quality_layout)
        
        # ses  Kalitesi seçimi
        audioLayout = QHBoxLayout()
        audioQuality_label = QLabel("Choose Audio Quality:")
        audioQuality_label.setFont(QFont("Arial",12))
        audioLayout.addWidget(audioQuality_label)
        
        self.audio_combo = QComboBox()
        self.audio_combo.setMinimumHeight(35)
        audioLayout.addWidget(self.audio_combo)
        
        layout.addLayout(audioLayout)

        # İndirme yolu seçimi
        path_layout = QHBoxLayout()

        path_label = QLabel("Download Path:")
        path_label.setFont(QFont("Arial", 12))
        path_layout.addWidget(path_label)

        self.path_input = QLineEdit()
        self.path_input.setText(os.path.expanduser("~/Downloads"))
        path_layout.addWidget(self.path_input)

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_folder)
        browse_button.setStyleSheet("""QPushButton{
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 5px;}
            QPushButton:hover{
                background-color: #1085E2;
                color: white;
                border: none;
                border-radius: 5px;}"""
            )
        path_layout.addWidget(browse_button)
        
        layout.addLayout(path_layout)
        
        # mp4 butonu
        self.video_button = QPushButton("MP4 Download")
        self.video_button.setMinimumHeight(45)
        self.video_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.video_button.setStyleSheet("""
            QPushButton {
                background-color: #33dd88;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #22ee77;
            }
        """)
        self.video_button.clicked.connect(self.start_download_video)
        layout.addWidget(self.video_button)
        
        # mp3 butonu
        self.Audio_button = QPushButton("MP3 Download")
        self.Audio_button.setMinimumHeight(45)
        self.Audio_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.Audio_button.setStyleSheet("""
            QPushButton {
                background-color: #edbb44;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #ffaa33;
            }
        """)
        self.Audio_button.clicked.connect(self.start_download_audio)
        layout.addWidget(self.Audio_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Durum etiketi
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.stacked_widget.addWidget(download_page)

    def on_url_changed(self):
        """URL değiştiğinde çağrılır"""
        url = self.url_input.text().strip()
        # Basit URL doğrulaması
        is_valid =False  
        if ((url) and ("youtube.com/watch" in url or "youtu.be/" in url)):
            is_valid= True
        else:
            is_valid=False

        self.search_button.setEnabled(is_valid)

    def search_video(self):
        """Video bilgilerini al"""
        url = self.url_input.text().strip()

        self.search_button.setText("Loading ...")
        self.search_button.setEnabled(False)

        # Video bilgilerini almak için thread başlat
        self.video_thread = VideoInfoThread(url)
        self.video_thread.info_received.connect(self.on_video_info_received)
        self.video_thread.error_occurred.connect(self.on_search_error)
        self.video_thread.start()

    def on_video_info_received(self, info):
        """Video bilgileri alındığında çağrılır"""
        self.current_video_info = info
        
        # Video bilgilerini göster
        self.video_title.setText(info['title'])
        self.video_author.setText(f"Channel: {info['author']}")

        # İstatistikleri formatla
        duration_mins = info['length'] // 60
        duration_secs = info['length'] % 60
        views_formatted = f"{info['views']:,}".replace(',', '.')

        self.video_stats.setText(f"Duration: {duration_mins}:{duration_secs:02d} | Views: {views_formatted}")
        #print("byara girdi")
        videos = []
        audios = []
        for s in info["streams"]:
            #print(s)
            if s['resolution'] != 'Audio Only'  :
                videos.append(s)
            elif s['resolution'] == 'Audio Only':
                audios.append(s)
                            
        videos.sort(key=lambda x: int(x['resolution'].replace("p", "")), reverse=True)
        #print(videos)
        def abr(s):
            a = getattr(s['stream'], 'abr', '0kbps')
            return int(a.replace("kbps", ""))

        audios.sort(key=abr, reverse=True)

        self.quality_combo.clear()
        self.audio_combo.clear()
        
        # Kalite seçeneklerini doldur

        for v in videos:
            #print(v)
            size_mb = v['filesize'] /\
                (1024*1024) if s['filesize'] else 0
            combo_text = f"{v['resolution']} - {v['file_extension']} ({size_mb:.1f} MB)"
            self.quality_combo.addItem(combo_text, v)

        for a in audios:
            size_mb = a['filesize'] /\
                (1024*1024) if s['filesize'] else 0
            combo_text = f"{getattr(a['stream'], 'abr', 'audio')}, {a['resolution']} - {a['file_extension']} ({size_mb:.1f} MB)"
            #
            self.audio_combo.addItem(combo_text, a)
        
         # default seçim
        index = 0
        for i, v in enumerate(videos):
            if v['resolution'] == "1080p":
                index = i
                break

        self.quality_combo.setCurrentIndex(index)
        self.audio_combo.setCurrentIndex(0)

        # İndirme sayfasına geç
        self.stacked_widget.setCurrentIndex(1)

        # Arama butonunu sıfırla
        self.search_button.setText("Take Video Information")
        self.search_button.setEnabled(True)

    def on_search_error(self, error_message):
        #"""Arama hatası durumunda çağrılır"""
        QMessageBox.critical(self, "Error", error_message)

        self.search_button.setText("Take Video Information")
        self.search_button.setEnabled(True)

    def go_back(self):
        #"""Ana sayfaya dön"""
        self.stacked_widget.setCurrentIndex(0)
        self.status_label.setText("")
        self.progress_bar.setVisible(False)

    def browse_folder(self):
        #"""Klasör seç"""
        folder = QFileDialog.getExistingDirectory(self, "Choose Downloading Folder")
        if folder:
            self.path_input.setText(folder)
  
    def start_download(self, mode):
        #"""İndirmeyi başlat"""
        #print("indeirme kısmına girdi , mode =",mode)
        if not self.current_video_info:
            return
        # Seçili stream'i al
        current_video_data = self.quality_combo.currentData()
        if not current_video_data:
            return
        # Seçili stream'i al
        current_audio_data = self.audio_combo.currentData()
        if not current_audio_data:
            return

        nevoutput_path = self.path_input.text().strip()
        if not nevoutput_path or not os.path.exists(nevoutput_path):
            QMessageBox.warning(
                self, "Attention", "Choose Valid Path !")
            return
        if (mode==0):
            
            # UI'yi indirme moduna geçir
            self.video_button.setText("Downloading...")
            self.video_button.setEnabled(False)
            self.Audio_button.setText("Wait")
            self.Audio_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Downloading Start...")
        elif(mode==1):
            self.Audio_button.setText("Downloading...")
            self.Audio_button.setEnabled(False)
            self.video_button.setText("Waiting")
            self.video_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Downloading Start...")
        else:
            return
            
        # İndirme thread'ini başlat
        
        stream = current_video_data["stream"]
        title = stream.title
        #print(title)
        self.download_thread = DownloadThread(output_path = nevoutput_path, 
                                              video_stream= current_video_data["stream"], 
                                              audio_stream = current_audio_data["stream"] , 
                                              mode=mode,title=title)
        self.download_thread.download_completed.connect(
            self.on_download_completed)
        self.download_thread.error_occurred.connect(self.on_download_error)
        self.download_thread.start()

        # Sahte progress için timer (pytube progress callback karmaşık olabiliyor)
        self.progress_timer =QTimer()
        self.progress_timer.timeout.connect(self.update_fake_progress)
        self.progress_value = 0
        self.progress_timer.start(200)
    
    def start_download_video(self):
         self.start_download(mode=0)
    def start_download_audio(self):
        print("ses indir tıklandı")
        self.start_download(mode=1)
        

    def update_fake_progress(self):
        #"""Sahte progress güncellemesi"""
        self.progress_value += 1
        if self.progress_value >= 90:
            self.progress_timer.stop()
        self.progress_bar.setValue(self.progress_value)

    def on_download_completed(self, message):
        """İndirme tamamlandığında çağrılır"""
        self.progress_timer.stop()
        self.progress_bar.setValue(100)
        self.status_label.setText(message)

        self.video_button.setText("MP4 Download")
        self.video_button.setEnabled(True)
        self.Audio_button.setText("MP3 Download")
        self.Audio_button.setEnabled(True)

        QMessageBox.information(self, "Succesful", "Video Succesfuly downloaded!")

    def on_download_error(self, error_message):
        """İndirme hatası durumunda çağrılır"""
        self.progress_timer.stop()
        self.progress_bar.setVisible(False)
        self.status_label.setText("")

        self.video_button.setText("MP4 Download")
        self.video_button.setEnabled(True)
        self.Audio_button.setText("MP3 Download")
        self.Audio_button.setEnabled(True)
        QMessageBox.critical(self, "Download Error", error_message)
        # Dosya yolları
        self.video_file = None
        self.audio_file = None

def main():
    app = QApplication(sys.argv)

    # Başlangıçta pytube versiyonunu kontrol et
    try:
        import pytube
        print(f"Pytube versiyonu: {pytube.__version__}")
    except:
        print("Pytube versiyonu tespit edilemedi")

    # Uygulama stili
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f0f0f0;
        }
        QLabel {
            color: #333333;
        }
        QLineEdit {
            padding: 8px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 11px;
        }
        QLineEdit:focus {
            border-color: #4CAF50;
        }
        QComboBox {
            padding: 5px;
            border: 2px solid #ddd;
            border-radius: 5px;
        }
        QPushButton {
            padding: 8px;
            border-radius: 5px;
            font-weight: bold;
        }
        QFrame {
            background-color: white;
            border-radius: 8px;
            padding: 10px;
        }
    """)

    # Hata durumunda kullanıcıya yardımcı mesaj göster
    try:
        window = VideoDownloader()
        window.show()

        # İlk açılışta ipuçları göster
        QTimer.singleShot(1000, lambda: show_tips_if_needed())

    except Exception as e:
        QMessageBox.critical(None, "Başlatma Hatası",
                             f"Uygulama başlatılırken hata oluştu:\n{ str(e)}\n\n"
                             f"Çözüm önerileri:\n"
                             f"1. pip install --upgrade pytube\n"
                             f"2. pip install PyQt5")
        return

    sys.exit(app.exec_())


def show_tips_if_needed():
    """İpuçlarını göster"""
    msg = QMessageBox()
    msg.setWindowTitle("Kullanım İpuçları")
    msg.setText("HTTP 400 hatası alırsanız şu çözümleri deneyin:")
    msg.setDetailedText("""
1. Pytube'u güncelleyin:
   pip install --upgrade pytube

2. Alternatif olarak yt-dlp kullanın:
   pip install yt-dlp

3. VPN kullanarak farklı bir IP'den deneyin

4. Video linkinin doğru ve erişilebilir olduğundan emin olun

5. Video gizli/kısıtlı ise indirilemeyebilir

6. Birkaç dakika sonra tekrar deneyin
""")
    msg.setIcon(QMessageBox.Information)
    msg.setStandardButtons(QMessageBox.Ok)
    # msg.exec_()  # Otomatik göstermeyi kapatıyoruz


if __name__ == '__main__':
    main()