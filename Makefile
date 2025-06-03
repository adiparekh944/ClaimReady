.PHONY: everything backend frontend install-backend install-frontend

application: 
	$(MAKE) backend & \
	$(MAKE) frontend

backend:
	  cd backend && source ClaimReady/bin/activate && FLASK_APP=api.py flask run --port=8080

frontend:
	cd frontend && npm run dev

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install 