# Deployment template

The application is designed for a Vite frontend on Firebase Hosting and a FastAPI container on
Google Cloud Run. Treat every identifier below as an example and use your own cloud project.

1. Create a Google Cloud project and enable Cloud Run, Cloud Build, Artifact Registry, Secret
   Manager and Firestore.
2. Create separate runtime, build and GitHub deployment service accounts with least privilege.
3. Store `APP_LLM_API_KEY` in Secret Manager. Never commit it or expose it to the frontend.
4. Copy `deploy/env.production.example.yaml` to the ignored `deploy/env.production.yaml` and
   replace `YOUR_DOMAIN`.
5. Deploy `backend/` to a Cloud Run service and update the service name in `firebase.json`.
6. Build `frontend/`, initialize Firebase Hosting, and configure the API rewrite.
7. Configure GitHub workload identity federation if you want keyless continuous deployment.
8. Run the health check and verify rate limiting, proxy hops, security headers and the resume
   endpoint before directing traffic to the service.

The private source repository uses a project-specific deployment workflow. It is intentionally not
included in this generated public copy.

