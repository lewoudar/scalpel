# Configuration
 
Pyscalpel allows you to configure various parameters for your spider using different flexible ways.
 
## Instantiating directly the Configuration class
 
The first obvious way to configure your spider is to use the class `Configuration` directly in your code.

```python
from scalpel import Configuration
from scalpel.green import StaticSpider, StaticResponse

def parse(spider: StaticSpider, response: StaticResponse) -> None:
    pass

config = Configuration(follow_robots_txt=False, min_request_delay=2)
spider = StaticSpider(urls=['http://foo.com'], parse=parse, config=config)
```

For a reference of all the settings you can set, please refer to the relevant [api](api.md#configuration) section.

Keep in mind that you can access your configuration during spider execution through `spider.config` attribute and you can even
set some values on the fly, but it is a good idea to only set your configuration before running your spider.

!!! note
    All the settings available have a default value.

## Setting configuration through the use of a .env file

To follow the [12 factor app](https://12factor.net/config) principles, you need to store your configuration in your
environment. One easy way to accomplish this is to use `.env` files.

To know what name you need to use in your `.env` file for a configuration variable, just put the `Configuration` 
attribute in **capital letters** and prefixed it with `SCALPEL_` i.e if you want to set the
`Configuration.min_request_delay` property, you need to set the environment variable `SCALPEL_MIN_REQUEST_DELAY`.

The value of the attribute is simple for string and numbers, but it is less obvious for other types, here are what 
you can expected for the following cases:

- For boolean values like `Configuration.follow_robots_txt`, the values `true`, `yes`, `y` and `1` are evaluated to 
`True` and values `false`, `no`, `n` and `0` are evaluated to `False`.
- For `Enum` like [Browser](api.md#browser), just write the enum values like `FIREFOX` or `CHROME`.
- For callables like `Configuration.msgpack_encoder` just write the path to the callable using dot notation. For example
if you have a module named `my_module` and a callable `my_callable` in that module, you can refer to it with
`my_module.my_callable`. You can adopt this logic with modules nested in packages. Keep in mind that the module you
specify must be in the python path for this to work.
- For a list of callables like `Configuration.response_middlewares`, the logic is the same as before except that each
callable is separated by a `;` or `:` or `,` or a whitespace. For example `my_module.callable_1:my_module.callable_2`.
For the first three separators, you can even put a whitespace after the separator for more visibility:
`my_module.callable_1, my_module.callable_2`.

Assuming we have a `.env` file like the following in our project:

```.env
SCALPEL_USER_AGENT = Mozilla/5.0
SCALPEL_FETCH_TIMEOUT = 4.0
SCALPEL_FOLLOW_ROBOTS_TXT = yes
```

We can set configuration for our spider like this:

```python
from scalpel import Configuration

config = Configuration.load_from_dotenv('.env')
print(config.follow_robots_txt)  # True
```

## Setting configuration through the use of a yaml file

[YAML](https://en.wikipedia.org/wiki/YAML) is a popular file format used for project configuration. You can use it to
configure your spider through the convenient class method `Configuration.load_from_yaml`. All your settings must be under
a top level key *scalpel*.

Assuming we have a yaml file like the following:

```yaml
# conf.yaml
scalpel:
    fetch_timeout: 4.0
    user_agent: Mozilla/5.0
    follow_robots_txt: true
```

We can set configuration for our spider like this:

```python
from scalpel import Configuration

config = Configuration.load_from_yaml('conf.yaml')
print(config.fetch_timeout)  # 4.0
```

## Setting configuration through the use of a toml file

[TOML](https://en.wikipedia.org/wiki/TOML) is another popular file format for project configuration. You can use it to
configure your spider through the use of the convenient class method `Configuration.load_from_toml`. Like for the yaml
part, your configuration must be on the *scalpel* namespace.

Assuming we have a toml file like the following:

```toml
# conf.toml
[scalpel]
user_agent = "Mozilla/5.0"
fetch_timeout = 4.0
follow_robots_txt = true
```

We can set configuration for our spider like this:

```python
from scalpel import Configuration

config = Configuration.load_from_toml('conf.toml')
print(config.fetch_timeout)  # 4.0
```