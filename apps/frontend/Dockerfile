# Image du frontend en deux étapes :
#  1) on construit l'application (Node + Vite) ;
#  2) on sert les fichiers statiques produits avec nginx (léger et rapide).

# --- Étape 1 : build ---
FROM node:22-alpine AS build
WORKDIR /app

# On installe d'abord les dépendances (mise en cache tant que package.json ne change pas).
COPY package.json ./
RUN npm install

# Puis le code source.
COPY . .

# L'URL de l'API est injectée au moment du build (variable Vite).
ARG VITE_API_URL=http://localhost:5000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# --- Étape 2 : service statique ---
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
