# ClaimReady: Smart Home Inventory & Valuation 📸🏠

![ClaimReady Logo](public/logo%202.png)

ClaimReady transforms your home photos and videos into a comprehensive digital inventory with intelligent valuations. Whether you're preparing for insurance claims, moving, or simply want to keep track of your belongings, ClaimReady makes it effortless to document and value everything that matters.

## How It Works 🖥️

ClaimReady uses cutting-edge AI technology to automatically detect, catalog, and value your home belongings from simple photos and videos.

- **Smart Detection:** Upload photos or videos of your home—ClaimReady automatically detects your belongings using advanced computer vision (Ultralytics YOLO v11), saving you hours of manual documentation. ✨

- **Intelligent Valuation:** Every detected item is analyzed by Google Gemini AI, combining image understanding and market data to provide accurate replacement value estimates—no manual research required. 💎

- **Multi-File Support:** Upload multiple photos or videos at once for comprehensive coverage of your entire home. Our system processes each file independently and combines all results into a unified inventory. 📸

- **Beautiful Results:** View your complete inventory with item details, estimated values, and a comprehensive summary of your total home value. 🎯

- **Secure Storage:** All your data is safely stored using Supabase's powerful backend services, ensuring your inventory is always accessible and protected. 🔒

## Key Features 🌟

### 📸 **Photo & Video Upload**
- Support for multiple image formats (JPG, PNG, GIF, BMP, WEBP)
- Video support (MP4, AVI, MOV, MKV, WMV)
- Drag-and-drop interface for easy file selection
- Batch processing for multiple files

### 🤖 **AI-Powered Detection**
- Advanced object detection using YOLO v11
- Automatic item categorization and identification
- Handles complex scenes with multiple objects
- Deduplication to prevent overcounting

### 💰 **Smart Valuation**
- Google Gemini AI for intelligent price estimation
- Market-aware pricing based on current trends
- Condition assessment from visual analysis
- Brand recognition for accurate valuations

### 📊 **Comprehensive Results**
- Total inventory value calculation
- Individual item details and valuations
- Combined results from multiple uploads
- Clean, organized presentation

## The Problem We Solve ☑️

Homeowners and renters face several challenges when it comes to documenting their belongings:

- **Time-Consuming Documentation:** Manually photographing and cataloging every item in your home is tedious and often incomplete
- **Insurance Preparation:** When disaster strikes, having a detailed inventory with valuations can make the difference between adequate compensation and significant losses
- **Moving & Organization:** Whether moving, downsizing, or just organizing, having a complete inventory helps with planning and decision-making
- **Value Assessment:** Most people don't know the true replacement value of their belongings until it's too late

ClaimReady solves these challenges by automating the entire process—from detection to valuation—in just minutes.

## Technology Stack 🛠️

### Frontend
- **Next.js 14** with TypeScript for a modern, responsive web application
- **Tailwind CSS** for beautiful, consistent styling
- **Framer Motion** for smooth animations and interactions
- **Custom fonts** (Black Future, Kumbh Sans) for unique branding

### Backend
- **Python Flask** API server for robust backend processing
- **Ultralytics YOLO v11** for advanced object detection
- **Google Gemini AI** for intelligent item valuation
- **Supabase** for secure data storage and management

### Key Integrations
- **Supabase Database** for storing job results and user data
- **Google Gemini API** for multimodal AI analysis
- **File Upload System** supporting multiple formats and batch processing

## Getting Started 🚀

### Prerequisites
- Node.js 18+ and npm
- Python 3.8+ with pip
- Supabase account and project
- Google Gemini API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ClaimReady.git
   cd ClaimReady
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   python api.py
   ```

4. **Environment Configuration**
   - Set up your Supabase credentials
   - Configure Google Gemini API key
   - Update environment variables as needed

### Usage

1. **Upload Files:** Navigate to the upload page and select photos or videos of your home
2. **Processing:** ClaimReady will automatically detect and analyze all items
3. **Review Results:** View your complete inventory with valuations on the results page
4. **Export:** Use your inventory for insurance, moving, or personal organization

## What Makes ClaimReady Special ❤️

- **Effortless:** Turn minutes of video or a few photos into a complete digital inventory
- **Accurate:** AI-powered detection and valuation ensures comprehensive coverage
- **Scalable:** Handles everything from studio apartments to large homes
- **User-Friendly:** Beautiful, intuitive interface that anyone can use
- **Secure:** Enterprise-grade security with Supabase backend

## Future Roadmap 🗺️

We're constantly improving ClaimReady to better serve our users:

- **Mobile App:** Native iOS and Android applications for on-the-go inventory management
- **Insurance Integration:** Direct integration with insurance providers for seamless claims processing
- **Advanced Analytics:** Detailed insights into your home value trends and recommendations
- **Voice Assistant:** Natural language queries about your inventory and valuations
- **Export Options:** PDF reports, CSV exports, and integration with popular home management tools

## Contributing 🤝

We welcome contributions to make ClaimReady even better! Please see our contributing guidelines for more information.

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Support 💬

Have questions or need help? Reach out to us through our support channels or create an issue on GitHub.

---

**ClaimReady** - Making home inventory management effortless, accurate, and secure. 🏠✨
