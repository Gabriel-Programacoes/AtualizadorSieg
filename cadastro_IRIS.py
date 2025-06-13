import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def cadastrarIRIS(navegador, dadosEmpresa, caminho_PFX, senhaCertificado):
    navegador.get(f'https://hub.sieg.com/IriS/#/Certificados')
    time.sleep(2)
    acoes = ActionChains(navegador)
    acoes.move_by_offset(100, 100)
    acoes.click()
    acoes.perform()
    WebDriverWait(navegador, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="manageCertificates"]/div[2]/a')))
    time.sleep(.2)
    navegador.find_element(By.XPATH, '//*[@id="manageCertificates"]/div[2]/a').click()
    WebDriverWait(navegador, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[5]/div[3]/div/div[2]/div/div/div[2]/div[4]/div/input')))
    time.sleep(3)
    navegador.find_element(By.XPATH,'/html/body/form/div[5]/div[3]/div/div[2]/div/div/div[2]/div[4]/div/input').send_keys(caminho_PFX)
    campo_CPF = navegador.find_element(By.ID, 'txtCertificateCnpjOrCpf')
    navegador.execute_script(f"arguments[0].value = '{dadosEmpresa[0]}'", campo_CPF)
    time.sleep(.1)
    navegador.find_element(By.ID, 'txtPasswordCertificate').send_keys(senhaCertificado)
    time.sleep(.1)
    navegador.find_element(By.ID, 'txtCertificateName').send_keys(f'{dadosEmpresa[3]:04} - {dadosEmpresa[2]}')
    time.sleep(.1)
    navegador.find_element(By.ID, 'chkAware').click()
    navegador.find_element(By.ID, 'btnAddCertificateIris').click()
    time.sleep(2)