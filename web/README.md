# Drop Calculator - Harmony of Dissonance

A web-based drop rate calculator for Castlevania: Harmony of Dissonance, enhanced with the luckyJuste patch mechanics. Calculate item drop rates with Rare Ring bonuses and Luck-based modifiers.

## Features

- **Drop Rate Calculation**: Browse 101 monsters and their drop rates (out of 1024).
- **Rare Ring Bonus**: Calculate how Rare Ring affects drop chances (+32 for common items, +16 for rare items).
- **luckyJuste Patch Support**: Model how equipment Luck affects drop rates with customizable EQUIPMENT_LUCK input.
- **Rare Ghost Mechanics**: Calculate appearance chance and rolls for the rare Rare Ghost enemy based on Luck.
- **Search & Filter**: Filter monsters and items by name in real time.
- **Responsive Design**: Optimized for desktop and mobile viewing.

## Development

### Prerequisites

- Node.js 20
- npm

### Install Dependencies

```bash
npm install
```

The project uses a local `.npmrc` file pointing to the public npm registry (not BBVA's artifactory).

### Start Development Server

```bash
npm run dev
```

The dev server will start on `http://localhost:5173/` (or another available port). The app will auto-reload on code changes.

### Project Structure

```
src/
├── drops-app.js          # Main Lit component (<drops-app>)
├── drops-app.css         # Component styles (imported via ?inline)
├── drop-math.js          # Pure logic: drop calculations, Rare Ghost mechanics
├── firebase-config.js    # Firebase initialization
└── main.js              # Entry point

drops.json              # 101 monster drop data (name, common/rare drop rates in HEX)
public/
├── favicon.svg          # Favicon
index.html             # Root HTML
```

## Building

### Production Build

```bash
npm run build
```

Output is in `dist/`. The build minifies and optimizes all assets.

```bash
npm run preview
```

Preview the production build locally before deploying.

## Deployment

### Firebase Hosting

The project is configured for Firebase Hosting.

**Prerequisites:**
- Firebase account
- Firebase CLI installed: `npm install -g firebase-tools`

**Deploy:**

```bash
firebase login
firebase deploy
```

The live site will be available at `https://harmony-of-dissonance-drop.firebaseapp.com`

## Technologies

- **Lit 3.x**: Lightweight web component framework (JavaScript, no TypeScript)
- **Vite 6.4.3**: Fast build tool and dev server
- **Firebase Hosting**: Deployment platform
- **Native JSON Import**: Drop data is imported as `drops.json`

## License

Harmony of Dissonance is owned by Konami. This calculator is a fan-made educational tool.
