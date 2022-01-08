This is a backend for Gitter (http://gitter.im) for errbot (http://errbot.io).

It allows you to use errbot from Gitter.

[![Screenshot](https://raw.githubusercontent.com/errbotio/err-backend-gitter/master/screenshot.png)](#screenshot)

## Installation

```
git checkout https://github.com/gbin/err-backend-gitter.git
```

and add:

```
BACKEND = 'Gitter'
BOT_EXTRA_BACKEND_DIR = '/path_to/err-backend-gitter'
```

to your config.py

## Authentication
From there you have can either add an application or use a personal token from a
user reserved to the bot.

### Adding an application, workflow for auth
1. pip install bottle requests
2. execute the script: ./oauth.py and it will guide you

### Adding as a real user
1. authenticate as the bot user (new incognito window helps ;) )
2. go visit https://developer.gitter.im/apps
3. use directly the token like this in you config.py

```
BOT_IDENTITY = {
    'token' : '54537fa855b9a7bbbbbbbbbc568ea7c069d8c34d'
}
```

## Contributing

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D
