#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
Módulo de dados (persistência, modelos, etc)

A persistência é exclusivamente SQLite, em `DATABASE`. O INI legado não é
backend, formato de saída nem fallback: é apenas entrada de uma importação
única, feita pelo `storage`, e desaparece depois dela. Este módulo mantém a API
pública de sempre — `ArquivoError`, `Atividade`, `parse_config`,
`salvar_config` e `creditar_tudo`, com as mesmas aridades — e traduz as falhas
do armazenamento para as mensagens públicas já conhecidas.

Copyright (C) 2010  Ygor Mutti
Licenciado sob GPLv3, com texto disponível no arquivo COPYING
'''

import os
import datetime

import storage
from utils import dias_x_entre


DATABASE = os.path.expanduser('~/.d10r.sqlite3')

# Entrada legada da importação única. É deliberadamente privada: não é
# configuração operacional, não pode ser escolhida pelo usuário e existe apenas
# enquanto a transição do INI para o SQLite tiver sentido.
_ENTRADA_LEGADA = storage.default_legacy_ini_path()

MSG_SEM_ARQUIVO = 'Nenhum arquivo de configuração encontrado.'
MSG_CORROMPIDO = 'Arquivo de configuração corrompido.'


class ArquivoError(Exception):
    pass


class ConfiguracaoAusente(ArquivoError):
    '''Armazenamento íntegro que ainda não tem configuração.

    É subclasse de `ArquivoError` para que qualquer `except ArquivoError`
    existente continue valendo, mas permite ao chamador distinguir "banco novo,
    siga para o questionário inicial" de "arquivo corrompido, pare". Sem essa
    distinção, um banco corrompido cairia no fluxo de primeira execução.'''


class Collection(type):
    '''Metaclass used to register classes instances.'''

    def __init__(cls, name, base, dict):
        '''Called when the class is instantiated (declared).'''
        super(Collection, cls).__init__(name, base, dict)

        cls.__all = []

        @classmethod
        def all(cls):
            '''Returns a list containing all instances of the class.'''
            return cls.__all

        @classmethod
        def clear(cls):
            cls.__all = []

        cls.all = all
        cls.clear = clear

    def __call__(cls, *args, **kwargs):
        '''Creates new instances and append them to __all.'''
        obj = super(Collection, cls).__call__(*args, **kwargs)
        cls.__all.append(obj)
        return obj


class Atividade(metaclass=Collection):

    def __init__(self, nome, pts, saldo):
        '''nome -> str
        pts -> float
        saldo -> float'''
        self.nome = nome
        self.pts = pts
        self.saldo = saldo

    def creditarh(self, toth, nvezes=1):
        '''Método chamado, semanalmente, para creditar horas em atividades, de
        acordo com a qtd. de horas disponíveis.'''
        self.saldo += (nvezes * (self.pts * (toth * 1.0)))

    def debitarh(self, horas):
        '''Diminui o saldo da atividade em horas.'''
        self.saldo -= horas


def parse_config():
    '''parse_config() -> (toth, inicio, timestamp, acumular)
    toth -> int
    inicio -> int
    timestamp -> datetime.date ou 0
    acumular -> bool

    Carrega o armazenamento e retorna o total de horas disponíveis, o dia da
    semana de início da contagem (no formato ISO), a data do último crédito de
    horas e a opção de acumular, além de instanciar as atividades.

    Resolve o estado inicial: um banco íntegro é carregado; um INI legado ainda
    existente é importado uma única vez e removido; e, se não houver nada, um
    banco v1 vazio é criado. Nesse último caso — e sempre que o banco existir sem
    configuração — levanta `ConfiguracaoAusente`, que o chamador converte no
    questionário de primeira execução. Corrupção levanta `ArquivoError`.

    As atividades só são registradas depois de o snapshot inteiro validar, de
    modo que uma falha nunca deixa `Atividade` pela metade.'''
    try:
        armazenamento = storage.ensure_storage(DATABASE, _ENTRADA_LEGADA)
        snapshot = armazenamento.load_snapshot()
    except storage.StorageError as erro:
        raise ArquivoError(MSG_CORROMPIDO) from erro

    if snapshot is storage.UNCONFIGURED:
        raise ConfiguracaoAusente(MSG_SEM_ARQUIVO)

    Atividade.clear()
    for atividade in snapshot.activities:
        Atividade(nome=atividade.name, pts=atividade.pts, saldo=atividade.saldo)

    # `0` continua sendo o "nenhum crédito ainda" público; no banco isso é NULL.
    timestamp = snapshot.last_credit_date
    if timestamp is None:
        timestamp = 0

    return (snapshot.toth, snapshot.inicio, timestamp, snapshot.acumular)


def salvar_config(toth, inicio, timestamp, acumular):
    '''salvar_config(toth, inicio, timestamp, acumular)
    toth -> int
    inicio -> int
    timestamp -> datetime.date, datetime.datetime ou 0
    acumular -> bool

    Grava a configuração e todas as atividades atuais numa única transação, de
    forma análoga à função parse_config(). Falha na gravação preserva
    integralmente o snapshot anterior.

    Uma atividade com o nome reservado do formato legado não é mais descartada em
    silêncio: a gravação falha com erro visível, para que nada seja perdido sem
    aviso.'''
    try:
        snapshot = storage.ConfigSnapshot(
            toth=toth,
            inicio=inicio,
            last_credit_date=_data_do_timestamp(timestamp),
            acumular=acumular,
            activities=tuple(
                storage.ActivitySnapshot(name=a.nome, pts=a.pts, saldo=a.saldo)
                for a in Atividade.all()),
        )
    except ValueError as erro:
        # Inclui ValidationError do Pydantic, que é subclasse de ValueError.
        raise ArquivoError('Configuração inválida: %s' % (erro,)) from erro

    try:
        armazenamento = storage.ensure_storage(DATABASE, _ENTRADA_LEGADA)
        armazenamento.save_snapshot(snapshot)
    except storage.StorageError as erro:
        raise ArquivoError(MSG_CORROMPIDO) from erro


def _data_do_timestamp(timestamp):
    '''Normaliza o `timestamp` público para a fronteira do armazenamento.

    O formato antigo usava `0` para "nenhum crédito ainda" e aceitava tanto
    `date` quanto `datetime`; o banco guarda uma data anulável. A conversão é
    desta fronteira, não do armazenamento, que valida em modo estrito.'''
    if isinstance(timestamp, datetime.datetime):
        return timestamp.date()
    if isinstance(timestamp, datetime.date):
        return timestamp
    if not timestamp:
        return None

    raise ArquivoError('Data de último crédito inválida: %r' % (timestamp,))


def creditar_tudo(toth, inicio, timestamp, acumular, hoje=None):
    '''Verifica se existem horas a serem creditadas nas atividades e credita-as.

    acumular define se todas as semanas em atraso devem ser creditadas; quando
    falso, no máximo uma semana é creditada e saldos positivos são zerados.
    hoje permite informar a data atual (útil em testes); por padrão, usa
    datetime.date.today().'''
    if hoje is None:
        hoje = datetime.date.today()
    if timestamp == 0: # primeira execução após init
        vezes = 1
    else:
        vezes = dias_x_entre(inicio, timestamp, hoje)
        # se o timestamp corresponde ao dia da semana de inicio da contagem
        # a funcao dias_x_entre contará, além do esperado, o próprio dia do
        # timestamp, sendo que as horas daquele dia já foram creditadas, daí:
        if timestamp.isoweekday() == inicio:
            vezes -= 1
        if vezes and not acumular:
            vezes = 1
    for a in Atividade.all():
        if vezes and not acumular and a.saldo > 0:
            a.saldo = 0
        a.creditarh(toth, vezes)

    return bool(vezes)
