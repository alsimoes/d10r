import pytest
import datetime
from d10r import calcula_prioridades
import data
import d10r


class AtividadeFake:
    def __init__(self, saldo=2.0):
        self.nome = 'Teste'
        self.saldo = saldo

    def debitarh(self, horas):
        self.saldo -= horas

def test_calcula_prioridades():
    # Lista de atividades ordenadas da mais para a menos prioritária
    atividades_ordenadas = ["Trabalho", "Estudar", "Academia", "Lazer"]
    
    prioridades = calcula_prioridades(atividades_ordenadas)
    
    # A pontuação deve ser:
    # Trabalho (mais prioritário) -> 4 pontos
    # Estudar -> 3 pontos
    # Academia -> 2 pontos
    # Lazer (menos prioritário) -> 1 ponto
    
    assert prioridades["Trabalho"] == 4
    assert prioridades["Estudar"] == 3
    assert prioridades["Academia"] == 2
    assert prioridades["Lazer"] == 1
    assert len(prioridades) == 4


def test_init_credita_primeira_execucao_e_grava_data(monkeypatch):
    primeira_data = datetime.date(2024, 1, 8)
    segunda_data = datetime.date(2024, 1, 9)
    chamadas_data = []

    class DateProbe:
        @classmethod
        def today(cls):
            chamadas_data.append(None)
            return primeira_data if len(chamadas_data) == 1 else segunda_data

    creditos = []
    salvos = []
    monkeypatch.setattr(d10r.datetime, 'date', DateProbe)
    monkeypatch.setattr(d10r.gui, 'notificar', lambda *args: None)
    monkeypatch.setattr(d10r, 'ler_atividades', lambda: {'A', 'B'})
    monkeypatch.setattr(d10r.gui, 'prioridade_dialog',
                        lambda atividades: ['A', 'B'])
    monkeypatch.setattr(d10r.gui, 'entrar', lambda *args: 10)
    monkeypatch.setattr(d10r.gui, 'perguntar', lambda *args: False)
    monkeypatch.setattr(data, 'creditar_tudo',
                        lambda *args: creditos.append(args))
    monkeypatch.setattr(data, 'salvar_config',
                        lambda *args: salvos.append(args))

    d10r.init()

    assert len(chamadas_data) == 1
    assert creditos == [(10, primeira_data.isoweekday(), 0, False)]
    assert salvos == [(10, primeira_data.isoweekday(), primeira_data, False)]


def test_cancelar_escolha_encerra_e_salva(monkeypatch):
    atividade = AtividadeFake()
    monkeypatch.setattr(data, 'parse_config', lambda: (8, 1, 0, True))
    monkeypatch.setattr(data, 'creditar_tudo', lambda *args, **kwargs: False)
    monkeypatch.setattr(data.Atividade, 'all', classmethod(lambda cls: [atividade]))
    monkeypatch.setattr(d10r, 'escolher_ativ', lambda: None)
    salvo = []
    monkeypatch.setattr(data, 'salvar_config', lambda *args: salvo.append(args))
    d10r.main()
    assert atividade.saldo == 2.0
    assert salvo


def test_cancelar_entrada_manual_gera_debito_zero(monkeypatch):
    atividade = AtividadeFake()
    monkeypatch.setattr(d10r.gui, 'menu', lambda *args: 'Inserir')
    monkeypatch.setattr(d10r.gui, 'horaspin', lambda *args: None)
    assert d10r.debitar(atividade) == 0.0


def test_main_sem_configuracao_vai_direto_ao_questionario(monkeypatch):
    # Nenhum menu de procurar/copiar/selecionar arquivo: o estado "não
    # configurado" leva direto à primeira configuração.
    chamadas = iter([data.ConfiguracaoAusente('Nenhum arquivo de configuração '
                                              'encontrado.'),
                     (8, 1, 0, True)])

    def parse_config_falso():
        resultado = next(chamadas)
        if isinstance(resultado, Exception):
            raise resultado
        return resultado

    inicializou = []
    monkeypatch.setattr(data, 'parse_config', parse_config_falso)
    monkeypatch.setattr(d10r, 'init', lambda: inicializou.append(True))
    monkeypatch.setattr(data, 'creditar_tudo', lambda *args, **kwargs: False)
    monkeypatch.setattr(data.Atividade, 'all', classmethod(lambda cls: []))
    monkeypatch.setattr(d10r, 'escolher_ativ', lambda: None)
    monkeypatch.setattr(data, 'salvar_config', lambda *args: None)

    d10r.main()

    assert inicializou == [True]


