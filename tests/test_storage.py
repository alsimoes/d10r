'''Testes da fundação de armazenamento (schema v1).

Nenhum teste deste arquivo toca o perfil real do usuário: todo banco vive em
`tmp_path` e todo caminho é injetado explicitamente.
'''

import contextlib
import datetime
import math
import os
import sqlite3
import subprocess
import sys

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

import storage
from storage import (UNCONFIGURED, ActivityRow, ActivitySnapshot, AppConfigRow,
                    ConfigSnapshot, SQLiteStore, SchemaVersionRow, StorageError,
                    Unconfigured)


@pytest.fixture
def db_path(tmp_path):
    '''Caminho de um banco que ainda não existe.'''
    return tmp_path / '.d10r.sqlite3'


@pytest.fixture
def store(db_path):
    '''Armazenamento já inicializado com o schema v1 vazio.'''
    loja = SQLiteStore(db_path)
    loja.bootstrap_v1()
    return loja


@pytest.fixture
def snapshot():
    '''Snapshot completo: Unicode, saldo negativo e data de crédito.'''
    return ConfigSnapshot(
        toth=20,
        inicio=3,
        last_credit_date=datetime.date(2024, 1, 1),
        acumular=False,
        activities=(
            ActivitySnapshot(name='Café ☕', pts=0.6, saldo=-999.5),
            ActivitySnapshot(name='Programação', pts=0.4, saldo=10.25),
        ),
    )


@pytest.fixture
def store_configurado(store, snapshot):
    '''Armazenamento com um snapshot já gravado.'''
    store.save_snapshot(snapshot)
    return store


def sql_bruto(caminho, *comandos):
    '''Executa SQL direto, para fabricar estados que a API nunca produziria.'''
    with contextlib.closing(sqlite3.connect(str(caminho))) as conexao:
        for comando in comandos:
            conexao.execute(comando)
        conexao.commit()


# --- Snapshots (DTOs) ------------------------------------------------------

def test_activity_snapshot_aceita_campos_validos():
    atividade = ActivitySnapshot(name='Estudar', pts=0.5, saldo=-3.5)
    assert (atividade.name, atividade.pts, atividade.saldo) == ('Estudar', 0.5, -3.5)


def test_activity_snapshot_aceita_int_onde_float_e_esperado():
    # O INI legado grava "saldo = 10"; getfloat devolve float, mas um int não
    # pode ser recusado sem quebrar parâmetros antes aceitos.
    atividade = ActivitySnapshot(name='Trabalho', pts=1, saldo=10)
    assert atividade.pts == 1.0 and atividade.saldo == 10.0


@pytest.mark.parametrize('campo', ['pts', 'saldo'])
@pytest.mark.parametrize('valor', [float('nan'), float('inf'), float('-inf')])
def test_activity_snapshot_rejeita_float_nao_finito(campo, valor):
    campos = {'name': 'A1', 'pts': 0.5, 'saldo': 0.0}
    campos[campo] = valor
    with pytest.raises(ValidationError):
        ActivitySnapshot(**campos)


@pytest.mark.parametrize('nome', ['', '   ', '\t'])
def test_activity_snapshot_rejeita_nome_em_branco(nome):
    with pytest.raises(ValidationError):
        ActivitySnapshot(name=nome, pts=0.5, saldo=0.0)


def test_activity_snapshot_preserva_o_nome_como_veio():
    # Validar não é normalizar: o nome é dado do usuário.
    assert ActivitySnapshot(name=' Ler ', pts=0.5, saldo=0.0).name == ' Ler '


def test_activity_snapshot_rejeita_o_nome_reservado():
    # O INI antigo descartava em silêncio a atividade homônima da seção de
    # parâmetros; aqui o estado inválido nem chega a existir.
    with pytest.raises(ValidationError, match='reservado: __header__'):
        ActivitySnapshot(name=storage.RESERVED_ACTIVITY_NAME, pts=1.0, saldo=0.0)


@pytest.mark.parametrize('nome', [' __header__', '__header__ ', ' __header__ ',
                                  '__HEADER__', '_header_', '__header__x'])
def test_activity_snapshot_recusa_apenas_o_literal_reservado(nome):
    # A comparação é com o valor literal: nenhuma normalização nova foi
    # introduzida, então nomes vizinhos continuam válidos e preservados.
    assert ActivitySnapshot(name=nome, pts=0.5, saldo=0.0).name == nome


