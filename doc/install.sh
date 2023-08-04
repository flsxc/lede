#!/bin/bash

# Check if Git is installed
if ! command -v git &> /dev/null
then
    echo "Git is not installed. Please install Git and run this script again."
    exit
else
        echo "Git is ok ...."
fi

# Check if Python 3.10 is installed
python_version=$(python3 --version 2>&1 | awk '{print $2}')
if [[ "$python_version" != 3.10* ]]
then
    echo "Python 3.10 is not installed. Please install Python 3.10 and run this script again."
    exit
else
        echo "Python is ok ....."
        sleep 1
fi

# Check if curl is installed
if ! command -v curl &> /dev/null
then
    echo "curl is not installed. Please install curl and run this script again."
    exit
else
        echo "curl is ok ....."
        sleep 1
fi



# Test if python3-venv is available
python3 -m venv test_venv
if [ $? -ne 0 ]
then
    echo "The virtual environment was not created successfully because ensurepip is not available or other reasons."
    echo "On Debian/Ubuntu systems, you need to install the python3-venv package using the following command:"
    echo ""
    echo "apt install python3.10-venv"
    echo ""
    echo "You may need to use sudo with that command. After installing the python3-venv package, try to run this script again."
    exit
else
    rm -rf test_venv
    echo "venv is ok...."
    sleep 1
fi



# Check if the current directory is inside a Git repository
if ! git rev-parse --is-inside-work-tree &> /dev/null
then
    echo "We are NOT inside FaceFlick Git repository."
    echo "Let's Clone the project for installation."
    if [ ! -d "FaceFlick" ]
    then
        git clone https://github.com/harrywenjie/FaceFlick.git
        cd FaceFlick || exit
    else
        echo "The directory 'FaceFlick' already exists. Please remove or rename it and run this script again."
        exit
    fi
else
    repo_url=$(git config --get remote.origin.url)
    if [ "$repo_url" == "https://github.com/harrywenjie/FaceFlick.git" ]
    then
        echo "We are already inside FaceFlick Git repository."
        echo "Let's check for updates"
        git pull origin
    else
        echo "We are NOT inside FaceFlick Git repository."
        echo "Let's Clone the project for installation."
        if [ ! -d "FaceFlick" ]
        then
            git clone https://github.com/harrywenjie/FaceFlick.git
            cd FaceFlick || exit
        else
            echo "The directory 'FaceFlick' already exists. Please remove or rename it and run this script again."
            exit
        fi
    fi
fi

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]
then
    python3 -m venv venv
    if [ $? -ne 0 ]
    then
        echo "The virtual environment was not created successfully."
        exit
    fi
fi

# Activate the virtual environment and install requirements
source venv/bin/activate
#pip install --use-pep517 -r linux_requirements.txt
pip install --use-pep517 --no-index --find-links=./packages -r linux_requirements.txt

# Create 'models' folders if they don't exist
mkdir -p models

# Download the file using curl and place it in the 'models' folder if it doesn't exist
if [ ! -f "./models/RealESRGAN_x2plus.pth" ]
then
    curl -k -L -o ./models/RealESRGAN_x2plus.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth
fi

if [ ! -f "./models/inswapper_128.onnx" ]
then
    curl -k -L -o ./models/inswapper_128.onnx https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx
fi

if [ ! -f "./models/GFPGANv1.3.pth" ]
then
    curl -k -L -o ./models/GFPGANv1.3.pth https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth
fi

echo "FaceFlick Installation Complete"
echo "If you see any errors, then you need to resolve them first"
echo "If you see no errors, then you can start using the project"
