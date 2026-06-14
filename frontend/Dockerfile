# SprachBoot frontend — Next static export served by nginx.
# next.config.ts uses output: 'export', so the build emits a static ./out
# bundle. NEXT_PUBLIC_API_URL is inlined at build time (browser hits the host
# port), so it is a build arg, not a runtime env.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/out /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