def test_config_snapshot_nao_se_constroi_com_nome_reservado():
    # Montar a tupla de atividades já falha, antes de existir um ConfigSnapshot.
    with pytest.raises(ValidationError, match='reservado'):
        ConfigSnapshot(
            toth=20, inicio=1, acumular=True,
            activities=(
                ActivitySnapshot(name='Ler', pts=0.5, saldo=0.0),
                ActivitySnapshot(name=storage.RESERVED_ACTIVITY_NAME,
                                 pts=0.5, saldo=0.0),
            ),
        )


def test_config_snapshot_rejeita_nome_reservado_em_atividade_aninhada():
    # Mesmo pela validação aninhada (única via em que o DTO recebe dados
    # brutos), o nome reservado é recusado e aponta a posição exata.
    dados = {
        'toth': 20, 'inicio': 1, 'acumular': True,
        'activities': [
            {'name': 'Ler', 'pts': 0.5, 'saldo': 0.0},
            {'name': storage.RESERVED_ACTIVITY_NAME, 'pts': 0.5, 'saldo': 0.0},
        ],
    }
    with pytest.raises(ValidationError) as erro:
        ConfigSnapshot.model_validate(dados, strict=False)

    locais = [e['loc'] for e in erro.value.errors()]
    assert ('activities', 1, 'name') in locais
    assert 'reservado: __header__' in str(erro.value)


@pytest.mark.parametrize('campos', [
    {'name': 'A1', 'pts': '0.5', 'saldo': 0.0},  # str não é float
    {'name': 'A1', 'pts': 0.5, 'saldo': None},   # saldo é obrigatório
    {'name': 123, 'pts': 0.5, 'saldo': 0.0},     # nome não é str
])
def test_activity_snapshot_rejeita_tipos_invalidos(campos):
    with pytest.raises(ValidationError):
        ActivitySnapshot(**campos)


def test_config_snapshot_aceita_estado_completo():
    snapshot = ConfigSnapshot(
        toth=20,
        inicio=7,
        last_credit_date=datetime.date(2024, 1, 1),
        acumular=False,
        activities=(
            ActivitySnapshot(name='Programação', pts=0.6, saldo=10.0),
            ActivitySnapshot(name='Academia', pts=0.4, saldo=-2.5),
        ),
    )
    assert snapshot.last_credit_date == datetime.date(2024, 1, 1)
    assert snapshot.acumular is False
    assert [a.name for a in snapshot.activities] == ['Programação', 'Academia']


def test_config_snapshot_sem_credito_e_sem_atividades():
    # Estado logo após a primeira configuração: nenhum crédito registrado.
    snapshot = ConfigSnapshot(toth=20, inicio=1, acumular=True)
    assert snapshot.last_credit_date is None
    assert snapshot.activities == ()


@pytest.mark.parametrize('inicio', [0, 8, -1])
def test_config_snapshot_exige_inicio_iso(inicio):
    with pytest.raises(ValidationError):
        ConfigSnapshot(toth=20, inicio=inicio, acumular=True)


@pytest.mark.parametrize('inicio', [1, 2, 3, 4, 5, 6, 7])
def test_config_snapshot_aceita_todo_o_intervalo_iso(inicio):
    assert ConfigSnapshot(toth=20, inicio=inicio, acumular=True).inicio == inicio


def test_config_snapshot_rejeita_nomes_duplicados():
    with pytest.raises(ValidationError, match='duplicados'):
        ConfigSnapshot(
            toth=20, inicio=1, acumular=True,
            activities=(
                ActivitySnapshot(name='Ler', pts=0.5, saldo=0.0),
                ActivitySnapshot(name='Ler', pts=0.5, saldo=1.0),
            ),
        )


@pytest.mark.parametrize('campos', [
    {'last_credit_date': '2024-01-01'},              # str não é date
    {'last_credit_date': 20240101},                  # int não é date
    {'acumular': 'True'},                            # str não é bool
    {'toth': '20'},                                  # str não é int
    {'activities': [ActivitySnapshot(name='A1', pts=0.5, saldo=0.0)]},  # lista não é tupla
    {'extra': 1},                                    # campo desconhecido
])
def test_config_snapshot_rejeita_entrada_nao_validada(campos):
    base = {'toth': 20, 'inicio': 1, 'acumular': True}
    base.update(campos)
    with pytest.raises(ValidationError):
        ConfigSnapshot(**base)


def test_snapshots_sao_imutaveis():
    snapshot = ConfigSnapshot(toth=20, inicio=1, acumular=True)
    with pytest.raises(ValidationError):
        snapshot.toth = 30


# --- Estado tipado "não configurado" ---------------------------------------

