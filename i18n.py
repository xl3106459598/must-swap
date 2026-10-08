LANGUAGES = ('en',)


def get_lang():
    return 'en'


def t(text, **values):
    return text.format(**values) if values else text
