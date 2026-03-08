FROM node:20-bookworm-slim

WORKDIR /app

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY renderer/package.json ./package.json
COPY renderer/package-lock.json ./package-lock.json

RUN npm ci
RUN npx playwright install --with-deps chromium

COPY renderer/server.js ./server.js
COPY renderer/render.html ./render.html
COPY renderer/render-entry.js ./render-entry.js
COPY renderer/vite.config.js ./vite.config.js
COPY renderer/src/renderers ./src/renderers

RUN npm run build

ENV PORT=3001

EXPOSE 3001

CMD ["node", "server.js"]