def test_unconfigured_e_singleton_e_distinto_de_snapshot():
    assert Unconfigured() is UNCONFIGURED
    assert repr(UNCONFIGURED) == 'UNCONFIGURED'
    assert not isinstance(UNCONFIGURED, ConfigSnapshot)


def test_banco_v1_novo_nao_esta_configurado(store):
    # Um banco recém-criado pode existir sem configuração até o questionário
    # inicial concluir; isso não é corrupção.
    assert store.is_configured() is False
    assert store.schema_version() == storage.SCHEMA_VERSION == 1


# --- Bootstrap e schema ----------------------------------------------------

def test_bootstrap_cria_o_arquivo_no_diretorio_indicado(db_path):
    loja = SQLiteStore(db_path)
    assert loja.exists() is False
    loja.bootstrap_v1()
    assert loja.exists() is True
    assert db_path.is_file()


def test_bootstrap_cria_exatamente_o_schema_v1(store):
    engine = storage.create_engine_for(store.path)
    try:
        inspetor = inspect(engine)
        assert sorted(inspetor.get_table_names()) == ['activity', 'app_config',
                                                      'schema_version']

        colunas = {tabela: {c['name']: c['nullable']
                            for c in inspetor.get_columns(tabela)}
                   for tabela in inspetor.get_table_names()}
        assert colunas['schema_version'] == {'id': False, 'version': False}
        assert colunas['app_config'] == {'id': False, 'toth': False,
                                        'inicio': False,
                                        'last_credit_date': True,
                                        'acumular': False}
        assert colunas['activity'] == {'id': False, 'name': False,
                                      'pts': False, 'saldo': False}

        indices = inspetor.get_indexes('activity')
        assert [(i['column_names'], bool(i['unique'])) for i in indices] == \
               [(['name'], True)]

        restricoes = {tabela: {c['name'] for c in
                               inspetor.get_check_constraints(tabela)}
                      for tabela in inspetor.get_table_names()}
        assert restricoes['schema_version'] == {'ck_schema_version_singleton'}
        assert restricoes['app_config'] == {'ck_app_config_singleton',
                                            'ck_app_config_inicio_iso'}
    finally:
        engine.dispose()


def test_bootstrap_deixa_apenas_o_metadado_de_versao(store):
    engine = storage.create_engine_for(store.path)
    try:
        with Session(engine) as sessao:
            versoes = sessao.exec(select(SchemaVersionRow)).all()
            assert [(v.id, v.version) for v in versoes] == [(1, 1)]
            assert sessao.exec(select(AppConfigRow)).all() == []
            assert sessao.exec(select(ActivityRow)).all() == []
    finally:
        engine.dispose()


def test_bootstrap_recusa_banco_existente(store):
    # create_all() nunca deve ser usado para atualizar um banco já criado.
    with pytest.raises(StorageError, match='já existe'):
        store.bootstrap_v1()


def test_bootstrap_nao_deixa_arquivo_parcial_quando_falha(db_path):
    def fabrica_quebrada(caminho, echo=False):
        raise RuntimeError('engine indisponível')

    loja = SQLiteStore(db_path, engine_factory=fabrica_quebrada)
    with pytest.raises(StorageError) as erro:
        loja.bootstrap_v1()
    assert isinstance(erro.value.__cause__, RuntimeError)
    assert loja.exists() is False


def test_bootstrap_remove_o_arquivo_quando_o_commit_falha(db_path, monkeypatch):
    existia_no_erro = []

    class SessaoQuebrada(storage.Session):
        def commit(self):
            # O arquivo já foi criado por create_all() neste ponto.
            existia_no_erro.append(os.path.exists(db_path))
            raise RuntimeError('commit indisponível')

    monkeypatch.setattr(storage, 'Session', SessaoQuebrada)
    loja = SQLiteStore(db_path)
    with pytest.raises(StorageError, match='schema v1'):
        loja.bootstrap_v1()

    assert existia_no_erro == [True]
    assert loja.exists() is False


# --- Restrições no banco ---------------------------------------------------

@pytest.mark.parametrize('linha, tabela', [
    (lambda: SchemaVersionRow(id=2, version=1), 'schema_version'),
    (lambda: AppConfigRow(id=2, toth=20, inicio=1, acumular=True), 'app_config'),
])
def test_banco_recusa_segunda_linha_em_tabela_singleton(store, linha, tabela):
    engine = storage.create_engine_for(store.path)
    try:
        with Session(engine) as sessao:
            sessao.add(linha())
            with pytest.raises(IntegrityError):
                sessao.commit()
    finally:
        engine.dispose()


