'''Testes da fundação de armazenamento (schema v1).

Nenhum teste deste arquivo toca o perfil real do usuário: todo banco vive em
`tmp_path` e todo caminho é injetado explicitamente.
'''

import datetime
import math
import os
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
