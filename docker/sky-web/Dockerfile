# Offline-only image used by SKY Developer for HTML5 / CSS3 / web DOM checks.
# Build is an explicit owner action; runtime never downloads dependencies.
FROM node:22-alpine
RUN npm install --global --ignore-scripts --no-audit --no-fund \
      html-validate@11.17.0 stylelint@17.16.0 jsdom@27.4.0 \
    && npm cache clean --force
ENV NODE_PATH=/usr/local/lib/node_modules
WORKDIR /opt/sky-web
COPY htmlvalidate.json stylelint.json smoke.cjs /opt/sky-web/
