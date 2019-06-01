#Docker image for E4GLCrashRestarter
#Creator:  H3dius/Hedius admin@e4gl.com gitlab.com/hedius
FROM python:3

#User and Group ID of the account used for execution
ARG UID=4000
ARG GID=4000

LABEL maintainer="Hedius @ hedius@e4gl.com" \
      description="image for E4GLCrashRestarter" \
      version="1.0"

# account for execution of script
RUN groupadd -r -g $GID  pythonRun && \
    useradd -r -g pythonRun -u $UID pythonRun

WORKDIR /usr/src/app

COPY --chown=pythonRun:pythonRun src/* ./

#Install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

RUN chown pythonRun:pythonRun -R /usr/src/app

USER pythonRun:pythonRun

CMD ["python", "E4GLCrashRestarter.py", "-c", "crashrestarter.cfg"]
