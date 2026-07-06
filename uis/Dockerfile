FROM node:22-alpine

WORKDIR /app/uis

COPY website/package.json website/package-lock.json ./website/
RUN cd website && npm ci

COPY backoffice/landing/package.json backoffice/landing/package-lock.json ./backoffice/landing/
RUN cd backoffice/landing && npm ci

COPY backoffice/backoffice_functions/package.json backoffice/backoffice_functions/package-lock.json ./backoffice/backoffice_functions/
RUN cd backoffice/backoffice_functions && npm ci

COPY backoffice/talent-tracker/package.json backoffice/talent-tracker/package-lock.json ./backoffice/talent-tracker/
RUN cd backoffice/talent-tracker && npm ci

COPY incident_analyzer/package.json incident_analyzer/package-lock.json ./incident_analyzer/
RUN cd incident_analyzer && npm ci

COPY supplier_directory/package.json supplier_directory/package-lock.json ./supplier_directory/
RUN cd supplier_directory && npm ci

COPY start.sh ./start.sh
RUN chmod +x ./start.sh

EXPOSE 3000 3001
CMD ["./start.sh"]
