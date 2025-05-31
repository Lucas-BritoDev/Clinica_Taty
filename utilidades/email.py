import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carregar variáveis de ambiente
load_dotenv()

def get_smtp_settings(provider=None):
    """
    Retorna as configurações SMTP com base no provedor de email.
    """
    # Usar o provedor especificado ou pegar do ambiente
    provider = provider or os.getenv("EMAIL_PROVIDER", "gmail")
    
    smtp_settings = {
        "gmail": {
            "server": "smtp.gmail.com",
            "port": 587,
            "use_ssl": False
        },
        "outlook": {
            "server": "smtp-mail.outlook.com",
            "port": 587,
            "use_ssl": False
        },
        "yahoo": {
            "server": "smtp.mail.yahoo.com",
            "port": 587,
            "use_ssl": False
        },
        "outro": {
            "server": os.getenv("SMTP_SERVER", ""),
            "port": int(os.getenv("SMTP_PORT", 587)),
            "use_ssl": os.getenv("SMTP_SSL", "False").lower() == "true"
        }
    }
    
    return smtp_settings.get(provider, smtp_settings["outro"])

def verificar_credenciais_email(email, senha, provider=None, custom_smtp=None):
    """
    Verifica se as credenciais de email estão corretas tentando se conectar ao servidor SMTP.
    
    Args:
        email (str): Email do remetente
        senha (str): Senha do email
        provider (str, optional): Provedor de email (gmail, outlook, yahoo, outro)
        custom_smtp (dict, optional): Configurações SMTP personalizadas para provedor "outro"
    
    Returns:
        tuple: (sucesso, mensagem)
    """
    try:
        if not email or not senha:
            return False, "Email e senha são obrigatórios"
        
        # Obter configurações SMTP
        if provider == "outro" and custom_smtp:
            smtp_config = custom_smtp
        else:
            smtp_config = get_smtp_settings(provider)
        
        # Conectar ao servidor SMTP
        if smtp_config["use_ssl"]:
            server = smtplib.SMTP_SSL(smtp_config["server"], smtp_config["port"])
        else:
            server = smtplib.SMTP(smtp_config["server"], smtp_config["port"])
            server.starttls()
        
        # Fazer login
        server.login(email, senha)
        
        # Se chegar aqui, o login foi bem-sucedido
        server.quit()
        return True, "Credenciais válidas"
    
    except smtplib.SMTPAuthenticationError:
        return False, "Credenciais inválidas. Verifique seu e-mail e senha."
    except smtplib.SMTPConnectError:
        return False, f"Não foi possível conectar ao servidor {smtp_config['server']}:{smtp_config['port']}"
    except Exception as e:
        return False, f"Erro ao verificar credenciais: {str(e)}"

def enviar_email(destinatario, assunto, corpo, anexo=None):
    """
    Envia um email com ou sem anexo.
    
    Args:
        destinatario (str): Email do destinatário
        assunto (str): Assunto do email
        corpo (str): Corpo do email (texto)
        anexo (str, optional): Caminho para o arquivo a ser anexado
    
    Returns:
        tuple: (sucesso, mensagem)
    """
    try:
        # Obter credenciais do ambiente ou da sessão
        remetente = os.getenv("EMAIL_REMETENTE")
        senha = os.getenv("EMAIL_SENHA")
        provider = os.getenv("EMAIL_PROVIDER", "gmail")
        
        if not remetente or not senha:
            return False, "Credenciais de email não configuradas"
        
        # Obter configurações SMTP
        smtp_config = get_smtp_settings(provider)
        
        # Criar mensagem
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = assunto
        
        # Adicionar corpo do email
        msg.attach(MIMEText(corpo, 'plain'))
        
        # Adicionar anexo, se houver
        if anexo and os.path.exists(anexo):
            with open(anexo, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(anexo))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(anexo)}"'
                msg.attach(part)
        
        # Conectar ao servidor e enviar
        if smtp_config["use_ssl"]:
            server = smtplib.SMTP_SSL(smtp_config["server"], smtp_config["port"])
        else:
            server = smtplib.SMTP(smtp_config["server"], smtp_config["port"])
            server.starttls()
        
        server.login(remetente, senha)
        server.send_message(msg)
        server.quit()
        
        return True, "Email enviado com sucesso"
    
    except Exception as e:
        logging.error(f"Erro ao enviar email: {str(e)}")
        return False, f"Erro ao enviar email: {str(e)}"