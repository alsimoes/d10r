'''Testes da importação única do INI legado e do corte para SQLite.

Nenhum teste deste arquivo toca o perfil real do usuário: os dois caminhos
(banco e INI) são sempre injetados e vivem em `tmp_path`.
'''

import contextlib
import datetime
import os
import sqlite3

import pytest

import storage
from storage import (UNCONFIGURED, ActivitySnapshot, ConfigSnapshot, SQLiteStore,
                    StorageError, ensure_storage, import_legacy_ini,
                    read_legacy_ini, remove_legacy_ini_exact)


CABECALHO_PADRAO = {'disponivel': '20', 'inicio': '3', 'timestamp': '20240101',
                    'acumular': 'False'}

ATIVIDADES_PADRAO = (('Café ☕', '0.6', '-999.5'), ('Programação', '0.4', '10.25'))

SNAPSHOT_PADRAO = ConfigSnapshot(
    toth=20, inicio=3, last_credit_date=datetime.date(2024, 1, 1), acumular=False,
    activities=(ActivitySnapshot(name='Café ☕', pts=0.6, saldo=-999.5),
                ActivitySnapshot(name='Programação', pts=0.4, saldo=10.25)),
)


def texto_ini(cabecalho=None, atividades=ATIVIDADES_PADRAO):
    '''Monta o conteúdo de um INI legado a partir das partes.'''
    campos = CABECALHO_PADRAO if cabecalho is None else cabecalho
    linhas = ['[%s]' % storage.LEGACY_HEADER]
    linhas += ['%s = %s' % (chave, valor) for chave, valor in campos.items()]
    for nome, pts, saldo in atividades:
        linhas += ['', '[%s]' % nome, 'pts = %s' % pts, 'saldo = %s' % saldo]
    return '\n'.join(linhas) + '\n'


@pytest.fixture
def db_path(tmp_path):
    '''Caminho do banco final, ainda inexistente.'''
    return tmp_path / '.d10r.sqlite3'


@pytest.fixture
def ini_path(tmp_path):
    '''Caminho do único INI legado aceito, ainda inexistente.'''
    return tmp_path / '.d10r'


@pytest.fixture
def ini(ini_path):
    '''INI legado válido, com Unicode e saldo negativo.'''
    ini_path.write_text(texto_ini(), encoding='utf-8')
    return ini_path


@pytest.fixture
def espiao_do_leitor(monkeypatch):
    '''Conta as invocações do leitor de INI, para provar "zero leituras".'''
    chamadas = []
    original = storage.read_legacy_ini

    def espiao(caminho):
        chamadas.append(os.fspath(caminho))
        return original(caminho)

    monkeypatch.setattr(storage, 'read_legacy_ini', espiao)
    return chamadas


def temporarios_em(diretorio):
    '''Temporários de importação que sobraram no diretório.'''
    return sorted(nome for nome in os.listdir(str(diretorio))
                  if nome.startswith(storage.TEMP_PREFIX))


# --- Leitor puro -----------------------------------------------------------

def test_leitor_converte_o_ini_em_snapshot(ini):
    assert read_legacy_ini(ini) == SNAPSHOT_PADRAO


def test_leitor_aceita_ini_legado_sem_acumular(ini_path):
    # O formato anterior ao modo acumulativo vale como acumulativo.
    campos = {k: v for k, v in CABECALHO_PADRAO.items() if k != 'acumular'}
    ini_path.write_text(texto_ini(campos), encoding='utf-8')
    assert read_legacy_ini(ini_path).acumular is True


@pytest.mark.parametrize('valor, esperado', [('True', True), ('False', False),
                                             ('yes', True), ('no', False),
                                             ('1', True), ('0', False)])
def test_leitor_preserva_acumular_explicito(ini_path, valor, esperado):
    campos = dict(CABECALHO_PADRAO, acumular=valor)
    ini_path.write_text(texto_ini(campos), encoding='utf-8')
    assert read_legacy_ini(ini_path).acumular is esperado


def test_leitor_preserva_unicode_e_saldo_negativo(ini):
    atividades = read_legacy_ini(ini).activities
    assert [a.name for a in atividades] == ['Café ☕', 'Programação']
    assert atividades[0].saldo == -999.5


