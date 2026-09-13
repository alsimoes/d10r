'''Configuração compartilhada do pytest.'''

import os

# Permite rodar os testes de interface sem servidor gráfico (CI, SSH, etc.)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest


def _arquivos_do_perfil():
    '''Nomes `.d10r*` que existem no perfil real do usuário.

    Neste Python no Windows, `os.path.expanduser` consulta apenas
    `USERPROFILE`; é esse diretório, e não `HOME`, que precisa ficar intocado.'''
    lar = os.path.expanduser('~')
    try:
        return {nome for nome in os.listdir(lar) if nome.startswith('.d10r')}
    except OSError:
        return set()


@pytest.fixture(scope='session', autouse=True)
def perfil_real_intocado():
    '''Falha a sessão se algum teste criar `.d10r*` no perfil real.

    Todo teste precisa injetar os dois caminhos (banco e entrada legada); esta
    rede de segurança pega qualquer caminho absoluto residual que ignore a
    injeção, inclusive em testes que esperam exceção.'''
    antes = _arquivos_do_perfil()
    yield
    novos = _arquivos_do_perfil() - antes
    assert not novos, ('a suíte escreveu no perfil real: %s'
                       % (sorted(novos),))


@pytest.fixture(scope='session')
def qapp():
    '''Instância única de QApplication para os testes de interface.'''
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
