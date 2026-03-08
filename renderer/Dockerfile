FROM node:20-slim

RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libdbus-1-3 libxkbcommon0 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libwayland-client0 \
    fonts-noto-cjk fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY renderer/package.json ./package.json
RUN npm install
RUN npx playwright install chromium

COPY renderer/server.js ./server.js
COPY renderer/render.html ./render.html
COPY renderer/render-entry.js ./render-entry.js
COPY renderer/vite.config.js ./vite.config.js
COPY src/renderers ./src/renderers

RUN npm run build

ENV PORT=3001

EXPOSE 3001

CMD ["node", "server.js"]