def test_leitor_preserva_a_ordem_das_secoes(ini_path):
    nomes = ['Zelar', 'Aprender', 'Malhar']
    ini_path.write_text(
        texto_ini(atividades=tuple((n, '0.3', '0.0') for n in nomes)),
        encoding='utf-8')
    assert [a.name for a in read_legacy_ini(ini_path).activities] == nomes


def test_leitor_trata_timestamp_zero_como_sem_credito(ini_path):
    campos = dict(CABECALHO_PADRAO, timestamp='0')
    ini_path.write_text(texto_ini(campos), encoding='utf-8')
    assert read_legacy_ini(ini_path).last_credit_date is None


def test_leitor_aceita_ini_sem_atividades(ini_path):
    ini_path.write_text(texto_ini(atividades=()), encoding='utf-8')
    assert read_legacy_ini(ini_path).activities == ()


def test_leitor_falha_em_arquivo_ausente(ini_path, tmp_path):
    with pytest.raises(StorageError, match='inexistente'):
        read_legacy_ini(ini_path)
    assert list(tmp_path.iterdir()) == []


CONTEUDOS_INVALIDOS = [
    pytest.param('', id='vazio'),
    pytest.param('[invalido', id='secao-nao-fechada'),
    pytest.param('sem cabecalho = 1\n', id='sem-cabecalho'),
    pytest.param(texto_ini({'inicio': '3', 'timestamp': '0'}), id='sem-disponivel'),
    pytest.param(texto_ini({'disponivel': 'vinte', 'inicio': '3',
                            'timestamp': '0'}), id='disponivel-nao-numerico'),
    pytest.param(texto_ini(atividades=(('Ler', 'meio', '0'),)),
                 id='pts-nao-numerico'),
    pytest.param(texto_ini(atividades=(('Ler', '0.5', 'nada'),)),
                 id='saldo-nao-numerico'),
    pytest.param(texto_ini(atividades=(('Ler', '0.5', '1'), ('Ler', '0.5', '2'))),
                 id='secao-duplicada'),
    pytest.param(texto_ini(dict(CABECALHO_PADRAO, inicio='9')),
                 id='inicio-fora-do-iso'),
    pytest.param(texto_ini(dict(CABECALHO_PADRAO, timestamp='20241350')),
                 id='data-inexistente'),
    pytest.param(texto_ini(atividades=(('Ler', 'nan', '0'),)), id='pts-nan'),
    pytest.param(texto_ini(atividades=(('Ler', '0.5', 'inf'),)), id='saldo-inf'),
    pytest.param(texto_ini(atividades=(('Ler', '0.5', '1'),
                                       ('Quebrada', 'meio', '2'))),
                 id='secao-valida-seguida-de-malformada'),
]


@pytest.mark.parametrize('conteudo', CONTEUDOS_INVALIDOS)
def test_leitor_reprova_ini_invalido_e_preserva_o_arquivo(ini_path, conteudo):
    # `nan`/`inf` eram aceitos em silêncio pelo formato antigo; agora são erro,
    # por decisão explícita do contrato.
    ini_path.write_text(conteudo, encoding='utf-8')
    with pytest.raises(StorageError):
        read_legacy_ini(ini_path)
    assert ini_path.read_text(encoding='utf-8') == conteudo


def test_leitor_reprova_encoding_invalido(ini_path):
    ini_path.write_bytes(b'[__header__]\ndisponivel = 20\ninicio = 1\n\xff\xfe')
    with pytest.raises(StorageError, match='corrompido'):
        read_legacy_ini(ini_path)


def test_leitor_nao_registra_atividade_nem_parcialmente(ini_path):
    # O leitor é puro: mesmo com uma seção válida antes da malformada, nada é
    # publicado no domínio. Regressão do Sprint 1, agora no nível do importador.
    import data

    data.Atividade.clear()
    try:
        ini_path.write_text(
            texto_ini(atividades=(('Valida', '0.5', '1'),
                                  ('Malformada', 'meio', '2'))),
            encoding='utf-8')
        with pytest.raises(StorageError):
            read_legacy_ini(ini_path)
        assert data.Atividade.all() == []

        # Nem no caminho de sucesso: converter não é registrar.
        ini_path.write_text(texto_ini(), encoding='utf-8')
        read_legacy_ini(ini_path)
        assert data.Atividade.all() == []
    finally:
        data.Atividade.clear()


