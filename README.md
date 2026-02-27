# Med-Flow-UCSC ~ App [Demo]
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

<br> Run front end on local servers (go to folder `medflow-ui`): `npm run dev`

# Backend setup
Go to the `backend` folder via a new terminal window.
Run this commands on a new terminal.

## Environment setup
Create new environment: `conda create -n med-flow_backend python=3.12 -y`
<br> Activate environment: `conda activate med-flow_backend`
<br> Make sure you are inside the `backend` folder.
<br> Install dependencies: `pip install -r requirements.txt`

## Run Backend API services
Command (make sure in folder `backend`): `uvicorn app.main:app --reload --port 8000`