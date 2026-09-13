import inspect
import pytest
import datetime
import os
import re
import subprocess
import sys

import data
import storage
from data import (ArquivoError, Atividade, ConfiguracaoAusente, salvar_config,
                  parse_config, creditar_tudo)

# Fixture para limpar as atividades antes de cada teste
@pytest.fixture(autouse=True)
def clear_atividades():
    Atividade.clear()


def escrever_ini(caminho, corpo):
    caminho.write_text(corpo, encoding='utf-8')
    return caminho


INI_COMPLETO = (
    '[__header__]\n'
    'disponivel = 20\n'
    'inicio = 1\n'
    'timestamp = 20240101\n'
    'acumular = False\n'
    '\n'
    '[Trabalho]\n'
    'pts = 0.6\n'
    'saldo = 10\n'
)


def test_atividade_creditar_debitar():
    # Cria uma atividade com 10% de prioridade (pts=0.1) e saldo zero
    ativ = Atividade(nome="Estudar", pts=0.1, saldo=0)
    
    # Simula o crédito de horas para uma semana de 40 horas
    ativ.creditarh(toth=40)
    assert ativ.saldo == 4.0  # 10% de 40 horas

    # Debita 1.5 horas
    ativ.debitarh(1.5)
    assert ativ.saldo == 2.5

def test_salvar_e_parse_config(perfil):
    # Cria dados de exemplo
    Atividade(nome="Trabalho", pts=0.6, saldo=10)
    Atividade(nome="Academia", pts=0.4, saldo=5)
    toth = 20
    inicio = 1 # Segunda-feira
    timestamp = datetime.date(2024, 1, 1)

    # Salva a configuração
    salvar_config(toth, inicio, timestamp, False)

    # Limpa as atividades da memória para forçar a leitura do arquivo
    Atividade.clear()
    
    # Lê a configuração
    parsed_toth, parsed_inicio, parsed_timestamp, parsed_acumular = parse_config()

    # Verifica se os dados foram lidos corretamente
    assert parsed_toth == toth
    assert parsed_inicio == inicio
    assert parsed_timestamp == timestamp
    assert parsed_acumular is False

    atividades_lidas = Atividade.all()
    assert len(atividades_lidas) == 2
    
    # Verifica os detalhes de uma das atividades
    trabalho = next(a for a in atividades_lidas if a.nome == "Trabalho")
    assert trabalho.pts == 0.6
    assert trabalho.saldo == 10


def test_parse_config_sem_armazenamento_pede_configuracao_inicial(perfil):
    # Sem banco e sem INI: cria o schema v1 vazio e sinaliza primeira execução.
    # `ConfiguracaoAusente` é ArquivoError, então quem já capturava continua
    # capturando.
    with pytest.raises(ConfiguracaoAusente, match='Nenhum arquivo') as erro:
        parse_config()
    assert isinstance(erro.value, ArquivoError)

    assert perfil.banco.exists()
    assert not perfil.ini.exists()
    assert storage.SQLiteStore(perfil.banco).schema_version() == 1
    assert Atividade.all() == []


def test_parse_config_banco_v1_vazio_continua_pedindo_configuracao(perfil):
    storage.SQLiteStore(perfil.banco).bootstrap_v1()
    with pytest.raises(ConfiguracaoAusente):
        parse_config()


@pytest.mark.parametrize('conteudo', ['', '[invalido', 'disponivel = 20\n'])
def test_parse_config_ini_invalido_falha_e_preserva_o_ini(perfil, conteudo):
    escrever_ini(perfil.ini, conteudo)
    with pytest.raises(ArquivoError, match='corrompido'):
        parse_config()
    # Falha antes da promoção preserva a entrada e não deixa banco final.
    assert perfil.ini.read_text(encoding='utf-8') == conteudo
    assert not perfil.banco.exists()

def test_parse_config_encoding_invalido_e_corrompido(perfil):
    perfil.ini.write_bytes(b'[__header__]\ndisponivel = 20\ninicio = 1\n\xff\xfe')
    with pytest.raises(ArquivoError, match='corrompido'):
        parse_config()

