FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json /app/

# Install dependencies
RUN npm install

# Copy server code
COPY server.js /app/

EXPOSE 3000

CMD ["node", "server.js"]
