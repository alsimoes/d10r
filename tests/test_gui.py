import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog

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
    assert not dlg.cronometro.is_alive()


@pytest.mark.parametrize('resultado', [0, 1])
def test_aceitar_ou_rejeitar_cronometro_para_a_thread(qapp, resultado):
    dlg = gui_pyside.CronometroDialogQt(AtividadeFake(), parar=False)
    dlg.done(resultado)
    assert not dlg.cronometro.is_alive()


def _clicar_no_dialogo_ativo(texto):
    '''Agenda um clique no botão 'texto' do diálogo modal que estiver aberto.'''
    from PySide6.QtWidgets import QApplication

    def clicar():
        dlg = QApplication.activeModalWidget()
        alvo = next((b for b in getattr(dlg, 'botoes', []) if b.text() == texto),
                    None)
        if alvo is None:
            dlg.done(0)  # não trava a suíte; o assert do teste acusa a falha
        else:
            alvo.click()
    QTimer.singleShot(100, clicar)


def test_buttonbox_retorna_o_botao_clicado(qapp):
    dlg = gui_pyside.ButtonBoxQt('d10r', 'O que deseja fazer?',
                                 ('Novo', 'Procurar', 'Sair'))
    assert [b.text() for b in dlg.botoes] == ['Novo', 'Procurar', 'Sair']
    dlg.botoes[1].click()
    assert dlg.get() == 'Procurar'


def test_buttonbox_ignora_esc_e_botao_fechar(qapp):
    dlg = gui_pyside.ButtonBoxQt('d10r', 'Mensagem', ('Sim', 'Não'))
    dlg.show()
    dlg.reject()  # Esc
    assert dlg.isVisible()
    dlg.close()   # botão "X"
    assert dlg.isVisible()
    dlg.botoes[0].click()
    assert not dlg.isVisible()


@pytest.mark.parametrize('botao, esperado', [('Sim', True), ('Não', False)])
def test_perguntar_usa_botoes(qapp, botao, esperado):
    _clicar_no_dialogo_ativo(botao)
    assert gui.perguntar('Confirma?') is esperado


def test_menu_retorna_texto_do_botao(qapp):
    _clicar_no_dialogo_ativo('Inserir')
    assert gui.menu('Como registrar?', ('Cronômetro', 'Inserir')) == 'Inserir'


def test_choicebox_preseleciona_primeira_opcao(qapp):
    dlg = gui_pyside.ChoiceBoxQt('d10r', 'Escolha', ['0- A', '1- B'])
    assert dlg.get() == '0- A'


def test_dialogos_de_entrada_e_arquivo_preservam_retorno_e_cancelamento(
        qapp, monkeypatch):
    monkeypatch.setattr(gui_pyside.QInputDialog, 'getInt',
                        lambda *args, **kwargs: (12, True))
    assert gui_pyside.integerbox('Horas', 'd10r', argUpperBound=168) == 12
    monkeypatch.setattr(gui_pyside.QInputDialog, 'getInt',
                        lambda *args, **kwargs: (0, False))
    assert gui_pyside.integerbox('Horas', 'd10r') is None

    monkeypatch.setattr(gui_pyside.QInputDialog, 'getText',
                        lambda *args, **kwargs: ('texto', True))
    assert gui_pyside.enterbox('Nome', 'd10r') == 'texto'
    monkeypatch.setattr(gui_pyside.QInputDialog, 'getText',
                        lambda *args, **kwargs: ('', False))
    assert gui_pyside.enterbox('Nome', 'd10r') is None

    monkeypatch.setattr(gui_pyside.QFileDialog, 'getOpenFileName',
                        lambda *args, **kwargs: ('/tmp/config.cfg', ''))
    assert gui_pyside.fileopenbox('Arquivo', 'd10r', '*.cfg') == '/tmp/config.cfg'
    monkeypatch.setattr(gui_pyside.QFileDialog, 'getOpenFileName',
                        lambda *args, **kwargs: ('', ''))
    assert gui_pyside.fileopenbox('Arquivo', 'd10r', '*.cfg') is None


def test_msgbox_wrapper_delega_para_qmessagebox(qapp, monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        gui_pyside.QMessageBox, 'information',
        lambda *args: chamadas.append(args) or 'ok',
    )
    assert gui_pyside.msgbox('Mensagem', 'd10r') == 'ok'
    assert chamadas[0][1:] == ('d10r', 'Mensagem')


@pytest.mark.parametrize('dialog_cls, args, cancel_name', [
    (gui_pyside.HoraSpinDialogQt, ('Informe:',), 'cancel_btn'),
    (gui_pyside.PrioridadeDialogQt, (['A', 'B'],), 'cancel_btn'),
    (gui_pyside.ChoiceBoxQt, ('d10r', 'Escolha', ['A', 'B']), 'cancel_btn'),
    (gui_pyside.TextEntryBoxQt, ('d10r', 'Nome'), 'cancel_btn'),
])
def test_dialogos_cancelam_sem_retorno(qapp, dialog_cls, args, cancel_name):
    dialog = dialog_cls(*args)
    getattr(dialog, cancel_name).click()
    assert dialog.result() == QDialog.DialogCode.Rejected


@pytest.mark.parametrize('saldo, esperado', [
    (1.5, '01:30'),   # positivo: sem '+'
    (-1.5, '-01:30'), # negativo: '-' preservado
    (0.0, '00:00'),
])
def test_rotulo_de_saldo_sem_mais_e_com_menos(qapp, saldo, esperado):
    dlg = gui_pyside.CronometroDialogQt(AtividadeFake(saldo=saldo), parar=False)
    dlg.done(0)
    assert dlg.tempoSaldoLbl.text() == '/ ' + esperado
