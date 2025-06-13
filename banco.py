import mysql.connector
import pyodbc
import base64
import os
import re
from datetime import datetime


# --- Exceção Customizada ---
class CertificadoNaoEncontradoError(Exception):
    """Exceção para ser usada quando um certificado não é encontrado no banco."""
    pass


# --- Funções de Acesso ao Banco ---

def obterDadosEmpresaDominio(codigo: int):
    str_conexao_dominio = "DSN=Dominio;UID=NEOSOLUTIONS;PWD=NEOSOLUTIONS"
    conexao_dominio = None  # Inicializa a variável de conexão
    try:
        conexao_dominio = pyodbc.connect(str_conexao_dominio)
        cursor = conexao_dominio.cursor()
        cursor.execute(f'SELECT cgce_emp, esta_emp, razao_emp FROM bethadba.geempre where codi_emp={codigo}')

        dados_raw = cursor.fetchone()

        # Verifica se a consulta retornou algum resultado
        if dados_raw is None:
            print(f"AVISO: Empresa com código {codigo} não foi encontrada no banco Dominio.")
            return None

        dados = list(dados_raw)
        dados.append(codigo)
        return dados

    except pyodbc.Error as ex:
        # Captura erros específicos de conexão ou consulta com o banco
        print(f"ERRO de Banco de Dados (Dominio) ao buscar empresa {codigo}: {ex}")
        return None  # Retorna None em caso de erro para não parar a aplicação


    finally:
        # Garante que a conexão com o banco seja sempre fechada
        if conexao_dominio:
            conexao_dominio.close()


def baixarCertificadoEmpresa(cnpj: str, codigo: int, base_path: str):
    config = {
        'user': 'root',
        'password': 'shadows2511',
        'host': '192.168.40.206',
        'port': 3307,
        'database': 'mafus_certificados',
    }
    conexao_gestao_cert = None  # Inicializa a variável de conexão
    try:
        conexao_gestao_cert = mysql.connector.connect(**config)
        cursor = conexao_gestao_cert.cursor()

        # 1. Tenta encontrar pelo CNPJ completo
        cursor.execute(f"SELECT dados, senha, razao, expiracao FROM certificados WHERE cnpj='{cnpj}'")
        dadosCert = cursor.fetchone()

        # 2. Se não encontrar, tenta pela raiz do CNPJ (matriz)
        if dadosCert is None:
            print(f"INFO: Certificado para CNPJ {cnpj} não encontrado. Tentando pela matriz...")
            part_cnpj = str(cnpj)[:8] + '0001'  # Busca pela matriz
            cursor.execute(
                f"SELECT dados, senha, razao, expiracao FROM certificados WHERE cnpj LIKE '{part_cnpj}%' LIMIT 1")
            dadosCert = cursor.fetchone()

        # 3. Se ainda assim não encontrar, levanta a exceção customizada
        if dadosCert is None:
            try:
                # Registra a falha em um arquivo de log específico
                with open('certificado_não_encontrado.txt', 'a', encoding='utf-8') as arquivo:
                    arquivo.write(f'{codigo};{cnpj}\n')
            except Exception as e_log:
                print(f"ERRO ao escrever no arquivo 'certificado_não_encontrado.txt': {e_log}")
            # Levanta a exceção que será tratada pelo script principal
            raise CertificadoNaoEncontradoError(f"Certificado não encontrado para CNPJ {cnpj} (Cod. {codigo})")

        # --- Se o certificado foi encontrado, prossegue ---

        # Verifica a data de expiração
        if dadosCert[3]:
            try:
                expiracao_cert = datetime.strptime(dadosCert[3], '%d/%m/%Y %H:%M')
                if expiracao_cert < datetime.now():
                    print(
                        f'AVISO: Certificado para CNPJ {cnpj} está vencido desde {expiracao_cert.strftime("%d/%m/%Y")}')
            except (ValueError, TypeError):
                print(f"AVISO: Formato de data de expiração inválido para CNPJ {cnpj}: '{dadosCert[3]}'")

        certificado_base64 = dadosCert[0]
        certificado_bytes = base64.b64decode(certificado_base64)

        # Cria o diretório de certificados se não existir
        certificados_dir = os.path.join(base_path, 'certificados')
        os.makedirs(certificados_dir, exist_ok=True)

        # Limpa o nome do arquivo para torná-lo seguro para o sistema de arquivos
        razao_segura = re.sub(r'[\\/*?:"<>|]', "", dadosCert[2])  # Remove caracteres inválidos
        razao_segura = razao_segura[:150]  # Limita o comprimento do nome do arquivo

        caminho_relativo_pfx = os.path.join('certificados', f'{razao_segura}.pfx')
        caminho_completo_pfx = os.path.join(base_path, caminho_relativo_pfx)

        # Salva o arquivo .pfx no disco no caminho completo e correto
        with open(caminho_completo_pfx, 'wb') as arquivo:
            arquivo.write(certificado_bytes)

        # Adiciona o caminho RELATIVO à tupla de dados e a retorna
        dadosCertComCaminho = dadosCert + (caminho_relativo_pfx,)

        return dadosCertComCaminho

    except mysql.connector.Error as ex:
        # Captura erros específicos de conexão ou consulta com o MySQL
        print(f"ERRO de Banco de Dados (MySQL) ao buscar certificado para CNPJ {cnpj}: {ex}")
        raise CertificadoNaoEncontradoError(f"Erro de banco ao buscar certificado para CNPJ {cnpj}") from ex

    finally:
        # Garante que a conexão com o banco seja sempre fechada
        if conexao_gestao_cert and conexao_gestao_cert.is_connected():
            conexao_gestao_cert.close()
