# Makefile for ClaimReady

# Run the backend Flask API
backend:
	cd backend && python3 api.py

# Run the frontend Next.js app
frontend:
	cd frontend && npm run dev

# Run both backend and frontend in parallel
application:
	$(MAKE) backend & \
	$(MAKE) frontend

.PHONY: backend frontend application 