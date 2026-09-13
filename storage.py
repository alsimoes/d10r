#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
Armazenamento SQLite do d10r (schema v1).

Este módulo concentra as entidades SQLModel que representam as tabelas, os DTOs
Pydantic que validam snapshots antes de qualquer gravação, a fábrica injetável de
engines, o bootstrap explícito do schema v1, o repositório transacional e a
importação única do INI legado.

O INI é apenas entrada transitória de parâmetros: é lido uma única vez, quando o
SQLite ainda não existe, e removido pelo caminho exato depois de um banco íntegro
existir. Nunca é backend, formato de saída nem fallback de recuperação.

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

import codecs
import datetime
import os
import tempfile
from configparser import ConfigParser, Error as ConfigParserError
from contextlib import contextmanager
from typing import Annotated, Optional, Union

from pydantic import (BaseModel, ConfigDict, Field, ValidationError,
                      field_validator, model_validator)
from sqlmodel import (CheckConstraint, Field as SQLField, Session, SQLModel,
                      create_engine, delete, select, text)


# Versão do schema gravada no metadado singleton. Este sprint só conhece a v1 e
# nunca tenta atualizar um banco já existente.
SCHEMA_VERSION = 1

# Chave primária fixa das tabelas singleton.
SINGLETON_ID = 1

# Seção e codificação do INI legado, replicadas do formato antigo para que os
# arquivos existentes continuem legíveis na importação única.
LEGACY_HEADER = '__header__'
LEGACY_ENCODING = 'utf-8'

# Prefixo do banco temporário de uma tentativa de importação. Cada tentativa cria
# o seu, no mesmo diretório do banco final, e nenhuma reutiliza o de outra.
TEMP_PREFIX = '.d10r-import-'


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

# Nome de seção que o INI de entrada reserva para os parâmetros semanais. O
# formato antigo descartava em silêncio uma atividade com esse nome; aqui ela é
# um erro explícito, para que nada seja persistido nem perdido sem aviso. O
# literal é repetido de propósito: `storage` não depende da facade.
RESERVED_ACTIVITY_NAME = '__header__'


class ActivitySnapshot(BaseModel):
    '''Atividade validada, pronta para persistência ou para o domínio.'''

    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)

    name: str = Field(min_length=1)
    pts: FiniteFloat
    saldo: FiniteFloat

    @field_validator('name')
    @classmethod
    def _nome_utilizavel(cls, valor):
        '''O nome é preservado como veio: nada de normalização.

        Só dois nomes são recusados — o nome em branco e o literal exato
        reservado pelo INI de entrada. A comparação é literal, de modo que
        variações com espaços ou outra caixa continuam sendo nomes válidos.'''
        if not valor.strip():
            raise ValueError('nome de atividade em branco')
        if valor == RESERVED_ACTIVITY_NAME:
            raise ValueError('nome de atividade reservado: %s'
                             % (RESERVED_ACTIVITY_NAME,))
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


