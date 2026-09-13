from PySide6.QtWidgets import QApplication, QVBoxLayout, QLabel, QPushButton, QLineEdit, QSpinBox, QDialog, QCheckBox, QHBoxLayout, QListWidget, QFileDialog, QMessageBox, QInputDialog
from PySide6.QtCore import QTimer
from utils import Cronometro, formatah

def parse_time_str_to_hours(time_str):
    """Converte uma string de tempo 'HH:MM:SS' ou 'HH:MM' para horas em float."""
    if isinstance(time_str, (int, float)):
        return float(time_str)
    try:
        parts = str(time_str).split(':')
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        seconds = int(parts[2]) if len(parts) > 2 else 0
        return hours + (minutes / 60.0) + (seconds / 3600.0)
    except (ValueError, IndexError):
        return 0.0

def formata_saldo(horas):
    '''formata_saldo(horas) -> 'HH:MM' ou '-HH:MM'

    Rótulo de saldo do cronômetro: horas positivas sem sinal e negativas com
    "-" (formatah com sinal=False removeria também o "-").'''
    if horas < 0:
        return formatah(horas)
    return formatah(horas, sinal=False)

class CronometroDialogQt(QDialog):
    '''Janela do cronômetro. Com parar=True, a contagem termina sozinha ao
    atingir o saldo da atividade; com parar=False, conta sem limite.'''
    def __init__(self, atividade, parar=True):
        super().__init__()
        self.decorrido_final = 0
        self.atividade = atividade
        self.setWindowTitle(f'd10r - Atividade: {atividade.nome}')
        self.setModal(True)
        saldo_num = parse_time_str_to_hours(getattr(atividade, 'saldo', 0))
        layout = QVBoxLayout()
        self.label = QLabel('Decorrido/Saldo:')
        layout.addWidget(self.label)
        self.tempoDecorridoLbl = QLabel('00:00:00')
        layout.addWidget(self.tempoDecorridoLbl)
        self.tempoSaldoLbl = QLabel('/ ' + formata_saldo(saldo_num))
        layout.addWidget(self.tempoSaldoLbl)
        self.pausarBtn = QCheckBox('Pausar')
        layout.addWidget(self.pausarBtn)
        self.pararBtn = QPushButton('Finalizar')
        layout.addWidget(self.pararBtn)
        self.setLayout(layout)
        if parar:
            self.cronometro = Cronometro(saldo_num, True)
        else:
            self.cronometro = Cronometro(None)
        self.cronometro.start()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(200)
        self.pararBtn.clicked.connect(self.fechar)
        self.pausarBtn.stateChanged.connect(self.pausarCb)
    def _refresh(self):
        self.tempoDecorridoLbl.setText(
            formatah(self.cronometro.decorridoh, segundos=True, sinal=False))
        if self.cronometro.isparado:
            self.fechar()
    def pausarCb(self):
        self.cronometro.pausar()
    def fechar(self):
        self.accept()
    def done(self, resultado):
        # accept() e reject() (Esc ou botão "X") passam por aqui: garante que a
        # thread pare e o tempo decorrido seja registrado em qualquer caso.
        self.timer.stop()
        self.cronometro.parar()
        if self.cronometro.is_alive():
            self.cronometro.join(timeout=1.0)
        self.decorrido_final = self.cronometro.decorridoh
        super().done(resultado)

    def get_decorrido(self):
        return self.decorrido_final

    @property
    def fim_alcancado(self):
        return self.cronometro.fim_alcancado

class HoraSpinDialogQt(QDialog):
    def __init__(self, msg):
        super().__init__()
        self.setWindowTitle('d10r - Debitar')
        layout = QVBoxLayout()
        self.msglbl = QLabel(msg)
        layout.addWidget(self.msglbl)
        # Layout para os spinboxes
        spin_layout = QHBoxLayout()
        self.horas_spin = QSpinBox()
        self.horas_spin.setRange(0, 99)
        spin_layout.addWidget(QLabel('Horas:'))
        spin_layout.addWidget(self.horas_spin)
        self.minutos_spin = QSpinBox()
        self.minutos_spin.setRange(0, 59)
        spin_layout.addWidget(QLabel('Minutos:'))
        spin_layout.addWidget(self.minutos_spin)
        self.segundos_spin = QSpinBox()
        self.segundos_spin.setRange(0, 59)
        spin_layout.addWidget(QLabel('Segundos:'))
        spin_layout.addWidget(self.segundos_spin)
        layout.addLayout(spin_layout)
        # Botões OK e Cancelar
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton('OK')
        self.cancel_btn = QPushButton('Cancelar')
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    def get(self):
        return (self.horas_spin.value(), self.minutos_spin.value(), self.segundos_spin.value())

