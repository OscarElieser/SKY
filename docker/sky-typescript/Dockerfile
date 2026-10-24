# Build once with: docker build -t sky-typescript:5.7.3 docker/sky-typescript
# Runtime use is strictly offline (SKY uses --pull never, --network none).
FROM node:22-alpine
RUN npm install --global --ignore-scripts --no-audit --no-fund typescript@5.7.3 \
 && npm cache clean --force
# Never run the model's code during Docker image build.