def test_leitor_nao_cria_nem_remove_arquivos(ini, tmp_path):
    read_legacy_ini(ini)
    assert [caminho.name for caminho in tmp_path.iterdir()] == ['.d10r']


# --- Remoção pelo caminho exato --------------------------------------------

def test_remocao_usa_o_caminho_exato_e_poupa_os_irmaos(ini, tmp_path):
    irmaos = ['.d10r.bak', '.d10r~', '.d10rX', '.d10r.sqlite3-orfao']
    for nome in irmaos:
        (tmp_path / nome).write_text('nao me apague', encoding='utf-8')

    remove_legacy_ini_exact(ini)

    assert not ini.exists()
    assert sorted(c.name for c in tmp_path.iterdir()) == sorted(irmaos)


def test_remocao_de_arquivo_ausente_nao_e_erro(ini_path):
    assert remove_legacy_ini_exact(ini_path) is None


def test_remocao_converte_falha_de_so_em_erro_de_armazenamento(ini, monkeypatch):
    def remove_quebrado(caminho, *args, **kwargs):
        raise PermissionError(13, 'acesso negado')

    monkeypatch.setattr('os.remove', remove_quebrado)
    with pytest.raises(StorageError, match='remover o arquivo legado') as erro:
        remove_legacy_ini_exact(ini)
    assert isinstance(erro.value.__cause__, PermissionError)


# --- Importação bem-sucedida ------------------------------------------------

def test_migracao_promove_o_banco_e_remove_o_ini(ini, db_path, tmp_path):
    loja = import_legacy_ini(ini, db_path)

    assert loja.load_snapshot() == SNAPSHOT_PADRAO
    assert not ini.exists()
    # Sobra exatamente o banco final: nenhum temporário, nenhum resíduo.
    assert [caminho.name for caminho in tmp_path.iterdir()] == ['.d10r.sqlite3']


def test_migracao_de_ini_legado_sem_acumular(ini_path, db_path):
    campos = {k: v for k, v in CABECALHO_PADRAO.items() if k != 'acumular'}
    ini_path.write_text(texto_ini(campos), encoding='utf-8')

    loja = import_legacy_ini(ini_path, db_path)
    assert loja.load_snapshot().acumular is True


def test_migracao_preserva_timestamp_zero(ini_path, db_path):
    campos = dict(CABECALHO_PADRAO, timestamp='0')
    ini_path.write_text(texto_ini(campos), encoding='utf-8')

    assert import_legacy_ini(ini_path, db_path).load_snapshot().last_credit_date \
           is None


def test_migracao_usa_temporario_unico_no_diretorio_do_banco(ini, db_path,
                                                             monkeypatch):
    origens = []
    replace_real = os.replace

    def replace_espiao(origem, destino, *args, **kwargs):
        origens.append(os.fspath(origem))
        return replace_real(origem, destino)

    monkeypatch.setattr('os.replace', replace_espiao)
    import_legacy_ini(ini, db_path)

    assert len(origens) == 1
    temporario = origens[0]
    assert os.path.dirname(temporario) == os.path.dirname(str(db_path))
    assert os.path.basename(temporario).startswith(storage.TEMP_PREFIX)
    assert temporario != str(db_path)


def test_migracao_nao_reaproveita_temporario_de_outra_tentativa(ini, db_path,
                                                               tmp_path):
    orfao = tmp_path / (storage.TEMP_PREFIX + 'de-uma-queda.sqlite3')
    orfao.write_text('resto de tentativa anterior', encoding='utf-8')

    import_legacy_ini(ini, db_path)

    # Nem reutilizado, nem apagado por padrão: a limpeza é sempre pelo caminho
    # exato da tentativa atual.
    assert orfao.read_text(encoding='utf-8') == 'resto de tentativa anterior'


def test_migracao_libera_o_arquivo_imediatamente(ini, db_path):
    import_legacy_ini(ini, db_path)
    # Sem sleep e sem retry: nenhum engine pode ter sobrado aberto.
    os.remove(str(db_path))
    assert not db_path.exists()