def test_main_com_armazenamento_corrompido_avisa_e_encerra(monkeypatch):
    # Corrupção não vira primeira execução: isso sobrescreveria dados que o
    # usuário ainda pode querer recuperar.
    avisos = []
    inicializou = []

    def parse_config_corrompido():
        raise data.ArquivoError('Arquivo de configuração corrompido.')

    monkeypatch.setattr(data, 'parse_config', parse_config_corrompido)
    monkeypatch.setattr(d10r, 'init', lambda: inicializou.append(True))
    monkeypatch.setattr(d10r.gui, 'notificar', lambda msg: avisos.append(msg))

    with pytest.raises(SystemExit) as saida:
        d10r.main()

    assert saida.value.code == 1
    assert inicializou == []
    assert avisos == ['Arquivo de configuração corrompido.']


def test_main_nao_insiste_quando_a_configuracao_nao_conclui(monkeypatch):
    # Se o questionário não deixar configuração gravada, o programa desiste em
    # vez de perguntar para sempre.
    def sempre_ausente():
        raise data.ConfiguracaoAusente('Nenhum arquivo de configuração '
                                       'encontrado.')

    tentativas = []
    monkeypatch.setattr(data, 'parse_config', sempre_ausente)
    monkeypatch.setattr(d10r, 'init', lambda: tentativas.append(True))

    with pytest.raises(data.ConfiguracaoAusente):
        d10r.main()

    assert tentativas == [True]


def test_main_integrado_cria_o_banco_e_conclui_a_primeira_configuracao(perfil,
                                                                      monkeypatch):
    # Integração real entre parse_config e main, num perfil temporário: nenhuma
    # das duas pontas é falsa, só o questionário e os diálogos.
    def init_falso():
        data.Atividade(nome='A1', pts=1.0, saldo=0.0)
        data.salvar_config(10, 1, 0, True)

    # `notificar` é interceptado de propósito: qualquer diálogo real aqui
    # significaria que o fluxo caiu no caminho de erro, e o teste precisa
    # reprovar em vez de abrir uma janela.
    avisos = []
    monkeypatch.setattr(d10r.gui, 'notificar', lambda msg: avisos.append(msg))
    monkeypatch.setattr(d10r, 'init', init_falso)
    monkeypatch.setattr(d10r, 'escolher_ativ', lambda: None)
    monkeypatch.setattr(data, 'creditar_tudo', lambda *args, **kwargs: False)

    d10r.main()

    assert avisos == []
    assert perfil.banco.exists()
    assert not perfil.ini.exists()
    assert [a.nome for a in data.Atividade.all()] == ['A1']
    assert data.parse_config() == (10, 1, 0, True)


def test_main_integrado_com_banco_corrompido_nao_configura(perfil, monkeypatch):
    perfil.banco.write_bytes(b'isto nao e um banco de dados SQLite' * 8)
    inicializou = []
    avisos = []
    monkeypatch.setattr(d10r, 'init', lambda: inicializou.append(True))
    monkeypatch.setattr(d10r.gui, 'notificar', lambda msg: avisos.append(msg))

    with pytest.raises(SystemExit):
        d10r.main()

    # Corrupção nunca vira primeira configuração: nada é sobrescrito.
    assert inicializou == []
    assert avisos == ['Arquivo de configuração corrompido.']


def test_runtime_nao_expoe_mais_o_menu_de_arquivo():
    assert not hasattr(d10r, 'menu_cfg')
    assert not hasattr(d10r, 'shutil')


def test_recusar_confirmacao_preserva_saldo(monkeypatch):
    atividade = AtividadeFake()
    escolhas = iter([atividade, None])
    perguntas = iter([False])
    salvo = []
    monkeypatch.setattr(data, 'parse_config', lambda: (8, 1, 0, True))
    monkeypatch.setattr(data, 'creditar_tudo', lambda *args, **kwargs: False)
    monkeypatch.setattr(d10r, 'escolher_ativ', lambda: next(escolhas))
    monkeypatch.setattr(d10r, 'debitar', lambda *args: 1.0)
    monkeypatch.setattr(d10r.gui, 'perguntar', lambda *args: next(perguntas))
    monkeypatch.setattr(data, 'salvar_config', lambda *args: salvo.append(args))
    d10r.main()
    assert atividade.saldo == 2.0
    assert salvo