# Resultado de `SQLiteStore.load_snapshot()`: um snapshot válido ou o estado
# tipado "não configurado", convertido na facade para o fluxo de primeira
# execução.
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

    def integrity_check(self):
        '''Valida o arquivo antes de ele ser usado como armazenamento.

        Reprova, nesta ordem: arquivo ausente, arquivo inacessível ou que não é
        um banco SQLite, `PRAGMA integrity_check` diferente de `ok`, metadado de
        schema ausente/duplicado e versão diferente da v1. Um banco v1 sem
        configuração passa: falta de configuração não é corrupção.'''
        self._exigir_arquivo()

        try:
            with self._engine() as engine:
                with engine.connect() as conexao:
                    resultado = [linha[0] for linha in
                                 conexao.execute(text('PRAGMA integrity_check'))]
                if resultado != ['ok']:
                    raise StorageError('Integridade do banco de dados inválida: %s'
                                       % ('; '.join(str(l) for l in resultado),))
                with Session(engine) as session:
                    self._exigir_metadado_v1(session)
        except StorageError:
            raise
        except Exception as erro:
            raise StorageError('Banco de dados inválido ou inacessível: %s'
                               % (self.path,)) from erro

    def load_snapshot(self):
        '''load_snapshot() -> ConfigSnapshot | Unconfigured

        Lê a configuração e as atividades numa única sessão. Devolve o estado
        tipado `UNCONFIGURED` quando o banco é v1 válido mas o singleton de
        configuração ainda não existe; qualquer outro desvio (metadado ausente,
        versão desconhecida, conteúdo que não valida) é erro de armazenamento.

        A ordem das atividades é a ordem de inserção, preservada pela chave
        técnica, para que a lista de prioridades do usuário não se embaralhe.'''
        self._exigir_arquivo()

        try:
            with self._session() as session:
                self._exigir_metadado_v1(session)

                config = session.get(AppConfigRow, SINGLETON_ID)
                if config is None:
                    return UNCONFIGURED

                # Os valores são extraídos dentro da sessão; nada é acessado
                # depois de a instância ser desanexada.
                parametros = {'toth': config.toth,
                              'inicio': config.inicio,
                              'last_credit_date': config.last_credit_date,
                              'acumular': config.acumular}
                atividades = [(linha.name, linha.pts, linha.saldo)
                              for linha in session.exec(
                                  select(ActivityRow).order_by(ActivityRow.id))]
        except StorageError:
            raise
        except Exception as erro:
            raise StorageError('Falha ao ler o banco de dados: %s'
                               % (self.path,)) from erro

        # A validação fica fora do bloco de I/O para que um conteúdo inválido não
        # seja confundido com uma falha de leitura.
        try:
            return ConfigSnapshot(
                activities=tuple(ActivitySnapshot(name=nome, pts=pts, saldo=saldo)
                                 for nome, pts, saldo in atividades),
                **parametros)
        except ValidationError as erro:
            raise StorageError('Conteúdo do banco de dados inválido: %s'
                               % (self.path,)) from erro

    def save_snapshot(self, snapshot):
        '''Grava o snapshot inteiro numa única transação.

        O singleton de configuração e o conjunto de atividades são substituídos
        juntos: ou a gravação completa acontece, ou o snapshot anterior fica
        intacto. Só aceita um `ConfigSnapshot` já validado, de modo que nomes
        reservados, duplicados ou floats não finitos não chegam ao banco.'''
        if not isinstance(snapshot, ConfigSnapshot):
            raise StorageError('save_snapshot() exige um ConfigSnapshot; '
                               'recebido %s.' % (type(snapshot).__name__,))
        self._exigir_arquivo()

        try:
            with self._session() as session:
                self._exigir_metadado_v1(session)

                # DELETE em massa, emitido de imediato: a substituição do
                # conjunto não pode depender da ordem em que a unidade de
                # trabalho do ORM resolveria remoções e inserções, porque o
                # índice único de `name` colide se um nome for reaproveitado
                # antes de a linha antiga sair.
                session.exec(delete(ActivityRow))

                config = session.get(AppConfigRow, SINGLETON_ID)
                if config is None:
                    config = AppConfigRow(id=SINGLETON_ID)
                    session.add(config)
                config.toth = snapshot.toth
                config.inicio = snapshot.inicio
                config.last_credit_date = snapshot.last_credit_date
                config.acumular = snapshot.acumular

                for atividade in snapshot.activities:
                    session.add(ActivityRow(name=atividade.name,
                                            pts=atividade.pts,
                                            saldo=atividade.saldo))

                # Único commit da operação; qualquer falha antes dele deixa a
                # sessão ser fechada e desfeita pelo gerenciador de contexto.
                session.commit()
        except StorageError:
            raise
        except Exception as erro:
            raise StorageError('Falha ao gravar o banco de dados: %s'
                               % (self.path,)) from erro

    def _exigir_metadado_v1(self, session):
        '''Exige exatamente um metadado de schema e que ele seja a v1.

        A ausência do metadado num arquivo preexistente é corrupção, e uma versão
        desconhecida nunca é aberta nem migrada em silêncio.'''
        versoes = [linha.version
                   for linha in session.exec(select(SchemaVersionRow))]

        if len(versoes) != 1:
            raise StorageError('Metadado de schema ausente ou duplicado: %s'
                               % (self.path,))
        if versoes[0] != SCHEMA_VERSION:
            raise StorageError('Versão de schema desconhecida: %r (esperada %r).'
                               % (versoes[0], SCHEMA_VERSION))

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


