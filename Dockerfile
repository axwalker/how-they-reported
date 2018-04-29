FROM jaimelopesflores/python3-firefox-headless

WORKDIR /usr/app

ADD requirements.txt ./
RUN pip install -r requirements.txt

ADD . /usr/app

RUN python -c "import nltk; nltk.download('punkt')"
