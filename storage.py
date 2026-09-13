#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
Fundação do armazenamento SQLite do d10r (schema v1).

Este módulo concentra as entidades SQLModel que representam as tabelas, os DTOs
Pydantic que validam snapshots antes de qualquer gravação, a fábrica injetável de
engines e o bootstrap explícito do schema v1.

Dois princípios são estruturais e valem para todo o módulo:

- nenhum caminho, engine ou sessão é criado no import; o caminho do banco é
  sempre explícito e os padrões dependentes do HOME são funções, avaliadas
  apenas quando chamadas;
- os DTOs operam em modo estrito: valores chegam já com o tipo correto e não são
  convertidos silenciosamente. Conversões de fronteira (por exemplo
  `datetime.datetime` para `datetime.date`, ou `timestamp=0` para
  `last_credit_date=None`) pertencem à facade de `data.py`, não a este módulo.

Copyright (C) 2010  Ygor Mutti
Licenciado sob GPLv3, com texto disponível no arquivo COPYING
'''

import datetime
import os
from contextlib import contextmanager
from typing import Annotated, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlmodel import (CheckConstraint, Field as SQLField, Session, SQLModel,
                      create_engine, select)


# Versão do schema gravada no metadado singleton. Este sprint só conhece a v1 e
# nunca tenta atualizar um banco já existente.
SCHEMA_VERSION = 1

# Chave primária fixa das tabelas singleton.
SINGLETON_ID = 1


class StorageError(Exception):
    '''Falha na fronteira do armazenamento.

    Erros de SQLModel/SQLAlchemy/Pydantic são convertidos para esta exceção,
    sempre preservando a causa original por exception chaining. A tradução para
    `data.ArquivoError` acontece na facade, fora deste módulo.'''


class Unconfigured:
    '''Estado tipado de um banco v1 válido que ainda não tem configuração.

    Distingue um banco novo, recém-criado pelo bootstrap, de um banco corrompido:
    a ausência de `AppConfigRow` é um estado legítimo, enquanto a ausência de
    `SchemaVersionRow` num arquivo preexistente é corrupção. É um singleton, o
    que permite comparar com `is UNCONFIGURED`.'''

    __slots__ = ()

    _instancia = None

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super(Unconfigured, cls).__new__(cls)
        return cls._instancia

    def __repr__(self):
        return 'UNCONFIGURED'


UNCONFIGURED = Unconfigured()


def default_db_path():
    '''default_db_path() -> str

    Caminho padrão do banco operacional. É uma função, e não uma constante de
    módulo, justamente para que o import não dependa do HOME.'''
    return os.path.expanduser('~/.d10r.sqlite3')


def default_legacy_ini_path():
    '''default_legacy_ini_path() -> str

    Caminho do único INI legado aceito como entrada transitória de parâmetros.
    Também é função por não poder ser resolvido no import.'''
    return os.path.expanduser('~/.d10r')


def sqlite_url(path):
    '''sqlite_url(path) -> sqlalchemy.engine.URL

    Monta a URL de um arquivo SQLite sem interpolar strings, o que mantém
    caminhos do Windows (com letra de unidade, espaços e contrabarras) válidos.'''
    from sqlalchemy.engine import URL

    return URL.create('sqlite', database=os.fspath(path))


def create_engine_for(path, echo=False):
    '''create_engine_for(path, echo=False) -> sqlalchemy.engine.Engine

    Fábrica padrão de engines. É injetável em `SQLiteStore` para que os testes
    possam observar ou substituir a criação do engine sem monkeypatch global.'''
    return create_engine(sqlite_url(path), echo=echo)


# --- Entidades (tabelas) ---------------------------------------------------

class SchemaVersionRow(SQLModel, table=True):
    '''Metadado singleton de versão do schema, presente desde o bootstrap.'''

    __tablename__ = 'schema_version'
    __table_args__ = (
        CheckConstraint('id = 1', name='ck_schema_version_singleton'),
    )

    id: int = SQLField(default=SINGLETON_ID, primary_key=True)
    version: int = SQLField(nullable=False)


class AppConfigRow(SQLModel, table=True):
    '''Configuração singleton do aplicativo.

    Fica separada de `SchemaVersionRow` para que um banco v1 novo e ainda não
    configurado seja distinguível de um banco corrompido.'''

    __tablename__ = 'app_config'
    __table_args__ = (
        CheckConstraint('id = 1', name='ck_app_config_singleton'),
        CheckConstraint('inicio BETWEEN 1 AND 7', name='ck_app_config_inicio_iso'),
    )

    id: int = SQLField(default=SINGLETON_ID, primary_key=True)
    toth: int = SQLField(nullable=False)
    inicio: int = SQLField(nullable=False)
    last_credit_date: Optional[datetime.date] = SQLField(default=None, nullable=True)
    acumular: bool = SQLField(nullable=False)


class ActivityRow(SQLModel, table=True):
    '''Atividade persistida: chave técnica, nome único, prioridade e saldo.'''

    __tablename__ = 'activity'

    id: Optional[int] = SQLField(default=None, primary_key=True)
    name: str = SQLField(nullable=False, unique=True, index=True)
    pts: float = SQLField(nullable=False)
    saldo: float = SQLField(nullable=False)


# --- Snapshots (DTOs) ------------------------------------------------------

# `pts` e `saldo` continuam floats neste sprint, mas NaN/Infinity nunca são
# valores aceitáveis de prioridade ou saldo.
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]


class ActivitySnapshot(BaseModel):
    '''Atividade validada, pronta para persistência ou para o domínio.'''

    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)

    name: str = Field(min_length=1)
    pts: FiniteFloat
    saldo: FiniteFloat

    @field_validator('name')
    @classmethod
    def _nome_nao_em_branco(cls, valor):
        '''O nome é preservado como veio; apenas nomes em branco são rejeitados.'''
        if not valor.strip():
            raise ValueError('nome de atividade em branco')
        return valor


class ConfigSnapshot(BaseModel):
    '''Estado completo de configuração: parâmetros semanais e atividades.

    `last_credit_date` nulo significa que nenhum crédito foi registrado ainda —
    é o equivalente validado do antigo `timestamp = 0` do INI. As atividades
    formam uma tupla porque o snapshot é imutável; no modo estrito, uma lista não
    é convertida em silêncio.'''

    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)

    toth: int
    inicio: int = Field(ge=1, le=7)
    last_credit_date: Optional[datetime.date] = None
    acumular: bool
    activities: tuple[ActivitySnapshot, ...] = ()

    @model_validator(mode='after')
    def _nomes_unicos(self):
        nomes = [a.name for a in self.activities]
        if len(set(nomes)) != len(nomes):
            raise ValueError('nomes de atividade duplicados')
        return self


# Resultado de uma leitura de configuração: um snapshot válido ou o estado
# tipado "não configurado". Consumido pela facade a partir do ticket 03.
LoadedConfig = Union[ConfigSnapshot, Unconfigured]


# --- Armazenamento ---------------------------------------------------------

class SQLiteStore:
    '''Armazenamento SQLite de um caminho explícito.

    Não há engine nem sessão global: cada operação cria o seu engine pela
    fábrica injetada e o descarta ao terminar, de modo que o arquivo possa ser
    substituído ou removido logo depois, inclusive no Windows.'''

    def __init__(self, path, engine_factory=create_engine_for):
        self.path = os.fspath(path)
        self._engine_factory = engine_factory

    def __repr__(self):
        return 'SQLiteStore(%r)' % (self.path,)

    @contextmanager
    def _engine(self):
        '''Engine de vida curta, sempre descartado ao sair do bloco.'''
        engine = self._engine_factory(self.path)
        try:
            yield engine
        finally:
            engine.dispose()

    @contextmanager
    def _session(self):
        '''Uma sessão por operação, com fechamento determinístico.'''
        with self._engine() as engine:
            with Session(engine) as session:
                yield session

    def exists(self):
        '''exists() -> bool: se o arquivo do banco já está no disco.'''
        return os.path.exists(self.path)

    def bootstrap_v1(self):
        '''Cria o arquivo com o schema v1 vazio e o metadado de versão.

        O banco resultante não tem configuração nem atividades: é exatamente o
        estado inicial de quem ainda vai responder ao questionário. Recusa-se a
        tocar num arquivo existente, porque `create_all()` jamais deve ser usado
        para atualizar um banco já criado.'''
        if self.exists():
            raise StorageError('Banco de dados já existe: %s' % (self.path,))

        try:
            with self._engine() as engine:
                SQLModel.metadata.create_all(engine)
                with Session(engine) as session:
                    session.add(SchemaVersionRow(id=SINGLETON_ID,
                                                 version=SCHEMA_VERSION))
                    session.commit()
        except Exception as erro:
            # Um arquivo meio criado envenenaria as execuções seguintes; remove-se
            # apenas este caminho exato, nunca por glob.
            self._descartar_arquivo_parcial()
            raise StorageError('Falha ao criar o schema v1.') from erro

    def schema_version(self):
        '''schema_version() -> int

        Versão registrada no metadado singleton. Arquivo ausente, metadado
        ausente ou duplicado são tratados como corrupção.'''
        self._exigir_arquivo()

        try:
            with self._session() as session:
                # Os valores são lidos dentro da sessão; nada é acessado depois
                # de a instância ser desanexada.
                versoes = [linha.version
                           for linha in session.exec(select(SchemaVersionRow)).all()]
        except Exception as erro:
            raise StorageError('Falha ao ler o metadado de schema.') from erro

        if len(versoes) != 1:
            raise StorageError('Metadado de schema ausente ou duplicado.')

        return versoes[0]

    def is_configured(self):
        '''is_configured() -> bool

        True quando o singleton de configuração existe. Um banco v1 sem ele é um
        banco novo e legítimo, não um banco corrompido.'''
        self._exigir_arquivo()

        try:
            with self._session() as session:
                return session.get(AppConfigRow, SINGLETON_ID) is not None
        except Exception as erro:
            raise StorageError('Falha ao ler a configuração.') from erro

    def _exigir_arquivo(self):
        '''Evita que uma leitura crie um banco vazio por efeito colateral.'''
        if not self.exists():
            raise StorageError('Banco de dados inexistente: %s' % (self.path,))

    def _descartar_arquivo_parcial(self):
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
        except OSError:
            # A falha original é mais informativa do que a falha de limpeza.
            pass