# --- Importação única do INI legado ----------------------------------------

def read_legacy_ini(legacy_ini_path):
    '''read_legacy_ini(legacy_ini_path) -> ConfigSnapshot

    Leitor puro: lê o INI inteiro em memória e devolve um snapshot validado.

    Não registra `Atividade`, não cria, grava nem apaga arquivo nenhum e não
    conhece o banco. Uma seção malformada depois de uma seção válida não deixa
    nada pela metade, porque nada é publicado antes de o snapshot inteiro
    validar. Qualquer desvio vira `StorageError` com a causa preservada, e o
    arquivo de entrada fica exatamente como estava.'''
    parser = ConfigParser()

    try:
        with codecs.open(os.fspath(legacy_ini_path), 'r',
                         LEGACY_ENCODING) as arquivo:
            parser.read_file(arquivo)
    except OSError as erro:
        raise StorageError('Arquivo legado inexistente ou ilegível: %s'
                           % (legacy_ini_path,)) from erro
    except (UnicodeError, ConfigParserError, ValueError) as erro:
        raise StorageError('Arquivo legado corrompido: %s'
                           % (legacy_ini_path,)) from erro

    try:
        toth = parser.getint(LEGACY_HEADER, 'disponivel')
        inicio = parser.getint(LEGACY_HEADER, 'inicio')
        timestamp = parser.getint(LEGACY_HEADER, 'timestamp')
        # A chave só apareceu no modo acumulativo; um INI anterior a ela vale
        # como acumulativo, igual ao formato antigo.
        acumular = parser.getboolean(LEGACY_HEADER, 'acumular', fallback=True)
        atividades = [(secao,
                       parser.getfloat(secao, 'pts'),
                       parser.getfloat(secao, 'saldo'))
                      for secao in parser.sections() if secao != LEGACY_HEADER]
    except (TypeError, ValueError, ConfigParserError) as erro:
        raise StorageError('Arquivo legado corrompido: %s'
                           % (legacy_ini_path,)) from erro

    try:
        return ConfigSnapshot(
            toth=toth,
            inicio=inicio,
            last_credit_date=_data_do_timestamp_legado(timestamp),
            acumular=acumular,
            activities=tuple(ActivitySnapshot(name=nome, pts=pts, saldo=saldo)
                             for nome, pts, saldo in atividades),
        )
    except (ValidationError, ValueError) as erro:
        raise StorageError('Parâmetros legados inválidos: %s'
                           % (legacy_ini_path,)) from erro


def remove_legacy_ini_exact(legacy_ini_path):
    '''Remove exatamente este caminho — nunca um padrão, nunca um glob.

    Arquivos irmãos (backups, cópias, sufixos) não são candidatos: só o caminho
    de entrada injetado é apagado. Já não existir não é erro; falhar em apagar é,
    e o chamador precisa tratar, porque nesse ponto o banco já é autoritativo.'''
    try:
        os.remove(os.fspath(legacy_ini_path))
    except FileNotFoundError:
        return
    except OSError as erro:
        raise StorageError('Falha ao remover o arquivo legado: %s'
                           % (legacy_ini_path,)) from erro


