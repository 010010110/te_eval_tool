
FROM node:20-bullseye






RUN apt-get update && \
    apt-get install -y python3.9 python3.9-venv python3.9-dev \

                       python3-pip \
                       build-essential default-jdk && \
    apt-get clean


RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1





WORKDIR /app


COPY backend/package.json backend/package-lock.json ./backend/
RUN npm install --prefix ./backend






COPY CLI/ /app/CLI/


RUN pip install --no-cache-dir -r CLI/requirements.txt







WORKDIR /app/CLI/
RUN python3 src/main.py env setup --model all






WORKDIR /app/backend
CMD [ "node", "server.js" ]


EXPOSE 3002