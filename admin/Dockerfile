FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/build ./build
# sirv-cli is tiny (~3 MB) and handles SPA fallback (--single) so SvelteKit's
# client-side routing works for any URL the user lands on directly.
RUN npm install --omit=dev --no-audit --no-fund sirv-cli@3.0.0
EXPOSE 8501
CMD ["npx", "sirv-cli", "build", "--port", "8501", "--host", "0.0.0.0", "--single", "--quiet"]