def import_legacy_ini(legacy_ini_path, db_path):
    '''import_legacy_ini(legacy_ini_path, db_path) -> SQLiteStore

    Importa os parâmetros do INI uma única vez e promove um SQLite íntegro.

    A ordem é: ler o INI inteiro, validar em DTOs, criar um temporário único no
    mesmo diretório do banco final, gravar o snapshot numa transação, verificar
    integridade e reler/comparar, descartar engines, promover com `os.replace()`
    e só então remover o INI pelo caminho exato.

    Qualquer falha antes da promoção remove apenas o temporário desta tentativa,
    não deixa banco final parcial e **preserva o INI** — preservar a entrada de
    uma importação que não chegou a um banco íntegro não é fallback: o chamador
    recebe erro e não usa esses valores. Depois da promoção, o banco já é
    autoritativo; se a remoção do INI falhar, o erro sobe e a próxima execução
    repete somente a remoção, sem reimportar.'''
    destino = SQLiteStore(db_path)
    if destino.exists():
        # O INI só é entrada quando o SQLite não existe; promover sobre um banco
        # existente sobrescreveria dados já convertidos.
        raise StorageError('Banco de dados já existe; importação recusada: %s'
                           % (destino.path,))

    snapshot = read_legacy_ini(legacy_ini_path)

    temporario = _reservar_temporario(destino.path)
    promovido = False
    try:
        try:
            parcial = SQLiteStore(temporario,
                                  engine_factory=destino._engine_factory)
            parcial.bootstrap_v1()
            parcial.save_snapshot(snapshot)

            # Releitura completa antes de qualquer promoção: só um banco que
            # devolve exatamente o mesmo snapshot autoriza o corte.
            parcial.integrity_check()
            if parcial.load_snapshot() != snapshot:
                raise StorageError(
                    'Releitura do banco importado divergiu do INI: %s'
                    % (legacy_ini_path,))

            # As operações acima já descartaram os seus engines; nenhum handle
            # fica aberto sobre o temporário, o que o Windows exige para renomear.
            os.replace(temporario, destino.path)
            promovido = True
        except StorageError:
            raise
        except Exception as erro:
            # A importação é fronteira: nada de exceção crua escapa para o
            # chamador, e a causa original é sempre encadeada.
            raise StorageError('Falha ao importar o arquivo legado: %s'
                               % (legacy_ini_path,)) from erro
    finally:
        if not promovido:
            _remover_temporario(temporario)

    # Última etapa, e só agora: o banco final já está íntegro no disco.
    remove_legacy_ini_exact(legacy_ini_path)

    return destino


def ensure_storage(db_path, legacy_ini_path):
    '''ensure_storage(db_path, legacy_ini_path) -> SQLiteStore

    Resolve o estado inicial do armazenamento em uma única decisão explícita:

    - banco presente: validar. Inválido ou inacessível vira erro sem consultar
      nem apagar o INI; válido vence, e um INI que ainda exista é removido pelo
      caminho exato **sem ser lido**;
    - banco ausente e INI presente: importar uma vez, promover e remover o INI;
    - banco ausente e INI ausente: criar o schema v1 vazio e seguir para a
      configuração inicial.

    Não existe seleção de INI alternativo, procura manual, cópia para o perfil
    nem fallback: ambos os caminhos são injetados pelo chamador.'''
    destino = SQLiteStore(db_path)

    if destino.exists():
        destino.integrity_check()
        if os.path.exists(os.fspath(legacy_ini_path)):
            # Banco válido vence: o INI não é lido, apenas removido.
            remove_legacy_ini_exact(legacy_ini_path)
        return destino

    if os.path.exists(os.fspath(legacy_ini_path)):
        return import_legacy_ini(legacy_ini_path, db_path)

    destino.bootstrap_v1()
    return destino


def _data_do_timestamp_legado(timestamp):
    '''Converte o `AAAAMMDD` do INI em data; `0` significa "nenhum crédito".'''
    if not timestamp:
        return None

    ano, resto = divmod(timestamp, 10000)
    mes, dia = divmod(resto, 100)
    return datetime.date(ano, mes, dia)


def _reservar_temporario(db_path):
    '''Reserva um nome de temporário único no mesmo diretório do banco final.

    O nome vem de `mkstemp`, que garante unicidade; o arquivo vazio é removido em
    seguida porque o bootstrap se recusa, por contrato, a tocar num arquivo que
    já existe. Ficar no mesmo diretório é o que torna a promoção por `os.replace`
    uma troca atômica, e não uma cópia entre volumes.'''
    diretorio = os.path.dirname(os.path.abspath(db_path)) or '.'
    descritor, caminho = tempfile.mkstemp(dir=diretorio, prefix=TEMP_PREFIX,
                                         suffix='.sqlite3')
    os.close(descritor)
    os.remove(caminho)
    return caminho


def _remover_temporario(caminho):
    '''Limpa somente o temporário desta tentativa, pelo caminho exato.'''
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
    except OSError:
        # A falha original da importação é mais informativa do que esta.
        pass