def test_migracao_recusa_banco_final_existente(ini, db_path):
    SQLiteStore(db_path).bootstrap_v1()
    antes = db_path.read_bytes()

    with pytest.raises(StorageError, match='já existe'):
        import_legacy_ini(ini, db_path)

    # O INI só é entrada quando o banco não existe; nada foi lido nem apagado.
    assert ini.exists()
    assert db_path.read_bytes() == antes


def test_migracao_ocorre_depois_da_verificacao_e_antes_da_remocao(ini, db_path,
                                                                 monkeypatch):
    ordem = []
    replace_real, remove_real = os.replace, os.remove
    load_real = SQLiteStore.load_snapshot

    def load_espiao(self):
        resultado = load_real(self)
        ordem.append('releitura')
        return resultado

    def replace_espiao(origem, destino, *args, **kwargs):
        ordem.append('promocao')
        return replace_real(origem, destino)

    def remove_espiao(caminho, *args, **kwargs):
        if os.path.abspath(caminho) == os.path.abspath(str(ini)):
            ordem.append('remocao-do-ini')
        return remove_real(caminho)

    monkeypatch.setattr(SQLiteStore, 'load_snapshot', load_espiao)
    monkeypatch.setattr('os.replace', replace_espiao)
    monkeypatch.setattr('os.remove', remove_espiao)

    import_legacy_ini(ini, db_path)

    assert ordem == ['releitura', 'promocao', 'remocao-do-ini']


# --- Falhas antes da promoção ----------------------------------------------

def quebrar_bootstrap(monkeypatch):
    def bootstrap_quebrado(self):
        raise RuntimeError('bootstrap indisponível')

    monkeypatch.setattr(SQLiteStore, 'bootstrap_v1', bootstrap_quebrado)


def quebrar_gravacao(monkeypatch):
    def save_quebrado(self, snapshot):
        raise RuntimeError('gravação indisponível')

    monkeypatch.setattr(SQLiteStore, 'save_snapshot', save_quebrado)


def quebrar_integridade(monkeypatch):
    def integridade_quebrada(self):
        raise StorageError('integridade reprovada')

    monkeypatch.setattr(SQLiteStore, 'integrity_check', integridade_quebrada)


def divergir_na_releitura(monkeypatch):
    def load_divergente(self):
        return ConfigSnapshot(toth=1, inicio=1, acumular=True)

    monkeypatch.setattr(SQLiteStore, 'load_snapshot', load_divergente)


def quebrar_promocao(monkeypatch):
    def replace_quebrado(origem, destino, *args, **kwargs):
        raise OSError(13, 'destino em uso')

    monkeypatch.setattr('os.replace', replace_quebrado)


# Para cada injeção, a causa que o erro de armazenamento deve encadear. `None`
# marca os casos em que a própria importação decide reprovar, sem exceção de
# origem para encadear.
FALHAS_ANTES_DA_PROMOCAO = [
    pytest.param(quebrar_bootstrap, RuntimeError, id='bootstrap'),
    pytest.param(quebrar_gravacao, RuntimeError, id='gravacao'),
    pytest.param(quebrar_integridade, None, id='integridade'),
    pytest.param(divergir_na_releitura, None, id='releitura-divergente'),
    pytest.param(quebrar_promocao, OSError, id='promocao'),
]


@pytest.mark.parametrize('quebrar, causa', FALHAS_ANTES_DA_PROMOCAO)
def test_falha_antes_da_promocao_preserva_o_ini_e_nao_deixa_banco(
        ini, db_path, tmp_path, monkeypatch, quebrar, causa):
    conteudo = ini.read_text(encoding='utf-8')
    quebrar(monkeypatch)

    with pytest.raises(StorageError):
        import_legacy_ini(ini, db_path)

    # Preservar a entrada de uma importação que não chegou a um banco íntegro não
    # é fallback: o chamador recebe erro e não usa esses valores.
    assert ini.read_text(encoding='utf-8') == conteudo
    assert not db_path.exists()
    assert temporarios_em(tmp_path) == []


def test_falha_de_leitura_nao_cria_temporario(ini_path, db_path, tmp_path):
    ini_path.write_text('[invalido', encoding='utf-8')

    with pytest.raises(StorageError):
        import_legacy_ini(ini_path, db_path)

    assert ini_path.exists()
    assert not db_path.exists()
    assert temporarios_em(tmp_path) == []