@pytest.mark.parametrize('inicio', [0, 8])
def test_banco_recusa_inicio_fora_do_intervalo_iso(store, inicio):
    engine = storage.create_engine_for(store.path)
    try:
        with Session(engine) as sessao:
            sessao.add(AppConfigRow(toth=20, inicio=inicio, acumular=True))
            with pytest.raises(IntegrityError):
                sessao.commit()
    finally:
        engine.dispose()


def test_banco_recusa_nomes_de_atividade_repetidos(store):
    engine = storage.create_engine_for(store.path)
    try:
        with Session(engine) as sessao:
            sessao.add(ActivityRow(name='Ler', pts=0.5, saldo=0.0))
            sessao.add(ActivityRow(name='Ler', pts=0.5, saldo=1.0))
            with pytest.raises(IntegrityError):
                sessao.commit()
    finally:
        engine.dispose()


# --- Caminhos injetáveis e ausência de estado global -----------------------

def test_engine_factory_e_injetavel(db_path):
    chamadas = []

    def fabrica(caminho, echo=False):
        chamadas.append(caminho)
        return storage.create_engine_for(caminho, echo=echo)

    loja = SQLiteStore(db_path, engine_factory=fabrica)
    loja.bootstrap_v1()
    assert chamadas == [str(db_path)]


def test_leitura_de_banco_inexistente_falha_sem_criar_arquivo(db_path, tmp_path):
    loja = SQLiteStore(db_path)
    for operacao in (loja.schema_version, loja.is_configured):
        with pytest.raises(StorageError, match='inexistente'):
            operacao()
    assert list(tmp_path.iterdir()) == []


def test_arquivo_pode_ser_removido_logo_apos_as_operacoes(store):
    # No Windows, um engine não descartado manteria o arquivo bloqueado.
    store.schema_version()
    store.is_configured()
    os.remove(store.path)
    assert store.exists() is False


def test_caminhos_padrao_sao_resolvidos_na_chamada(monkeypatch):
    pedidos = []

    def expanduser_falso(caminho):
        pedidos.append(caminho)
        return caminho.replace('~', '/lar-falso')

    monkeypatch.setattr('os.path.expanduser', expanduser_falso)
    assert storage.default_db_path() == '/lar-falso/.d10r.sqlite3'
    assert storage.default_legacy_ini_path() == '/lar-falso/.d10r'
    assert pedidos == ['~/.d10r.sqlite3', '~/.d10r']


def test_import_nao_cria_arquivos_nem_le_o_home(tmp_path):
    raiz = os.path.dirname(os.path.abspath(storage.__file__))
    lar = tmp_path / 'lar'
    lar.mkdir()

    ambiente = dict(os.environ)
    ambiente['HOME'] = str(lar)
    ambiente['USERPROFILE'] = str(lar)
    for chave in ('HOMEDRIVE', 'HOMEPATH'):
        ambiente.pop(chave, None)

    codigo = ('import os, sys\n'
              'sys.path.insert(0, %r)\n'
              'import storage\n'
              'print(os.path.expanduser("~"))\n' % raiz)
    # -B evita escrever __pycache__ na árvore do projeto durante o teste.
    resultado = subprocess.run([sys.executable, '-B', '-c', codigo],
                               cwd=str(tmp_path), env=ambiente,
                               capture_output=True, text=True)

    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == str(lar)
    # O import não pode criar banco, INI ou qualquer outro arquivo.
    assert list(lar.iterdir()) == []
    assert list(tmp_path.iterdir()) == [lar]


def test_modulo_nao_expoe_engine_nem_sessao_global():
    for atributo in ('engine', 'ENGINE', 'session', 'SESSION', 'CONFIG', 'DB'):
        assert not hasattr(storage, atributo), atributo


def test_snapshot_admite_valores_numericos_de_fronteira():
    # Garante que a validação de finitude não rejeita extremos legítimos.
    grande = ConfigSnapshot(
        toth=0, inicio=1, acumular=True,
        activities=(ActivitySnapshot(name='A1', pts=0.0,
                                     saldo=-1.7976931348623157e+308),),
    )
    assert math.isfinite(grande.activities[0].saldo)


# --- integrity_check -------------------------------------------------------

def test_integrity_check_aprova_banco_v1_recem_criado(store):
    # Falta de configuração não é corrupção.
    assert store.integrity_check() is None
    assert store.load_snapshot() is UNCONFIGURED


def test_integrity_check_aprova_banco_configurado(store_configurado):
    assert store_configurado.integrity_check() is None


# --- Round-trip ------------------------------------------------------------

def test_round_trip_preserva_o_snapshot_inteiro(store, snapshot):
    store.save_snapshot(snapshot)
    assert store.load_snapshot() == snapshot