def test_parse_config_secao_malformada_nao_deixa_atividades(perfil):
    conteudo = (
        '[__header__]\n'
        'disponivel = 20\n'
        'inicio = 1\n'
        'timestamp = 20240101\n'
        '\n'
        '[Valida]\n'
        'pts = 0.5\n'
        'saldo = 10\n'
        '\n'
        '[Malformada]\n'
        'pts = meio\n'
        'saldo = 5\n'
    )
    escrever_ini(perfil.ini, conteudo)
    with pytest.raises(ArquivoError):
        parse_config()
    assert Atividade.all() == []

def test_parse_config_legado_sem_acumular_usa_fallback_true(perfil):
    escrever_ini(perfil.ini,
        '[__header__]\n'
        'disponivel = 20\n'
        'inicio = 1\n'
        'timestamp = 20240101\n')
    assert parse_config() == (20, 1, datetime.date(2024, 1, 1), True)


def test_parse_config_importa_o_ini_uma_vez_e_o_remove(perfil):
    escrever_ini(perfil.ini, INI_COMPLETO)

    assert parse_config() == (20, 1, datetime.date(2024, 1, 1), False)
    assert [(a.nome, a.pts, a.saldo) for a in Atividade.all()] == \
           [('Trabalho', 0.6, 10.0)]

    # Depois da importação validada, o INI não existe mais.
    assert not perfil.ini.exists()
    assert perfil.banco.exists()


def test_parse_config_repetido_nao_duplica_atividades(perfil):
    escrever_ini(perfil.ini, INI_COMPLETO)

    parse_config()
    parse_config()

    # O registro acontece sobre um conjunto limpo, e não acumulando.
    assert [a.nome for a in Atividade.all()] == ['Trabalho']


def test_parse_config_reinicio_nao_le_mais_o_ini(perfil, monkeypatch):
    escrever_ini(perfil.ini, INI_COMPLETO)
    primeira = parse_config()

    leituras = []
    original = storage.read_legacy_ini

    def espiao(caminho):
        leituras.append(caminho)
        return original(caminho)

    monkeypatch.setattr(storage, 'read_legacy_ini', espiao)
    Atividade.clear()

    assert parse_config() == primeira
    assert leituras == []


def test_parse_config_com_banco_valido_remove_o_ini_sem_ler(perfil, monkeypatch):
    # Banco já convertido, com valores diferentes dos do INI: se algum valor do
    # INI vazar, o teste detecta.
    Atividade(nome='Do banco', pts=1.0, saldo=3.0)
    salvar_config(40, 5, datetime.date(2025, 5, 5), True)
    Atividade.clear()
    escrever_ini(perfil.ini, INI_COMPLETO)

    leituras = []
    monkeypatch.setattr(storage, 'read_legacy_ini',
                        lambda caminho: leituras.append(caminho))

    assert parse_config() == (40, 5, datetime.date(2025, 5, 5), True)
    assert leituras == []
    assert not perfil.ini.exists()
    assert [a.nome for a in Atividade.all()] == ['Do banco']


def test_parse_config_banco_corrompido_nao_toca_o_ini(perfil, monkeypatch):
    perfil.banco.write_bytes(b'isto nao e um banco de dados SQLite' * 8)
    escrever_ini(perfil.ini, INI_COMPLETO)

    leituras = []
    monkeypatch.setattr(storage, 'read_legacy_ini',
                        lambda caminho: leituras.append(caminho))

    with pytest.raises(ArquivoError, match='corrompido') as erro:
        parse_config()

    # Nem ler, nem importar, nem apagar; e a causa original fica encadeada.
    assert leituras == []
    assert perfil.ini.read_text(encoding='utf-8') == INI_COMPLETO
    assert isinstance(erro.value.__cause__, storage.StorageError)
    assert not isinstance(erro.value, ConfiguracaoAusente)


def test_parse_config_registra_atividades_somente_apos_validacao(perfil):
    Atividade(nome='Boa', pts=0.5, saldo=1.0)
    salvar_config(20, 1, 0, True)
    Atividade.clear()

    # Valor gravado fora da API: a leitura reprova e nada é registrado.
    import contextlib
    import sqlite3
    with contextlib.closing(sqlite3.connect(str(perfil.banco))) as conexao:
        conexao.execute("UPDATE activity SET pts = 'nao e numero'")
        conexao.commit()

    with pytest.raises(ArquivoError, match='corrompido'):
        parse_config()
    assert Atividade.all() == []


