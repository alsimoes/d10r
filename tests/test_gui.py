import pytest
from PySide6.QtCore import QTimer

import gui
import gui_pyside


class AtividadeFake:
    def __init__(self, nome='Estudar', saldo=1.0):
        self.nome = nome
        self.saldo = saldo


def test_gui_usa_dialogo_de_cronometro_do_pyside():
    # Regressão: gui.py redefinia CronometroDialogQt, sombreando o import, e a
    # classe local não tinha exec(), o que encerrava o programa.
    assert gui.CronometroDialogQt is gui_pyside.CronometroDialogQt


def test_cronometro_dialog_levanta_fim_alcancado(qapp):
    atividade = AtividadeFake(saldo=1 / 3600)  # 1 segundo
    with pytest.raises(gui.FimAlcancado):
        gui.cronometro_dialog(atividade, parar=True)


def test_cronometro_sem_limite_quando_parar_e_false(qapp):
    # Atividade sem saldo, que o usuário decidiu continuar mesmo assim
    dlg = gui_pyside.CronometroDialogQt(AtividadeFake(saldo=-2.0), parar=False)
    assert dlg.cronometro.fim is None
    QTimer.singleShot(300, dlg.pararBtn.click)
    dlg.exec()
    assert dlg.cronometro.isparado
    assert not dlg.fim_alcancado
    assert dlg.get_decorrido() >= 0


def test_fechar_janela_do_cronometro_para_a_thread(qapp):
    dlg = gui_pyside.CronometroDialogQt(AtividadeFake(), parar=False)
    dlg.show()
    dlg.close()  # equivalente ao botão "X"
    assert dlg.cronometro.isparado
    assert not dlg.timer.isActive()
