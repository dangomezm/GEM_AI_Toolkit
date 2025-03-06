# GEM AI Toolkit
This is the beta version of the toolkit for building feature prediction using facade images, for seismic risk assessment with AI. This toolkit allows analysis of images from Google Street View, using the Google API, and also supports images from the local device. The Graphic User Interface enables a fast assessment of the building, including an object detection module, to isolate the building of interest.

![image](https://github.com/user-attachments/assets/e809d08e-fe5a-466d-bc86-b74b14c95796)

# How to use
This guideline utilizes [Anaconda](https://www.anaconda.com/) to facilitate the configuration of the recommended virtual environment for working with AI. It can be downloaded for various operating systems from  
[Download Anaconda](https://www.anaconda.com/download/success), and installation instructions can be found in [Installing Anaconda](https://www.anaconda.com/docs/getting-started/anaconda/install#macos-linux-installation). Once Anaconda has been installed, it is necessary to create a virtual environment. *Note: Python 3.9.13 can also be installed directly, and the virtual environment can be created using your preferred method* 

## 1. Create a virtual environment 
### *Windows*
* Clone this repository
* Open Anaconda Prompt
* *Create a virtual environment:* conda create -n MY_VIRTUAL_ENVIRONMENT_NAME python=3.9.13 (e.g., conda create -n GEM_AI python=3.9.13)

  ![conda](https://github.com/user-attachments/assets/69da3746-5967-4f68-b6c8-37bd168313f9)

```bash
conda create -n YOUR_VIRTUAL_ENVIRONMENT_NAME python=3.9.13
``` 
* Activate the virtual environment
```bash
conda activate YOUR_VIRTUAL_ENVIRONMENT_NAME 
```
![image](https://github.com/user-attachments/assets/c0d77e7f-931c-472f-a144-a1bb84cbb406)

* Assign path to the cloned repository
```bash
cd /d YOUR_REPO_PATH
```
![image](https://github.com/user-attachments/assets/66ae8a6d-6855-4316-8c8e-1fc2557d8ce5)

* Install dependencies
```bash
pip install -r requirements.txt
```
* Execute GUI
```bash
python main.py
```
![image](https://github.com/user-attachments/assets/caf7ec75-bd96-4406-a881-a3a97336b7ee)

### *MacOS*

### *Linux*

# Citation
Daniel Gómez. (2025). dangomezm/GEM_AI_Toolkit: GEM_V1 (GEM_V1). Zenodo. https://doi.org/10.5281/zenodo.14977499