@pytest.mark.parametrize('timestamp', [0, None])
def test_salvar_e_parse_config_tratam_ausencia_de_credito(perfil, timestamp):
    Atividade(nome='A1', pts=1.0, saldo=0.0)
    salvar_config(20, 1, timestamp, True)
    Atividade.clear()

    # `0` continua sendo o valor público de "nenhum crédito ainda".
    assert parse_config()[2] == 0


def test_salvar_config_aceita_datetime(perfil):
    Atividade(nome='A1', pts=1.0, saldo=0.0)
    salvar_config(20, 1, datetime.datetime(2024, 3, 7, 22, 30), True)
    Atividade.clear()

    assert parse_config()[2] == datetime.date(2024, 3, 7)


def test_salvar_config_preserva_unicode_e_saldo_negativo(perfil):
    Atividade(nome='Programação ☕', pts=0.3, saldo=-42.5)
    salvar_config(20, 7, datetime.date(2024, 1, 1), False)
    Atividade.clear()

    parse_config()
    assert [(a.nome, a.saldo) for a in Atividade.all()] == \
           [('Programação ☕', -42.5)]


def test_salvar_config_recusa_nome_reservado_com_erro_visivel(perfil):
    Atividade(nome='Boa', pts=0.5, saldo=1.0)
    salvar_config(20, 1, datetime.date(2024, 1, 1), True)

    # O formato antigo descartava esta atividade em silêncio; agora a gravação
    # falha de forma visível e o snapshot anterior fica intacto.
    Atividade(nome='__header__', pts=0.5, saldo=2.0)
    with pytest.raises(ArquivoError, match='reservado'):
        salvar_config(20, 1, datetime.date(2024, 1, 1), True)

    Atividade.clear()
    parse_config()
    assert [a.nome for a in Atividade.all()] == ['Boa']


def test_salvar_config_recusa_timestamp_invalido(perfil):
    Atividade(nome='A1', pts=1.0, saldo=0.0)
    with pytest.raises(ArquivoError, match='Data de último crédito'):
        salvar_config(20, 1, 'ontem', True)


def test_aridades_publicas_permanecem_inalteradas():
    assert str(inspect.signature(parse_config)) == '()'
    assert str(inspect.signature(salvar_config)) == \
           '(toth, inicio, timestamp, acumular)'
    assert str(inspect.signature(creditar_tudo)) == \
           '(toth, inicio, timestamp, acumular, hoje=None)'


def test_runtime_respeita_o_perfil_redirecionado_sem_injecao(tmp_path):
    # Sem monkeypatch de caminho nenhum: só o perfil redirecionado. Pega qualquer
    # caminho absoluto residual que ignore a injeção e vá direto ao `~` real.
    # Precisa de subprocesso porque os caminhos são resolvidos no import.
    raiz = os.path.dirname(os.path.abspath(data.__file__))
    lar = tmp_path / 'lar'
    lar.mkdir()

    ambiente = dict(os.environ)
    ambiente['USERPROFILE'] = str(lar)
    ambiente['HOME'] = str(lar)
    for chave in ('HOMEDRIVE', 'HOMEPATH'):
        ambiente.pop(chave, None)

    codigo = ('import sys\n'
              'sys.path.insert(0, %r)\n'
              'import data\n'
              'try:\n'
              '    data.parse_config()\n'
              'except data.ConfiguracaoAusente:\n'
              '    pass\n'
              'print(data.DATABASE)\n' % raiz)
    resultado = subprocess.run([sys.executable, '-B', '-c', codigo],
                               cwd=str(tmp_path), env=ambiente,
                               capture_output=True, text=True)

    assert resultado.returncode == 0, resultado.stderr
    # `expanduser` preserva a barra do padrão, então a comparação é normalizada.
    assert os.path.normpath(resultado.stdout.strip()) == \
           os.path.normpath(str(lar / '.d10r.sqlite3'))
    # O banco foi criado no perfil redirecionado, e nada mais foi criado lá.
    assert [caminho.name for caminho in lar.iterdir()] == ['.d10r.sqlite3']


def test_nenhum_caminho_de_runtime_usa_ini_como_fallback():
    # Teste estático: o menu de procurar/copiar INI e o uso de shutil/CONFIG
    # saíram do runtime para sempre.
    raiz = os.path.dirname(os.path.abspath(data.__file__))
    for modulo in ('data.py', 'd10r.py'):
        with open(os.path.join(raiz, modulo), encoding='utf-8') as fonte:
            texto = fonte.read()
        assert 'shutil' not in texto, modulo
        assert 'escolher_arquivo' not in texto, modulo
        # O identificador `CONFIG` como configuração operacional saiu; o casamento
        # é por token, para não confundir com `storage.UNCONFIGURED`.
        assert not re.search(r'(?<![A-Z_])CONFIG\b', texto), modulo

    assert not hasattr(data, 'CONFIG')


