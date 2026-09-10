import pytest
from utils import formatah, dias_x_entre
import datetime

def test_formatah():
    # Testa formatação padrão (sem segundos, com sinal)
    assert formatah(2.5) == '+02:30'
    assert formatah(-1.75) == '-01:45'
    assert formatah(0) == '00:00'

    # Testa com segundos
    assert formatah(1.255, segundos=True) == '+01:15:18'

    # Testa sem sinal
    assert formatah(3.0, sinal=False) == '03:00'
    assert formatah(-2.25, sinal=False) == '02:15'

def test_dias_x_entre():
    # Testa a contagem de dias da semana entre duas datas
    # Ex: Quantas segundas-feiras (1) entre 1 e 15 de janeiro de 2024
    d_inicio = datetime.date(2024, 1, 1)
    d_fim = datetime.date(2024, 1, 15)
    # Dias 1, 8, 15 são segundas-feiras
    assert dias_x_entre(1, d_inicio, d_fim) == 3

    # Ex: Quantas sextas-feiras (5) no mesmo período
    # Dias 5, 12 são sextas-feiras
    assert dias_x_entre(5, d_inicio, d_fim) == 2


def test_cronometro_sem_fim():
    from utils import Cronometro
    assert Cronometro(None).fim is None
    assert Cronometro(None, True).fim is None


def test_cronometro_marca_fim_alcancado():
    from utils import Cronometro
    c = Cronometro(0, True)
    c.run()  # síncrono: o fim já foi atingido na primeira verificação
    assert c.isparado
    assert c.fim_alcancado


def _contar_ingenuo(dia, antes, depois):
    total = (depois - antes).days
    return sum(1 for k in range(total + 1)
               if (antes + datetime.timedelta(k)).isoweekday() == dia)


def test_dias_x_entre_virada_de_semana():
    # Regressão: de sábado (10/01/2026) a segunda (12/01/2026) há 1 segunda-feira
    sabado = datetime.date(2026, 1, 10)
    segunda = datetime.date(2026, 1, 12)
    assert dias_x_entre(1, sabado, segunda) == 1


def test_dias_x_entre_confere_com_contagem_ingenua():
    base = datetime.date(2026, 1, 5)
    for desloc in range(7):
        antes = base + datetime.timedelta(desloc)
        for dias in range(0, 30):
            depois = antes + datetime.timedelta(dias)
            for dia in range(1, 8):
                assert dias_x_entre(dia, antes, depois) == \
                    _contar_ingenuo(dia, antes, depois), (dia, antes, depois)
