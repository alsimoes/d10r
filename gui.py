#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
Módulo de interface gráfica

Os diálogos são implementados com PySide6 em gui_pyside.py; este módulo expõe
funções simples usadas pelo d10r.py.

Copyright (C) 2010  Ygor Mutti
Licenciado sob GPLv3, com texto disponível no arquivo COPYING
'''

from gui_pyside import (CronometroDialogQt, HoraSpinDialogQt,
                         PrioridadeDialogQt, msgbox, ynbox, integerbox,
                         enterbox, choicebox, buttonbox, fileopenbox)

TITLE = 'd10r'


class FimAlcancado(Exception):
    pass


def cronometro_dialog(atividade, parar=True):
    '''cronometro_dialog(atividade, parar=True) -> float

    Fábrica de janelas de cronômetro. Retorna o tempo decorrido em horas desde a
    chamada da função. parar determina se o cronômetro deve parar quando o tempo
    decorrido for igual ao saldo da atividade; nesse caso, levanta FimAlcancado.'''
    dlg = CronometroDialogQt(atividade, parar)
    dlg.exec()
    if parar and dlg.fim_alcancado:
        raise FimAlcancado
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
    msgbox(msg, TITLE)


def perguntar(pergunta):
    '''perguntar(pergunta) -> bool

    Exibe uma janela com uma pergunta do tipo sim ou não e retorna a resposta
    como bool.'''
    return bool(ynbox(pergunta, TITLE))


def entrar(msg, inteiro=False):
    '''entrar(msg) -> str

    Exibe uma janela com a mensagem em msg e uma caixa de texto para que o
    usuário informe alguma string.'''
    if inteiro:
        # há 168h em uma semana
        return integerbox(msg, TITLE, argUpperBound=168)
    return enterbox(msg, TITLE)


def escolher(msg, opcoes):
    '''escolher(msg, opcoes) -> opção

    Exibe uma janela que permite que o usuário escolha uma dentre várias opções
    e retorna a opção escolhida.'''
    return choicebox(msg, TITLE, opcoes)


def menu(msg, botoes):
    '''menu(msg, botoes) -> botoes[i]

    Exibe uma janela com uma mensagem e vários botões, retornando o texto
    contido no botão pressionado pelo usuário.'''
    return buttonbox(msg, TITLE, botoes)


def escolher_arquivo(msg, extensao):
    '''escolher_arquivo(msg, extensao) -> str

    Exibe uma janela para que o usuário escolha um arquivo e retorna o path
    completo para o arquivo escolhido.'''
    return fileopenbox(msg, TITLE, '*.' + extensao)