@pytest.mark.parametrize('acumular', [True, False])
def test_creditar_tudo_primeira_execucao_credita_exatamente_uma_vez(acumular):
    # Testa a função que credita horas para todas as atividades
    Atividade(nome="A1", pts=0.5, saldo=0)
    Atividade(nome="A2", pts=0.5, saldo=2)
    
    # Simula a primeira execução
    creditar_tudo(toth=10, inicio=1, timestamp=0, acumular=acumular)
    
    atividades = Atividade.all()
    a1 = next(a for a in atividades if a.nome == "A1")
    a2 = next(a for a in atividades if a.nome == "A2")

    assert a1.saldo == 5.0 # 50% de 10
    assert a2.saldo == (7.0 if acumular else 5.0)


@pytest.mark.parametrize('timestamp, hoje, esperado', [
    # último crédito numa segunda, 14 dias depois: 2 semanas (antes creditava 1)
    (datetime.date(2024, 1, 1), datetime.date(2024, 1, 15), 2),
    # último crédito numa segunda, 7 dias depois: 1 semana (antes creditava 0)
    (datetime.date(2024, 1, 1), datetime.date(2024, 1, 8), 1),
    # último crédito num sábado, segunda seguinte: 1 semana (antes creditava 0)
    (datetime.date(2024, 1, 6), datetime.date(2024, 1, 8), 1),
    # mesma semana, antes da próxima segunda: nada a creditar
    (datetime.date(2024, 1, 2), datetime.date(2024, 1, 7), 0),
])
def test_creditar_tudo_semanas(timestamp, hoje, esperado):
    Atividade(nome='A1', pts=0.5, saldo=0)
    creditou = creditar_tudo(toth=10, inicio=1, timestamp=timestamp,
                             acumular=True, hoje=hoje)
    assert creditou is bool(esperado)
    assert Atividade.all()[0].saldo == 5.0 * esperado


def test_creditar_tudo_confere_com_contagem_ingenua():
    # Conta as ocorrências do dia de início em (timestamp, hoje]
    base = datetime.date(2026, 1, 5)
    for inicio in range(1, 8):
        for desloc in range(7):
            timestamp = base + datetime.timedelta(desloc)
            for dias in range(1, 30):
                hoje = timestamp + datetime.timedelta(dias)
                esperado = sum(
                    1 for k in range(1, dias + 1)
                    if (timestamp + datetime.timedelta(k)).isoweekday() == inicio)
                Atividade.clear()
                Atividade(nome='A1', pts=1.0, saldo=0)
                creditar_tudo(toth=1, inicio=inicio, timestamp=timestamp,
                              acumular=True, hoje=hoje)
                assert Atividade.all()[0].saldo == esperado, (inicio, timestamp, hoje)


def test_creditar_tudo_nao_acumulativo_limita_atraso_a_uma_semana():
    Atividade(nome='A1', pts=0.5, saldo=0)
    creditou = creditar_tudo(
        toth=10, inicio=1, timestamp=datetime.date(2024, 1, 1),
        acumular=False, hoje=datetime.date(2024, 1, 22),
    )
    assert creditou is True
    assert Atividade.all()[0].saldo == 5.0


def test_creditar_tudo_nao_acumulativo_zera_saldo_positivo_antes_de_creditar():
    Atividade(nome='A1', pts=0.5, saldo=3)
    creditar_tudo(
        toth=10, inicio=1, timestamp=datetime.date(2024, 1, 1),
        acumular=False, hoje=datetime.date(2024, 1, 8),
    )
    assert Atividade.all()[0].saldo == 5.0


def test_creditar_tudo_nao_acumulativo_preserva_saldo_negativo():
    Atividade(nome='A1', pts=0.5, saldo=-3)
    creditar_tudo(
        toth=10, inicio=1, timestamp=datetime.date(2024, 1, 1),
        acumular=False, hoje=datetime.date(2024, 1, 8),
    )
    assert Atividade.all()[0].saldo == 2.0
