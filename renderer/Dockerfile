FROM globalinsight-renderer:latest

WORKDIR /app

COPY renderer/server.js ./server.js
COPY renderer/render.html ./render.html
COPY renderer/render-entry.js ./render-entry.js
COPY renderer/vite.config.js ./vite.config.js
COPY renderer/package.json ./package.json
COPY renderer/src/renderers ./src/renderers

RUN npm run build

ENV PORT=3001

EXPOSE 3001

CMD ["node", "server.js"]
