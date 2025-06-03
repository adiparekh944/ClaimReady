# ClaimReady: Next-Gen Home Inventory & Valuation 🔥🏡

![ClaimReady Banner](https://github.com/user-attachments/assets/5ea1ce92-ccce-4c1d-b5ba-1c59a04c6a4c)

**ClaimReady** is the fastest way to create a digital inventory of your home, get instant AI-powered valuations, and prepare for insurance claims—before disaster strikes. Built for speed, privacy, and peace of mind.

---

## 🚀 Why ClaimReady?

- **No More Paperwork:** Just upload a video walkthrough—ClaimReady detects, catalogs, and values your items automatically.
- **AI Valuation:** Uses Google Gemini for multimodal (image + text) price estimates, tailored to your region and item condition.
- **Voice Assistant:** Ask about your inventory, get valuations, or request insurance advice—all hands-free.
- **Privacy First:** Your data is encrypted and stored securely with Supabase. You control your records.
- **Disaster-Ready:** Designed for wildfire, flood, and theft risk zones—so you're never caught unprepared.

---

## 🛠️ Quickstart

1. **Clone the repo:**
   ```bash
   git clone https://github.com/your-org/claimready.git
   cd claimready
   ```
2. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   cd frontend && npm install
   ```
3. **Set up environment:**
   - Copy `.env.example` to `.env` in `backend/` and fill in your API keys (Supabase, Gemini, ElevenLabs, etc).
4. **Run the backend:**
   ```bash
   cd backend
   python api.py
   ```
5. **Run the frontend:**
   ```bash
   cd ../frontend
   npm run dev
   ```
6. **Open your browser:**
   - Visit [http://localhost:3000](http://localhost:3000) to get started.

---

## ✨ Features

- **Video-to-Inventory:** Upload a home tour video—ClaimReady uses YOLOv8 to detect and snapshot every valuable item.
- **AI-Powered Valuation:** Each item is analyzed by Gemini for a conservative, insurance-grade price estimate.
- **Voice-Driven Insights:** Interact with your inventory using natural language—get instant answers and insurance tips.
- **Secure Cloud Storage:** All data is stored in Supabase with strict RLS policies and encryption.
- **Export & Share:** Download your inventory or share it with your insurance provider in one click.

---

## 🏗️ Architecture Overview

- **Frontend:** Next.js (React), TypeScript, Tailwind CSS
- **Backend:** Flask (Python), YOLOv8, Gemini API, ElevenLabs, Supabase
- **Database:** Supabase Postgres (with RLS)
- **Storage:** Supabase Buckets for images/videos
- **AI:** Google Gemini (multimodal), OpenAI Whisper (voice-to-text), ElevenLabs (text-to-speech)

---

## 🤝 Contributing

We welcome contributions! To get started:

1. Fork the repo and create a new branch.
2. Make your changes (see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines).
3. Submit a pull request with a clear description.

**Ideas for contribution:**
- New AI prompts for valuation or insurance advice
- UI/UX improvements
- Integrations with more insurance providers
- Localization (multi-language support)

---

## 📣 Get Involved

- **Star this repo** to support the project!
- **Open an issue** for bugs, feature requests, or questions.
- **Join our Discord** (link coming soon) to connect with the team and other users.

---

## 📝 License

MIT License. See [LICENSE](LICENSE) for details.

---

> ClaimReady: Because your memories deserve more than a spreadsheet.