@pytest.mark.parametrize('quebrar, causa', FALHAS_ANTES_DA_PROMOCAO)
def test_falha_antes_da_promocao_nao_deixa_excecao_crua_escapar(ini, db_path,
                                                               monkeypatch,
                                                               quebrar, causa):
    quebrar(monkeypatch)
    with pytest.raises(StorageError) as erro:
        import_legacy_ini(ini, db_path)

    if causa is None:
        # A própria importação reprovou; não há exceção de origem a encadear.
        assert erro.value.__cause__ is None
    else:
        assert isinstance(erro.value.__cause__, causa)


# --- Falha na remoção depois da promoção -----------------------------------

@pytest.fixture
def remocao_do_ini_falha(ini, monkeypatch):
    '''Faz apenas a remoção do INI falhar, sem afetar temporários.'''
    remove_real = os.remove

    def remove_seletivo(caminho, *args, **kwargs):
        if os.path.abspath(caminho) == os.path.abspath(str(ini)):
            raise PermissionError(13, 'acesso negado')
        return remove_real(caminho, *args, **kwargs)

    monkeypatch.setattr('os.remove', remove_seletivo)


def test_falha_na_remocao_do_ini_gera_erro_com_banco_intacto(
        ini, db_path, remocao_do_ini_falha):
    with pytest.raises(StorageError, match='remover o arquivo legado'):
        import_legacy_ini(ini, db_path)

    # O banco já é autoritativo e completo; a coexistência é que é o problema.
    assert db_path.exists()
    assert SQLiteStore(db_path).load_snapshot() == SNAPSHOT_PADRAO
    assert ini.exists()


def test_proximo_inicio_repete_so_a_remocao_sem_reimportar(
        ini, db_path, monkeypatch, espiao_do_leitor):
    remove_real = os.remove

    def remove_seletivo(caminho, *args, **kwargs):
        if os.path.abspath(caminho) == os.path.abspath(str(ini)):
            raise PermissionError(13, 'acesso negado')
        return remove_real(caminho, *args, **kwargs)

    monkeypatch.setattr('os.remove', remove_seletivo)
    with pytest.raises(StorageError):
        ensure_storage(db_path, ini)
    assert len(espiao_do_leitor) == 1

    # Segunda invocação, como um processo que reinicia: o INI não é lido de novo,
    # só removido.
    monkeypatch.undo()
    loja = ensure_storage(db_path, ini)

    assert len(espiao_do_leitor) == 1
    assert not ini.exists()
    assert loja.load_snapshot() == SNAPSHOT_PADRAO


# --- ensure_storage: matriz de estados iniciais ----------------------------

def test_sem_banco_e_sem_ini_cria_schema_v1_vazio(db_path, ini_path, tmp_path,
                                                  espiao_do_leitor):
    loja = ensure_storage(db_path, ini_path)

    assert loja.load_snapshot() is UNCONFIGURED
    assert loja.schema_version() == 1
    assert espiao_do_leitor == []
    assert not ini_path.exists()
    assert [caminho.name for caminho in tmp_path.iterdir()] == ['.d10r.sqlite3']


def test_so_ini_valido_importa_promove_e_remove(ini, db_path, espiao_do_leitor):
    loja = ensure_storage(db_path, ini)

    assert loja.load_snapshot() == SNAPSHOT_PADRAO
    assert not ini.exists()
    assert len(espiao_do_leitor) == 1


def test_so_ini_invalido_falha_e_preserva_o_ini(ini_path, db_path, tmp_path):
    ini_path.write_text(texto_ini(atividades=(('Ler', 'meio', '0'),)),
                        encoding='utf-8')

    with pytest.raises(StorageError):
        ensure_storage(db_path, ini_path)

    assert ini_path.exists()
    assert not db_path.exists()
    assert temporarios_em(tmp_path) == []


def test_banco_valido_sem_ini_apenas_carrega(db_path, ini_path, espiao_do_leitor):
    SQLiteStore(db_path).bootstrap_v1()
    antes = db_path.read_bytes()

    loja = ensure_storage(db_path, ini_path)

    assert loja.load_snapshot() is UNCONFIGURED
    assert db_path.read_bytes() == antes
    assert espiao_do_leitor == []


