# FleetLock Phase 3 (Monorepo)

This repository contains both services for the FleetLock Phase 3 project:

- `backend/` - Flask API, auth/KYC/claims/admin workflows, Render deployment config
- `frontend/` - React app (CRA + CRACO), Vercel deployment config

## Source Snapshot

This monorepo was assembled from:

- Backend source commit: `07eb3b9`
- Frontend source commit: `98eb6a3`

## Local Development

### Backend

1. `cd backend`
2. `pip install -r requirements.txt`
3. Configure `.env` from `.env.example`
4. `python main.py`

### Frontend

1. `cd frontend`
2. `npm install`
3. Create `.env.local` with:
   - `REACT_APP_API_BASE_URL=http://localhost:5000`
   - `REACT_APP_BACKEND_URL=http://localhost:5000`
4. `npm start`

## Deployment

- Backend: Render (uses `backend/render.yaml` and `backend/.python-version`)
- Frontend: Vercel (uses `frontend/vercel.json`)