def test_round_trip_preserva_unicode_e_saldo_negativo(store_configurado, snapshot):
    lido = store_configurado.load_snapshot()
    assert [a.name for a in lido.activities] == ['Café ☕', 'Programação']
    assert lido.activities[0].saldo == -999.5


@pytest.mark.parametrize('quantidade', [0, 1, 5])
def test_round_trip_com_zero_uma_e_n_atividades(store, quantidade):
    entrada = ConfigSnapshot(
        toth=40, inicio=1, acumular=True,
        activities=tuple(ActivitySnapshot(name='A%d' % i, pts=0.1 * i, saldo=float(i))
                         for i in range(quantidade)),
    )
    store.save_snapshot(entrada)
    lido = store.load_snapshot()
    assert lido == entrada
    assert len(lido.activities) == quantidade


def test_round_trip_preserva_last_credit_date_nulo(store):
    # NULL continua NULL aqui; a conversão para o `timestamp = 0` público é da
    # facade, no ticket 05.
    entrada = ConfigSnapshot(toth=20, inicio=1, acumular=True,
                             activities=(ActivitySnapshot(name='A1', pts=1.0,
                                                          saldo=0.0),))
    store.save_snapshot(entrada)
    lido = store.load_snapshot()
    assert lido.last_credit_date is None
    assert lido == entrada


@pytest.mark.parametrize('acumular', [True, False])
def test_round_trip_preserva_acumular(store, acumular):
    store.save_snapshot(ConfigSnapshot(toth=20, inicio=1, acumular=acumular))
    assert store.load_snapshot().acumular is acumular


@pytest.mark.parametrize('inicio', [1, 4, 7])
def test_round_trip_preserva_inicio_em_todo_o_intervalo(store, inicio):
    store.save_snapshot(ConfigSnapshot(toth=20, inicio=inicio, acumular=True))
    assert store.load_snapshot().inicio == inicio


def test_round_trip_preserva_a_ordem_das_atividades(store):
    # A ordem da lista é a ordem de prioridade que o usuário montou com
    # Subir/Descer; embaralhá-la seria regressão visível.
    nomes = ['Zelar', 'Aprender', 'Malhar', 'Beta', 'Alfa']
    store.save_snapshot(ConfigSnapshot(
        toth=20, inicio=1, acumular=True,
        activities=tuple(ActivitySnapshot(name=n, pts=0.2, saldo=0.0)
                         for n in nomes),
    ))
    assert [a.name for a in store.load_snapshot().activities] == nomes


# --- Atualização e remoção -------------------------------------------------

def test_save_snapshot_configura_um_banco_v1_vazio(store, snapshot):
    assert store.is_configured() is False
    store.save_snapshot(snapshot)
    assert store.is_configured() is True
    assert store.load_snapshot() == snapshot


def test_save_snapshot_substitui_o_conjunto_de_atividades(store_configurado):
    novo = ConfigSnapshot(
        toth=30, inicio=5, last_credit_date=datetime.date(2025, 6, 2),
        acumular=True,
        activities=(ActivitySnapshot(name='Dormir', pts=1.0, saldo=2.0),),
    )
    store_configurado.save_snapshot(novo)

    lido = store_configurado.load_snapshot()
    assert lido == novo
    assert [a.name for a in lido.activities] == ['Dormir']


def test_save_snapshot_reaproveita_nomes_sem_violar_o_indice_unico(store_configurado,
                                                                  snapshot):
    # Renomear/atualizar mantendo os mesmos nomes é o caso em que o índice único
    # de `name` quebraria se a substituição inserisse antes de remover.
    atualizado = snapshot.model_copy(update={'activities': tuple(
        ActivitySnapshot(name=a.name, pts=a.pts, saldo=a.saldo + 1.0)
        for a in snapshot.activities)})
    store_configurado.save_snapshot(atualizado)

    lido = store_configurado.load_snapshot()
    assert [a.name for a in lido.activities] == [a.name for a in snapshot.activities]
    assert [a.saldo for a in lido.activities] == [-998.5, 11.25]


def test_save_snapshot_remove_todas_as_atividades(store_configurado):
    store_configurado.save_snapshot(
        ConfigSnapshot(toth=20, inicio=1, acumular=True, activities=()))

    assert store_configurado.load_snapshot().activities == ()
    engine = storage.create_engine_for(store_configurado.path)
    try:
        with Session(engine) as sessao:
            assert sessao.exec(select(ActivityRow)).all() == []
    finally:
        engine.dispose()