def test_banco_valido_com_ini_remove_sem_ler(db_path, ini_path, espiao_do_leitor):
    # INI com valores sentinela divergentes: se algum vazar para o banco, o teste
    # detecta.
    preexistente = ConfigSnapshot(
        toth=40, inicio=1, last_credit_date=datetime.date(2025, 5, 5),
        acumular=True,
        activities=(ActivitySnapshot(name='Do banco', pts=1.0, saldo=3.0),))
    loja = SQLiteStore(db_path)
    loja.bootstrap_v1()
    loja.save_snapshot(preexistente)
    antes = db_path.read_bytes()
    ini_path.write_text(texto_ini(), encoding='utf-8')

    resultado = ensure_storage(db_path, ini_path)

    assert espiao_do_leitor == []
    assert not ini_path.exists()
    assert resultado.load_snapshot() == preexistente
    assert db_path.read_bytes() == antes


def banco_zero_byte(caminho):
    caminho.write_bytes(b'')


def banco_bytes_aleatorios(caminho):
    caminho.write_bytes(b'isto nao e um banco de dados SQLite' * 8)


def banco_sem_tabelas(caminho):
    with contextlib.closing(sqlite3.connect(str(caminho))) as conexao:
        conexao.execute('CREATE TABLE outra_coisa (x INTEGER)')
        conexao.commit()


def banco_sem_metadado(caminho):
    SQLiteStore(caminho).bootstrap_v1()
    with contextlib.closing(sqlite3.connect(str(caminho))) as conexao:
        conexao.execute('DELETE FROM schema_version')
        conexao.commit()


def banco_schema_futuro(caminho):
    SQLiteStore(caminho).bootstrap_v1()
    with contextlib.closing(sqlite3.connect(str(caminho))) as conexao:
        conexao.execute('UPDATE schema_version SET version = 2')
        conexao.commit()


BANCOS_INVALIDOS = [
    pytest.param(banco_zero_byte, id='zero-bytes'),
    pytest.param(banco_bytes_aleatorios, id='bytes-aleatorios'),
    pytest.param(banco_sem_tabelas, id='sem-tabelas'),
    pytest.param(banco_sem_metadado, id='sem-metadado'),
    pytest.param(banco_schema_futuro, id='schema-futuro'),
]


@pytest.mark.parametrize('fabricar', BANCOS_INVALIDOS)
def test_banco_invalido_falha_sem_tocar_no_ini(db_path, ini_path, fabricar,
                                               espiao_do_leitor):
    fabricar(db_path)
    conteudo_db = db_path.read_bytes()
    ini_path.write_text(texto_ini(), encoding='utf-8')

    with pytest.raises(StorageError):
        ensure_storage(db_path, ini_path)

    # Nem ler, nem importar, nem apagar: o INI e o banco ficam como estavam.
    assert espiao_do_leitor == []
    assert ini_path.exists()
    assert db_path.read_bytes() == conteudo_db


@pytest.mark.parametrize('fabricar', BANCOS_INVALIDOS)
def test_banco_invalido_falha_mesmo_sem_ini(db_path, ini_path, fabricar):
    fabricar(db_path)
    with pytest.raises(StorageError):
        ensure_storage(db_path, ini_path)
    assert not ini_path.exists()


def test_reinicio_depois_da_migracao_nao_le_mais_o_ini(ini, db_path,
                                                       espiao_do_leitor):
    primeira = ensure_storage(db_path, ini)
    assert len(espiao_do_leitor) == 1

    segunda = ensure_storage(db_path, ini)

    assert len(espiao_do_leitor) == 1
    assert segunda.load_snapshot() == primeira.load_snapshot() == SNAPSHOT_PADRAO


def test_ensure_storage_libera_o_arquivo_imediatamente(ini, db_path):
    ensure_storage(db_path, ini)
    os.remove(str(db_path))
    assert not db_path.exists()


def test_ensure_storage_aceita_caminhos_em_qualquer_diretorio(tmp_path, ini):
    # Os dois caminhos são injetados de forma independente: o banco não precisa
    # morar junto do INI.
    outro = tmp_path / 'outro'
    outro.mkdir()
    destino = outro / 'banco.sqlite3'

    loja = ensure_storage(destino, ini)

    assert loja.load_snapshot() == SNAPSHOT_PADRAO
    assert not ini.exists()
    assert temporarios_em(outro) == []
