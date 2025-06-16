📋 Tabela de Conteúdos
📌 Sobre o Projeto

✨ Funcionalidades

🛠️ Tecnologias Utilizadas

🚀 Começando

📋 Pré-requisitos

⚙️ Instalação

👨‍💻 Como Usar

🏗️ Arquitetura do Projeto

🤝 Como Contribuir

📄 Licença

📧 Contato

📌 Sobre o Projeto
O Atualizador SIEG foi desenvolvido para resolver um desafio comum em escritórios de contabilidade: a atualização manual e massiva de certificados digitais de empresas na plataforma SIEG. Este processo, quando feito manualmente, é repetitivo, demorado e propenso a erros.

Esta ferramenta automatiza completamente o fluxo de trabalho:

Busca os dados cadastrais da empresa em um banco Dominio.

Obtém o arquivo do certificado digital e sua senha de um banco MySQL.

Realiza o login na plataforma SIEG, navega até a página correta e submete as informações e o arquivo, tudo isso em lote e com mínima intervenção humana.

O resultado é uma economia drástica de tempo e um aumento na precisão dos dados.

## ✨ Funcionalidades
Processamento em Lote: Atualize dezenas ou centenas de empresas de uma só vez.

Interface Gráfica Simples: Uma UI clara e objetiva construída com CustomTkinter.

Modo de Operação Flexível: Execute com o navegador visível (padrão) ou em modo headless (oculto) para maior performance.

Logs e Relatórios: Geração de logs detalhados para depuração e relatórios de pendências ao final de cada execução.

Cancelamento Seguro: Interrompa o processo a qualquer momento sem corromper dados.

🛠️ Tecnologias Utilizadas
Este projeto foi construído com as seguintes tecnologias:

CustomTkinter: Para a interface gráfica.

PyODBC: Para a conexão com o banco de dados Dominio.

🚀 Começando
Para ter uma cópia local do projeto rodando, siga estes passos.

📋 Pré-requisitos
Python 3.10+ instalado.

Acesso de Rede aos servidores de banco de dados (MySQL e Dominio).

DSN ODBC configurado na máquina local com o nome Dominio para a conexão com o sistema Dominio.

Sistema Operacional Windows.

⚙️ Instalação
Clone o repositório:

git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio

Crie e ative um ambiente virtual (altamente recomendado):

python -m venv venv
.\venv\Scripts\activate

Instale as dependências a partir de requirements.txt:

pip install -r requirements.txt

Configure suas credenciais:

Crie um arquivo chamado .env na raiz do projeto.

Adicione suas credenciais do SIEG neste arquivo:

email=seu_email@dominio.com
senha=sua_senha_aqui

👨‍💻 Como Usar
Execute a aplicação:

python main.py

Na tela principal, insira os códigos das empresas no campo de texto, separados por vírgula, espaço ou quebra de linha. Alternativamente, clique em "Carregar Arquivo" para usar um .txt.

Escolha as configurações desejadas (Modo Headless, Timeout).

Clique em "Iniciar Atualização" para começar.

Acompanhe o progresso na barra de status. Você pode clicar em "Cancelar Processo" a qualquer momento.

Ao final, verifique a mensagem de resumo e o relatório de pendências, caso haja algum problema. Para detalhes técnicos, consulte o arquivo atualizador_sieg.log.

🏗️ Arquitetura do Projeto
Uma visão geral da função dos principais arquivos do projeto:

🤝 Como Contribuir
Contribuições são o que tornam a comunidade de código aberto um lugar incrível para aprender, inspirar e criar. Qualquer contribuição que você fizer será muito apreciada.

Se você tiver uma sugestão para melhorar este projeto, por favor, crie um "fork" do repositório e crie um "pull request". Você também pode simplesmente abrir uma "issue" com a tag "melhoria".

Faça um Fork do Projeto

Crie sua Feature Branch (git checkout -b feature/AmazingFeature)

Faça o Commit de suas alterações (git commit -m 'Add some AmazingFeature')

Faça o Push para a Branch (git push origin feature/AmazingFeature)

Abra um Pull Request

📄 Licença
Distribuído sob a Licença MIT. Veja LICENSE.txt para mais informações.

📧 Contato
Seu Nome - @seu_twitter - seu_email@exemplo.com

Link do Projeto: https://github.com/seu-usuario/seu-repositorio