def test_save_snapshot_nao_duplica_o_singleton(store_configurado, snapshot):
    store_configurado.save_snapshot(snapshot.model_copy(update={'toth': 99}))

    engine = storage.create_engine_for(store_configurado.path)
    try:
        with Session(engine) as sessao:
            configs = sessao.exec(select(AppConfigRow)).all()
            assert [(c.id, c.toth) for c in configs] == [(1, 99)]
            versoes = sessao.exec(select(SchemaVersionRow)).all()
            assert [(v.id, v.version) for v in versoes] == [(1, 1)]
    finally:
        engine.dispose()


def test_save_snapshot_recusa_objeto_que_nao_e_snapshot(store):
    for invalido in ({'toth': 20}, None, 'snapshot'):
        with pytest.raises(StorageError, match='ConfigSnapshot'):
            store.save_snapshot(invalido)
    assert store.is_configured() is False


# --- Rollback --------------------------------------------------------------

SNAPSHOT_INTRUSO = ConfigSnapshot(
    toth=999, inicio=7, acumular=True,
    activities=(ActivitySnapshot(name='Intruso', pts=1.0, saldo=42.0),),
)


@pytest.fixture(params=['no-commit', 'no-meio-da-transacao'])
def gravacao_que_falha(request, monkeypatch):
    '''Injeta a falha em dois pontos distintos da gravação.

    `no-commit` deixa o flush emitir DELETE e INSERTs e só então falha.
    `no-meio-da-transacao` falha depois de o DELETE das atividades já ter sido
    enviado ao banco, mas antes do commit — é a injeção que distingue uma
    transação única de uma sequência de commits parciais. A carga do ORM não
    passa por `__init__`, então a releitura seguinte continua funcionando.'''
    if request.param == 'no-commit':
        class SessaoQuebrada(storage.Session):
            def commit(self):
                self.flush()
                raise RuntimeError('commit indisponível')

        monkeypatch.setattr(storage, 'Session', SessaoQuebrada)
    else:
        def init_quebrado(self, **kwargs):
            raise RuntimeError('linha inválida')

        monkeypatch.setattr(storage.ActivityRow, '__init__', init_quebrado)
    return request.param


def test_save_snapshot_preserva_o_snapshot_anterior_quando_falha(
        store_configurado, snapshot, gravacao_que_falha):
    with pytest.raises(StorageError, match='gravar'):
        store_configurado.save_snapshot(SNAPSHOT_INTRUSO)

    # Nada da tentativa sobrevive, nem mesmo as remoções já enviadas ao banco.
    assert store_configurado.load_snapshot() == snapshot


def test_save_snapshot_falho_nao_deixa_atividade_parcial(store_configurado,
                                                         gravacao_que_falha):
    with pytest.raises(StorageError):
        store_configurado.save_snapshot(SNAPSHOT_INTRUSO)

    engine = storage.create_engine_for(store_configurado.path)
    try:
        with Session(engine) as sessao:
            nomes = [linha.name for linha in sessao.exec(select(ActivityRow))]
    finally:
        engine.dispose()
    assert nomes == ['Café ☕', 'Programação']
    assert 'Intruso' not in nomes


def test_save_snapshot_falho_nao_altera_o_singleton(store_configurado, snapshot,
                                                    gravacao_que_falha):
    with pytest.raises(StorageError):
        store_configurado.save_snapshot(SNAPSHOT_INTRUSO)

    with contextlib.closing(sqlite3.connect(str(store_configurado.path))) as conexao:
        assert conexao.execute('SELECT toth, inicio FROM app_config').fetchall() \
               == [(snapshot.toth, snapshot.inicio)]


def test_falha_de_gravacao_preserva_a_causa_original(store_configurado,
                                                    gravacao_que_falha):
    with pytest.raises(StorageError) as erro:
        store_configurado.save_snapshot(SNAPSHOT_INTRUSO)
    assert isinstance(erro.value.__cause__, RuntimeError)


def test_banco_segue_utilizavel_depois_de_uma_gravacao_falha(store_configurado,
                                                            snapshot, monkeypatch):
    class SessaoQuebrada(storage.Session):
        def commit(self):
            self.flush()
            raise RuntimeError('commit indisponível')

    monkeypatch.setattr(storage, 'Session', SessaoQuebrada)
    with pytest.raises(StorageError):
        store_configurado.save_snapshot(
            ConfigSnapshot(toth=1, inicio=1, acumular=True))

    # Com a sessão normal de volta, a gravação seguinte funciona.
    monkeypatch.undo()
    novo = snapshot.model_copy(update={'toth': 7})
    store_configurado.save_snapshot(novo)
    assert store_configurado.load_snapshot() == novo


