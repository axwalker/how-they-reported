FROM joyzoursky/python-chromedriver:3.6

WORKDIR /usr/app

ADD requirements.txt ./
RUN pip install -r requirements.txt

ADD . /usr/app

RUN python -c "import nltk; nltk.download('punkt')"
