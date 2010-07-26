#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Módulo de interface gráfica do d10r

Este módulo concentra(rá) todas as classes e funções relacionadas a GUI.
'''

import time
import threading
import Tkinter as tk

import easygui as eg

from utils import formatah


TITLE = 'd10r'


class FimAlcancado(Exception):
    pass


class Cronometro(threading.Thread):
    '''Cronômetro assíncrono com threads.'''
    def __init__(self, fim=None, h=False):
        super(Cronometro, self).__init__()
        if fim and h:
            self.fim = fim * 3600
        else:
            self.fim = fim
        self._decorrido = 0
        self._pausado = False
        self._parado = False

    def run(self):
        while True:
            if self.fim != None and self.decorrido >= self.fim:
                self._decorrido = self.fim
                self.parar()
            if self._parado:
                break
            time.sleep(1)
            if not self._pausado:
                self._decorrido += 1

    def pausar(self):
        '''Pausa o cronômetro ou continua a contar, se estiver pausado.'''
        if self._pausado:
            self._pausado = False
        else:
            self._pausado = True

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


class CronometroDialog:
    '''Janela que exibe o nome de uma atividade, o tempo decorrido, o saldo e
    botões para que o usuário pause ou pare o cronômetro.'''

    def __init__(self, atividade, root, parar=True):
        self.atividade = atividade
        if parar:
            self.cronometro = Cronometro(atividade.saldo, True)
        else:
            self.cronometro = Cronometro(None)
        self.root = root
        self.construir()

    def start(self):
        if not self.cronometro.isAlive():
            self.cronometro.start()
        self._refresh()

    def _refresh(self):
        self.tempoDecorridoLbl.config(text=formatah(-self.cronometro.decorridoh,
                                      segundos=True))
        if not self.cronometro.isparado:
            self.tempoDecorridoLbl.after(200, self._refresh)
        else:
            self.fechar()

    def fechar(self):
        self.root.quit()
        self.root.destroy()

    def pararCb(self):
        self.cronometro.parar()
        self.fechar()

    def pausarCb(self):
        self.cronometro.pausar()

    def construir(self):
        '''Cria a janela com os widgets e configura o label para ser atualizado
        com o tempo decorrido.'''
        ### Janela ###
        self.root.title(u'%s - Atividade: %s' % (TITLE, self.atividade.nome))
        self.root.protocol('WM_DELETE_WINDOW', self.pararCb)
        self.root.iconname(TITLE)
        self.root.wm_attributes('-topmost', 1)

        ### Frames ###

        mainFrame = tk.Frame(self.root)
        mainFrame.pack()

        ### Labels ###

        atividadeLabel = tk.Label(mainFrame, text='Decorrido/Saldo: ', justify='left')
        atividadeLabel.pack(side='left', expand=True)

        self.tempoDecorridoLbl = tk.Label(mainFrame,
                                 text=formatah(-self.cronometro.decorridoh, True))
        self.tempoDecorridoLbl.pack(side='left', expand=True)

        tempoSaldoLbl = tk.Label(mainFrame,
                                 text='/ ' + formatah(self.atividade.saldo))
        tempoSaldoLbl.pack(side='left', expand=True)

        ### Buttons ###
        pausarBtn = tk.Checkbutton(mainFrame, text='Pausar', command=self.pausarCb)
        pausarBtn.pack(side='left')

        pararBtn = tk.Button(mainFrame, text='Finalizar', command=self.pararCb)
        pararBtn.pack(side='left')


class HoraSpinDialog:
    def __init__(self, msg):
        self.msg = msg
        self.construir()
        self.root.mainloop()

    def get(self):
        try:
            return (self.horas, self.minutos, self.segundos)
        except NameError:
            return None

    def construir(self):
        self.root = tk.Tk()
        self.root.title('%s - Debitar' % TITLE)
        self.root.protocol('WM_DELETE_WINDOW', self.fechar)

        msglbl = tk.Label(self.root, text=self.msg)
        msglbl.pack()

        formframe = tk.Frame(self.root)
        formframe.pack()

        lblsframe = tk.Frame(formframe)
        lblsframe.pack(side='left')

        spinsframes = tk.Frame(formframe)
        spinsframes.pack(side='left')

        horalbl = tk.Label(lblsframe, text='Horas: ')
        horalbl.pack()

        minutolbl = tk.Label(lblsframe, text='Minutos: ')
        minutolbl.pack()

        segundolbl = tk.Label(lblsframe, text='Segundos: ')
        segundolbl.pack()

        self._horaspn = tk.Spinbox(spinsframes, values=range(100))
        self._horaspn.pack()

        self._minutospn = tk.Spinbox(spinsframes, values=range(100))
        self._minutospn.pack()

        self._segundospn = tk.Spinbox(spinsframes, values=range(100))
        self._segundospn.pack()

        okbtn = tk.Button(self.root, text='OK', command=self.okbtn_cb)
        okbtn.pack()

    def okbtn_cb(self):
        self.horas = int(self._horaspn.get())
        self.minutos = int(self._minutospn.get())
        self.segundos = int(self._segundospn.get())
        self.fechar()

    def fechar(self):
        self.root.quit()
        self.root.destroy()


def cronometro_dialog(atividade, parar=True):
    '''cronometroDialog(atividade) -> float

    Fábrica de janelas de cronômetro. Retorna o tempo decorrido em horas desde a
    chamada da função. parar determina se o cronômetro deve parar quanto o tempo
    decorrido for igual ao saldo da atividade.'''
    root = tk.Tk()
    d = CronometroDialog(atividade, root, parar)
    d.start()
    root.mainloop()
    if atividade.saldo == d.cronometro.decorridoh:
        raise FimAlcancado
    return d.cronometro.decorridoh


def horaspin(msg):
    h = HoraSpinDialog(msg)
    return h.get()


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
        return eg.integerbox(msg, TITLE)
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
