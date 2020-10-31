SHELL = /bin/sh
ROOTDIR = $(realpath .)
CONFIG = crashrestarter.cfg

install:
	pip3 install --user src/requirements.txt

update:
	git pull

start: update
	python3 src/E4GLCrashRestarter.py -c ${ROOTDIR}/${CONFIG}

docker:
	sudo docker-compose up -d

update-docker:
	sudo docker-compose down --rmi all
	git pull
	sudo docker-compose up -d