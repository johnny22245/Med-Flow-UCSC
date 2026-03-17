# Med-Flow-UCSC ~ App
**Authors**  
- Akash Chowdhury (achowd10@ucsc.edu)
- Vlad Pavlovich (vpavlovi@ucsc.edu)
- Julius Dunfoy (jdunfoy@ucsc.edu)
- Abhiram Borra (abborra@ucsc.edu)

Med-Flow is a local, multi-agentic AI for safe clinical support. Using a hub-and-spoke architecture with LangGraph and LoRA adapters, it decomposes reasoning into staged, verifiable steps. It enforces human-in-the-loop checkpoints at every node to ensure privacy, auditability, and safety.

## License
This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**. 

### 🛑 Commercial Use Restriction
Commercial use of this software is strictly prohibited without a separate agreement. If you wish to use Med-Flow for commercial purposes, including but not limited to paid clinical services or integration into proprietary software, please contact the authors at [Insert Email] to discuss licensing terms.

## Documentation

Check the latest `*....V{max_number}` in the folder `documentation`.

## Environment setup - UI (Front-end)
Create new environment: `conda create -n med-flow python=3.12 -y`
<br> Activate environment: `conda activate med-flow`
<br> Install dependencies: `pip install -r requirements.txt`

### School GPU NPM setup
<br> Run this commands:
<br> `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash`
<br> `source ~/.bashrc`
<br> `nvm install --lts`
<br> Check if properly installed: `npm -v`
<br> Go to folder: `medflow-ui` and run: `npm install`


<br> Run front end on local servers (go to folder `medflow-ui`): `npm run dev`

# Backend setup
Go to the `backend` folder via a new terminal window.
Run this commands on a new terminal.

## Environment setup
Create new environment: `conda create -n med-flow_backend python=3.12 -y`
<br> Activate environment: `conda activate med-flow_backend`
<br> Make sure you are inside the `backend` folder.
<br> Install dependencies: `pip install -r requirements.txt`

### Setup for Llava-Med
Create new environment: `conda create -n llava_med python=3.10 -y`
<br> Activate environment: `conda activate llava_med`
<br> Install Llava-Med, go to folder `backend/LLaVA-Med` and run: `pip install -e .`

## Run Backend API services
Command (make sure in folder `backend`): `bash start_backend.sh`

## DB setup
Create new environment: `conda create -n medflow_DB python=3.12 -y`
<br> Activate environment: `conda activate medflow_DB`
<br> Make sure to be on the root folder which contains: `docker-compose.yml`
<br> Install dependencies: `pip install -r requirements_DB.txt`

### For Mac UI testing only:
Install docker over mac/linux. Check if the same is present: `docker --version`. If not present, follow the installation steps: 
<br> 1. `brew install --cask docker` -- Post this use Applications to open and start docker app.
<br> Sanity commands: A) `docker run hello-world` , B) `docker compose version`
<br> Next steps:
<br> Run from folder which contains: `docker-compose.yml` -- `docker compose up -d`

### For Linux run via GPU for models:
Install postgres into your existing environment
`conda install -c conda-forge postgresql -y`

Initialize a data folder in your home directory (where you have permission)
`initdb -D ~/medflow_db_data`

Start the server on a custom port (5433) so it doesn't clash
`pg_ctl -D ~/medflow_db_data -l logfile -o "-p 5433" start`

Create your database
`createdb -p 5433 medflow_db`
<br> Goto `backend` folder and then run: `alembic upgrade head`

## Other notes:
Kindly use local model paths and set them in this file: `backend/.env`

For any-other model model dependecies check this drive folder (view via UC Santa Cruz email): `https://drive.google.com/drive/folders/18XrMrYmM1G4KvlbNdc2ws4RS_Q0jH_lJ?usp=share_link`
