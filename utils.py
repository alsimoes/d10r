#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
Funções e classes úteis e reutilizáveis

Copyright (C) 2010  Ygor Mutti
Licenciado sob GPLv3, com texto disponível no arquivo COPYING
'''

import sys
import threading
import time

WINDOWS = 'win'
LINUX = 'linux'
MAC = 'darwin'


def plataforma():
    '''plataforma() -> str

    Descobre a plataforma em que o programa está rodando. Possíveis retornos são
    WINDOWS, LINUX e MAC.'''
    if sys.platform.startswith('win'):
        return WINDOWS
    elif sys.platform.startswith('darwin'):
        return MAC
    return LINUX


def formatah(horas, segundos=False, sinal=True):
    '''formatah(horas, segundos=False, sinal=True) -> '[+-]HH:MM[:SS]'

    Recebe uma quantidade de horas como float e retorna uma string HH:MM.'''
    if sinal and horas:
        sinal = '-' if (horas < 0) else '+'
    else:
        sinal = ''
    s = abs(horas) * 3600.0
    m, s = divmod(s, 60.0)
    h, m = divmod(m, 60.0)

    if segundos:
        return '%s%02d:%02d:%02d' % (sinal, int(h), int(m), int(s))
    else:
        return '%s%02d:%02d' % (sinal, int(h), int(m))


def dias_ate_prox_dia(dia, x):
    '''dias_ate_prox_dia(dia, x) -> int

    Determina quantos dias faltam, a partir de x (um dia da semana), para dia
    (outro dia da semana). Os dias devem estar no formato ISO para dia da semana.'''
    if dia == x:
        return 0
    elif dia < x:
        return (7 + dia - x)
    else:
        return (dia - x)


def dias_x_entre(dia, antes, depois):
    '''dias_x_entre(dia, antes, depois) -> int

    Determina quantas vezes um dia da semana (formato ISO) ocorre entre duas
    datas, incluindo as duas extremidades.'''
    total_dias = (depois - antes).days + 1
    if total_dias <= 0:
        return 0
    n, resto = divmod(total_dias, 7)
    # Os dias restantes cobrem os deslocamentos 0..resto-1 a partir de 'antes',
    # inclusive quando atravessam a virada da semana (ex.: sábado -> segunda).
    if resto and dias_ate_prox_dia(dia, antes.isoweekday()) < resto:
        n += 1
    return n


class Cronometro(threading.Thread):
    '''Cronômetro assíncrono com threads.

    fim=None cria um cronômetro sem limite, que só para com parar(). Se h=True,
    fim é interpretado em horas; caso contrário, em segundos.'''
    def __init__(self, fim=None, h=False):
        # daemon: uma contagem esquecida não impede o programa de encerrar
        super().__init__(daemon=True)
        if fim is None:
            self.fim = None
        else:
            self.fim = float(fim) * 3600 if h else float(fim)
        self._decorrido = 0
        self._pausado = False
        self._parado = False
        self._fim_alcancado = False
        self._stop_event = threading.Event()
    def run(self):
        while True:
            if self.fim is not None and self.decorrido >= self.fim:
                self._decorrido = self.fim
                self._fim_alcancado = True
                self.parar()
            if self._stop_event.is_set():
                break
            if self._stop_event.wait(1):
                break
            if not self._pausado:
                self._decorrido += 1
    def pausar(self):
        self._pausado = not self._pausado
    def parar(self):
        self._parado = True
        self._stop_event.set()
    @property
    def decorrido(self):
        return self._decorrido
    @property
    def decorridoh(self):
        return self._decorrido / 3600.0
    @property
    def isparado(self):
        return self._parado
    @property
    def fim_alcancado(self):
        '''True se a contagem parou por ter atingido fim.'''
        return self._fim_alcancado

ICON = 'icons/d10r.ico' if plataforma() == WINDOWS else '@icons/d10r.xbm'
