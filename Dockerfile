FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update && apt-get -y upgrade
RUN apt-get -y install npm
RUN apt-get -y install nodejs build-essential
RUN apt-get -y install python3
RUN apt-get -y install python3-pip
RUN apt-get -y install sqlite3
RUN useradd -ms /bin/bash ubuntu

USER ubuntu
WORKDIR /home/ubuntu/
COPY --chown=ubuntu . /home/ubuntu/

USER root
RUN python3 -m pip install -r ./django-rest-react-prototype/requirements.txt --target=/usr/local/lib/python3.8/dist-packages
RUN python3 -m pip install django --target=/usr/local/lib/python3.8/dist-packages

EXPOSE 8000
EXPOSE 80
EXPOSE 5000

WORKDIR /home/ubuntu/django-rest-react-prototype/frontend/
RUN npm install && npm run dev

WORKDIR /home/ubuntu/
CMD ["./runServers.sh"]
USER ubuntu
