#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import time
import easygui as eg
from utils import ICON
from gui_pyside import CronometroDialogQt, HoraSpinDialogQt, PrioridadeDialogQt
'''
Módulo de interface gráfica

Copyright (C) 2010  Ygor Mutti
Licenciado sob GPLv3, com texto disponível no arquivo COPYING
'''

# AVISO: Este módulo foi migrado para PySide6. Todas as funções e classes Tkinter foram removidas.
# Use gui_pyside.py para interface gráfica.

# Mantém apenas utilitários e lógica não gráfica
import time
import threading
from utils import formatah, plataforma, WINDOWS

ICON = 'icons/d10r.ico' if plataforma() == WINDOWS else '@icons/d10r.xbm'
TITLE = 'd10r'

class FimAlcancado(Exception):
    pass

# Removida a classe Cronometro (agora em utils.py)

class CronometroDialogQt:
    '''Cronômetro assíncrono com threads.'''
    def __init__(self, atividade, h=False):
        super().__init__()
        if atividade and h:
            self.fim = atividade.saldo * 3600
        else:
            self.fim = atividade.saldo if atividade else None
        self._decorrido = 0
        self._pausado = False
        self._parado = False

    def run(self):
        while True:
            if self.fim is not None and self.decorrido >= self.fim:
                self._decorrido = self.fim
                self.parar()
            if self._parado:
                break
            time.sleep(1)
            if not self._pausado:
                self._decorrido += 1

    def pausar(self):
        '''Pausa o cronômetro ou continua a contar, se estiver pausado.'''
        self._pausado = not self._pausado

    def parar(self):
        '''Encerra a contagem e finaliza a thread.'''
        self._parado = True

    @property
    def decorrido(self):
        '''Tempo em segundos decorrido desde o início da contagem.'''
        return self._decorrido

    @property
    def decorridoh(self):
        '''Mesmo que decorrido, porém retorna o valor em horas.'''
        return self._decorrido / 3600.0

    @property
    def isparado(self):
        return self._parado
        '''Mesmo que decorrido, porém retorna o valor em horas.'''
        return self._decorrido / 3600.0

    @property
    def isparado(self):
        return self._parado


def cronometro_dialog(atividade, parar=True):
    '''cronometroDialog(atividade) -> float

    Fábrica de janelas de cronômetro. Retorna o tempo decorrido em horas desde a
    chamada da função. parar determina se o cronômetro deve parar quanto o tempo
    decorrido for igual ao saldo da atividade.'''
    dlg = CronometroDialogQt(atividade, parar)
    dlg.exec()
    return dlg.get_decorrido()


def horaspin(msg):
    dlg = HoraSpinDialogQt(msg)
    if dlg.exec():
        return dlg.get()
    return (0, 0, 0)


def prioridade_dialog(atividades):
    dlg = PrioridadeDialogQt(atividades)
    if dlg.exec():
        return dlg.get()
    return None


def notificar(msg):
    '''Exibe uma janela de diálogo com a mensagem em msg.'''
    eg.msgbox(msg, TITLE)


def perguntar(pergunta):
    '''perguntar(pergunta) -> bool

    Exibe uma janela com uma pergunta do tipo sim ou não e retorna a resposta
    como bool.'''
    return bool(eg.ynbox(pergunta, TITLE))


def entrar(msg, inteiro=False):
    '''entrar(msg) -> str

    Exibe uma janela com a mensagem em msg e uma caixa de texto para que o
    usuário informe alguma string.'''
    if inteiro:
        # há 168h em uma semana
        return eg.integerbox(msg, TITLE, argUpperBound=168)
    return eg.enterbox(msg, TITLE)


def escolher(msg, opcoes):
    '''escolher(msg, opcoes) -> opção

    Exibe uma janela que permite que o usuário escolha uma dentre várias opções
    e retorna a opção escolhida.'''
    return eg.choicebox(msg, TITLE, opcoes)


def menu(msg, botoes):
    '''menu(msg, botoes) -> botoes[i]

    Exibe uma janela com uma mensagem e vários botões, retornando o texto
    contido no botão pressionado pelo usuário.'''
    return eg.buttonbox(msg, TITLE, botoes)


def escolher_arquivo(msg, extensao):
    '''escolher_arquivo(msg, extensao) -> str

    Exibe uma janela para que o usuário escolha um arquivo e retorna o path
    completo para o arquivo escolhido.'''
    return eg.fileopenbox(msg, TITLE, '*.' + extensao)
