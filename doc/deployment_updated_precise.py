import json
from fabric import Connection
import argparse
from paramiko import AutoAddPolicy
import concurrent.futures
import logging
import os
from io import StringIO

# Check if the logs directory exists, if not, create it.
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(filename='deployment.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Parse command line arguments
try:
    parser = argparse.ArgumentParser()
    parser.add_argument('--install_data', action='store_true', help='Whether to install data')
    parser.add_argument('--install_driver', action='store_true', help='Whether to install driver')
    parser.add_argument('--install_service', action='store_true', help='Whether to install service')
    parser.add_argument('--force_restart', action='store_true', help='Whether to force restart after deployment')
    parser.add_argument('--install_api', action='store_true', help='Whether to install API')
    parser.add_argument('--restart_service', action='store_true', help='Whether to restart service after deployment')
    parser.add_argument('--install_http', action='store_true', help='Whether to install nginx server to host a folder')
    args = parser.parse_args()
    install_data = args.install_data
    install_driver = args.install_driver
    install_service = args.install_service
    force_restart = args.force_restart
    install_api = args.install_api
    restart_service = args.restart_service    
    install_http = args.install_http    
except Exception:
    install_data = True
    install_driver = True
    install_service = True
    force_restart = True
    install_api = True
    restart_service = True
    install_http = True


# Local path to the config
local_config_path = './config.json'

# Load server information from JSON file
try:
    if install_api:
        server_file = 'api_servers.json'
    else:
        server_file = 'servers.json'

    with open(server_file, 'r') as file:
        servers = json.load(file)
except Exception as e:
    print(f"Failed to load server information from {server_file}: {e}")
    exit(1)

# Load other deployment settings from JSON file
try:
    with open('deploysettings.json', 'r') as file:
        deploy_settings = json.load(file)
        api_port = deploy_settings.get('api_port', 9999)
        loading_point = deploy_settings.get('loading_point', '/var/www/images') 
except Exception as e:
    print(f"Failed to load deployment settings from JSON file: {e}")
    exit(1)

# Loop through each server and deploy the project
def deploy_to_server(server, install_data, install_driver, install_service,
                      force_restart, install_api, restart_service, install_http):   
    # Set up a unique logger for this server
    logger = logging.getLogger(server['host'])
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(f'logs/{server["host"]}.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    try:
        message = f"Deploying to {server['host']}"
        logger.info(message)
        print(message)

        # Remote path where the tarball should be placed
        remote_path = f'/opt/FaceFlick.tar.gz'
        remote_data_path = f'/opt/FaceFlickData.tar.gz'

        remote_config_path = f'/opt/FaceFlick/config.json'

        # Create a new SSH connection
        with Connection(
            host=server['host'], 
            user=server['user'], 
            connect_kwargs={
                'password': server['password'],
                'allow_agent': False,
                'look_for_keys': False,
            }
        ) as conn:
            conn.client.set_missing_host_key_policy(AutoAddPolicy())
            
            # Create the FaceFlick directory on the remote server
            if conn.run(f'test -d /opt/FaceFlick', warn=True, hide=False).failed:                
                message = f"Missing FaceFlick Folder, Creating it."
                print(message)
                logger.info(message)
                conn.sudo(password=server['password'], 'mkdir -p /opt/FaceFlick', hide=False)
            else:
                message = f"Found FaceFlick Folder, Procceed with deployment."
                print(message)
                logger.info(message) 

            #Check folders existence
            if install_data != True:
                folders = ['drivers', 'gfpgan', 'models', 'packages']
                for folder in folders:
                    if conn.run(f'test -d /opt/FaceFlick/{folder}', warn=True, hide=False).failed:
                        message = f"Missing one or more data folders. Forcing install_data to True."
                        print(message)
                        logger.info(message) 
                        install_data = True
                        break
            
            if install_api:
                message = f"Installing API. Forcing install_driver and install_service to False."
                print(message)
                logger.info(message) 
                install_driver = False
                install_service = False
                install_http = False

            # Transfer the tarball to the server
            message = f"Start Transfering FaceFlick.tar.gz to server {server['host']} with {server['user']}..."
            print(message)
            logger.info(message) 

            temp_path = f"/home/{server['user']}/temp.tar.gz"
            conn.run(f'wget -O {temp_path} {deploy_settings["code_url"]} --progress=bar:force', hide=False)
            conn.sudo(password=server['password'], f'mv {temp_path} {remote_path}', hide=False)

            message = f"Completed Transfering FaceFlick.tar.gz to server {server['host']} with {server['user']}."
            print(message)
            logger.info(message) 

            if install_data:
                message = f"Start Downloading FaceFlickData.tar.gz to server {server['host']} with {server['user']}..."
                print(message)
                logger.info(message)                 
                # First download the file to a temporary location
                temp_data_path = f"/home/{server['user']}/temp_data.tar.gz"
                conn.run(f'wget -O {temp_data_path} {deploy_settings["data_url"]} --progress=bar:force', hide=False)
                # Then move the file to the desired location with sudo
                conn.sudo(password=server['password'], f'mv {temp_data_path} {remote_data_path}', hide=False)


                message = f"Completed Downloading FaceFlickData.tar.gz to server {server['host']} with {server['user']}."
                print(message)
                logger.info(message) 

            # Extract the tarball
            message = f"Start Extracting FaceFlick.tar.gz to server {server['host']} with {server['user']}..."
            print(message)
            logger.info(message) 

            conn.sudo(password=server['password'], 'tar -xzvf /opt/FaceFlick.tar.gz -C /opt/', hide=False)

            message = f"Completed Extracting FaceFlick.tar.gz to server {server['host']} with {server['user']}."
            print(message)
            logger.info(message)

            # Delete the FaceFlick.tar.gz file after extracting
            message = f"Deleting FaceFlick.tar.gz on server {server['host']} with {server['user']}..."
            print(message)
            logger.info(message)

            conn.sudo(password=server['password'], 'rm -f /opt/FaceFlick.tar.gz', hide=False)
                        
            if install_data:
                message = f"Start Extracting FaceFlickData.tar.gz to server {server['host']} with {server['user']}..."
                print(message)
                logger.info(message) 

                conn.sudo(password=server['password'], 'tar -xzvf /opt/FaceFlickData.tar.gz -C /opt/FaceFlick', hide=False)

                message = f"Completed Extracting FaceFlickData.tar.gz to server {server['host']} with {server['user']}."
                print(message)
                logger.info(message)

                # Delete the FaceFlickData.tar.gz file after extracting
                message = f"Deleting FaceFlickData.tar.gz on server {server['host']} with {server['user']}..."
                print(message)
                logger.info(message)

                conn.sudo(password=server['password'], 'rm -f /opt/FaceFlickData.tar.gz', hide=False)


            if install_driver:
                try:
                    # Installing CUDA118 Including Driver 520
                    message = f"Start installing CUDA118 Including Driver 520 to server {server['host']} with {server['user']}..."
                    print(message)
                    logger.info(message)

                    conn.sudo(password=server['password'], 'cp /opt/FaceFlick/drivers/cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600', hide=False)
                    conn.sudo(password=server['password'], 'dpkg -i /opt/FaceFlick/drivers/cuda-repo-ubuntu2204-11-8-local_11.8.0-520.61.05-1_amd64.deb', hide=False)
                    print("Copied gpg key...")
                    conn.sudo(password=server['password'], 'cp /var/cuda-repo-ubuntu2204-11-8-local/cuda-*-keyring.gpg /usr/share/keyrings/', hide=False)
                    conn.sudo(password=server['password'], 'apt-get update', hide=False)
                    conn.sudo(password=server['password'], 'DEBIAN_FRONTEND=noninteractive apt-get -y install cuda', hide=False)

                    # Updating .bashrc file
                    # Using 'echo' with 'sudo' and redirection ('>>') requires a special syntax
                    if conn.run(r'grep -Fxq "export PATH=/usr/local/cuda-11.8/bin\${PATH:+:\${PATH}}" ~/.bashrc', warn=True, hide=False).failed:
                        conn.run("echo 'export PATH=/usr/local/cuda-11.8/bin${PATH:+:${PATH}}' | sudo tee -a ~/.bashrc", hide=False)
                    else:
                        print("The PATH export line already exists in .bashrc, skipping...")

                    if conn.run(r'grep -Fxq "export LD_LIBRARY_PATH=/usr/local/cuda-11.8/lib64\${LD_LIBRARY_PATH:+:\${LD_LIBRARY_PATH}}" ~/.bashrc', warn=True, hide=False).failed:
                        conn.run("echo 'export LD_LIBRARY_PATH=/usr/local/cuda-11.8/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}' | sudo tee -a ~/.bashrc", hide=False)
                    else:
                        print("The LD_LIBRARY_PATH export line already exists in .bashrc, skipping...")


                    conn.run('source ~/.bashrc', hide=False)

                    message = f"Finished installing CUDA118 Including Driver 520 to server {server['host']} with {server['user']}."
                    print(message)
                    logger.info(message)

                    # Installing CUDNN
                    message = f"Start installing CUDNN to server {server['host']} with {server['user']}..."
                    print(message)
                    logger.info(message)

                    conn.sudo(password=server['password'], 'dpkg -i /opt/FaceFlick/drivers/cudnn-local-repo-ubuntu2204-8.9.3.28_1.0-1_amd64.deb', hide=False)
                    conn.sudo(password=server['password'], 'cp /var/cudnn-local-repo-ubuntu2204-8.9.3.28/cudnn-local-*-keyring.gpg /usr/share/keyrings/', hide=False)
                    print("Copied gpg key...")
                    conn.sudo(password=server['password'], 'apt-get update', hide=False)
                    conn.sudo(password=server['password'], 'DEBIAN_FRONTEND=noninteractive apt-get install -y libcudnn8 libcudnn8-dev', hide=False)
                    conn.run('cat /usr/include/cudnn_version.h | grep CUDNN_MAJOR -A 2', hide=False)

                    message = f"Finished installing CUDNN Including Driver 520 to server {server['host']} with {server['user']}."
                    print(message)
                    logger.info(message)
                except Exception as e:
                    message = f"Failed install drivers to {server['host']}: {e}"
                    print(message)
                    logger.info(message)


            # Installing necessary packages
            message = f"Start installing necessary packages to server {server['host']} with {server['user']}..."
            print(message)
            logger.info(message)
            conn.sudo(password=server['password'], 'DEBIAN_FRONTEND=noninteractive apt install -y python-is-python3', hide=False)
            conn.sudo(password=server['password'], 'DEBIAN_FRONTEND=noninteractive apt install -y python3.10-venv', hide=False)
            conn.sudo(password=server['password'], 'DEBIAN_FRONTEND=noninteractive apt-get install -y gcc', hide=False)
            conn.sudo(password=server['password'], 'DEBIAN_FRONTEND=noninteractive apt-get install -y g++', hide=False)
            conn.sudo(password=server['password'], 'DEBIAN_FRONTEND=noninteractive apt-get install -y python3-dev', hide=False)
            conn.sudo(password=server['password'], 'DEBIAN_FRONTEND=noninteractive apt-get install -y python3-tk', hide=False)


            message = f"Finished installing necessary packages to server {server['host']} with {server['user']}."
            print(message)
            logger.info(message)

            message = f"Start installing FaceFlick to server {server['host']} with {server['user']}..."
            print(message)
            logger.info(message)
            # Change directory to FaceFlick and run setup.sh
            with conn.cd('/opt/FaceFlick'):
                conn.run('bash setup.sh', hide=False)
            message = f"Finished installing FaceFlick to server {server['host']} with {server['user']}."
            print(message)
            logger.info(message)

            if install_service:
                # Define the content of the service file as a Python multi-line string
                service_file_content = f"""
                [Unit]
                Description=Foreman Service
                After=network.target

                [Service]
                User=root
                Group=root
                WorkingDirectory=/opt/FaceFlick
                Environment="PATH=/opt/FaceFlick/venv/bin"
                ExecStart=/opt/FaceFlick/venv/bin/python3 /opt/FaceFlick/foreman.py
                Restart=always
                RestartSec=180s
                StartLimitInterval=1800
                StartLimitBurst=20

                [Install]
                WantedBy=multi-user.target
                """
                try:
                    print("Installing Foreman Service")
                    # First, create the service file in the home directory of the user
                    remote_service_file_path = f"/home/{server['user']}/foreman.service"
                    file_object = StringIO(service_file_content)
                    conn.put(file_object, remote_service_file_path)                    
                    exist = conn.run("systemctl list-units --full --all | grep -Fq 'foreman.service'", warn=True)
                    if exist .ok:
                        print("The 'foreman' service exists. Let's reinstall it")
                        running = conn.run("systemctl is-active --quiet foreman", warn=True)
                        if running.ok:
                            print("The 'foreman' service is running. Stopping it")
                            conn.sudo(password=server['password'], 'systemctl stop foreman', hide=False)    
                        conn.sudo(password=server['password'], 'systemctl disable foreman', hide=False)
                      
                    # Then, move the service file to /etc/systemd/system with sudo
                    conn.sudo(password=server['password'], f'mv {remote_service_file_path} /etc/systemd/system/foreman.service', hide=False)
                    # Reload the systemd daemon
                    conn.sudo(password=server['password'], 'systemctl daemon-reload', hide=False)
                    # Enable the service
                    conn.sudo(password=server['password'], 'systemctl enable foreman', hide=False)
                except Exception as e:
                    message = f"Failed install service to {server['host']}: {e}"
                    print(message)
                    logger.info(message)

            if install_api:
                # Define the content of the service file as a Python multi-line string
                service_file_content = f"""
                [Unit]
                Description=FaceFlickAPI Service
                After=network.target

                [Service]
                User=root
                Group=root
                WorkingDirectory=/opt/FaceFlick
                Environment="PATH=/opt/FaceFlick/venv/bin"
                ExecStart=/opt/FaceFlick/venv/bin/python3 /opt/FaceFlick/API.py --host 0.0.0.0 --port {api_port}
                Restart=always
                RestartSec=180s
                StartLimitInterval=1800
                StartLimitBurst=20

                [Install]
                WantedBy=multi-user.target
                """
                try:
                    print("Installing FaceFlickAPI Service")
                    # First, create the service file in the home directory of the user
                    remote_service_file_path = f"/home/{server['user']}/faceflickapi.service"
                    file_object = StringIO(service_file_content)
                    conn.put(file_object, remote_service_file_path)                    
                    exist = conn.run("systemctl list-units --full --all | grep -Fq 'faceflickapi.service'", warn=True)
                    if exist .ok:
                        print("The 'faceflickapi' service exists. Let's reinstall it")
                        running = conn.run("systemctl is-active --quiet faceflickapi", warn=True)
                        if running.ok:
                            print("The 'faceflickapi' service is running. Stopping it")
                            conn.sudo(password=server['password'], 'systemctl stop faceflickapi', hide=False)    
                        conn.sudo(password=server['password'], 'systemctl disable faceflickapi', hide=False)
                    
                    # Then, move the service file to /etc/systemd/system with sudo
                    conn.sudo(password=server['password'], f'mv {remote_service_file_path} /etc/systemd/system/faceflickapi.service', hide=False)
                    # Reload the systemd daemon
                    conn.sudo(password=server['password'], 'systemctl daemon-reload', hide=False)
                    # Enable the service
                    conn.sudo(password=server['password'], 'systemctl enable faceflickapi', hide=False)
                    # Start the service
                    conn.sudo(password=server['password'], 'systemctl start faceflickapi', hide=False)
                except Exception as e:
                    message = f"Failed install service to {server['host']}: {e}"
                    print(message)
                    logger.info(message)

            if install_http:
                # Define the configuration                
                httpconfig = f"""
                server {{
                    listen 80;
                    listen [::]:80;

                    server_name {server['host']};

                    location / {{
                        root {loading_point};
                        autoindex on;
                    }}
                }}
                """

                # Check if Nginx is already installed
                nginx_installed = conn.sudo(password=server['password'], 'which nginx', warn=True, hide=True).ok

                if nginx_installed:
                    print("Nginx is already installed. Stopping it...")
                else:
                    print("Nginx not found. Installing it...")
                    conn.sudo(password=server['password'], 'apt update', hide=False)
                    conn.sudo(password=server['password'], 'DEBIAN_FRONTEND=noninteractive apt install -y nginx', hide=False)

                conn.sudo(password=server['password'], 'systemctl stop nginx', hide=False)

                # Check if another service is running on port 80
                if conn.sudo(password=server['password'], 'lsof -i :80', warn=True, hide=False).ok:
                    message = "Another service is running on port 80..."
                    print(message)
                    logger.error(message)

                # Remove all existing configurations
                conn.sudo(password=server['password'], 'rm -f /etc/nginx/sites-available/*')
                conn.sudo(password=server['password'], 'rm -f /etc/nginx/sites-enabled/*')

                # Check if the loading_point directory exists; if not, create it
                if conn.run(f'test -d {loading_point}', warn=True, hide=False).failed:                
                    conn.sudo(password=server['password'], f'mkdir -p {loading_point}', hide=False)

                httpconfig_file_path = f"/home/{server['user']}/images"
                file_object = StringIO(httpconfig)
                conn.put(file_object, httpconfig_file_path)

                # Check if the configuration file already exists in the target directory; if not, move it
                if conn.run(f'test -f /etc/nginx/sites-available/images', warn=True, hide=False).failed:
                    conn.sudo(password=server['password'], f'mv {httpconfig_file_path} /etc/nginx/sites-available/images', hide=False)               
     
                # Check if the symlink already exists; if not, create it
                if conn.run(f'test -L /etc/nginx/sites-enabled/images', warn=True, hide=False).failed:
                    conn.sudo(password=server['password'], 'ln -sf /etc/nginx/sites-available/images /etc/nginx/sites-enabled/')

                # Validate the configuration
                result = conn.sudo(password=server['password'], 'nginx -t', warn=True)
                if result.failed:
                    print("Nginx configuration test failed!")
                    logger.error("Nginx configuration test failed!")

                print("Nginx configuration is valid.")

                # Enable and start the Nginx service
                conn.sudo(password=server['password'], 'systemctl enable nginx', hide=False)
                conn.sudo(password=server['password'], 'systemctl start nginx', hide=False)


            # Copy the config.json file to the FaceFlick directory
            message = f"Start Transfering config.json to server {server['host']} with {server['user']}..."
            print(message)
            logger.info(message)
  

            temp_path = f"/home/{server['user']}/temp_config.json"
            conn.put(local_config_path, temp_path)
            conn.sudo(password=server['password'], f'mv {temp_path} {remote_config_path}')

            

            message = f"Completed Transfering config.json to server {server['host']} with {server['user']}."
            print(message)
            logger.info(message)
            
            if restart_service:
                message = f"Checking if foreman service exists on server {server['host']}"
                print(message)
                logger.info(message)

                exist = conn.run("systemctl list-units --full --all | grep -Fq 'foreman.service'", warn=True)                
                if exist.ok:
                    message = f"Restarting foreman service on server {server['host']}, this will restart its workers and reload new config."
                    print(message)
                    logger.info(message)

                    conn.sudo(password=server['password'], 'systemctl restart foreman', hide=False)                    

            
            message = f"Deployment completed to server {server['host']} with {server['user']}."
            print(message)
            logger.info(message)

  
            if install_driver or install_service or force_restart:
                message = f"Rebooting {server['host']} with {server['user']} for GPU driver update."
                print(message)
                logger.info(message)
                try:
                    conn.sudo(password=server['password'], 'reboot', hide=False)
                except Exception as e:
                    message = f"Server {server['host']} is rebooting."
                    print(message)
                    logger.info(message)

    except Exception as e:
        message = f"Failed to deploy to {server['host']}: {e}"
        print(message)
        logger.error(message)
        logging.error(message)

if __name__ == '__main__':
    with concurrent.futures.ProcessPoolExecutor(max_workers=deploy_settings['max_workers']) as executor:        
        executor.map(deploy_to_server, servers, [install_data]*len(servers), [install_driver]*len(servers),
                      [install_service]*len(servers), [force_restart]*len(servers), [install_api]*len(servers),
                        [restart_service]*len(servers), [install_http]*len(servers))

    print('Deployment to all servers complete')