# --- Banco inválido, ausente e schema futuro -------------------------------

def test_operacoes_falham_sem_criar_banco_inexistente(db_path, tmp_path):
    loja = SQLiteStore(db_path)
    operacoes = [
        loja.integrity_check,
        loja.load_snapshot,
        lambda: loja.save_snapshot(ConfigSnapshot(toth=20, inicio=1, acumular=True)),
    ]
    for operacao in operacoes:
        with pytest.raises(StorageError, match='inexistente'):
            operacao()
    assert list(tmp_path.iterdir()) == []


def banco_zero_byte(caminho):
    caminho.write_bytes(b'')


def banco_bytes_aleatorios(caminho):
    caminho.write_bytes(b'isto nao e um banco de dados SQLite' * 8)


def banco_sem_tabelas(caminho):
    # Arquivo SQLite legítimo, mas sem nenhuma das tabelas do schema v1.
    sql_bruto(caminho, 'CREATE TABLE outra_coisa (x INTEGER)')


def banco_sem_metadado(caminho):
    SQLiteStore(caminho).bootstrap_v1()
    sql_bruto(caminho, 'DELETE FROM schema_version')


def banco_schema_futuro(caminho):
    SQLiteStore(caminho).bootstrap_v1()
    sql_bruto(caminho, 'UPDATE schema_version SET version = 2')


VARIANTES_INVALIDAS = [
    pytest.param(banco_zero_byte, id='zero-bytes'),
    pytest.param(banco_bytes_aleatorios, id='bytes-aleatorios'),
    pytest.param(banco_sem_tabelas, id='sem-tabelas'),
    pytest.param(banco_sem_metadado, id='sem-metadado'),
    pytest.param(banco_schema_futuro, id='schema-futuro'),
]


@pytest.mark.parametrize('fabricar', VARIANTES_INVALIDAS)
def test_integrity_check_reprova_banco_invalido(db_path, fabricar):
    fabricar(db_path)
    with pytest.raises(StorageError):
        SQLiteStore(db_path).integrity_check()


@pytest.mark.parametrize('fabricar', VARIANTES_INVALIDAS)
def test_load_snapshot_reprova_banco_invalido(db_path, fabricar):
    fabricar(db_path)
    with pytest.raises(StorageError):
        SQLiteStore(db_path).load_snapshot()


@pytest.mark.parametrize('fabricar', VARIANTES_INVALIDAS)
def test_save_snapshot_reprova_banco_invalido(db_path, fabricar):
    fabricar(db_path)
    with pytest.raises(StorageError):
        SQLiteStore(db_path).save_snapshot(
            ConfigSnapshot(toth=20, inicio=1, acumular=True))


def test_schema_futuro_falha_sem_tentar_migrar(db_path):
    banco_schema_futuro(db_path)
    loja = SQLiteStore(db_path)
    with pytest.raises(StorageError, match='desconhecida'):
        loja.load_snapshot()

    # Nem downgrade, nem create_all, nem qualquer escrita: o arquivo fica como
    # estava.
    with contextlib.closing(sqlite3.connect(str(db_path))) as conexao:
        assert conexao.execute('SELECT version FROM schema_version').fetchall() \
               == [(2,)]


def test_metadado_ausente_nao_e_confundido_com_nao_configurado(db_path, tmp_path):
    # Caminhos de código distintos: sem metadado é corrupção; sem configuração é
    # um banco novo e legítimo. Uma checagem frouxa ("a tabela existe?")
    # confundiria os dois.
    corrompido = tmp_path / 'corrompido.sqlite3'
    banco_sem_metadado(corrompido)
    with pytest.raises(StorageError, match='Metadado de schema'):
        SQLiteStore(corrompido).load_snapshot()

    novo = SQLiteStore(db_path)
    novo.bootstrap_v1()
    assert novo.load_snapshot() is UNCONFIGURED


def test_load_snapshot_recusa_conteudo_que_nao_valida(store_configurado):
    # Valor gravado fora da API: o DTO tem de reprovar em vez de propagar lixo.
    sql_bruto(store_configurado.path,
              "UPDATE activity SET pts = 'nao e numero' WHERE name = 'Café ☕'")
    with pytest.raises(StorageError, match='Conteúdo') as erro:
        store_configurado.load_snapshot()
    assert isinstance(erro.value.__cause__, ValidationError)


