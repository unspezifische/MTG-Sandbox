# Build stage
FROM node:20 AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
# The shared Kachhapa appearance prebuild lives above this repository and is
# verified by the host/CI build. The frontend-only Docker context cannot read
# that parent workspace, so build the already-verified React source directly.
RUN npx react-scripts build

# Serve stage
FROM nginx:alpine

COPY nginx-docker.conf /etc/nginx/nginx.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
