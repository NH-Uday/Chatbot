# /client/Dockerfile
FROM node:20-alpine

WORKDIR /app

# Install deps
COPY package*.json ./
RUN npm install

# Copy all Next.js source
COPY . .

# Build-time public env var from ARG
ARG NEXT_PUBLIC_API_BASE
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}

RUN npm run build

# Start Next.js in production mode
CMD ["npm", "run", "start", "--", "-p", "3000"]