def test_load_snapshot_recusa_nome_reservado_gravado_diretamente(store_configurado):
    # O nome reservado não pode ser descartado em silêncio na leitura: ele é erro
    # explícito, como na validação do DTO.
    sql_bruto(store_configurado.path,
              "INSERT INTO activity (name, pts, saldo) "
              "VALUES ('__header__', 0.5, 1.0)")
    with pytest.raises(StorageError, match='Conteúdo') as erro:
        store_configurado.load_snapshot()
    assert 'reservado: __header__' in str(erro.value.__cause__)


def test_save_snapshot_nunca_grava_o_nome_reservado(store_configurado):
    # Não existe caminho: o snapshot com o nome reservado não chega a ser
    # construído, e o banco continua sem essa linha.
    with pytest.raises(ValidationError, match='reservado'):
        ConfigSnapshot(toth=20, inicio=1, acumular=True,
                       activities=(ActivitySnapshot(name='__header__', pts=0.5,
                                                    saldo=0.0),))

    with contextlib.closing(sqlite3.connect(str(store_configurado.path))) as conexao:
        assert conexao.execute(
            "SELECT count(*) FROM activity WHERE name = '__header__'"
        ).fetchone() == (0,)


# --- Handles e bloqueio no Windows -----------------------------------------

@contextlib.contextmanager
def sem_compartilhamento(caminho):
    '''Abre o arquivo com share mode 0, como um processo que trava o banco.'''
    import ctypes
    from ctypes import wintypes

    GENERIC_READ = 0x80000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    HANDLE_INVALIDO = ctypes.c_void_p(-1).value

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                                     wintypes.DWORD, wintypes.LPVOID,
                                     wintypes.DWORD, wintypes.DWORD,
                                     wintypes.HANDLE]
    handle = kernel32.CreateFileW(str(caminho), GENERIC_READ, 0, None,
                                  OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
    if handle == HANDLE_INVALIDO:
        raise OSError(ctypes.get_last_error(), 'CreateFileW falhou')
    try:
        yield
    finally:
        kernel32.CloseHandle(handle)


@pytest.mark.skipif(os.name != 'nt', reason='share mode é específico do Windows')
def test_banco_bloqueado_vira_erro_de_armazenamento_com_causa(store_configurado):
    operacoes = [
        store_configurado.integrity_check,
        store_configurado.load_snapshot,
        lambda: store_configurado.save_snapshot(
            ConfigSnapshot(toth=20, inicio=1, acumular=True)),
    ]
    with sem_compartilhamento(store_configurado.path):
        for operacao in operacoes:
            with pytest.raises(StorageError) as erro:
                operacao()
            # Mesma regra de "banco inválido/desconhecido", com a causa de SO
            # preservada por exception chaining.
            assert erro.value.__cause__ is not None


@pytest.mark.skipif(os.name != 'nt', reason='share mode é específico do Windows')
def test_banco_volta_a_funcionar_quando_o_bloqueio_termina(store_configurado,
                                                           snapshot):
    with sem_compartilhamento(store_configurado.path):
        with pytest.raises(StorageError):
            store_configurado.load_snapshot()
    assert store_configurado.load_snapshot() == snapshot


def test_arquivo_pode_ser_removido_logo_apos_gravar(store, snapshot):
    store.save_snapshot(snapshot)
    # Sem sleep e sem retry: se algum engine ficasse vivo, o Windows recusaria.
    os.remove(store.path)
    assert store.exists() is False


def test_arquivo_pode_ser_substituido_logo_apos_ler(store_configurado, tmp_path):
    store_configurado.load_snapshot()
    substituto = tmp_path / 'substituto.sqlite3'
    SQLiteStore(substituto).bootstrap_v1()

    os.replace(str(substituto), store_configurado.path)
    assert store_configurado.load_snapshot() is UNCONFIGURED


def test_store_nao_retem_engine_nem_sessao_entre_chamadas(store, snapshot):
    esperado = set(vars(store))
    store.save_snapshot(snapshot)
    store.load_snapshot()
    store.integrity_check()
    # Nenhum atributo novo: nada de engine ou sessão guardados na instância.
    assert set(vars(store)) == esperado


@pytest.mark.parametrize('operacao', ['load_snapshot', 'integrity_check',
                                      'save_snapshot'])
def test_cada_operacao_usa_um_unico_engine(store_configurado, operacao):
    engines = []

    def fabrica(caminho, echo=False):
        engine = storage.create_engine_for(caminho, echo=echo)
        engines.append(engine)
        return engine

    loja = SQLiteStore(store_configurado.path, engine_factory=fabrica)
    if operacao == 'save_snapshot':
        loja.save_snapshot(ConfigSnapshot(toth=20, inicio=1, acumular=True))
    else:
        getattr(loja, operacao)()

    assert len(engines) == 1