class PrioridadeDialogQt(QDialog):
    def __init__(self, atividades):
        super().__init__()
        self.setWindowTitle('d10r - Prioridades')
        layout = QVBoxLayout()
        msg = ('Use os botões "Subir" e "Descer" para ordenar as atividades listadas abaixo por ordem descrescente de prioridade (mais importantes primeiro).')
        layout.addWidget(QLabel(msg))
        self.listbox = QListWidget()
        for atividade in atividades:
            self.listbox.addItem(atividade)
        self.listbox.setCurrentRow(0)
        layout.addWidget(self.listbox)
        # Botões de controle
        btns_layout = QHBoxLayout()
        self.subir_btn = QPushButton('Subir')
        self.descer_btn = QPushButton('Descer')
        btns_layout.addWidget(self.subir_btn)
        btns_layout.addWidget(self.descer_btn)
        layout.addLayout(btns_layout)
        # Botões OK/Cancelar
        ok_cancel_layout = QHBoxLayout()
        self.ok_btn = QPushButton('OK')
        self.cancel_btn = QPushButton('Cancelar')
        ok_cancel_layout.addWidget(self.ok_btn)
        ok_cancel_layout.addWidget(self.cancel_btn)
        layout.addLayout(ok_cancel_layout)
        self.setLayout(layout)
        self.subir_btn.clicked.connect(self.subir)
        self.descer_btn.clicked.connect(self.descer)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    def subir(self):
        cur = self.listbox.currentRow()
        if cur > 0:
            item = self.listbox.takeItem(cur)
            self.listbox.insertItem(cur-1, item)
            self.listbox.setCurrentRow(cur-1)
    def descer(self):
        cur = self.listbox.currentRow()
        if cur < self.listbox.count()-1:
            item = self.listbox.takeItem(cur)
            self.listbox.insertItem(cur+1, item)
            self.listbox.setCurrentRow(cur+1)
    def get(self):
        return [self.listbox.item(i).text() for i in range(self.listbox.count())]

class ChoiceBoxQt(QDialog):
    def __init__(self, title, msg, choices):
        super().__init__()
        self.setWindowTitle(title)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(msg))
        self.listbox = QListWidget()
        for choice in choices:
            self.listbox.addItem(str(choice))
        # A primeira opção já vem selecionada, como no comportamento anterior.
        if self.listbox.count():
            self.listbox.setCurrentRow(0)
        layout.addWidget(self.listbox)
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton('OK')
        self.cancel_btn = QPushButton('Cancelar')
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    def get(self):
        selected = self.listbox.currentItem()
        return selected.text() if selected else None

class ButtonBoxQt(QDialog):
    '''Mensagem com um botão para cada opção; get() devolve a opção clicada.

    A janela não fecha sem que um botão seja
    escolhido: Esc e o botão "X" são ignorados.'''
    def __init__(self, title, msg, choices):
        super().__init__()
        self.setWindowTitle(title)
        self.resposta = None
        layout = QVBoxLayout()
        msglbl = QLabel(msg)
        msglbl.setWordWrap(True)
        layout.addWidget(msglbl)
        btn_layout = QHBoxLayout()
        self.botoes = []
        for choice in choices:
            btn = QPushButton(str(choice))
            btn.setAutoDefault(False)
            btn.clicked.connect(lambda _checked=False, c=choice: self._escolher(c))
            btn_layout.addWidget(btn)
            self.botoes.append(btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        if self.botoes:
            self.botoes[0].setDefault(True)
            self.botoes[0].setFocus()
    def _escolher(self, choice):
        self.resposta = choice
        self.accept()
    def reject(self):
        QApplication.beep()
    def closeEvent(self, event):
        if self.resposta is None:
            QApplication.beep()
            event.ignore()
        else:
            super().closeEvent(event)
    def get(self):
        return self.resposta

class TextEntryBoxQt(QDialog):
    def __init__(self, title, msg, default_text=''):
        super().__init__()
        self.setWindowTitle(title)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(msg))
        self.entry = QLineEdit()
        self.entry.setText(default_text)
        layout.addWidget(self.entry)
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton('OK')
        self.cancel_btn = QPushButton('Cancelar')
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    def get(self):
        return self.entry.text()

# Wrappers de diálogo usados pela facade gui.py. Mantêm as assinaturas
# observáveis da camada de interface anterior, mas usam apenas widgets PySide6.

def msgbox(msg, title):
    return QMessageBox.information(None, title, msg)


def ynbox(msg, title):
    dialog = ButtonBoxQt(title, msg, ('Sim', 'Não'))
    return dialog.exec() and dialog.get() == 'Sim'


def integerbox(msg, title, argUpperBound=168):
    valor, aceito = QInputDialog.getInt(
        None, title, msg, 0, 0, argUpperBound, 1,
    )
    return valor if aceito else None


def enterbox(msg, title, default=''):
    valor, aceito = QInputDialog.getText(None, title, msg, text=default)
    return valor if aceito else None


def choicebox(msg, title, choices):
    dialog = ChoiceBoxQt(title, msg, choices)
    return dialog.get() if dialog.exec() else None


def buttonbox(msg, title, choices):
    dialog = ButtonBoxQt(title, msg, choices)
    return dialog.get() if dialog.exec() else None


def fileopenbox(msg, title, default='*'):
    caminho, _ = QFileDialog.getOpenFileName(None, title, '', default)
    return caminho or None


# Funções utilitárias para seleção de arquivo e mensagem

def file_open_dialog(title, filetypes=None):
    dialog = QFileDialog()
    dialog.setWindowTitle(title)
    if filetypes:
        dialog.setNameFilters(filetypes)
    if dialog.exec():
        return dialog.selectedFiles()[0]
    return None

def show_message(title, msg):
    QMessageBox.information(None, title, msg)
