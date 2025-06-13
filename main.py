import customtkinter as ctk
from tkinter import filedialog
import threading
import time
import re
import os
import subprocess
import logging
import traceback
import sys

from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
from CTkMessagebox import CTkMessagebox

import banco
import cadastro_IRIS

# --- Configurações Iniciais ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- Definição de Caminhos (Paths) ---
# Esta função ajusta os caminhos para funcionar tanto no modo script quanto no modo .exe
def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funcionando em dev e no PyInstaller """
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent.absolute()
    return base_path / relative_path

# Importe 'sys' no topo do seu arquivo, junto com os outros imports
# Ex: import sys

OUTPUT_PATH = resource_path(".")
ASSETS_PATH = resource_path(os.path.join("assets", "frame0"))
DEBUG_SCREENSHOTS_PATH = OUTPUT_PATH / "debug_screenshots"
DEBUG_SCREENSHOTS_PATH.mkdir(parents=True, exist_ok=True)

LOG_FILE_PATH = OUTPUT_PATH / "atualizador_sieg.log"
CERTIFICADOS_PROBLEMAS_FILE = OUTPUT_PATH / "certificados_problemas.txt"


# --- Função Auxiliar ---
def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)


# --- Classe Principal da Aplicação ---
class AtualizadorSiegApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Configuração do Logger ---
        self.setup_logger()

        # --- Carregamento de Configurações (.env) ---
        load_dotenv()
        self.email = os.getenv("email")
        self.senha = os.getenv("senha")

        if not self.email or not self.senha:
            self.logger.error(
                "As variáveis 'email' e 'senha' não foram encontradas no arquivo .env. Aplicação será encerrada.")
            CTkMessagebox(title="Erro de Configuração",
                          message="As variáveis 'email' e 'senha' não foram encontradas no arquivo .env.\n\nVerifique o arquivo e reinicie a aplicação.",
                          icon="cancel",
                          master=self)
            # Atraso para garantir que a mensagem seja visível antes de fechar
            self.after(100, self.destroy)
            return
        self.logger.info("Credenciais do arquivo .env carregadas com sucesso.")

        # --- Configurações da Janela Principal ---
        self.title("Atualizador SIEG - Grupo Meta")
        self.geometry("900x700")
        self.minsize(850, 700)
        self.setup_window_icon()


        # --- Variáveis de Estado e UI ---
        self.colors = {
            'primary': "#C8E0F4", 'secondary': "#508AA8", 'accent': "#9DD1F1",
            'success': "#10b981", 'warning': "#f59e0b", 'error': "#ef4444",
            'dark_bg': "#031927", 'card_bg': "#031927"
        }
        self.is_processing = False
        self.processed_companies_count = 0
        self.total_companies_to_process = 0
        self.navegador = None
        self.empresas_problema = []
        self.cod_empresas_dominio_list = []
        self.cancel_requested = False

        # --- Construção da Interface Gráfica ---
        self.setup_ui()
        self.logger.info("Interface do usuário (UI) configurada e pronta.")

    def setup_logger(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        # Prevenir handlers duplicados se o __init__ for chamado mais de uma vez
        if self.logger.hasHandlers():
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)

        try:
            # Handler para escrever logs em arquivo
            file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

        except Exception:
            # Em caso de falha ao criar o logger, imprime no console.
            print(f"FALHA CRÍTICA AO CONFIGURAR O ARQUIVO DE LOG: {LOG_FILE_PATH}")
            traceback.print_exc()

        self.logger.info("=====================================================================")
        self.logger.info("Aplicação Atualizador SIEG iniciada e logger configurado.")
        self.logger.info(f"Caminho do arquivo de log: {LOG_FILE_PATH}")

    def setup_window_icon(self):
        try:
            icon_path = relative_to_assets("cert.ico")
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
                self.logger.debug("Ícone da janela definido com sucesso.")
            else:
                self.logger.warning(f"Arquivo de ícone não encontrado em: {icon_path}")
        except Exception as e:
            self.logger.error(f"Erro ao tentar definir o ícone da janela: {e}", exc_info=True)

    def setup_ui(self):
        """Cria e organiza todos os widgets da interface gráfica."""
        self.main_frame = ctk.CTkFrame(self, fg_color=self.colors['dark_bg'])
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.create_header()
        self.create_main_section()
        self.create_settings_section()
        self.create_footer()

    def create_header(self):
        """Cria o cabeçalho da aplicação com logos e título."""
        header_frame = ctk.CTkFrame(self.main_frame, height=100, fg_color=self.colors['card_bg'], corner_radius=15)
        header_frame.pack(fill="x", pady=(0, 15), ipady=10)
        header_frame.grid_columnconfigure((0, 2), weight=1)
        header_frame.grid_columnconfigure(1, weight=2)

        # Logo SIEG
        sieg_logo_path = relative_to_assets("image_3.png")
        if sieg_logo_path.exists():
            sieg_pil_image = Image.open(sieg_logo_path)
            sieg_ctk_image = ctk.CTkImage(light_image=sieg_pil_image, dark_image=sieg_pil_image,
                                          size=(int(sieg_pil_image.width * 0.8), int(sieg_pil_image.height * 0.8)))
            sieg_image_label = ctk.CTkLabel(header_frame, image=sieg_ctk_image, text="")
            sieg_image_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Título
        app_title_header = ctk.CTkLabel(header_frame, text="Atualizador de Empresas SIEG",
                                        font=ctk.CTkFont(size=24, weight="bold"), text_color="white")
        app_title_header.grid(row=0, column=1, sticky="ew")

        # Logo Meta
        meta_logo_path = relative_to_assets("image_4.png")
        if meta_logo_path.exists():
            meta_pil_image = Image.open(meta_logo_path)
            meta_ctk_image = ctk.CTkImage(light_image=meta_pil_image, dark_image=meta_pil_image,
                                          size=(int(meta_pil_image.width * 0.8), int(meta_pil_image.height * 0.8)))
            meta_image_label = ctk.CTkLabel(header_frame, image=meta_ctk_image, text="")
            meta_image_label.grid(row=0, column=2, padx=20, pady=10, sticky="e")

    def request_cancellation(self):
        """Sinaliza o cancelamento e inicia o fecho do navegador em segundo plano."""
        if self.is_processing:
            self.logger.warning("Pedido de cancelamento imediato recebido do utilizador.")
            self.cancel_requested = True
            self.start_btn.configure(text="A Cancelar...", state="disabled")

            current_progress_value = self.progress_bar.get()
            self.update_progress_display(
                progress_value=current_progress_value,
                current_processed=self.processed_companies_count,
                total_to_process=self.total_companies_to_process,
                status_text="Cancelando..."
            )

            # Inicia o fecho do navegador numa nova thread para não bloquear a interface.
            quit_thread = threading.Thread(target=self._force_quit_browser_in_thread, daemon=True)
            quit_thread.start()

    def create_main_section(self):
        """Cria a seção principal para entrada de dados e controle."""
        main_card = ctk.CTkFrame(self.main_frame, fg_color=self.colors['card_bg'], corner_radius=15)
        main_card.pack(fill="x", pady=(0, 15), ipady=15)

        input_frame = ctk.CTkFrame(main_card, fg_color="transparent")
        input_frame.pack(fill="x", padx=30, pady=(0, 20))

        ctk.CTkLabel(input_frame, text="Códigos das Empresas:", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="white", anchor="w").pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(input_frame,
                     text="Insira os códigos numéricos separados por vírgulas ou um por linha (ex: 1, 2, 3).",
                     font=ctk.CTkFont(size=12), text_color="#94a3b8", anchor="w").pack(fill="x", pady=(0, 10))

        entry_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        entry_frame.pack(fill="x", pady=(0, 15))

        self.companies_entry = ctk.CTkTextbox(entry_frame, height=100, font=ctk.CTkFont(size=14), corner_radius=10,
                                              border_width=2, border_color=self.colors['secondary'],
                                              activate_scrollbars=True)
        self.companies_entry.pack(fill="x", expand=True)

        buttons_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 0))
        buttons_frame.grid_columnconfigure(2, weight=1)

        self.load_file_btn = ctk.CTkButton(buttons_frame, text="Carregar Arquivo",
                                           font=ctk.CTkFont(size=14, weight="bold"), height=40, corner_radius=10,
                                           fg_color=self.colors['secondary'], hover_color=self.colors['accent'],
                                           command=self.load_companies_file)
        self.load_file_btn.grid(row=0, column=0, padx=(0, 10))

        self.clear_btn = ctk.CTkButton(buttons_frame, text="Limpar Campo", font=ctk.CTkFont(size=14, weight="bold"),
                                       height=40, corner_radius=10, fg_color="transparent", border_width=2,
                                       border_color=self.colors['secondary'], text_color=self.colors['secondary'],
                                       hover_color=self.colors['accent'], command=self.clear_companies_input)
        self.clear_btn.grid(row=0, column=1)

        self.start_btn = ctk.CTkButton(buttons_frame, text="Iniciar Atualização",
                                       font=ctk.CTkFont(size=16, weight="bold"), height=40, corner_radius=10,
                                       fg_color=self.colors['success'], hover_color="#059669",
                                       command=self.start_automation_process)
        self.start_btn.grid(row=0, column=2, padx=(20, 0), sticky="ew")

        # Frame de progresso, inicialmente oculto
        self.progress_frame = ctk.CTkFrame(main_card, fg_color="transparent")
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="", font=ctk.CTkFont(size=14),
                                           text_color="#94a3b8")
        self.progress_label.pack(pady=(0, 5))
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=20, corner_radius=10,
                                               progress_color=self.colors['success'])
        self.progress_bar.pack(fill="x", expand=True)
        self.progress_bar.set(0)

    def create_settings_section(self):
        """Cria a seção de configurações opcionais."""
        settings_card = ctk.CTkFrame(self.main_frame, fg_color=self.colors['card_bg'], corner_radius=15)
        settings_card.pack(fill="x", pady=(0, 15), ipady=15)
        ctk.CTkLabel(settings_card, text="Configurações (Opcional)", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="white").pack(pady=(10, 10))

        config_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        config_frame.pack(fill="x", padx=30, pady=(0, 15))
        config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(config_frame, text="Timeout WebDriver (segundos):", font=ctk.CTkFont(size=14),
                     text_color="white").grid(row=0, column=0, sticky="w", pady=5)
        self.timeout_entry = ctk.CTkEntry(config_frame, width=100, font=ctk.CTkFont(size=14))
        self.timeout_entry.grid(row=0, column=1, sticky="e", padx=(20, 0))
        self.timeout_entry.insert(0, "30")

        ctk.CTkLabel(config_frame, text="Modo Headless (Navegador Invisível):", font=ctk.CTkFont(size=14),
                     text_color="white").grid(row=1, column=0, sticky="w", pady=5)
        self.headless_switch = ctk.CTkSwitch(config_frame, text="", progress_color=self.colors['success'])
        self.headless_switch.grid(row=1, column=1, sticky="e", padx=(20, 0))

    def create_footer(self):
        """Cria o rodapé da aplicação."""
        footer_frame = ctk.CTkFrame(self.main_frame, height=50, fg_color=self.colors['card_bg'], corner_radius=15)
        footer_frame.pack(fill="x", pady=(0, 5), side="bottom")
        footer_frame.pack_propagate(False)
        ctk.CTkLabel(footer_frame, text="© 2025 Grupo Meta - Soluções Contábeis | Adaptado para SIEG",
                     font=ctk.CTkFont(size=12), text_color="#64748b").pack(expand=True)

    def load_companies_file(self):
        """Abre uma janela para carregar códigos de um arquivo .txt ou .csv."""
        if self.is_processing:
            CTkMessagebox(title="Atenção",
                          message="Aguarde o processo atual finalizar antes de carregar um novo arquivo.",
                          icon="warning", master=self)
            return
        file_path = filedialog.askopenfilename(title="Selecionar arquivo de códigos",
                                               filetypes=[("Arquivos de texto", "*.txt"), ("Arquivos CSV", "*.csv"),
                                                          ("Todos", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                self.companies_entry.delete("1.0", "end")
                self.companies_entry.insert("1.0", content)
                self.logger.info(f"Arquivo de códigos carregado com sucesso: {os.path.basename(file_path)}")
            except Exception as e:
                self.logger.error(f"Erro ao carregar arquivo de códigos: {file_path}", exc_info=True)
                CTkMessagebox(title="Erro de Leitura", message=f"Não foi possível ler o arquivo:\n{e}", icon="cancel",
                              master=self)

    def clear_companies_input(self):
        """Limpa o campo de texto dos códigos de empresa."""
        if self.is_processing:
            CTkMessagebox(title="Atenção", message="Não é possível limpar o campo durante o processamento.",
                          icon="warning", master=self)
            return
        self.companies_entry.delete("1.0", "end")
        self.logger.info("Campo de códigos de empresas limpo pelo usuário.")

    def _parse_and_validate_company_codes(self, text_input: str) -> tuple[list[str], list[str]]:
        """
        Analisa o texto de entrada, separa os códigos e valida se são puramente numéricos.
        Retorna uma tupla contendo duas listas: (codigos_validos, codigos_invalidos).
        """
        if not text_input.strip():
            return [], [] # Retorna listas vazias se a entrada estiver em branco

        # Separa os códigos por vírgula, espaço ou quebra de linha.
        # Filtra quaisquer strings vazias que possam resultar da separação.
        potential_codes = re.split(r'[,\n\r\s]+', text_input.strip())
        potential_codes = [code for code in potential_codes if code]

        valid_codes = []
        invalid_codes = []
        seen_codes = set() # Usado para evitar códigos válidos duplicados

        for code in potential_codes:
            if code.isdigit(): # Verifica se a string contém APENAS dígitos
                if code not in seen_codes:
                    valid_codes.append(code)
                    seen_codes.add(code)
            else:
                # Se contiver qualquer outro caractere, é inválido
                invalid_codes.append(code)

        return valid_codes, invalid_codes

    def start_automation_process(self):
        """Inicia o processo de automação em uma nova thread."""
        if self.is_processing:
            self.logger.warning("Tentativa de iniciar processo enquanto outro já está em execução.")
            CTkMessagebox(title="Atenção", message="Um processo já está em andamento.", icon="warning", master=self)
            return

        companies_text = self.companies_entry.get("1.0", "end-1c")

        valid_codes, invalid_codes = self._parse_and_validate_company_codes(companies_text)

        if invalid_codes:
            self.logger.error(f"Entrada inválida detectada. Códigos inválidos: {invalid_codes}")
            # Cria uma mensagem de erro para o usuário
            error_message = (
                "Os seguintes códigos são inválidos, pois contêm letras ou caracteres especiais:\n\n"
                f" - {', '.join(invalid_codes)}\n\n"
                "Por favor, insira apenas códigos numéricos."
            )
            CTkMessagebox(title="Códigos Inválidos Encontrados", message=error_message, icon="cancel", master=self)
            return

        # 3. Verifica se há pelo menos um código válido para processar
        if not valid_codes:
            self.logger.error("Nenhum código de empresa válido foi fornecido para iniciar o processo.")
            CTkMessagebox(title="Nenhum Código Válido", message="Nenhum código válido foi encontrado para processar. Por favor, verifique a entrada.", icon="warning", master=self)
            return # Impede o início do processo

        # 4. Se todas as validações passaram, continua com a automação
        self.cod_empresas_dominio_list = valid_codes
        self.empresas_problema = []
        self.total_companies_to_process = len(self.cod_empresas_dominio_list)
        self.cancel_requested = False
        self.processed_companies_count = 0
        self.logger.info(f"Iniciando processo de automação para {self.total_companies_to_process} empresa(s) válidas: {', '.join(self.cod_empresas_dominio_list)}")

        # Configura a UI para o modo de processamento
        self.progress_frame.pack(fill="x", padx=30, pady=(10, 20), after=self.start_btn.master.master)
        self.update_progress_display(0, 0, self.total_companies_to_process, "Preparando...")

        # Muda o botão para a função de CANCELAR
        self.start_btn.configure(
            text="Cancelar Processo",
            command=self.request_cancellation,
            fg_color=self.colors['error'],
            hover_color="#c13e3e"
        )
        self.is_processing = True

        # Inicia a thread de automação
        automation_thread = threading.Thread(target=self.run_selenium_automation_thread,
                                             args=(self.cod_empresas_dominio_list,),
                                             daemon=True)
        automation_thread.start()
        self.logger.debug("Thread de automação Selenium iniciada.")

    def update_progress_display(self, progress_value: float, current_processed: int, total_to_process: int, status_text: str = "Processando..."):
        """Atualiza a barra de progresso e o texto de status na GUI."""

        def _update():
            if self.progress_bar.winfo_exists() and self.progress_label.winfo_exists():
                self.progress_bar.set(progress_value)
                self.progress_label.configure(
                    text=f"{status_text} ({current_processed}/{total_to_process}) - {int(progress_value * 100)}%")

        # Garante que a atualização da GUI ocorra na thread principal
        self.after(0, _update)

    def run_selenium_automation_thread(self, company_codes_list: list[str]):
        """Função principal da thread de automação."""
        self.logger.info(f"Thread de automação iniciada para {len(company_codes_list)} códigos.")
        try:
            if not self.open_browser():
                self.logger.error("Falha ao abrir o navegador. Encerrando thread de automação.")
                return

            if self.perform_login():
                self.process_all_companies(company_codes_list)
            else:
                self.logger.error("Falha no login. Processamento de empresas não continuará.")

        except WebDriverException:
            # Esta excepção é esperada quando o navegador é fechado remotamente pelo botão Cancelar.
            if self.cancel_requested:
                self.logger.info("A automação foi interrompida com sucesso pelo pedido do utilizador.")
            else:
                # Se não foi um cancelamento, foi um erro inesperado de driver/navegador.
                self.logger.critical("O navegador ou o driver foi encerrado inesperadamente durante a operação.", exc_info=True)

        except Exception:
            self.logger.critical("Erro crítico não tratado na thread de automação.", exc_info=True)

        finally:
            self.logger.info("Rotina de limpeza da thread iniciada.")
            self.cleanup_final()
            self.after(0, self.finish_process_ui)
            self.logger.info("Thread de automação Selenium concluída.")

    def open_browser(self) -> bool:
        """Configura e abre o navegador Selenium."""
        try:
            self.logger.info("Tentando iniciar o navegador Chrome...")
            chrome_driver_path = OUTPUT_PATH / "chrome_standalone" / "chromedriver.exe"
            chrome_exe_path = OUTPUT_PATH / "chrome_standalone" / "chrome.exe"

            if not chrome_driver_path.exists() or not chrome_exe_path.exists():
                msg = f"ChromeDriver ou Chrome.exe não encontrado na pasta 'chrome_standalone'."
                self.logger.error(msg + f" (ChromeDriver: {chrome_driver_path}, Chrome: {chrome_exe_path})")
                CTkMessagebox(title="Erro Crítico", message=f"{msg}\n\nVerifique a pasta 'chrome_standalone'.",
                              icon="cancel", master=self)
                return False

            service = Service(executable_path=str(chrome_driver_path))
            options = Options()
            options.binary_location = str(chrome_exe_path)
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            if self.headless_switch.get() == 1:
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=200,200")
                self.logger.info("Modo Headless (navegador invisível) ativado.")
            else:
                self.logger.info("Modo Headless desativado (navegador visível).")

            self.navegador = webdriver.Chrome(service=service, options=options)
            if not self.headless_switch.get() == 1: self.navegador.maximize_window()
            self.logger.info("Navegador Chrome iniciado com sucesso.")
            return True
        except Exception:
            self.logger.error("Erro fatal ao iniciar o navegador Chrome.", exc_info=True)
            CTkMessagebox(title="Erro no Navegador",
                          message=f"Não foi possível iniciar Chrome Driver.\n\nVerifique os logs para detalhes.",
                          icon="cancel", master=self)
            return False

    def perform_login(self) -> bool:
        """Executa o processo de login no Sieg Hub."""
        if not self.navegador:
            self.logger.error("Tentativa de login, mas o navegador não está aberto.")
            return False

        try:
            self.logger.info("Iniciando processo de login no Sieg Hub...")
            self.navegador.get('https://hub.sieg.com/')
            timeout_val = int(self.timeout_entry.get() or "30")
            self.logger.debug(f"Timeout para elementos da página: {timeout_val} segundos.")

            self.navegador.find_element(By.ID, 'txtEmail').send_keys(self.email)
            self.navegador.find_element(By.ID, 'txtPassword').send_keys(self.senha)
            self.navegador.find_element(By.ID, 'btnSubmit').click()

            self.logger.info("Botão 'Entrar' clicado. Aguardando confirmação de login...")

            login_success_condition = EC.any_of(
                EC.visibility_of_element_located((By.ID, "lnkSair")),
                EC.url_contains("default.aspx")
            )
            WebDriverWait(self.navegador, timeout_val + 15).until(login_success_condition)
            self.logger.info(f"Login no Sieg Hub realizado com sucesso. URL atual: {self.navegador.current_url}")
            return True

        except Exception:
            self.logger.error(
                f"Falha durante o processo de login no Sieg Hub. URL final: {self.navegador.current_url if self.navegador else 'N/A'}",
                exc_info=True)
            try:
                error_shot_path = DEBUG_SCREENSHOTS_PATH / f"login_error_timeout_{int(time.time())}.png"
                if self.navegador: self.navegador.save_screenshot(str(error_shot_path))
                self.logger.warning(f"Screenshot do erro de login salvo em: {error_shot_path}")
                error_divs = self.navegador.find_elements(By.XPATH,
                                                          "//*[@id='returnError']/div | //div[contains(@class,'alert-danger')]")
                if error_divs and error_divs[0].text.strip():
                    self.logger.error(f"Mensagem de erro detectada na página de login: '{error_divs[0].text.strip()}'")
            except Exception as e_debug:
                self.logger.warning(
                    f"Não foi possível capturar detalhes adicionais da página de erro de login: {e_debug}")
            return False

    def process_all_companies(self, company_codes_list: list[str]):
        if not self.navegador:
            self.logger.error("Navegador não está disponível para processar empresas.")
            return

        self.logger.info(f"Iniciando processamento em lote de {len(company_codes_list)} empresa(s).")
        for index, cod_empresa_str in enumerate(company_codes_list):
            # --- VERIFICAÇÃO DE CANCELAMENTO ---
            # Antes de processar cada nova empresa, verifica se o cancelamento foi solicitado.
            if self.cancel_requested:
                self.logger.info("Cancelamento detectado dentro do loop. Interrompendo o processamento de empresas.")
                break

            # Se não foi cancelado, o código continua
            current_company_num = index + 1
            self.logger.info(
                f"--- Processando empresa Cód: {cod_empresa_str} ({current_company_num}/{self.total_companies_to_process}) ---")
            status_text_progress = f"Empresa {cod_empresa_str}"
            self.update_progress_display(index / self.total_companies_to_process, index, self.total_companies_to_process, status_text_progress)

            success_this_company = self.process_single_company(cod_empresa_str)

            if success_this_company:
                self.processed_companies_count += 1
                self.logger.info(f"--- SUCESSO Empresa Cód: {cod_empresa_str} ---")
            else:
                self.logger.error(
                    f"--- FALHA Empresa Cód: {cod_empresa_str} (verificar logs anteriores para detalhes) ---")

            self.update_progress_display(current_company_num / self.total_companies_to_process, current_company_num,
                                         self.total_companies_to_process,
                                         status_text_progress + (" - OK" if success_this_company else " - Falha"))
            time.sleep(0.5)

        # Se o loop terminou, regista a informação.
        if self.cancel_requested:
            self.logger.info("Processamento em lote interrompido pelo utilizador.")
        else:
            self.logger.info("Processamento em lote de todas as empresas listadas foi concluído.")

    def process_single_company(self, cod_empresa_str: str) -> bool:
        if not (self.navegador and self.navegador.service.is_connectable()):
            self.logger.error(f"Navegador inválido ou desconectado antes de processar a empresa {cod_empresa_str}.")
            return False

        self.logger.debug(f"Iniciando processamento para código: {cod_empresa_str}")
        timeout_val = int(self.timeout_entry.get() or "30")
        razaoSocial, cnpjEmpresa = "N/A", "N/A"
        caminho_pfx_completo = None

        try:
            # Etapa 1: Obter dados da empresa e do certificado
            dadosEmpresa = banco.obterDadosEmpresaDominio(cod_empresa_str)
            if not dadosEmpresa or len(dadosEmpresa) < 3:
                self.logger.warning(f"Dados da empresa {cod_empresa_str} não encontrados na Domínio. Pulando.")
                self.empresas_problema.append({'code': cod_empresa_str, 'razao': razaoSocial, 'cnpj': cnpjEmpresa, 'status': 'Empresa não encontrada na Domínio'})
                return False
            cnpjEmpresa, ufEmpresa, razaoSocial = dadosEmpresa[0], dadosEmpresa[1], dadosEmpresa[2]
            self.logger.info(
                f"Dados obtidos da Domínio para {cod_empresa_str}: CNPJ {cnpjEmpresa}, Razão '{razaoSocial}'")

            try:
                certificado_data = banco.baixarCertificadoEmpresa(cnpjEmpresa, cod_empresa_str, OUTPUT_PATH)
                if not certificado_data or len(certificado_data) < 5:
                    raise banco.CertificadoNaoEncontradoError("Dados do certificado retornados são inválidos.")
            except banco.CertificadoNaoEncontradoError as e:
                self.logger.warning(f"Certificado para CNPJ {cnpjEmpresa} (Empresa {cod_empresa_str}) não encontrado. Registrando e continuando.")
                self.empresas_problema.append({'code': cod_empresa_str, 'razao': razaoSocial, 'status': 'Certificado Não Encontrado'})
                return False




            senha_certificado, caminho_pfx_relativo = certificado_data[1], certificado_data[4]
            caminho_pfx_completo = OUTPUT_PATH / caminho_pfx_relativo
            if not caminho_pfx_completo.exists():
                self.logger.error(f"Arquivo PFX '{caminho_pfx_completo}' não encontrado no disco. Verifique banco.py. Pulando.")
                self.empresas_problema.append({'code': cod_empresa_str, 'razao': razaoSocial, 'status': 'Erro ao salvar PFX'})
                return False
            self.logger.info(f"Certificado baixado com sucesso: {caminho_pfx_completo.name}")

            # Etapa 2: Navegação e Upload
            url_edicao = f'https://hub.sieg.com/Adicionar-certificado.aspx?edit=true&certificateId=23942-{cnpjEmpresa}'
            self.navegador.get(url_edicao)
            self.logger.debug(f"Acessando URL de edição: {url_edicao}")

            temQueCadastrar = False
            try:
                WebDriverWait(self.navegador, 6).until(EC.visibility_of_element_located(
                    (By.XPATH, '//*[@id="returnError"]/div[contains(.,"não encontrado")]')))
                self.logger.info(f"Empresa CNPJ {cnpjEmpresa} não encontrada no Sieg. Procedendo como novo cadastro.")
                self.navegador.get('https://hub.sieg.com/adicionar-certificado.aspx')
                temQueCadastrar = True
                WebDriverWait(self.navegador, timeout_val).until(
                    EC.presence_of_element_located((By.ID, 'certificateFile')))
            except TimeoutException:
                self.logger.info(f"Empresa CNPJ {cnpjEmpresa} já cadastrada. Procedendo como atualização.")

            if not temQueCadastrar:
                try:
                    self.navegador.find_element(By.ID, 'chkUpdateFile').click()
                    self.logger.info("Checkbox 'Atualizar arquivo' marcada.")
                except Exception:
                    self.logger.warning("Não foi possível marcar 'chkUpdateFile' (pode não ser necessário).",
                                        exc_info=False)

            time.sleep(2)
            self.navegador.find_element(By.ID, 'certificateFile').send_keys(str(caminho_pfx_completo))
            self.navegador.find_element(By.ID, 'passwordCert').send_keys(senha_certificado)
            self.navegador.find_element(By.ID, 'validated-certificate').click()
            self.logger.info("Arquivo PFX e senha enviados, validação iniciada.")

            try:
                divErro = WebDriverWait(self.navegador, 7).until(
                    EC.visibility_of_element_located((By.XPATH, '//*[@id="returnError"]/div')))
                erro_txt = divErro.text.strip()
                if "vencido" in erro_txt.lower() or "inválida" in erro_txt.lower():
                    self.logger.warning(f"CERTIFICADO VENCIDO/INVÁLIDO para {cnpjEmpresa}: {erro_txt}")
                    self.empresas_problema.append({'code': cod_empresa_str, 'razao': razaoSocial, 'status': 'Certificado Vencido/Inválido'})
                    with open(CERTIFICADOS_PROBLEMAS_FILE, 'a', encoding='utf-8') as f:
                        f.write(f'{cod_empresa_str}|{razaoSocial}|{cnpjEmpresa}|PROBLEMA: {erro_txt}\n')
                    return False
            except TimeoutException:
                self.logger.info("Nenhuma mensagem de erro (vencido/inválido) detectada.")

            # Etapa 3: Preenchimento do Formulário
            self.navegador.find_element(By.ID, 'chkUpdateFileIrisAndIr').click()
            self.logger.debug("Checkbox 'IRIS' marcada.")

            # Preenchimento robusto de CNPJ e Nome
            self.logger.debug(f"Inserindo CNPJ '{cnpjEmpresa}' no formulário.") #LOG
            campoCNPJ = WebDriverWait(self.navegador, timeout_val).until(
                EC.presence_of_element_located((By.ID, 'cnpjCert')))
            time.sleep(0.1)
            acoes = ActionChains(self.navegador)
            acoes.double_click(on_element=campoCNPJ)
            acoes.perform()
            time.sleep(1)
            campoCNPJ.send_keys(Keys.BACKSPACE)
            time.sleep(1)
            self.navegador.execute_script("arguments[0].value = ''; arguments[0].value = arguments[1];", campoCNPJ, cnpjEmpresa)
            campoCNPJ.send_keys(Keys.SPACE)
            self.logger.info(f"CNPJ {cnpjEmpresa} inserido.")

            nome_fmt = f'{cod_empresa_str:0>4} - {razaoSocial}'
            campoNome = self.navegador.find_element(By.ID, 'nameCert')
            self.navegador.execute_script("arguments[0].value = arguments[1];", campoNome, nome_fmt)
            self.logger.debug(f"Nome da empresa '{nome_fmt}' inserido.")

            # Navegação pelos passos
            time.sleep(2)
            self.navegador.find_element(By.ID, 'next-step').click()
            self.logger.debug("Avançou para o passo 1.")

            if temQueCadastrar:
                self.logger.info("Preenchendo dados de novo cadastro (UF, XML Cancelados).")
                WebDriverWait(self.navegador, timeout_val).until(
                    EC.element_to_be_clickable((By.ID, 'ufCert'))).send_keys(ufEmpresa)
                self.navegador.find_element(By.ID, 'chkBoxXmlCancelados').click()

            cbNoturna = WebDriverWait(self.navegador, timeout_val).until(
                EC.presence_of_element_located((By.ID, 'chkActiveNightConsult')))
            if not cbNoturna.is_selected():
                self.logger.info("'Consulta Noturna' desmarcada, tentando marcar...")
                WebDriverWait(self.navegador, 10).until(EC.element_to_be_clickable(cbNoturna)).click()

            time.sleep(2)
            self.navegador.find_element(By.ID, 'next-step').click()
            self.logger.debug("Avançou para o passo 2.")

            if temQueCadastrar:
                self.logger.info("Preenchendo dados de novo cadastro (NFe, CTe).")
                WebDriverWait(self.navegador, timeout_val).until(
                    EC.element_to_be_clickable((By.ID, 'chkBoxNfe'))).click()
                time.sleep(0.3)
                self.navegador.find_element(By.ID, 'chkBoxCte').click()

            time.sleep(2)
            self.navegador.find_element(By.ID, 'next-step').click()
            self.logger.debug("Avançou para o passo final (confirmação).")

            time.sleep(2)
            WebDriverWait(self.navegador, 30).until(EC.element_to_be_clickable((By.ID, 'btnAddCertificate'))).click()
            self.logger.info("Botão final 'Adicionar Certificado' clicado. Aguardando sucesso...")

            WebDriverWait(self.navegador, 25).until(EC.presence_of_element_located((By.XPATH,
                                                                                    "//b[contains(text(),'Certificado Cadastrado com Sucesso!') or contains(text(),'Certificado Atualizado com Sucesso!')]")))
            self.logger.info(f"Mensagem de sucesso recebida para empresa {cod_empresa_str}.")

            # Cadastro no IRIS se necessário
            if temQueCadastrar:
                self.logger.info(f"Iniciando cadastro no SIEG Iris para {cod_empresa_str}...")
                cadastro_IRIS.cadastrarIRIS(self.navegador, dadosEmpresa, str(caminho_pfx_completo), senha_certificado)
                self.logger.info(f"Cadastro no SIEG Iris para {cod_empresa_str} concluído.")

            return True

        except banco.CertificadoNaoEncontradoError as e:
            # Trata um erro esperado de forma controlada
            self.logger.warning(f"Certificado para CNPJ {cnpjEmpresa} (Empresa {cod_empresa_str}) não foi encontrado: {e}")
            self.empresas_problema.append({'code': cod_empresa_str, 'razao': razaoSocial, 'status': 'Certificado Não Encontrado'})
            return False

        except Exception:
            if self.cancel_requested:
                raise

            self.logger.error(f"FALHA GERAL no processamento da empresa {cod_empresa_str} (CNPJ: {cnpjEmpresa})", exc_info=True)
            self.empresas_problema.append({'code': cod_empresa_str, 'razao': razaoSocial, 'status': 'Erro Inesperado'})
            return False

        finally:
            # O arquivo PFX não será mais removido aqui.
            # A limpeza será feita no final de todo o processo.
            self.logger.debug(f"Finalizando processamento para empresa {cod_empresa_str}.")

    def cleanup_final(self):

        self.logger.info("Iniciando rotina de limpeza final...")

        # Limpar pasta de certificados
        self.cleanup_certificates_folder()

        # Fechar navegador
        if self.navegador:
            try:
                self.navegador.quit()
                self.logger.info("Navegador Chrome fechado com sucesso.")
            except Exception:
                self.logger.warning("Erro ao tentar fechar o navegador (pode já estar fechado).", exc_info=True)
            finally:
                self.navegador = None

        self.cleanup_certificates_folder()

        # Finalizar processos ChromeDriver remanescentes (mais seguro que conhost.exe)
        try:
            processo_a_matar = "chromedriver.exe"
            self.logger.info(f"Tentando finalizar processos '{processo_a_matar}' remanescentes...")
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(["taskkill", "/F", "/IM", processo_a_matar], check=False, startupinfo=startupinfo,
                               capture_output=True)
                self.logger.info(f"Comando para finalizar '{processo_a_matar}' executado.")
        except Exception:
            self.logger.error(f"Erro ao tentar executar taskkill para '{processo_a_matar}'.", exc_info=True)

        self.logger.info("Rotina de limpeza final concluída.")

    def _force_quit_browser_in_thread(self):
        """
        Executa o comando para fechar o navegador numa thread separada para não bloquear a UI.
        """
        if self.navegador:
            try:
                self.navegador.quit()
                self.logger.info("Comando para fechar o navegador enviado para interrupção imediata.")
            except Exception as e:
                # Loga o erro mas não incomoda o utilizador, pois o objetivo principal (fechar) provavelmente funcionou.
                self.logger.error(f"Erro ao tentar forçar o fecho do navegador numa thread: {e}", exc_info=False)

    def cleanup_certificates_folder(self):
        cert_dir = OUTPUT_PATH / "certificados"
        if not cert_dir.is_dir():
            self.logger.info(f"Pasta de certificados '{cert_dir}' não encontrada para limpeza.")
            return

        self.logger.info(f"Limpando arquivos .pfx da pasta '{cert_dir}'...")
        cleaned_count = 0
        for item in os.listdir(cert_dir):
            if item.lower().endswith('.pfx'):
                try:
                    os.remove(cert_dir / item)
                    cleaned_count += 1
                except Exception:
                    self.logger.warning(f"Erro ao remover arquivo de certificado: {item}", exc_info=True)
        self.logger.info(f"{cleaned_count} arquivo(s) .pfx removidos da pasta de certificados.")

    def finish_process_ui(self):
        self.logger.info("Atualizando UI após conclusão do processo.")
        self.is_processing = False

        if self.start_btn.winfo_exists():
            self.start_btn.configure(
                state="normal",
                text="Iniciar Atualização",
                command=self.start_automation_process,
                fg_color=self.colors['success'],
                hover_color="#059669"
            )

        if self.empresas_problema:
            self.logger.warning(f"Processo finalizado com {len(self.empresas_problema)} pendência(s).")

            # Monta a mensagem para a janela de relatório
            report_message = "As seguintes empresas não foram atualizadas e requerem atenção:\n"
            for company in self.empresas_problema:
                report_message += f"\n- Cód: {company['code']}, Razão: {company['razao']}\n"
                report_message += f"  Motivo: {company['status']}\n"

            # Exibe o relatório em uma CTkMessagebox
            CTkMessagebox(title="Relatório de Pendências",
                          message=report_message,
                          icon="warning",
                          width=500,
                          master=self)
        else:
            self.logger.info("Processo finalizado sem nenhuma pendência registrada.")

        final_msg = "Processo finalizado."
        log_level = "INFO"
        icon_type = "info"

        if self.total_companies_to_process > 0:
            rate = (self.processed_companies_count / self.total_companies_to_process) * 100
            final_msg += f" {self.processed_companies_count} de {self.total_companies_to_process} empresa(s) com sucesso ({rate:.0f}%)."
            if rate == 100:
                icon_type = "check"
            elif self.processed_companies_count > 0:
                icon_type = "warning"
                log_level = "WARNING"
            else:
                icon_type = "cancel"
                log_level = "ERROR"
        else:
            final_msg = "Processo finalizado. Nenhuma empresa válida foi processada."

        # Loga a mensagem final no nível apropriado
        getattr(self.logger, log_level.lower(), self.logger.info)(final_msg)

        if self.winfo_exists():
            CTkMessagebox(title="Processo Concluído", message=final_msg, icon=icon_type, master=self)
            self.progress_frame.pack_forget()  # Oculta a barra de progresso

    def run(self):
        try:
            self.logger.info("Iniciando o mainloop da aplicação.")
            self.mainloop()
        except Exception:
            self.logger.critical("Erro fatal não tratado no mainloop da aplicação.", exc_info=True)
        finally:
            self.logger.info("Aplicação encerrada.")
            logging.shutdown()


# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                        handlers=[
                            logging.FileHandler(LOG_FILE_PATH, mode='w', encoding='utf-8'),
                            logging.StreamHandler()  # Para ver logs iniciais também no console
                        ],
                        force=True)

    main_logger = logging.getLogger(__name__)
    try:
        # main_logger.info("Script principal (__main__) iniciado.")
        app = AtualizadorSiegApp()
        if hasattr(app, 'email') and app.winfo_exists():
            app.run()
        else:
            main_logger.error(
                "Falha crítica na inicialização da aplicação (provavelmente config .env ou janela fechada). A GUI não será executada.")
    except Exception:
        main_logger.critical("Erro crítico global durante a inicialização ou execução da aplicação.", exc_info=True)
        try:
            # Fallback para um erro muito básico se CTk não puder ser usado
            from tkinter import messagebox

            messagebox.showerror("Erro Crítico na Aplicação",
                                 f"Ocorreu um erro irrecuperável.\n\nConsulte o arquivo de log para detalhes:\n{LOG_FILE_PATH}")
        except:
            print(f"ERRO CRÍTICO IRRECUPERÁVEL. Consulte o arquivo de log: {LOG_FILE_PATH}")
    finally:
        main_logger.info("Script principal (__main__) finalizado.")